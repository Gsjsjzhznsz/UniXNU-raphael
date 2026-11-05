#!/usr/bin/env python3
"""Derive the bounded MMU-checkpoint policy solely from the frozen kernel."""
import re,struct,zlib
from entry_probe import sha
from native_entry import make_contract as entry_contract
MAGIC=int.from_bytes(b'RPHMMU01','little')
POLICY='magic version arm_init low_vectors high_vectors tables tables_bytes tcr mair sctlr exception_sp interrupt_sp arm_opcode start start_bytes start_crc ttb ttb_bytes ttb_crc flags bootstrap_skip'.split()
FIELDS='version status armed trap_count entry checkpoint_va original_instruction probe_instruction esr elr far spsr x0 x1 x20 x21 x22 x23 x24 x25 sp lr sctlr vbar tcr ttbr0 ttbr1 mair saved_sctlr saved_vbar saved_tcr saved_ttbr0 saved_ttbr1 saved_mair saved_cpacr saved_tpidr_el0 saved_tpidrro saved_tpidr_el1 saved_sp_el0 frequency affinity vector_slot cache_off_sctlr relay_pa tables tables_bytes tables_crc_before tables_crc_after physical_translation virtual_translation patch_restored tables_restored mmu_restored args_ok segments_ok zero_ok error expected_tcr expected_mair expected_sctlr expected_phys_base expected_virt_base expected_mem_bytes tables_changed_count interrupted_sp current_el daif cpacr tpidr_el0 tpidrro tpidr_el1 counter'.split()

def make_policy(kernel,adt,window,frequency,affinity):
 c=entry_contract(kernel,adt,window,frequency,affinity);commands,size=struct.unpack_from('<2I',kernel,16);at=32;segments=[];symtab=None
 for _ in range(commands):
  cmd,n=struct.unpack_from('<2I',kernel,at)
  if cmd==0x19:
   va,memory,offset,data=struct.unpack_from('<4Q',kernel,at+24);prot=struct.unpack_from('<I',kernel,at+60)[0]
   if data:segments.append((va,data,offset,prot))
  if cmd==2:symtab=struct.unpack_from('<4I',kernel,at+8)
  at+=n
 assert symtab
 symoff,count,stroff,strbytes=symtab;assert symoff+count*16<=len(kernel) and stroff+strbytes<=len(kernel);symbols={}
 for i in range(count):
  string,typ,sect,desc,value=struct.unpack_from('<IBBHQ',kernel,symoff+i*16)
  if string>=strbytes or not typ&0xe:continue
  end=kernel.index(0,stroff+string,stroff+strbytes);name=kernel[stroff+string:end].decode()
  symbols[name]=value
 def read(v,n,execute=False):
  hits=[s for s in segments if s[0]<=v and v+n<=s[0]+s[1] and (not execute or s[3]&4)];assert len(hits)==1,(hex(v),n)
  va,data,offset,prot=hits[0];return kernel[offset+v-va:offset+v-va+n]
 def words(v,n):return list(struct.unpack('<'+str(n)+'I',read(v,n*4,True)))
 start=symbols['_start_first_cpu'];assert start==c['first_cpu_virtual'];code=words(start,256);end=code.index(0xd65f03c0)+1;code=code[:end]
 assert code[-3:]==[0x8b160280,0xcb170000,0xd65f03c0]
 assert code[7:12]==[0xf9400696,0xf9400a97,0xf9400e98,code[10],0xf9423a9a]
 # The exact linked clearing loop bounds the only original memory writes.
 assert [0xd2800202,0xd377d842,0xf8008420,0xf1000442,0x54ffffc1] in [code[i:i+5] for i in range(len(code)-4)]
 assert 0x9140432a in code and code.count(0x9140432a)==2
 ttb=symbols['_set_mmu_ttb'];ttbcode=words(ttb,4);assert ttbcode==[0xd5033b9f,0xd5182000,0xd5033fdf,0xd65f03c0]
 sctlr_at=code.index(0xd5181000);movs=code[sctlr_at-4:sctlr_at];sctlr=0;shifts=set()
 for w in movs:
  assert w&0xff80001f==0xf2800000
  shift=((w>>21)&3)*16;shifts.add(shift);sctlr|=((w>>5)&65535)<<shift
 assert shifts=={0,16,32,48}
 mair_at=code.index(0xd518a200);begin=max(i for i in range(mair_at) if code[i]==0xaa1f03e0);regs={0:0,1:0}
 for w in code[begin:mair_at]:
  if w==0xaa1f03e0:regs[0]=0
  elif w&0xff80001f==0xd2800001:regs[1]=((w>>5)&65535)<<(((w>>21)&3)*16)
  elif w==0xaa010000:regs[0]|=regs[1]
  else:raise AssertionError('Unrecognized MAIR construction '+hex(w))
 tables=symbols['_bootstrap_pagetables'];assert read(tables,65536)==bytes(65536)
 arm=symbols['_arm_init'];[armop]=words(arm,1);assert armop==0xd10343ff
 low=symbols['_LowExceptionVectorBase'];high=symbols['_ExceptionVectorsBase'];assert not low%4096 and not high%2048
 read(low,4096,True);read(high,2048,True)
 tcr=struct.unpack('<Q',read(symbols['_sysreg_restore'],8))[0]
 # Original start.s begins its bootstrap mappings at the native Mach header,
 # which follows imported prelink segments in the combined image.
 header=symbols['__mh_execute_header'];assert struct.unpack_from('<I',read(header,28),24)[0]&0x80000000==0
 skip=header-window['virtual_base'];assert 0<=skip<254*1048576 and skip%4096==0
 assert [0xcb170012,0xcb120318,0x8b1202d6,0x8b1202f7] in [code[i:i+4] for i in range(len(code)-3)]
 values=[MAGIC,2,arm,low,high,tables,65536,tcr,regs[0],sctlr,symbols['_excepstack_top'],symbols['_intstack_top'],armop,start,len(code)*4,zlib.crc32(read(start,len(code)*4)),ttb,16,zlib.crc32(read(ttb,16)),1,skip]
 policy=dict(zip(POLICY,values));raw=struct.pack('<21Q',*values)
 base=window['virtual_base'];pa=c['entry']-c['xnu_entry_virtual']
 contract=dict(policy=policy,policy_sha256=sha(raw),kernel_sha256=sha(kernel),entry=c['entry'],args=c['args'],frequency=frequency,affinity=affinity,physical_delta=pa,mmu_enable_pa=start+sctlr_at*4+pa,
  physical_base=base+pa,virtual_base=base,window_bytes=window.get('window_bytes',256*1048576),segment_count=c['segment_count'],arm_init_pa=arm+pa,low_vectors_pa=low+pa,high_vectors_pa=high+pa,tables_pa=tables+pa,
  start_machine_code_sha256=sha(read(start,len(code)*4)),ttb_machine_code_sha256=sha(read(ttb,16)),
  instrumentation='Original low and normal vector entries relay through the physical kernel alias; first arm_init instruction is BRK; all modified code and bootstrap tables restored')
 return raw,contract

def decode(raw,contract):
 assert len(raw)==72*8
 d=dict(zip(FIELDS,struct.unpack('>72Q',raw)));p=contract['policy'];early=contract.get('early');e=early['policy'] if early else None
 checkpoint=e['checkpoint'] if early else p['arm_init'];opcode=e['opcode'] if early else p['arm_opcode'];pmap=bool(e and e['version']>=2)
 assert d['version']==(2 if pmap else 1) and d['status']==3 and d['armed']==d['trap_count']==1 and not d['error']
 for n in ['entry','frequency','affinity']:assert d[n]==contract[n],n
 assert d['checkpoint_va']==d['elr']==checkpoint and d['original_instruction']==opcode and d['probe_instruction']==0xd42a6a20 and d['esr']==0xf2005351
 if early and not pmap:assert d['x0']==0 and d['x1']==e['const_args']
 elif e and e['version']==3 and e['reserved2']==0:assert d['x0']==e['const_args']
 elif not early:assert d['x0']==contract['args']-contract['physical_delta'] and d['x20']==contract['args'] and d['x21']==0
 assert d['expected_virt_base']==contract['virtual_base'] and d['expected_phys_base']==contract['physical_base'] and d['expected_mem_bytes']==contract['window_bytes']
 # arm_init owns x22-x25 until its epilogue; at C checkpoints inspect
 # the real copied boot_args and page tables instead of caller register values.
 if not early:
  assert d['x22']==contract['virtual_base']+p.get('bootstrap_skip',0) and d['x23']==contract['physical_base']+p.get('bootstrap_skip',0) and d['x24']==contract['window_bytes']-p.get('bootstrap_skip',0) and d['x25']==contract['tables_pa']
 assert d['tables']==contract['tables_pa'] and d['tables_bytes']==p['tables_bytes']==65536
 assert ((e and e['version']>=8) or d['sp']==p['exception_sp']) and d['lr']==(e['return_va'] if early else p['arm_init'])
 if e and e['version']>=5:
  # Exact dynamic stack is mandatory in decode_thread, including page walks.
  assert e['frame_bytes']==(contract['early']['observer_frame_bytes'] if e['reserved2']==20 else 0 if e['reserved2']==11 else 368 if e['reserved2']==19 else 80) and d['interrupted_sp']%16==0
  if e['reserved2']==11:assert d['x20']==checkpoint
 else:assert d['interrupted_sp']==p['interrupt_sp']-(e['frame_bytes'] if early else 0)
 assert d['sctlr']==d['expected_sctlr']==p['sctlr'] and d['sctlr']&0x1005==0x1005 and d['cache_off_sctlr']&0x1005==0
 assert d['vbar']==p['high_vectors'] and d['vector_slot']==0 and d['spsr']&0x3df==(0x204 if e and e['version']>=6 and e['reserved2']!=20 else 0x3c4) and d['current_el']==4 and d['daif']==0x3c0
 assert d['tcr']==d['expected_tcr']==p['tcr'] and d['mair']==d['expected_mair']==p['mair']
 if pmap:
  assert d['ttbr0']!=d['ttbr1'] and all(v%4096==0 and contract['physical_base']<=v<v+4096<=contract['physical_base']+contract['window_bytes'] for v in [d['ttbr0'],d['ttbr1']])
 else:assert d['ttbr0']==contract['tables_pa'] and d['ttbr1']==contract['tables_pa']+4096
 assert d['relay_pa']==(contract['early']['compiled']['relay']+contract['physical_delta'] if e and e['version']>=7 else contract['low_vectors_pa']+2048)
 assert d['virtual_translation']==(early['checkpoint_pa'] if early else contract['arm_init_pa']) and d['physical_translation']==(0 if pmap else d['virtual_translation'])
 assert d['tables_crc_before']==zlib.crc32(bytes(65536)) and d['tables_crc_before']!=d['tables_crc_after'] and d['tables_changed_count']>0
 assert all(d[n]==1 for n in ['patch_restored','tables_restored','mmu_restored','args_ok'])
 assert d['segments_ok']==d['zero_ok']==contract.get('segment_count',10) and d['counter']>0
 return dict(**d,arm_init_entry_reached=True,arm_init_c_body_executed=bool(early),xnu_bootstrap_mmu_verified=True,full_xnu_boot_verified=False)


def audit_tables(raw,d,contract):
 assert len(raw)==65536 and zlib.crc32(raw)==d['tables_crc_after']
 base=d['tables'];used=set();entries=[]
 if d['version']==2:d=dict(d,ttbr0=base,ttbr1=base+4096)
 def walk(root,address,high):
  bits=64-((d['tcr']>>(16 if high else 0))&63);assert bits==38
  cursor=address&((1<<bits)-1);table=root&0x0000fffffffff000
  for level in range(1,4):
   assert base<=table and table+4096<=base+65536
   used.add(table);shift=12+9*(3-level);index=(cursor>>shift)&511
   e=struct.unpack_from('<Q',raw,table-base+index*8)[0];assert e&1
   if level<3 and e&3==3:table=e&0x0000fffffffff000;continue
   assert level==2 and e&3==1 and e&0xfff==0x601
   mask=(1<<shift)-1;return (e&0x0000fffffffff000&~mask)|(cursor&mask)
  raise AssertionError('No block translation')
 skip=contract['policy'].get('bootstrap_skip',0)
 phys=(contract['physical_base']+skip)&~0x1fffff;virt=(contract['virtual_base']+skip)&~0x1fffff
 blocks=(contract['window_bytes']-skip)//0x200000
 for i in range(blocks):
  a=phys+i*0x200000;v=virt+i*0x200000
  for offset in [0,0x1fffff]:
   assert walk(d['ttbr0'],a+offset,False)==a+offset and walk(d['ttbr1'],v+offset,True)==a+offset
 assert walk(d['ttbr0'],contract['arm_init_pa'],False)==contract['arm_init_pa']
 assert walk(d['ttbr1'],contract['policy']['arm_init'],True)==contract['arm_init_pa']
 assert walk(d['ttbr1'],contract['args']-contract['physical_delta'],True)==contract['args']
 for page in range(16):
  at=base+page*4096;words=struct.unpack_from('<512Q',raw,page*4096)
  if at not in used:assert not any(words)
  else:
   for i,e in enumerate(words):
    if e:entries.append((at,i,e))
 assert len(used)==4 and len(entries)==2+blocks*2
 return dict(passed=True,bytes=len(raw),crc32=zlib.crc32(raw),sha256=sha(raw),table_pages=sorted(used),nonzero_descriptors=len(entries),block_pairs=blocks,
  original_tables_restored=d['tables_restored']==1,scope='Original bootstrap 2MiB blocks; partial base/end granules are not a full final kernel pmap claim')
