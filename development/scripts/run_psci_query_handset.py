#!/usr/bin/env python3
"""Build and temporarily execute standard PSCI queries; original Android returns.

No reset call, partition write or UART MMIO. Closed boot/DTB inputs stay private.
"""
import argparse,datetime as dt,json,shlex,struct,subprocess,time,uuid
from pathlib import Path
from entry_probe import ROOT,SOURCE,sha,image_parameters,compile_probe,instrument
from private_android_image import read_boot,repack
from inspect_device import read_fdt
ADB='/mnt/d/Android/platform-tools/adb.exe';FB='/mnt/d/Android/platform-tools/fastboot.exe'
def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',required=True,type=Path);p.add_argument('--qemu-report',required=True,type=Path);p.add_argument('--serial',required=True);a=p.parse_args()
 q=json.loads(a.qemu_report.read_text());assert q['passed'] and not q['reset_executed']
 boot=read_boot(a.collection.resolve());params=image_parameters(boot['image'])
 out=ROOT/'evidence/private/psci-query'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(mode=0o700,parents=True,exist_ok=False)
 identifier='raphael-psci-query-'+uuid.uuid4().hex
 probe=compile_probe(out,params,identifier,main_source=SOURCE/'PsciProbe.c');image=instrument(boot['image'],probe,params);packed=repack(boot,image);(out/'boot-psci-query.img').write_bytes(packed)
 provenance=json.loads((out/'probe-inputs.json').read_text())
 for item in provenance['inputs']:
  source=ROOT/item['file'];data=source.read_bytes();assert sha(data)==item['sha256'];target=out/'snapshot'/item['file'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 disassembly=(out/'EntryProbe.disassembly.txt').read_text();assert 'smc' in disassembly and 'hvc' not in disassembly
 report=dict(passed=False,identifier=identifier,artifact_directory=str(out.relative_to(ROOT)),source_boot_sha256=sha(boot['raw']),image_sha256=sha(packed),probe_sha256=sha(probe),query_only=True,reset_executed=False,used_flash_or_erase=False,qemu_report=str(a.qemu_report.resolve().relative_to(ROOT)),qemu_report_sha256=sha(a.qemu_report.read_bytes()),source_inputs=provenance['inputs'])
 records=[]
 def save():
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'device-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 def call(tool,*args,timeout=10,file=None):
  command=[tool,'-s',a.serial,*args]
  try:result=subprocess.run(command,capture_output=True,timeout=timeout)
  except subprocess.TimeoutExpired:records.append(dict(command=command,timeout=True));save();return None
  entry=dict(command=command,returncode=result.returncode,stderr=result.stderr.decode(errors='replace'),utc=dt.datetime.now(dt.timezone.utc).isoformat())
  if file:(out/file).write_bytes(result.stdout);entry.update(file=file,sha256=sha(result.stdout))
  else:entry['stdout']=result.stdout.decode(errors='replace')
  records.append(entry);save();return result
 def root(command,**kw):return call(ADB,'exec-out','su -c '+shlex.quote(command),**kw)
 try:
  result=root('sha256sum /dev/block/bootdevice/by-name/boot');assert result and result.returncode==0 and result.stdout.decode().split()[0]==report['source_boot_sha256']
  result=root('cat /sys/firmware/fdt',file='before.dtb');assert result and result.returncode==0
  tree=read_fdt(result.stdout);psci=next(n for n in tree.children if n.name=='psci');assert psci.strings('method')==['smc'] and 'arm,psci-1.0' in psci.strings('compatible')
  assert call(ADB,'reboot','bootloader').returncode==0
  ready=False
  for _ in range(40):
   result=call(FB,'getvar','unlocked',timeout=3)
   if result and b'unlocked: yes' in result.stderr:ready=True;break
   time.sleep(1)
  assert ready
  windows=subprocess.check_output(['wslpath','-w',str(out/'boot-psci-query.img')],text=True).strip()
  result=call(FB,'boot',windows,timeout=60);report['fastboot_boot_accepted']=bool(result and result.returncode==0);assert report['fastboot_boot_accepted']
  print('query probe accepted; waiting for original Android',flush=True)
  ready=False
  for _ in range(100):
   result=call(ADB,'get-state',timeout=2)
   if result and result.returncode==0 and result.stdout.strip()==b'device':
    result=call(ADB,'shell','getprop sys.boot_completed')
    if result and result.stdout.strip()==b'1':ready=True;break
   time.sleep(1)
  report['android_boot_completed']=ready;assert ready
  result=root('id');report['root_verified']=bool(result and result.returncode==0 and b'uid=0' in result.stdout)
  result=root('sha256sum /dev/block/bootdevice/by-name/boot');report['boot_partition_unchanged']=bool(result and result.stdout.decode().split()[0]==report['source_boot_sha256'])
  result=root('cat /sys/firmware/fdt',file='after.dtb');assert result and result.returncode==0
  tree=read_fdt(result.stdout);chosen=next(n for n in tree.children if n.name=='chosen');assert chosen.strings('raphael,entry-probe-id')==[identifier]
  raw=chosen.properties['raphael,psci-query'];assert len(raw)==48
  version,conduit,psci_version,reset_feature,el,reset_called=struct.unpack('>6Q',raw)
  report['observation']=dict(schema=version,conduit=conduit,psci_version=psci_version,system_reset_feature=reset_feature,current_el=el,reset_called=reset_called,fdt_sha256=sha(result.stdout))
  assert version==1 and conduit==1 and 0<psci_version>>16<0x8000 and reset_feature==0 and el==4 and reset_called==0
  report['passed']=report['root_verified'] and report['boot_partition_unchanged']
 except BaseException as error:
  import traceback
  report['failure']=type(error).__name__+': '+str(error);(out/'exception.txt').write_text(traceback.format_exc())
 finally:save();print(out);print(json.dumps({k:report.get(k) for k in ['passed','failure','observation','android_boot_completed','boot_partition_unchanged']},indent=2))
 if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
