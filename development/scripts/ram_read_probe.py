#!/usr/bin/env python3
"""Immutable sourced RAM-read policy and independent big-endian wire checks."""
import json, struct, subprocess, re
from entry_probe import ROOT, sha
FIELDS=('version status reason base bytes stride requested attempted completed active_address digest nonzero start_counter end_counter frequency mmfr0 physical_bits ram_ranges fixed_reservations header_reservations dynamic_pools policy_guards entry_guards current_el sctlr daif').split()
WINDOW=0x10000000
STRIDE=0x200000
GUID='d2cd8ed5-a64e-45d3-8b4e-3d02d1f1b0fb'
MASK=(1<<64)-1
PA=[32,36,40,42,44,48,52]
def encode(base,guards):
 assert base%STRIDE==0 and 0<=base<=MASK-WINDOW and 0<len(guards)<=128
 assert all(0<=a<=MASK-n and n>0 and (base+WINDOW<=a or a+n<=base) for a,n in guards)
 return struct.pack('<8Q',1,64,64+16*len(guards),base,WINDOW,STRIDE,256,len(guards))+b''.join(struct.pack('<QQ',a,n) for a,n in guards)
def policy(raw):
 assert len(raw)>=64
 v,h,t,b,n,s,k,g=struct.unpack_from('<8Q',raw)
 assert (v,h,t,n,s,k)==(1,64,len(raw),WINDOW,STRIDE,256) and len(raw)==64+16*g
 guards=[struct.unpack_from('<QQ',raw,64+16*i) for i in range(g)]
 assert encode(b,guards)==raw
 return dict(version=v,base=b,bytes=n,stride=s,max_reads=k,guards=[dict(base=a,bytes=z) for a,z in guards],sha256=sha(raw))
def sourced_policy():
 ap=ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json';hp=ROOT/'UniXNU-raphael/evidence/kernel-window-host.json'
 a,h=[json.loads(p.read_text()) for p in [ap,hp]]
 assert a['passed'] and h['passed'] and h['audit_sha256']==sha(ap.read_bytes()) and h['randomized_discrete_models']==256
 for item in a['source_inputs']+h['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
 for item in a['primary_sources']:
  path=ROOT/item['repository']/item['path'];assert sha(path.read_bytes())==item['sha256']
  assert path.read_bytes()==subprocess.check_output(['git','-C',str(ROOT/item['repository']),'show',item['revision']+':'+item['path']])
 cp=ROOT/a['collection'];report=cp/'report.json';assert sha(report.read_bytes())==a['collection_report_sha256']
 for item in json.loads(report.read_text())['files']:assert sha((cp/item['file']).read_bytes())==item['sha256']
 base=min(c['aligned_example']['base'] for c in a['candidates'])
 raw=encode(base,[(g['base'],g['bytes']) for g in a['excluded_ranges']])
 return dict(policy=policy(raw),sources=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in [ap,hp,report]],source='Lowest aligned candidate from current sourced interval audit',ram_written=False,allocator_enabled=False),raw

def decode(raw,expected):
 assert len(raw)==len(FIELDS)*8
 d=dict(zip(FIELDS,struct.unpack('>26Q',raw)))
 assert d['version']==1 and d['status']==3 and d['reason']==0
 for k in ['base','bytes','stride']:assert d[k]==expected[k],k
 assert d['requested']==d['attempted']==d['completed']==256
 assert d['active_address']==d['base']+d['bytes']-8 and 0<=d['nonzero']<=256
 assert 1000<=d['frequency']<=1000000000 and d['start_counter']<=d['end_counter']<=d['start_counter']+d['frequency']//10
 assert d['mmfr0']&15<len(PA) and d['physical_bits']==PA[d['mmfr0']&15] and d['base']+d['bytes']<=1<<d['physical_bits']
 assert 1<=d['ram_ranges']<=32 and d['fixed_reservations']<=128 and d['header_reservations']<=128
 assert d['policy_guards']==len(expected['guards']) and 1<=d['entry_guards']<=8
 assert d['current_el']==4 and d['sctlr']&0x1005==0 and d['daif']&0x3c0==0x3c0
 return dict(**d,passed=True,sparse_reads_only=True,entire_window_tested=False,ram_written=False,allocator_enabled=False,ownership_proven=False)
def verify_result_storage(build):
 from inspect_diagnostic_fd import SEC_GUID
 fd=json.loads((build/'fd-inspection.json').read_text());assert fd['passed']
 sec=next(f for f in fd['files'] if f['guid']==SEC_GUID);section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 mp=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map'
 m=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+mRamRead\s*$',mp.read_text());assert m
 rva=int(m[1],16);size=26*8;data=next(s for s in pe['sections'] if s['name']=='.data')
 assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes'] and data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
 raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes();offset=section['offset']+4+rva
 assert offset+size<=section['offset']+section['bytes'] and raw[offset:offset+size]==bytes(size)
 return dict(bytes=size,rva=rva,physical_address=pe['image_base']+rva,fd_offset=offset,materialized_zero_data=True)
