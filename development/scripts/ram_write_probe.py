#!/usr/bin/env python3
"""Independent transaction-wire checks; original words never enter the report."""
import json,re,struct
from entry_probe import ROOT,sha
FIELDS=('version status reason base bytes page_bytes requested_pages completed_pages active_page backup_words dirty restored_pages read_attempts write_attempts pattern_words pattern_mismatches restore_words restore_mismatches original_digest restore_digest start_counter end_counter frequency').split()
def decode(raw,policy,pages,fault=False):
 assert len(raw)==23*8
 d=dict(zip(FIELDS,struct.unpack('>23Q',raw)))
 assert d['version']==1 and d['status']==(2 if fault else 3) and d['reason']==0
 assert d['base']==policy['base'] and d['bytes']==policy['bytes'] and d['page_bytes']==4096
 assert 1<=pages<=65536 and d['requested_pages']==pages
 complete=0 if fault else pages;restored=1 if fault else pages
 assert d['completed_pages']==complete and d['restored_pages']==restored
 assert d['active_page']==d['base']+(0 if fault else pages-1)*4096
 assert d['backup_words']==d['dirty']==d['pattern_mismatches']==d['restore_mismatches']==0
 assert d['restore_words']==restored*512 and d['original_digest']==d['restore_digest']
 assert d['pattern_words']==(0 if fault else pages*1024)
 assert d['read_attempts']==(1024 if fault else pages*2048)
 assert d['write_attempts']==(769 if fault else pages*1536)
 assert 1000<=d['frequency']<=1000000000
 assert d['start_counter']<=d['end_counter']<=d['start_counter']+d['frequency']*8
 return dict(**d,passed=True,original_words_restored=True,entire_window_tested=pages==65536 and not fault,allocator_enabled=False,ownership_proven=False,injected_udf=fault,real_data_abort_verified=False)
def verify_storage(build):
 from inspect_diagnostic_fd import SEC_GUID
 f=json.loads((build/'fd-inspection.json').read_text());assert f['passed']
 sec=next(x for x in f['files'] if x['guid']==SEC_GUID);section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 mp=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map').read_text()
 raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes();output=[]
 data=next(s for s in pe['sections'] if s['name']=='.data')
 for name,size in [('mRamWrite',232),('mRamBackup',4096)]:
  m=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+'+name+r'\s*$',mp);assert m,name
  rva=int(m[1],16);offset=section['offset']+4+rva
  assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes'] and data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
  assert offset+size<=section['offset']+section['bytes'] and raw[offset:offset+size]==bytes(size)
  output.append(dict(symbol=name,bytes=size,rva=rva,physical_address=pe['image_base']+rva,fd_offset=offset,materialized_zero_data=True))
 assert output[0]['rva']+232<=output[1]['rva'] or output[1]['rva']+4096<=output[0]['rva']
 return output
