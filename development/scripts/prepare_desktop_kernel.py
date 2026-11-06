#!/usr/bin/env python3
"""Prepare an isolated OS-driver kernel candidate; never publish it as phone-ready."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import struct
import sys
from entry_probe import ROOT
from source_pins import locked_revision


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernelcache', type=Path, required=True)
    parser.add_argument('--inspection', type=Path, default=ROOT / 'UniXNU-raphael/evidence/native-kernel-structure.json')
    parser.add_argument('--original-fairplay', action='store_true', help='Explicit21H461 original FairPlayIOKit import with audited symbol addends')
    args = parser.parse_args()
    upstream = ROOT / 'sources/UniXNU'
    sys.path.insert(0, str(upstream / 'scripts'))
    from unixnu.cli import parser as cli_parser
    from unixnu.config import Context
    ctx = Context(cli_parser().parse_args(['status', '-D', str(ROOT / 'UniXNU-raphael')]))
    profile = ctx.board['kernel']['prelink']
    source = json.loads(args.inspection.read_text())
    assert source['passed'] and source['undefined_symbol_count'] == 0
    kernel = ROOT / source['artifact_directory'] / 'native-kernel.macho'
    cache = args.kernelcache.resolve()
    assert digest(cache) == profile['kernelcache_sha256'], 'Kernelcache/profile version mismatch'
    assert digest(kernel) == source['native_macho_sha256'], 'Selected native kernel changed'
    revision = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    assert revision == locked_revision('UniXNU')
    out = ROOT / 'artifacts/desktop-prelink' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    candidate = out / 'kernel.macho'
    command = [sys.executable, str(upstream / 'kits/XnuPrelink/emit_prelink.py'),
               '--kernel', str(kernel), '--prelinked', str(cache),
               '--slide=' + profile['slide'], '--output', str(candidate)]
    if args.original_fairplay:
        if ctx.board['board']['os_profile'] != 'ipados-17.7.11-21H461':
            raise ValueError('Original FairPlay addends are qualified only for the explicit21H461 candidate')
        command[1] = str(ROOT / 'scripts/emit_fairplay_prelink.py')
        command += ['--root', 'com.apple.driver.FairPlayIOKit']
    for name in profile['roots']:
        command += ['--root', name]
    if profile.get('early_security_init'):
        command += ['--early-security-init', profile['early_security_init']]
    report = dict(passed=False, source_revision=revision, os_profile=ctx.board['board']['os_profile'],
                  native_kernel=str(kernel.relative_to(ROOT)), native_kernel_sha256=source['native_macho_sha256'],
                  original_kernelcache_sha256=profile['kernelcache_sha256'], command=command,
                  handset_executed=False, runtime_qualified=False,
                  purpose='Include matching APFS, storage, security, HID and display OS dependencies for userspace bring-up')
    print(out, flush=True)
    with (out / 'prelink.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    report['returncode'] = result.returncode
    if result.returncode == 0:
        # Prelink resolves native instructions against imported OS symbols.
        # Populate the source provider's normal integrity field after that final
        # link, retaining the original runtime POST and all negative checks.
        if b'_source_corecrypto14_bootstrap\0' in kernel.read_bytes():
            seal=[sys.executable,str(upstream/'scripts/seal-source-crypto-kernel.py'),str(candidate)]
            finalized=subprocess.run(seal,capture_output=True,text=True)
            (out/'source-crypto-finalize.log').write_text(finalized.stdout+finalized.stderr)
            if finalized.returncode:raise RuntimeError('Final prelink POST integrity preparation failed: '+finalized.stdout+finalized.stderr)
            report['source_crypto_finalization']=dict(command=seal,metadata=str(candidate.with_suffix(candidate.suffix+'.crypto-hmac.json').relative_to(ROOT)),runtime_selftests_executed=False)
        metadata = json.loads(candidate.with_suffix('.json').read_text())
        report.update(passed=True, candidate=str(candidate.relative_to(ROOT)),
                      candidate_sha256=digest(candidate), candidate_bytes=candidate.stat().st_size,
                      runtime_qualified=metadata.get('runtime_qualified', False))
        # A separate structural record: do not overwrite the native-only index.
        from native_early import image
        raw = candidate.read_bytes()
        segments, symbols = image(raw)
        undefined = subprocess.check_output(['llvm-nm', '--undefined-only', str(candidate)], text=True)
        if undefined.strip():
            raise RuntimeError('Prelinked candidate has undefined kernel symbols: ' + undefined[:2000])
        headers = subprocess.check_output(['llvm-readobj', '--file-headers', '--sections', str(candidate)], text=True)
        (out / 'macho-structure.txt').write_text(headers)
        entry = None
        at = 32
        for _ in range(struct.unpack_from('<I', raw, 16)[0]):
            cmd, size = struct.unpack_from('<II', raw, at)
            if cmd == 5:
                assert entry is None and size == 288
                entry = struct.unpack_from('<Q', raw, at + 272)[0]
            at += size
        assert entry is not None
        for i, seg in enumerate(segments):
            assert seg['file_bytes'] <= seg['bytes'] and seg['offset'] + seg['file_bytes'] <= len(raw)
            for other in segments[i+1:]:
                assert seg['virtual'] + seg['bytes'] <= other['virtual'] or other['virtual'] + other['bytes'] <= seg['virtual']
        assert any(seg['protection'] & 4 and seg['virtual'] <= entry < seg['virtual'] + seg['file_bytes'] for seg in segments)
        (out / 'native-kernel.macho').symlink_to('kernel.macho')
        inspection = dict(passed=True, artifact_directory=str(out.relative_to(ROOT)),
                          native_macho_sha256=digest(candidate), native_macho_bytes=len(raw),
                          undefined_symbol_count=0, entry_virtual_address=entry,
                          prelink_executed=True, handset_executed=False, bootable_phone_image=False,
                          segments=[dict(name=x['name'],virtual_address=x['virtual'],virtual_bytes=x['bytes'],
                                         file_offset=x['offset'],file_bytes=x['file_bytes'],initial_protection=x['protection']) for x in segments])
        (out / 'inspection.json').write_text(json.dumps(inspection, indent=2) + '\n')
        report['inspection'] = str((out / 'inspection.json').relative_to(ROOT))

    else:
        report['failure_tail'] = (out / 'prelink.log').read_text(errors='replace')[-6000:]
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report.get(k) for k in ['passed', 'returncode', 'candidate_bytes', 'failure_tail']}, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
