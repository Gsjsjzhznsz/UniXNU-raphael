#!/usr/bin/env python3
"""Independently bind cached-page builds and immutable handset readbacks."""
import argparse
import json
import subprocess
from pathlib import Path
from entry_probe import ROOT, sha
from sec_build_provenance import verify_archived_build
from inspect_device import read_fdt
from ram_read_probe import decode as decode_before
from ram_mapped_probe import decode as decode_mapped
from ram_cache_write import decode

EVIDENCE = ROOT / 'UniXNU-raphael/evidence'


def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))


def bind(build):
    d = json.loads((build / 'report.json').read_text())
    pages, stage = d['ram_cache_write_pages'], d['stop_stage']
    assert pages and stage in [2, 3] and d['ram_mapped_probe'] and not d['ram_write_pages']
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    qpath = ROOT / d['qemu_evidence']
    q = json.loads(qpath.read_text())
    assert q['qemu_passed'] and q['ram_cache_write_pages'] == pages and q['stop_stage'] == stage
    for group, repo, rev, prefix in [('source_inputs', ROOT, revision, ''),
                                    ('upstream_inputs', ROOT / 'sources/UniXNU', d['unixnu_revision'], 'sources/UniXNU/')]:
        assert d[group] == q[group]
        for item in d[group]:
            raw = (build / 'source-snapshot' / item['path']).read_bytes()
            assert sha(raw) == item['sha256']
            assert raw == subprocess.check_output(['git', '-C', str(repo), 'show', rev + ':' + item['path'][len(prefix):]])
    names = ['ram_cache_write.py', 'ram_mapped_probe.py', 'ram_read_probe.py', 'ram_write_probe.py',
             'audit_ram_cache.py', 'audit_ram_mapped.py', 'audit_ram_write.py', 'audit_ram_read.py',
             'validate_ram_cache.py', 'validate_ram_mapped.py', 'validate_ram_read.py', 'validate_ram_write.py',
             'run_ram_cache_qemu.py', 'build_sec_dxe.py', 'build_handset_sec_dxe.py', 'inspect_diagnostic_fd.py',
             'run_sec_dxe.py', 'sec_build_provenance.py', 'reboot_after_probe.py', 'record_ram_cache.py',
             'fixtures/sec_dxe_kernel.c', 'fixtures/ram_cache_host.c']
    checks = []
    for name in names:
        path = ROOT / 'scripts' / name
        assert path.read_bytes() == subprocess.check_output(['git', '-C', str(ROOT), 'show', revision + ':scripts/' + name])
        checks.append(ref(path))
    report = dict(source_revision=revision, unixnu_revision=d['unixnu_revision'], ram_cache_write_pages=pages,
                  source_inputs=d['source_inputs'], upstream_inputs=d['upstream_inputs'], verification_inputs=checks,
                  phases=[dict(stage=stage, private_build=str(build.relative_to(ROOT)), image_sha256=d['image_sha256'],
                               firmware_sha256=d['firmware_sha256'], qemu_report=d['qemu_evidence'], qemu_report_sha256=sha(qpath.read_bytes()))],
                  handset_executed=False)
    target = EVIDENCE / ('ram-cache-source-binding-pages' + str(pages) + '-stage' + str(stage) + '-' + build.name + '.json')
    assert not target.exists()
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(verify_archived_build(build, d, target), indent=2))
    print(target)


def record(bindings, runs, cleanup):
    phases = []
    sources = pages = revision = None
    for stage, binding_path, run in zip([2, 3], bindings, runs):
        binding = json.loads(binding_path.read_text())
        phase = binding['phases'][0]
        assert phase['stage'] == stage
        if sources is not None:
            assert sources == binding['source_inputs'] and pages == binding['ram_cache_write_pages']
            assert revision == binding['source_revision']
        sources, pages, revision = binding['source_inputs'], binding['ram_cache_write_pages'], binding['source_revision']
        build = ROOT / phase['private_build']
        d = json.loads((build / 'report.json').read_text())
        v = verify_archived_build(build, d, binding_path)
        for item in binding['verification_inputs']:
            assert sha(subprocess.check_output(['git', '-C', str(ROOT), 'show', revision + ':' + item['path']])) == item['sha256']
        assert run.is_relative_to(ROOT / 'evidence/private/sec-dxe-run')
        handoff = EVIDENCE / ('sec-ram-cache-pages' + str(pages) + '-stage' + str(stage) + '-handoff-' + run.name + '.json')
        h = json.loads(handoff.read_text())
        attempt = EVIDENCE / ('sec-dxe-attempt-' + run.name + '.json')
        a = json.loads(attempt.read_text())
        assert h.keys() - a.keys() == {'fdt_sha256', 'limits', 'log_sha256', 'map_sha256', 'source'}
        assert a.keys() - h.keys() == {'observation_seconds', 'started_utc'}
        assert all(h[k] == a[k] for k in h.keys() & a.keys())
        assert ROOT / h['private_readback'] == run and h['private_build'] == phase['private_build']
        for key in ['firmware_checkpoint_passed', 'ram_read_checkpoint_verified', 'ram_mapped_checkpoint_verified',
                    'ram_cache_checkpoint_verified', 'nonce_matched', 'root_verified', 'boot_partition_unchanged', 'android_boot_completed']:
            assert h[key], key
        assert h['sec_dxe_stage_verified'] == stage and h['entry']['status'] == 0
        assert h['build_source_verification']['source_revision'] == v['source_revision']
        for key in ['image_sha256', 'firmware_sha256']:
            assert h[key] == phase[key] == d[key]
        blob = (run / 'after.dtb').read_bytes()
        assert sha(blob) == h['fdt_sha256']
        tree = read_fdt(blob)
        chosen = next(n for n in tree.walk() if n.name == 'chosen' and n.parent is tree)
        raw = (run / 'ram-read.bin').read_bytes()
        assert raw == chosen.properties['raphael,ram-read']
        before = decode_before(raw, d['ram_read_evidence']['policy'])
        assert before == h['ram_read']
        raw = (run / 'ram-mapped.bin').read_bytes()
        assert raw == chosen.properties['raphael,ram-mapped']
        mapped = decode_mapped(raw, before, stage)
        assert mapped == h['ram_mapped']
        raw = (run / 'ram-cache.bin').read_bytes()
        assert raw == chosen.properties['raphael,ram-cache-write']
        cached = decode(raw, before, mapped, d['ram_read_evidence']['policy'], pages, stage)
        assert cached == h['ram_cache']
        assert sha((run / 'firmware.log').read_bytes()) == h['log_sha256']
        assert sha((run / 'firmware-memory-map.bin').read_bytes()) == h['map_sha256']
        phases.append(dict(stage=stage, source_binding=ref(binding_path), handoff=ref(handoff), immutable_attempt=ref(attempt),
                           private_readback=str(run.relative_to(ROOT)), image_sha256=h['image_sha256'],
                           firmware_sha256=h['firmware_sha256'], before=before, mapped=mapped, cache=cached))
    cp = cleanup / 'report.json'
    assert cp.is_relative_to(ROOT / 'evidence/private/entry-probe-cleanup') and cleanup.name > runs[-1].name
    c = json.loads(cp.read_text())
    for key in ['normal_android_reboot', 'android_boot_completed', 'root_verified', 'boot_partition_unchanged', 'transient_probe_absent']:
        assert c[key], key
    assert not c['flash_or_restore_performed']
    w = phases[-1]['cache']['write']
    result = dict(passed=True, pages=pages, tested_bytes=pages*4096, source_revision=revision, phases=phases, cleanup=ref(cp),
                  elapsed_ms=(w['end_counter']-w['start_counter'])*1000/w['frequency'], cache_poc_maintenance_verified=True,
                  all_tested_original_bytes_restored=True, read_only_mapping_restored=True,
                  android_return_and_clean_reboot_verified=True, new_allocator_memory=False,
                  cross_page_alias_tested=False, ownership_proven=False, handset_xnu_executed=False)
    target = EVIDENCE / ('boot-ram-cache-observation-pages' + str(pages) + '.json')
    result_bytes = json.dumps(result, indent=2) + '\n'
    immutable = EVIDENCE / (target.stem + '-' + runs[-1].name + '.json')
    assert not immutable.exists()
    immutable.write_text(result_bytes)
    target.write_text(result_bytes)
    print(target)
    print('Pages:', pages, 'elapsed ms:', result['elapsed_ms'], 'original bytes and RO map restored; Android cleanup verified')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    b = sub.add_parser('bind')
    b.add_argument('--build', required=True, type=Path)
    r = sub.add_parser('record')
    for name in ['stage2-binding', 'stage3-binding', 'stage2-run', 'stage3-run', 'cleanup']:
        r.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    if args.mode == 'bind':
        bind(args.build.resolve())
    else:
        record([args.stage2_binding.resolve(), args.stage3_binding.resolve()],
               [args.stage2_run.resolve(), args.stage3_run.resolve()], args.cleanup.resolve())


if __name__ == '__main__':
    main()
