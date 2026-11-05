# SPDX-License-Identifier: BSD-2-Clause-Patent
# QEMU-only removal of the current diagnostic BRK; original functions thereafter.
import gdb,json,struct,hashlib
from pathlib import Path
s=json.load(open(SPEC));out=Path(s['output']);c=s['contract'];e=c['early']['policy'];result=dict(stops=[],target_complete=False);baseline={}
def reg(n):return int(gdb.parse_and_eval('$'+n))&((1<<64)-1)
def sr(n):
 for name in [n.upper()+'_EL1',n.upper()+'_EL0',n.upper(),n+'_el1',n+'_el0']:
  try:return reg(name)
  except gdb.error:pass
 raise AssertionError(n)
def mode(v):assert 'OK' in gdb.execute('maintenance packet Qqemu.PhyMemMode:'+str(v),to_string=True)
def mem(pa,n):return bytes(gdb.selected_inferior().read_memory(pa,n))
def save():(out/'trace.json').write_text(json.dumps(result,indent=2)+chr(10))
def snapshot(label):
 d=dict(label=label,pc=reg('pc'),sp=reg('sp'),lr=reg('x30'),cpsr=reg('cpsr')&0xffffffff)
 for j in range(29):d['x'+str(j)]=reg('x'+str(j))
 for n in ['sctlr','tcr','ttbr0','ttbr1','mair','vbar','cntfrq','cntp_ctl','cntp_cval','cntv_ctl','cntv_cval','cntkctl']:d[n]=sr(n)
 d['segments']=[];mode(1)
 try:
  for i,seg in enumerate(s['segments']):
   pa=seg['virtual_address']+c['physical_delta'];raw=mem(pa,seg['bytes']);meta=dict(index=i,physical=pa,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
   if not result['stops'] or seg['virtual_address'] in [x['virtual'] for x in c['early']['ranges']]:
    name=label+'-segment-'+str(i)+'.bin';(out/name).write_bytes(raw);meta['file']=name
    if not result['stops']:baseline[i]=raw
    meta['changed_words_from_first']=sum(raw[j:j+8]!=baseline[i][j:j+8] for j in range(0,len(raw),8))
   d['segments'].append(meta)
  adt=mem(c['args']+4096,s['adt_bytes']);(out/(label+'-adt.bin')).write_bytes(adt);d['adt_sha256']=hashlib.sha256(adt).hexdigest()
 finally:mode(0)
 if label=='kprintf-first-entry':
  data=mem(d['x0'],256).split(bytes(1),1)[0];d['format_utf8']=data.decode(errors='replace');(out/'kprintf-first-format.bin').write_bytes(data)
 result['stops'].append(d);save();return d
def stop(at):
 b=gdb.Breakpoint('*'+hex(at),type=gdb.BP_HARDWARE_BREAKPOINT);gdb.execute('continue');b.delete()
 if reg('pc')!=at:
  snapshot('unexpected-stop');result['unexpected_esr']=sr('esr');result['unexpected_elr']=sr('elr');save();raise AssertionError('Unexpected stop '+hex(reg('pc')))
def call(name,label):
 stop(s['targets'][name]);r=snapshot(label+'-entry');ret=r['lr'];stop(ret);return snapshot(label+'-returned')
gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64');gdb.execute('target remote '+s['socket'])
stop(e['checkpoint']);assert struct.unpack('<I',mem(e['checkpoint'],4))[0]==0xd42a6a20;gdb.selected_inferior().write_memory(e['checkpoint'],struct.pack('<I',e['opcode']));first=snapshot('post-pmap-entry');ret=first['lr']
# Stop on unexpected faults or panic without interpreting them as successful progress.
catch=[gdb.Breakpoint('*'+hex(base+i*128),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True) for base in [c['policy']['high_vectors'],c['low_vectors_pa']] for i in [0,4,8,12]]
catch.append(gdb.Breakpoint('*'+hex(s['targets']['_panic']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True))
stop(ret);r=snapshot('debug-inherit-returned');assert r['x0']&0xffffffff==0xffffffff
r=call('_serial_init','serial');assert r['x0']==0
stop(s['targets']['_kprintf']);r=snapshot('kprintf-first-entry');assert r['format_utf8']=='kprintf initialized'+chr(10)
call('_PE_create_console','create-console');call('_PE_init_printf','init-printf');call('_cpu_machine_idle_init','idle-init')
stop(s['targets']['_PE_init_platform']);r=snapshot('platform-second-entry');assert r['x0']==1;ret=r['lr'];stop(ret);snapshot('platform-second-returned')
call('_cpu_timebase_init','timebase-init');call('_PE_init_cpu','init-cpu');call('_fiq_context_init','fiq-context');stop(s['targets']['_machine_startup']);snapshot('machine-startup-entry')
result['target_complete']=True;save();gdb.execute('disconnect')
