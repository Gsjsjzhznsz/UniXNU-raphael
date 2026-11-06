#!/usr/bin/env python3
"""Explicit native development comparison for the observed vnode-cache limit."""
import argparse,datetime,json,struct,sys
from pathlib import Path
from entry_probe import ROOT,sha
from validate_handset_adt import parse
sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'))
from unixnu.devicetree import node
KEY='kern.maxvnodes'
def encode(t):
 return node(t['props']['name'].rstrip(b'\0').decode(),[(k,v) for k,v in t['props'].items() if k!='name'],[encode(c) for c in t['nodes'].values()])
def strip_vfs_default(tree):
 value=tree['nodes']['defaults']['props'].pop(KEY,None)
 if value is not None:assert value==struct.pack('<I',8192), 'Only explicit8192-vnode development comparison is supported'
 return value is not None

def transform(raw,value):
 if value!=8192:raise ValueError('This comparison explicitly selects8192 vnodes')
 tree,end=parse(raw);assert end==len(raw) and encode(tree)==raw
 props=tree['nodes']['defaults']['props'];assert KEY not in props
 props[KEY]=struct.pack('<I',value);result=encode(tree)
 verify,finish=parse(result);assert finish==len(result) and verify['nodes']['defaults']['props'][KEY]==struct.pack('<I',value)
 del verify['nodes']['defaults']['props'][KEY];assert encode(verify)==raw
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-report',type=Path,required=True);p.add_argument('--max-vnodes',type=int,choices=[8192],required=True);a=p.parse_args()
 source=a.data_report.resolve();assert source.is_relative_to(ROOT/'evidence/private/handset-storage-adt')
 data=json.loads(source.read_text());assert data['passed'] and data['persistent'] is False
 adt=ROOT/data['adt'];result=transform(adt.read_bytes(),a.max_vnodes)
 from native_watchdog_budget import from_adt
 assert from_adt(result)==from_adt(adt.read_bytes())
 out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-vnode8192');out.mkdir(parents=True,mode=0o700)
 path=out/'kernel.macho.adt';path.write_bytes(result)
 provenance=json.loads((adt.parent/'adt-provenance.json').read_text());provenance.update(adt_sha256=sha(result),adt_bytes=len(result),vfs_source_adt=str(adt.relative_to(ROOT)),explicit_max_vnodes=a.max_vnodes)
 (out/'adt-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 report=dict(passed=True,source_adt=str(adt.relative_to(ROOT)),adt=str(path.relative_to(ROOT)),only_property='/defaults/'+KEY,max_vnodes=a.max_vnodes,native_source_contract=['sources/apple-xnu-native/pexpert/gen/bootargs.c:507','sources/apple-xnu-native/bsd/dev/unix_startup.c:201'],runtime_baseline='UniXNU-raphael/evidence/native-vfs-cache.json',handset_verified=False,desktop_verified=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 data.update(adt=str(path.relative_to(ROOT)),source_data_report=str(source.relative_to(ROOT)),explicit_max_vnodes=a.max_vnodes,vfs_comparison_report=str((out/'report.json').relative_to(ROOT)),handset_qualified=False,handset_verified=False)
 (out/'data-report.json').write_text(json.dumps(data,indent=2)+'\n');print(out)
if __name__=='__main__':main()
