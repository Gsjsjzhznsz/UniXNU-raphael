#!/usr/bin/env python3
"""Re-read frozen raw images, FDT, wires, logs and source Git blobs."""
import argparse,datetime as dt,json,lzma,struct,subprocess,tempfile,zlib
from pathlib import Path
from entry_probe import ROOT,sha
from inspect_device import read_fdt
from private_android_image import read_boot
from inspect_diagnostic_fd import inspect_fd

def load(path):return json.loads(path.read_text())
def chosen(blob):
 t=read_fdt(blob);return next(n for n in t.walk() if n.name=='chosen' and n.parent is t)
def main():
 p=argparse.ArgumentParser();p.add_argument('--revision',required=True);a=p.parse_args();rev=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.revision],text=True).strip()
 parent=ROOT/'artifacts/android-return-verification';parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 cases=[];bound=set()
 for stamp in ['20261028T204929Z','20261028T205204Z']:
  run=ROOT/'evidence/private/android-return-run'/stamp;rr=load(run/'report.json');assert rr['passed'] and rr['experiment_passed'] and rr['unassisted_android_return'] and not rr.get('auto_recovered_from_bootloader') and not (run/'bootloader-recovery.json').exists()
  build=ROOT/rr['build'];br=load(build/'report.json');assert sha((build/'report.json').read_bytes())==rr['build_report_sha256'] and sha((build/'boot-android-return.img').read_bytes())==br['image_sha256']==rr['image_sha256']
  for item in br['source_inputs']+br['upstream_inputs']+br['return_stub']['source_inputs']:
   path=item['path'];snapshot=build/'source-snapshot'/path
   if not snapshot.exists():snapshot=build/'snapshot'/path
   raw=snapshot.read_bytes();assert sha(raw)==item['sha256']
   if path.startswith('sources/'):
    # Fixed upstream trees are separate pinned repositories.
    if path.startswith('sources/mu_basecore/'):
     repo=ROOT/'sources/mu_basecore';pin='cfb93724a06ff86ff5ba971413368a7809ee42a5'
    elif path.startswith('sources/UniXNU/'):
     repo=ROOT/'sources/UniXNU';pin='40d21cc65171c3a24faa130a2a8e899f85790485'
    else:raise AssertionError(path)
    original=subprocess.check_output(['git','-C',str(repo),'show',pin+':'+str((ROOT/path).relative_to(repo))])
   else:original=subprocess.check_output(['git','-C',str(ROOT),'show',rev+':'+path])
   assert raw==original,path;bound.add(path)
  qp=ROOT/br['qemu_evidence'];q=load(qp);assert sha(qp.read_bytes())==br['qemu_evidence_sha256'] and q['passed'] and q['stage']==rr['stage'] and q['return_wire'][0:2]==[1,3]
  log=(qp.parent/'serial.log').read_bytes();assert b'ANDROID_RETURN_QEMU_OK' in log and b'FAIL ' not in log
  image=(build/'diagnostic.Image').read_bytes();layout=br['layout'];fd=image[layout['FdBase']-layout['ImageBase']:layout['FdBase']-layout['ImageBase']+layout['FdSize']];assert inspect_fd(fd,layout['FdBase'])['passed'] and sha(fd)==br['firmware_sha256']
  rd=(build/'expanded-ramdisk.bin').read_bytes();cap=br['capsule'];words=cap['policy_words'];kernel=lzma.decompress(rd[(cap['ramdisk_bytes']+7)&~7:],format=lzma.FORMAT_ALONE);assert len(kernel)==cap['kernel_bytes'] and sha(kernel)==cap['kernel_sha256'] and zlib.crc32(kernel)==words[9]
  assert sha(rd)==cap['expanded_ramdisk_sha256'] and sha(rd[:cap['ramdisk_bytes']])==cap['ramdisk_sha256']
  c=chosen((run/'after.dtb').read_bytes());assert c.strings('raphael,sec-dxe-id')==[br['identifier']]
  wire=c.properties['raphael,android-return'];assert wire==(run/'android-return-wire.bin').read_bytes();w=struct.unpack('>10Q',wire);d=struct.unpack('>48Q',c.properties['raphael,sec-dxe'])
  assert list(w)==rr['return_words'] and list(d)==rr['sec_words'] and w[0:2]==(1,3) and w[2]==w[7]==words[8] and w[3]==w[4]==words[9] and w[8]==len(kernel) and w[9]==1
  assert d[27:29]==(rr['stage'],0) and d[6]==4 and d[30]&0x1005==0x1005 and d[31]>=layout['ImageBase']+cap['declared_image_bytes'] and d[23]>=layout['ImageBase']+cap['declared_image_bytes']
  assert w[5:7]==(br['kernel_window']['base']+br['kernel_window']['bytes']-0x40000,br['kernel_window']['base']+br['kernel_window']['bytes'])
  assert int.from_bytes(c.properties['linux,initrd-end'],'big')-int.from_bytes(c.properties['linux,initrd-start'],'big')==cap['ramdisk_bytes']
  cleanup=chosen((run/'cleanup.dtb').read_bytes());assert not any(k.startswith('raphael,') for k in cleanup.properties)
  commands=load(run/'commands.json');boots=[x for x in commands if 'fastboot.exe' in x['command'][0] and 'boot' in x['command']];assert len(boots)==1 and boots[0]['returncode']==0
  assert not any(any(word in ['flash','erase','format'] for word in x['command']) for x in commands)
  hashes=[x for x in commands if any('sha256sum /dev/block/bootdevice/by-name/boot' in arg for arg in x['command'])];assert len(hashes)>=3 and all(x['returncode']==0 and x['stdout'].split()[0]==br['source_sha256'] for x in hashes)
  assert (run/'before-boot-id.txt').read_bytes()!=(run/'after-boot-id.txt').read_bytes()
  if rr['stage']==6:
   from kernel_window import check_log
   assert d[38:40]==(1,1) and d[44:46]==(0,1) and check_log((run/'sec-dxe.log').read_bytes(),br['kernel_window'])['passed']
  cases.append(dict(stage=rr['stage'],passed=True,private_run=str(run.relative_to(ROOT)),run_report_sha256=sha((run/'report.json').read_bytes()),build=str(build.relative_to(ROOT)),build_report_sha256=sha((build/'report.json').read_bytes()),image_sha256=br['image_sha256'],firmware_sha256=br['firmware_sha256'],fdt_sha256=sha((run/'after.dtb').read_bytes()),wire_sha256=sha(wire),qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),return_wire=list(w)))
 failed=ROOT/'evidence/private/android-return-run/20261028T203621Z';f=load(failed/'report.json');assert not f['passed'] and not f['nonce_matched'] and not f['return_record_found'] and (failed/'bootloader-recovery.json').exists()
 host=ROOT/'artifacts/android-return-host/20261028T205246.825875Z-wtev4e1o';assert load(host/'report.json')['passed'] and b'ANDROID_RETURN_HOST_OK 4107 checks' in (host/'host-test.log').read_bytes()
 report=dict(passed=True,implementation_revision=rev,cases=cases,git_bound_input_count=len(bound),source_paths=sorted(bound),host_report=str((host/'report.json').relative_to(ROOT)),host_report_sha256=sha((host/'report.json').read_bytes()),failure_retained=dict(private_run=str(failed.relative_to(ROOT)),report_sha256=sha((failed/'report.json').read_bytes()),direct_android_return_verified=False,bootloader_reboot_was_required=True),xnu_handset_executed=False,scope='Small 3MiB FV / 12MiB arena; real high-stub Android restoration, not native 20MiB FAT handset qualification',verifier_sha256=sha(Path(__file__).read_bytes()))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,git_bound_input_count=len(bound),stages=[x['stage'] for x in cases]),indent=2))
if __name__=='__main__':main()
