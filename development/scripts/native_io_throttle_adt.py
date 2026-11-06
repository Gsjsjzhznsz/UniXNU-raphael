#!/usr/bin/env python3
"""Explicit startup comparison using original XNU I/O throttle defaults."""
import argparse,datetime,json,struct,sys
from pathlib import Path
from entry_probe import ROOT,sha
from validate_handset_adt import parse
from native_vfs_adt import encode
KEYS=tuple('kern.io_throttle_window_tier'+str(i) for i in (1,2,3))
def strip_io_throttle_defaults(tree):
 props=tree['nodes']['defaults']['props'];values=[props.pop(k,None) for k in KEYS]
 assert values==[None]*3 or values==[struct.pack('<I',0)]*3,'Only the complete zero-window startup comparison is supported'
 return values[0] is not None

def transform(raw):
 tree,end=parse(raw);assert end==len(raw) and encode(tree)==raw
 props=tree['nodes']['defaults']['props'];assert not any(k in props for k in KEYS)
 for key in KEYS:props[key]=struct.pack('<I',0)
 result=encode(tree);verify,stop=parse(result);assert stop==len(result)
 assert strip_io_throttle_defaults(verify) and encode(verify)==raw
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-report',type=Path,required=True);a=p.parse_args()
 source=a.data_report.resolve();data=json.loads(source.read_text());assert data['passed'] and data['persistent'] is False
 adt=ROOT/data['adt'];raw=transform(adt.read_bytes());out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-io-window0');out.mkdir(parents=True)
 target=out/'kernel.macho.adt';target.write_bytes(raw)
 prov=json.loads((adt.parent/'adt-provenance.json').read_text());prov.update(adt_sha256=sha(raw),adt_bytes=len(raw),io_throttle_source_adt=str(adt.relative_to(ROOT)),io_throttle_windows_msecs=[0,0,0]);(out/'adt-provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 data.update(adt=str(target.relative_to(ROOT)),source_data_report=str(source.relative_to(ROOT)),explicit_io_throttle_windows_msecs=[0,0,0],handset_qualified=False,handset_verified=False);(out/'data-report.json').write_text(json.dumps(data,indent=2)+'\n')
 (out/'report.json').write_text(json.dumps(dict(passed=True,source_adt=str(adt.relative_to(ROOT)),adt=str(target.relative_to(ROOT)),only_properties=['/defaults/'+k for k in KEYS],windows_msecs=[0,0,0],native_source_contract='sources/apple-xnu-native/bsd/miscfs/specfs/spec_vnops.c:1358',handset_verified=False,desktop_verified=False),indent=2)+'\n');print(out)
if __name__=='__main__':main()
