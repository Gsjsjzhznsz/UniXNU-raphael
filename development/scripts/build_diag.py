#!/usr/bin/env python3
"""Compile a protocol-only AArch64 UEFI diagnostic. This does not build a board FD."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / 'artifacts/uefi-diag' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    records = []

    def run(args):
        result = subprocess.run(list(map(str, args)), capture_output=True)
        records.append(dict(command=list(map(str, args)), returncode=result.returncode,
                            stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace')))
        (out / 'commands.json').write_text(json.dumps(records, indent=2))
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace'))
        return result.stdout

    include = ROOT / 'sources/mu_basecore/MdePkg/Include'
    source = ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg/Application/RaphaelDiag/RaphaelDiag.c'
    obj = out / 'RaphaelDiag.obj'
    image = out / 'RaphaelDiag.efi'
    run(['clang-18', '--target=aarch64-windows-msvc', '-ffreestanding', '-fno-builtin',
         '-fshort-wchar', '-fno-stack-protector', '-mgeneral-regs-only', '-Os',
         '-Wall', '-Wextra', '-Werror', '-Wno-unused-command-line-argument',
         '-I', include, '-I', include / 'AArch64', '-c', source, '-o', obj])
    run(['lld-link', '/subsystem:efi_application', '/entry:RaphaelDiagEntry', '/nodefaultlib',
         '/machine:arm64', '/dynamicbase', '/fixed:no', '/timestamp:0', f'/out:{image}', obj])
    inspection = run(['llvm-readobj', '--file-headers', '--sections', '--coff-basereloc', image])
    (out / 'pe-inspection.txt').write_bytes(inspection)
    raw = image.read_bytes()
    pe = struct.unpack_from('<I', raw, 0x3c)[0]
    assert raw[:2] == b'MZ' and raw[pe:pe + 4] == b'PE\0\0'
    machine, sections = struct.unpack_from('<HH', raw, pe + 4)
    optional = pe + 24
    assert machine == 0xaa64 and sections > 0
    assert struct.unpack_from('<H', raw, optional)[0] == 0x20b
    assert struct.unpack_from('<H', raw, optional + 68)[0] == 10
    entry, image_size = struct.unpack_from('<I', raw, optional + 16)[0], struct.unpack_from('<I', raw, optional + 56)[0]
    assert 0 < entry < image_size
    reloc_rva, reloc_bytes = struct.unpack_from('<II', raw, optional + 112 + 5 * 8)
    assert reloc_rva and reloc_bytes, 'Application must support relocation'
    report = dict(kind='host-compiled-and-structure-checked', device_executed=False,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), entry_rva=entry,
                  reloc_bytes=reloc_bytes,
                  limitation='UEFI application only; not SEC/FD/boot.img; no device boot claim')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(image)


if __name__ == '__main__':
    main()
