#!/usr/bin/env python3
"""Explicit cache metadata plus the unchanged reversible-page engine wire."""
import struct,json,re
from entry_probe import ROOT
from ram_write_probe import decode as decode_write
FIELDS=('version status reason base bytes pages current_el sctlr daif frequency read_write_translations par_preserved pre_page_sync post_page_sync map_restored restore_denials').split()
def decode(raw,before,mapped,policy,pages,stage,fault=False):
 assert len(raw)==39*8 and stage in [2,3] and 1<=pages<=65536
 d=dict(zip(FIELDS,struct.unpack('>16Q',raw[:128])))
 assert before['passed'] and mapped['passed'] and d['version']==1
 assert d['base']==before['base']==policy['base'] and d['bytes']==before['bytes']==policy['bytes'] and d['pages']==pages
 if stage==2:
  assert not fault and d['status']==1 and d['reason']==0 and raw[128:]==bytes(23*8)
  assert all(d[k]==0 for k in FIELDS if k not in ['version','status','base','bytes','pages'])
  write=None
 else:
  assert d['status']==(2 if fault else 3) and d['reason']==(3 if fault else 0)
  assert d['current_el']==4 and d['sctlr']&0x1005==0x1005 and d['daif']&0x3c0==0x3c0
  assert d['frequency']==before['frequency']==mapped['frequency']
  assert d['read_write_translations']==d['par_preserved']==d['restore_denials']==256 and d['map_restored']==1
  assert d['pre_page_sync']==(1 if fault else pages) and d['post_page_sync']==(1 if fault else 3*pages)
  write=decode_write(raw[128:],policy,pages,fault)
  assert write['frequency']==d['frequency'] and write['start_counter']>=mapped['end_counter']
 return dict(**d,passed=True,write=write,cache_maintenance_verified=stage==3,
  ram_written=stage==3,all_original_bytes_restored=stage==3,allocator_enabled=False,ownership_proven=False,cross_page_alias_tested=False)

def verify_storage(build):
 from ram_write_probe import verify_storage as verify_engine
 from inspect_diagnostic_fd import SEC_GUID
 result=dict(engine=verify_engine(build),cache={})
 report=json.loads((build/'fd-inspection.json').read_text());sec=next(f for f in report['files'] if f['guid']==SEC_GUID);section=next(s for s in sec['sections'] if 'pe' in s)
 data=next(s for s in section['pe']['sections'] if s['name']=='.data');directory=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
 mp=(directory/'RaphaelSec.dll.map').read_text();fd=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
 for name,size in [('mRamCache',176),('mCacheMapActive',8),('mCacheMapBase',8),('mCacheMapBytes',8),('mCacheState',8)]:
  match=re.search(r'(?m)^([0-9a-f]+)\s+.*\s'+name+'$',mp);assert match,name
  rva=int(match[1],16);assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes'] and data['rva']==data['raw_offset']
  offset=section['offset']+4+rva;assert fd[offset:offset+size]==bytes(size)
  result['cache'][name]=dict(bytes=size,rva=rva,fd_offset=offset,materialized_zero_data=True)
 return result
