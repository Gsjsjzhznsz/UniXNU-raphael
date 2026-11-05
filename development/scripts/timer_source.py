#!/usr/bin/env python3
"""Independent masked physical-timer source/result validation; no IRQ claim."""
import struct
FIELDS='version status reason frequency original_ctl original_cval start_counter deadline observed_ctl observed_cval end_counter polls restored_ctl restored_cval write_calls trap_esr trap_elr'.split()
def decode(raw,frequency,expect_fault=False):
 assert len(raw)==17*8
 r=dict(zip(FIELDS,struct.unpack('>17Q',raw)))
 assert r['version']==1 and r['frequency']==frequency and 1000<=frequency<=1000000000
 assert r['original_ctl']<=7 and not(r['original_ctl']&1)
 assert r['restored_ctl']<=7 and (r['restored_ctl']^r['original_ctl'])&3==0 and r['restored_cval']==r['original_cval']
 assert r['write_calls']==5 and r['deadline']==r['start_counter']+frequency//100
 assert r['observed_cval']==r['deadline'] and r['start_counter']<=((1<<64)-1)-frequency//10
 if expect_fault:
  assert r['status']==3 and r['reason']==3 and r['trap_esr']>>26==0 and r['trap_elr']>0 and r['polls']==0
 else:
  assert r['status']==8 and r['reason']==0 and r['trap_esr']==r['trap_elr']==0
  assert r['observed_ctl']==7 and 1<=r['polls']<=1000000
  assert r['deadline']<=r['end_counter'] and r['end_counter']-r['start_counter']<=frequency//10
 return dict(**r,passed=True,physical_source_expiration_verified=not expect_fault,simulated_write_failure=expect_fault,
             cntp_registers_restored=True,gic_written=False,cntv_written=False,irq_delivery_verified=False)
