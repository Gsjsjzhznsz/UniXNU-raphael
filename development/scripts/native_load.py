#!/usr/bin/env python3
"""Independent expected loaded-memory contract; no patched kernel or loader."""
import struct
import zlib
from entry_probe import align, sha
MAGIC = int.from_bytes(b'RPHLOAD1', 'little')
FIELDS = 'version status physical_base args tree entry window_bytes segment_count file_segments_ok zero_segments_ok tree_crc args_ok exit_notice_count frequency affinity error'.split()

def make_policy(kernel, adt, window, frequency, affinity, exit_complete=False, trust_cache=None, ramdisk=None):
    assert struct.unpack_from('<3I', kernel) == (0xfeedfacf, 0x100000c, 0)
    count, size = struct.unpack_from('<2I', kernel, 16)
    at = 32; segments = []; entry = None
    for _ in range(count):
        command, length = struct.unpack_from('<2I', kernel, at)
        assert length >= 8 and at + length <= 32 + size
        if command == 0x19:
            va, memory, offset, data = struct.unpack_from('<4Q', kernel, at + 24)
            protection = struct.unpack_from('<I', kernel, at + 60)[0]
            if memory:
                assert data <= memory and offset + data <= len(kernel)
                segments.append(dict(virtual_address=va, bytes=memory, file_bytes=data,
                    crc32=zlib.crc32(kernel[offset:offset+data]), protection=protection))
        if command == 5:
            assert length == 288 and entry is None
            entry = struct.unpack_from('<Q', kernel, at + 272)[0]
        at += length
    assert at == 32 + size and entry is not None and 0 < len(segments) <= 64
    base = min(s['virtual_address'] for s in segments)
    end = max(s['virtual_address'] + s['bytes'] for s in segments)
    owned = window.get('window_bytes', 256*1048576)
    assert owned in (256*1048576,512*1048576,704*1048576)
    from validate_handset_adt import parse
    tree,parsed_bytes=parse(adt);assert parsed_bytes==len(adt)
    declared=tree['nodes']['chosen']['props'].get('darwinboot-memory-size',struct.pack('<Q',256*1048576))
    assert declared==struct.pack('<Q',owned), 'Loader ADT and exact memory grant must agree'
    assert base == window['virtual_base'] and end - base < 256 * 1048576 - 2 * 1048576
    candidate = window['base'] + (base & (2*1048576-1))
    assert candidate>>30==(candidate+owned-1)>>30, 'Exact recovery mapping supports one L1 span; include kernel alignment offset'
    assert candidate + owned <= window['base'] + window['bytes'] - 0x40000
    assert any(s['protection'] & 4 and s['virtual_address'] <= entry < s['virtual_address'] + s['file_bytes'] for s in segments)
    args = align(end - base, 16384)
    source_adt=adt; trust=None; packed=None
    if ramdisk is not None:
        assert trust_cache is not None, 'Packed Data requires original TrustCache contract'
        from native_ramdisk import validate_packed
        packed=validate_packed(ramdisk)
    if trust_cache is not None:
        from native_trust import bind_adt
        adt,trust=bind_adt(adt,candidate+args+4096,trust_cache,len(ramdisk) if ramdisk is not None else 0)
        assert trust['physical']+trust['bytes']<=candidate+owned-2*1048576
    if packed:
        from native_ramdisk import bind_adt as bind_packed
        adt,packed=bind_packed(adt,candidate+args+4096,ramdisk)
        assert packed['physical']+align(packed['bytes'],4096)==trust['physical']
    words = [MAGIC, 3 if packed else 2 if trust else 1, len(segments), base, end, entry, args, len(adt), zlib.crc32(adt),
             candidate, owned, frequency, affinity]
    rows = [struct.pack('<5Q', s['virtual_address'] - base, s['bytes'], s['file_bytes'], s['crc32'], s['protection']) for s in segments]
    raw = struct.pack('<13Q', *words) + b''.join(rows)
    if trust:raw+=struct.pack('<4Q',trust['physical']-candidate,trust['bytes'],trust['crc32'],trust['adt_offset'])
    if packed:raw+=struct.pack('<4Q',packed['physical']-candidate,packed['bytes'],packed['crc32'],packed['adt_offset'])
    return raw, dict(**({'ramdisk':packed} if packed else {}),**({'trust_cache':trust} if trust else {}),policy_sha256=sha(raw), kernel_sha256=sha(kernel), adt_sha256=sha(source_adt),
        adt_crc32=zlib.crc32(adt), adt_bytes=len(adt), physical_base=candidate,
        args=candidate+args, tree=candidate+args+4096, entry=candidate+entry-base,
        window_bytes=owned, segments=segments, frequency=frequency, affinity=affinity,
        exit_boot_services_completion_expected=exit_complete, xnu_execution_expected=False)

def decode(raw, contract):
    assert len(raw) == 16 * 8
    d = dict(zip(FIELDS, struct.unpack('>16Q', raw)))
    complete=contract['exit_boot_services_completion_expected']
    assert d['version'] == (2 if complete else 1) and d['status'] == (4 if complete else 3) and not d['error']
    assert d['exit_notice_count'] == 1 and d['args_ok'] == 1
    assert d['segment_count'] == d['file_segments_ok'] == d['zero_segments_ok'] == len(contract['segments'])
    for name in ['physical_base', 'args', 'tree', 'entry', 'window_bytes', 'frequency', 'affinity']:
        assert d[name] == contract[name], name
    assert d['tree_crc'] == contract['adt_crc32']
    return dict(**d, **({'original_trust_sidecar_loaded_verified':True} if contract.get('trust_cache') else {}), **({'packed_data_sidecar_loaded_verified':True} if contract.get('ramdisk') else {}), original_loader_loaded_memory_verified=True,
        before_exit_boot_services_notification_reached=not complete, exit_boot_services_completed=complete,
        xnu_executed=False)
