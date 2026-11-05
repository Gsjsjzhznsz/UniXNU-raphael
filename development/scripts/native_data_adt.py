#!/usr/bin/env python3
"""Freeze a new ephemeral packed APFS Data seed and exact ADT placeholder."""
import argparse,datetime,json,sys
from pathlib import Path
from entry_probe import ROOT,sha
from native_ramdisk import with_placeholder,validate_packed

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--adt',type=Path,required=True);p.add_argument('--scratch-data',type=Path,required=True);a=p.parse_args()
 source=a.adt.resolve();scratch_path=a.scratch_data.resolve()
 assert source.is_relative_to(ROOT/'evidence/private/handset-storage-adt')
 assert scratch_path.is_relative_to(ROOT/'evidence/private/desktop-data')
 scratch=json.loads(scratch_path.read_text());assert scratch['passed'] and not scratch['handset_executed'] and scratch['bytes'] in (512*1048576,1024*1048576)
 image=ROOT/scratch['image'];assert image.stat().st_size==scratch['bytes']
 out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-ephemeral-data');out.mkdir(parents=True,mode=0o700)
 sys.path.insert(0,str(ROOT/'sources/UniXNU/drivers/DarwinBoot/Test'));from packed_ramdisk import pack
 packed=out/'data.packed';transport=pack(image,packed);meta=validate_packed(packed.read_bytes());assert meta['logical_bytes']==scratch['bytes']
 adt=out/'kernel.macho.adt';adt.write_bytes(with_placeholder(source.read_bytes()))
 provenance=json.loads((source.parent/'adt-provenance.json').read_text());provenance.update(adt_sha256=sha(adt.read_bytes()),adt_bytes=adt.stat().st_size,ephemeral_data_source_adt=str(source.relative_to(ROOT)),ephemeral_data_seed_report=str(scratch_path.relative_to(ROOT)))
 (out/'adt-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 (out/'report.json').write_text(json.dumps(dict(passed=True,adt=str(adt.relative_to(ROOT)),packed=str(packed.relative_to(ROOT)),packed_sha256=meta['sha256'],transport=transport,logical_bytes=meta['logical_bytes'],scratch_data=str(scratch_path.relative_to(ROOT)),handset_qualified=False,persistent=False),indent=2)+'\n');print(out)
if __name__=='__main__':main()
