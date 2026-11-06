#!/usr/bin/env python3
"""Decode sparse active tables and independently check the exact-grant transition."""
import struct,zlib
from entry_probe import sha
FIELDS='version status error transition_base transition_bytes transition_crc_before transition_crc_after transition_ok original_ttbr0 original_ttbr1 observed_transition_ttbr0 clean_base clean_bytes table_pages nonzero_descriptors sparse_bytes sparse_capacity root0_empty relay_unmapped high_data_pages high_probes capture_ok table_crc_xor reserved adt_physical adt_bytes adt_crc_before adt_crc_after adt_crc_restored adt_restored adt_changed_bytes adt_backup_ok'.split()
MASK=0x0000fffffffff000

def transition_image(base,grant,bytes_,relay,relay_bytes=1):
 assert base%4096==grant%4096==bytes_%4096==0 and bytes_ in (256*1048576,512*1048576,704*1048576,896*1048576,1536*1048576)
 assert 0<=grant<grant+bytes_<=1<<38 and grant<=relay<relay+relay_bytes<=grant+bytes_ and 1<=relay_bytes<=2048
 pages=6 if bytes_==1536*1048576 else 4
 spans=((grant+bytes_-1)>>30)-(grant>>30)+1
 words=[0]*(pages*512);partial=1+spans;assert partial+2<=pages
 for i in range(spans):words[((grant>>30)+i)&255]=(base+(1+i)*4096)|3
 for block in range(grant&~0x1fffff,grant+bytes_,0x200000):
  index=(1+(block>>30)-(grant>>30))*512+((block>>21)&511)
  flags=0x0040000000000601|(0 if relay<block+0x200000 and block<relay+relay_bytes else 1<<53)
  if grant<=block and block+0x200000<=grant+bytes_:words[index]=block|flags
  else:
   assert partial<pages;words[index]=(base+partial*4096)|3
   for j in range(512):
    pa=block+j*4096
    if grant<=pa<pa+4096<=grant+bytes_:words[partial*512+j]=pa|(flags|2)
   partial+=1
 return struct.pack('<'+str(len(words))+'Q',*words)

def decode(raw,sparse,transition,adt_snapshot,original_adt,c,mmu):
 if c.get('trust_cache'):
  from native_trust import apply_binding
  original_adt=apply_binding(original_adt,c['trust_cache'])
 if c.get('ramdisk'):
  from native_ramdisk import apply_binding as apply_packed
  original_adt=apply_packed(original_adt,c['ramdisk'])
 assert len(raw)==256;d=dict(zip(FIELDS,struct.unpack('>32Q',raw)));assert d['version']==1 and d['status']==3 and d['error']==d['reserved']==0
 assert all(d[k]==1 for k in ['transition_ok','root0_empty','relay_unmapped','capture_ok'])
 assert d['original_ttbr0']==mmu['ttbr0'] and d['original_ttbr1']==mmu['ttbr1'] and d['observed_transition_ttbr0']==d['transition_base']
 assert d['clean_base']==c['physical_base'] and d['clean_bytes']==c['window_bytes'] and d['transition_bytes']==len(transition)==(24576 if c['window_bytes']==1536*1048576 else 16384)
 assert d['transition_crc_before']==d['transition_crc_after']==zlib.crc32(transition)
 assert transition==transition_image(d['transition_base'],c['physical_base'],c['window_bytes'],mmu['relay_pa'],((c.get('early') or {}).get('compiled') or {}).get('bytes',1))
 assert d['sparse_capacity'] in (65536,131072,524288) and d['sparse_bytes']==len(sparse)<=d['sparse_capacity'] and 0<d['table_pages']<=256
 pages={};levels={};at=0;descriptors=0;xor=0;metadata=[]
 while at<len(sparse):
  assert at+16<=len(sparse);pa,level,count,crc=struct.unpack_from('<QHHI',sparse,at);at+=16
  assert pa%4096==0 and pa not in pages and c['physical_base']<=pa<pa+4096<=c['physical_base']+c['window_bytes'] and 1<=level<=3 and count<=512
  page=bytearray(4096);last=-1
  for _ in range(count):
   assert at+10<=len(sparse);index,value=struct.unpack_from('<HQ',sparse,at);at+=10;assert last<index<512 and value&1;last=index
   struct.pack_into('<Q',page,index*8,value)
  assert zlib.crc32(page)==crc;xor^=crc;descriptors+=count;pages[pa]=bytes(page);levels[pa]=level;metadata.append(dict(physical=pa,level=level,crc32=crc,nonzero=count,sha256=sha(page)))
 assert at==len(sparse) and len(pages)==d['table_pages'] and descriptors==d['nonzero_descriptors'] and xor==d['table_crc_xor']
 reached={}
 def visit(pa,level):
  assert pa in pages and levels[pa]==level
  if pa in reached:assert reached[pa]==level;return
  reached[pa]=level
  for v in struct.unpack('<512Q',pages[pa]):
   if not v:continue
   if level<3 and v&3==3:visit(v&MASK,level+1)
   else:assert v&3==(3 if level==3 else 1)
 visit(d['original_ttbr0'],1);visit(d['original_ttbr1'],1);assert reached.keys()==pages.keys() and pages[d['original_ttbr0']]==bytes(4096)
 assert mmu['tcr']==c['policy']['tcr'] and 64-(mmu['tcr']&63)==64-((mmu['tcr']>>16)&63)==38
 def walk(va,high):
  va&=(1<<38)-1;pa=d['original_ttbr1' if high else 'original_ttbr0']
  for level in range(1,4):
   shift=12+9*(3-level);v=struct.unpack_from('<Q',pages[pa],8*((va>>shift)&511))[0]
   if not v&1:return None
   if level<3 and v&3==3:pa=v&MASK;continue
   assert v&3==(3 if level==3 else 1);low=(1<<shift)-1;return (v&MASK&~low)|(va&low)
  raise AssertionError('Incomplete translation')
 assert walk(c['low_vectors_pa']+2048,False) is None
 count=0
 for segment in c['early']['ranges']:
  for offset in range(0,segment['bytes'],4096):
   va=segment['virtual']+offset;assert walk(va,True)==va+c['physical_delta'];count+=1
 assert count==d['high_data_pages']
 probes=[c['early']['policy']['checkpoint'],c['policy']['low_vectors'],c['policy']['high_vectors']]
 for va in probes:assert walk(va,True)==va+c['physical_delta']
 assert d['high_probes']==len(probes)
 assert d['adt_physical']==c['args']+4096 and d['adt_bytes']==len(adt_snapshot)==len(original_adt)<=65536
 assert d['adt_crc_before']==d['adt_crc_restored']==zlib.crc32(original_adt) and d['adt_crc_after']==zlib.crc32(adt_snapshot)
 assert d['adt_restored']==d['adt_backup_ok']==1 and d['adt_changed_bytes']==sum(x!=y for x,y in zip(original_adt,adt_snapshot))
 # Parsing is independent of XNU's in-place ADT mutation. Both trees must retain structure.
 from validate_native_load_evidence import parse_adt
 expected=parse_adt(original_adt);seed=expected['children']['chosen']['properties']['random-seed'];assert len(seed)==64
 expected['children']['chosen']['properties']['random-seed']=bytes(len(seed));assert parse_adt(adt_snapshot)==expected
 blob=b''.join(pages[k] for k in sorted(pages))
 return dict(**d,pages=metadata,table_snapshot_bytes=len(blob),table_snapshot_sha256=sha(blob),transition_sha256=sha(transition),adt_snapshot_sha256=sha(adt_snapshot),sparse_sha256=sha(sparse),original_pmap_verified=True,post_pmap_recovery_verified=True,full_xnu_boot_verified=False,scope='Instrumented original arm_vm_init return; dynamic pages captured but not covered by mutable-segment byte restoration')
