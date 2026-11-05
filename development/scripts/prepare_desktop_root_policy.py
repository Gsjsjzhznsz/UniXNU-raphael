#!/usr/bin/env python3
"""Create a private owner policy for the actual immutable emulator root disks."""
import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from entry_probe import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system-disks',type=Path,required=True)
    args=parser.parse_args()
    disks=json.loads(args.system_disks.read_text());assert disks['passed']
    out=ROOT/'evidence/private/desktop-root-policy'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False);out.chmod(0o700)
    (out/'disks.json').write_bytes(args.system_disks.read_bytes())
    key=out/'owner.pem';public=out/'owner-public.pem'
    subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:3072','-out',key],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    key.chmod(0o600)
    subprocess.run(['openssl','pkey','-in',key,'-pubout','-out',public],check=True)
    script=ROOT/'sources/UniXNU/kits/VerifiedRoot/tools/manifest.py'
    spec=importlib.util.spec_from_file_location('desktop_manifest',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    report=dict(passed=False,phone_written=False,apple_root_trust_claimed=False,policies=[])
    try:
        for disk in disks['disks']:
            image=ROOT/disk['path'];assert image.stat().st_size==disk['bytes']
            containers=disk['apfs_containers'];assert len(containers)==1 and len(containers[0]['volumes'])==1
            target=out/disk['role']
            print('Creating actual block-read policy:',disk['role'],flush=True)
            with image.open('rb') as stream:
                meta=module.make(stream,disk['bytes'],key,public,containers[0]['volumes'][0],1,target)
            report['policies'].append(dict(role=disk['role'],path=str(target.relative_to(ROOT)),**meta))
        report['passed']=True
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(out,flush=True)


if __name__=='__main__':
    main()
