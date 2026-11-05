#!/usr/bin/env python3
"""Independent wire parser for bounded, non-acknowledging system-register reads."""
import struct
HEADER='version status attempted completed failed_selector trap_esr trap_elr'.split()
REGISTERS='current_el daif mpidr sre ctlr pmr bpr1 igrpen1 rpr hppir1 cntp_ctl cntp_cval cntv_ctl cntv_cval cntkctl cntfrq'.split()
FAULT='injected_fault_recovered injected_fault_esr injected_fault_elr'.split()
FIELDS=HEADER+REGISTERS+FAULT

def decode(raw,mpidr,frequency,expect_fault=False):
 assert len(raw)==len(FIELDS)*8
 result=dict(zip(FIELDS,struct.unpack('>'+'Q'*len(FIELDS),raw)))
 r=result;assert r['version']==1 and r['status']==5
 assert r['attempted']==r['completed']==16 and r['failed_selector']==(1<<64)-1
 assert r['trap_esr']==r['trap_elr']==0
 assert r['current_el']==4 and r['daif']&0x3c0==0x3c0 and r['mpidr']==mpidr
 assert r['sre']&1 and r['sre']<=0xffffffff and r['ctlr']<=0xffffffff
 assert r['pmr']<=255 and r['bpr1']<=7 and r['igrpen1']<=1 and r['rpr']<=255
 assert r['hppir1']<=0xffffff and r['cntp_ctl']<=7 and r['cntv_ctl']<=7 and r['cntkctl']<=0xffffffff
 assert r['cntfrq']==frequency and frequency>0
 if expect_fault:
  assert r['injected_fault_recovered']==1 and r['injected_fault_esr']>>26==0 and r['injected_fault_elr']>0
 else:assert not any(r[k] for k in FAULT)
 return dict(**r,passed=True,priority_bits=((r['ctlr']>>8)&7)+1,eoi_mode=(r['ctlr']>>1)&1,
             interrupts_acknowledged=False,icc_or_timer_written=False,irq_delivery_verified=False,
             register_writes_restored=False,atomic_snapshot=False)
