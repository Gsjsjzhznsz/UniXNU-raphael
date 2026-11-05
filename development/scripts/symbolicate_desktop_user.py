#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Read original dyld-cache symbols for ABI-qualified QEMU process snapshots.
No source binary is rewritten. A caller-supplied slide is explicitly unverified.
Header fields follow pinned Apple dyld a571176e8e00c47e95b95e3156820ebec0cbd5e6.
"""
import argparse,bisect,json,struct,functools
from pathlib import Path

symbol_streams={}
@functools.lru_cache(maxsize=32768)
def read(path,offset,size):
 if path.suffix=='.symbols':
  stream=symbol_streams.setdefault(path,None)
  if stream is None:stream=path.open('rb');symbol_streams[path]=stream
  stream.seek(offset);data=stream.read(size)
 else:
  with path.open('rb') as stream:
   stream.seek(offset);data=stream.read(size)
 if len(data)!=size:raise ValueError('Short original cache read')
 return data

class OriginalCache:
 def __init__(self,directory):
  self.directory=directory;self.main=(directory/'dyld_shared_cache_arm64').read_bytes();main=self.main[:512];assert len(self.main)<=16777216
  assert main[:16].rstrip(b'\0')==b'dyld_v1   arm64'
  self.region,self.region_size,self.maximum=struct.unpack_from('<3Q',main,224)
  off,count=struct.unpack_from('<2Q',main,136);assert 0<count<10000
  table=read(directory/'dyld_shared_cache_arm64',off,count*32);self.images=[]
  for i in range(count):
   _,va,size,path=struct.unpack_from('<16sQ2I',table,i*32)
   name=self.main[path:self.main.index(0,path)].decode()
   self.images.append((va,size,name))
  self.symbols=directory/'dyld_shared_cache_arm64.symbols'
  header=read(self.symbols,0,512);assert header[88:104]==main[400:416]
  self.local=struct.unpack_from('<Q',header,72)[0]
  no,nc,so,ss,eo,ec=struct.unpack('<6I',read(self.symbols,self.local,24))
  self.nlists,self.ncount,self.strings,self.ssize=self.local+no,nc,self.local+so,ss
  table=read(self.symbols,self.local+eo,ec*16)
  self.entries={struct.unpack_from('<Q',table,i*16)[0]:struct.unpack_from('<2I',table,i*16+8) for i in range(ec)}
  self.loaded={};self.mappings=[]
  for path in directory.glob('dyld_shared_cache_arm64*'):
   if path.suffix=='.symbols':continue
   header=read(path,0,4096);off,count=struct.unpack_from('<2I',header,16)
   assert count<1000
   for i in range(count):
    va,size,offset,_,_=struct.unpack_from('<3Q2I',header,off+i*32) if off+(i+1)*32<=len(header) else struct.unpack('<3Q2I',read(path,off+i*32,32))
    self.mappings.append((va,size,path,offset))
 def virtual(self,va,size):
  for start,length,path,offset in self.mappings:
   if start<=va and va+size<=start+length:return read(path,offset+va-start,size)
  raise ValueError('Address outside original cache mappings: '+hex(va))
 def pointer(self,va):
  """Decode only the selected cache's actual v2 chained data pointer."""
  raw=struct.unpack('<Q',self.virtual(va,8))[0]
  for start,length,path,offset in self.mappings:
   if not start<=va<start+length:continue
   header=read(path,0,512);off,count=struct.unpack_from('<2I',header,312);assert 0<count<1000
   for index in range(count):
    # dyld_cache_mapping_and_slide_info is six Q words and two I words.
    mapping=struct.unpack('<6Q2I',read(path,off+index*56,56))
    if not mapping[0]<=va<mapping[0]+mapping[1]:continue
    if not mapping[4]:return raw
    info=read(path,mapping[3],40);assert struct.unpack_from('<I',info)[0]==2
    mask,base=struct.unpack_from('<2Q',info,24)
    return (raw&(~mask&((1<<64)-1)))+base
  raise ValueError('Pointer has no qualified mapping')
 def cfstring(self,va):
  raw=self.virtual(va,32);length=struct.unpack_from('<Q',raw,24)[0]
  assert 0<length<=4096
  return self.virtual(self.pointer(va+16),length).decode('ascii')
 def exports(self,base):
  header=self.virtual(base,32);count,size=struct.unpack_from('<2I',header,16);cmds=self.virtual(base+32,size);at=0;link=trie=None
  for _ in range(count):
   cmd,length=struct.unpack_from('<2I',cmds,at);assert length>=8 and at+length<=size
   if cmd==0x19:
    name,va,_,offset,_=struct.unpack_from('<16s4Q',cmds,at+8)
    if name.rstrip(b'\0')==b'__LINKEDIT':link=(va,offset)
   if cmd==0x80000033:trie=struct.unpack_from('<2I',cmds,at+8)
   at+=length
  if not link or not trie:return []
  data=self.virtual(link[0]+trie[0]-link[1],trie[1]);rows=[]
  def uleb(at):
   value=shift=0
   while shift<64:
    byte=data[at];at+=1;value|=(byte&127)<<shift
    if byte<128:return value,at
    shift+=7
   raise ValueError('Invalid original export trie')
  def visit(node,prefix,seen):
   assert node not in seen;seen=seen|{node};size,at=uleb(node);end=at+size
   if size:
    flags,pos=uleb(at)
    if flags==0:
     value,_=uleb(pos);rows.append((base+value,prefix,'export'))
   cursor=end+1
   for _ in range(data[end]):
    stop=data.index(0,cursor);edge=data[cursor:stop].decode();child,cursor=uleb(stop+1);visit(child,prefix+edge,seen)
  visit(0,'',set());return rows
 def locate(self,pc,slide):
  va=pc-slide;row=dict(pc=hex(pc),unslid_va=hex(va),image=None)
  image=next((im for im in self.images if im[0]<=va<im[0]+im[1]),None)
  if not image:return row
  base,size,name=image;row['image']=name
  entry=self.entries.get(base-self.region)
  if base not in self.loaded:
   start,count=entry or (0,0);assert start+count<=self.ncount
   raw=read(self.symbols,self.nlists+start*16,count*16);items=[]
   for i in range(count):
    string,kind,section,_,value=struct.unpack_from('<IBBHQ',raw,i*16)
    if not kind&0xe0 and kind&0xe==0xe and section and base<=value<base+size:
     assert string<self.ssize;items.append((value,string,'local'))
   self.loaded[base]=sorted(items+self.exports(base),key=lambda x:x[0])
  items=self.loaded[base];at=bisect.bisect_right([x[0] for x in items],va)-1
  if at>=0:
   value,string,kind=items[at];name=string if kind=='export' else read(self.symbols,self.strings+string,min(2048,self.ssize-string)).split(b'\0')[0].decode(errors='replace')
   row.update(symbol=name,symbol_kind=kind,offset=va-value)
  return row

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--observation',type=Path,required=True);parser.add_argument('--pid',type=int,required=True);parser.add_argument('--slide',type=lambda x:int(x,0));parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
 cache=OriginalCache(a.cache);d=json.loads(a.observation.read_text());samples=d.get('progress_samples',[])+[dict(process_snapshot=d.get('process_snapshot',{}))];rows=[]
 for index,sample in enumerate(samples):
  for proc in sample.get('process_snapshot',{}).get('processes',[]):
   if proc['pid']!=a.pid:continue
   actual=proc.get('shared_region',{}).get('slide');slide=actual if actual is not None else a.slide
   if slide is None:continue
   assert 0<=slide<=cache.maximum and slide%4096==0
   for thread in proc.get('threads',[]):
    state=thread.get('user_state',{});pcs=[(key,state.get(key,0)) for key in ['pc','lr']]
    pcs += [('frame_'+str(n),frame['return_address']-4) for n,frame in enumerate(thread.get('user_frames',[])) if frame['return_address']]
    instruction_match=None
    if thread.get('user_instruction_window'):
     try:instruction_match=cache.virtual(state['pc']-8-slide,32).hex()==thread['user_instruction_window']
     except ValueError:pass
    rows.append(dict(sample=index,pid=proc['pid'],comm=proc['comm'],thread=thread['address'],thread_state=thread['state'],original_cache_instruction_match=instruction_match,user_mapping=thread.get('user_mapping'),user_stack_error=thread.get('user_stack_error'),cache_slide=hex(slide),slide_source='same-build task.shared_region.sr_slide' if actual is not None else 'caller supplied; not runtime verified',frames=[dict(register=key,**cache.locate(pc,slide)) for key,pc in pcs if pc]))
 assert rows,'No matching process with a runtime or explicitly supplied slide'
 runtime=[]
 slides={row['cache_slide'] for row in rows if row['slide_source'].startswith('same-build')};assert len(slides)<=1
 if slides:
  slide=int(next(iter(slides)),16)
  for event in d.get('runtime_syscalls',[]):
   if event.get('pid')!=a.pid or not event.get('after_target_main'):continue
   pcs=[event['pc']]+[frame['return_address']-4 for frame in event.get('frames',[]) if frame['return_address']]
   runtime.append(dict(syscall=event['syscall_number'],path=event.get('path'),frames=[cache.locate(pc,slide) for pc in pcs]))
 report=dict(source_observation=str(a.observation),cache_header_source='Apple dyld a571176e8e00c47e95b95e3156820ebec0cbd5e6/cache-builder/dyld_cache_format.h',symbols_uuid_matches=True,process_samples=rows,after_main_syscalls=runtime,original_files_modified=False,handset_executed=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
