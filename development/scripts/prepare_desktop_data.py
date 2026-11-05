#!/usr/bin/env python3
"""Prepare a NEW emulator scratch APFS and original default /var seed.
Requires libfsapfs-python==20260921 in the workspace venv. No device writes.
"""
import argparse,ast,datetime as dt,json,os,stat,struct,subprocess,uuid
from pathlib import Path
import pyfsapfs
from entry_probe import ROOT

class ReadOnlyRange:
 """File-like view of the inspected APFS container; never copies the OS disk."""
 def __init__(self,path,offset,length):
  self.file=path.open('rb');self.start=offset;self.length=length;self.at=0
 def read(self,size=-1):
  if size<0:size=self.length-self.at
  size=min(size,self.length-self.at);self.file.seek(self.start+self.at)
  data=self.file.read(size);self.at+=len(data);return data
 def seek(self,offset,whence=0):
  if whence not in (0,1,2):raise ValueError(whence)
  pos=offset if whence==0 else self.at+offset if whence==1 else self.length+offset
  if not 0<=pos<=self.length:raise ValueError(pos)
  self.at=pos;return pos
 def tell(self):return self.at

def checksum(raw):
 total=weighted=0
 for word, in struct.iter_unpack('<I',raw[8:]):total+=word;weighted+=total
 lo=0xffffffff-(total+weighted)%0xffffffff
 hi=0xffffffff-(total+lo)%0xffffffff
 return lo|(hi<<32)

def normalize_new_checkpoint(image):
 # Only the freshly-created regular scratch file is passed here.
 # Layout: apfsprogs 20231203 include/apfs/raw.h; Apple APFS requires
 # map entries to enumerate the contiguous checkpoint data in address order.
 with image.open('r+b') as stream:
  header=stream.read(4096);assert header[32:36]==b'NXSB'
  blocksize=struct.unpack_from('<I',header,36)[0];assert blocksize==4096
  desc_blocks=struct.unpack_from('<I',header,104)[0]
  desc_base,data_base=struct.unpack_from('<2Q',header,112)
  index,length,data_index,data_length=struct.unpack_from('<4I',header,136)
  assert 0<length<=desc_blocks<=65536
  changes=[]
  for i in range(length):
   block=desc_base+(index+i)%desc_blocks;stream.seek(block*blocksize);raw=bytearray(stream.read(blocksize))
   if struct.unpack_from('<I',raw,24)[0]&0xffff!=12:continue
   assert struct.unpack_from('<Q',raw)[0]==checksum(raw)
   count=struct.unpack_from('<I',raw,36)[0];assert 0<count and 40+40*count<=blocksize
   records=[bytes(raw[40+40*j:80+40*j]) for j in range(count)]
   address=lambda r:struct.unpack_from('<Q',r,32)[0]
   ordered=sorted(records,key=address);cursor=data_base+data_index
   for record in ordered:
    assert address(record)==cursor
    size=struct.unpack_from('<I',record,8)[0];assert size and size%blocksize==0
    cursor+=size//blocksize
   assert cursor==data_base+data_index+data_length
   raw[40:40+40*count]=b''.join(ordered);struct.pack_into('<Q',raw,0,checksum(raw))
   stream.seek(block*blocksize);stream.write(raw)
   changes.append(dict(block=block,before=[address(r) for r in records],after=[address(r) for r in ordered]))
  assert len(changes)==1
 return changes

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--size-mib',type=int,choices=[128,256,512,1024],default=128,help='Capacity of this NEW emulator-only scratch file');ap.add_argument('--volume-uuid',type=uuid.UUID,help='Explicit existing kernel Data UUID contract; use only in an isolated emulator');ap.add_argument('--user-skeleton',action='store_true',help='Add empty generic user-management directories from the pinned upstream recipe; no keys or user records');ap.add_argument('--system-disks',type=Path,required=True);a=ap.parse_args()
 assert pyfsapfs.get_version()=='20260921'
 disks=json.loads(a.system_disks.read_text());assert disks['passed']
 disk=next(d for d in disks['disks'] if d['role']=='OS');image=(ROOT/disk['path']).resolve()
 assert image.is_file() and image.is_relative_to(ROOT/'artifacts') and image.stat().st_size==disk['bytes']
 assert len(disk['apfs_containers'])==1
 description=disk['apfs_containers'][0]
 span=ReadOnlyRange(image,description['offset'],description['bytes'])
 container=pyfsapfs.container();container.open_file_object(span);volume=container.get_volume(0)
 assert str(volume.identifier).lower()==description['volumes'][0].lower()
 out=ROOT/'evidence/private/desktop-data'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 out.mkdir(parents=True,exist_ok=False);os.chmod(out,0o700)
 entries=[];payload=bytearray();excluded=['/private/var/staged_system_apps']
 def visit(entry,path):
  item=dict(path=path,uid=entry.owner_identifier,gid=entry.group_identifier,mode=entry.file_mode)
  if stat.S_ISREG(entry.file_mode):
   data=entry.read(entry.size);assert len(data)==entry.size
   item.update(kind='file',offset=len(payload),bytes=len(data));payload.extend(data)
  elif stat.S_ISDIR(entry.file_mode):item['kind']='directory'
  elif stat.S_ISLNK(entry.file_mode):item.update(kind='symlink',target=entry.symbolic_link_target)
  else:raise ValueError('Unsupported original var entry '+path)
  entries.append(item)
  if item['kind']=='directory':
   for child in sorted(entry.sub_file_entries,key=lambda e:e.name):
    assert child.name not in ('.','..') and '/' not in child.name
    name=path+'/'+child.name
    if name not in excluded:visit(child,name)
 visit(volume.get_file_entry_by_path('/private/var'),'/private/var')
 skeleton=None
 if a.user_skeleton:
  source=ROOT/'sources/UniXNU/scripts/prepare-offline-data.py'
  syntax=ast.parse(source.read_text())
  nodes=[n.value for n in syntax.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRECTORIES' for t in n.targets)]
  assert len(nodes)==1;directories=ast.literal_eval(nodes[0]);existing={e['path']:e for e in entries};created=[]
  mobile=existing['/private/var/mobile'];assert mobile['kind']=='directory'
  for name in directories:
   parts=Path(name).parts;assert parts and all(x not in ('/','..','.') for x in parts)
   for n in range(1,len(parts)+1):
    path='/private/var/'+'/'.join(parts[:n])
    if path in existing:assert existing[path]['kind']=='directory';continue
    is_mobile=parts[0]=='mobile';owner=mobile if is_mobile else existing['/private/var']
    item=dict(path=path,uid=owner['uid'],gid=owner['gid'],mode=stat.S_IFDIR|(0o700 if parts[0]=='keybags' else 0o755),kind='directory',metadata_source='Local empty-directory creation policy; not an original APFS inode')
    entries.append(item);existing[path]=item;created.append(path)
  entries.sort(key=lambda e:e['path'])
  skeleton=dict(recipe=str(source.relative_to(ROOT)),revision=subprocess.check_output(['git','-C',str(ROOT/'sources/UniXNU'),'rev-parse','HEAD'],text=True).strip(),created=created,added_keys_or_user_records=False,permission_policy='New keybags directories root 0700; other new directories 0755; original mobile owner/group for mobile subtree, root var owner/group otherwise')
 (out/'seed.bin').write_bytes(payload)
 (out/'seed.json').write_text(json.dumps(dict(entries=entries,source_disk=disk['path'],source_volume=description['volumes'][0],metadata_source='Original entries: original APFS inode via libfsapfs 20260921; added skeleton entries: explicitly recorded local policy',excluded=excluded,user_skeleton=skeleton),indent=2)+'\n')
 scratch=out/'data.raw';size=a.size_mib*1048576
 with scratch.open('xb') as stream:stream.truncate(size)
 cu,vu=str(uuid.uuid4()),str(a.volume_uuid or uuid.uuid4());commands=[]
 for args in [['mkapfs','-s','-L','RaphaelScratchData','-U',cu,'-u',vu,str(scratch)],['apfsck',str(scratch)],['fsapfsinfo',str(scratch)]]:
  commands.append(args);r=subprocess.run(args,capture_output=True,text=True)
  (out/(args[0]+'.log')).write_text(r.stdout+r.stderr)
  assert r.returncode==0,(args[0],r.returncode,r.stderr)
  if args[0]=='mkapfs':checkpoint_normalization=normalize_new_checkpoint(scratch)
 formatted=pyfsapfs.container();formatted.open(str(scratch))
 assert str(formatted.identifier).lower()==cu and str(formatted.get_volume(0).identifier).lower()==vu
 counts={kind:sum(e['kind']==kind for e in entries) for kind in ['file','directory','symlink']}
 report=dict(passed=True,artifact_directory=str(out.relative_to(ROOT)),image=str(scratch.relative_to(ROOT)),bytes=size,capacity_policy='Explicit host-owned emulator scratch capacity, not handset storage',explicit_kernel_volume_contract=bool(a.volume_uuid),container_uuid=cu,volume_uuid=vu,seed=str((out/'seed.json').relative_to(ROOT)),seed_bytes=len(payload),entries=len(entries),entry_counts=counts,user_skeleton=skeleton,commands=commands,host_format_checked=True,checkpoint_normalization=checkpoint_normalization,apple_apfs_mount_verified=False,handset_executed=False,limits=['New emulator scratch only; experimental apfsprogs formatter','Original default var only; private seed excluded from public source','Mount, writes and desktop not implied by host checks'])
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
