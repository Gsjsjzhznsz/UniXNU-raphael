#!/usr/bin/env python3
"""Private small-Image Android return; never flashes or executes a handset."""
import argparse,datetime as dt,json,struct,tempfile,uuid
from pathlib import Path
from entry_probe import ROOT,image_parameters,align,sha,run
from android_return import build_stub,capsule
from build_psci_reset import compile_image
from build_sec_dxe import build_firmware
from private_android_image import read_boot,repack
from inspect_diagnostic_fd import inspect_fd
from kernel_window import BLOCK,WINDOW,encode_policy

def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);p.add_argument('--qemu-report',type=Path,required=True);p.add_argument('--stage',type=int,choices=[3,6],default=3);a=p.parse_args()
 qp=a.qemu_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['stage']==a.stage and q['structure_checked'] and q['layout']['ArenaSize']==12*1048576
 for item in q['source_inputs']+q['upstream_inputs']+q['return_stub']['source_inputs']:
  assert sha((ROOT/item['path']).read_bytes())==item['sha256'],item['path']
 query_path=ROOT/'evidence/private/psci-query/20261028T194116Z/report.json';query=json.loads(query_path.read_text());assert query['passed'] and query['observation']['conduit']==1 and query['observation']['system_reset_feature']==0
 audit_path=ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json';audit=json.loads(audit_path.read_text());assert audit['passed'] and audit['memory_views_agree'];candidate=next(c for c in audit['candidates'] if c['every_kernel_offset_fits']);window=candidate['aligned_example']['base'];assert window+WINDOW+BLOCK<=candidate['run']['end_exclusive']
 entry_path=ROOT/'UniXNU-raphael/evidence/entry-handoff.json';entry=json.loads(entry_path.read_text())['entry'];base=entry['image_base']
 boot=read_boot(a.collection.resolve());original=image_parameters(boot['image']);assert original['image_size']==entry['original_image_size'] and original['entry']==entry['original_entry_offset']
 parent=ROOT/'evidence/private/android-return-build';parent.mkdir(mode=0o700,parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 try:
  low,reset_inputs=compile_image(out,False);lp=image_parameters(low);stub,stub_report=build_stub(out,False);rd,policy,cap=capsule(boot['image'],boot['ramdisk'],original,1)
  (out/'expanded-ramdisk.bin').write_bytes(rd)
  # Run the real SDK against this freshly collected private kernel too.
  host=sorted((ROOT/'artifacts/android-return-host').glob('*/report.json'))[-1];h=json.loads(host.read_text());assert h['passed']
  assert sha((ROOT/'scripts/fixtures/android_return_host.c').read_bytes())==h['host_fixture_sha256']
  (out/'original.Image').write_bytes(boot['image']);compressed=rd[align(len(boot['ramdisk']),8):];(out/'original.Image.lzma').write_bytes(compressed)
  host_log=run(out,[host.parent/'host-test',out/'original.Image.lzma',out/'original.Image']);(out/'host-decoder.log').write_bytes(host_log);assert b'ANDROID_RETURN_HOST_OK' in host_log
  extent=base+65536;fd=extent+65536;stack=fd+3*1048576;arena=max(stack+0x40000,align(base+original['image_size'],65536));fdt=arena+12*1048576;end=fdt+0x110000
  values=dict(ImageBase=base,ImageSize=65536,OriginalEntry=lp['entry'],OriginalInstruction=lp['instruction'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=3*1048576,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=12*1048576,FdtBase=fdt,FdtSize=0x110000,ContextBase=extent)
  kw=dict(base=window,bytes=WINDOW+BLOCK,virtual_base=q['kernel_window']['virtual_base'],guards=[dict(base=g['base'],bytes=g['bytes']) for g in audit['excluded_ranges']],experimental_boot_grant=True,handset_parameters=True,source=str(audit_path.relative_to(ROOT)),source_sha256=sha(audit_path.read_bytes()),limits=['Explicit experimental boot grant, not hidden DMA or firmware ownership proof','New direct use is limited to final 256KiB of alignment slack'])
  encode_policy(kw);identifier='raphael-android-return-v1-'+uuid.uuid4().hex
  raw,report=build_firmware(out,values,identifier,'private handset Android return; RAM-only',stop_stage=3 if a.stage==3 else 4,kernel_window=kw,android_return=dict(stub=stub,policy=policy,qemu=False))
  structure=inspect_fd(raw,fd);image=bytearray(low+bytes(end-base-len(low)));image[fd-base:fd-base+len(raw)]=raw;struct.pack_into('<I',image,0,0x14000000|((fd-base)//4));struct.pack_into('<Q',image,16,len(image));packed=repack(boot,image,ramdisk=rd);assert repack(boot,boot['image'])==boot['raw'],'Original repack must remain exact'
  (out/'boot-android-return.img').write_bytes(packed);(out/'diagnostic.Image').write_bytes(image)
  report.update(passed=True,stage=a.stage,identifier=identifier,layout=values,capsule=cap,return_stub=stub_report,reset_inputs=reset_inputs,qemu_evidence=str(qp.relative_to(ROOT)),qemu_evidence_sha256=sha(qp.read_bytes()),query_evidence=str(query_path.relative_to(ROOT)),query_evidence_sha256=sha(query_path.read_bytes()),structure_checked=True,source_sha256=sha(boot['raw']),image_sha256=sha(packed),image_bytes=len(packed),arm64_image_bytes=len(image),firmware_sha256=sha(raw),unchanged_dtbs=boot['dtbs'],original_kernel_restored_at_runtime=True,proprietary=True,publicly_redistributable=False,handset_executed=False,xnu_executed=False)
  (out/'fd-inspection.json').write_text(json.dumps(structure,indent=2)+'\n')
 except Exception as e:
  (out/'failure.json').write_text(json.dumps(dict(passed=False,failure=str(e)),indent=2)+'\n');raise
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['passed','stage','image_sha256','arm64_image_bytes']},indent=2))
if __name__=='__main__':main()
