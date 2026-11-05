#!/usr/bin/env python3
"""Validate the one-shot IRQ wire, linked instruction window and saved stack."""
import struct
FIELDS='version status expected_id frequency start_counter deadline end_counter polls entries observed_id irq_counter irq_elr irq_spsr daif_before daif_unmasked daif_after eoi_count source_masked spurious_count unexpected_id spsel stack_pointer handler_sp active_cleared'.split()
def linked_window(build):
 import json,re
 from inspect_diagnostic_fd import SEC_GUID
 fd=json.loads((build/'fd-inspection.json').read_text());assert fd['passed']
 sec=next(f for f in fd['files'] if f['guid']==SEC_GUID);pe=next(s['pe'] for s in sec['sections'] if 'pe' in s)
 mp=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map';text=mp.read_text()
 result={}
 for key,name in [('open','RaphaelIrqWindowOpen'),('close','RaphaelIrqWindowClose'),('handler','RaphaelTimerIrqHandler')]:
  m=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+'+name+r'\s*$',text);assert m,name
  rva=int(m[1],16);segment=next(s for s in pe['sections'] if s['rva']<=rva<s['rva']+s['virtual_bytes'])
  assert segment['name']=='.text' and segment['rva']==segment['raw_offset'];result[key]=pe['image_base']+rva
 assert result['open']<result['close']<result['handler']
 return result

def decode(raw,route,icc,layout,window):
 assert len(raw)==24*8
 r=dict(zip(FIELDS,struct.unpack('>24Q',raw)))
 assert r['version']==1 and r['status']==5 and r['entries']==1
 assert route['passed'] and route['registers_restored'] and route['restore_ok']==1
 assert r['expected_id']==r['observed_id']==route['intid'] and 16<=r['expected_id']<32
 assert r['frequency']==icc['cntfrq']==route['frequency'] and icc['eoi_mode']==0
 assert r['deadline']==r['start_counter']+r['frequency']//10
 assert r['start_counter']<=r['irq_counter']<=r['end_counter']<=r['deadline']
 assert 0<=r['polls']<=1000000
 assert window['open']<=r['irq_elr']<=window['close']
 assert r['irq_spsr']&0x3c0==r['daif_unmasked']==0x340
 assert r['daif_before']==r['daif_after']==0x3c0 and r['spsel']==1
 assert r['eoi_count']==r['source_masked']==r['active_cleared']==1
 assert r['spurious_count']==r['unexpected_id']==0
 assert not(r['stack_pointer']&15) and r['handler_sp']==r['stack_pointer']-80
 assert layout['StackBase']<=r['handler_sp']<r['stack_pointer']<=layout['StackBase']+layout['StackSize']
 return dict(**r,passed=True,single_irq_handler_verified=True,source_masked_before_eoi=True,
             expected_ppi_acknowledged_once=True,eoi_mode_zero_only=True,full_timer_arch_verified=False)

def verify_result_storage(build):
 import json,re
 from inspect_diagnostic_fd import SEC_GUID
 fd=json.loads((build/'fd-inspection.json').read_text());assert fd['passed']
 sec=next(f for f in fd['files'] if f['guid']==SEC_GUID);section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 mp=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map';text=mp.read_text()
 data=next(s for s in pe['sections'] if s['name']=='.data');raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
 records={}
 for name,size in [('mTimerIrq',192),('RaphaelActiveIrqResult',8)]:
  m=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+'+name+r'\s*$',text);assert m,name
  rva=int(m[1],16);offset=section['offset']+4+rva
  assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes'] and data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
  assert offset+size<=section['offset']+section['bytes'] and raw[offset:offset+size]==bytes(size)
  records[name]=dict(bytes=size,rva=rva,physical_address=pe['image_base']+rva,fd_offset=offset,materialized_zero_data=True)
 return dict(records=records,linked_window=linked_window(build),within_sec_xip_pe=True)
