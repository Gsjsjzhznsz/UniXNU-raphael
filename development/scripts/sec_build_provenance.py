#!/usr/bin/env python3
"""Validate an archived handset build without substituting current source."""
import json
import subprocess
from pathlib import Path
from entry_probe import ROOT, sha


def verify_archived_build(build, description, binding_path):
    binding_path = binding_path.resolve()
    assert binding_path.is_relative_to(ROOT / 'UniXNU-raphael/evidence')
    binding_raw = binding_path.read_bytes()
    binding = json.loads(binding_raw)
    revision = binding['source_revision']
    assert len(revision) == 40 and all(c in '0123456789abcdef' for c in revision)
    assert subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', revision + '^{commit}'], text=True).strip() == revision
    phases = [x for x in binding['phases'] if x['private_build'] == str(build.relative_to(ROOT))]
    assert len(phases) == 1
    phase = phases[0]
    assert phase['stage'] == {2: 2, 3: 3, 4: 6}[description['stop_stage']]
    for name in ['image_sha256', 'firmware_sha256']:
        assert phase[name] == description[name]
    assert description['compiled_from_source_snapshot']
    assert description['source_snapshot'] == 'source-snapshot/'
    assert binding['source_inputs'] == description['source_inputs']
    assert binding['upstream_inputs'] == description['upstream_inputs']
    assert binding['unixnu_revision'] == description['unixnu_revision']
    assert binding.get('darwin_inputs',[])==description.get('darwin_inputs',[])
    assert binding.get('darwin_revision')==description.get('darwin_revision')
    count = 0
    for group, repository, commit, prefix in [
        ('source_inputs', ROOT, revision, ''),
        ('upstream_inputs', ROOT / 'sources/UniXNU', description['unixnu_revision'], 'sources/UniXNU/'),
        *([('darwin_inputs',ROOT/'sources/UniXNU/drivers/DarwinBoot',description['darwin_revision'],'sources/UniXNU/drivers/DarwinBoot/')] if description.get('darwin_test') else []),
    ]:
        for item in description[group]:
            relative = Path(item['path'])
            assert not relative.is_absolute() and '..' not in relative.parts
            name = relative.as_posix()
            assert name.startswith(prefix)
            snapshot = build / 'source-snapshot' / relative
            assert snapshot.resolve().is_relative_to(build / 'source-snapshot')
            raw = snapshot.read_bytes()
            assert sha(raw) == item['sha256'], 'archived snapshot changed: ' + name
            git_raw = subprocess.check_output(['git', '-C', str(repository), 'show', commit + ':' + name[len(prefix):]])
            assert sha(git_raw) == item['sha256'], 'historical Git blob differs: ' + name
            count += 1
    qemu_path = ROOT / description['qemu_evidence']
    assert phase['qemu_report'] == description['qemu_evidence']
    qemu_raw = qemu_path.read_bytes()
    qemu = json.loads(qemu_raw)
    assert sha(qemu_raw)==phase['qemu_report_sha256']
    assert qemu.get('darwin_inputs',[])==description.get('darwin_inputs',[])
    assert qemu['qemu_passed'] and all(x['passed'] for x in qemu['executions'].values())
    for group in ['source_inputs', 'upstream_inputs']:
        assert qemu[group] == description[group]
    inspection = json.loads((build / 'fd-inspection.json').read_text())
    assert inspection['passed'] and inspection['sha256'] == description['firmware_sha256']
    fd_files = list((build / 'Build').glob('**/FV/*.fd'))
    matches = [x for x in fd_files if sha(x.read_bytes()) == description['firmware_sha256']]
    assert len(matches) == 1, 'archived firmware file not uniquely identified'
    assert sha((build / 'boot-sec-dxe.img').read_bytes()) == description['image_sha256']
    return dict(mode='archived-build-git-and-snapshot', source_revision=revision,
                unixnu_revision=description['unixnu_revision'], verified_source_inputs=count,
                source_binding=str(binding_path.relative_to(ROOT)), source_binding_sha256=sha(binding_raw),
                build_report_sha256=sha((build / 'report.json').read_bytes()),
                qemu_report_sha256=sha(qemu_raw), reused_image=True)
