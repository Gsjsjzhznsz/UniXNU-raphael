#!/usr/bin/env python3
"""Private opt-in allocator experiment, independent of diagnostic RAM probes."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import uuid
from entry_probe import ROOT, image_parameters, instrument, sha
from build_sec_dxe import build_firmware
from inspect_diagnostic_fd import inspect_fd
from kernel_window import BLOCK, WINDOW, encode_policy
from private_android_image import read_boot, repack


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--collection',type=Path,required=True)
    parser.add_argument('--qemu-report',type=Path,required=True)
    parser.add_argument('--inspection',type=Path,required=True)
    parser.add_argument('--stop-after-stage',type=int,choices=[2,3,4],required=True)
    args=parser.parse_args()
    qp=args.qemu_report.resolve()
    q=json.loads(qp.read_text())
    assert q['qemu_passed'] and q['allocation_verification']['passed'] and q['structure_checked']
    for item in q['source_inputs']+q['upstream_inputs']:
        assert sha((ROOT/item['path']).read_bytes())==item['sha256'],item['path']
    ip=args.inspection.resolve()
    inspection=json.loads(ip.read_text())
    assert inspection['passed'] and inspection['undefined_symbol_count']==0
    virtual=min(s['virtual_address'] for s in inspection['segments'] if s['virtual_bytes'])
    assert virtual==q['kernel_window']['virtual_base']
    ap=ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json'
    audit=json.loads(ap.read_text())
    assert audit['passed'] and audit['memory_views_agree']
    candidate=next(c for c in audit['candidates'] if c['every_kernel_offset_fits'])
    base=candidate['aligned_example']['base']
    assert base+WINDOW+BLOCK<=candidate['run']['end_exclusive']
    policy=dict(base=base,bytes=WINDOW+BLOCK,virtual_base=virtual,
                guards=[dict(base=g['base'],bytes=g['bytes']) for g in audit['excluded_ranges']],
                experimental_boot_grant=True,handset_parameters=True,
                source=str(ap.relative_to(ROOT)),source_sha256=sha(ap.read_bytes()),
                native_inspection=str(ip.relative_to(ROOT)),native_inspection_sha256=sha(ip.read_bytes()),
                limits=['Admission is an explicit experimental boot policy, not proof of hidden DMA/firmware ownership',
                        'Historical reversible RAM writes covered 256MiB; the extra 2MiB is alignment slack, not a test result',
                        'This profile exercises allocation metadata only; no kernel branch or direct window data writes'])
    encode_policy(policy)
    plan_path=ROOT/'UniXNU-raphael/evidence/memory-plan-check.json'
    plan=json.loads(plan_path.read_text())
    entry=json.loads((ROOT/'UniXNU-raphael/evidence/entry-handoff.json').read_text())['entry']
    boot=read_boot(args.collection.resolve())
    p=image_parameters(boot['image'])
    assert p['image_size']==entry['original_image_size'] and p['entry']==entry['original_entry_offset']
    bridge,fd,stack,arena,fdt=plan['regions']
    values=dict(ImageBase=entry['image_base'],ImageSize=p['image_size'],OriginalEntry=p['entry'],
                OriginalInstruction=p['instruction'],ExtentBase=bridge['base'],ExtentEnd=plan['requested_image_end'],
                FdBase=fd['base'],FdSize=fd['length'],StackBase=stack['base'],StackSize=stack['length'],
                ArenaBase=arena['base'],ArenaSize=arena['length'],FdtBase=fdt['base'],FdtSize=fdt['length'],ContextBase=bridge['base'])
    out=ROOT/'evidence/private/sec-dxe-build'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    identifier='raphael-kernel-window-v1-'+uuid.uuid4().hex
    raw,report=build_firmware(out,values,identifier,'private handset experimental allocator; RAM-only test',
                              stop_stage=args.stop_after_stage,kernel_window=policy)
    structure=inspect_fd(raw,fd['base'])
    (out/'fd-inspection.json').write_text(json.dumps(structure,indent=2)+'\n')
    parameters=dict(p,probe_offset=fd['base']-entry['image_base'])
    payload=raw+bytes(plan['requested_image_end']-fd['base']-len(raw))
    image=instrument(boot['image'],payload,parameters)
    assert len(image)==plan['requested_image_size']
    packed=repack(boot,image)
    (out/'boot-sec-dxe.img').write_bytes(packed)
    report.update(identifier=identifier,image_sha256=sha(packed),image_bytes=len(packed),
                  firmware_sha256=sha(raw),firmware_bytes=len(raw),layout=values,structure_checked=True,
                  source_sha256=sha(boot['raw']),unchanged_original_kernel_sha256=sha(boot['image']),
                  unchanged_ramdisk_sha256=sha(boot['ramdisk']),unchanged_dtbs=boot['dtbs'],
                  qemu_evidence=str(qp.relative_to(ROOT)),qemu_evidence_sha256=sha(qp.read_bytes()),
                  plan_sha256=sha(plan_path.read_bytes()),proprietary=True,publicly_redistributable=False,
                  handset_executed=False,full_uefi_platform=False,kernel_executed=False)
    for name in ['kernel_window.py','build_kernel_window_handset.py','run_sec_dxe.py']:
        data=(ROOT/'scripts'/name).read_bytes()
        dst=out/'verification-inputs'/name
        dst.parent.mkdir(exist_ok=True)
        dst.write_bytes(data)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(out)
    print(json.dumps(dict(image_sha256=sha(packed),firmware_sha256=sha(raw),stage=args.stop_after_stage)))


if __name__=='__main__':main()
