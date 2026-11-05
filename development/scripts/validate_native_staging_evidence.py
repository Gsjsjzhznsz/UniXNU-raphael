#!/usr/bin/env python3
"""Re-decode raw native staging evidence and bind frozen source to Git."""
import argparse
import datetime as dt
from functools import lru_cache
import json
import lzma
import re
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from entry_probe import ROOT, sha
from inspect_device import read_fdt
from inspect_diagnostic_fd import inspect_fd, PAYLOAD_GUID, PAYLOAD_PART1_GUID
from kernel_window import check_log
from payload_probe import decode
from validate_android_return_evidence import chosen, load
from private_android_image import read_boot, repack

PINS = {
    'sources/UniXNU': '40d21cc65171c3a24faa130a2a8e899f85790485',
    'sources/mu_basecore': 'cfb93724a06ff86ff5ba971413368a7809ee42a5',
}

@lru_cache(maxsize=None)
def pinned_tree(repo, revision):
    raw = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-rz', revision])
    entries = {}
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        entries[name.decode()] = (kind, oid)
    return entries

def pinned_bytes(repo, revision, relative):
    entries = pinned_tree(repo, revision)
    if relative in entries:
        kind, oid = entries[relative]
        assert kind == 'blob', relative
        return subprocess.check_output(['git', '-C', str(repo), 'cat-file', 'blob', oid])
    links = [(name, oid) for name, (kind, oid) in entries.items()
             if kind == 'commit' and relative.startswith(name + '/')]
    assert len(links) == 1, (str(repo), revision, relative)
    name, oid = links[0]
    # Resolve the gitlink in its parent's pinned tree, never the submodule HEAD.
    return pinned_bytes(repo / name, oid, relative[len(name) + 1:])

def git_bytes(path, revision):
    for repo, pin in PINS.items():
        if path.startswith(repo + '/'):
            return pinned_bytes(ROOT / repo, pin, str(Path(path).relative_to(repo)))
    return pinned_bytes(ROOT, revision, path)

def bind(base, report, revision, bound):
    items = report['source_inputs'] + report['upstream_inputs']
    items += report['return_stub']['source_inputs'] + report['reset_inputs']
    items += report['workflow_inputs']
    for item in items:
        path = item['path']
        snapshots = [base / prefix / path for prefix in
            ['source-snapshot', 'snapshot', 'workflow-snapshot']]
        raw = next(p for p in snapshots if p.is_file()).read_bytes()
        assert sha(raw) == item['sha256'], path
        assert raw == git_bytes(path, revision), path
        bound.add(path)
    assert sha(git_bytes('scripts/build_sec_dxe.py', revision)) == report['builder_sha256']

def file_read(log, layout, kernel):
    match = re.search(rb'NATIVE_STAGING kernel bytes=(\d+) buffer=([0-9a-f]+) crc=([0-9a-f]+) expected=([0-9a-f]+) status=Success', log, re.I)
    assert match and int(match[1]) == len(kernel)
    assert int(match[3], 16) == int(match[4], 16) == zlib.crc32(kernel)
    at = int(match[2], 16)
    end = layout['ArenaBase'] + layout['ArenaSize'] - 20 * 1048576
    assert layout['ArenaBase'] <= at <= end and len(kernel) <= end - at
    assert b'NATIVE_STAGING window_restore=Success' in log
    return dict(bytes=len(kernel), buffer=at, crc32=zlib.crc32(kernel))

def inspect_build(base, report):
    assert report['sparse_arena'] and report['native_boot'] and not report['native_handoff']
    assert report['structure_checked'] and report['returncode'] == 0
    layout = report['layout']; image = (base / 'diagnostic.Image').read_bytes()
    assert len(image) == layout['StackBase'] + layout['StackSize'] - layout['ImageBase']
    assert struct.unpack_from('<Q', image, 16)[0] == len(image)
    assert len(image) < layout['ArenaBase'] - layout['ImageBase']
    fd = image[layout['FdBase'] - layout['ImageBase']:layout['FdBase'] - layout['ImageBase'] + layout['FdSize']]
    structure = inspect_fd(fd, layout['FdBase'])
    assert structure['passed'] and sha(fd) == report['firmware_sha256']
    parts = []
    for guid in [PAYLOAD_GUID, PAYLOAD_PART1_GUID]:
        record = next(f for f in structure['files'] if f['guid'] == guid)
        [section] = record['sections']
        parts.append(fd[section['offset'] + 4:section['offset'] + section['bytes']])
    fat = (base / 'diagnostic-payload.img').read_bytes()
    assert b''.join(parts) == fat and len(fat) == 20 * 1048576
    assert sha(fat) == report['payload']['image_sha256']
    kernel = subprocess.check_output(['mtype', '-i', str(base / 'diagnostic-payload.img'), '::/EFI/UniXNU/kernel.macho'])
    assert sha(kernel) == report['payload']['kernel_sha256']
    adt = subprocess.check_output(['mtype', '-i', str(base / 'diagnostic-payload.img'), '::/EFI/UniXNU/kernel.macho.adt'])
    assert adt == b'INVALID_ADT_STAGING_ONLY_NO_HANDOFF'
    assert sha(adt) == report['payload']['adt_sha256']
    return image, kernel

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--failed-run', type=Path, action='append', default=[])
    args = parser.parse_args()
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', args.revision], text=True).strip()
    parent = ROOT / 'artifacts/native-staging-verification'; parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'), dir=parent))
    print(out, flush=True)
    cases = []; bound = set()
    for run in args.run:
        run = run.resolve(); rr = load(run / 'report.json')
        assert rr['passed'] and rr['experiment_passed'] and rr['unassisted_android_return']
        assert not rr.get('auto_recovered_from_bootloader') and not (run / 'bootloader-recovery.json').exists()
        build = ROOT / rr['build']; br = load(build / 'report.json')
        assert sha((build / 'report.json').read_bytes()) == rr['build_report_sha256']
        bind(build, br, revision, bound); image, kernel = inspect_build(build, br)
        assert len(kernel) == br['staging_kernel_bytes'] and sha(kernel) == br['staging_kernel_sha256']
        packed = (build / 'boot-android-return.img').read_bytes()
        assert sha(packed) == br['image_sha256'] == rr['image_sha256']
        ks, _, rs = struct.unpack_from('<3I', packed, 8); page = struct.unpack_from('<I', packed, 36)[0]
        assert page == 4096 and packed[page:page + 16] == b'UNCOMPRESSED_IMG'
        assert struct.unpack_from('<I', packed, page + 16)[0] == len(image)
        assert packed[page + 20:page + 20 + len(image)] == image
        trailer = packed[page + 20 + len(image):page + ks]; dtbs = []
        while trailer:
            assert trailer[:4] == b'\xd0\x0d\xfe\xed'
            size = struct.unpack_from('>I', trailer, 4)[0]; assert 40 <= size <= len(trailer)
            dtbs.append(dict(bytes=size, sha256=sha(trailer[:size]))); trailer = trailer[size:]
        assert dtbs == br['unchanged_dtbs']
        ramdisk = (build / 'expanded-ramdisk.bin').read_bytes(); at = page + ((ks + page - 1) // page) * page
        assert packed[at:at + rs] == ramdisk
        cap = br['capsule']; policy = cap['policy_words']
        restored = lzma.decompress(ramdisk[(cap['ramdisk_bytes'] + 7) & ~7:], format=lzma.FORMAT_ALONE)
        assert len(restored) == cap['kernel_bytes'] and sha(restored) == cap['kernel_sha256']
        assert zlib.crc32(restored) == policy[9] and sha(ramdisk) == cap['expanded_ramdisk_sha256']
        assert sha(ramdisk[:cap['ramdisk_bytes']]) == cap['ramdisk_sha256']
        original = read_boot(ROOT / 'evidence/private/device/20261027T120325Z')
        assert sha(original['raw']) == br['source_sha256']
        assert restored == original['image']
        assert ramdisk[:cap['ramdisk_bytes']] == original['ramdisk']
        assert original['dtbs'] == dtbs
        assert repack(original, image, ramdisk=ramdisk) == packed
        assert repack(original, original['image']) == original['raw']
        c = chosen((run / 'after.dtb').read_bytes())
        assert c.strings('raphael,sec-dxe-id') == [br['identifier']]
        w = struct.unpack('>10Q', c.properties['raphael,android-return'])
        d = struct.unpack('>48Q', c.properties['raphael,sec-dxe'])
        assert list(w) == rr['return_words'] and list(d) == rr['sec_words']
        assert w[:2] == (1, 3) and w[2] == w[7] == policy[8] and w[3] == w[4] == policy[9]
        assert w[8] == len(restored) and w[9] == 1 and d[27:29] == (rr['stage'], 0)
        assert d[6] == 4 and d[30] & 0x1005 == 0x1005
        assert d[23] >= br['layout']['ImageBase'] + cap['declared_image_bytes']
        assert d[31] >= br['layout']['ImageBase'] + cap['declared_image_bytes']
        assert w[5:7] == (br['kernel_window']['base'] + br['kernel_window']['bytes'] - 0x40000, br['kernel_window']['base'] + br['kernel_window']['bytes'])
        first = int.from_bytes(c.properties['linux,initrd-start'], 'big')
        assert int.from_bytes(c.properties['linux,initrd-end'], 'big') - first == cap['ramdisk_bytes']
        assert br['layout']['ImageBase'] + len(image) <= first
        assert first + len(ramdisk) <= br['layout']['ArenaBase']
        payload = decode(c.properties['raphael,payload-diagnostic'], br['layout'], rr['stage'], native_staging=True)
        log = c.properties['raphael,sec-dxe-log']; assert log == (run / 'sec-dxe.log').read_bytes()
        observed = None
        if rr['stage'] == 6:
            observed = file_read(log, br['layout'], kernel)
            assert observed == rr['staging_file_read'] and check_log(log, br['kernel_window'])['passed']
            assert d[38:40] == (1, 1) and d[44:46] == (0, 1)
        qp = ROOT / br['qemu_evidence']; q = load(qp)
        assert sha(qp.read_bytes()) == br['qemu_evidence_sha256'] and q['passed'] and q['stage'] == rr['stage']
        bind(qp.parent, q, revision, bound); inspect_build(qp.parent, q)
        qlog = (qp.parent / 'serial.log').read_bytes()
        assert b'ANDROID_RETURN_QEMU_OK' in qlog and b'FAIL ' not in qlog
        if rr['stage'] == 6: file_read(qlog, q['layout'], kernel)
        cleanup = chosen((run / 'cleanup.dtb').read_bytes()); before = chosen((run / 'before.dtb').read_bytes())
        assert not any(k.startswith('raphael,') for t in [cleanup, before] for k in t.properties)
        commands = load(run / 'commands.json')
        for command in commands:
            if command.get('file'): assert sha((run / command['file']).read_bytes()) == command['sha256']
        boots = [x for x in commands if 'fastboot.exe' in x['command'][0] and 'boot' in x['command']]
        assert len(boots) == 1 and boots[0]['returncode'] == 0
        assert not any(set(x['command']) & {'flash', 'erase', 'format'} for x in commands)
        hashes = [x for x in commands if any('sha256sum /dev/block/bootdevice/by-name/boot' in v for v in x['command'])]
        assert len(hashes) >= 3 and all(x['returncode'] == 0 and x['stdout'].split()[0] == br['source_sha256'] for x in hashes)
        assert (run / 'before-boot-id.txt').read_bytes() != (run / 'after-boot-id.txt').read_bytes()
        assert all(rr.get(k) for k in ['cleanup_android_completed', 'cleanup_root_verified', 'cleanup_boot_unchanged', 'cleanup_transient_properties_absent'])
        cases.append(dict(stage=rr['stage'], passed=True, private_run=str(run.relative_to(ROOT)), run_report_sha256=sha((run / 'report.json').read_bytes()), build=str(build.relative_to(ROOT)), build_report_sha256=sha((build / 'report.json').read_bytes()), image_sha256=br['image_sha256'], firmware_sha256=br['firmware_sha256'], qemu_report=str(qp.relative_to(ROOT)), qemu_report_sha256=sha(qp.read_bytes()), kernel_sha256=sha(kernel), downloaded_image_bytes=len(image), grant_footprint_bytes=br['layout']['ExtentEnd']-br['layout']['ImageBase'], experimental_arena_bytes=br['layout']['ArenaSize'], whole_file_read=observed, payload=payload, fdt_sha256=sha((run / 'after.dtb').read_bytes())))
    assert sorted(x['stage'] for x in cases) == [3, 6]
    failures = []
    for path in args.failed_run:
        path = path.resolve(); rr = load(path / 'report.json'); assert not rr['passed']
        failures.append(dict(private_run=str(path.relative_to(ROOT)), report_sha256=sha((path / 'report.json').read_bytes()), nonce_matched=rr.get('nonce_matched', False), auto_recovered_from_bootloader=rr.get('auto_recovered_from_bootloader', False)))
    report = dict(passed=True, implementation_revision=revision, cases=cases, failed_runs_retained=failures, git_bound_input_count=len(bound), source_paths=sorted(bound), xnu_handset_executed=False, valid_adt_supplied=False, limits=['Separate experimental arena grant is outside the downloaded Image; not full RAM or DMA ownership proof', 'Full kernel file read only; NativeHandoff FALSE, placeholder ADT, no ExitBootServices or XNU execution'], verifier_sha256=sha(Path(__file__).read_bytes()))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, stages=[x['stage'] for x in cases], git_bound_input_count=len(bound)), indent=2))

if __name__ == '__main__':
    main()
