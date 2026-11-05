#!/usr/bin/env python3
"""Check bounded boot-CPU GIC restoration against the actual ADT resources."""
import struct
REGISTERS='dist waker group modifier enabled pending active config priority0 priority_timer sre ctlr pmr bpr1 igrpen1 hppir1'.split()
def decode(raw,resources):
 assert len(raw)==56*8
 words=struct.unpack('>56Q',raw);names='version status dist rdist timer_id restore_ok changed_words reserved'.split();d=dict(zip(names,words[:8]))
 assert d['version']==1 and d['status']==3 and d['restore_ok']==1 and d['reserved']==0
 regs=resources['gic_registers'];assert d['dist']==regs[0][0] and regs[1][0]<=d['rdist']<d['rdist']+0x20000<=regs[1][0]+regs[1][1]
 assert d['timer_id']==resources['timer_intid'] and 16<=d['timer_id']<=31
 before,observed,after=words[8:24],words[24:40],words[40:56]
 assert before[:15]==after[:15] and before[6]==0 and before[10]&1
 assert d['changed_words']==sum(x!=y for x,y in zip(before,observed))
 return dict(**d,saved=dict(zip(REGISTERS,before)),observed=dict(zip(REGISTERS,observed)),restored=dict(zip(REGISTERS,after)),bounded_boot_cpu_gic_restored=True,normal_xnu_irq_verified=False,complete_gic_ownership_proven=False)
