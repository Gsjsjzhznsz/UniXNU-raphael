#!/usr/bin/env python3
"""Independent route result validation; does not claim an IRQ handler ran."""
import struct
from ppi_probe import resource
FIELDS='version status reason intid flags sgi_base frequency original_dist dist_during restored_dist original_igrpen igrpen_during restored_igrpen original_ctl original_cval restored_ctl restored_cval deadline start_counter end_counter ctl_during hppir_before hppir_during hppir_after pending_before pending_during pending_after active_before active_after enabled_before enabled_during enabled_after daif_before daif_after polls clear_polls rwp_polls mmio_reads mmio_writes sys_reads sys_writes restore_ok trap_esr trap_elr'.split()
def decode(raw,blob,gic,enable_map,icc,expect_fault=False,expect_irq=False):
 assert len(raw)==len(FIELDS)*8
 r=dict(zip(FIELDS,struct.unpack('>'+str(len(FIELDS))+'Q',raw)));intid,flags=resource(blob)
 assert r['version']==1 and r['restore_ok']==1
 assert (r['status'],r['reason'])==((3,2) if expect_fault else (6,0))
 assert enable_map['passed'] and enable_map['all_observed_disabled'] and enable_map['status']==3
 assert r['intid']==intid and r['flags']==flags and 16<=intid<32
 assert r['sgi_base']==gic['frames'][gic['boot_index']]['base']+0x10000
 assert r['original_dist']==gic['ctlr']==r['restored_dist'] and r['original_dist'] in [0x10,0x50]
 assert r['dist_during']==r['original_dist']|2
 assert r['original_igrpen']==r['restored_igrpen']==0
 assert r['original_ctl']==icc['cntp_ctl'] and r['original_cval']==icc['cntp_cval']
 assert r['original_ctl']<=7 and not(r['original_ctl']&1) and r['restored_ctl']<=7
 assert not((r['original_ctl']^r['restored_ctl'])&3) and r['original_cval']==r['restored_cval']
 assert r['frequency']==icc['cntfrq'] and 1000<=r['frequency']<=1000000000
 assert r['deadline']==r['start_counter']+r['frequency']//100
 mask=1<<intid
 assert r['hppir_before']==r['hppir_after']==1023
 assert not(r['pending_before']&mask) and not((r['pending_after']^r['pending_before'])&mask)
 assert r['active_before']==r['active_after']==r['enabled_before']==r['enabled_after']==0 and r['enabled_during']==mask
 assert r['daif_before']&0x3c0==r['daif_after']&0x3c0==0x3c0
 assert 1<=r['clear_polls']<=1000000 and 2<=r['rwp_polls']<=2000000
 assert r['mmio_writes']==4
 if expect_fault:
  assert r['igrpen_during']==0 and r['sys_writes']==6 and r['trap_esr']>>26==0 and r['trap_elr']>0
  assert r['polls']==r['hppir_during']==r['ctl_during']==r['pending_during']==0
 else:
  assert r['igrpen_during']==1 and r['sys_writes']==7 and r['trap_esr']==r['trap_elr']==0
  assert r['deadline']<=r['end_counter']<=r['start_counter']+r['frequency']//10
  assert r['ctl_during']==5 and r['hppir_during']==intid and r['pending_during']&mask
  assert 1<=r['polls']<=1000000 and r['mmio_reads']>=15 and r['sys_reads']>=18
 return dict(**r,passed=True,physical_timer_route_observed=not expect_fault,source_withdrawal_observed=not expect_fault,registers_restored=True,injected_undefined_recovered=expect_fault,
             cpu_irq_unmasked=expect_irq,interrupt_acknowledged=expect_irq,irq_handler_executed=expect_irq,complete_gic_ownership_proven=False)

def verify_result_storage(build):
 """Require the entire static wire record to have backing bytes in the XIP FD."""
 import json,re
 from inspect_diagnostic_fd import SEC_GUID
 report=json.loads((build/'fd-inspection.json').read_text());assert report['passed']
 sec=next(f for f in report['files'] if f['guid']==SEC_GUID)
 section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 path=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map'
 match=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+mTimerRoute\s*$',path.read_text());assert match
 rva=int(match[1],16);data=next(s for s in pe['sections'] if s['name']=='.data')
 size=len(FIELDS)*8
 assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes']
 assert data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
 raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
 offset=section['offset']+4+rva
 assert offset+size<=section['offset']+section['bytes'] and raw[offset:offset+size]==bytes(size)
 return dict(bytes=size,rva=rva,fd_offset=offset,physical_address=pe['image_base']+rva,
             linker_map=str(path.relative_to(build)),materialized_zero_data=True,within_sec_xip_pe=True)
