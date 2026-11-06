# SPDX-License-Identifier: BSD-2-Clause-Patent
# Observe original switch, high prefix, bounded clean and original restoration.
import gdb,json,struct,hashlib
from pathlib import Path
s=json.load(open(SPEC));out=Path(s['output']);c=s['contract'];p=c['policy'];e=c['early']['policy'];trace=[];mask=0x0000fffffffff000

def reg(n):return int(gdb.parse_and_eval('$'+n))&((1<<64)-1)
def sr(n):
 for name in [n.upper()+'_EL1',n.upper()+'_EL0',n.upper(),n+'_el1',n+'_el0']:
  try:return reg(name)
  except gdb.error:pass
 raise AssertionError(n)
def record(label,**extra):
 d=dict(label=label,pc=reg('pc'),sp=reg('sp'),lr=reg('x30'),cpsr=reg('cpsr')&0xffffffff,**extra)
 for n in ['x0','x1','x8','x10','x13','x14','x16','x17','x20','x21','x22','x23','x24','x25']:d[n]=reg(n)
 for n in ['sctlr','tcr','ttbr0','ttbr1','mair','vbar']:d[n]=sr(n)
 trace.append(d);(out/'trace.json').write_text(json.dumps(trace,indent=2)+chr(10));return d
def stop(at):
 b=gdb.Breakpoint('*'+hex(at),type=gdb.BP_HARDWARE_BREAKPOINT);gdb.execute('continue');b.delete();assert reg('pc')==at,hex(reg('pc'))
def mem(at,n):return bytes(gdb.selected_inferior().read_memory(at,n))
def word(at):return struct.unpack('<I',mem(at,4))[0]
def qword(at):return struct.unpack('<Q',mem(at,8))[0]
def mode(v):assert 'OK' in gdb.execute('maintenance packet Qqemu.PhyMemMode:'+str(v),to_string=True)
def literal(code,base,offset,register):
 w=struct.unpack_from('<I',code,offset)[0];assert w&0xff00001f==0x58000000|register;imm=(w>>5)&0x7ffff;imm-=1<<19 if imm&(1<<18) else 0;return base+offset+4*imm

gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64');gdb.execute('target remote '+s['socket'])
if s['case']=='trace':
 stop(s['symbols']['_arm_vm_init']);r=record('arm-vm-entry');assert r['ttbr0']==c['tables_pa'] and r['ttbr1']==c['tables_pa']+4096
 end=r['lr'];stop(s['symbols']['_set_mmu_ttb_alternate']);r=record('ttbr1-entry');ret=r['lr'];new1=r['x0'];stop(ret);assert record('ttbr1-return')['ttbr1']==new1
 stop(s['symbols']['_set_mmu_ttb']);r=record('ttbr0-entry');ret=r['lr'];new0=r['x0'];stop(ret);assert record('ttbr0-return')['ttbr0']==new0
 stop(end);record('arm-vm-returned')
stop(e['checkpoint']);r=record('checkpoint');assert r['sp']==p['interrupt_sp']-e['frame_bytes'] and r['lr']==e['return_va']
assert word(e['checkpoint'])==0xd42a6a20
relay=c['low_vectors_pa']+2048;mode(1)
try:
 code=mem(relay,1024)
 # State literal is the first LDR x16 after the cache-off MSR, not the high prefix literals.
 off=next(i for i in range(0,len(code),4) if struct.unpack_from('<I',code,i)[0]==0xd5181010)
 loads=[i for i in range(off+4,len(code),4) if struct.unpack_from('<I',code,i)[0]&0xff00001f==0x58000010];assert loads
 state=qword(literal(code,relay,loads[0],16));pmap=qword(state+592);transition=qword(pmap+24);early=qword(state+584)
 assert qword(state)==2 and qword(pmap)==1 and qword(pmap+32)==(24576 if c["window_bytes"]==1536*1048576 else 16384)
 tables={};levels={}
 def visit(pa,level):
  assert pa&4095==0 and c['physical_base']<=pa<pa+4096<=c['physical_base']+c['window_bytes']
  if pa in tables:assert levels[pa]==level;return
  assert len(tables)<256;tables[pa]=mem(pa,4096);levels[pa]=level
  for v in struct.unpack('<512Q',tables[pa]):
   if v&1 and level<3 and v&3==3:visit(v&mask,level+1)
 visit(r['ttbr0']&mask,1);visit(r['ttbr1']&mask,1)
 if s['case']=='trace':
  blob=b''.join(tables[k] for k in sorted(tables));(out/'active-tables.bin').write_bytes(blob)
  (out/'active-pages.json').write_text(json.dumps([dict(physical=pa,level=levels[pa],offset=i*4096,sha256=hashlib.sha256(tables[pa]).hexdigest()) for i,pa in enumerate(sorted(tables))],indent=2)+chr(10))
  (out/'transition.bin').write_bytes(mem(transition,qword(pmap+32)));adt=qword(pmap+192);adtbytes=qword(pmap+200);(out/'adt.bin').write_bytes(mem(adt,adtbytes))
  for i,x in enumerate(c['early']['ranges']):(out/('range-'+str(i)+'.bin')).write_bytes(mem(x['virtual']+c['physical_delta'],x['bytes']))
 elif s['case']=='transition-corrupt':
  at=transition+511*8;before=qword(at);assert before==0;gdb.selected_inferior().write_memory(at,struct.pack('<Q',1));record('transition-unused-corrupted',address=at,before=0,after=1)
 elif s['case']=='backup-corrupt':
  at=qword(early+64);before=qword(at);gdb.selected_inferior().write_memory(at,struct.pack('<Q',before^1));record('backup-corrupted',address=at,before=before,after=before^1)
 elif s['case']=='bad-active-table':
  va=c['early']['ranges'][0]['virtual']&((1<<38)-1);pa=r['ttbr1']&mask
  for level in range(1,4):
   shift=12+9*(3-level);at=pa+((va>>shift)&511)*8;before=qword(at)
   if level<3 and before&3==3:pa=before&mask;continue
   assert level==3 and before&3==3;break
  after=before^4096;gdb.selected_inferior().write_memory(at,struct.pack('<Q',after));record('active-leaf-corrupted',address=at,before=before,after=after)
finally:mode(0)
if s['case']=='wrong-brk':gdb.selected_inferior().write_memory(e['checkpoint'],struct.pack('<I',0xd42a6a40));record('wrong-brk-written')
if s['case']=='trace':
 gdb.execute('stepi');assert record('exception-vector')['pc']==p['high_vectors']
 for _ in range(3):gdb.execute('stepi')
 high=p['low_vectors']+2048;assert record('high-prefix')['pc']==high
 prefix=mem(high,128);at=next(i for i in range(0,len(prefix),4) if struct.unpack_from('<I',prefix,i)[0]==0xd5182010)
 stop(high+at);r=record('before-transition');assert r['x8']==new0 and r['x16']==transition
 gdb.execute('stepi');assert record('after-transition')['ttbr0']==transition
 # Locate the one BR x16 in the prefix; its literal is the physical body.
 branches=[i for i in range(0,len(prefix),4) if struct.unpack_from('<I',prefix,i)[0]==0xd61f0200];assert len(branches)==1
 body=qword(literal(prefix,high,branches[0]-4,16));stop(body);r=record('physical-body');assert r['ttbr0']==transition and r['ttbr1']==new1 and r['x8']==new0
 physical_code=mem(relay,1024);cleans=[relay+i for i in range(0,len(physical_code),4) if struct.unpack_from('<I',physical_code,i)[0]==0xd50b7e2d];assert len(cleans)==1
 stop(cleans[0]);r=record('clean-first-line');assert r['x13']==c['physical_base'] and r['x14']==c['physical_base']+c['window_bytes'] and r['x10']==4<<((sr('ctr')>>16)&15)
 stop(relay+off);gdb.execute('stepi');gdb.execute('stepi');r=record('cache-off');assert r['sctlr']&0x1005==0 and r['ttbr0']==transition and r['x8']==new0
 record('captured',original_ttbr0=new0,original_ttbr1=new1,transition=transition)
gdb.execute('detach')
