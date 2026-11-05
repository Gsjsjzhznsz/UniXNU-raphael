# SPDX-License-Identifier: BSD-2-Clause-Patent
# QEMU-only runtime unpatch of the existing arm_init checkpoint, read-only observation thereafter.
import gdb,json,struct,hashlib
from pathlib import Path
s=json.load(open(SPEC));out=Path(s['output']);c=s['contract'];p=c['policy'];result=dict(stops=[],target_complete=False);baseline={};inferior=None
mask=(1<<64)-1
def reg(n):return int(gdb.parse_and_eval('$'+n))&mask
def sr(n):
 for name in [n.upper()+'_EL1',n.upper(),n+'_el1']:
  try:return reg(name)
  except gdb.error:pass
 raise AssertionError(n)
def save(): (out/'trace.json').write_text(json.dumps(result,indent=2)+chr(10))
def snapshot(label):
 r=dict(label=label,pc=reg('pc'),sp=reg('sp'),lr=reg('x30'),cpsr=reg('cpsr')&0xffffffff)
 for n in range(29):r['x'+str(n)]=reg('x'+str(n))
 for n in ['sctlr','tcr','ttbr0','ttbr1','mair','vbar']:r[n]=sr(n)
 r['segments']=[]
 for i,segment in enumerate(s['segments']):
  address=segment['virtual_address'];size=segment['bytes'];raw=bytes(inferior.read_memory(address,size));name=label+'-segment-'+str(i)+'.bin';(out/name).write_bytes(raw)
  if label=='arm-init':baseline[i]=raw
  before=baseline[i];dirty=[offset for offset in range(0,size,4096) if before[offset:offset+4096]!=raw[offset:offset+4096]]
  changed=sum(x!=y for x,y in zip(before,raw))
  r['segments'].append(dict(index=i,virtual_address=address,bytes=size,protection=segment['protection'],file=name,sha256=hashlib.sha256(raw).hexdigest(),changed_bytes=changed,dirty_pages=dirty))
 r['table_sha256']=hashlib.sha256(bytes(inferior.read_memory(p['tables'],65536))).hexdigest()
 result['stops'].append(r);save();return r
def stop(at):
 b=gdb.Breakpoint('*'+hex(at),type=gdb.BP_HARDWARE_BREAKPOINT);gdb.execute('continue');b.delete()
 if reg('pc')!=at:result['unexpected_pc']=reg('pc');save();raise AssertionError('Unexpected stop '+hex(reg('pc')))
gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64');gdb.execute('target remote '+s['socket']);inferior=gdb.selected_inferior()
stop(p['arm_init']);assert struct.unpack('<I',bytes(inferior.read_memory(p['arm_init'],4)))[0]==0xd42a6a20
inferior.write_memory(p['arm_init'],struct.pack('<I',p['arm_opcode']))
snapshot('arm-init')
# Unexpected synchronous exceptions stop before the stage10 recovery uses its old CRC assumptions.
catch=[gdb.Breakpoint('*'+hex(base+i*128),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True) for base in [p['high_vectors'],c['low_vectors_pa']] for i in [0,4,8,12]]
stop(s['targets']['_PE_init_platform']);r=snapshot('platform-first');assert r['x0']==0 and r['x1']>c['virtual_base'];ret=r['lr']
stop(ret);snapshot('platform-returned')
stop(s['targets']['_rtclock_early_init']);snapshot('rtclock-entry')
stop(s['targets']['_arm_vm_init']);snapshot('arm-vm-entry')
assert len({x['table_sha256'] for x in result['stops']})==1
result['target_complete']=True;save()
# The host terminates this QEMU; no claim of restored original memory or Android return.
gdb.execute('disconnect')
