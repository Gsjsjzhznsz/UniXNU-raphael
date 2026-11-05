# SPDX-License-Identifier: BSD-2-Clause-Patent
# Isolated emulator probing; guest edits never alter handset artifacts.
import gdb,json,struct
from pathlib import Path
s=json.load(open(SPEC));out=Path(s['output']);c=s['contract'];e=c['early']['policy'];inf=None
r=dict(mode=s['mode'],events=[],target_reached=False)
def save():(out/'observation.json').write_text(json.dumps(r,indent=2)+chr(10))
def reg(n):return int(gdb.parse_and_eval('$'+n))&((1<<64)-1)
def mem(v,n):return bytes(gdb.selected_inferior().read_memory(v,n))
def text(v):
 try:return mem(v,256).split(bytes(1),1)[0].decode(errors='replace')
 except gdb.error:return '<unmapped>'
def snap(name):
 a=dict(label=name,pc=reg('pc'),sp=reg('sp'),lr=reg('x30'),cpsr=reg('cpsr')&0xffffffff)
 a.update({('x'+str(i)):reg('x'+str(i)) for i in range(8)});r['events'].append(a);save();return a
def stop(v):
 b=gdb.Breakpoint('*'+hex(v),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);gdb.execute('continue');b.delete();assert reg('pc')==v
class Point(gdb.Breakpoint):
 def __init__(self,name,v):
  super().__init__('*'+hex(v),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);self.name=name
 def stop(self):
  if self.name=='_kprintf':
   a=dict(label='kprintf',pc=reg('pc'),format=text(reg('x0')))
   try:a['stack_arguments']=list(struct.unpack('<6Q',mem(reg('sp'),48)));a['string_arguments']=[text(v) for v in a['stack_arguments'][:2]]
   except gdb.error:pass
   r['events'].append(a);save();return False
  a=snap(self.name)
  if self.name in ['_panic','_panic_with_options']:
   a['format']=text(a['x0'] if self.name=='_panic' else a['x2'])
   try:
    a['stack_arguments']=list(struct.unpack('<8Q',mem(a['sp'],64)));a['string_arguments']=[text(v) for v in a['stack_arguments']]
   except gdb.error:pass
   a['frames']=[];fp=reg('x29')
   for _ in range(16):
    try:
     previous,lr=struct.unpack('<2Q',mem(fp,16));a['frames'].append(dict(fp=fp,lr=lr))
     if previous<=fp or previous-fp>65536:break
     fp=previous
    except gdb.error:break
   r['panic']=a;save();return True
  if self.name==s['target']:r['target_reached']=True;save();return True
  return False
gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64');gdb.execute('target remote '+s['socket'])
if s.get('kalloc_zones'):
 assert 1<=s['kalloc_zones']<=1000
 stop(c['policy']['arm_init']);args=reg('x0');line=('-v keepsyms=1 cpus=1 kt_fixed_zones='+str(s['kalloc_zones'])).encode()+bytes(1)
 gdb.selected_inferior().write_memory(args+0x6c,line);r['qemu_boot_arguments']=line[:-1].decode();save()
if s['mode']=='panic':
 stop(s['symbols']['_serial_init']);snap('before-injected-panic')
 gdb.execute('set $pc='+hex(s['symbols']['_panic']));gdb.execute('set $x0='+hex(s['format_address']));r['panic_forced_in_qemu']=True;save()
 try:gdb.execute('continue')
 except gdb.error:pass
else:
 stop(e['checkpoint']);snap('original-checkpoint')
 assert struct.unpack('<I',mem(e['checkpoint'],4))[0]==0xd42a6a20
 gdb.selected_inferior().write_memory(e['checkpoint'],struct.pack('<I',e['opcode']))
 # Resume original vectors and panic prologues for real mainline IRQ execution.
 for v,name in [(c['policy']['low_vectors'],'low-vectors.bin'),(c['policy']['high_vectors'],'high-vectors.bin'),(s['symbols']['_panic'],'panic.bin'),(s['symbols']['_panic_with_options'],'panic-options.bin')]:
  gdb.selected_inferior().write_memory(v,(out/name).read_bytes())
 points=[Point(n,v) for n,v in s['symbols'].items() if n!='_serial_init']
 gdb.execute('continue');snap('terminal-stop');gdb.execute('disconnect')
save()
