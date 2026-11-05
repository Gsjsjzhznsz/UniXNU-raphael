#!/usr/bin/env python3
"""Expose original Apple desktop system disks for read-only host emulation only."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import struct
import subprocess
import re
import sys
import uuid
import zlib
from entry_probe import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'artifacts/desktop-system/ipsw/21H461')
    parser.add_argument('--raw-os', type=Path, help='Reuse an already decompressed OS raw disk')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'sources/UniXNU/scripts'))
    from unixnu.udif import Image
    out = ROOT / 'artifacts/desktop-disks' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    report = dict(passed=False, handset_written=False, filesystem_modified=False, disks=[])
    try:
        for role, name in [('OS', '044-76040-038.dmg'), ('SystemOS', '044-76034-038.dmg')]:
            source = (args.inputs / name).resolve()
            image = Image(source)
            target = out / (role + '.raw')
            print(f'{role}: {image.size} raw bytes', flush=True)
            if role == 'OS' and args.raw_os:
                assert args.raw_os.stat().st_size == image.size
                target.symlink_to(args.raw_os.resolve())
            elif image.chunks is None:
                target.symlink_to(source)
            else:
                partial = target.with_suffix('.partial')
                with partial.open('xb') as stream:
                    for block in image.blocks():
                        if block.strip(b'\0'):
                            stream.write(block)
                        else:
                            stream.seek(len(block), os.SEEK_CUR)
                    stream.truncate()
                    stream.flush()
                    os.fsync(stream.fileno())
                assert partial.stat().st_size == image.size
                partial.chmod(0o444)
                partial.rename(target)
            with target.open('rb') as stream:
                first = stream.read(4096)
                containers = []
                if first[32:36] == b'NXSB':
                    candidates = [(0, image.size)]
                else:
                    header = bytearray(first[512:1024])
                    assert header[:8] == b'EFI PART', 'Expected GPT or raw APFS container'
                    header_bytes, checksum = struct.unpack_from('<II', header, 12)
                    assert 92 <= header_bytes <= 512
                    struct.pack_into('<I', header, 16, 0)
                    assert zlib.crc32(header[:header_bytes]) == checksum, 'GPT header CRC'
                    lba, count, stride, entries_crc = struct.unpack_from('<QIII', header, 72)
                    assert 0 < count <= 4096 and 128 <= stride <= 4096
                    stream.seek(lba * 512)
                    entries = stream.read(count * stride)
                    assert zlib.crc32(entries) == entries_crc, 'GPT partition array CRC'
                    candidates = []
                    for index in range(count):
                        entry = entries[index*stride:(index+1)*stride]
                        if uuid.UUID(bytes_le=entry[:16]) != uuid.UUID('7c3457ef-0000-11aa-aa11-00306543ecac'):
                            continue
                        start, end = struct.unpack_from('<QQ', entry, 32)
                        assert start <= end and (end+1)*512 <= image.size
                        candidates.append((start*512, (end-start+1)*512))
                assert candidates, 'No APFS container in original disk'
                for offset, length in candidates:
                    stream.seek(offset)
                    superblock = stream.read(4096)
                    assert superblock[32:36] == b'NXSB', 'APFS container superblock'
                    block_size, blocks = struct.unpack_from('<IQ', superblock, 36)
                    assert block_size == 4096 and blocks * block_size <= length
                    info=subprocess.check_output(['fsapfsinfo','-o',str(offset),str(target)],text=True)
                    (out/(role+'-apfs-info.txt')).write_text(info)
                    volume_ids=re.findall(r'Volume: [0-9]+ information:[\s\S]*?Identifier\s*: ([0-9a-f-]{36})',info)
                    assert volume_ids, 'No readable APFS volume metadata'
                    containers.append(dict(offset=offset, bytes=length, block_bytes=block_size,
                                           blocks=blocks, uuid=str(uuid.UUID(bytes=superblock[72:88])),volumes=volume_ids))
            report['disks'].append(dict(role=role, source=str(source.relative_to(ROOT)),
                path=str(target.relative_to(ROOT)), bytes=image.size,
                original_source_unchanged=True, raw_symlink=target.is_symlink(),
                apfs_containers=containers))
        report['passed'] = True
    finally:
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(out, flush=True)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
