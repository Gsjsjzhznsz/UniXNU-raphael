#!/usr/bin/env python3
"""Independent first-instruction contract. No board address is hardcoded."""
import struct
from entry_probe import sha
from native_load import make_policy
FIELDS='version status armed_count trap_count entry checkpoint original_instruction probe_instruction esr elr far spsr x0 x1 x20 x21 sp sctlr current_el daif counter vbar tcr ttbr0 ttbr1 mair saved_sctlr saved_vbar saved_tcr saved_ttbr0 saved_ttbr1 saved_mair frequency affinity patch_restored mmu_restored exit_completed error prefix_instructions vector_slot'.split()
PREFIX=[0xd510109f,0xd5034fdf,0xaa0003f4,0xd2800015]
PROBE=0xd42a6a00

def make_contract(kernel, adt, window, frequency, affinity):
    _,c=make_policy(kernel,adt,window,frequency,affinity,exit_complete=True)
    commands,size=struct.unpack_from('<2I',kernel,16);at=32;segments=[];entry=None
    for _ in range(commands):
        command,length=struct.unpack_from('<2I',kernel,at)
        if command==0x19:
            va,memory,offset,data=struct.unpack_from('<4Q',kernel,at+24)
            protection=struct.unpack_from('<I',kernel,at+60)[0]
            if data:segments.append((va,data,offset,protection))
        if command==5:entry=struct.unpack_from('<Q',kernel,at+272)[0]
        at+=length
    def words(address,count):
        choices=[s for s in segments if s[3]&4 and s[0]<=address and address+count*4<=s[0]+s[1]]
        assert len(choices)==1,'Instruction range is not inside exactly one executable file segment'
        va,data,offset,protection=choices[0]
        return list(struct.unpack_from('<'+str(count)+'I',kernel,offset+address-va))
    [branch]=words(entry,1);assert branch&0xfc000000==0x14000000
    displacement=branch&0x3ffffff
    if displacement&0x2000000:displacement-=0x4000000
    target=entry+displacement*4
    prefix=words(target,5);assert prefix[:4]==PREFIX and prefix[4]==0xf0ffffe0
    checkpoint=c['entry']+target-entry+16
    return dict(kernel_sha256=sha(kernel),entry=c['entry'],checkpoint=checkpoint,args=c['args'],
        original_instruction=prefix[4],probe_instruction=PROBE,frequency=frequency,affinity=affinity,
        xnu_entry_virtual=entry,first_cpu_virtual=target,first_cpu_prefix=prefix,segment_count=len(c['segments']),
        executed_original_instructions=['b start_first_cpu','msr OSLAR_EL1, xzr','msr DAIFSet, #15','mov x20, x0','mov x21, #0'],
        instrumentation='One loaded ADRP replaced after original CRC verification; restored before post-execution CRC verification')

def decode(raw,contract,layout):
    assert len(raw)==320
    d=dict(zip(FIELDS,struct.unpack('>40Q',raw)))
    assert d['version']==1 and d['status']==3 and d['armed_count']==d['trap_count']==1 and d['error']==0
    for name in ['entry','checkpoint','original_instruction','probe_instruction','frequency','affinity']:assert d[name]==contract[name],name
    assert d['elr']==d['checkpoint'] and d['esr']==0xf2005350
    assert d['x0']==d['x20']==contract['args'] and d['x21']==0 and d['x1']==d['entry']
    assert d['current_el']==4 and d['sctlr']&0x1005==0 and d['spsr']&0x3df==0x3c5
    assert d['vector_slot'] in [0,4] and d['prefix_instructions']==5 and d['daif']==0x3c0
    assert d['saved_sctlr']&0x1005==0x1005 and d['patch_restored']==d['mmu_restored']==d['exit_completed']==1
    for name in ['tcr','ttbr0','ttbr1','mair']:assert d[name]==d['saved_'+name],name
    lo=layout['ArenaBase'];hi=lo+layout['ArenaSize']-20*1048576
    assert lo<=d['vbar']<hi and d['vbar']%2048==0 and lo<=d['saved_vbar']<hi
    assert layout['StackBase']<=d['sp']<=layout['StackBase']+layout['StackSize'] and d['counter']>0
    return dict(**d,xnu_instrumented_prefix_executed=True,original_instruction_count=5,
        full_xnu_boot_verified=False,arm_init_reached=False)
