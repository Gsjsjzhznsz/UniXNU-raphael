#!/usr/bin/env python3
"""Pack only the freshly collected handset kernel/DTBs/ramdisk and new probe.

Output is private: it contains proprietary/current-device Android inputs.
Nothing is flashed or executed by this build command.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import struct
import uuid
from entry_probe import ROOT, image_parameters, compile_probe, instrument, align, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--requested-image-size', type=lambda x: int(x, 0),
                        help='Pad the downloaded Image to a checked candidate size; no tail writes')
    args = parser.parse_args()
    collection = args.collection.resolve()
    assert (collection / 'COMPLETE').is_file()
    raw = (collection / 'boot.img').read_bytes()
    input_sha = sha(raw)
    inventory = json.loads((ROOT / 'UniXNU-raphael/proprietary-inputs.json').read_text())
    assert next(x['sha256'] for x in inventory if x['name'] == 'boot') == input_sha
    assert raw[:8] == b'ANDROID!'
    kernel_size, _, ramdisk_size, _, second_size, _, _, page, version = struct.unpack_from('<9I', raw, 8)
    assert page == 4096 and version == 1 and second_size == 0
    assert struct.unpack_from('<I', raw, 1632)[0] == 0, 'Recovery-DTBO packing not implemented'
    kernel = raw[page:page + kernel_size]
    ramdisk_at = page + align(kernel_size, page)
    ramdisk = raw[ramdisk_at:ramdisk_at + ramdisk_size]
    assert len(ramdisk) == ramdisk_size
    assert kernel[:16] == b'UNCOMPRESSED_IMG'
    declared = struct.unpack_from('<I', kernel, 16)[0]
    image, trailer = kernel[20:20 + declared], kernel[20 + declared:]
    assert len(image) == declared and trailer[:4] == b'\xd0\x0d\xfe\xed'
    at, dtbs = 0, []
    while at < len(trailer):
        assert trailer[at:at + 4] == b'\xd0\x0d\xfe\xed'
        length = struct.unpack_from('>I', trailer, at + 4)[0]
        assert 40 <= length <= len(trailer) - at
        dtbs.append(dict(bytes=length, sha256=sha(trailer[at:at + length])))
        at += length
    parameters = image_parameters(image)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'evidence/private/entry-probe-build' / stamp
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    identifier = 'raphael-entry-v1-' + uuid.uuid4().hex
    payload = compile_probe(out, parameters, identifier)
    padded_payload = payload
    if args.requested_image_size is not None:
        plan = json.loads((ROOT / 'UniXNU-raphael/evidence/memory-plan-check.json').read_text())
        assert plan['passed'] and not plan['boot_enabled']
        assert args.requested_image_size == plan['requested_image_size']
        assert parameters['image_size'] == plan['regions'][0]['base'] - plan['requested_image_base'] or \
               parameters['probe_offset'] == plan['regions'][0]['base'] - plan['requested_image_base']
        assert args.requested_image_size >= parameters['probe_offset'] + len(payload)
        assert args.requested_image_size % page == 0 and args.requested_image_size < 128 * 1024 * 1024
        padded_payload += bytes(args.requested_image_size - parameters['probe_offset'] - len(payload))
    instrumented = instrument(image, padded_payload, parameters)
    new_kernel = kernel[:16] + struct.pack('<I', len(instrumented)) + instrumented + trailer
    header = bytearray(raw[:page])
    struct.pack_into('<I', header, 8, len(new_kernel))
    digest = hashlib.sha1()
    for part in [new_kernel, ramdisk, b'', b'']:
        digest.update(part)
        digest.update(struct.pack('<I', len(part)))
    header[576:608] = digest.digest() + bytes(12)
    result = bytes(header) + new_kernel + bytes(align(len(new_kernel), page) - len(new_kernel))
    result += ramdisk + bytes(align(len(ramdisk), page) - len(ramdisk))
    assert len(result) <= len(raw)
    result += bytes(len(raw) - len(result))
    # Independently round-trip the actual sections from the final file.
    assert result[page:page + len(new_kernel)] == new_kernel
    new_ramdisk_at = page + align(len(new_kernel), page)
    assert result[new_ramdisk_at:new_ramdisk_at + ramdisk_size] == ramdisk
    assert new_kernel[20 + len(instrumented):] == trailer
    assert struct.unpack_from('<I', result, 8)[0] == len(new_kernel)
    (out / 'boot-entry-probe.img').write_bytes(result)
    report = dict(kind='temporary Linux-entry probe; not UEFI firmware',
                  source_partition='boot', source_sha256=input_sha,
                  source_unchanged_kernel_image_sha256=sha(image),
                  identifier=identifier, parameters=parameters,
                  probe_bytes=len(payload), probe_sha256=sha(payload),
                  extended_arm64_image_bytes=len(instrumented),
                  candidate_extent_download_test=args.requested_image_size is not None,
                  zero_tail_padding_bytes=len(padded_payload) - len(payload),
                  padded_tail_written_or_read_by_probe=False,
                  kernel_bytes=len(new_kernel), ramdisk_bytes=len(ramdisk),
                  unchanged_ramdisk_sha256=sha(ramdisk), unchanged_appended_dtbs=dtbs,
                  image_sha256=sha(result), image_bytes=len(result),
                  changed_original_image_fields=['code0 (B instruction)', 'image_size'],
                  restored_before_original_entry=True,
                  original_kernel_relocated=False, fixed_physical_addresses_used=False,
                  inherited_original_header_parameters=True,
                  avb_footer_copied=False,
                  proprietary=True, publicly_redistributable=False,
                  host_build=True, structure_checked=True, handset_executed=False,
                  limits=['Bootloader mirror is an interface reference, not an exact binary source match',
                          'Successful Android return and a matching nonce are both required to validate execution',
                          'No claim of UEFI, framebuffer, physical keys, DarwinBoot or XNU execution'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(out)


if __name__ == '__main__':
    main()
