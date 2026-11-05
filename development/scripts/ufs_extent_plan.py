#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Freeze immutable system-file extents and a bounded native-sector read plan."""
import argparse,datetime as dt,json,shlex,struct,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
ADB='/mnt/d/Android/platform-tools/adb.exe'
HEADER=struct.Struct('<8Q');EXTENT=struct.Struct('<QQQI4x');REQUEST=struct.Struct('<QQ')
def encode(m,expected):
 b=m['bounds'];maps=m['extents'];requests=m['requests']
 assert len(expected)==4096 and 0<len(maps)<=128 and 0<len(requests)<=8
 data=HEADER.pack(1,len(maps),b['file_bytes'],b['lun_bytes'],b['partition_base'],b['partition_bytes'],len(requests),m['extent_repeats'])
 data+=b''.join(EXTENT.pack(e['logical'],e['physical'],e['bytes'],e['flags']) for e in maps)+bytes((128-len(maps))*32)
 data+=b''.join(REQUEST.pack(q['offset'],q['bytes']) for q in requests)+bytes((8-len(requests))*16)+expected
 assert len(data)==8384;return data
def inspect_policy(data):
 assert len(data)==8384
 version,count,file_bytes,lun,base,part,requests,repeats=HEADER.unpack_from(data)
 assert version==1 and 0<count<=128 and 0<requests<=8 and 0<repeats<=16
 assert file_bytes>0 and file_bytes%512==0 and 0<lun<1<<64 and lun%4096==0
 assert base%4096==part%4096==0 and part>0 and base+part<=lun
 assert file_bytes<(1<<64)-4095
 at=0;seen=[]
 for i in range(count):
  logical,physical,size,flags=EXTENT.unpack_from(data,64+i*32)
  assert data[64+i*32+28:64+(i+1)*32]==bytes(4)
  assert logical==at and size>0 and size%4096==physical%4096==0 and flags==(1 if i+1==count else 0)
  assert base<=physical and physical+size<=base+part and at+size<=(file_bytes+4095)//4096*4096
  assert all(not(physical<end and begin<physical+size) for begin,end in seen)
  seen.append((physical,physical+size));at+=size
 assert at==(file_bytes+4095)//4096*4096
 assert data[64+count*32:4160]==bytes((128-count)*32)
 total=0
 for i in range(requests):
  offset,size=REQUEST.unpack_from(data,4160+i*16)
  assert offset%512==size%512==0 and size>0 and offset+size<=file_bytes and size<=4096-total
  total+=size
 assert total==4096 and data[4160+requests*16:4288]==bytes((8-requests)*16)
 return dict(sha256=sha(data),count=count,requests=requests,repeats=repeats,file_bytes=file_bytes)
def validate_manifest(plan,reference):
 assert plan.resolve().is_relative_to(ROOT/'evidence/private/ufs-readonly')
 m=json.loads((plan.parent/'extent-source.json').read_text());assert m['passed'] and m['immutable'] and m['file_encryption_policy_absent']
 expected=reference.read_bytes();assert len(expected)==4096 and sha(expected)==m['sha256']
 assert encode(m,expected)==plan.read_bytes() and sha(plan.read_bytes())==m['extent_plan_sha256']
 inspect_policy(plan.read_bytes())
 return dict(extent_repeats=m['extent_repeats'],extent_physical_reads=m['extent_physical_reads'],extent_plan_sha256=m['extent_plan_sha256'],extent_source=str((plan.resolve().parent/'extent-source.json').relative_to(ROOT)),source_file=m['source_file'],probe_goal='extent_virtual_disk')
def validate_current(metadata,root):
 m=json.loads((ROOT/metadata['extent_source']).read_text());file=m['source_file']
 assert file.startswith('/data/unixnu-raphael-system-') and file.endswith(('/OS.raw','/SystemOS.raw','/Payload.raw'))
 inspector='/data/local/tmp/raphael-extent-preflight-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 # Binary stdin to the existing root call is unavailable; shell-safe hex encodes a tiny inspector only.
 path=subprocess.check_output(['wslpath','-w',str(ROOT/'artifacts/android-fiemap/inspector')],text=True).strip()
 serial=metadata['serial']
 subprocess.run([ADB,'-s',serial,'push',path,inspector],capture_output=True,check=True,timeout=30)
 def run(s):
  v=root(s);assert v and v.returncode==0;return v.stdout
 try:
  run('chmod 700 '+inspector)
  assert int(run('stat -c %s '+shlex.quote(file)))==m['bounds']['file_bytes']
  mapping=json.loads(run(inspector+' '+shlex.quote(file)));assert mapping==m['fiemap'],'Immutable allocation or flags changed'
  return True
 finally:run('rm '+inspector)
def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--stage-report',type=Path,required=True);p.add_argument('--role',choices=['OS','SystemOS','Payload'],required=True);a=p.parse_args()
 stage=json.loads(a.stage_report.read_text());assert stage['passed']
 disk=next(d for d in stage['disks'] if d['role']==a.role);assert disk['complete'] and disk['immutable']
 out=ROOT/'evidence/private/ufs-readonly'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,mode=0o700);print(out,flush=True)
 commands=[]
 def root(s,timeout=30):
  v=subprocess.run([ADB,'-s',a.serial,'exec-out','su -c '+shlex.quote(s)],capture_output=True,timeout=timeout)
  commands.append(dict(command=s,returncode=v.returncode));(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert v.returncode==0,v.stderr;return v.stdout
 inspector='/data/local/tmp/raphael-extent-'+out.name
 path=subprocess.check_output(['wslpath','-w',str(ROOT/'artifacts/android-fiemap/inspector')],text=True).strip()
 subprocess.run([ADB,'-s',a.serial,'push',path,inspector],capture_output=True,check=True,timeout=30);root('chmod 700 '+inspector)
 try:
  f=json.loads(root(inspector+' '+disk['target']));assert f==disk['fiemap']
  assert f['policy_rc']==-61 and f['fiemap_rc']==f['flags_rc']==0 and f['inode_flags']&0x10 and not f['inode_flags']&0x800
  mounts=root('cat /proc/mounts');assert any(v.split()[0:3]==[b'/dev/block/bootdevice/by-name/userdata',b'/data',b'ext4'] or (len(v.split())>=3 and v.split()[1:3]==[b'/data',b'ext4']) for v in mounts.splitlines())
  assert root('readlink -f /dev/block/bootdevice/by-name/userdata').strip()==b'/dev/block/sda31'
  geo=root('readlink /sys/class/block/sda/device; cat /sys/class/block/sda/size; cat /sys/class/block/sda/queue/logical_block_size');(out/'lun0-geometry.txt').write_bytes(geo)
  lines=geo.decode().splitlines();assert lines[0].endswith('/0:0:0:0');sectors,block=map(int,lines[-2:]);assert block==4096
  start,parts=map(int,root('cat /sys/class/block/sda31/start; cat /sys/class/block/sda31/size').split())
  maps=[dict(logical=e['logical'],physical=start*512+e['physical'],bytes=e['length'],flags=e['flags']) for e in f['extents']]
  at=0
  for i,e in enumerate(maps):
   assert e['logical']==at and e['physical']%4096==e['bytes']%4096==0 and e['bytes']>0 and e['flags']==(1 if i==len(maps)-1 else 0)
   assert start*512<=e['physical'] and e['physical']+e['bytes']<=(start+parts)*512<=sectors*512
   at+=e['bytes']
  assert at==(disk['source_bytes']+4095)//4096*4096
  boundary=maps[1]['logical'] if len(maps)>1 else 4096
  offsets=[(0,512),(512,512),(disk['apfs_containers'][0]['offset'] if disk['apfs_containers'] else 4096,512),((disk['source_bytes']//2)//512*512,512),(disk['source_bytes']-512,512),(disk['source_bytes']-4096,512),(boundary-512,1024)]
  requests=[dict(offset=o,bytes=n) for o,n in offsets];data=b'';physical_reads=0
  with (ROOT/disk['source']).open('rb') as stream:
   for q in requests:
    stream.seek(q['offset']);expected=stream.read(q['bytes']);content=root('dd if='+disk['target']+' bs=512 skip='+str(q['offset']//512)+' count='+str(q['bytes']//512)+' 2>/dev/null');assert content==expected
    remaining=q['bytes'];logical=q['offset'];native=b''
    while remaining:
     e=next(e for e in maps if e['logical']<=logical<e['logical']+e['bytes']);phys=e['physical']+logical-e['logical'];inside=phys%4096;n=min(4096-inside,remaining,e['bytes']-(logical-e['logical']))
     raw=root('dd if=/dev/block/sda bs=4096 skip='+str(phys//4096)+' count=1 2>/dev/null');assert len(raw)==4096
     native+=raw[inside:inside+n];logical+=n;remaining-=n;physical_reads+=1
    assert native==expected;data+=expected
  assert len(data)==4096 and json.loads(root(inspector+' '+disk['target']))==f
  m=dict(passed=True,immutable=True,file_encryption_policy_absent=True,extent_stable_across_collection=True,source_file=disk['target'],stage_report=str(a.stage_report.resolve().relative_to(ROOT)),fiemap=f,extents=maps,requests=requests,bounds=dict(file_bytes=disk['source_bytes'],lun_bytes=sectors*512,partition_base=start*512,partition_bytes=parts*512),extent_repeats=16,extent_physical_reads=physical_reads*16,sha256=sha(data),media_written=False,handset_native_read_verified=False)
  policy=encode(m,data);m['extent_plan_sha256']=sha(policy)
  (out/'extent-policy.bin').write_bytes(policy);(out/'lun0-known-block.bin').write_bytes(data);(out/'extent-source.json').write_text(json.dumps(m,indent=2)+'\n')
  print(json.dumps(dict(passed=True,policy=str(out/'extent-policy.bin'),extents=len(maps),physical_reads=m['extent_physical_reads']),indent=2))
 finally:root('rm '+inspector)
if __name__=='__main__':main()
