#!/usr/bin/env python3
"""Derive early-C checkpoint and recovery ranges from the frozen Mach-O."""
import struct,zlib
from entry_probe import sha
MAGIC=int.from_bytes(b'RPHEAR01','little')
GUID='3d7c6c2f-3c93-41f6-8a43-e63fe3ea8078'
HEADER='magic version checkpoint opcode return_va frame_bytes const_args boot_args args_bytes count backup_bytes delta_capacity flags reserved0 reserved1 reserved2'.split()
FIELDS='version status error checkpoint_va return_va const_args_va original_args_pa args_bytes backup_base backup_bytes delta_bytes delta_words delta_overflow saved_ranges restored_ranges args_copy_ok'.split()
RANGE='virtual physical bytes crc_before crc_after crc_restored changed_words backup_ok'.split()

def image(kernel):
 commands=struct.unpack_from('<I',kernel,16)[0];at=32;segments=[];symtab=None
 for _ in range(commands):
  cmd,n=struct.unpack_from('<2I',kernel,at)
  if cmd==0x19:
   name=kernel[at+8:at+24].rstrip(b'\0').decode();va,size,offset,data=struct.unpack_from('<4Q',kernel,at+24)
   if size:segments.append(dict(name=name,virtual=va,bytes=size,offset=offset,file_bytes=data,protection=struct.unpack_from('<I',kernel,at+60)[0]))
  if cmd==2:symtab=struct.unpack_from('<4I',kernel,at+8)
  at+=n
 assert symtab;symoff,count,stroff,strbytes=symtab;symbols={}
 for i in range(count):
  string,typ,sect,desc,value=struct.unpack_from('<IBBHQ',kernel,symoff+i*16)
  if string>=strbytes or not typ&0xe:continue
  end=kernel.index(0,stroff+string,stroff+strbytes);symbols[kernel[stroff+string:end].decode()]=value
 return segments,symbols

def make_policy(kernel,mmu,pmap=False,platform=False,platform_stop="startup"):
 assert not platform or pmap
 segments,symbols=image(kernel)
 def read(v,n):
  hits=[s for s in segments if s['virtual']<=v and v+n<=s['virtual']+s['file_bytes']];assert len(hits)==1
  s=hits[0];at=s['offset']+v-s['virtual'];return kernel[at:at+n]
 points={'startup':('_machine_startup',0),'console':('_PE_create_console',1),'idle':('_cpu_machine_idle_init',2),'timebase':('_cpu_timebase_init',3),'cpu':('_PE_init_cpu',4),'serial':('_serial_init',5),'bootstrap':('_kernel_bootstrap',6),'vm-ready':('_sched_init',7),'vm-entry':('_vm_mem_bootstrap',8),'vm-memory':('_atm_init',9),'load-context':('_load_context',10),'first-thread':('_kernel_bootstrap_thread',11),'iokit-entry':('_PE_init_iokit',12),'iokit-return':('_PE_init_iokit',13),'irq-enabled':('_ml_set_interrupts_enabled',14),'irq-compiled':('_raphael_native_irq_checkpoint',15),'pre-lockdown':('_raphael_native_prepare_checkpoint',16),'post-lockdown':('_raphael_native_lockdown_checkpoint',17),'iokit-matched':('_raphael_native_matched_checkpoint',18),'bsd-scheduling':('_raphael_native_bsd_checkpoint',19),'root-observer':('_raphael_native_root_checkpoint',20)}
 assert platform_stop in points;target_name,target_id=points[platform_stop]
 arm=symbols['_arm_init'];target=symbols[target_name if platform else '_PE_consistent_debug_inherit' if pmap else '_arm_vm_init'];opcode=struct.unpack('<I',read(target,4))[0];assert (platform and opcode!=0) or opcode==(0xd100c3ff if pmap else 0xd10643ff)
 prologue=struct.unpack('<I',read(arm,4))[0];assert prologue==0xd10343ff;frame=(prologue>>10)&4095;assert frame==208
 code=read(arm,0x1000);calls=[]
 for at in range(0,len(code),4):
  w=struct.unpack_from('<I',code,at)[0]
  if w&0xfc000000==0x94000000:
   imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm
   if arm+at+imm*4==(symbols['_machine_startup'] if platform and target_id>=6 else target):calls.append(arm+at+4)
 if platform and target_id>=6:
  # This linked startup has a balanced frame and a tail B, so kernel_bootstrap
  # inherits the original arm_init return address and its 208-byte frame.
  start=symbols['_machine_startup'];words=struct.unpack('<5I',read(start,20))
  assert words[0]==0xa9bf7bfd and words[1]==0x910003fd and words[3]==0xa8c17bfd
  def branch_target(pc,word,opcode):
   assert word&0xfc000000==opcode
   imm=word&0x3ffffff
   if imm&(1<<25):imm-=1<<26
   return pc+imm*4
  assert branch_target(start+8,words[2],0x94000000)==symbols['_machine_conf']
  assert branch_target(start+16,words[4],0x14000000)==symbols['_kernel_bootstrap']
 assert len(calls)==1
 if platform and target_id in (7,8,9,10):
  # The original kernel_bootstrap frame is live at both call entries.
  # vm-entry precedes VM initialization; vm-memory follows vm_mem_bootstrap;
  # vm-ready also follows original STARTUP_SUB_OSLOG callbacks.
  # load-context is the last original call before switching thread context.
  start=symbols['_kernel_bootstrap'];body=read(start,0x800)
  first=struct.unpack_from('<I',body)[0];assert first==0xd10183ff
  returns=[]
  for at in range(0,len(body),4):
   w=struct.unpack_from('<I',body,at)[0]
   if w&0xfc000000==0x94000000 and branch_target(start+at,w,0x94000000)==target:returns.append(start+at+4)
  assert len(returns)==1
  subsp=[w for (w,) in struct.iter_unpack('<I',body[:returns[0]-start]) if w&0xffc003ff==0xd10003ff]
  assert subsp==[first],subsp
  calls=returns;frame+=(first>>10)&4095
 thread_policy=None
 if platform and 11<=target_id<=20:
  # Match the linked stack producer and consumer; these are software offsets,
  # never physical board parameters. No stale bootstrap-stack frame applies.
  cont=symbols['_Call_continuation'];words=struct.unpack('<19I',read(cont,76))
  assert words[0]==0xd538d084 and words[1]&0xffc003ff==0x91000086
  top_offset=(words[1]>>10)&4095
  assert words[2:5]==(0xf94000c5,0x910000bf,0xd280001d)
  assert words[8:12]==(0xaa0003f4,0xaa0103f5,0xaa0203f6,0xb4000063)
  assert words[14:18]==(0xaa1503e0,0xaa1603e1,0xd63f0280,0xd538d080)
  attach=symbols['_machine_stack_attach'];aw=struct.unpack('<17I',read(attach,68))
  assert aw[0]&0xffc003ff==0xf9000001
  base_offset=((aw[0]>>10)&4095)*8
  assert aw[5]&0xffc003ff==0xd1000109
  context_bytes=(aw[5]>>10)&4095
  assert aw[6]==0xf9000009|((top_offset//8)<<10)
  assert aw[4]==0x8b080028 and aw[8]==0xd538425f and aw[10]==0xf9003109
  # ADRP + LDR is the actual runtime kernel_stack_size global read.
  adrp=aw[1];assert adrp&0x9f00001f==0x90000008
  imm=((adrp>>5)&0x7ffff)<<2|((adrp>>29)&3)
  if imm&(1<<20):imm-=1<<21
  assert aw[3]&0xffc003ff==0xf9400108
  size_va=((attach+4)&~4095)+(imm<<12)+(((aw[3]>>10)&4095)*8)
  assert size_va==symbols['_kernel_stack_size'] and context_bytes==208
  calls=[cont+17*4];frame=0
  if 12<=target_id<=19:
   caller=symbols['_kernel_bootstrap_thread'];body=read(caller,0x800);first=struct.unpack_from('<I',body)[0]
   assert first==0xd10143ff
   returns=[caller+i+4 for i in range(0,len(body),4) if struct.unpack_from('<I',body,i)[0]&0xfc000000==0x94000000 and branch_target(caller+i,struct.unpack_from('<I',body,i)[0],0x94000000)==(symbols['_bsd_init'] if target_id==19 else target)]
   assert len(returns)==1
   assert [w for (w,) in struct.iter_unpack('<I',body[:returns[0]-caller]) if w&0xffc003ff==0xd10003ff]==[first]
   calls=returns;frame=(first>>10)&4095
   if target_id==19:
    caller=symbols['_bsd_init'];body=read(caller,0x1800);first=struct.unpack_from('<I',body)[0]
    assert first==0xd10483ff
    returns=[caller+i+4 for i in range(0,len(body),4) if struct.unpack_from('<I',body,i)[0]&0xfc000000==0x94000000 and branch_target(caller+i,struct.unpack_from('<I',body,i)[0],0x94000000)==target]
    assert len(returns)==1
    before=body[:returns[0]-caller]
    assert [w for (w,) in struct.iter_unpack('<I',before) if w&0xffc003ff==0xd10003ff]==[first]
    # The diagnostic yields through real IOSleep, after bsd_bufferinit and
    # before the original 30-second RTC discovery. Never bypass that discovery.
    assert struct.unpack_from('<2I',before,len(before)-12)[0]==0x52800c80
    assert branch_target(caller+len(before)-8,struct.unpack_from('<I',before,len(before)-8)[0],0x94000000)==symbols['_IOSleep']
    calls=returns;frame+=(first>>10)&4095
   if target_id in (13,14):
    target=returns[0];opcode=struct.unpack('<I',read(target,4))[0];target_name=target_name+' return'


  thread_policy=dict(base_offset=base_offset,top_offset=top_offset,size_va=size_va,context_bytes=context_bytes)
 if platform and target_id==20:
  caller=symbols['_raphael_native_root_observer'];body=read(caller,0x800);first=struct.unpack_from('<I',body)[0]
  if first&0xffc003ff==0xd10003ff:frame=(first>>10)&4095
  else:
   assert first&0xffc003e0==0xa98003e0,'Observer must start with a 64-bit stack-pair allocation'
   immediate=(first>>15)&127;immediate=immediate-128 if immediate&64 else immediate;frame=-immediate*8
  assert 16<=frame<=256 and frame%16==0
  returns=[caller+i+4 for i in range(0,len(body),4) if struct.unpack_from('<I',body,i)[0]&0xfc000000==0x94000000 and branch_target(caller+i,struct.unpack_from('<I',body,i)[0],0x94000000)==target]
  assert len(returns)==1
  before=body[:returns[0]-caller]
  assert [i for i,(w,) in enumerate(struct.iter_unpack('<I',before)) if w&0xffc003ff==0xd10003ff or w&0xffc003e0==0xa98003e0]==[0]
  calls=returns
 # Actual linked sizeof(boot_args) copy ABI and adjacent BootArgs symbol.
 argsbytes=symbols['_BootArgs']-symbols['_const_boot_args'];assert argsbytes==0x480
 ranges=[s for s in segments if s['name'] in ['__DATA_CONST','__DATA','__BOOTDATA']];assert [s['name'] for s in ranges]==['__DATA_CONST','__DATA','__BOOTDATA']
 if platform and target_id>=17:
  reclaim=[s for s in segments if s['name'] in ('__KLD','__KLDDATA')]
  assert [s['name'] for s in reclaim]==['__KLD','__KLDDATA'] and all(s['bytes']==16384 for s in reclaim)
  ranges+=reclaim
 imported=[s for s in segments if s['name'] in ('__PRELINK_INFO','__PRELINK_DATA','__PLK_DATA_CONST')] if platform and target_id>=17 else []
 if imported:assert [s['name'] for s in imported]==['__PRELINK_INFO','__PRELINK_DATA','__PLK_DATA_CONST'];ranges+=imported
 backup=sum(s['bytes'] for s in ranges);assert backup<=(12 if imported else 3)*1048576 and all(s['virtual']%4096==s['bytes']%4096==0 for s in ranges)
 version=9 if imported else 8 if target_id>=17 and platform else 7 if target_id>=15 and platform else 6 if target_id==14 and platform else 5 if thread_policy else 4 if platform and target_id in (7,8,9,10) else 3 if platform else 2 if pmap else 1
 values=[MAGIC,version,target,opcode,calls[0],frame,symbols['_const_boot_args'],symbols['_BootArgs'],argsbytes,len(ranges),backup,0x100000 if version>=9 else 0x80000 if version>=4 else 0x40000,version,symbols['_panic'] if platform else 0,symbols['_panic_with_options'] if platform else 0,target_id if platform else 0]
 exception_policy=None
 if version>=8:
  replace=symbols['_arm64_replace_bootstack'];code=struct.unpack('<12I',read(replace,48))
  assert code[:3]==(0xa9bf7bfd,0x910003fd,0xf9401000) and code[5:8]==(0xd50041bf,0x9100001f,0xd50040bf)
  field=((code[2]>>10)&4095)*8;assert field==32
  cpu_data=symbols['_percpu_slot_cpu_data']
  finalize=symbols['_arm_vm_prot_finalize'];body=read(finalize,0x180)
  # Validate the actual ADRP/ADD/MOV argument before the original allocator.
  matches=[]
  for offset in range(12,len(body),4):
   w=struct.unpack_from('<I',body,offset)[0]
   if w&0xfc000000==0x94000000 and branch_target(finalize+offset,w,0x94000000)==symbols['_cpu_stack_alloc']:
    adrp,add,mov=struct.unpack_from('<3I',body,offset-12)
    assert adrp&0x9f00001f==0x90000013 and add&0xffc003ff==0x91000273 and mov==0xaa1303e0
    imm=((adrp>>5)&0x7ffff)<<2|((adrp>>29)&3)
    if imm&(1<<20):imm-=1<<21
    actual=((finalize+offset-12)&~4095)+(imm<<12)+((add>>10)&4095)
    assert actual==cpu_data;matches.append(actual)
  assert matches==[cpu_data]
  stack_bytes=symbols['_excepstack_top']-symbols['_excepstack'];assert stack_bytes==16384
  exception_policy=dict(field_va=cpu_data+field,bytes=stack_bytes)
  values[13]=exception_policy['field_va'];values[14]=stack_bytes
 policy=dict(zip(HEADER,values));raw=struct.pack('<16Q',*values);metadata=[]
 for s in ranges:
  original=kernel[s['offset']:s['offset']+s['file_bytes']]+bytes(s['bytes']-s['file_bytes']);crc=zlib.crc32(original)
  raw+=struct.pack('<4Q',s['virtual'],s['bytes'],s['file_bytes'],crc);metadata.append(dict(s,original_crc32=crc))
 if thread_policy:raw+=struct.pack('<4Q',*thread_policy.values())
 compiled=None
 if target_id>=15 and platform:
  assert opcode==0xd42a6a20
  unmask=symbols['_ml_set_interrupts_enabled'];first=struct.unpack('<I',read(unmask,4))[0]
  impl=branch_target(unmask,first,0x14000000)
  assert struct.pack('<I',0xd50347ff) in read(impl,0x400),'Expected original DAIFClr #7 implementation'
  compiled=dict(config=symbols['_raphael_native_diag_config'],relay=symbols['_raphael_native_relay'],body=symbols['_raphael_native_relayBody'],bytes=symbols['_raphael_native_relayEnd']-symbols['_raphael_native_relay'])
  assert 0<compiled['bytes']<=2048 and read(compiled['config'],8)==bytes.fromhex('5250484443464731')
  # Kernel synchronous BRKs reach the compiled bridge. User exceptions must
  # remain on the original XNU path; all checks inspect already linked text.
  for slot in (0,4):
   at=mmu['policy']['high_vectors']+slot*128
   words=struct.unpack('<8I',read(at,32))
   if words[0]==0xd5385212:
    assert words[1:5]==(0xd35afE52,0xf100f25f,0x54000061,0xd2800011|(slot<<5))
    assert branch_target(at+20,words[5],0x14000000)==compiled['relay']
   else:
    assert words[0]==0xd2800011|(slot<<5)
    assert branch_target(at+4,words[1],0x14000000)==compiled['relay']
  at=mmu['policy']['high_vectors']+8*128
  first=struct.unpack('<I',read(at,4))[0]
  el0_original=symbols.get('el0_synchronous_vector_64_long')
  compiled['el0_brk_forwarded']=bool(first&0xfc000000==0x14000000 and el0_original is not None and branch_target(at,first,0x14000000)==el0_original)
  if not compiled['el0_brk_forwarded']:
   # Retain inspection of frozen historical artifacts without upgrading them.
   words=struct.unpack('<8I',read(at,32))
   assert words[:5]==(0xd5385212,0xd35afe52,0xf100f25f,0x54000061,0xd2800111)
   assert branch_target(at+20,words[5],0x14000000)==compiled['relay']
  # Verify the unchanged default POST's expected HMAC against final linked
  # diagnostic text, as generated by the pinned kernel build, not a reseal.
  import hmac,hashlib
  at=32;text=None;expected=None
  for _ in range(struct.unpack_from('<I',kernel,16)[0]):
   cmd,n=struct.unpack_from('<II',kernel,at)
   if cmd==0x19:
    for i in range(struct.unpack_from('<I',kernel,at+64)[0]):
     o=at+72+i*80;name=kernel[o:o+16].rstrip(b'\0');va,size=struct.unpack_from('<QQ',kernel,o+32)
     if name==b'__text' and kernel[o+16:o+32].rstrip(b'\0') in (b'__TEXT',b'__TEXT_EXEC'):assert text is None;text=read(va,size)
     if name==b'__fips_hmacs':assert size==32;expected=read(va,size)
   at+=n
  if '_source_corecrypto14_status' in symbols:
   assert text and expected and hmac.digest(b'\0',text,'sha256')==expected,'Diagnostic kernel was not finalized with intact default POST integrity'
  else:
   # The OS-prelink profile uses the imported original provider and its own
   # image integrity field. Do not apply the source-only native HMAC contract.
   assert expected is None and '_register_crypto_functions' in symbols and '_g_crypto_funcs' in symbols
  raw+=struct.pack('<4Q',*(compiled[k] for k in ['config','relay','body','bytes']))

 observer_limit=None
 if platform and target_id==20 and '_raphael_native_root_limit' in symbols:
  observer_limit=struct.unpack('<I',read(symbols['_raphael_native_root_limit'],4))[0];assert observer_limit in (100,400,500,600,1200,2400,3600,7200,18000)
 watchdog_checkpoint_mode=None
 if '_raphael_native_watchdog_method_checkpoint' in symbols:
  marker=struct.unpack('<I',read(symbols['_raphael_native_watchdog_method_checkpoint'],4))[0]
  assert observer_limit in (3600,7200,18000)
  from native_service_window import checkpoint_mode
  watchdog_checkpoint_mode=checkpoint_mode(marker,read,symbols)
 return raw,dict(watchdog_checkpoint_mode=watchdog_checkpoint_mode,watchdog_method_checkpoint=('_raphael_native_watchdog_method_checkpoint' in symbols),observer_limit_polls=observer_limit,**({"exception_policy":exception_policy} if exception_policy else {}),compiled=compiled,thread_policy=thread_policy,observer_frame_bytes=(frame if platform and target_id==20 else None),policy=policy,ranges=metadata,policy_sha256=sha(raw),kernel_sha256=sha(kernel),checkpoint_pa=target+mmu['physical_delta'],instrumentation=(('Original arm_init prefix to '+target_name+' entry; timers, panic probes and mutable segments restored') if platform else 'Original arm_vm_init runs and returns before PE_consistent_debug_inherit BRK; exact owned-grant transition TTBR0 and full mutable-segment recovery' if pmap else 'Original C runs to arm_vm_init entry BRK; temporary vector relay and complete mutable-segment backup/restoration'),scope=(('Original arm_init to '+target_name+' entry; target body and normal IRQ not executed') if platform else 'Original arm_vm_init returned with replaced TTBR1 and invalid original TTBR0; no normal XNU interrupt or userland claim' if pmap else 'Original arm_init C up to arm_vm_init first instruction, before pmap rebuild'))

def decode_service_thread(t,record_words,resolve):
 assert t[21]<=16 and t[22] in (0,1)
 frames=[];previous_fp=0
 for k in range(t[21]):
  fp,lr=t[24+k*2:26+k*2];assert fp%16==0 and previous_fp<fp and t[5]<=fp<=t[5]+t[6]-16;previous_fp=fp
  frames.append(dict(fp=fp,lr=lr,caller=resolve(lr)))
 result=dict(thread=t[0],tid=t[1],state=t[2],wait_event=t[3],continuation=t[4],continuation_symbol=resolve(t[4]),stack_base=t[5],stack_bytes=t[6],saved_sp=t[7],saved_fp=t[8],saved_lr=t[9],saved_lr_symbol=resolve(t[9]),user_pc=t[10],user_lr=t[11],user_sp=t[12],user_cpsr=t[13],user_x0_x1_x16_x2_x3_x4_x5=list(t[14:21]),frames=frames)
 if record_words==128:
  assert t[60]<=16 and t[61]<=3 and (t[58]==0xffffffff or t[58]%(4096)==0)
  user_frames=[];previous=0
  for k in range(t[60]):
   fp,lr=t[64+k*2:66+k*2];assert fp%16==0 and fp>previous and t[12]<=fp<=t[12]+1048576;previous=fp
   user_frames.append(dict(fp=fp,lr=lr))
  result.update(shared_cache_slide=None if t[58]==0xffffffff else t[58],user_fp=t[59],user_frame_status=t[61],user_frames=user_frames,user_x6_x7=list(t[56:58]))
  if t[96]==0x314c4454485052:
   signed=lambda v:v-(1<<64) if v&(1<<63) else v
   result['thread_cpu_ledger']=dict(options=t[97],limit_ticks=t[98],balance_ticks=signed(t[99]),credit_ticks=signed(t[100]),debit_ticks=signed(t[101]),refill_period_ns=t[102],since_last_refill_ns=t[103],actions=t[104],sample_counter=t[105])
 return result

def decode_service_spawn_snapshot(read,symbols,resolve):
 h=struct.unpack('<8Q',read(symbols['_raphael_service_spawn_header'],64))
 if not h[0]:
  assert not any(h)
  return dict(captured=False)
 assert h[:2]==(0x31575053485052,1) and h[2] in (1,2)
 assert h[5:]==(64,128,136) and 0<=h[4]<=min(64,h[3]) and h[3]<256
 assert h[2]!=2 or h[4]==min(64,h[3])
 rows=[];seen=set()
 for slot in range(h[4]):
  raw=read(symbols['_raphael_service_spawn_threads']+slot*136*8,136*8)
  v=struct.unpack('<136Q',raw)
  assert 1<=v[0]<256 and v[0] not in seen and v[1]<=1 and v[2] in (0,1) and v[3]==2
  name=raw[32:64].split(b'\0',1)[0].decode()
  assert name=='xpcproxy';seen.add(v[0])
  threads=[decode_service_thread(v[8:],128,resolve)] if v[1] else []
  rows.append(dict(pid=v[0],name=name,threads_truncated=bool(v[2]),threads=threads))
 return dict(captured=h[2]==2,observed_proxies=h[3],capacity=64,
  processes_truncated=h[3]>64,processes=rows,
  scope='One referenced thread per xpcproxy in PID1..255 at the existing first-method stop; thread order is not proof of main-thread identity, job label, XPC check-in or reply delivery')

def decode_service_snapshot(read,symbols):
 key='_raphael_service_header'
 if key not in symbols:return None
 h=struct.unpack('<8Q',read(symbols[key],64))
 if not h[0]:return dict(captured=False)
 assert h[0]==0x31565253485052 and h[1] in (1,2) and h[2]<256 and h[3]<256 and h[4]<=min(8,h[3]) and h[5:]==(256,8,8)
 assert h[1]!=2 or h[2]==255
 record_words=struct.unpack('<Q',read(symbols['_raphael_service_record_words'],8))[0] if '_raphael_service_record_words' in symbols else 64
 assert record_words in (64,128)
 service_words=8+8*record_words
 addresses=sorted((v,k) for k,v in symbols.items() if k.startswith('_') and '/' not in k)
 from bisect import bisect_right
 def resolve(pc):
  pos=bisect_right(addresses,(pc,chr(0x10ffff)))-1
  if pos>=0:
   address,name=addresses[pos]
   if pc-address<4096:return dict(symbol=name,offset=pc-address)
  return None
 probe=None
 if '_raphael_service_kernel_probe' in symbols:
  probe=struct.unpack('<64Q',read(symbols['_raphael_service_kernel_probe'],512))
  assert probe[21]<=16 and probe[22] in (0,1)
  probe=dict(thread=probe[0],tid=probe[1],state=probe[2],wait_event=probe[3],continuation=probe[4],saved_lr=probe[9],saved_lr_symbol=resolve(probe[9]),frame_count=probe[21],stack_captured=probe[22]==1)
 process_raw=read(symbols['_raphael_service_processes'],h[3]*64)
 processes=[]
 for i in range(h[3]):
  raw=process_raw[i*64:(i+1)*64];v=struct.unpack('<8Q',raw);assert 1<=v[0]<256 and v[6]<=8
  processes.append(dict(pid=v[0],state=v[1],name=raw[16:48].split(b'\0',1)[0].decode(errors='replace'),service_slot=v[6]-1 if v[6] else None))
 services=[]
 for slot in range(h[4]):
  raw=read(symbols['_raphael_service_threads']+slot*service_words*8,service_words*8);v=struct.unpack('<'+str(service_words)+'Q',raw)
  assert 1<=v[0]<256 and v[1]<=8 and v[2] in (0,1) and v[3]==2
  threads=[]
  for j in range(v[1]):
   threads.append(decode_service_thread(v[8+j*record_words:8+(j+1)*record_words],record_words,resolve))
  assert any(p['pid']==v[0] and p['service_slot']==slot for p in processes)
  services.append(dict(pid=v[0],name=raw[32:64].split(b'\0',1)[0].decode(errors='replace'),threads_truncated=bool(v[2]),threads=threads))
 result=dict(record_words=record_words,kernel_probe=probe,captured=h[1]==2,scanned_through_pid=h[2],processes=processes,services=services,pid_capacity=256,service_capacity=8,threads_per_service_capacity=8,scope='Bounded read-only original process and saved thread states at observer deadline; missing names outside PID range or caps remain unknown')
 if '_raphael_service_spawn_header' in symbols:
  result['spawn_waits']=decode_service_spawn_snapshot(read,symbols,resolve)
 return result

def decode_service_exceptions(read,symbols):
 key='_raphael_service_exceptions'
 if key not in symbols:return None
 records=[]
 for slot in range(4):
  raw=read(symbols[key]+slot*144*8,144*8);v=struct.unpack('<144Q',raw)
  if not v[0]:
   assert not v[1]
   continue
  assert v[0]==0x31584553504852 and v[1] in (1,2) and v[2]>0 and v[4]>0 and v[7]>0
  row=dict(slot=slot,pid=v[2],name=raw[64:96].split(b'\0',1)[0].decode(errors='replace'),complete=v[1]==2,exception=v[3],code_count=v[4],codes=list(v[5:7]),occurrences=v[7])
  assert row['name']==['SpringBoard','watchdogd','backboardd','liveactivitiesd'][slot]
  if row['complete']:
   t=v[16:];assert t[60]<=16 and t[61]<=3 and (t[58]==0xffffffff or t[58]%4096==0)
   frames=[];previous=0
   for k in range(t[60]):
    fp,lr=t[64+k*2:66+k*2];assert fp%16==0 and fp>previous and t[12]<=fp<=t[12]+1048576;previous=fp;frames.append(dict(fp=fp,lr=lr))
   row['thread']=dict(tid=t[1],state=t[2],user_pc=t[10],user_lr=t[11],user_sp=t[12],user_cpsr=t[13],user_x0_x1_x16_x2_x3_x4_x5=list(t[14:21]),shared_cache_slide=None if t[58]==0xffffffff else t[58],user_fp=t[59],user_frame_status=t[61],user_frames=frames,user_x6_x7=list(t[56:58]))
  records.append(row)
 return dict(records=records,scope='First original exception per selected service; later count only; original delivery unchanged')

def decode_init_snapshot(read,symbols):
 if '_raphael_native_user_record' not in symbols:return None
 raw=read(symbols['_raphael_native_user_record'],128);w=struct.unpack('<16Q',raw)
 assert w[0] in (0,0x3130525355485052)
 result=dict(observer_started=w[0]!=0,stage=int.from_bytes(read(symbols['_raphael_native_init_stage'],4),'little'),exec_error=int.from_bytes(read(symbols['_raphael_native_init_exec_error'],4),'little',signed=True),syscall_entries=w[1],last_syscall=w[2],first_user_pc=w[3],first_user_cpsr=w[4],pid=w[5],first_syscall=w[6],last_user_pc=w[7],last_x16=w[8],exec_attempts=w[10],process_name=raw[96:128].split(b'\0',1)[0].decode(errors='replace'))
 exceptions=decode_service_exceptions(read,symbols)
 if exceptions is not None:result['service_exceptions']=exceptions
 for name in ['stage','status','authorized','mount_status','readonly','native_union','root_recheck']:
  symbol='_native_owner_cache_'+name
  if symbol in symbols:result['systemos_'+name]=int.from_bytes(read(symbols[symbol],4),'little',signed=name in ['status','mount_status'])
 if '_raphael_native_copy_record' in symbols:
  copy=struct.unpack('<8Q',read(symbols['_raphael_native_copy_record'],64))
  result['copyout']=dict(step=copy[1],last_error=copy[2],scratch_address=copy[3],scratch_allocation_result=copy[4])
 if '_raphael_native_init_stack' in symbols:
  stack=struct.unpack('<64Q',read(symbols['_raphael_native_init_stack'],512))
  if stack[0]==0x314b5453485052:
   def near(address):
    matches=[(va,name) for name,va in symbols.items() if va<=address and name.startswith('_') and '/' not in name]
    if not matches:return None
    va,name=max(matches)
    return dict(symbol=name,offset=address-va) if address-va<4096 else None
   assert stack[20]<=16
   result['init_thread_stack']=dict(thread=stack[1],state=stack[2],wait_event=stack[3],continuation=stack[4],continuation_symbol=near(stack[4]),base=stack[5],bytes=stack[6],saved_sp=stack[7],saved_fp=stack[8],saved_lr=stack[9],saved_lr_symbol=near(stack[9]),saved_x19_x28=list(stack[10:20]),frames=[dict(fp=stack[24+i*2],lr=stack[25+i*2],caller=near(stack[25+i*2])) for i in range(stack[20])])
 if '_raphael_native_sync_record' in symbols:
  sync=struct.unpack('<144Q',read(symbols['_raphael_native_sync_record'],1152))
  assert sync[0] in (0,0x31434e5953485052)
  entries=[]
  for slot in range(min(sync[1],4)):
   v=sync[16+slot*32:48+slot*32]
   entries.append(dict(sequence=v[0],esr=v[1],exception_class=v[1]>>26,far=v[2],pc=v[3],lr=v[4],sp=v[5],cpsr=v[6],ttbr0=v[7],ttbr1=v[8],tcr=v[9],sctlr=v[10],x0_x5=list(v[11:17]),x16_x18=list(v[17:20])))
  result['copyout_sync_exceptions']=dict(count=sync[1],first_three_and_last=entries)
 if '_raphael_native_vm_record' in symbols:
  vm=struct.unpack('<32Q',read(symbols['_raphael_native_vm_record'],256))
  assert vm[0] in (0,0x314d56485052)
  result['copyout_vm_fault']=dict(count=vm[1],phase=vm[2],fault_code=vm[3],fault_type=vm[4],fault_address=vm[5],recover=vm[6],map=vm[7],pmap=vm[8],ttep=vm[9],vm_result=vm[10],fast_result=vm[11],ttbr0_after=vm[12],tcr_after=vm[13])
 if '_raphael_native_kill_record' in symbols:
  rawkill=read(symbols['_raphael_native_kill_record'],384);kill=struct.unpack('<48Q',rawkill)
  assert kill[0] in (0,0x314c4c494b485052)
  if kill[0]:result['pid1_kill']=dict(signal=kill[2],csflags=kill[3],reason_namespace=kill[4],reason_code=kill[5],caller=kill[6],has_reason=bool(kill[7]),process_name=rawkill[64:128].split(b'\0',1)[0].decode(errors='replace'),description=rawkill[128:384].split(b'\0',1)[0].decode(errors='replace'))
 if '_raphael_native_exec_record' in symbols:
  rawexec=read(symbols['_raphael_native_exec_record'],512)
  attempts=[]
  for slot in range(4):
   v=struct.unpack_from('<16Q',rawexec,slot*128)
   if v[0]:attempts.append(dict(sequence=v[0],phase=v[1],error=v[2] if v[1]==2 else None,path=rawexec[slot*128+32:(slot+1)*128].split(b'\0',1)[0].decode(errors='replace')))
  result['exec_calls']=attempts
 if '_raphael_native_syscall_ring' in symbols:
  ring=struct.unpack('<512Q',read(symbols['_raphael_native_syscall_ring'],4096));calls=[]
  for slot in range(32):
   v=ring[slot*16:(slot+1)*16]
   if v[0]:calls.append(dict(sequence=v[0],code=v[1],pc=v[2],thread=v[3],cpsr=v[4],args=list(v[5:11]),phase=v[11],error=v[12] if v[11]==2 else None,result0=v[13],result1=v[14],tid=v[15]))
  result['unix_syscall_trace']=sorted(calls,key=lambda v:v['sequence'])
  result['exec_user_thread']=w[11]
 result['pid1_el0_syscall_verified']=result['observer_started'] and result['syscall_entries']>0 and result['pid']==1 and 0<result['first_user_pc']<1<<48 and result['first_user_cpsr']&15==0 and result['process_name']=='launchd'
 result['exec_loaded_verified']=result['stage']==4 and result['exec_error']==0 and result['exec_attempts']>0
 if '_raphael_offline_aks_stage' in symbols:
  result['offline_keystore']={name:int.from_bytes(read(symbols['_raphael_offline_aks_'+name],8),'little') for name in ['stage','opens','refused','calls','selector','result','selectors']}
 for name in ['vm_page_free_count','vm_page_active_count','vm_page_inactive_count','vm_page_wire_count']:
  if '_'+name in symbols:result[name]=int.from_bytes(read(symbols['_'+name],4),'little')
 if '_raphael_native_pmgr_record' in symbols:
  pmgr=struct.unpack('<16Q',read(symbols['_raphael_native_pmgr_record'],128))
  if pmgr[0]:
   assert pmgr[0]==0x3152474d50485052
   result['original_pmgr_nub']=dict(stage=pmgr[1],mode=pmgr[2],module_load_status=pmgr[3],class_bytes=pmgr[4],object=pmgr[5],aon_provider_after_init=pmgr[6],attached=pmgr[7],started=pmgr[8],aon_provider_after_start=pmgr[9],hardware_power_management_verified=False)
 if '_raphael_watchdog_client_record' in symbols:
  c=struct.unpack('<16Q',read(symbols['_raphael_watchdog_client_record'],128))
  if c[0]:
   assert c[0]==0x31434c57485052 and 1<=c[1]<=5 and c[6] in (0,1) and c[10] in (0,1)
   result['watchdog_client']=dict(stage=c[1],opens=c[2],closes=c[3],checkins=c[4],last_checkin_counter=c[5],userspace_monitoring=bool(c[6]),counter_frequency=c[7],failures=c[8],last_selector=c[9],missed_checkin=bool(c[10]),metaclass=c[11],service=c[12],initial_hardware_armed=bool(c[13]),absolute_deadline_counter=c[14],module_load_status=c[15],scope='Original watchdogd client on the bounded physical watchdog; IOKit monitoring unsupported' if c[13] else 'QEMU original ancestry and service lifecycle only; hardware unavailable')
 if '_raphael_watchdog_method_record' in symbols:
  wm=struct.unpack('<32Q',read(symbols['_raphael_watchdog_method_record'],256))
  if wm[24]:
   assert wm[24]==wm[25]==1
   result['watchdog_registry']=dict(primary_marker=1,property_match_verified=True,hardware_pmu_verified=False,property_writes_supported=False,scope='Diagnostic registry handle only; inherited setProperties remains unsupported')
  if wm[0]:
   assert wm[0]==0x314d57485052 and wm[1] in (1,2)
   keys=['result','selector','opened','has_arguments','version','argument_selector','async_wake_port','async_reference_count','scalar_input_count','scalar_output_count','structure_input_size','structure_output_size','input_descriptor','output_descriptor','scalar_output_pointer','structure_input_pointer','structure_output_pointer','structure_output_descriptor_size','async_reference_pointer','variable_output_pointer','guard']
   result['watchdog_method']=dict(complete=wm[1]==2,calls=wm[2],**dict(zip(keys,wm[3:24])))
 if '_cs_native4k_full_blocks' in symbols:
  signature={}
  for name in ['cs_native4k_full_blocks','cs_native4k_page_checks','cs_native4k_ready_blobs','cs_native4k_read_ticks','cs_native4k_hash_ticks','cs_native4k_bytes','cs_validate_page_bad_hash','cs_validate_page_no_hash']:
   if '_'+name in symbols:signature[name]=int.from_bytes(read(symbols['_'+name],8),'little')
  result['native4k_signature']=signature
 # Pinned XNU kern_exit.c exposes this original PID1-only, one-shot sysctl as
 # 'Boolean indicator that launchd has reached main'. Do not infer it from a
 # syscall count or a successful exec; retain old images without this symbol.
 if '_initproc_spawned' in symbols:
  spawned=int.from_bytes(read(symbols['_initproc_spawned'],4),'little',signed=True)
  assert spawned in (0,1)
  result['original_initproc_spawned']=spawned
 if '_real_phys_size' in symbols:result['real_phys_size']=int.from_bytes(read(symbols['_real_phys_size'],8),'little')
 if '_native_owner_data_stage' in symbols:
  data={}
  for name in ['native_owner_data_stage','native_owner_data_status','native_owner_data_readonly','native_owner_data_source_lookup','native_owner_data_target_lookup','raphael_data_seed_status','raphael_data_seed_entries','raphael_data_seed_index','native_ram_block_ready','native_ram_block_sparse']:
   if '_'+name in symbols:data[name]=int.from_bytes(read(symbols['_'+name],4),'little',signed=name.endswith(('status','readonly','lookup')))
  for name in ['native_owner_data_seed_size','raphael_data_seed_written','raphael_data_seed_readback','native_ram_block_bytes','native_ram_block_reads','native_ram_block_writes','native_ram_block_failures','native_ram_block_resident_bytes']:
   if '_'+name in symbols:data[name]=int.from_bytes(read(symbols['_'+name],8),'little')
  result['ephemeral_data']=data
 if '_raphael_display_stage' in symbols:
  display={}
  fields32='stage guard clients hardware_stage video_status surface_status family_status meta_status'.split()
  fields64='row_bytes depth rotate map_length validations rejected kicks frames blank_frames retired bytes nonblack reject_reason transfer_status client_status power_status base width height'.split()
  for name in fields32+fields64:
   key='_raphael_display_'+name
   if key in symbols:display[name]=int.from_bytes(read(symbols[key],4 if name in fields32 else 8),'little',signed=name in ['surface_status','family_status','meta_status'])
  display['scope']='Original-family memory presentation counters; panel visibility and desktop acceptance require independent observation'
  result['display']=display
 services=decode_service_snapshot(read,symbols)
 if services is not None:result['services']=services
 result['launchd_main_verified']=result['pid1_el0_syscall_verified'] and result.get('original_initproc_spawned')==1
 return result

def decode(raw,delta,kernel,contract,mmu_observation,tables,sparse=None):
 v=contract['early']['policy']['version'];base=640 if v>=9 else 448 if v>=8 else 320;assert len(raw)==base+(96 if v>=5 else 0)+(64 if v>=8 else 0);values=struct.unpack('>'+str(base//8)+'Q',raw[:base]);d=dict(zip(FIELDS,values));c=contract['early'];p=c['policy']
 assert d['version']==p['version'] and d['status']==3 and d['error']==0 and d['checkpoint_va']==p['checkpoint'] and d['return_va']==p['return_va']
 assert d['const_args_va']==p['const_args'] and d['original_args_pa']==contract['args'] and d['args_bytes']==p['args_bytes']
 assert d['backup_bytes']==p['backup_bytes'] and d['delta_bytes']==len(delta)==d['delta_words']*12 and 0<len(delta)<=p['delta_capacity']
 assert not d['delta_overflow'] and d['saved_ranges']==d['restored_ranges']==p['count'] and d['args_copy_ok']==1
 originals=[];observed=[];ranges=[]
 for i,s in enumerate(c['ranges']):
  r=dict(zip(RANGE,values[16+i*8:24+i*8]));assert r['virtual']==s['virtual'] and r['physical']==s['virtual']+contract['physical_delta'] and r['bytes']==s['bytes']
  original=kernel[s['offset']:s['offset']+s['file_bytes']]+bytes(s['bytes']-s['file_bytes']);assert zlib.crc32(original)==r['crc_before']==r['crc_restored']==s['original_crc32'] and r['backup_ok']==1
  originals.append(original);observed.append(bytearray(original));ranges.append(r)
 joined=bytearray(b''.join(originals));seen=set();previous=-1
 for off,value in struct.iter_unpack('<IQ',delta):
  assert off%8==0 and off>previous and off+8<=len(joined);previous=off;seen.add(off)
  assert struct.unpack_from('<Q',joined,off)[0]!=value
  struct.pack_into('<Q',joined,off,value)
 cursor=0
 for i,(r,s) in enumerate(zip(ranges,c['ranges'])):
  actual=bytes(joined[cursor:cursor+s['bytes']]);observed[i]=actual;count=sum(originals[i][j:j+8]!=actual[j:j+8] for j in range(0,len(actual),8));assert count==r['changed_words'] and zlib.crc32(actual)==r['crc_after'];cursor+=s['bytes']
  r['snapshot_sha256']=sha(actual)
 def read(v,n):
  for s,b in zip(c['ranges'],observed):
   if s['virtual']<=v and v+n<=s['virtual']+s['bytes']:return b[v-s['virtual']:v-s['virtual']+n]
  raise AssertionError('Missing reconstructed range')
 args=read(p['const_args'],p['args_bytes']);assert struct.unpack_from('<HH',args)==(2,2)
 assert struct.unpack_from('<3Q',args,8)==(contract['virtual_base'],contract['physical_base'],contract['window_bytes'])
 assert struct.unpack_from('<Q',args,0x478)[0]==contract['window_bytes'] and args[0x6c:0x6c+len(b'-v keepsyms=1 cpus=1')]==b'-v keepsyms=1 cpus=1'
 assert struct.unpack('<Q',read(p['boot_args'],8))[0]==p['const_args']
 assert read(contract['policy']['tables'],65536)==tables
 thread=decode_thread(raw[base:base+96],contract,mmu_observation,sparse) if v>=5 else None
 exception=decode_exception(raw[base+96:],contract,mmu_observation,sparse,read) if v>=8 else None
 crypto=None;cpu=None
 if v>=7:
  _,symbols=image(kernel)
  functions=struct.unpack('<Q',read(symbols['_g_crypto_funcs'],8))[0]
  assert functions!=0,'Original crypto provider must register real functions before this checkpoint'
  if '_source_corecrypto14_status' in symbols:
   status=struct.unpack('<I',read(symbols['_source_corecrypto14_status'],4))[0];assert status==0
   crypto=dict(status=status,functions=functions,provider='source',original_post_returned=True,integrity_expected_digest_modified=False,runtime_text_patched=False)
  else:
   crypto=dict(functions=functions,provider='original-prelinked',provider_functions_registered=True,original_post_returned=None,runtime_text_patched=False,scope='Function registration observed; source-provider status and POST result are not exported by this image')
  if p['reserved2']>=18:
   fields32='stage registered intid physical_timer last_irq'.split()
   fields64='timer_irqs ipi_irqs eois dist_pa redist_pa frequency'.split()
   cpu={name:int.from_bytes(read(symbols['_raphael_cpu_'+name],4 if name in fields32 else 8),'little') for name in fields32+fields64}
   cpu['normal_xnu_irq_verified']=cpu['stage']==5 and cpu['registered']==1 and cpu['timer_irqs']>0 and cpu['eois']==cpu['timer_irqs']+cpu['ipi_irqs']
   if p['reserved2'] in (19,20):assert cpu['normal_xnu_irq_verified'],'Real boot CPU and timer-backed wake must complete before accepting BSD scheduling'


 storage=None
 if v>=9:
  _,symbols=image(kernel)
  names32=['online','start_stage','last_result']+(['diagnostic_state','diagnostic_online_before'] if '_raphael_ufs_diagnostic_state' in symbols else []);names64=['requests','failures','bytes']+(['manifest_bytes','policy_allocated_bytes'] if '_raphael_ufs_manifest_bytes' in symbols else [])
  if '_raphael_ufs_start_detail' in symbols:names32+=['start_detail']
  names64 += [name for name in ["diagnostic_aborts", "diagnostic_stop_counter", "diagnostic_quiesced_counter"] if "_raphael_ufs_"+name in symbols]
  if all('_raphael_ufs_'+n in symbols for n in names32+names64):
   storage={n:int.from_bytes(read(symbols['_raphael_ufs_'+n],4 if n in names32 else 8),'little') for n in names32+names64}
   storage['scope']='Same checkpoint runtime globals; online and actual request counts are independent observations'
   dma_mapping=decode_dma_mapping(read,symbols)
   if dma_mapping:storage['dma_mapping']=dma_mapping
   write_probe=decode_write_probe(read,symbols)
   if write_probe:storage['write_probe']=write_probe

 root=None
 if p['reserved2']==20:
  words=struct.unpack('<16Q',read(symbols['_raphael_native_root_record'],128))
  assert words[0]==0x31544f4f52485052 and words[1]==2 and words[7] in (50,100,400,500,600,1200,2400,3600,7200,18000) and 1<=words[2]<=words[7]
  expected_limit=contract['early'].get('observer_limit_polls')
  assert expected_limit is None or words[7]==expected_limit
  root=dict(observer_completed=True,observer_limit_polls=words[7],observer_limit_ms=words[7]*100,bsd_stage=int.from_bytes(read(symbols['_raphael_native_root_stage'],4),'little'),polls=words[2],root_accepted_observed=words[3]==1,root_vnode=words[4],mount_flags=words[5],root_device=words[6],filesystem=read(symbols['_raphael_native_root_record']+64,32).split(b'\0',1)[0].decode(errors='replace'),device_name=read(symbols['_raphael_native_root_record']+96,32).split(b'\0',1)[0].decode(errors='replace'))
  for name in ['accepted','apple_autherr','decision','readonly','mount_device','selected_device']:
   symbol='_native_owner_root_'+name
   root['owner_'+name]=int.from_bytes(read(symbols[symbol],4),'little',signed=name in ['apple_autherr','decision','readonly'])
  root['apfs_root_mounted_verified']=root['root_accepted_observed'] and root['root_vnode']!=0 and root['filesystem']=='apfs' and root['owner_accepted']==root['owner_decision']==root['owner_readonly']==1 and root['owner_mount_device']==root['owner_selected_device']
 watchdog_budget=None
 if '_raphael_native_watchdog_record' in symbols:
  w=struct.unpack('<16Q',read(symbols['_raphael_native_watchdog_record'],128))
  if w[0]:
   assert w[0]==0x3154445748505255 and w[1] in (2,3) and w[4]==20 and w[5] in (60000,180000,300000,420000,780000,1860000)
   assert w[8]>0 and w[9]-w[6]<w[7] and w[7]==w[14]*(w[5]//1000)
   assert 0<w[6]<=w[9]<=w[10]<=mmu_observation['counter'], 'Watchdog physical-counter chronology must precede the same-run capture'
   watchdog_budget=dict(status=w[1],base=w[2],frequency=w[3],hardware_seconds=w[4],budget_ms=w[5],start_counter=w[6],deadline_ticks=w[7],pets=w[8],last_pet_counter=w[9],stop_counter=w[10],counter_frequency=w[14])
   if w[11]:
    assert w[11]==w[14]*{60000:40,180000:120,300000:240,420000:360,780000:720,1860000:1800}[w[5]] and w[13] in (0,1)
    assert not w[13] or w[6]+w[11]<=w[12]<=w[10]
    watchdog_budget.update(observer_deadline_ticks=w[11],contract_version=w[15],observer_deadline_reached=bool(w[13]),elapsed_ms=(w[10]-w[6])*1000/w[14])
 qemu_observer=None
 if '_raphael_qemu_observer_record' in symbols:
  q=struct.unpack('<4Q',read(symbols['_raphael_qemu_observer_record'],32))
  if q[0]:
   assert not watchdog_budget and q[1]>0 and q[3] in (0,1)
   if q[3]:assert q[0]+q[1]*40<=q[2]<=mmu_observation['counter']
   qemu_observer=dict(rootless_fixture=True,deadline_ms=40000,deadline_reached=bool(q[3]),elapsed_ms=(q[2]-q[0])*1000/q[1] if q[3] else None)
 expected_watchdog=contract['early'].get('diagnostic_watchdog_budget')
 if expected_watchdog:
  assert watchdog_budget and watchdog_budget['status']==2 and watchdog_budget['pets']>=2
  assert all(watchdog_budget[a]==expected_watchdog[b] for a,b in [('base','base'),('frequency','frequency'),('hardware_seconds','seconds'),('budget_ms','budget_ms')])
 init=decode_init_snapshot(read,symbols) if v>=7 else None
 if root and contract['early'].get('watchdog_method_checkpoint'):
  root['watchdog_method_checkpoint_requested']=True
  method=(init or {}).get('watchdog_method')
  if watchdog_budget and not watchdog_budget.get('observer_deadline_reached') and root['polls']<root['observer_limit_polls']:
   assert method and method['complete'], 'Early handset stop requires the completed method record'
   marker=struct.unpack('<I',read(symbols['_raphael_native_watchdog_method_checkpoint'],4))[0]
   from native_service_window import checkpoint_mode
   mode=checkpoint_mode(marker,read,symbols)
   expected_mode=contract['early'].get('watchdog_checkpoint_mode')
   assert expected_mode is None or expected_mode==mode or (marker==2 and expected_mode=='first-display-client'), 'Checkpoint mode does not match kernel marker'
   root['watchdog_checkpoint_marker']=marker
   if mode in ('first-display-client','first-display-client-attempt'):
    display=(init or {}).get('display',{})
    assert display.get('clients',0)>0 and display.get('client_status')==0, 'Early display stop requires successful original client return'
    root['display_client_return_verified']=mode=='first-display-client'
    root['stop_reason']='first-display-client-after-watchdog-method' if mode=='first-display-client' else 'first-display-client-attempt-after-watchdog-method'
   elif mode=='first-method-plus-5s':
    from native_service_window import decode_service_window
    window=decode_service_window(read,symbols,watchdog_budget,mmu_observation['counter'])
    assert window['completed'], 'Early post-method stop requires five physical seconds'
    root['service_window']=window
    root['stop_reason']='five-seconds-after-first-watchdog-method'
   else:root['stop_reason']='first-watchdog-method-complete'
  elif qemu_observer and qemu_observer['deadline_reached']:
   root['stop_reason']='rootless-qemu-deadline'
  else:root['stop_reason']='observer-bound'
  if contract['early'].get('watchdog_checkpoint_mode')=='first-method-plus-5s' and 'service_window' not in root:
   from native_service_window import decode_service_window
   root['service_window']=decode_service_window(read,symbols,watchdog_budget,mmu_observation['counter'])
 console=None
 if v>=7:
  try:
   console=decode_recovered_console(read,symbols)
   if console:console['full_checkpoint_verified']=True
  except (AssertionError,ValueError,struct.error) as error:console=dict(unavailable=True,error=str(error) or type(error).__name__)
 return dict(**d,**({'console':console} if console else {}),**({'init':init} if init else {}),**({'thread':thread} if thread else {}),**({'exception_stack':exception} if exception else {}),**({'crypto':crypto} if crypto else {}),**({'cpu':cpu} if cpu else {}),**({'storage':storage} if storage is not None else {}),**({'root':root} if root else {}),**({'diagnostic_watchdog_budget':watchdog_budget} if watchdog_budget else {}),**({'qemu_observer':qemu_observer} if qemu_observer else {}),ranges=ranges,delta_sha256=sha(delta),arm_init_c_executed=True,arm_vm_init_entry_reached=True,pmap_rebuild_executed=p['version']>=2,full_xnu_boot_verified=False)


def decode_thread(raw,c,m,sparse):
 names='version status thread_va thread_pa base_field_pa top_field_pa stack_base stack_top stack_bytes stack_pages first_pa last_pa'.split()
 assert len(raw)==96 and sparse is not None
 d=dict(zip(names,struct.unpack('>12Q',raw)));t=c['early']['thread_policy'];assert d['version']==1 and d['status']==3
 assert d['thread_va']==m['tpidr_el1'] and d['stack_top']==m['interrupted_sp']+c['early']['policy']['frame_bytes']
 if c['early']['policy']['reserved2']==11:assert m['x20']==c['early']['policy']['checkpoint']
 assert d['stack_bytes']%4096==0 and 4096<=d['stack_bytes']<=65536 and d['stack_base']%4096==0
 assert d['stack_top']==d['stack_base']+d['stack_bytes']-t['context_bytes'] and d['stack_pages']==d['stack_bytes']//4096
 walk=sparse_walk(c,m,sparse)
 assert d['thread_pa']==walk(d['thread_va']) and d['base_field_pa']==walk(d['thread_va']+t['base_offset']) and d['top_field_pa']==walk(d['thread_va']+t['top_offset'])
 mapped=[walk(d['stack_base']+i*4096) for i in range(d['stack_pages'])]
 assert mapped[0]==d['first_pa'] and mapped[-1]==d['last_pa'] and len(set(mapped))==len(mapped)
 assert m['interrupted_sp']!=c['policy']['interrupt_sp'] and m['lr']==c['early']['policy']['return_va']
 return dict(**d,first_thread_stack_verified=True,normal_xnu_irq_verified=False)


def sparse_walk(c,m,sparse):
 pages={};at=0
 while at<len(sparse):
  pa,level,count,crc=struct.unpack_from('<QHHI',sparse,at);at+=16;page=bytearray(4096)
  assert pa not in pages and c['physical_base']<=pa<pa+4096<=c['physical_base']+c['window_bytes']
  for _ in range(count):
   ix,val=struct.unpack_from('<HQ',sparse,at);at+=10;assert ix<512;struct.pack_into('<Q',page,ix*8,val)
  assert zlib.crc32(page)==crc;pages[pa]=(level,page)
 assert at==len(sparse)
 def walk(va):
  assert va>>38==(1<<26)-1
  va&=(1<<38)-1
  pa=m['ttbr1'];mask=0x0000fffffffff000
  for level in range(1,4):
   assert pa in pages and pages[pa][0]==level
   shift=12+9*(3-level);w=struct.unpack_from('<Q',pages[pa][1],((va>>shift)&511)*8)[0];assert w&1
   if level<3 and w&3==3:pa=w&mask;continue
   assert w&3==(3 if level==3 else 1);lo=(1<<shift)-1;pa=(w&mask&~lo)|(va&lo)
   assert c['physical_base']<=pa<c['physical_base']+c['window_bytes'];return pa
  raise AssertionError('Missing thread translation')
 return walk

def decode_exception(raw,c,m,sparse,read):
 names='version status field_va field_pa top bytes first_pa last_pa'.split()
 assert len(raw)==64;d=dict(zip(names,struct.unpack('>8Q',raw)))
 p=c['early']['exception_policy'];assert d['version']==1 and d['status']==3
 assert d['field_va']==p['field_va'] and d['bytes']==p['bytes'] and d['top']==m['sp']
 assert struct.unpack('<Q',read(d['field_va'],8))[0]==d['top']
 walk=sparse_walk(c,m,sparse);assert walk(d['field_va'])==d['field_pa']
 pages=[walk(d['top']-d['bytes']+i*4096) for i in range(d['bytes']//4096)]
 assert len(set(pages))==len(pages) and pages[0]==d['first_pa'] and pages[-1]==d['last_pa']
 return dict(**d,original_allocated_exception_stack_verified=True)


def decode_write_probe(read,symbols):
 if '_raphael_ufs_write_probe_record' not in symbols:return None
 w=struct.unpack('<8Q',read(symbols['_raphael_ufs_write_probe_record'],64))
 if not w[0]:return None
 assert w[0]==1 and w[1] in (1,3,7,15,31,63) and w[6]==1
 assert 0<w[3]<w[4] and w[3]<=0xffffffff and w[7]>0
 if w[2]==0:assert w[1]==63 and w[5]==0
 caller=None
 if '_raphael_ufs_write_request_record' in symbols:
  c=struct.unpack('<6Q',read(symbols['_raphael_ufs_write_request_record'],48))
  assert c[0]==1 and c[1]>0 and c[4] in (0,1)
  if c[4]:assert c[5]>=w[7] and c[3]==w[1]
  caller=dict(version=c[0],attempts=c[1],result=c[2],stages=c[3],finished=c[4]==1,counter=c[5])
 return dict(caller=caller,version=1,stages=w[1],result=w[2],lba=w[3],lun_blocks=w[4],ocs=w[5],permission_revoked=True,counter=w[7],immediate_readback_verified=w[2]==0,persistence_after_reboot_verified=False,scope='Native kernel synchronous diagnostic write; separate Android reboot/media readback is required')

def decode_dma_mapping(read,symbols):
 if '_raphael_ufs_dma_mapping_record' not in symbols:return None
 w=struct.unpack('<8Q',read(symbols['_raphael_ufs_dma_mapping_record'],64))
 if not w[0]:return None
 assert w[0]==1 and w[1] in (1,2,3)
 result=dict(version=w[0],status=w[1],physical=w[2],bytes=w[3],first_par=w[4],last_par=w[5],mair=w[6],verified_pages=w[7],normal_noncacheable_verified=w[1]==2)
 if w[1]==2:assert w[3] in (8192,20480) and w[7]==w[3]//4096 and w[4]>>56==w[5]>>56==0x44
 return result

def recovered_snapshot_reader(raw,delta,kernel,contract):
 """Validate every restored mutable-segment CRC; no active-pmap or checkpoint acceptance."""
 p=contract['early']['policy'];ranges=contract['early']['ranges']
 assert p['version']>=7 and len(raw)>=(640 if p['version']>=9 else 448 if p['version']>=8 else 320)
 values=struct.unpack('>'+str((640 if p['version']>=9 else 448 if p['version']>=8 else 320)//8)+'Q',raw[:640 if p['version']>=9 else 448 if p['version']>=8 else 320])
 assert values[0]==p['version'] and values[1]==3 and values[2]==0
 assert values[9]==p['backup_bytes'] and values[10]==len(delta)==values[11]*12 and not values[12]
 assert values[13]==values[14]==len(ranges) and values[15]==1
 original=[];observations=[]
 for i,r in enumerate(ranges):
  v=values[16+i*8:24+i*8]
  assert v[0]==r['virtual'] and v[1]==r['virtual']+contract['physical_delta'] and v[2]==r['bytes']
  block=kernel[r['offset']:r['offset']+r['file_bytes']]+bytes(r['bytes']-r['file_bytes'])
  assert zlib.crc32(block)==v[3]==v[5]==r['original_crc32'] and v[7]==1
  original.append(block);observations.append(v)
 joined=bytearray(b''.join(original));previous=-1
 for offset,value in struct.iter_unpack('<IQ',delta):
  assert offset%8==0 and offset>previous and offset+8<=len(joined);previous=offset
  assert struct.unpack_from('<Q',joined,offset)[0]!=value
  struct.pack_into('<Q',joined,offset,value)
 cursor=0;observed=[]
 for r,v,before in zip(ranges,observations,original):
  block=bytes(joined[cursor:cursor+r['bytes']]);cursor+=r['bytes']
  assert zlib.crc32(block)==v[4] and sum(before[j:j+8]!=block[j:j+8] for j in range(0,len(block),8))==v[6]
  observed.append(block)
 def read(address,count):
  for r,b in zip(ranges,observed):
   if r['virtual']<=address and address+count<=r['virtual']+r['bytes']:return b[address-r['virtual']:address-r['virtual']+count]
  raise AssertionError('Panic record is outside recovered mutable ranges')
 _,symbols=image(kernel)
 return read,symbols

def decode_recovered_console(read,symbols):
 """Read only the original msgbuf reachable inside restored mutable ranges."""
 if '_msgbufp' not in symbols:return None
 pointer=struct.unpack('<Q',read(symbols['_msgbufp'],8))[0]
 magic,size,write_index,read_index,buffer=struct.unpack('<4IQ',read(pointer,24))
 assert magic==0x63061 and 0<size<=1048576 and write_index<size and read_index<size
 data=read(buffer,size)
 return dict(source='Original XNU msgbuf in CRC-verified restored mutable segments',capacity=size,write_index=write_index,read_index=read_index,text=(data[write_index:]+data[:write_index]).replace(b'\0',b'').decode(errors='replace'),full_checkpoint_verified=False)

def decode_recovered_globals(raw,delta,kernel,contract):
 """Diagnostic evidence after a rejected checkpoint; never a passed experiment."""
 read,symbols=recovered_snapshot_reader(raw,delta,kernel,contract)
 storage={}
 for name in ['requests','failures','bytes']:
  key='_raphael_ufs_'+name
  if key in symbols:storage[name]=int.from_bytes(read(symbols[key],8),'little')
 write_probe=decode_write_probe(read,symbols)
 if write_probe:storage['write_probe']=write_probe
 try:console=decode_recovered_console(read,symbols)
 except (AssertionError,ValueError,struct.error) as error:console=dict(unavailable=True,error=str(error) or type(error).__name__)
 return dict(console=console,snapshot_crc_verified=True,mutable_segments_restored=True,full_checkpoint_verified=False,scope='Restored mutable segments only; complete active pmap and normal checkpoint acceptance remain mandatory',init=decode_init_snapshot(read,symbols),dma_mapping=decode_dma_mapping(read,symbols),storage=storage)

def decode_compiled_panic(raw,delta,kernel,contract):
 """Failure evidence only: validate the restored snapshot, never accept a stop."""
 read,symbols=recovered_snapshot_reader(raw,delta,kernel,contract)
 record=read(symbols['_raphael_native_panic_record'],256)
 magic,active,caller,fmt,args,reason,context,options=struct.unpack('<8Q',record[:64])
 assert magic==0x31434e5048505255 and active==1
 closest=max((v,k) for k,v in symbols.items() if v<=caller and k.startswith('_') and '/' not in k)
 telemetry={}
 dma_mapping=decode_dma_mapping(read,symbols)
 if dma_mapping:telemetry['ufs_dma_mapping']=dma_mapping
 write_probe=decode_write_probe(read,symbols)
 if write_probe:telemetry['ufs_write_probe']=write_probe
 for prefix,names,width in [('raphael_cpu_',['stage','registered','intid','physical_timer','last_irq'],4),('raphael_ufs_',['online','start_stage','last_result','diagnostic_state','diagnostic_online_before'],4),('armdt_platform_',['configured','child_count','cpu_count','bus_count','defaults_count','nvram_proxy','device_count'],4)]:
  for name in names:
   symbol='_'+prefix+name
   if symbol in symbols:telemetry[prefix+name]=int.from_bytes(read(symbols[symbol],width),'little')
 fault=None
 if '_raphael_native_fault_record' in symbols:
  record_fault=read(symbols['_raphael_native_fault_record'],512);f=struct.unpack('<64Q',record_fault)
  if f[0]==0x31544c4650485255 and f[1]==1:
   pc=f[2];near=max((v,k) for k,v in symbols.items() if v<=pc and k.startswith('_') and '/' not in k)
   fault=dict(pc=pc,lr=f[3],sp=f[4],far=f[5],esr=f[6],cpsr=f[7],registers=list(f[8:37]),fp=f[37],message=record_fault[304:432].split(b'\0',1)[0].decode(errors='replace'),pc_symbol=near[1] if pc-near[0]<4096 else None,pc_offset=pc-near[0] if pc-near[0]<4096 else None)
 if '_raphael_ufs_start_detail' in symbols:telemetry['raphael_ufs_start_detail']=int.from_bytes(read(symbols['_raphael_ufs_start_detail'],4),'little')
 init=decode_init_snapshot(read,symbols)
 if '_raphael_native_root_stage' in symbols:telemetry['raphael_native_root_stage']=int.from_bytes(read(symbols['_raphael_native_root_stage'],4),'little')
 return dict(**({'init':init} if init else {}),**({'fault':fault} if fault else {}),telemetry=telemetry,source_compiled_panic=True,checkpoint_reached=False,caller=caller,caller_symbol=closest[1] if caller-closest[0]<4096 else None,caller_offset=caller-closest[0] if caller-closest[0]<4096 else None,format_address=fmt,args_address=args,reason=reason,context=context,options=options,format=record[64:].split(b'\0',1)[0].decode(errors='replace'),snapshot_crc_verified=True,mutable_segments_restored=True,delta_sha256=sha(delta))
