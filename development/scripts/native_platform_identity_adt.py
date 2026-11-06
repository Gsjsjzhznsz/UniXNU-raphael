#!/usr/bin/env python3
"""Persistent port-assigned handset UUID; no Apple or hardware identity claim."""
import argparse,datetime,json,uuid
from pathlib import Path
from entry_probe import ROOT,sha
from validate_handset_adt import parse
from native_vfs_adt import encode
KEY='unixnu-platform-uuid'
def qualify_property(value):
 assert isinstance(value,bytes) and len(value)==16
 identity=uuid.UUID(bytes=value)
 assert identity.version==4 and identity.variant==uuid.RFC_4122
 return identity

def assigned_identity():
 path=ROOT/'evidence/private/platform-identity/raphael.json'
 if path.exists():
  data=json.loads(path.read_text());value=uuid.UUID(data['uuid']).bytes;qualify_property(value);return value
 value=uuid.uuid4().bytes;path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:json.dump(dict(uuid=str(uuid.UUID(bytes=value)),source='Port-assigned random UUIDv4 retained for this local handset;not an Apple chip or observed hardware identifier'),f,indent=2);f.write('\n')
 return value

def strip_platform_identity(tree):
 value=tree['nodes']['chosen']['props'].pop(KEY,None)
 if value is not None:qualify_property(value)
 return value

def transform(raw,value):
 qualify_property(value);tree,end=parse(raw);assert end==len(raw) and encode(tree)==raw
 props=tree['nodes']['chosen']['props'];assert KEY not in props
 props[KEY]=value;result=encode(tree);back,stop=parse(result);assert stop==len(result) and strip_platform_identity(back)==value and encode(back)==raw
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--data-report',type=Path,required=True);args=ap.parse_args()
 source=args.data_report.resolve();data=json.loads(source.read_text());assert data['passed'] and data['persistent'] is False
 adt=ROOT/data['adt'];value=assigned_identity();raw=transform(adt.read_bytes(),value)
 out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-platform-uuid');out.mkdir(parents=True)
 target=out/'kernel.macho.adt';target.write_bytes(raw)
 provenance=json.loads((adt.parent/'adt-provenance.json').read_text());provenance.update(adt_sha256=sha(raw),adt_bytes=len(raw),platform_identity_source_adt=str(adt.relative_to(ROOT)),port_assigned_platform_identity=True);(out/'adt-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 data.update(adt=str(target.relative_to(ROOT)),source_data_report=str(source.relative_to(ROOT)),port_assigned_platform_identity=True,handset_qualified=False,handset_verified=False);(out/'data-report.json').write_text(json.dumps(data,indent=2)+'\n')
 (out/'report.json').write_text(json.dumps(dict(passed=True,source_adt=str(adt.relative_to(ROOT)),adt=str(target.relative_to(ROOT)),only_properties=['/chosen/'+KEY],identity_source='Persistent private port-assigned UUIDv4;no hardware identity claim',kernel_consumer='patches/xnu/raphael-platform-uuid.patch',handset_verified=False,desktop_verified=False),indent=2)+'\n');print(out)
if __name__=='__main__':main()
