#!/usr/bin/env python3
"""Strict current-device boot-v1 input and repacking; no firmware fetching."""
import hashlib
import json
import struct
from entry_probe import ROOT, align, sha


def read_boot(collection):
    assert (collection / 'COMPLETE').is_file()
    raw = (collection / 'boot.img').read_bytes()
    inventory = json.loads((ROOT / 'UniXNU-raphael/proprietary-inputs.json').read_text())
    assert sha(raw) == next(x['sha256'] for x in inventory if x['name'] == 'boot')
    assert raw[:8] == b'ANDROID!'
    ks, _, rs, _, ss, _, _, page, version = struct.unpack_from('<9I', raw, 8)
    assert page == 4096 and version == 1 and ss == 0
    assert struct.unpack_from('<I', raw, 1632)[0] == 0
    kernel = raw[page:page + ks]
    ramdisk_at = page + align(ks, page)
    ramdisk = raw[ramdisk_at:ramdisk_at + rs]
    assert len(ramdisk) == rs and kernel[:16] == b'UNCOMPRESSED_IMG'
    n = struct.unpack_from('<I', kernel, 16)[0]
    image, trailer = kernel[20:20 + n], kernel[20 + n:]
    assert len(image) == n
    at, dtbs = 0, []
    while at < len(trailer):
        assert trailer[at:at + 4] == b'\xd0\x0d\xfe\xed'
        size = struct.unpack_from('>I', trailer, at + 4)[0]
        assert 40 <= size <= len(trailer) - at
        dtbs.append(dict(bytes=size, sha256=sha(trailer[at:at + size])))
        at += size
    assert len(dtbs) == 4
    return dict(raw=raw, image=image, trailer=trailer, ramdisk=ramdisk, page=page, dtbs=dtbs)


def repack(boot, image, ramdisk=None):
    raw, page = boot['raw'], boot['page']
    if ramdisk is None: ramdisk = boot['ramdisk']
    kernel = b'UNCOMPRESSED_IMG' + struct.pack('<I', len(image)) + image + boot['trailer']
    header = bytearray(raw[:page])
    struct.pack_into('<I', header, 8, len(kernel))
    struct.pack_into('<I', header, 16, len(ramdisk))
    digest = hashlib.sha1()
    for part in [kernel, ramdisk, b'', b'']:
        digest.update(part)
        digest.update(struct.pack('<I', len(part)))
    header[576:608] = digest.digest() + bytes(12)
    result = bytes(header) + kernel + bytes(align(len(kernel), page) - len(kernel))
    result += ramdisk + bytes(align(len(ramdisk), page) - len(ramdisk))
    assert len(result) <= len(raw)
    result += bytes(len(raw) - len(result))
    # Exact section round trip, including the freshly collected closed inputs.
    at = page + align(len(kernel), page)
    assert result[page:page + len(kernel)] == kernel
    assert result[at:at + len(ramdisk)] == ramdisk
    assert kernel[20 + len(image):] == boot['trailer']
    return result
