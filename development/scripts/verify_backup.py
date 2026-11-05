#!/usr/bin/env python3
"""Verify the supplied backup, opening only in read mode. No restoration claim."""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/mnt/d/PhoneBackups/raphael/2026-10-27').resolve()


def main():
    records = []
    for line in (BACKUP / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        target = (BACKUP / name).resolve()
        assert target.is_relative_to(BACKUP), 'Checksum path leaves backup directory'
        before = target.stat()
        digest = hashlib.sha256()
        with target.open('rb') as stream:
            while chunk := stream.read(8 * 1024 * 1024):
                digest.update(chunk)
        after = target.stat()
        assert before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
        records.append(dict(name=name, bytes=before.st_size, matched=digest.hexdigest() == expected))
    assert records and all(record['matched'] for record in records)
    out = ROOT / 'evidence/private/backup-verification' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    report = dict(backup=str(BACKUP), verified_files=len(records),
                  total_bytes=sum(record['bytes'] for record in records), passed=True,
                  limitation='Checksum consistency only; incomplete phone backup, not restore-tested', files=records)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print({key: value for key, value in report.items() if key != 'files'})
    print(out)


if __name__ == '__main__':
    main()
