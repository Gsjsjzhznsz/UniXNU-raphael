#!/usr/bin/env python3
"""Bind the three real handset manager checkpoints to archived source and cleanup."""
import argparse
import json
from pathlib import Path
from entry_probe import ROOT, sha
from manager_probe import decode
from sec_build_provenance import verify_archived_build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cleanup', required=True, type=Path)
    args = parser.parse_args()
    binding_path = ROOT / 'UniXNU-raphael/evidence/manager-source-binding-stage6.json'
    binding = json.loads(binding_path.read_text())
    assert [p['stage'] for p in binding['phases']] == [2, 3, 6]
    phases = []
    final = None
    for phase in binding['phases']:
        stage = phase['stage']
        build = ROOT / phase['private_build']
        description = json.loads((build / 'report.json').read_text())
        verified = verify_archived_build(build, description, binding_path)
        path = ROOT / f'UniXNU-raphael/evidence/sec-manager-stage{stage}-handoff.json'
        report = json.loads(path.read_text())
        for key in ['firmware_checkpoint_passed', 'nonce_matched', 'root_verified',
                    'boot_partition_unchanged', 'android_boot_completed',
                    'payload_checkpoint_verified', 'manager_checkpoint_verified',
                    'physical_timer_checkpoint_verified']:
            assert report[key], (stage, key)
        assert report['sec_dxe_stage_verified'] == stage
        assert report['private_build'] == phase['private_build']
        assert report['build_source_verification']['source_revision'] == verified['source_revision']
        for key in ['image_sha256', 'firmware_sha256']:
            assert report[key] == description[key] == phase[key]
        private = ROOT / report['private_readback']
        raw = (private / 'manager-run.bin').read_bytes()
        assert decode(raw, stage, report['payload'], report['entry']['cntfrq']) == report['manager']
        attempt = ROOT / f'UniXNU-raphael/evidence/sec-dxe-attempt-{private.name}.json'
        immutable = json.loads(attempt.read_text())
        assert report.keys()-immutable.keys() == {'fdt_sha256', 'limits', 'log_sha256', 'map_sha256', 'source'}
        assert immutable.keys()-report.keys() == {'observation_seconds', 'started_utc'}
        assert all(report[k] == immutable[k] for k in report.keys() & immutable.keys())
        assert immutable['started_utc'] == private.name
        assert report['fdt_sha256'] == sha((private/'after.dtb').read_bytes())
        phases.append(dict(stage=stage, attempt=private.name, evidence=str(path.relative_to(ROOT)),
                           evidence_sha256=sha(path.read_bytes()),
                           immutable_attempt_sha256=sha(attempt.read_bytes()),
                           image_sha256=report['image_sha256'], firmware_sha256=report['firmware_sha256'],
                           manager=report['manager']))
        final = report
    cleanup_path = args.cleanup.resolve() / 'report.json'
    assert cleanup_path.is_relative_to(ROOT / 'evidence/private/entry-probe-cleanup')
    cleanup = json.loads(cleanup_path.read_text())
    assert cleanup_path.parent.name > phases[-1]['attempt']
    assert all(cleanup[k] for k in ['normal_android_reboot', 'android_boot_completed',
                                   'root_verified', 'boot_partition_unchanged', 'transient_probe_absent'])
    assert not cleanup['flash_or_restore_performed']
    manager = final['manager']
    timer = final['physical_timer']
    assert manager['complete_unixnu_manager_executed'] and manager['countdown_verified']
    assert timer['physical_only_timer_arch_verified'] and timer['restore_ok']
    assert timer['irq_count'] == timer['eoi_count'] == timer['notify_count'] > 0
    assert timer['unexpected'] == timer['spurious'] == 0
    result = dict(passed=True, source_revision=binding['source_revision'],
                  unixnu_revision=binding['unixnu_revision'], phases=phases,
                  manager=manager, payload=final['payload'], physical_timer=timer,
                  manager_elapsed_ticks=manager['end_counter']-manager['start_counter'],
                  manager_elapsed_seconds=(manager['end_counter']-manager['start_counter'])/manager['frequency'],
                  firmware_checkpoint_passed=True, handset_executed=True,
                  complete_unixnu_manager_executed=True, visible_manager_verified=False,
                  synthetic_read_only_payload_only=True, darwin_boot_executed=False, xnu_executed=False,
                  partition_writes_performed=False, cleanup=cleanup,
                  cleanup_private_directory=str(cleanup_path.parent.relative_to(ROOT)),
                  cleanup_report_sha256=sha(cleanup_path.read_bytes()),
                  recorder_sha256=sha(Path(__file__).read_bytes()),
                  limitations=['Headless synthetic exit configuration; no full manager visibility/input evidence',
                               'Physical-only TimerArch remains limited to a ten-second diagnostic',
                               'No handset DarwinBoot, XNU, permanent UEFI or complete RAM ownership claim'])
    target = ROOT / 'UniXNU-raphael/evidence/boot-manager-observation.json'
    assert not target.exists(), 'Keep existing observations immutable'
    target.write_text(json.dumps(result, indent=2)+'\n')
    main_binding = ROOT / 'UniXNU-raphael/evidence/manager-source-binding.json'
    assert not main_binding.exists()
    main_binding.write_bytes(binding_path.read_bytes())
    print(target)
    print('Manager elapsed seconds:', result['manager_elapsed_seconds'])
    print('Physical IRQ / EOI:', timer['irq_count'], timer['eoi_count'])


if __name__ == '__main__':
    main()
