#!/usr/bin/env python3
"""Decode two-pass standard GICv3 enable views; never assert complete ownership."""
import struct
HEADER='version status reason read_count spi_words frame_count enabled_spi_or enabled_local_or lpi_enabled_or changed_words distributor_before distributor_after all_observed_disabled'.split()
WORDS=60

def decode(raw,gic):
 assert len(raw)==WORDS*8
 v=list(struct.unpack('>60Q',raw));r=dict(zip(HEADER,v[:13]))
 assert r['version']==1 and r['status'] in [3,4] and r['reason']==0
 assert gic['pidr2']&0xf0==0x30 and not(gic['typer']&0xfb00)
 assert r['spi_words']==gic['typer']&31 and r['frame_count']==gic['frame_count'] and 1<=r['frame_count']<=8
 assert r['read_count']==3+2*(r['spi_words']+2*r['frame_count'])
 assert r['distributor_before']==gic['ctlr'] and r['distributor_after']<=0xffffffff
 spi,local,ctlr=v[13:44],v[44:52],v[52:60]
 assert not any(spi[r['spi_words']:]+local[r['frame_count']:]+ctlr[r['frame_count']:])
 assert all(x<=0xffffffff for x in spi+local+ctlr)
 assert r['enabled_spi_or']<=0xffffffff and r['enabled_local_or']<=0xffffffff and r['lpi_enabled_or']<=1
 def bit_or(values):
  out=0
  for x in values:out|=x
  return out
 a,b,c=bit_or(spi),bit_or(local),bit_or([x&1 for x in ctlr])
 if r['status']==3:
  assert r['changed_words']==0 and r['distributor_before']==r['distributor_after']
  assert (r['enabled_spi_or'],r['enabled_local_or'],r['lpi_enabled_or'])==(a,b,c)
 else:
  assert 1<=r['changed_words']<=r['spi_words']+2*r['frame_count']+1
  assert r['enabled_spi_or']|a==r['enabled_spi_or'] and r['enabled_local_or']|b==r['enabled_local_or'] and r['lpi_enabled_or']|c==r['lpi_enabled_or']
 disabled=bool(r['status']==3 and not(r['distributor_before']&0x80000003) and r['distributor_before']&0x10 and not(a|b|c))
 assert r['all_observed_disabled']==int(disabled)
 return dict(**r,spi_enable_words=spi,local_enable_words=local,redistributor_ctlr=ctlr,passed=True,
             atomic_snapshot=False,secure_interrupts_observed=False,interrupts_written=False,
             irq_delivery_verified=False,complete_gic_ownership_proven=False)


def verify_result_storage(build):
 """Require the entire static wire record to have backing bytes in the XIP FD."""
 import json,re
 from inspect_diagnostic_fd import SEC_GUID
 report=json.loads((build/'fd-inspection.json').read_text());assert report['passed']
 sec=next(f for f in report['files'] if f['guid']==SEC_GUID)
 section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 path=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map'
 match=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+mGicEnableMap\s*$',path.read_text());assert match
 rva=int(match[1],16);data=next(s for s in pe['sections'] if s['name']=='.data')
 size=WORDS*8
 assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes']
 assert data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
 raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
 offset=section['offset']+4+rva
 assert offset+size<=section['offset']+section['bytes'] and raw[offset:offset+size]==bytes(size)
 return dict(bytes=size,rva=rva,fd_offset=offset,physical_address=pe['image_base']+rva,
             linker_map=str(path.relative_to(build)),materialized_zero_data=True,within_sec_xip_pe=True)
