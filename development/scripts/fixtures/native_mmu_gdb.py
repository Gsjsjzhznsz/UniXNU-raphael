# SPDX-License-Identifier: BSD-2-Clause-Patent
# GDB observer and deliberate negative-case corruption, isolated QEMU only.
import gdb,json,struct
s=json.load(open(SPEC));c=s['contract'];p=c['policy'];trace=[];early=c.get('early');e=early['policy'] if early else None;checkpoint=e['checkpoint'] if early else p['arm_init']
def reg(n):return int(gdb.parse_and_eval('$'+n))&((1<<64)-1)
def sysreg(n):
 for name in [n.upper()+'_EL1',n.upper(),n+'_el1']:
  try:return reg(name)
  except gdb.error:pass
 raise AssertionError('Missing register '+n)
def record(label):
 d=dict(label=label,pc=reg('pc'),sp=reg('sp'),lr=reg('x30'),cpsr=reg('cpsr')&0xffffffff)
 for n in ['x0','x1','x20','x21','x22','x23','x24','x25']:d[n]=reg(n)
 for n in ['sctlr','tcr','ttbr0','ttbr1','mair','vbar']:d[n]=sysreg(n)
 trace.append(d);json.dump(trace,open(s['output'],'w'),indent=2);return d
def stop(at):
 b=gdb.Breakpoint('*'+hex(at),type=gdb.BP_HARDWARE_BREAKPOINT);gdb.execute('continue');assert reg('pc')==at;b.delete()
gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64');gdb.execute('target remote '+s['socket'])
if s['case']=='trace':
 stop(c['mmu_enable_pa']);d=record('before-enable');assert d['sctlr']&0x1005==0 and d['tcr']==p['tcr'] and d['ttbr0']==c['tables_pa'] and d['ttbr1']==c['tables_pa']+4096 and d['mair']==p['mair']
 gdb.execute('stepi');record('after-enable-msr');gdb.execute('stepi');record('after-enable-isb')
stop(checkpoint);d=record('checkpoint' if early else 'arm-init');assert d['sctlr']==p['sctlr'] and d['vbar']==p['high_vectors']
assert d['sp']==p['interrupt_sp']-(e['frame_bytes'] if early else 0) and d['lr']==(e['return_va'] if early else p['arm_init'])
if not early:assert d['x20']==c['args'] and d['x21']==0
else:assert d['x0']==0 and d['x1']==e['const_args']
if s['case']=='trace':
 if early:
  from pathlib import Path
  out=Path(s['output']).parent
  for i,r in enumerate(early['ranges']):(out/('early-range-'+str(i)+'.bin')).write_bytes(bytes(gdb.selected_inferior().read_memory(r['virtual'],r['bytes'])))
 gdb.execute('stepi');assert record('exception-vector')['pc']==p['high_vectors']
 gdb.execute('stepi');record('vector-mov');gdb.execute('stepi');record('vector-ldr');gdb.execute('stepi');assert record('physical-relay')['pc']==c['low_vectors_pa']+2048
 relay=c['low_vectors_pa']+2048;relay_code=bytes(gdb.selected_inferior().read_memory(relay,1024))
 close=[relay+i for i in range(0,len(relay_code),4) if struct.unpack_from('<I',relay_code,i)[0]==0xd5181010];assert len(close)==1
 stop(close[0]);gdb.execute('stepi');gdb.execute('stepi')
 assert record('relay-cache-off')['sctlr']&0x1005==0
elif s['case']=='wrong-brk':
 gdb.selected_inferior().write_memory(checkpoint,struct.pack('<I',0xd42a6a40));record('wrong-brk-written')
elif s['case']=='backup-corrupt':
 # Decode the copied relay's single LDR-literal x16 to its state pointer.
 relay=c['low_vectors_pa']+2048;code=bytes(gdb.selected_inferior().read_memory(relay,1024));hits=[]
 for i in range(0,len(code),4):
  op=struct.unpack_from('<I',code,i)[0]
  if op&0xff00001f==0x58000010:
   offset=(op>>5)&0x7ffff;offset=offset-(1<<19) if offset&(1<<18) else offset
   hits.append(relay+i+offset*4)
 assert len(hits)==1
 def qword(at):return struct.unpack('<Q',bytes(gdb.selected_inferior().read_memory(at,8)))[0]
 assert 'OK' in gdb.execute('maintenance packet Qqemu.PhyMemMode:1',to_string=True)
 state=qword(hits[0]);early_state=qword(state+584);backup=qword(early_state+64)
 assert qword(early_state)==1 and qword(early_state+72)==e['backup_bytes']
 before=qword(backup);gdb.selected_inferior().write_memory(backup,struct.pack('<Q',before^1));assert 'OK' in gdb.execute('maintenance packet Qqemu.PhyMemMode:0',to_string=True);d=record('backup-corrupted');d.update(backup_base=backup,before=before,after=before^1);json.dump(trace,open(s['output'],'w'),indent=2)
else:
 # Corrupt the final high-alias 2MiB block, away from code and vectors.
 index=(((c['virtual_base']&((1<<38)-1))>>21)&511)+c['window_bytes']//0x200000-1
 address=c['tables_pa']+12288+index*8
 old=struct.unpack('<Q',bytes(gdb.selected_inferior().read_memory(address,8)))[0];assert old&0xfff==0x601
 gdb.selected_inferior().write_memory(address,struct.pack('<Q',old^0x200000));d=record('last-table-block-corrupted');d.update(corrupt_address=address,original_descriptor=old,corrupt_descriptor=old^0x200000);json.dump(trace,open(s['output'],'w'),indent=2)
gdb.execute('detach')
