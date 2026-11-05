#!/usr/bin/env python3
"""Independent PPI permission/result decoding with a fresh FDT-derived IRQ."""
import struct
from inspect_device import read_fdt,Error
from derive_interrupt_contract import analyze_tree
from qemu_arch_probe import parse_resources
FIELDS='version status reason intid flags sgi_base mask enabled_before enabled_during enabled_after active_before pending_before rwp_polls write_count ctlr_before ctlr_after read_count restore_ok pending_after active_after'.split()
def _resource(blob):
 root=read_fdt(blob)
 if 'linux,dummy-virt' in root.strings('compatible'):
  q=parse_resources(blob);return q['timer_phys'],4
 f=analyze_tree(root);e=f['timer_interrupts'][1];return e['intid'],e['specifier'][2]
def resource(blob):
 try:return _resource(blob)
 except Error as error:raise ValueError(str(error)) from error
def decode(raw,blob,gic):
 assert len(raw)==20*8
 r=dict(zip(FIELDS,struct.unpack('>20Q',raw)));intid,flags=resource(blob)
 assert r['version']==1 and r['status'] in [3,6] and r['reason']==0
 assert r['intid']==intid and r['flags']==flags and 16<=intid<32 and r['mask']==1<<intid
 assert r['sgi_base']==gic['frames'][gic['boot_index']]['base']+0x10000
 assert r['enabled_before']==gic['sgi']['enabled'] and r['enabled_before']&r['mask']==0
 assert r['active_before']&r['mask']==r['pending_before']&r['mask']==0
 expected=r['enabled_before']|(r['mask'] if r['status']==6 else 0)
 assert r['enabled_during']==expected and r['enabled_after']==r['enabled_before']
 assert r['ctlr_before']==gic['ctlr']==r['ctlr_after'] and r['ctlr_before']&0x80000003==0 and r['ctlr_before']&0x10
 assert 1<=r['rwp_polls']<=1000000 and r['write_count']==2 and r['read_count']==10+r['rwp_polls'] and r['restore_ok']==1
 assert (r['pending_after']^r['pending_before'])&r['mask']==(r['active_after']^r['active_before'])&r['mask']==0
 return dict(**r,passed=True,ppi_enable_writable=r['status']==6,enabled_bit_restored=True,
             distributor_written=False,group_or_priority_written=False,irq_delivery_verified=False)

def verify_result_storage(build):
 """The SEC static record must be fully materialized within its XIP PE section."""
 import json,re
 from inspect_diagnostic_fd import SEC_GUID
 report=json.loads((build/'fd-inspection.json').read_text());assert report['passed']
 sec=next(f for f in report['files'] if f['guid']==SEC_GUID)
 section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 path=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map'
 match=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+mPpiProbe\s*$',path.read_text());assert match
 rva=int(match[1],16);data=next(s for s in pe['sections'] if s['name']=='.data')
 assert data['rva']<=rva and rva+160<=data['rva']+data['virtual_bytes']
 assert data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
 raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
 offset=section['offset']+4+rva
 assert offset+160<=section['offset']+section['bytes'] and raw[offset:offset+160]==bytes(160)
 return dict(bytes=160,rva=rva,fd_offset=offset,physical_address=pe['image_base']+rva,
             linker_map=str(path.relative_to(build)),materialized_zero_data=True,within_sec_xip_pe=True)
