#!/usr/bin/env python3
"""Export only committed source/metadata to a new Windows review directory."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    assert not destination.exists(), 'Never overwrite an existing checkpoint'
    assert not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'])
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'archive', '--format=tar', revision])
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        members = archive.getmembers()
        for member in members:
            path = Path(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            assert path.parts[0] not in ['evidence', 'sources', 'artifacts', 'logs', '.cache', '.venv']
            assert not member.issym() and not member.islnk()
        destination.mkdir(parents=True, exist_ok=False)
        archive.extractall(destination, filter='data')
    (destination / 'CHECKPOINT.json').write_text(json.dumps(dict(
        revision=revision, authoritative_workspace=str(ROOT),
        role='committed source and sanitized metadata snapshot; not a separate development tree',
        private_images_or_backups_included=False), indent=2) + '\n')
    print(destination)
    print('Revision:', revision)


if __name__ == '__main__':
    main()
