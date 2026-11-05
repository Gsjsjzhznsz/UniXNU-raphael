#!/usr/bin/env python3
"""Re-read frozen source, boot artifacts, FDT records, logs and allocation map."""
import argparse
import datetime as dt
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from entry_probe import ROOT, sha
from inspect_device import read_fdt
from inspect_diagnostic_fd import inspect_fd
from kernel_window import check_admission, check_log, encode_policy


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--qemu',type=Path,required=True)
    parser.add_argument('--run',type=Path,action='append',required=True)
    parser.add_argument('--cleanup',type=Path,required=True)
    parser.add_argument('--source-revision',required=True)
    args=parser.parse_args()
    qp=args.qemu.resolve()
    q=json.loads(qp.read_text())
    assert q['qemu_passed'] and q['structure_checked']
    check_log((qp.parent/'serial.log').read_bytes(),q['kernel_window'])
    phases=[]
    for rp in args.run:
        rp=rp.resolve()
        r=json.loads(rp.read_text())
        public=ROOT/'UniXNU-raphael/evidence'/('sec-dxe-attempt-'+rp.parent.name+'.json')
        attempt=json.loads(public.read_text())
        build=ROOT/attempt['private_build']
        bp=build/'report.json'
        b=json.loads(bp.read_text())
        assert b['kernel_window'] and b['qemu_evidence_sha256']==sha(qp.read_bytes())
        for k in ['firmware_checkpoint_passed','nonce_matched','android_boot_completed','root_verified','boot_partition_unchanged']:
            assert r[k],(rp,k)
        for item in b['source_inputs']+b['upstream_inputs']:
            local=ROOT/item['path']
            snapshot=build/'source-snapshot'/item['path']
            assert sha(snapshot.read_bytes())==sha(local.read_bytes())==item['sha256']
            if item in b['source_inputs']:
                blob=subprocess.check_output(['git','show',args.source_revision+':'+item['path']],cwd=ROOT)
                assert blob==snapshot.read_bytes()
        image=build/'boot-sec-dxe.img'
        assert sha(image.read_bytes())==b['image_sha256']
        fd=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd'
        assert sha(fd.read_bytes())==b['firmware_sha256']
        inspect_fd(fd.read_bytes(),b['layout']['FdBase'])
        assert (build/'kernel-window-policy.bin').read_bytes()==encode_policy(b['kernel_window'])
        tree=read_fdt((rp.parent/'after.dtb').read_bytes())
        chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
        record=struct.unpack('>48Q',chosen.properties['raphael,sec-dxe'])
        stage={2:2,3:3,4:6}[b['stop_stage']]
        assert record[27]==stage and record[28]==0
        assert chosen.properties['raphael,sec-dxe-id'].rstrip(b'\0').decode()==b['identifier']
        log=chosen.properties['raphael,sec-dxe-log']
        assert log==(rp.parent/'firmware.log').read_bytes()
        verified=check_log(log,b['kernel_window']) if stage==6 else check_admission(log,b['kernel_window'])
        if stage==6:
            raw=chosen.properties['raphael,sec-dxe-map']
            assert raw==(rp.parent/'firmware-memory-map.bin').read_bytes()
            assert len(raw)==record[41] and record[42]>=40 and len(raw)%record[42]==0
            w=b['kernel_window'];owned=[]
            arena=b['layout']['ArenaBase'];end=arena+b['layout']['ArenaSize']
            for off in range(0,len(raw),record[42]):
                typ,_,physical,virtual,pages,attributes=struct.unpack_from('<II4Q',raw,off)
                limit=physical+4096*pages
                if w['base']<=physical and limit<=w['base']+w['bytes']:
                    assert typ==4 and pages>0
                    owned.append((physical,limit))
                elif typ in [3,4,5,6,7]:assert arena<=physical<limit<=end
            at=w['base']
            for start,limit in sorted(owned):assert start==at;at=limit
            assert at==w['base']+w['bytes']
        phases.append(dict(stage=stage,run=str(rp.parent.relative_to(ROOT)),
            run_report_sha256=sha(rp.read_bytes()),build=str(build.relative_to(ROOT)),
            build_report_sha256=sha(bp.read_bytes()),image_sha256=b['image_sha256'],
            firmware_sha256=b['firmware_sha256'],log_sha256=sha(log),verification=verified))
    assert sorted(p['stage'] for p in phases)==[2,3,6]
    cp=args.cleanup.resolve();cleanup=json.loads(cp.read_text())
    assert all(cleanup[k] for k in ['normal_android_reboot','android_boot_completed','root_verified','boot_partition_unchanged','transient_probe_absent'])
    report=dict(passed=True,source_revision=args.source_revision,phases=phases,
        qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),
        cleanup=str(cp.relative_to(ROOT)),cleanup_sha256=sha(cp.read_bytes()),
        verifier_sha256=sha(Path(__file__).read_bytes()),
        handset_allocation_lifecycle_verified=True,handset_darwinboot_valid_kernel_executed=False,
        handset_xnu_executed=False,full_physical_ownership_proven=False,
        external_uart_verified=False,partition_writes_performed=False)
    parent=ROOT/'artifacts/kernel-window-verification';parent.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
    data=json.dumps(report,indent=2)+'\n';(out/'report.json').write_text(data)
    (ROOT/'UniXNU-raphael/evidence/kernel-window-uefi-verification.json').write_text(data)
    print(out);print('Kernel window evidence verified')


if __name__=='__main__':main()
