#!/usr/bin/env python3
"""Run the independent SEC/DXE allocator, without AAVMF providing its services."""
import datetime as dt
import json
from pathlib import Path
import struct
import tempfile
from entry_probe import ROOT, align, image_parameters, sha
from build_sec_dxe import build_fixture, build_firmware, run_case
from inspect_diagnostic_fd import inspect_fd
from qemu_arch_probe import generate_resources
from inspect_device import read_fdt,registers
from kernel_window import BLOCK, WINDOW, check_log, encode_policy


def main():
    parent=ROOT/'artifacts/kernel-window-uefi-qemu'
    parent.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
    resources=generate_resources(out,memory_mb=1024)
    tree=read_fdt((out/'qemu-virt.dtb').read_bytes())
    bank=next(n for n in tree.walk() if n.properties.get('device_type')==b'memory\0')
    [(ram_start,ram_bytes)]=registers(bank)
    original=build_fixture(out)
    p=image_parameters(original)
    base=ram_start+p['text_offset']  # QEMU virt, no handset constant.
    extent=base+align(p['image_size'],65536)
    fd=extent+65536
    stack=fd+0x300000
    arena=stack+0x40000
    fdt=arena+0x1000000
    end=fdt+0x110000
    values=dict(ImageBase=base,ImageSize=p['image_size'],OriginalEntry=p['entry'],
                OriginalInstruction=p['instruction'],ExtentBase=extent,ExtentEnd=end,
                FdBase=fd,FdSize=0x300000,StackBase=stack,StackSize=0x40000,
                ArenaBase=arena,ArenaSize=0x1000000,FdtBase=fdt,FdtSize=0x110000,ContextBase=extent)
    policy=dict(base=align(ram_start+ram_bytes//2,BLOCK),bytes=WINDOW+BLOCK,virtual_base=0xfffffff007004000,
                guards=[dict(base=base,bytes=end-base)],experimental_boot_grant=True,
                source='Same-run QEMU generated 1GiB FDT RAM bank midpoint',handset_parameters=False)
    raw,report=build_firmware(out,values,'qemu-sec-dxe-v1','QEMU only',kernel_window=policy)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    structure=inspect_fd(raw,fd)
    execution=run_case(out,original,raw,p,values,dtb=out/'qemu-virt.dtb',memory_mb=1024)
    log=(out/'serial.log').read_bytes()
    verified=check_log(log,policy) if execution['passed'] else dict(passed=False)
    report.update(qemu_passed=execution['passed'] and verified['passed'],executions=dict(normal=execution),
                  structure_checked=True,firmware_sha256=sha(raw),layout=values,
                  allocation_verification=verified,qemu_resources=resources,handset_executed=False,xnu_executed=False)
    (out/'layout.json').write_text(json.dumps(dict(values=values,scope='QEMU only'),indent=2)+'\n')
    (out/'fd-inspection.json').write_text(json.dumps(structure,indent=2)+'\n')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(out)
    print(json.dumps(dict(passed=report['qemu_passed'],execution=execution),indent=2))
    assert report['qemu_passed'],log[-6500:]


if __name__=='__main__':main()
