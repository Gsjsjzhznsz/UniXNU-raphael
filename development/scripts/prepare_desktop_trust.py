#!/usr/bin/env python3
"""Pack the two unchanged original Apple version-2 trust modules for DarwinBoot."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import struct
import sys
import tomllib
from entry_probe import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=ROOT/'artifacts/desktop-system/ipsw/21H461')
    args=parser.parse_args()
    sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'))
    from unixnu.ipsw import im4p_payload
    out=ROOT/'artifacts/desktop-trust'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    modules=[];records=[]
    for name in ['044-76040-038.dmg.trustcache','044-76034-038.dmg.trustcache']:
        source=args.inputs/name;original=source.read_bytes();module=im4p_payload(original)
        version=struct.unpack_from('<I',module)[0];count=struct.unpack_from('<I',module,20)[0]
        assert version==2 and len(module)==24+24*count
        entries=[module[24+i*24:48+i*24] for i in range(count)]
        assert all(1<=x[20]<=4 for x in entries)
        assert all(left[:20]<right[:20] for left,right in zip(entries,entries[1:]))
        modules.append(module);records.append(dict(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(original).hexdigest(),entries=count,module_sha256=hashlib.sha256(module).hexdigest()))
    offset=4+4*len(modules);offsets=[]
    for module in modules:offsets.append(offset);offset+=len(module)
    bundle=struct.pack('<'+'I'*(len(modules)+1),len(modules),*offsets)+b''.join(modules)
    profile=tomllib.loads((ROOT/'sources/UniXNU/profiles/os/ipados-17.7.11-21H461/profile.toml').read_text())
    assert hashlib.sha256(bundle).hexdigest() in profile['payload']['trust_cache_sha256']
    (out/'original-trust.bundle').write_bytes(bundle)
    report=dict(passed=True,original_modules_unchanged=True,added_owner_cdhashes=False,apple_signature_chain_verified=False,
                modules=records,bundle=str((out/'original-trust.bundle').relative_to(ROOT)),bytes=len(bundle),sha256=hashlib.sha256(bundle).hexdigest())
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(out);print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
