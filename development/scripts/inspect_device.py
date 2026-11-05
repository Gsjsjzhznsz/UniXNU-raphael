#!/usr/bin/env python3
"""Extract sourced observations, never turn Linux memory into a UEFI allocator map."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'sources/UniXNU/scripts'))
from unixnu.devicetree import read_fdt, registers, physical, number
from unixnu.util import Error


def sha(data):
    return hashlib.sha256(data).hexdigest()


def node_path(node):
    if node.parent is None:
        return '/'
    return node_path(node.parent).rstrip('/') + '/' + node.name


def region(base, size, source):
    assert base >= 0 and size > 0 and base + size <= 1 << 64
    return dict(base=base, size=size, end_exclusive=base + size,
                base_hex=hex(base), size_hex=hex(size), source=source)


def fdt_summary(blob):
    root = read_fdt(blob)
    anomalies = []
    def strings(node, key):
        try:
            return node.strings(key)
        except Error as exc:
            anomalies.append(dict(node=node_path(node), property=key, error=str(exc)))
            return []
    memory, fixed, dynamic, peripherals, cpus = [], [], [], [], []
    for node in root.walk():
        path = node_path(node)
        props = node.properties
        if strings(node, 'device_type') == ['memory']:
            for base, size in registers(node):
                memory.append(region(physical(node.parent, base, size), size, path + ':reg'))
        if path.startswith('/reserved-memory/') and node.parent.name == 'reserved-memory':
            if 'reg' in props:
                for base, size in registers(node):
                    item = region(physical(node.parent, base, size), size, path + ':reg')
                    item.update(no_map='no-map' in props, reusable='reusable' in props)
                    fixed.append(item)
            elif 'size' in props:
                dynamic.append(dict(node=path, requested_bytes=number(node.cells('size')),
                                    alloc_ranges=node.cells('alloc-ranges'),
                                    limitation='Address selected by Linux, not specified by this property'))
        if strings(node, 'device_type') == ['cpu']:
            cpus.append(dict(node=path, affinity=number(node.cells('reg')),
                             compatible=strings(node, 'compatible'), enabled=node.enabled(),
                             enable_method=strings(node, 'enable-method')))
        compatible = strings(node, 'compatible')
        interesting = any(value in compatible for value in ['arm,gic-v3', 'arm,armv8-timer', 'qcom,msm-geni', 'qcom,sm8150-tlmm', 'qcom,msm-qgic2', 'qcom,ufshc', 'qcom,msm-geni-uart', 'qcom,mdss-dsi-panel', 'gpio-keys', 'goodix,gt9889', 'qca,wcn3990'])
        if interesting:
            data = dict(node=path, compatible=compatible, enabled=node.enabled())
            if 'reg' in props:
                data['reg_cells'] = node.cells('reg')
                try:
                    spans = registers(node)
                    if any(size == 0 for _, size in spans):
                        data['reg_interpretation'] = 'Bus address without MMIO length; not translated'
                    else:
                        data['registers'] = [region(physical(node.parent, base, size), size, path + ':reg') for base, size in spans]
                except Error as exc:
                    data['reg_interpretation'] = str(exc)
            for prop in ['interrupts', 'clock-frequency', 'redistributor-stride', 'qcom,mdss-dsi-panel-width', 'qcom,mdss-dsi-panel-height', 'qcom,mdss-dsi-bpp', 'goodix,panel-max-x', 'goodix,panel-max-y']:
                if prop in props:
                    data[prop] = node.cells(prop)
            for prop in ['qcom,mdss-dsi-panel-name', 'qcom,mdss-dsi-panel-type']:
                if prop in props:
                    data[prop] = strings(node, prop)
            peripherals.append(data)
    reserve_offset = struct.unpack_from('>I', blob, 16)[0]
    memreserve = []
    while reserve_offset + 16 <= len(blob):
        base, size = struct.unpack_from('>QQ', blob, reserve_offset)
        reserve_offset += 16
        if base == size == 0:
            break
        memreserve.append(region(base, size, 'FDT header reservation table'))
    else:
        raise ValueError('Unterminated FDT reservation table')
    overlaps = []
    for i, a in enumerate(fixed):
        for b in fixed[i + 1:]:
            lo, hi = max(a['base'], b['base']), min(a['end_exclusive'], b['end_exclusive'])
            if lo < hi:
                overlaps.append(dict(first=a['source'], second=b['source'], base_hex=hex(lo), size_hex=hex(hi - lo)))
    return dict(model=root.strings('model'), compatible=root.strings('compatible'),
                qcom_msm_id=root.cells('qcom,msm-id'), qcom_board_id=root.cells('qcom,board-id'),
                memory=memory, dt_described_ram_bytes=sum(item['size'] for item in memory),
                fixed_reservations=fixed, dynamic_pools=dynamic, header_reservations=memreserve,
                overlapping_reservations=overlaps, cpus=cpus, peripherals=peripherals,
                malformed_properties=anomalies)


def scan_fdts(raw, destination, prefix):
    found = []
    offset = 0
    while True:
        offset = raw.find(b'\xd0\x0d\xfe\xed', offset)
        if offset < 0:
            break
        try:
            size = struct.unpack_from('>I', raw, offset + 4)[0]
            assert 40 <= size <= len(raw) - offset
            blob = raw[offset:offset + size]
            tree = read_fdt(blob)
        except (ValueError, AssertionError, struct.error, RuntimeError, Error):
            offset += 4
            continue
        try:
            summary = fdt_summary(blob)
        except (ValueError, AssertionError, struct.error, RuntimeError, Error) as exc:
            # A boot-time template may contain zero-sized RAM placeholders. Preserve
            # the structurally valid tree instead of rejecting it as a false match.
            summary = dict(model=tree.strings('model'), compatible=tree.strings('compatible'),
                           qcom_msm_id=tree.cells('qcom,msm-id'), qcom_board_id=tree.cells('qcom,board-id'),
                           resource_summary_unavailable=str(exc))
        name = f'{prefix}-{len(found):02}.dtb'
        (destination / name).write_bytes(blob)
        found.append(dict(file=name, offset=offset, size=size, sha256=sha(blob), summary=summary))
        offset += size
    return found


def inspect_boot(raw, out):
    assert raw[:8] == b'ANDROID!'
    values = struct.unpack_from('<10I', raw, 8)
    keys = ['kernel_size', 'kernel_addr', 'ramdisk_size', 'ramdisk_addr', 'second_size', 'second_addr', 'tags_addr', 'page_size', 'header_version', 'os_version']
    header = dict(zip(keys, values))
    page = header['page_size']
    assert page >= 2048 and page <= 65536 and page & (page - 1) == 0
    assert header['header_version'] <= 2, 'Only legacy Android boot headers supported'
    offset = page
    parts = []
    for name in ['kernel', 'ramdisk', 'second']:
        size = header[name + '_size']
        assert offset + size <= len(raw)
        content = raw[offset:offset + size]
        parts.append(dict(name=name, offset=offset, size=size, sha256=sha(content)))
        if size:
            (out / (name + '.bin')).write_bytes(content)
        offset += (size + page - 1) // page * page
    if header['header_version'] >= 1:
        recovery_size = struct.unpack_from('<I', raw, 1632)[0]
        recovery_offset = struct.unpack_from('<Q', raw, 1636)[0]
        header.update(recovery_dtbo_size=recovery_size, recovery_dtbo_offset=recovery_offset,
                      header_size=struct.unpack_from('<I', raw, 1644)[0])
        if recovery_size:
            assert recovery_offset >= offset and recovery_offset + recovery_size <= len(raw)
            (out / 'recovery-dtbo.bin').write_bytes(raw[recovery_offset:recovery_offset + recovery_size])
            offset = recovery_offset + (recovery_size + page - 1) // page * page
    if header['header_version'] == 2:
        size, address = struct.unpack_from('<IQ', raw, 1648)
        assert offset + size <= len(raw)
        header.update(dtb_size=size, dtb_addr=address)
        (out / 'header-dtb.bin').write_bytes(raw[offset:offset + size])
    kernel = (out / 'kernel.bin').read_bytes()
    kernel_info = dict(compression='none-or-unrecognized')
    if kernel.startswith(b'UNCOMPRESSED_IMG') and len(kernel) >= 84 and kernel[76:80] == b'ARM\x64':
        declared = struct.unpack_from('<I', kernel, 16)[0]
        assert 64 <= declared <= len(kernel) - 20
        image = kernel[20:20 + declared]
        text_offset, image_size, flags = struct.unpack_from('<QQQ', image, 8)
        (out / 'Image').write_bytes(image)
        kernel_info.update(compression='uncompressed-with-observed-20-byte-wrapper',
                           wrapper_magic='UNCOMPRESSED_IMG', wrapper_u32=declared,
                           image_sha256=sha(image), image_bytes=len(image),
                           wrapper_semantics='Observed length matches plausible payload; bootloader interpretation not source-verified',
                           arm64_image_header=dict(text_offset=text_offset, image_size=image_size, flags=flags,
                                                   limitation='Current Linux image metadata, not a UEFI FD address'))
        kernel_info['appended_fdts'] = scan_fdts(kernel[20 + declared:], out, 'kernel-appended')
        kernel_info['embedded_fdts'] = scan_fdts(image, out, 'image-embedded')
        kernel_info['trailing_prefix_hex'] = kernel[20 + declared:20 + declared + 32].hex()
    if kernel.startswith(b'\x1f\x8b'):
        decoder = zlib.decompressobj(31)
        decompressed = decoder.decompress(kernel, 256 * 1024 * 1024)
        assert decoder.eof and not decoder.unconsumed_tail
        (out / 'Image').write_bytes(decompressed)
        trailing = decoder.unused_data
        kernel_info.update(compression='gzip', compressed_stream_bytes=len(kernel) - len(trailing), image_bytes=len(decompressed),
                           image_sha256=sha(decompressed), trailing_bytes=len(trailing))
        kernel_info['appended_fdts'] = scan_fdts(trailing, out, 'kernel-appended')
        kernel_info['embedded_fdts'] = scan_fdts(decompressed, out, 'image-embedded')
        if len(decompressed) >= 64 and decompressed[56:60] == b'ARM\x64':
            text_offset, image_size, flags = struct.unpack_from('<QQQ', decompressed, 8)
            kernel_info['arm64_image_header'] = dict(text_offset=text_offset, image_size=image_size, flags=flags,
                                                    limitation='Describes current Linux image; not the UEFI FD placement')
    return dict(header=header, parts=parts, kernel=kernel_info)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('collection', type=Path)
    args = parser.parse_args()
    source = args.collection.resolve()
    assert (source / 'COMPLETE').is_file()
    out = source / 'analysis' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    blob = (source / 'live.dtb').read_bytes()
    facts = dict(evidence_kind='runtime-Android-observation', live_fdt_sha256=sha(blob),
                 facts=fdt_summary(blob), allocation_policy='NOT AN APPROVED UEFI ALLOCATION MAP')
    iomem = (source / 'iomem.txt').read_text()
    facts['linux_system_ram'] = [region(int(a, 16), int(b, 16) - int(a, 16) + 1, '/proc/iomem:System RAM')
                                 for a, b in re.findall(r'^([0-9a-f]+)-([0-9a-f]+) : System RAM$', iomem, re.M)]
    (out / 'hardware-observations.json').write_text(json.dumps(facts, indent=2) + '\n')
    boot = inspect_boot((source / 'boot.img').read_bytes(), out)
    (out / 'boot-analysis.json').write_text(json.dumps(boot, indent=2) + '\n')
    dtbo = (source / 'dtbo.img').read_bytes()
    magic, total, header_size, entry_size, count, entries_offset, page_size, version = struct.unpack_from('>8I', dtbo)
    assert magic == 0xd7b7ab1e and total <= len(dtbo) and header_size >= 32 and entry_size >= 32
    assert entries_offset >= header_size and entries_offset + count * entry_size <= total
    entries = []
    for index in range(count):
        size, offset, ident, rev, *custom = struct.unpack_from('>8I', dtbo, entries_offset + index * entry_size)
        assert offset >= entries_offset + count * entry_size and offset + size <= total
        blob = dtbo[offset:offset + size]
        summary = fdt_summary(blob)
        name = f'dtbo-{index:02}.dtb'
        (out / name).write_bytes(blob)
        entries.append(dict(index=index, size=size, offset=offset, id=ident, revision=rev,
                            custom=custom, sha256=sha(blob), file=name, summary=summary))
    (out / 'dtbo-analysis.json').write_text(json.dumps(dict(total_bytes=total, page_size=page_size, version=version, entries=entries), indent=2) + '\n')
    public = ROOT / 'UniXNU-raphael/evidence'
    public.mkdir(parents=True, exist_ok=True)
    (public / 'hardware-observations.json').write_text(json.dumps(facts, indent=2) + '\n')
    print(json.dumps(dict(memory=facts['facts']['memory'], dt_described_ram_bytes=facts['facts']['dt_described_ram_bytes'],
                          overlaps=facts['facts']['overlapping_reservations'], cpu_count=len(facts['facts']['cpus']),
                          boot_header=boot['header'], dtbo_count=count), indent=2))
    print(out)


if __name__ == '__main__':
    main()
