#!/usr/bin/env python3
"""Temporary standalone reset receiver; distinguish recovery from instruction trace."""
import argparse,datetime as dt,json,shlex,subprocess,time
from pathlib import Path
from entry_probe import ROOT,sha
from inspect_device import read_fdt
ADB='/mnt/d/Android/platform-tools/adb.exe';FB='/mnt/d/Android/platform-tools/fastboot.exe'
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--serial',required=True);a=p.parse_args()
 build=a.build.resolve();assert build.is_relative_to(ROOT/'evidence/private/psci-reset-build')
 description=json.loads((build/'report.json').read_text());image=build/'boot-psci-reset.img'
 assert description['passed'] and not description['qemu_hvc_enabled'] and not description['contains_original_android_kernel'] and sha(image.read_bytes())==description['packed_image_sha256']
 for item in description['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
 for key in ['query','qemu']:assert sha((ROOT/description[key+'_report']).read_bytes())==description[key+'_report_sha256']
 out=ROOT/'evidence/private/psci-reset-run'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(mode=0o700,parents=True,exist_ok=False)
 report=dict(passed=False,private_build=str(build.relative_to(ROOT)),artifact_directory=str(out.relative_to(ROOT)),image_sha256=sha(image.read_bytes()),used_flash_or_erase=False,reset_instruction_trace_verified=False,reset_result_registers_observed=False,limits=['Operational automatic return observed; no direct phone SMC instruction/return trace','Standalone reset receiver only; not XNU or independent UEFI execution'])
 records=[]
 def save():
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 def call(tool,*args,timeout=10,file=None):
  command=[tool,'-s',a.serial,*args];entry=dict(command=command,utc=dt.datetime.now(dt.timezone.utc).isoformat())
  try:result=subprocess.run(command,capture_output=True,timeout=timeout)
  except subprocess.TimeoutExpired:entry['timeout']=True;records.append(entry);save();return None
  entry.update(returncode=result.returncode,stderr=result.stderr.decode(errors='replace'))
  if file:(out/file).write_bytes(result.stdout);entry.update(file=file,sha256=sha(result.stdout))
  else:entry['stdout']=result.stdout.decode(errors='replace')
  records.append(entry);save();return result
 def root(command,**kw):return call(ADB,'exec-out','su -c '+shlex.quote(command),**kw)
 try:
  result=root('id');assert result and result.returncode==0 and b'uid=0' in result.stdout
  result=root('sha256sum /dev/block/bootdevice/by-name/boot');assert result and result.stdout.decode().split()[0]==description['source_boot_sha256']
  result=root('cat /proc/sys/kernel/random/boot_id',file='before-boot-id.txt');assert result and result.returncode==0
  result=root('cat /sys/firmware/fdt',file='before.dtb');assert result and result.returncode==0
  tree=read_fdt(result.stdout);psci=next(n for n in tree.children if n.name=='psci');assert psci.strings('method')==['smc']
  assert call(ADB,'reboot','bootloader').returncode==0
  ready=False
  for _ in range(40):
   result=call(FB,'getvar','unlocked',timeout=3)
   if result and b'unlocked: yes' in result.stderr:ready=True;break
   time.sleep(1)
  assert ready
  windows=subprocess.check_output(['wslpath','-w',str(image)],text=True).strip();start=time.monotonic()
  result=call(FB,'boot',windows,timeout=60);report['fastboot_boot_accepted']=bool(result and result.returncode==0);assert report['fastboot_boot_accepted']
  print('standalone receiver accepted; waiting for automatic Android recovery',flush=True)
  ready=False
  for _ in range(110):
   result=call(ADB,'get-state',timeout=2)
   if result and result.returncode==0 and result.stdout.strip()==b'device':
    result=call(ADB,'shell','getprop sys.boot_completed')
    if result and result.stdout.strip()==b'1':ready=True;break
   time.sleep(1)
  report.update(android_boot_completed=ready,seconds_after_fastboot_boot=round(time.monotonic()-start,3));assert ready
  result=root('id');report['root_verified']=bool(result and b'uid=0' in result.stdout)
  result=root('sha256sum /dev/block/bootdevice/by-name/boot');report['boot_partition_unchanged']=bool(result and result.stdout.decode().split()[0]==description['source_boot_sha256'])
  result=root('cat /proc/sys/kernel/random/boot_id',file='after-boot-id.txt');report['new_android_boot']=bool(result and result.stdout!=(out/'before-boot-id.txt').read_bytes())
  result=root('cat /sys/firmware/fdt',file='after.dtb');assert result and result.returncode==0
  tree=read_fdt(result.stdout);chosen=next(n for n in tree.children if n.name=='chosen');report['temporary_properties_cleared']=not any(k.startswith('raphael,') for k in chosen.properties)
  report['passed']=all(report[k] for k in ['android_boot_completed','root_verified','boot_partition_unchanged','new_android_boot','temporary_properties_cleared'])
 except BaseException as error:
  import traceback
  report['failure']=type(error).__name__+': '+str(error);(out/'exception.txt').write_text(traceback.format_exc())
 finally:save();print(out);print(json.dumps(report,indent=2))
 if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
