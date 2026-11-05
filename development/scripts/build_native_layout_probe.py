#!/usr/bin/env python3
"""Measure current bootloader FDT placement for the native payload budget.

Only the old bounded entry probe is accessed; the larger tail is zero padding.
This is not an allocation permission or a UEFI native-profile execution test.
"""
import argparse,datetime as dt,json,uuid
from pathlib import Path
from entry_probe import ROOT,compile_probe,image_parameters,instrument,align,sha
from private_android_image import read_boot,repack

def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);a=p.parse_args()
 boot=read_boot(a.collection.resolve());params=image_parameters(boot['image'])
 entry=json.loads((ROOT/'UniXNU-raphael/evidence/entry-handoff.json').read_text())['entry'];base=entry['image_base']
 extent=base+align(params['image_size'],65536);fd=extent+65536;stack=fd+22*1048576;arena=stack+0x40000;fdt=arena+48*1048576;end=fdt+0x110000
 assert 64<=params['image_size']<end-base<128*1048576
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'evidence/private/entry-probe-build'/stamp;out.mkdir(mode=0o700,parents=True,exist_ok=False)
 identifier='raphael-native-layout-'+uuid.uuid4().hex;probe=compile_probe(out,params,identifier)
 tail_bytes=end-base-params['probe_offset'];assert tail_bytes>=len(probe)
 instrumented=instrument(boot['image'],probe+bytes(tail_bytes-len(probe)),params);assert len(instrumented)==end-base
 packed=repack(boot,instrumented);(out/'boot-entry-probe.img').write_bytes(packed)
 provenance=json.loads((out/'probe-inputs.json').read_text())
 for item in provenance['inputs']:
  raw=(ROOT/item['file']).read_bytes();assert sha(raw)==item['sha256'];dest=out/'snapshot'/item['file'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 report=dict(kind='native layout placement probe; bounded old receiver and untouched zero tail',source_sha256=sha(boot['raw']),identifier=identifier,parameters=params,
  image_sha256=sha(packed),image_bytes=len(packed),extended_arm64_image_bytes=len(instrumented),zero_tail_padding_bytes=tail_bytes-len(probe),padded_tail_written_or_read_by_probe=False,candidate_extent_download_test=False,
  future_native_layout=dict(ImageBase=base,ImageSize=params['image_size'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=22*1048576,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=48*1048576,FdtBase=fdt,FdtSize=0x110000,ContextBase=extent),
  original_image_sha256=sha(boot['image']),unchanged_dtbs=boot['dtbs'],unchanged_ramdisk_sha256=sha(boot['ramdisk']),source_inputs=provenance['inputs'],handset_executed=False,uefi_executed=False,limits=['Future layout values are design budgets derived from the current Image and new payload sizes','No direct access to the expanded zero tail; no whole-RAM or ownership claim'])
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(json.dumps(dict(image_bytes=len(packed),image_sha256=sha(packed),future_layout=report['future_native_layout']),indent=2))
if __name__=='__main__':main()
