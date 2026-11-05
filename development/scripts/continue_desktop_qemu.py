#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Continue a retained isolated QEMU, then leave it stopped for further work.
Never opens ADB, fastboot, block devices or an original disk for writing.
"""
import argparse,datetime as dt,json,os,signal,socket,subprocess,tempfile,time
from pathlib import Path
from entry_probe import ROOT

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--user-memory',type=Path,help='Bounded stopped read of previously observed user addresses');p.add_argument('--until-frame',action='store_true',help='Stop at first actual copied and retired frame, not desktop acceptance');p.add_argument('--sparse-data-abi',type=Path,help='Matching C++ DWARF sparse device reader; captures real allocated pages only');p.add_argument('--user-trace',type=Path,help='Read-only original user-code probes for already observed threads; no guest instruction writes');p.add_argument('--exception-process',help='Stop on the next actual XNU exception_triage for this exact process comm');p.add_argument('--capture-data',action='store_true');p.add_argument('--observer-source',type=Path,help='Explicit revised read-only observer; copied into this new continuation only');p.add_argument('--capture-timeout',type=int,default=60,help='Host-only final stopped capture budget; does not extend guest execution');p.add_argument('--run-seconds',type=int,default=0);a=p.parse_args()
 assert 0<=a.run_seconds<=1800 and 60<=a.capture_timeout<=600
 assert a.capture_timeout==60 or a.capture_data
 source=a.report.resolve();assert source.is_relative_to(ROOT/'artifacts/native-xnu-qemu')
 original=json.loads(source.read_text());retained=original['paused_emulator'];pid=retained['pid']
 command=Path('/proc')/str(pid)/'cmdline';assert command.exists()
 args=command.read_bytes().split(b'\0');assert b'qemu-system-aarch64' in args[0] and any(str(source.parent).encode() in x for x in args)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-live-'),dir=ROOT/'artifacts/native-xnu-qemu'))
 client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);client.settimeout(10);client.connect(retained['qmp_socket']);stream=client.makefile('rwb',buffering=0);assert 'QMP' in json.loads(stream.readline())
 def qmp(name,arguments=None):
  stream.write((json.dumps(dict(execute=name,**({'arguments':arguments} if arguments else {})))+'\r\n').encode())
  while True:
   answer=json.loads(stream.readline())
   if 'error' in answer:raise RuntimeError(answer['error'])
   if 'return' in answer:return answer['return']
 qmp('qmp_capabilities');qmp('stop');assert not qmp('query-status')['running']
 spec=json.loads((source.parent/'debugger-spec.json').read_text());spec['output']=str(out/'debugger-observation.json');spec['capture_data_after']=1 if a.capture_data else 0
 if a.exception_process:
  assert 0<len(a.exception_process.encode('ascii'))<=16
  names=[line.split() for line in (source.parent/'symbols.txt').read_text().splitlines()]
  matches=[int(row[0],16) for row in names if len(row)==3 and row[2]=='_exception_triage'];assert len(matches)==1
  spec['exception_process']=a.exception_process;spec['exception_address']=matches[0]
 if a.user_memory:
  memory=json.loads(a.user_memory.read_text());assert len(memory['requests'])<=16 and 0<len(memory['process'].encode('ascii'))<=16
  for request in memory['requests']:assert 0<request['address']<1<<40 and 0<request['bytes']<=4096
  spec['user_memory']=memory
 if a.sparse_data_abi:
  sparse=json.loads(a.sparse_data_abi.read_text());assert sparse['candidate_sha256']==original['kernel_sha256'] and sparse['guest_modified'] is False
  spec['sparse_data_abi']=sparse
 if a.until_frame:
  rows=[line.split() for line in (source.parent/'symbols.txt').read_text().splitlines()]
  addresses=[int(row[0],16) for row in rows if len(row)==3 and row[2]=='_raphael_display_frame_checkpoint'];assert len(addresses)==1
  spec['frame_address']=addresses[0]
 if a.user_trace:
  trace=json.loads(a.user_trace.read_text());assert trace['original_files_modified'] is False and 0<len(trace['sites'])<=12
  assert 0<len(trace['process'].encode('ascii'))<=16
  for site in trace['sites']:
   assert 0<site['address']<1<<40 and len(bytes.fromhex(site['prefix']))==16 and 1<=site.get('max_hits',1)<=16
  spec['user_trace']=trace
 (out/'debugger-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
 observer_source=a.observer_source.resolve() if a.observer_source else source.parent/'observer.py'
 assert observer_source.is_relative_to(ROOT)
 prefix=observer_source.read_text().split("try:\n gdb.execute('set pagination off')")[0]
 assert 'def capture_processes()' in prefix and 'target remote' not in prefix
 code="SPEC="+repr(str(out/'debugger-spec.json'))+'\n'+prefix+r"""
gdb.execute('set pagination off');gdb.execute('set confirm off');gdb.execute('set architecture aarch64')
gdb.execute('target remote '+spec['socket']);inferior=gdb.selected_inferior()
def kernel_access():
 if reg('cpsr')&31:return
 point=gdb.Breakpoint('*'+hex(spec['milestones']['_unix_syscall']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
 gdb.execute('continue');assert reg('cpsr')&31;point.delete()
def collect(label):
 kernel_access();snapshot(label);capture_processes();capture_msgbuf();result.setdefault('progress_samples',[]).append(dict(label=label,process_snapshot=result['process_snapshot']))
 result['display_state']={}
 for name,address in spec['data_symbols'].items():
  if name.startswith('_raphael_display_'):
   size=4 if name in ('_raphael_display_stage','_raphael_display_clients','_raphael_display_guard','_raphael_display_surface_status','_raphael_display_family_status','_raphael_display_meta_status','_raphael_display_hardware_stage','_raphael_display_video_status') else 8
   result['display_state'][name]=int.from_bytes(bytes(inferior.read_memory(address,size)),'little')
 result['offline_keystore_state']={name:int.from_bytes(bytes(inferior.read_memory(address,8)),'little') for name,address in spec['data_symbols'].items() if name.startswith('_raphael_offline_aks_')}
 result['ram_block_state']={name:int.from_bytes(bytes(inferior.read_memory(address,4 if name in ('_native_ram_block_ready','_native_ram_block_sparse') else 8)),'little') for name,address in spec['data_symbols'].items() if name.startswith('_native_ram_block_') and name!='_native_ram_block_seed_sha256'}
 result['kernel_memory_state']={name:int.from_bytes(bytes(inferior.read_memory(spec['data_symbols'][name],8)),'little') for name in ('_gPhysBase','_gVirtBase','_real_phys_size') if name in spec['data_symbols']}
 save()
try:
 collect('attached')
 if spec.get('user_memory'):
  memory=spec['user_memory'];processes=[p for p in result['process_snapshot']['processes'] if p['comm']==memory['process'] and p['pid']==memory['pid']]
  assert len(processes)==1,'Previously observed process no longer exists'
  reader,mapping=task_user_reader(processes[0]['task'],spec['user_abi']['process_snapshot']);result['user_memory']=[]
  for request in memory['requests']:
   result['user_memory'].append(dict(**request,content=reader(request['address'],request['bytes']).hex(),mapping=mapping))
  save()
 if spec.get('sparse_data_abi'):
  sparse_abi=spec['sparse_data_abi']
  class SparseDevice(gdb.Breakpoint):
   def stop(self):
    instance=reg('x0')
    if not reg('cpsr')&31:return False
    if int.from_bytes(bytes(inferior.read_memory(instance,8)),'little')!=sparse_abi['vtable']:return False
    result['sparse_data_instance']=instance;self.enabled=False;save();return False
  sparse_probe=SparseDevice('*'+hex(sparse_abi['io_entry']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
 if spec.get('user_trace'):
  trace=spec['user_trace'];processes=[p for p in result['process_snapshot']['processes'] if p['comm']==trace['process']]
  assert len(processes)<=1,'Trace process name is not unique'
  candidates=processes or [p for p in result['process_snapshot']['processes'] if p['comm']=='launchd' and p.get('shared_region')]
  assert len(candidates)==1,'An observed original shared region is required before installing probes'
  seed=candidates[0];slide=seed['shared_region']['slide']
  layout=spec['user_abi']['process_snapshot'];field=lambda kind,name:layout[kind]['fields'][name]
  read_virtual=lambda address,size=8:int.from_bytes(bytes(inferior.read_memory(address,size)),'little')
  kernel_phys=read_virtual(spec['data_symbols']['_gPhysBase']);kernel_virt=read_virtual(spec['data_symbols']['_gVirtBase']);kernel_bytes=read_virtual(spec['data_symbols']['_real_phys_size'])
  kernel_aliases=[]
  for index in range(8):
   pa,va,size=struct.unpack('<3Q',bytes(inferior.read_memory(spec['data_symbols']['_ptov_table']+index*24,24)))
   if not size:break
   kernel_aliases.append((pa,va,size))
  kernel_tcr=reg('TCR_EL1');kernel_ttbr=reg('TTBR1_EL1')
  kernel_va_bits=64-((kernel_tcr>>16)&63);kernel_root_level=4-((kernel_va_bits-12+8)//9)
  assert (kernel_tcr>>30)&3==2 and 12<kernel_va_bits<=48 and 0<=kernel_root_level<=3,'Trace supports the actual 4KiB kernel translation geometry only'
  kernel_root=kernel_ttbr&0x0000fffffffff000
  def read_word(address,size=8):
   # EL0 KPTI can hide kernel VAs. Walk the real EL1 TTBR1 saved while
   # stopped in the kernel, using host-debug physical reads only.
   assert 'OK' in gdb.execute('maintenance packet Qqemu.PhyMemMode:1',to_string=True)
   try:
    data=bytearray()
    while len(data)<size:
     va=address+len(data);table=kernel_root;physical=None
     for level in range(kernel_root_level,4):
      shift=12+9*(3-level);index_bits=min(9,kernel_va_bits-shift)
      assert index_bits>0 and kernel_phys<=table and table+4096<=kernel_phys+kernel_bytes,'Kernel table outside observed owned memory'
      entry=int.from_bytes(bytes(inferior.read_memory(table+((va>>shift)&((1<<index_bits)-1))*8,8)),'little')
      assert entry&1,'Invalid original kernel translation descriptor'
      if level==3 or entry&3==1:
       assert level in (1,2,3) and (entry&3)==(3 if level==3 else 1),'Unsupported original kernel translation descriptor'
       physical=(entry&0x0000fffffffff000&~((1<<shift)-1))|(va&((1<<shift)-1));break
      assert entry&3==3;table=entry&0x0000fffffffff000
     count=min(size-len(data),4096-(va&4095))
     assert physical is not None and kernel_phys<=physical and physical+count<=kernel_phys+kernel_bytes,'Kernel trace byte outside observed owned memory'
     data.extend(bytes(inferior.read_memory(physical,count)))
    return int.from_bytes(data,'little')
   finally:assert 'OK' in gdb.execute('maintenance packet Qqemu.PhyMemMode:0',to_string=True)
  result['user_trace_kernel_reader']=dict(physical_base=kernel_phys,virtual_base=kernel_virt,bytes=kernel_bytes,aliases=kernel_aliases,tcr=kernel_tcr,ttbr1=kernel_ttbr,root_level=kernel_root_level,guest_modified=False)
  result['user_trace_scope']=dict(process=trace['process'],slide=slide,slide_source_pid=seed['pid'],scope='Every actual original-code hit checks current thread_ro.proc identity and its task shared-region slide; includes newly created threads/process instances')
  result['user_trace_events']=[]
  class UserTrace(gdb.Breakpoint):
   def __init__(self,site):
    self.site=site;self.hits=0
    super().__init__('*'+hex(site['address']+slide),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
   def stop(self):
    if reg('cpsr')&31:return False
    try:
     thread=reg('TPIDR_EL1');ro=read_word(thread+field('thread','ro'));proc=read_word(ro+field('thread_ro','proc'))
     if not proc:return False
     comm=read_word(proc+spec['user_abi']['proc']['comm'],16).to_bytes(16,'little').split(b'\0')[0].decode(errors='replace')
     if comm!=trace['process']:return False
     pid=read_word(proc+spec['user_abi']['proc']['pid'],4)
     task=read_word(ro+field('thread_ro','task'));shared=read_word(task+field('task','shared_region'))
     assert shared and read_word(shared+field('shared_region','slide'),4)==slide,'Actual process cache slide differs from probe region'
     prefix=bytes(inferior.read_memory(reg('pc'),16)).hex();assert prefix==self.site['prefix'],'Original user instruction prefix differs'
     event=dict(site=self.site['name'],pid=pid,process=comm,thread=thread,pc=reg('pc'),cpsr=reg('cpsr'),arguments=[reg('x'+str(i)) for i in range(8)],lr=reg('x30'),original_instruction_match=True)
     event['memory']=[]
     for request in self.site.get('memory',[]):
      address=reg('x'+str(request['register']))+request.get('offset',0);size=request['bytes'];assert 0<size<=256
      try:event['memory'].append(dict(address=address,bytes=bytes(inferior.read_memory(address,size)).hex()))
      except Exception as error:event['memory'].append(dict(address=address,error=str(error)))
     result['user_trace_events'].append(event);self.hits+=1
     if self.hits>=self.site.get('max_hits',1):self.enabled=False
     save();return (bool(trace.get('stop_after_all_hits')) and all(not probe.enabled for probe in user_probes)) or (bool(trace.get('stop_after_sites')) and set(trace['stop_after_sites'])<=set(e['site'] for e in result['user_trace_events']))
    except Exception as error:
     import traceback
     result['failure']=type(error).__name__+': '+str(error);result['observer_traceback']=traceback.format_exc();save();return True
  user_probes=[UserTrace(site) for site in trace['sites']]
 if spec.get('frame_address'):
  class ActualFrame(gdb.Breakpoint):
   def stop(self):
    read=lambda name:int.from_bytes(bytes(inferior.read_memory(spec['data_symbols'][name],8)),'little')
    return read('_raphael_display_frames')>0 and read('_raphael_display_retired')>0
  frame_probe=ActualFrame('*'+hex(spec['frame_address']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
 if spec.get('exception_process'):
  class SelectedException(gdb.Breakpoint):
   def stop(self):
    layout=spec['user_abi']['process_snapshot'];read=lambda a:int.from_bytes(bytes(inferior.read_memory(a,8)),'little')
    thread=reg('TPIDR_EL1');ro=read(thread+layout['thread']['fields']['ro']);proc=read(ro+layout['thread_ro']['fields']['proc'])
    comm=bytes(inferior.read_memory(proc+spec['user_abi']['proc']['comm'],16)).split(b'\0')[0].decode(errors='replace')
    return comm==spec['exception_process']
  selected=SelectedException('*'+hex(spec['exception_address']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
 if RUN_SECONDS:
  result['continuing_guest']=True;save();gdb.execute('continue')
  if spec.get('exception_address')==reg('pc'):
   count=reg('x2');assert 0<count<=2
   result['captured_exception']=dict(exception=reg('x0'),codes=list(struct.unpack('<'+'Q'*count,bytes(inferior.read_memory(reg('x1'),count*8)))),thread=reg('TPIDR_EL1'),process=spec['exception_process'])
   selected.delete()
  if spec.get('frame_address')==reg('pc'):result['actual_frame_checkpoint_reached']=True
  if result.get('failure'):raise RuntimeError(result['failure'])
  for probe in locals().get('user_probes',[]):probe.enabled=False
  collect('after-continue')
 observer_started-=1;capture_data_once()
 if result.get('failure'):raise RuntimeError(result['failure'])
 result['completed']=True;save()
except Exception as error:
 import traceback
 if not result.get('failure'):result['failure']=type(error).__name__+': '+str(error);result['observer_traceback']=traceback.format_exc()
 save();raise
""".replace('RUN_SECONDS',str(a.run_seconds))
 compile(code,'live-observer.py','exec')
 (out/'observer.py').write_text(code);gdbfile=out/'debug.gdb';gdbfile.write_text('python\nexec(compile(open('+repr(str(out/'observer.py'))+').read(),"live-observer.py","exec"))\nend\nquit\n')
 report=dict(source_report=str(source.relative_to(ROOT)),observer_source=str(observer_source.relative_to(ROOT)),artifact_directory=str(out.relative_to(ROOT)),paused_emulator=retained,run_seconds_requested=a.run_seconds,capture_timeout_seconds=a.capture_timeout,handset_executed=False,desktop_verified=False)
 try:
  with (out/'gdb.log').open('w') as log:
   proc=subprocess.Popen(['gdb-multiarch','-q','-nx','-batch','-x',str(gdbfile)],stdout=log,stderr=subprocess.STDOUT)
   deadline=time.monotonic()+60
   while proc.poll() is None:
    observation=out/'debugger-observation.json';current=json.loads(observation.read_text()) if observation.exists() else {}
    if current.get('continuing_guest'):break
    if not a.run_seconds and current.get('completed'):break
    if time.monotonic()>deadline:raise TimeoutError('Initial stopped snapshot did not complete')
    time.sleep(0.25)
   if a.run_seconds and proc.poll() is None:
    try:proc.wait(timeout=a.run_seconds)
    except subprocess.TimeoutExpired:proc.send_signal(signal.SIGINT)
   try:proc.wait(timeout=a.capture_timeout if a.capture_data else 20)
   except subprocess.TimeoutExpired:proc.kill();proc.wait();raise TimeoutError('Final observer capture did not complete')
  report['debugger_returncode']=proc.returncode
  if proc.returncode:report['failure']='GDB observer exited '+str(proc.returncode)+'; see gdb.log'
  observation=out/'debugger-observation.json'
  if observation.exists():
   d=json.loads(observation.read_text());report['observer_completed']=d.get('completed',False)
   if d.get('failure'):report['failure']=d['failure']
   elif not report['observer_completed']:report['failure']=report.get('failure') or 'Observer did not complete'
   if a.capture_data and 'data_ram_snapshot' not in d:
    report['failure']=report.get('failure') or d.get('data_ram_snapshot_error') or d.get('data_ram_snapshot_unavailable') or 'Requested Data snapshot absent'
  else:report['failure']=report.get('failure') or 'Observer output absent'
 except Exception as error:
  report['failure']=type(error).__name__+': '+str(error)
  raise
 finally:
  qmp('stop');report['paused_emulator']['status']=qmp('query-status');assert not report['paused_emulator']['status']['running']
  screen=out/'qemu-screen.png';qmp('screendump',dict(filename=str(screen),format='png'));client.close()
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
