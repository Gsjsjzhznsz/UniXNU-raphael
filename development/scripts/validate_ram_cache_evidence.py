#!/usr/bin/env python3
"""Recheck archived code, raw cached-page wires and normal Android recovery."""
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path
from entry_probe import ROOT, sha
from inspect_device import read_fdt
from sec_build_provenance import verify_archived_build
from ram_read_probe import decode as decode_before
from ram_mapped_probe import decode as decode_mapped
from ram_cache_write import decode


def checked(reference):
    path = (ROOT / reference['path']).resolve()
    assert path.is_relative_to(ROOT)
    assert sha(path.read_bytes()) == reference['sha256'], path
    return path


def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))


def main():
    evidence = ROOT / 'UniXNU-raphael/evidence'
    indexes = [p for p in evidence.glob('boot-ram-cache-observation-pages*.json')
               if p.stem.split('pages')[-1].isdigit()]
    assert indexes, 'No handset cached-page evidence'
    verified = []
    for path in sorted(indexes, key=lambda p: int(p.stem.split('pages')[-1])):
        item = json.loads(path.read_text())
        pages = item['pages']
        assert item['passed'] and item['tested_bytes'] == pages * 4096
        assert item['all_tested_original_bytes_restored'] and item['read_only_mapping_restored']
        assert not any(item[k] for k in ['new_allocator_memory', 'cross_page_alias_tested', 'ownership_proven', 'handset_xnu_executed'])
        assert [p['stage'] for p in item['phases']] == [2, 3]
        inputs = None
        source_hash = None
        references = []
        for phase in item['phases']:
            stage = phase['stage']
            binding_path = checked(phase['source_binding'])
            binding = json.loads(binding_path.read_text())
            assert binding['source_revision'] == item['source_revision'] and binding['ram_cache_write_pages'] == pages
            if inputs is not None:
                assert inputs == binding['source_inputs']
            inputs = binding['source_inputs']
            for script in binding['verification_inputs']:
                raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', binding['source_revision'] + ':' + script['path']])
                assert sha(raw) == script['sha256']
            h = json.loads(checked(phase['handoff']).read_text())
            attempt = json.loads(checked(phase['immutable_attempt']).read_text())
            assert all(h[k] == attempt[k] for k in h.keys() & attempt.keys())
            assert h['firmware_checkpoint_passed'] and h['ram_cache_checkpoint_verified'] and h['entry']['status'] == 0
            build = ROOT / h['private_build']
            description = json.loads((build / 'report.json').read_text())
            verify_archived_build(build, description, binding_path)
            if source_hash is not None:
                assert source_hash == description['source_sha256']
            source_hash = description['source_sha256']
            run = ROOT / phase['private_readback']
            assert run == ROOT / h['private_readback']
            blob = (run / 'after.dtb').read_bytes()
            assert sha(blob) == h['fdt_sha256']
            tree = read_fdt(blob)
            chosen = next(n for n in tree.walk() if n.name == 'chosen' and n.parent is tree)
            read_wire, mapped_wire, cache_wire = [(run / name).read_bytes() for name in ['ram-read.bin', 'ram-mapped.bin', 'ram-cache.bin']]
            for wire, key in [(read_wire, 'raphael,ram-read'), (mapped_wire, 'raphael,ram-mapped'), (cache_wire, 'raphael,ram-cache-write')]:
                assert wire == chosen.properties[key]
            policy = description['ram_read_evidence']['policy']
            before = decode_before(read_wire, policy)
            mapped = decode_mapped(mapped_wire, before, stage)
            cache = decode(cache_wire, before, mapped, policy, pages, stage)
            assert before == phase['before'] == h['ram_read']
            assert mapped == phase['mapped'] == h['ram_mapped']
            assert cache == phase['cache'] == h['ram_cache']
            for name, key in [('firmware.log', 'log_sha256'), ('firmware-memory-map.bin', 'map_sha256')]:
                assert sha((run / name).read_bytes()) == h[key]
            references.extend(ref(run / n) for n in ['after.dtb', 'ram-read.bin', 'ram-mapped.bin', 'ram-cache.bin', 'firmware.log'])
        final = item['phases'][-1]['cache']['write']
        assert final['completed_pages'] == final['restored_pages'] == pages
        assert final['dirty'] == final['backup_words'] == final['pattern_mismatches'] == final['restore_mismatches'] == 0
        elapsed = (final['end_counter'] - final['start_counter']) * 1000 / final['frequency']
        assert elapsed == item['elapsed_ms'] and elapsed <= 8000
        cleanup_path = checked(item['cleanup'])
        cleanup = json.loads(cleanup_path.read_text())
        for key in ['normal_android_reboot', 'android_boot_completed', 'root_verified', 'boot_partition_unchanged', 'transient_probe_absent']:
            assert cleanup[key]
        assert not cleanup['flash_or_restore_performed']
        baseline = cleanup_path.parent / 'baseline.dtb'
        blob = baseline.read_bytes()
        assert sha(blob) == cleanup['fdt_sha256']
        tree = read_fdt(blob)
        chosen = next(n for n in tree.walk() if n.name == 'chosen' and n.parent is tree)
        assert not any(k.startswith('raphael,') for k in chosen.properties)
        commands_path = cleanup_path.parent / 'commands.json'
        commands = json.loads(commands_path.read_text())
        successes = [c for c in commands if c['returncode'] == 0]
        hashes = [(c.get('stdout') or '').split()[0] for c in successes if 'sha256sum' in ' '.join(c['arguments'])]
        assert len(hashes) == 2 and all(h == source_hash for h in hashes)
        assert any(c['arguments'] == ['reboot'] for c in successes)
        assert any((c.get('stdout') or '').startswith('uid=0') for c in successes)
        assert any('getprop sys.boot_completed' in ' '.join(c['arguments']) and (c.get('stdout') or '').strip() == '1' for c in successes)
        assert any('/sys/firmware/fdt' in ' '.join(c['arguments']) and c['stdout_sha256'] == sha(blob) for c in successes)
        references += [ref(baseline), ref(commands_path)]
        immutable = evidence / (path.stem + '-' + Path(item['phases'][-1]['private_readback']).name + '.json')
        assert immutable.read_bytes() == path.read_bytes()
        verified.append(dict(observation=ref(path), immutable_observation=ref(immutable), source_revision=item['source_revision'],
                             pages=pages, bytes=pages*4096, elapsed_ms=elapsed, raw_inputs=references,
                             archived_source_verified=True, wires_redecoded=True, firmware_original_restore_record_redecoded=True,
                             baseline_fdt_diagnostics_absent=True, normal_android_boot_root_and_boot_hash_rechecked=True))
    result = dict(passed=True, observations=verified, maximum_tested_bytes=max(i['bytes'] for i in verified),
                  allocator_enabled=False, ownership_proven=False, cross_page_alias_tested=False, handset_xnu_executed=False,
                  decoder_sha256=sha((ROOT / 'scripts/ram_cache_write.py').read_bytes()), runner_sha256=sha(Path(__file__).read_bytes()))
    parent = ROOT / 'artifacts/ram-cache-evidence-validation'
    parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'), dir=parent))
    raw = json.dumps(result, indent=2) + '\n'
    (out / 'report.json').write_text(raw)
    (evidence / 'ram-cache-independent-verification.json').write_text(raw)
    print(out)
    for i in verified:
        print(i['bytes'], 'bytes,', i['elapsed_ms'], 'ms: archived code, raw wires, firmware restore record and normal reboot rechecked')


if __name__ == '__main__':
    main()
