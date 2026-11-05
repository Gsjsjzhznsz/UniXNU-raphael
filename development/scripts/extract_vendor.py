#!/usr/bin/env python3
"""Extract local-device firmware modules and inventory DEPEX; no other boards."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def depex(data):
    names = {0: 'BEFORE', 1: 'AFTER', 2: 'PUSH', 3: 'AND', 4: 'OR', 5: 'NOT', 6: 'TRUE', 7: 'FALSE', 8: 'END', 9: 'SOR'}
    tokens = []
    cursor = 0
    while cursor < len(data):
        opcode = data[cursor]
        cursor += 1
        token = dict(op=names.get(opcode, 'UNKNOWN_' + hex(opcode)))
        if opcode in (0, 1, 2):
            assert cursor + 16 <= len(data), 'Truncated DEPEX GUID'
            token['guid'] = str(uuid.UUID(bytes_le=data[cursor:cursor + 16]))
            cursor += 16
        tokens.append(token)
        if opcode == 8:
            assert not any(data[cursor:]), 'Unexpected bytes after DEPEX END'
            break
    return tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('collection', type=Path)
    parser.add_argument('--partition', choices=['xbl', 'abl', 'imagefv'], default='xbl')
    args = parser.parse_args()
    collection = args.collection.resolve()
    partition = args.partition
    extracted = collection / (partition + '-extracted')
    command = [str(ROOT / '.venv/bin/uefi-firmware-parser'), '-b', '-e', '-p', '-o', str(extracted), str(collection / (partition + '.img'))]
    if not extracted.exists():
        result = subprocess.run(command, capture_output=True, timeout=120)
        (collection / (partition + '-parser.log')).write_bytes(result.stdout + result.stderr)
        assert result.returncode == 0
    modules = []
    for ui in sorted(extracted.rglob('*.ui')):
        folder = ui.parent
        if not folder.name.startswith('file-'):
            continue
        item = dict(name=ui.read_bytes().decode('utf-16-le').rstrip('\0'), file_guid=folder.name[5:],
                    source_partition=partition, source_partition_sha256=digest(collection / (partition + '.img')),
                    private_relative_directory=str(folder.relative_to(collection)), images=[], dependencies=[],
                    use='reference-only; no module linked into new firmware',
                    limits='DEPEX lists dispatch prerequisites; does not establish every runtime protocol or data dependency')
        item['ffs_object_sha256'] = digest(folder / 'file.obj')
        item['raw_sections'] = [dict(file=path.name, bytes=path.stat().st_size, sha256=digest(path))
                                for path in sorted(folder.glob('*.raw'))]
        for path in sorted(folder.glob('*.pe')):
            raw = path.read_bytes()
            pe = struct.unpack_from('<I', raw, 0x3c)[0] if raw[:2] == b'MZ' else 0
            machine = struct.unpack_from('<H', raw, pe + 4)[0] if raw[pe:pe + 4] == b'PE\0\0' else None
            item['images'].append(dict(file=path.name, bytes=len(raw), sha256=digest(path), machine=machine))
        for path in sorted(folder.glob('*.depex')):
            item['dependencies'].append(dict(sha256=digest(path), tokens=depex(path.read_bytes())))
        modules.append(item)
    tools = dict(command=command, version=subprocess.check_output([str(ROOT / '.venv/bin/pip'), 'freeze'], text=True).splitlines(),
                 wheels=[dict(file=path.name, sha256=digest(path)) for path in sorted((ROOT / '.cache/tools').glob('*.whl'))])
    prefix = '' if partition == 'xbl' else partition + '-'
    (collection / (prefix + 'vendor-extraction-tool.json')).write_text(json.dumps(tools, indent=2) + '\n')
    (collection / (prefix + 'vendor-modules.json')).write_text(json.dumps(modules, indent=2) + '\n')
    # Public-safe metadata only. No modules or private source paths are copied.
    public = [{key: value for key, value in item.items() if key != 'private_relative_directory'} for item in modules]
    filename = 'vendor-module-metadata.json' if partition == 'xbl' else partition + '-module-metadata.json'
    (ROOT / 'UniXNU-raphael/evidence' / filename).write_text(json.dumps(public, indent=2) + '\n')
    (ROOT / 'tool-inputs.lock.json').write_text(json.dumps({key: value for key, value in tools.items() if key != 'command'}, indent=2) + '\n')
    print('Named FFS objects:', len(modules))
    for item in modules:
        if item['name'] in ['DisplayDxe', 'PmicDxe', 'SPMI', 'ButtonsDxe', 'UFSDxe', 'ClockDxe', 'DALTLMM', 'ScmDxe']:
            print(item['name'], item['file_guid'], 'PE images=', len(item['images']), 'DEPEX=', len(item['dependencies']))


if __name__ == '__main__':
    main()
