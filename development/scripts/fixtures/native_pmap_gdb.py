# SPDX-License-Identifier: BSD-2-Clause-Patent
# Original C after temporary checkpoint removal; all following accesses are observations.
import gdb,json,struct,hashlib
from pathlib import Path
s=json.load(open(SPEC));out=Path(s['output']);c=s['contract'];e=c['early']['policy'];p=c['policy'];result=dict(stops=[],target_complete=False);baseline={}
mask=(1<<64)-1
def reg(n):return int(gdb.parse_and_eval('$'+n))&mask
def sr(n):
 for name in [n.upper()+'_EL1',n.upper(),n+'_el1']:
  try:return reg(name)
  except gdb.error:pass
 raise AssertionError(n)
def mode(v):assert 'OK' in gdb.execute('maintenance packet Qqemu.PhyMemMode:'+str(v),to_string=True)
def save():(out/'trace.json').write_text(json.dumps(result,indent=2)+chr(10))
def snapshot(label):
 r=dict(label=label,pc=reg('pc'),sp=reg('sp'),lr=reg('x30'),cpsr=reg('cpsr')&0xffffffff)
 for n in range(29):r['x'+str(n)]=reg('x'+str(n))
 for n in ['sctlr','tcr','ttbr0','ttbr1','mair','vbar']:r[n]=sr(n)
 r['segments']=[]
 for i,segment in enumerate(c['early']['ranges']):
  address=segment['virtual'];size=segment['bytes'];raw=bytes(gdb.selected_inferior().read_memory(address,size));name=label+'-data-'+str(i)+'.bin';(out/name).write_bytes(raw)
  if label=='arm-vm-entry':baseline[i]=raw
  before=baseline[i];changed=sum(x!=y for x,y in zip(before,raw));words=sum(before[j:j+8]!=raw[j:j+8] for j in range(0,size,8))
  r['segments'].append(dict(name=segment['name'],virtual=address,bytes=size,file=name,sha256=hashlib.sha256(raw).hexdigest(),changed_bytes=changed,changed_words=words))
 result['stops'].append(r);save();return r
def stop(at):
 b=gdb.Breakpoint('*'+hex(at),type=gdb.BP_HARDWARE_BREAKPOINT);gdb.execute('continue');b.delete()
 if reg('pc')!=at:result['unexpected_pc']=reg('pc');result['unexpected_esr']=sr('esr');save();raise AssertionError('Unexpected stop '+hex(reg('pc')))
def active_tables(r):
 # Capture each unique active page-table page from physical RAM.
 table_pages={};levels={};mode(1)
 try:
  def visit(pa,level):
   pa&=0x0000fffffffff000
   assert c['physical_base']<=pa and pa+4096<=c['physical_base']+c['window_bytes']
   if pa in levels:assert levels[pa]==level;return
   assert len(levels)<512;levels[pa]=level;raw=bytes(gdb.selected_inferior().read_memory(pa,4096));table_pages[pa]=raw
   for value in struct.unpack('<512Q',raw):
    if value&1 and level<3 and value&3==3:visit(value,level+1)
  visit(r['ttbr0'],1);visit(r['ttbr1'],1)
 finally:mode(0)
 table_blob=b''.join(table_pages[pa] for pa in sorted(table_pages));(out/'active-tables.bin').write_bytes(table_blob)
 pages=[dict(physical=pa,level=levels[pa],offset=i*4096,sha256=hashlib.sha256(table_pages[pa]).hexdigest()) for i,pa in enumerate(sorted(table_pages))]
 def walk(address,high):
  bits=64-((r['tcr']>>(16 if high else 0))&63);assert bits==38
  address&=(1<<bits)-1;pa=(r['ttbr1'] if high else r['ttbr0'])&0x0000fffffffff000
  for level in range(1,4):
   shift=12+9*(3-level);value=struct.unpack_from('<Q',table_pages[pa],((address>>shift)&511)*8)[0]
   if not value&1:return None
   if level<3 and value&3==3:pa=value&0x0000fffffffff000;continue
   assert (level<3 and value&3==1) or (level==3 and value&3==3)
   return (value&0x0000fffffffff000&~((1<<shift)-1))|(address&((1<<shift)-1))
  raise AssertionError('No translation')
 probes=[]
 for va in [p['low_vectors'],p['high_vectors'],e['checkpoint'],s['targets']['_PE_consistent_debug_inherit']]:
  physical=walk(va,True);assert physical==va+c['physical_delta'];probes.append(dict(virtual=va,physical=physical))
 checked=0
 for segment in c['early']['ranges']:
  for offset in range(0,segment['bytes'],4096):
   va=segment['virtual']+offset;assert walk(va,True)==va+c['physical_delta'];checked+=1
 relay=c['low_vectors_pa']+2048;assert walk(relay,False) is None
 root0=table_pages[r['ttbr0']&0x0000fffffffff000];assert root0==bytes(4096)
 result['active_tables']=dict(pages=pages,bytes=len(table_blob),sha256=hashlib.sha256(table_blob).hexdigest(),root0_empty=True,physical_relay_mapped=False,original_high_data_pages_verified=checked,high_probes=probes)
 save()
gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64');gdb.execute('target remote '+s['socket'])
stop(e['checkpoint']);assert struct.unpack('<I',bytes(gdb.selected_inferior().read_memory(e['checkpoint'],4)))[0]==0xd42a6a20
gdb.selected_inferior().write_memory(e['checkpoint'],struct.pack('<I',e['opcode']));first=snapshot('arm-vm-entry');end=first['lr']
# Stop before instrumented vectors branch to a physical alias that may no longer exist.
catch=[gdb.Breakpoint('*'+hex(base+i*128),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True) for base in [p['high_vectors'],c['low_vectors_pa']] for i in [0,4,8,12]]
stop(s['targets']['_set_mmu_ttb_alternate']);r=snapshot('ttbr1-entry');new1=r['x0'];ret=r['lr']
stop(ret);r=snapshot('ttbr1-return');assert r['ttbr1']==new1
stop(s['targets']['_set_mmu_ttb']);r=snapshot('ttbr0-entry');new0=r['x0'];ret=r['lr']
stop(ret);r=snapshot('ttbr0-return');assert r['ttbr0']==new0
stop(end);r=snapshot('arm-vm-returned');assert r['ttbr0']==new0 and r['ttbr1']==new1
stop(s['targets']['_PE_consistent_debug_inherit']);r=snapshot('pre-debug-inherit');active_tables(r)
result['target_complete']=True;save();gdb.execute('disconnect')
