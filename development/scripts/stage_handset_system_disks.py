#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Stage original OS disks only in a new private, unencrypted project directory."""
import argparse, datetime as dt, hashlib, json, shlex, subprocess
from pathlib import Path
from entry_probe import ROOT
ADB='/mnt/d/Android/platform-tools/adb.exe'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--disks',type=Path,required=True);a=p.parse_args()
 source=json.loads(a.disks.read_text());assert source['passed']
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 out=ROOT/'evidence/private/handset-system-disks'/stamp;out.mkdir(parents=True,mode=0o700)
 directory='/data/unixnu-raphael-system-'+stamp
 report=dict(passed=False,stage_directory=directory,source_report=str(a.disks.resolve().relative_to(ROOT)),created_only_new_private_stage=True,disks=[],partition_table_modified=False,original_files_overwritten=False)
 def save(): (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 def root(command,timeout=30):
  v=subprocess.run([ADB,'-s',a.serial,'exec-out','su -c '+shlex.quote(command)],capture_output=True,timeout=timeout)
  if v.returncode: raise RuntimeError(v.stderr.decode(errors='replace'))
  return v.stdout
 def upload(src,target,log_path):
  # Windows adb exec-in can stall on a large WSL stdin stream. Use the native
  # file-transfer protocol, then create the private plaintext target locally.
  temporary='/data/local/tmp/unixnu-stage-'+stamp+'-'+Path(target).name
  windows=subprocess.check_output(['wslpath','-w',str(src)],text=True).strip()
  with log_path.open('wb') as log:
   subprocess.run([ADB,'-s',a.serial,'push',windows,temporary],stdout=log,stderr=log,check=True,timeout=1800)
  try:root('umask 077; set -C; cat '+shlex.quote(temporary)+' > '+shlex.quote(target),120)
  finally:root('rm -f '+shlex.quote(temporary))
 print(out,flush=True);save()
 try:
  assert b'uid=0' in root('id');assert root('getprop sys.boot_completed').strip()==b'1'
  assert b'raphael,' not in root('ls /sys/firmware/devicetree/base/chosen/')
  root('umask 077; mkdir '+shlex.quote(directory))
  inspector=directory+'/fiemap'
  upload(ROOT/'artifacts/android-fiemap/inspector',inspector,out/'inspector-upload.log')
  root('chmod 700 '+inspector)
  for disk in source['disks']:
   src=ROOT/disk['path'];assert src.stat().st_size==disk['bytes']
   assert disk['role'] in ['OS','SystemOS','Payload'] and src.resolve().is_relative_to(ROOT)
   assert src.is_file()
   target=directory+'/'+disk['role']+'.raw'
   item=dict(role=disk['role'],source=disk['path'],source_bytes=disk['bytes'],target=target,apfs_containers=disk['apfs_containers'],complete=False)
   report['disks'].append(item);save();print('Uploading '+disk['role']+' '+str(disk['bytes'])+' bytes',flush=True)
   upload(src,target,out/(disk['role']+'-upload.log'))
   root('sync; chmod 400 '+target+'; chattr +i '+target,120)
   assert int(root('stat -c %s '+target))==disk['bytes']
   mapping=json.loads(root(inspector+' '+target));assert mapping['policy_rc']==-61 and mapping['fiemap_rc']==mapping['flags_rc']==0
   assert mapping['inode_flags']&0x10 and not mapping['inode_flags']&0x800
   assert 0<mapping['count']<=128
   h=digest(src);remote=root('sha256sum '+target,240).decode().split()[0];assert h==remote
   assert mapping==json.loads(root(inspector+' '+target))
   item.update(complete=True,sha256=h,fiemap=mapping,file_encryption_policy_absent=True,immutable=True,extent_stable_across_collection=True);save()
   print(disk['role']+' verified; extents='+str(mapping['count']),flush=True)
  root('rm '+inspector)
  report['passed']=True
 except Exception as e:report['failure']=repr(e);raise
 finally:save()
 print(json.dumps(dict(passed=True,report=str(out/'report.json')),indent=2),flush=True)
if __name__=='__main__':main()
