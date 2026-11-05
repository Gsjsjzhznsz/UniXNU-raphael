#!/usr/bin/env python3
"""Independent mapped-RAM wire; never reinterpret the existing MMU-off record."""
import json,re,struct
from entry_probe import ROOT,sha
FIELDS=('version status reason base bytes stride requested attempted completed active_address before_digest digest nonzero start_counter end_counter frequency current_el sctlr daif read_translations write_denied par_preserved first_read_par last_read_par last_write_par original_par restored_par').split()
MASK=(1<<64)-1
PA_MASK=0x0000fffffffff000

def decode(raw,before,stage):
 assert len(raw)==27*8 and stage in [2,3]
 d=dict(zip(FIELDS,struct.unpack('>27Q',raw)));assert before['passed']
 assert d['version']==1 and d['reason']==0
 for k in ['base','bytes','stride','requested']:assert d[k]==before[k]
 assert d['before_digest']==before['digest']
 if stage==2:
  assert d['status']==1
  assert all(d[k]==0 for k in FIELDS if k not in ['version','status','base','bytes','stride','requested','before_digest'])
 else:
  assert d['status']==3 and d['requested']==d['attempted']==d['completed']==256
  assert d['active_address']==d['base']+d['bytes']-8
  assert d['read_translations']==d['write_denied']==d['par_preserved']==256
  assert d['digest']==before['digest'] and d['nonzero']==before['nonzero']
  assert d['frequency']==before['frequency'] and before['end_counter']<=d['start_counter']<=d['end_counter']<=d['start_counter']+d['frequency']//10
  assert d['current_el']==4 and d['sctlr']&0x1005==0x1005 and d['daif']&0x3c0==0x3c0
  for key,address in [('first_read_par',d['base']),('last_read_par',d['active_address'])]:
   assert d[key]&1==0 and d[key]&PA_MASK==address&~4095 and d[key]>>56==0xff
  assert d['last_write_par']&1 and d['original_par']==d['restored_par']
 return dict(**d,passed=True,mapped_reads_verified=stage==3,write_permission_queries_only=True,ram_written=False,
             allocator_enabled=False,ownership_proven=False,entire_window_tested=False)

def verify_storage(build):
 from inspect_diagnostic_fd import SEC_GUID
 report=json.loads((build/'fd-inspection.json').read_text());assert report['passed']
 sec=next(f for f in report['files'] if f['guid']==SEC_GUID);section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 directory=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
 text=(directory/'RaphaelSec.dll.map').read_text();data=next(s for s in pe['sections'] if s['name']=='.data')
 results={}
 for name,size in [('mRamMapped',216),('mSavedPar',8),('mParActive',8)]:
  match=re.search(r'(?m)^([0-9a-f]+)\s+.*\s'+name+r'$',text);assert match,name
  rva=int(match[1],16)
  assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes'] and data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
  offset=section['offset']+4+rva;raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
  assert raw[offset:offset+size]==bytes(size)
  results[name]=dict(bytes=size,rva=rva,fd_offset=offset,materialized_zero_data=True)
 return results
