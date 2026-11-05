# SPDX-License-Identifier: BSD-2-Clause-Patent
# Runs inside GDB against an isolated QEMU only. No target-code patching.
import gdb,json,struct,time
from pathlib import Path
spec=json.loads(Path(SPEC).read_text())
result={'breakpoints':[],'stops':[],'native_instruction_executed':False,'arm_init_reached':False,'target_reached':False,'reached_symbols':[]}
out=Path(spec['output'])
def save():out.write_text(json.dumps(result,indent=2)+'\n')
def reg(name):return int(gdb.parse_and_eval('$'+name)) & ((1<<64)-1)
def snapshot(label):
 item=dict(label=label,pc=reg('pc'),sp=reg('sp'),x0=reg('x0'),fp=reg('x29'),lr=reg('x30'),cpsr=reg('cpsr'))
 item['cpsr']&=0xffffffff
 for n in ['SCTLR_EL1','SCTLR','sctlr_el1']:
  try:item['sctlr_el1']=reg(n);break
  except gdb.error:pass
 for n in ['ESR_EL1','ESR','FAR_EL1','FAR','ELR_EL1','ELR','CNTFRQ_EL0','CNTFRQ','MPIDR_EL1','MPIDR','TPIDR_EL1']:
  try:item[n]=reg(n)
  except gdb.error:pass
 result['stops'].append(item);save();return item
def capture_msgbuf():
 abi=spec.get('user_abi',{}).get('msgbuf')
 if not abi or '_msgbufp' not in spec.get('data_symbols',{}):return
 try:
  pointer=int.from_bytes(bytes(inferior.read_memory(spec['data_symbols']['_msgbufp'],8)),'little')
  fields={name:int.from_bytes(bytes(inferior.read_memory(pointer+offset,8 if name=='msg_bufc' else 4)),'little') for name,offset in abi['fields'].items()}
  assert fields['msg_magic']==abi['magic'] and 0<fields['msg_size']<=1048576 and 0<=fields['msg_bufx']<fields['msg_size'],fields
  raw=bytes(inferior.read_memory(fields['msg_bufc'],fields['msg_size']));at=fields['msg_bufx']
  text=(raw[at:]+raw[:at]).lstrip(b'\0').decode(errors='replace')
  (out.parent/'kernel-msgbuf.log').write_text(text)
  result['kernel_message_buffer']=dict(pointer=pointer,fields=fields,log='kernel-msgbuf.log',text=text)
 except Exception as error:result['kernel_message_buffer_error']=type(error).__name__+': '+str(error)
observer_started=time.monotonic()
def capture_data_once():
 if not spec.get('capture_data_after') or 'data_ram_snapshot' in result:return
 if time.monotonic()-observer_started<spec['capture_data_after']:return
 try:
  data=spec['data_symbols'];read=lambda a:int.from_bytes(bytes(inferior.read_memory(a,8)),'little')
  base=read(data['_native_owner_data_seed_base']);size=read(data['_native_owner_data_seed_size'])
  if spec['expected_data_seed'].get('sparse'):
   abi=spec.get('sparse_data_abi');instance=result.get('sparse_data_instance')
   if not abi or not instance:
    result['data_ram_snapshot_unavailable']='Sparse block device has no contiguous data base; matching DWARF and an observed actual I/O instance required'
    save();return
   fields=abi['fields'];offsets=abi['sparse_fields'];sparse=instance+fields['sparse']
   assert read(instance)==abi['vtable'] and read(instance+fields['memory'])==0
   assert bytes(inferior.read_memory(instance+fields['online'],1))==b'\x01' and bytes(inferior.read_memory(instance+fields['isBig'],1))==b'\x00'
   assert base==0 and size==spec['expected_data_seed']['image_bytes'] and 0<size<=0x80000000 and size%4096==0
   assert read(instance+fields['capacity'])*512==size and read(sparse+offsets['bytes'])==size
   table=read(sparse+offsets['pages']);resident=read(sparse+offsets['resident']);assert table and resident<=size and resident%4096==0
   count=size//4096;raw=bytearray()
   for offset in range(0,count*8,1048576):raw.extend(bytes(inferior.read_memory(table+offset,min(1048576,count*8-offset))))
   pages=struct.unpack('<'+'Q'*count,raw);assert sum(bool(p) for p in pages)*4096==resident
   path=out.parent/'data-observed.raw'
   with path.open('xb') as stream:
    stream.truncate(size)
    index=0
    while index<count:
     pointer=pages[index]
     if not pointer:index+=1;continue
     assert pointer>>48==0xffff
     end=index+1
     while end<count and end-index<256 and pages[end]==pointer+(end-index)*4096:end+=1
     stream.seek(index*4096);stream.write(bytes(inferior.read_memory(pointer,(end-index)*4096)));index=end
   result['data_ram_snapshot']=dict(path=path.name,base=0,bytes=size,resident_bytes=resident,instance=instance,scope='Actual sparse RAM pages reconstructed with single QEMU CPU stopped; implicit holes are zero; no guest writes; APFS consistency and persistence not assumed',layout=abi)
   save();return
  assert size==spec['expected_data_seed']['image_bytes'] and 0<size<=0x20000000
  assert spec['virtual_base']<=base and base+size<=spec['virtual_base']+spec['window']
  path=out.parent/'data-observed.raw'
  with path.open('xb') as stream:
   for offset in range(0,size,1048576):stream.write(bytes(inferior.read_memory(base+offset,min(1048576,size-offset))))
  result['data_ram_snapshot']=dict(path=path.name,base=base,bytes=size,scope='Dense owned QEMU RAM disk captured with the single CPU stopped; APFS consistency and persistence not assumed')
 except Exception as error:result['data_ram_snapshot_error']=type(error).__name__+': '+str(error)
 save()
def task_user_reader(task,layout):
 # Read-only translation for another task; never change TTBRs or page tables.
 # Geometry comes from the exact build's native_pt_attr, and PA aliases follow
 # that build's arm_vm_init.c phystokv()/ptov_table implementation.
 field=lambda kind,name:layout[kind]['fields'][name]
 read=lambda a,n=8:int.from_bytes(bytes(inferior.read_memory(a,n)),'little')
 symbols=spec['data_symbols'];phys=read(symbols['_gPhysBase']);virt=read(symbols['_gVirtBase']);length=read(symbols['_real_phys_size'])
 assert phys==spec['physical_base'] and 0<length<=spec['window'],dict(phys=phys,expected=spec['physical_base'],size=length,window=spec['window'])
 aliases=[]
 for index in range(8):
  pa,va,size=struct.unpack('<3Q',bytes(inferior.read_memory(symbols['_ptov_table']+24*index,24)))
  if not size:break
  aliases.append((pa,va,size))
 def physical(address,size):
  assert phys<=address and address+size<=phys+length,dict(address=address,bytes=size,phys=phys,length=length)
  for pa,va,span_bytes in aliases:
   if pa<=address and address+size<=pa+span_bytes:return bytes(inferior.read_memory(va+address-pa,size))
  return bytes(inferior.read_memory(virt+address-phys,size))
 vm_map=read(task+field('task','map'));pmap=read(vm_map+field('vm_map','pmap'));root=read(pmap+field('pmap','ttep'));rootva=read(pmap+field('pmap','tte'))
 attr=read(symbols['_native_pt_attr']);level=read(attr+field('page_table_attr','root_level'),4);last=read(attr+field('page_table_attr','max_level'),4);page=read(attr+field('page_table_attr','page_size'))
 assert page==4096 and 0<=level<=last==3 and root%8==0,dict(page=page,level=level,last=last,root=root)
 assert physical(root,8)==bytes(inferior.read_memory(rootva,8))
 minimum=read(pmap+field('pmap','min'));maximum=read(pmap+field('pmap','max'))
 def user(address,size):
  assert minimum<=address and address+size<=maximum and 0<size<=4096
  output=bytearray()
  while size:
   table=root
   for current in range(level,last+1):
    shift=12+9*(last-current);index=(address>>shift)&511
    descriptor=int.from_bytes(physical(table+index*8,8),'little')
    if not descriptor&1:raise ValueError('Requested user page is not resident')
    if current==last or not descriptor&2:
     assert current>0 and (current<last or descriptor&3==3)
     offsetmask=(1<<shift)-1;pa=(descriptor&0x0000fffffffff000&~offsetmask)+(address&offsetmask);break
    table=descriptor&0x0000fffffffff000
   take=min(size,4096-(address&4095));output.extend(physical(pa,take));address+=take;size-=take
  return bytes(output)
 return user,dict(pmap=pmap,root_physical=root,root_virtual=rootva,granule=page,root_level=level,physical_alias_crosscheck=True)

def capture_processes():
 identity=spec.get('data_symbols',{}).get('_gIOPlatformUUIDAndSerialDone')
 if identity:
  result['platform_uuid_published']=bool(int.from_bytes(bytes(inferior.read_memory(identity,1)),'little'))
 layout=spec.get('user_abi',{}).get('process_snapshot')
 if not layout or '_allproc' not in spec.get('data_symbols',{}):return
 result['process_snapshot']=dict(processes=[],scope='Stopped QEMU CPU; bounded read-only process/thread census, not proof of main or scheduling progress')
 read=lambda a,n=8:int.from_bytes(bytes(inferior.read_memory(a,n)),'little')
 field=lambda kind,name:layout[kind]['fields'][name]
 try:
  proc=read(spec['data_symbols']['_allproc']);seen=set()
  while proc and proc not in seen and len(seen)<512:
   seen.add(proc);abi=spec['user_abi'];comm=bytes(inferior.read_memory(proc+abi['proc']['comm'],16)).split(b'\0')[0].decode(errors='replace')
   record=dict(address=proc,pid=read(proc+abi['proc']['pid'],4),comm=comm,stat=read(proc+field('proc','stat'),1))
   result['process_snapshot']['processes'].append(record)
   if record['pid'] in globals().get('runtime_target_pids',set()) or comm in ('xpcproxy','backboardd','SpringBoard','launchd','logd','notifyd','cfprefsd','runningboardd','containermanager','containermanage','lsd','com.apple.datami','com.apple.migrat','PreBoard','keybagd','profiled','nehelper','configd','swcd','locationd'):
    try:
     ro=read(proc+field('proc','ro'));assert read(ro+field('proc_ro','proc'))==proc
     task=read(ro+field('proc_ro','task'));head=task+field('task','threads');cursor=read(head+field('queue_entry','next'))
     record.update(task=task,thread_count=read(task+field('task','thread_count'),4),threads=[])
     if 'shared_region' in layout:
      shared=read(task+field('task','shared_region'))
      if shared:record['shared_region']=dict(address=shared,slide=read(shared+field('shared_region','slide'),4),base=read(shared+field('shared_region','base')),size=read(shared+field('shared_region','size')))
     threads=set()
     while cursor!=head and cursor and cursor not in threads and len(threads)<64:
      # XNU queue_enter stores the element base, not the chain address.
      threads.add(cursor);thread=cursor
      tro=read(thread+field('thread','ro'));assert read(tro+field('thread_ro','task'))==task
      item=dict(address=thread,state=read(thread+field('thread','state'),4),wait_event=read(thread+field('thread','wait_event')),continuation=read(thread+field('thread','continuation')))
      record['threads'].append(item)
      if 'kernel_state' in layout:
       saved=read(thread+field('thread','machine')+field('machine_thread','kstackptr'))
       if saved:
        item['kernel_state']={k:read(saved+field('kernel_state',k)) for k in ('fp','lr','sp')}
        fp=item['kernel_state']['fp'];item['kernel_frames']=[]
        for _ in range(20):
         if not fp or fp&15:break
         try:
          previous,ret=struct.unpack('<2Q',bytes(inferior.read_memory(fp,16)))
          item['kernel_frames'].append(dict(fp=fp,return_address=ret))
          if previous<=fp or previous-fp>65536:break
          fp=previous
         except gdb.error:break
      user=read(thread+field('thread','machine')+field('machine_thread','upcb'))
      if user:
       state=abi['saved_state'];item['user_state']={k:read(user+state[k],4 if k in ('cpsr','esr') else 8) for k in ('pc','sp','fp','lr','cpsr','esr')}
       item['user_state']['syscall_number']=read(user+state['x']+16*8)
       item['user_state']['arguments']=[read(user+state['x']+j*8) for j in range(8)]
       if spec.get('exception_process')==comm and item['user_state']['esr']>>26==0x3c:
        item['user_state']['general_registers']=list(struct.unpack('<29Q',bytes(inferior.read_memory(user+state['x'],29*8))))
       if 'pmap' in layout and (record['pid'] in globals().get('runtime_target_pids',set()) or comm in ('xpcproxy','backboardd','SpringBoard','containermanager','lsd','com.apple.datami','com.apple.migrat','PreBoard','keybagd','profiled','nehelper','configd','swcd','locationd')):
        try:
         reader,mapping=task_user_reader(task,layout);item['user_mapping']=mapping;item['user_frames']=[];fp=item['user_state']['fp']
         if 'general_registers' in item['user_state']:
          item['user_exception_register_memory']={}
          for number in (19,20,21):
           address=item['user_state']['general_registers'][number]
           try:item['user_exception_register_memory']['x'+str(number)]=dict(address=address,bytes=reader(address,128).hex())
           except Exception as error:item['user_exception_register_memory']['x'+str(number)]=dict(address=address,error=str(error))
         if comm=='xpcproxy' and item['user_state']['syscall_number'] in (244,463):
          try:item['pending_exec_path']=reader(item['user_state']['arguments'][1],256).split(b'\0')[0].decode(errors='replace')
          except Exception:pass
         if item['user_state']['syscall_number']==(1<<64)-47 and item['user_state']['esr']>>26==0x15:
          try:
           message=reader(item['user_state']['arguments'][0],24);bits,size,remote,local,voucher,ident=struct.unpack('<5Ii',message)
           if 24<=size<=65536:item['pending_mach_message']=dict(bits=bits,size=size,remote=remote,local=local,voucher=voucher,id=ident,raw_header=message.hex(),scope='Saved user trap input buffer; no successful RPC or reply implied')
          except Exception:pass
         try:item['user_instruction_window']=reader(item['user_state']['pc']-8,32).hex()
         except Exception:pass
         for _ in range(24):
          if not fp or fp&15:break
          previous,ret=struct.unpack('<2Q',reader(fp,16));item['user_frames'].append(dict(fp=fp,return_address=ret))
          if previous<=fp or previous-fp>1048576:break
          fp=previous
        except Exception as error:
         import traceback
         item['user_stack_error']=type(error).__name__+': '+str(error);item['user_stack_traceback']=traceback.format_exc()
      cursor=read(thread+field('thread','task_links')+field('queue_entry','next'))
    except Exception as error:record['thread_error']=type(error).__name__+': '+str(error)
   proc=read(proc+field('proc','next'))
  result['process_snapshot']['bounded']=bool(proc)
 except Exception as error:result['process_snapshot']['error']=type(error).__name__+': '+str(error)
 save()
try:
 gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64')
 gdb.execute('target remote '+spec['socket'])
 gdb.execute('set logging file '+spec['register_log']);gdb.execute('set logging enabled on')
 gdb.execute('info all-registers');gdb.execute('set logging enabled off')
 inferior=gdb.selected_inferior();gate=spec['gate']
 if spec.get('preload'):
  import hashlib,re
  pre=spec['preload'];magic,release,exits=struct.unpack('<3Q',bytes(inferior.read_memory(gate,24)))
  assert magic==0x4e41544956454731 and release==0 and exits==0
  class Allocation(gdb.Breakpoint):
   def stop(self):return reg('x1')==pre['kernel_bytes']
  pool=Allocation('*'+hex(pre['allocate_pool']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
  inferior.write_memory(gate+8,struct.pack('<Q',1));gdb.execute('continue')
  assert reg('pc')==pre['allocate_pool'] and reg('x0')==4 and reg('x1')==pre['kernel_bytes']
  slot,caller=reg('x2'),reg('x30');pool.delete()
  ret=gdb.Breakpoint('*'+hex(caller),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);gdb.execute('continue')
  assert reg('pc')==caller and reg('x0')==0
  source=struct.unpack('<Q',bytes(inferior.read_memory(slot,8)))[0];ret.delete()
  assert pre['arena_base']<=source and source+pre['kernel_bytes']<=pre['arena_base']+pre['arena_bytes']
  assert not(source<spec['physical_base']+spec['window'] and spec['physical_base']<source+pre['kernel_bytes'])
  result['kernel_file_buffer']=dict(address=source,bytes=pre['kernel_bytes'],memory_type=4,in_staging_arena=True,outside_kernel_window=True)
  class FreeSource(gdb.Breakpoint):
   def stop(self):return reg('x0')==source
  free=FreeSource('*'+hex(pre['free_pool']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);gdb.execute('continue')
  assert reg('pc')==pre['free_pool'] and reg('x0')==source
  digest=hashlib.sha256(bytes(inferior.read_memory(source,pre['kernel_bytes']))).hexdigest();assert digest==pre['kernel_sha256']
  result['kernel_file_buffer'].update(sha256=digest,file_bytes_match=True,free_called_after_load=True);free.delete();save()
  wait=gdb.Breakpoint('*'+hex(pre['gate_wait']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);gdb.execute('continue')
  assert reg('pc')==pre['gate_wait'];wait.delete()
  text=Path(pre['serial_log']).read_text(errors='replace')
  layout=re.search(r'DARWINBOOT: ARM64 va=0x([0-9a-fA-F]+) pa=0x([0-9a-fA-F]+) args=0x([0-9a-fA-F]+) entry=0x([0-9a-fA-F]+) owned=0x([0-9a-fA-F]+)',text);assert layout
  va,pa,args,entry,window=[int(v,16) for v in layout.groups()]
  assert va==spec['virtual_base'] and pa==spec['physical_base'] and window==spec['window'] and entry==spec['entry']
  spec['args']=args;result['observed_loader_layout']=dict(virtual_base=va,physical_base=pa,args=args,entry=entry,window=window);save()
 raw=bytes(inferior.read_memory(gate,24));magic,release,exits=struct.unpack('<3Q',raw)
 assert magic==0x4e41544956454731 and release==0 and exits==1,(magic,release,exits)
 result['exit_notice_count']=exits
 entry=gdb.Breakpoint('*'+hex(spec['entry']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
 result['breakpoints'].append(dict(name='native-entry',address=spec['entry']));save()
 inferior.write_memory(gate+8,struct.pack('<Q',1))
 gdb.execute('continue')
 initial=snapshot('native-entry')
 assert initial['pc']==spec['entry'] and initial['x0']==spec['args'] and initial['cpsr']&15==5
 assert initial['cpsr']&0x3c0==0x3c0 and initial['sctlr_el1']&0x1005==0
 import hashlib
 verified=[]
 for segment in spec['segments']:
  size=segment['file_bytes']
  if not size:continue
  address=spec['physical_base']+segment['virtual_address']-spec['virtual_base']
  data=bytes(inferior.read_memory(address,size))
  digest=hashlib.sha256(data).hexdigest()
  assert digest==segment['sha256'],segment['name']
  verified.append(dict(name=segment['name'],physical_address=address,bytes=size,sha256=digest))
 result['loaded_segments']=verified;result['loaded_file_bytes_match']=True;save()
 args=bytes(inferior.read_memory(initial['x0'],64))
 revision,version=struct.unpack_from('<2H',args)
 assert revision==version==2
 result['boot_args_revision']=revision;result['boot_args_version']=version
 entry.delete();gdb.execute('stepi')
 executed=snapshot('after-first-native-instruction')
 assert executed['pc']!=initial['pc']
 result['native_instruction_executed']=True;save()
 points=[]
 spawn_returns={}
 runtime_target_pids=set()
 target_main_points={}
 for name,value in spec['milestones'].items():
  if name in ('_write','_exit','_execve','_posix_spawn'):continue
  for address in set([value,spec['physical_base']+value-spec['virtual_base']]):
   if address in [initial['pc'],executed['pc']]:continue
   b=gdb.Breakpoint('*'+hex(address),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,name,address));result['breakpoints'].append(dict(name=name,address=address))
 save()
 for i in range(4096 if spec.get('runtime_observation') else 512):
  gdb.execute('continue');item=snapshot('milestone')
  matches=[(b,n,a) for b,n,a in points if b.is_valid() and a==item['pc']]
  if not matches:
   # A host SIGINT on the observation deadline stops the guest for read-only
   # PC/frame inspection. This is a failed target, never a synthetic milestone.
   stopped=dict(item,registers={n:reg(n) for n in ['x'+str(j) for j in range(1,8)]},frames=[])
   fp=item['fp']
   for _ in range(20):
    if not fp or fp&15:break
    try:
     previous,ret=struct.unpack('<2Q',bytes(inferior.read_memory(fp,16)))
     stopped['frames'].append(dict(fp=fp,return_address=ret))
     if previous<=fp or previous-fp>65536:break
     fp=previous
    except gdb.error:break
   try:stopped['instructions']=gdb.execute('x/12i '+hex(item['pc']),to_string=True)
   except gdb.error:pass
   result['interrupted_progress']={}
   for n,address in spec.get('data_symbols',{}).items():
    if n.startswith(('_native_virtio_','_native_owner_cache_')):
     size=8 if n.endswith(('verified_blocks','sectors','mmio_physical','actual_mount_flags')) else 32 if n.endswith('first_sector_sha256') else 4
     try:result['interrupted_progress'][n]=bytes(inferior.read_memory(address,size)).hex() if size==32 else int.from_bytes(bytes(inferior.read_memory(address,size)),'little')
     except gdb.error:pass
   result['interrupted_stop']=stopped
   request=spec.get('progress_request')
   if request and Path(request).exists():
    if item['cpsr']&0x1f:
     Path(request).unlink();capture_processes();capture_msgbuf();capture_data_once()
     result.setdefault('progress_samples',[]).append(dict(cpu=stopped,process_snapshot=result.get('process_snapshot')))
    else:result['progress_snapshot_deferred_to_kernel']=True
    result.pop('interrupted_stop',None);save();continue
   save();break
  names=[n for _,n,_ in matches];item['symbols']=names;save()
  request=spec.get('progress_request')
  if request and Path(request).exists() and item['cpsr']&0x1f and result.get('original_launchd_main_executed'):
   Path(request).unlink();capture_processes();capture_msgbuf();capture_data_once()
   result.setdefault('progress_samples',[]).append(dict(cpu=item,process_snapshot=result.get('process_snapshot')));save()
  if names==['_raphael_cpu_start_return'] and item['sp']!=result['cpu_start']['entry_sp']:
   result['unrelated_cpu_return_stops']=result.get('unrelated_cpu_return_stops',0)+1
   save();continue
  result['reached_symbols']+=names
  for matched,label,address in matches:
   if label in spawn_returns:
    event=spawn_returns[label];event.update(returned=True,status=reg('x0')&0xffffffff)
    try:event['return_value']=int.from_bytes(bytes(inferior.read_memory(event['return_storage'],4)),'little')
    except gdb.error:pass
    matched.delete();save()
  for matched,label,address in matches:
   if label not in target_main_points:continue
   target=target_main_points[label];assert item['cpsr']&0x1f==0
   if target['phase']=='dyld':
    header,argc=struct.unpack('<2Q',bytes(inferior.read_memory(item['sp'],16)))
    assert 0<argc<=128 and 0<header<1<<48 and header%4096==0
    target.update(phase='main',mach_header=header,argc=argc,main=header+spec['runtime_main']['entry_offset'])
    matched.delete();b=TargetEL0(target['main'],target['pid'],target['thread']);new=label+'_main';target_main_points[new]=target;points.append((b,new,target['main']))
    result.setdefault('runtime_main_entries',[]).append(target);save()
   elif target['phase']=='main':
    target['phase']='main_instruction_completion';matched.delete();b=TargetEL0(item['pc']+4,target['pid'],target['thread']);new=label+'_completed';target_main_points[new]=target;points.append((b,new,item['pc']+4))
   else:
    actual=bytes(inferior.read_memory(target['main'],16)).hex();assert actual==spec['runtime_main']['entry_bytes']
    target.update(phase='verified',entry_bytes=actual,first_instruction_completed=True,checkpoint_pc=item['pc'],checkpoint_sp=item['sp'])
    result['target_main_executed']=dict(target);matched.delete();save()
    runtime_after_main_threads.add(target['thread']);runtime_syscall_probe.enabled=True
  if '_runtime_thread_entry' in names:
   pending_user_threads.add(reg('x0'));runtime_syscall_probe.enabled=True
   layout=spec.get('user_abi',{}).get('process_snapshot')
   if layout:
    try:
     read=lambda a,n=8:int.from_bytes(bytes(inferior.read_memory(a,n)),'little')
     tro=read(reg('x0')+layout['thread']['fields']['ro']);proc=read(tro+layout['thread_ro']['fields']['proc'])
     abi=spec['user_abi'];event=dict(thread=reg('x0'),entry=reg('x1'),proc=proc,pid=read(proc+abi['proc']['pid'],4),comm=bytes(inferior.read_memory(proc+abi['proc']['comm'],16)).split(b'\0')[0].decode(errors='replace'))
     result.setdefault('runtime_thread_entries',[]).append(event);save()
     if spec.get('runtime_main') and event['pid'] in runtime_target_pids:
      class TargetEL0(gdb.Breakpoint):
       def __init__(self,address,pid,thread):
        super().__init__('*'+hex(address),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);self.target_pid=pid;self.target_thread=thread
       def stop(self):
        if reg('cpsr')&0x1f:return False
        # KPTI makes kernel pointers unreadable at EL0. TPIDR_EL1 itself is
        # the exact thread pointer written by this XNU's cswitch.s.
        return reg('TPIDR_EL1')==self.target_thread
      label='_runtime_target_dyld_'+str(len(target_main_points));target=dict(pid=event['pid'],thread=event['thread'],phase='dyld')
      b=TargetEL0(event['entry'],event['pid'],event['thread']);target_main_points[label]=target;points.append((b,label,event['entry']))

    except gdb.error:pass
  for event_name,argument_name in [('_runtime_write','write_args'),('_runtime_exit','exit_args'),('_runtime_execve','execve_args'),('_runtime_posix_spawn','posix_spawn_args')]:
   if event_name not in names:continue
   abi=spec['user_abi'];proc=reg('x0');arg=reg('x1')
   read=lambda address,size:int.from_bytes(bytes(inferior.read_memory(address,size)),'little')
   event=dict(kind=event_name.removeprefix('_runtime_'),pid=read(proc+abi['proc']['pid'],4),comm=bytes(inferior.read_memory(proc+abi['proc']['comm'],16)).split(b'\0')[0].decode(errors='replace'),scope='Original BSD handler entry; invocation, not successful return')
   event['arguments']={field:read(arg+layout['offset'],layout['bytes']) for field,layout in abi['bsd_arguments'][argument_name]['fields'].items()}
   try:
    if argument_name in ('execve_args','posix_spawn_args'):
     address=event['arguments'].get('path',event['arguments'].get('fname'));event['path']=bytes(inferior.read_memory(address,256)).split(b'\0')[0].decode(errors='replace')
    if argument_name=='write_args' and 0<event['arguments']['nbyte']<=4096:
     event['write_text']=bytes(inferior.read_memory(event['arguments']['cbuf'],event['arguments']['nbyte'])).decode(errors='replace')
   except gdb.error:pass
   result.setdefault('runtime_events',[]).append(event)
   if event_name=='_runtime_posix_spawn' and (event.get('path') in ('/usr/libexec/backboardd','/System/Library/CoreServices/SpringBoard.app/SpringBoard') or (spec.get('runtime_main') and Path(event.get('path','')).name==spec['runtime_main']['comm'])):
    if spec.get('runtime_main') and Path(event['path']).name==spec['runtime_main']['comm']:runtime_target_pids.add(event['pid'])
    label='_runtime_spawn_return_'+str(len(spawn_returns));entry_sp=reg('sp')
    class SpawnReturn(gdb.Breakpoint):
     def __init__(self,address,sp):
      super().__init__('*'+hex(address),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);self.entry_sp=sp
     def stop(self):return reg('sp')==self.entry_sp
    return_event=dict(pid=event['pid'],path=event['path'],entry_sp=entry_sp,return_storage=reg('x2'),returned=False)
    result.setdefault('target_spawn_results',[]).append(return_event);spawn_returns[label]=return_event
    b=SpawnReturn(item['lr'],entry_sp);points.append((b,label,item['lr']))
   save()

  if '_thread_setentrypoint' in names and spec.get('original_main'):
   entry=reg('x1');assert 0<entry<1<<48 and entry%4==0
   result['initial_user_entry']=dict(thread=reg('x0'),pc=entry,observed=False)
   b=gdb.Breakpoint('*'+hex(entry),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_initial_user_entry',entry));save()
  if '_initial_user_entry' in names:
   assert item['cpsr']&0x1f==0
   raw_stack=bytes(inferior.read_memory(item['sp'],16));header,argc=struct.unpack('<2Q',raw_stack)
   original=spec['original_main'];assert argc==1 and header%4096==0 and 0<header<1<<48
   # Main's header is demand-paged; reading it here must not force guest faults.
   # Verify it when LC_MAIN actually executes and the original loader has mapped it.
   main=header+original['entry_offset'];result['initial_user_entry']['observed']=True
   result['followed_main_entry']=dict(mach_header=header,startup_stack=item['sp'],startup_stack_bytes=raw_stack.hex(),entry_offset=original['entry_offset'],pc=main,observed=False)
   b=gdb.Breakpoint('*'+hex(main),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_original_launchd_main',main));save()
  if '_load_init_program' in names:
   result['init_proc']=reg('x0');save()
  if '_unix_syscall' in names and spec.get('user_abi'):
   abi=spec['user_abi'];proc=reg('x2');state=reg('x0')
   def readint(address,size):return int.from_bytes(bytes(inferior.read_memory(address,size)),'little')
   pid=readint(proc+abi['proc']['pid'],4)
   user={k:readint(state+v,4 if k in ('cpsr','esr') else 8) for k,v in abi['saved_state'].items() if k not in ('bytes','x')}
   user['syscall_number']=readint(state+abi['saved_state']['x']+16*8,8)
   comm=bytes(inferior.read_memory(proc+abi['proc']['comm'],16)).split(b'\0')[0].decode(errors='replace')
   live_initproc=readint(spec['data_symbols']['_initproc'],8)
   user.update(proc=proc,pid=pid,comm=comm,saved_state=state,thread=reg('x1'),same_init_proc=proc==result.get('init_proc'))
   user['same_live_init_proc']=proc==live_initproc
   user['arguments']=[readint(state+abi['saved_state']['x']+j*8,8) for j in range(8)]
   try:
    if user['syscall_number'] in (5,59,244,463):user['path']=bytes(inferior.read_memory(user['arguments'][1 if user['syscall_number'] in (244,463) else 0],256)).split(b'\0')[0].decode(errors='replace')
    if user['syscall_number']==4 and 0<user['arguments'][2]<=4096:user['write_text']=bytes(inferior.read_memory(user['arguments'][1],user['arguments'][2])).decode(errors='replace')
   except gdb.error:pass
   user['instruction_before_pc']=bytes(inferior.read_memory(user['pc']-4,4)).hex()
   result.setdefault('user_syscalls',[]).append(user)
   valid_el0=user['instruction_before_pc']=='011000d4' and user['cpsr']&0x1f==0 and user['esr']>>26==0x15 and 0<user['pc']<1<<48
   user['svc64_verified']=valid_el0
   verified=pid==1 and comm=='launchd' and user['same_live_init_proc'] and valid_el0
   result['pid1_el0_syscall_verified']=bool(verified or result.get('pid1_el0_syscall_verified'));save()
   if verified:result['verified_user_syscall_count']=result.get('verified_user_syscall_count',0)+1
   if spec['stop_at']=='_unix_syscall' and result.get('verified_user_syscall_count',0)<spec.get('user_syscall_count',1):continue
   if spec.get('runtime_observation') and result.get('original_launchd_main_executed'):
    if spec.get('runtime_process'):
     pending_user_threads.discard(user['thread'])
     if user['thread'] in runtime_after_main_threads:
      runtime_after_main_counts[user['thread']]=runtime_after_main_counts.get(user['thread'],0)+1
      user['after_target_main']=True;user['frames']=[];fp=user['fp']
      try:user['instruction_window']=bytes(inferior.read_memory(user['pc']-8,32)).hex()
      except gdb.error:pass
      for _ in range(24):
       if not fp or fp&15:break
       try:
        previous,ret=struct.unpack('<2Q',bytes(inferior.read_memory(fp,16)));user['frames'].append(dict(fp=fp,return_address=ret))
        if previous<=fp or previous-fp>1048576:break
        fp=previous
       except gdb.error:break
     runtime_syscall_probe.enabled=bool(pending_user_threads or any(runtime_after_main_counts.get(t,0)<64 for t in runtime_after_main_threads))
    result.setdefault('runtime_syscalls',[]).append(user)
    if verified:result['runtime_pid1_samples']=result.get('runtime_pid1_samples',0)+1
    process_target=spec.get('runtime_process')
    if process_target and comm==process_target and valid_el0:
     result['runtime_process_executed']=dict(pid=pid,comm=comm,pc=user['pc'],instruction_before_pc=user['instruction_before_pc'],scope='QEMU EL0 process execution only; no desktop claim')
     result['target_reached']=True;save();break
    if not process_target and result.get('runtime_pid1_samples',0)>=spec['user_syscall_count']:
     result['runtime_sample_completed']=True;result['target_reached']=True;save();break
  if '_original_launchd_main' in names:
   main=result['followed_main_entry'];assert item['cpsr']&0x1f==0 and item['x0']==1
   main.update(observed=True,cpsr=item['cpsr'],argc=item['x0'])
   # QEMU's PC breakpoint can stop before an instruction-page fault is resolved.
   # Continue through the real kernel fault, signature check and fetch; do not
   # read unmapped pages or claim execution merely from this first PC stop.
   for b,_,_ in matches:b.delete()
   b=gdb.Breakpoint('*'+hex(item['pc']+4),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_original_launchd_main_completed',item['pc']+4));save();continue
  if '_original_launchd_main_completed' in names:
   main=result['followed_main_entry'];original=spec['original_main']
   assert item['pc']==main['pc']+4 and item['cpsr']&0x1f==0
   actual=bytes(inferior.read_memory(main['pc'],16)).hex();assert actual==original['entry_bytes']
   try:
    header_bytes=bytes(inferior.read_memory(main['mach_header'],32)).hex()
    assert header_bytes==original['header'];main['mach_header_bytes']=header_bytes
   except gdb.MemoryError:main['header_page_not_resident_at_main']=True
   main.update(entry_bytes=actual,first_instruction_completed=True,checkpoint_pc=item['pc'],checkpoint_cpsr=item['cpsr'])
   result['original_launchd_main_executed']=True;save()
   if spec.get('runtime_observation'):
    address=spec['milestones']['_unix_syscall']
    pending_user_threads=set();runtime_after_main_threads=set();runtime_after_main_counts={}
    class RuntimeSyscall(gdb.Breakpoint):
     def stop(self):
      return not spec.get('runtime_process') or reg('x1') in pending_user_threads or (reg('x1') in runtime_after_main_threads and runtime_after_main_counts.get(reg('x1'),0)<64)
    b=RuntimeSyscall('*'+hex(address),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    runtime_syscall_probe=b
    points.append((b,'_unix_syscall',address))
    if spec.get('runtime_process'):
     assert spec['user_abi'].get('bsd_arguments')
     b.enabled=False
     for symbol,label in [('_thread_setentrypoint','_runtime_thread_entry'),('_write','_runtime_write'),('_exit','_runtime_exit'),('_execve','_runtime_execve'),('_posix_spawn','_runtime_posix_spawn')]:
      address=spec['milestones'][symbol]
      class RuntimeEvent(gdb.Breakpoint):
       def __init__(self,address,label):
        super().__init__('*'+hex(address),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True);self.label=label
       def stop(self):
        if self.label!='_runtime_write':return True
        try:
         abi=spec['user_abi'];args=abi['bsd_arguments']['write_args']['fields']
         fd=int.from_bytes(bytes(inferior.read_memory(reg('x1')+args['fd']['offset'],4)),'little')
         if fd in (1,2):return True
         comm=bytes(inferior.read_memory(reg('x0')+abi['proc']['comm'],16)).split(b'\0')[0]
         return comm in (b'launchd',b'usermanagerd')
        except gdb.error:return True
      event=RuntimeEvent(address,label)
      points.append((event,label,address))
     result['runtime_observation_policy']='Original BSD lifecycle/log handlers plus first SVC64 of each thread_setentrypoint; no all-syscall breakpoint while threads run normally'
    save()
  if '_fipspost_post' in names:
   result['source_crypto_post']=dict(mode=reg('x0')&0xffffffff,mach_header=reg('x1'),returned=False)
   b=gdb.Breakpoint('*'+hex(item['lr']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_source_crypto_post_return',item['lr']))
  if '_source_crypto_post_return' in names:
   result['source_crypto_post'].update(returned=True,status=reg('x0')&0xffffffff)
  if '_corecrypto_kext_start' in names:
   b=gdb.Breakpoint('*'+hex(item['lr']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_source_crypto_start_return',item['lr']))
  if '_source_crypto_start_return' in names:result['source_crypto_start_status']=reg('x0')&0xffffffff
  if any(name in names for name in ['_PE_init_iokit','_source_crypto_start_return','_platform_configure_return','_panic','_bsd_init']) and '_source_corecrypto14_status' in spec.get('data_symbols',{}):
   data=spec['data_symbols']
   provider=struct.unpack('<Q',bytes(inferior.read_memory(data['_g_crypto_funcs'],8)))[0]
   status=struct.unpack('<I',bytes(inferior.read_memory(data['_source_corecrypto14_status'],4)))[0]
   initialized=bytes(inferior.read_memory(data['_crypto_init'],1))[0]
   state=dict(at_symbols=names,status=status,crypto_init=initialized,functions=provider,initialized=status==0 and initialized==1 and provider!=0)
   result.setdefault('source_crypto_provider_states',[]).append(state);result['source_crypto_provider']=state
  if any(name in names for name in ['_raphael_cpu_start_return','_raphael_irq_return','_bsd_init','_panic']) and '_raphael_cpu_stage' in spec.get('data_symbols',{}):
   state={}
   wide=['timer_irqs','ipi_irqs','eois','dist_pa','redist_pa','frequency']
   for name,address in spec['data_symbols'].items():
    if name.startswith('_raphael_cpu_'):
     size=8 if name.removeprefix('_raphael_cpu_') in wide else 4
     state[name.removeprefix('_raphael_cpu_')]=int.from_bytes(bytes(inferior.read_memory(address,size)),'little')
   if '_source_pthread_status' in spec['data_symbols']:
    state['pthread_status']=int.from_bytes(bytes(inferior.read_memory(spec['data_symbols']['_source_pthread_status'],4)),'little')
    state['pthread_functions']=int.from_bytes(bytes(inferior.read_memory(spec['data_symbols']['_pthread_functions'],8)),'little')
   result.setdefault('cpu_states',[]).append(dict(at_symbols=names,state=state));result['cpu_state']=state
  if '__ZN14RaphaelBootCpu9interruptEv' in names:
   result.setdefault('irq_calls',[]).append(dict(return_target=item['lr'],entry_pc=item['pc']))
   b=gdb.Breakpoint('*'+hex(item['lr']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_raphael_irq_return',item['lr']))
  if '__ZN14RaphaelBootCpu5startEP9IOService' in names:
   result['cpu_start']=dict(entry_sp=item['sp'],instance=reg('x0'),provider=reg('x1'),return_target=item['lr'],returned_true=False)
   b=gdb.Breakpoint('*'+hex(item['lr']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_raphael_cpu_start_return',item['lr']))
  if '_raphael_cpu_start_return' in names:
   ok=reg('x0')==1 and item['pc']==result['cpu_start']['return_target']
   result['cpu_start'].update(returned_true=ok,return_value=reg('x0'))
   assert ok and result['cpu_state']['stage']==5 and result['cpu_state']['registered']==1,'Real boot CPU start did not succeed'
  if '__ZN13ArmDTPlatform9configureEP9IOService' in names:
   result['platform_configure']=dict(provider=reg('x1'),instance=reg('x0'),return_target=item['lr'],returned_true=False)
   b=gdb.Breakpoint('*'+hex(item['lr']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_platform_configure_return',item['lr']));save()
  if '_platform_configure_return' in names:
   counters={name:struct.unpack('<I',bytes(inferior.read_memory(address,4)))[0] for name,address in spec['data_symbols'].items() if name.startswith('_armdt_platform_')}
   ok=reg('x0')==1 and item['pc']==result['platform_configure']['return_target']
   result['platform_configure'].update(returned_true=ok,return_value=reg('x0'),counters=counters)
   assert ok,'Real IODT platform configure returned failure'
   for key in ['configured','cpu_count','bus_count','defaults_count','nvram_proxy']:
    assert counters['_armdt_platform_'+key]==1,(key,counters)
   save()
  if '_kalloc_type_apply_policy' in names:
   count=struct.unpack('<Q',bytes(inferior.read_memory(spec['data_symbols']['_num_kt_sizeclass'],8)))[0]
   assert 3<=count<=64
   pointers=[reg('x'+str(j)) for j in range(4)]
   policy=dict(count=count,budget=reg('x4')&0xffff,pointers=pointers)
   policy['zone_sizes']=list(struct.unpack('<'+'H'*count,bytes(inferior.read_memory(spec['data_symbols']['_kt_zone_cfg'],2*count))))
   policy['frequency']=[list(struct.unpack('<'+'H'*count,bytes(inferior.read_memory(address,2*count)))) for address in pointers[:2]]
   result['kalloc_policy']=policy
   b=gdb.Breakpoint('*'+hex(item['lr']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   points.append((b,'_kalloc_policy_return',item['lr']))
  if '_kalloc_policy_return' in names:
   policy=result['kalloc_policy'];count=policy['count']
   policy['allocated']=[list(struct.unpack('<'+'H'*count,bytes(inferior.read_memory(address,2*count)))) for address in policy['pointers'][2:]]
   policy['classes_exceeding_31']=[dict(index=j,bytes=policy['zone_sizes'][j],signature=policy['allocated'][0][j],type=policy['allocated'][1][j]) for j in range(count) if policy['frequency'][0][j] and sum(v[j] for v in policy['allocated'])>31]
   save()
  if '_arm_init' in names:
   assert item['sctlr_el1']&0x1005==0x1005
   result['arm_init_reached']=True;save()
  if '_native_owner_root_checkpoint' in names or '_native_owner_root_accepted_checkpoint' in names:
   result['owner_root']={name.removeprefix('_native_owner_root_'):int.from_bytes(bytes(inferior.read_memory(address,4)),'little',signed=name.endswith('autherr')) for name,address in spec['data_symbols'].items() if name.startswith('_native_owner_root_')}
  if '_raphael_data_seed_checkpoint' in names:
   data={}
   for name,address in spec['data_symbols'].items():
    if not name.startswith(('_native_owner_data_','_raphael_data_seed_')):continue
    size=8 if name.endswith(('_seed_size','_written','_readback')) else 4
    data[name]=int.from_bytes(bytes(inferior.read_memory(address,size)),'little',signed=name.endswith(('_status','_readonly')))
   result['emulator_data_seed']=data
   expected=spec['expected_data_seed']
   assert data['_native_owner_data_stage']==4 and data['_native_owner_data_status']==0 and data['_native_owner_data_readonly']==0,data
   assert data['_native_owner_data_seed_size']==expected['image_bytes'],data
   assert data['_raphael_data_seed_status']==reg('x0')==0,data
   assert data['_raphael_data_seed_entries']==expected['entries'],data
   assert data['_raphael_data_seed_written']==data['_raphael_data_seed_readback']==expected['bytes'],data
   result['data_seed_verified']=True;save()
  if '_native_apfs_probe_checkpoint' in names:
   result['apfs_registration']={name.removeprefix('_native_apfs_'):int.from_bytes(bytes(inferior.read_memory(address,8 if name.endswith('vfsops') else 4)),'little',signed=name.endswith('status')) for name,address in spec['data_symbols'].items() if name.startswith('_native_apfs_')}
  if '_native_virtio_read_checkpoint' in names:
   state={}
   for name,address in spec['data_symbols'].items():
    if not name.startswith('_native_virtio_'):continue
    key=name.removeprefix('_native_virtio_')
    size=32 if key=='first_sector_sha256' else 8 if key in ('sectors','mmio_physical','verified_blocks') else 4
    raw=bytes(inferior.read_memory(address,size))
    state[key]=raw.hex() if size==32 else int.from_bytes(raw,'little')
   result.setdefault('block_reads',[]).append(state)
   if spec.get('expected_os_block') and spec['stop_at']=='_native_virtio_read_checkpoint':
    expected=spec['expected_os_block']
    if state['sectors']!=expected['sectors']:save();continue
    assert state['ready']==1 and state['read_requests']>0 and state['read_failures']==0
    assert state['first_sector_sha256']==expected['first_sector_sha256']
    result['original_os_first_sector_read']=True
  irq_verified=result.get('cpu_state',{}).get('stage')==5 and result.get('cpu_state',{}).get('timer_irqs',0)>0 and result.get('cpu_state',{}).get('eois',0)>=result.get('cpu_state',{}).get('timer_irqs',0)
  if spec['stop_at'] in names and (spec['stop_at']!='_raphael_irq_return' or irq_verified):
   if spec.get('capture_memory'):
    result['target_memory']=dict(memory={f"{b['address']:x}:{b['bytes']:x}":bytes(inferior.read_memory(b['address'],b['bytes'])).hex() for b in spec['capture_memory']},system_registers={n:(reg('SCTLR') if n=='SCTLR_EL1' else reg(n)) for n in ['TCR_EL1','SCTLR_EL1','TTBR0_EL1','TTBR1_EL1']})
   result['target_reached']=True;save();break
  if any('panic' in n or 'ExceptionVector' in n for n in names):
   if spec.get('expected_data_seed'):
    result['data_at_failure']={name:int.from_bytes(bytes(inferior.read_memory(address,8 if name.endswith(('_seed_size','_written','_readback')) else 4)),'little',signed=name.endswith(('_status','_readonly','_lookup'))) for name,address in spec['data_symbols'].items() if name.startswith(('_native_owner_data_','_raphael_data_seed_'))}
    save()
   if '_panic' in names:
    try:
     result['panic_format']=bytes(inferior.read_memory(item['x0'],1024)).split(b'\0',1)[0].decode(errors='replace')
     stack=bytes(inferior.read_memory(item['sp'],256));words=list(struct.unpack('<32Q',stack))
     result['panic_stack_words']=words;result['panic_stack_strings']=[]
     def in_kernel(address):
      return any(base<=address<base+spec['window'] for base in [spec['virtual_base'],spec['physical_base']])
     for i,value in enumerate(words[:8]):
      if not in_kernel(value):continue
      try:
       raw=bytes(inferior.read_memory(value,512));end=raw.find(b'\0')
       if end<0:continue
       string=raw[:end]
       if string and all(32<=c<127 or c in (9,10,13) for c in string):
        result['panic_stack_strings'].append(dict(word=i,address=value,text=string.decode('ascii')))
      except gdb.error:pass
     result['panic_backtrace']=gdb.execute('bt 20',to_string=True)
     fp=item['fp'];frames=[]
     for _ in range(16):
      if not fp or fp&15 or not in_kernel(fp):break
      try:
       previous,ret=struct.unpack('<2Q',bytes(inferior.read_memory(fp,16)))
       frames.append(dict(fp=fp,return_address=ret))
       if previous<=fp or previous-fp>65536:break
       fp=previous
      except gdb.error:break
     result['panic_frame_chain']=frames
     result['panic_caller_disassembly']=gdb.execute('x/8i '+hex(item['lr']-16),to_string=True)
    except gdb.error:pass
   save();break
  for b,n,_ in matches:
   if n=='_native_virtio_read_checkpoint' and spec.get('expected_os_block'):continue
   if n=='_unix_syscall' and spec.get('runtime_observation') and result.get('original_launchd_main_executed'):continue
   if n.startswith('_runtime_'):continue
   if n!='__ZN14RaphaelBootCpu9interruptEv' or spec['stop_at']!='_raphael_irq_return':b.delete()
 capture_msgbuf()
 capture_processes()
 if '_raphael_display_stage' in spec.get('data_symbols',{}):
  result['display_state']={}
  for name,address in spec['data_symbols'].items():
   if name.startswith('_raphael_display_'):
    size=4 if name in ('_raphael_display_stage','_raphael_display_clients','_raphael_display_guard','_raphael_display_surface_status','_raphael_display_family_status','_raphael_display_meta_status','_raphael_display_hardware_stage','_raphael_display_video_status') else 8
    result['display_state'][name]=int.from_bytes(bytes(inferior.read_memory(address,size)),'little')
 result['completed']=True;save()
except Exception as error:
 import traceback
 result['failure']=type(error).__name__+': '+str(error);result['observer_traceback']=traceback.format_exc();save();raise
