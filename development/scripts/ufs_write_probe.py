#!/usr/bin/env python3
"""Allocate and verify one owned plaintext UFS diagnostic block; never repartition."""
import argparse,datetime as dt,json,shlex,struct,subprocess,uuid
from pathlib import Path
from entry_probe import ROOT,sha
MAGIC=0x3157525346485052
HEADER=struct.Struct('<8Q')
ADB='/mnt/d/Android/platform-tools/adb.exe'
def inspect_policy(raw,lba=None):
 assert len(raw)==8256
 magic,version,lun,first,size,target,count,block=HEADER.unpack_from(raw)
 assert magic==MAGIC and version==1 and count==1 and block==4096
 assert 0<first<lun and 0<size<=lun-first and first<=target<first+size and target<=0xffffffff
 assert lba is None or target==lba
 assert raw[64:4160]!=raw[4160:]
 return dict(lun_blocks=lun,partition_first=first,partition_blocks=size,lba=target,blocks=1,logical_bytes=block)
def validate_manifest(path,lba=None):
 path=path.resolve();assert path.is_relative_to(ROOT/'evidence/private/ufs-write')
 m=json.loads((path.parent/'report.json').read_text());raw=path.read_bytes();policy=inspect_policy(raw,lba)
 assert m['passed'] and m['created_only_new_private_stage'] and m['file_encryption_policy_absent'] and m['immutable']
 assert m['policy']==str(path.relative_to(ROOT)) and m['policy_sha256']==sha(raw) and policy==m['write_window']
 assert m['source_file'].startswith('/data/unixnu-raphael-ufs-write-') and m['source_file'].endswith('/probe.bin')
 assert m['fiemap']['count']==1 and m['fiemap']['extents'][0]['length']==12288
 assert raw[64:4160]==(path.parent/'before.bin').read_bytes()[4096:8192]
 assert raw[4160:]==(path.parent/'replacement.bin').read_bytes()
 assert policy['lba']==m['partition_start_512_sectors']//8+m['fiemap']['extents'][0]['physical']//4096+1
 return dict(report=str((path.parent/'report.json').relative_to(ROOT)),policy=str(path.relative_to(ROOT)),policy_sha256=sha(raw),source_file=m['source_file'],write_window=policy)
def check_live(metadata,root,serial,after=False):
 m=json.loads((ROOT/metadata['report']).read_text());directory=ROOT/metadata['report'];out=directory.parent
 validate_manifest(ROOT/metadata['policy'])
 inspector='/data/local/tmp/raphael-ufs-write-preflight-'+uuid.uuid4().hex
 native=ROOT/'artifacts/android-fiemap/inspector';win=subprocess.check_output(['wslpath','-w',str(native)],text=True).strip()
 subprocess.run([ADB,'-s',serial,'push',win,inspector],check=True,capture_output=True,timeout=20)
 def run(command):
  r=root(command);assert r and r.returncode==0,command
  return r.stdout
 try:
  run('chmod 700 '+shlex.quote(inspector));mapping=json.loads(run(inspector+' '+shlex.quote(m['source_file'])))
  assert mapping==m['fiemap'],'Diagnostic allocation changed'
  assert run('readlink -f /dev/block/bootdevice/by-name/userdata').strip()==b'/dev/block/sda31'
  assert tuple(map(int,run('cat /sys/class/block/sda31/start; cat /sys/class/block/sda31/size').split()))==(m['partition_start_512_sectors'],m['partition_size_512_sectors'])
  before=(out/'before.bin').read_bytes();expected=before[:4096]+(out/'replacement.bin').read_bytes()+before[8192:] if after else before
  content=run('cat '+shlex.quote(m['source_file']));assert content==expected,'Diagnostic file preimage/readback or guard mismatch'
  first=m['write_window']['lba']-1
  raw=run('dd if=/dev/block/sda bs=4096 skip='+str(first)+' count=3 2>/dev/null')
  assert raw==expected,'Physical media readback or guard mismatch'
  return dict(verified=True,allocated_bytes=12288,written_bytes=4096 if after else 0,guard_blocks_unchanged=True,file_matches_raw_lun=True,phase='after_reboot' if after else 'preflight')
 finally:run('rm '+shlex.quote(inspector))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--serial',required=True);p.add_argument('--resume-stage',type=Path,help='Read and finish an already allocated private stage after host collection failure');a=p.parse_args()
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') if not a.resume_stage else a.resume_stage.name;out=ROOT/'evidence/private/ufs-write'/stamp
 if a.resume_stage:assert out.resolve()==a.resume_stage.resolve() and out.is_dir()
 else:out.mkdir(parents=True,mode=0o700)
 print(out,flush=True)
 stage='/data/unixnu-raphael-ufs-write-'+stamp;target=stage+'/probe.bin';commands=[]
 def root(command):
  r=subprocess.run([ADB,'-s',a.serial,'exec-out','su -c '+shlex.quote(command)],capture_output=True,timeout=30)
  commands.append(dict(command=command,returncode=r.returncode,stdout_bytes=len(r.stdout),stderr=r.stderr.decode(errors='replace')));(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,r.stderr
  return r.stdout
 assert b'uid=0' in root('id') and root('getprop sys.boot_completed').strip()==b'1'
 assert b'raphael,' not in root('ls /sys/firmware/devicetree/base/chosen/')
 if not a.resume_stage:
  root('umask 077; mkdir '+shlex.quote(stage));tag=uuid.uuid4().bytes
  before=bytes((i*17+0x35)&255 for i in range(12288));replacement=b'RAPHAEL-UFS-WRITE-PROBE-v1'+tag
  replacement=(replacement+bytes((i*29+0x71)&255 for i in range(4096)))[:4096]
  (out/'before.bin').write_bytes(before);(out/'replacement.bin').write_bytes(replacement)
  subprocess.run([ADB,'-s',a.serial,'exec-in','su -c '+shlex.quote('umask 077; set -C; cat > '+target)],input=before,capture_output=True,check=True,timeout=20)
 else:
  before=(out/'before.bin').read_bytes();replacement=(out/'replacement.bin').read_bytes();assert len(before)==12288 and len(replacement)==4096
 inspector=stage+'/fiemap'
 if not a.resume_stage:
  with (ROOT/'artifacts/android-fiemap/inspector').open('rb') as stream:
   subprocess.run([ADB,'-s',a.serial,'exec-in','su -c '+shlex.quote('set -C; cat > '+inspector)],stdin=stream,check=True,capture_output=True,timeout=20)
 root('chmod 700 '+inspector+'; sync; chmod 400 '+target+'; chattr +i '+target)
 f=json.loads(root(inspector+' '+target));assert f['policy_rc']==-61 and f['fiemap_rc']==f['flags_rc']==0 and f['inode_flags']&0x10 and not f['inode_flags']&0x800 and f['count']==1
 e=f['extents'][0];assert e['logical']==0 and e['length']==12288 and e['physical']%4096==0 and e['flags']==1
 assert root('readlink -f /dev/block/bootdevice/by-name/userdata').strip()==b'/dev/block/sda31'
 start,size=map(int,root('cat /sys/class/block/sda31/start; cat /sys/class/block/sda31/size').split());assert start%8==size%8==0
 geo=root('readlink /sys/class/block/sda/device; cat /sys/class/block/sda/size; cat /sys/class/block/sda/queue/logical_block_size');(out/'lun0-geometry.txt').write_bytes(geo)
 lines=geo.decode().splitlines();assert lines[0].endswith('/0:0:0:0');sectors,block=map(int,lines[-2:]);assert block==4096
 lba=start//8+e['physical']//4096+1;raw=HEADER.pack(MAGIC,1,sectors//8,start//8,size//8,lba,1,4096)+before[4096:8192]+replacement
 policy=out/'write-policy.bin';policy.write_bytes(raw);window=inspect_policy(raw,lba)
 assert root('cat '+target)==before
 assert root('dd if=/dev/block/sda bs=4096 skip='+str(lba-1)+' count=3 2>/dev/null')==before
 assert json.loads(root(inspector+' '+target))==f;root('rm '+inspector)
 reference=ROOT/'evidence/private/ufs-readonly'/(stamp+'-write-probe');reference.mkdir(parents=True,mode=0o700)
 (reference/'lun0-known-block.bin').write_bytes(replacement);(reference/'lun0-geometry.txt').write_bytes(geo)
 source=dict(passed=True,source_file=target,file_encryption_policy_absent=True,extent_stable_across_collection=True,lba=lba,bytes=4096,sha256=sha(replacement),preimage_sha256=sha(before[4096:8192]),purpose='expected diagnostic write readback',write_policy=str(policy.relative_to(ROOT)))
 (reference/'read-source.json').write_text(json.dumps(source,indent=2)+'\n')
 m=dict(passed=True,created_only_new_private_stage=True,partition_table_modified=False,original_files_overwritten=False,source_file=target,fiemap=f,immutable=True,file_encryption_policy_absent=True,partition_start_512_sectors=start,partition_size_512_sectors=size,policy=str(policy.relative_to(ROOT)),policy_sha256=sha(raw),write_window=window,reference=str((reference/'lun0-known-block.bin').relative_to(ROOT)),native_write_verified=False,persistent_data_verified=False)
 (out/'report.json').write_text(json.dumps(m,indent=2)+'\n');validate_manifest(policy,lba);print(json.dumps(m,indent=2))
if __name__=='__main__':main()
