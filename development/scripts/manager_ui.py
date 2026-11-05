#!/usr/bin/env python3
"""Independent visible-manager framebuffer wire, with explicit QEMU-only absence."""
import json,re,struct
from entry_probe import sha
FIELDS='version status base width height stride frame_pixels pixels_changed pixels_restored mismatches input_ready query_verified active backup fallback pixel_format'.split()
def decode(raw,stage,gop=None,qemu_model=False):
 assert len(raw)==128
 d=dict(zip(FIELDS,struct.unpack('>16Q',raw)))
 assert d['version']==1
 if stage<6:
  assert stage in [2,3] and d['status']==1 and all(d[k]==0 for k in FIELDS[2:])
  verified=False
 elif qemu_model:
  assert d['status']==5 and all(d[k]==0 for k in FIELDS[2:]);verified=False
 else:
  assert d['status']==4 and gop and gop['protocol_installed'] and gop['mapped_read_verified']
  for k in ['base','width','height','stride']:assert d[k]==gop[k]
  assert d['pixel_format']==1 and d['base']>0
  assert d['frame_pixels']==d['width']*d['height']==d['pixels_restored'] and 0<d['pixels_changed']<=d['frame_pixels']
  assert d['input_ready']==d['query_verified']==1 and d['mismatches']==d['active']==d['backup']==d['fallback']==0
  verified=True
 return dict(**d,passed=True,manager_framebuffer_changed_and_restored=verified,qemu_missing_hardware_model=stage==6 and qemu_model,human_visibility_verified=False,physical_keys_verified=False,xnu_executed=False)
def verify_result_storage(build):
 from inspect_diagnostic_fd import SEC_GUID
 fd=json.loads((build/'fd-inspection.json').read_text());sec=next(f for f in fd['files'] if f['guid']==SEC_GUID);section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 mp=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map'
 m=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+mManagerUi\s*$',mp.read_text());assert m
 rva=int(m[1],16);size=352;data=next(s for s in pe['sections'] if s['name']=='.data')
 assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes'] and data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
 raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes();offset=section['offset']+4+rva
 assert offset+size<=section['offset']+section['bytes'] and raw[offset:offset+size]==bytes(size)
 return dict(bytes=size,rva=rva,fd_offset=offset,physical_address=pe['image_base']+rva,materialized_zero_data=True)
