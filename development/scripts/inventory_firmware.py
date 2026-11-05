#!/usr/bin/env python3
"""Inventory raw FV headers and top-level FFS files without executing firmware."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import uuid

ROOT = Path(__file__).resolve().parents[1]


def volumes(raw):
    result = []
    cursor = 0
    while True:
        position = raw.find(b'_FVH', cursor)
        if position < 0:
            break
        cursor = position + 4
        base = position - 40
        if base < 0 or base + 56 > len(raw):
            continue
        size = struct.unpack_from('<Q', raw, base + 32)[0]
        header_size = struct.unpack_from('<H', raw, base + 48)[0]
        if not (56 <= header_size <= size <= len(raw) - base) or header_size % 2:
            continue
        header = raw[base:base + header_size]
        if sum(struct.unpack('<' + 'H' * (len(header) // 2), header)) & 0xffff:
            continue
        attributes = struct.unpack_from('<I', raw, base + 44)[0]
        files = []
        ext_offset = struct.unpack_from('<H', raw, base + 52)[0]
        at = (header_size + 7) & ~7
        if ext_offset:
            if ext_offset + 20 > size:
                continue
            ext_size = struct.unpack_from('<I', raw, base + ext_offset + 16)[0]
            if ext_size < 20 or ext_offset + ext_size > size:
                continue
            at = (max(header_size, ext_offset + ext_size) + 7) & ~7
        while at + 24 <= size:
            ffs = raw[base + at:base + at + 24]
            erased = b'\xff' if attributes & 0x800 else b'\0'
            if ffs == erased * 24:
                break
            length = int.from_bytes(ffs[20:23], 'little')
            file_header = 24
            if ffs[19] & 1:
                if at + 32 > size or length != 0xffffff:
                    break
                length = struct.unpack_from('<Q', raw, base + at + 24)[0]
                file_header = 32
            if length < file_header or at + length > size:
                break
            guid = str(uuid.UUID(bytes_le=ffs[:16]))
            sections = []
            section_at = at + file_header
            while section_at + 4 <= at + length:
                section_size = int.from_bytes(raw[base + section_at:base + section_at + 3], 'little')
                kind = raw[base + section_at + 3]
                section_header = 4
                if section_size == 0xffffff:
                    if section_at + 8 > at + length:
                        break
                    section_size = struct.unpack_from('<I', raw, base + section_at + 4)[0]
                    section_header = 8
                if section_size < section_header or section_at + section_size > at + length:
                    break
                data = raw[base + section_at + section_header:base + section_at + section_size]
                entry = dict(type=kind, bytes=section_size)
                if kind == 0x15:
                    entry['ui_name'] = data.decode('utf-16-le', errors='replace').rstrip('\0')
                if kind == 0x13:
                    entry['dxe_depex_hex'] = data.hex()
                if kind in (0x10, 0x12):
                    entry['image_sha256'] = hashlib.sha256(data).hexdigest()
                if kind in (1, 2, 0x17):
                    entry['limitation'] = 'Nested/compressed section; top-level scan does not resolve drivers or dependencies'
                sections.append(entry)
                section_at = (section_at + section_size + 3) & ~3
            files.append(dict(guid=guid, type=ffs[18], state=ffs[23], offset=base + at,
                              bytes=length, sections=sections))
            at = (at + length + 7) & ~7
        result.append(dict(offset=base, bytes=size, header_bytes=header_size,
                           filesystem_guid=str(uuid.UUID(bytes_le=raw[base + 16:base + 32])),
                           header_checksum_valid=True, files=files))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('collection', type=Path)
    source = parser.parse_args().collection.resolve()
    records = []
    purposes = {
        'boot': 'Current boot format and Linux/DT reference; modified kernel, not assumed factory stock',
        'dtbo': 'Board overlay and IDs; compare against live FDT and Xiaomi primary source',
        'xbl': 'Inventory original-device UEFI firmware volumes and possible protocol providers',
        'xbl_config': 'Source-device early boot configuration; not consumed by current diagnostic',
        'abl': 'Bootloader format and protocol investigation; no replacement or execution',
        'imagefv': 'Vendor firmware-volume inventory; dependencies unresolved',
        'uefisecapp': 'Secure firmware input inventory; no execution or reuse approved by this scan',
    }
    for name, purpose in purposes.items():
        path = source / (name + '.img')
        raw = path.read_bytes()
        item = dict(name=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                    source='/dev/block/bootdevice/by-name/' + name,
                    collection='fresh read-only ADB exec-out; byte count and before/after source hash matched',
                    purpose=purpose, current_use='reference-only; not linked into any artifact',
                    redistribution='private; excluded from version control',
                    dependency_status='Not established; volume inventory is not a dependency proof')
        item['container'] = 'ELF' if raw.startswith(b'\x7fELF') else 'Android boot' if raw.startswith(b'ANDROID!') else 'other'
        item['firmware_volumes'] = volumes(raw)
        records.append(item)
    private = source / 'firmware-inventory.json'
    private.write_text(json.dumps(records, indent=2) + '\n')
    public = ROOT / 'UniXNU-raphael/proprietary-inputs.json'
    public.write_text(json.dumps([{key: value for key, value in record.items() if key != 'firmware_volumes'} for record in records], indent=2) + '\n')
    for record in records:
        print(record['name'], record['container'], 'FV=', len(record['firmware_volumes']),
              'FFS=', sum(len(fv['files']) for fv in record['firmware_volumes']))


if __name__ == '__main__':
    main()
