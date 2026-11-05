#!/usr/bin/env python3
"""Record source-device vendor declarations; do not authorize new firmware placement."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('collection', type=Path)
    source = parser.parse_args().collection.resolve()
    candidates = []
    for ui in (source / 'xbl-extracted').rglob('*.ui'):
        if ui.read_bytes().decode('utf-16-le').rstrip('\0') == 'uefiplat.cfg':
            candidates.extend(ui.parent.glob('*.raw'))
    assert len(candidates) == 1
    path = candidates[0]
    raw = path.read_bytes()
    section = None
    entries = []
    for line_number, line in enumerate(raw.decode('ascii').splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            section = stripped[1:-1]
        if section not in ['MemoryMap', 'RegisterMap'] or not stripped.startswith('0x'):
            continue
        row = next(csv.reader([stripped], skipinitialspace=True))
        assert len(row) == 8, (line_number, row)
        base, size = int(row[0], 0), int(row[1], 0)
        assert size > 0 and base + size <= 1 << 64
        entries.append(dict(section=section, source_line=line_number, base=base, size=size,
                            base_hex=hex(base), size_hex=hex(size), label=row[2],
                            hob=row[3], resource_type=row[4], resource_attributes=row[5],
                            memory_type=row[6], cache_attributes=row[7]))
    report = dict(status='vendor-declared; not verified free at new-firmware entry',
                  source_partition='xbl', source_partition_sha256=hashlib.sha256((source / 'xbl.img').read_bytes()).hexdigest(),
                  config_file_guid=path.parent.name[5:], config_sha256=hashlib.sha256(raw).hexdigest(),
                  entries=entries,
                  limits=['Configuration can be overridden at runtime; referenced uefiplatLA.cfg not found by UI name in current extraction',
                          'Original FD/stack can still be used by bootloader services; do not overwrite based solely on this file',
                          'Display Reserved does not specify active GOP base, format or stride'])
    target = ROOT / 'UniXNU-raphael/evidence/vendor-declared-layout.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    for item in entries:
        if item['label'] in ['UEFI FD', 'UEFI Stack', 'SEC Heap', 'MMU PageTables', 'Log Buffer', 'Display Reserved']:
            print(item['label'], item['base_hex'], item['size_hex'], 'source-line=', item['source_line'])
    print(target)


if __name__ == '__main__':
    main()
