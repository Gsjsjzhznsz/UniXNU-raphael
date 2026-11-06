#!/usr/bin/env python3
"""Derive an explicit512/704/896/1536MiB loader budget from the qualified handset ADT."""
import argparse,datetime,json,struct,sys
from pathlib import Path
from entry_probe import ROOT,sha
from validate_handset_adt import parse

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--adt',type=Path,required=True);p.add_argument('--mib',type=int,choices=[512,704,896,1536],default=512);p.add_argument('--data-report',type=Path);a=p.parse_args()
 source=a.adt.resolve();assert source.is_relative_to(ROOT/'evidence/private/handset-storage-adt')
 tree,end=parse(source.read_bytes());assert end==source.stat().st_size
 props=tree['nodes']['chosen']['props'];previous=struct.unpack('<Q',props.get('darwinboot-memory-size',struct.pack('<Q',256*1048576)))[0];assert previous in (256*1048576,512*1048576,704*1048576,896*1048576) and previous<a.mib*1048576
 audit_path=ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json';audit=json.loads(audit_path.read_text())
 assert audit['passed'] and audit['memory_views_agree']
 from kernel_window import BLOCK,encode_policy,select_handset_window
 owned=a.mib*1048576
 base=select_handset_window(audit,owned)['aligned_example']['base']
 assert any(s['base']<=base and base+owned+BLOCK<=s['end_exclusive'] for s in audit['structural_unreserved_runs'])
 encode_policy(dict(base=base,bytes=owned+BLOCK,window_bytes=owned,virtual_base=0,experimental_boot_grant=True,guards=[dict(base=g['base'],bytes=g['bytes']) for g in audit['excluded_ranges']]))
 props['darwinboot-memory-size']=struct.pack('<Q',owned)
 sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'));from unixnu.devicetree import node
 def encode(t):return node(t['props']['name'].rstrip(b'\0').decode(),[(k,v) for k,v in t['props'].items() if k!='name'],[encode(c) for c in t['nodes'].values()])
 raw=encode(tree);check,stop=parse(raw);assert stop==len(raw) and check==tree
 out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-memory'+str(a.mib));out.mkdir(parents=True,mode=0o700)
 path=out/'kernel.macho.adt';path.write_bytes(raw)
 provenance=json.loads((source.parent/'adt-provenance.json').read_text());provenance.update(adt_sha256=sha(raw),adt_bytes=len(raw),experimental_kernel_window_bytes=owned,memory_budget_source_adt=str(source.relative_to(ROOT)),memory_budget_audit=str(audit_path.relative_to(ROOT)))
 (out/'adt-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 if a.data_report:
  data=json.loads(a.data_report.read_text());assert data['passed'] and data['persistent'] is False and (ROOT/data['adt']).resolve()==source
  data.update(adt=str(path.relative_to(ROOT)),source_data_report=str(a.data_report.resolve().relative_to(ROOT)),experimental_kernel_window_bytes=owned,handset_qualified=False,handset_verified=False)
  (out/'data-report.json').write_text(json.dumps(data,indent=2)+'\n')
 (out/'report.json').write_text(json.dumps(dict(passed=True,adt=str(path.relative_to(ROOT)),window_bytes=owned,source_adt=str(source.relative_to(ROOT)),hardware_properties_unchanged=True,handset_verified=False,full_physical_ownership_proven=False),indent=2)+'\n');print(out)
if __name__=='__main__':main()
