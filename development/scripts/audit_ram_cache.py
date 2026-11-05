#!/usr/bin/env python3
"""Audit the linked cache callback and both independently restored QEMU phases."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from entry_probe import ROOT, sha
from audit_ram_read import inspect_load
from audit_ram_write import inspect_write
from audit_ram_mapped import inspect_translation
from ram_cache_write import verify_storage


def linked_function(build, name):
    directory = build / 'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
    mapping = (directory / 'RaphaelSec.dll.map').read_text()
    dis = subprocess.check_output(['llvm-objdump', '-d', str(directory / 'RaphaelSec.efi')], text=True)
    instructions = [(int(m[1], 16), int(m[2], 16), m[3]) for m in re.finditer(
        r'(?m)^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$', dis)]
    match = re.search(r'(?m)^([0-9a-f]+)\s+([0-9a-f]+)\s+4\s+.*:\(\.text\)\n\1\s+00000000\s+0\s+'
                      + re.escape(name) + '$', mapping)
    assert match, name
    start, size = int(match[1], 16), int(match[2], 16)
    body = [i for i in instructions if start <= i[0] < start + size]
    assert len(body) * 4 == size
    return body, mapping, dis


# Exact linked AArch64 contributions produced by the pinned compiler. Local
# branch encodings are position independent; the sole BL is checked separately
# against the real checkpoint symbol. Include the failure blocks after RET.
_DIRECT_READ = (
    0xa9bd53f3, 0xf9000bf5, 0xa901fbfd, 0x910063fd, 0xf9404048,
    0xaa0003f4, 0xaa0103f5, 0xf9402109, 0xeb00013f, 0x54000201,
    0xf9402909, 0xb50001c9, 0xf9402508, 0xb5000188, 0xaa0203f3,
    0xf9404c48, 0xf9405442, 0xaa1403e0, 0x52820001, 0xd63f0100,
    0x72001c1f, 0x54000160, 0xf9403268, 0x91000508, 0xf9003268,
    0x52800020, 0xf9400288, 0xf90002a8, 0xa941fbfd, 0xf9400bf5,
    0xa8c353f3, 0xd65f03c0, 0x2a1f03e0, 0x17fffffb,
)
_DIRECT_WRITE = (
    0xa9be53f3, 0xa9017bfd, 0x910043fd, 0xf9404048, 0xf9000001,
    0xaa0203f3, 0xaa0003f4, 0xf9403508, 0xf104051f, 0x54000041,
    None, 0xf9404268, 0xf9402100, 0x913fe008, 0xeb14011f,
    0x54000141, 0xf9404e68, 0xf9405662, 0x52820001, 0xd63f0100,
    0x72001c1f, 0x54000100, 0xf9403668, 0x91000508, 0xf9003668,
    0x52800020, 0xa9417bfd, 0xa8c253f3, 0xd65f03c0, 0x2a1f03e0,
    0x17fffffc,
)


def verify_direct_body(body, write=False, checkpoint=None):
    expected = _DIRECT_WRITE if write else _DIRECT_READ
    assert len(body) == len(expected), 'complete native callback extent differs'
    for index, ((address, opcode, _), want) in enumerate(zip(body, expected)):
        assert address == body[0][0] + index * 4, 'non-contiguous native callback'
        if want is not None:
            assert opcode == want, ('native opcode differs', index, hex(opcode), hex(want))
        else:
            assert write and index == 10 and opcode & 0xfc000000 == 0x94000000
            displacement = opcode & 0x03ffffff
            if displacement & 0x02000000:
                displacement -= 0x04000000
            assert address + displacement * 4 == checkpoint, 'BL is not the restoration checkpoint'
    return True


def inspect_direct_access(build, write=False):
    name = 'WriteCacheRam64' if write else 'ReadCacheRam64'
    body, mapping, dis = linked_function(build, name)
    checkpoint = int(re.search(r'(?m)^([0-9a-f]+)\s+.*\sRaphaelRamWriteCheckpoint$', mapping)[1], 16)
    verify_direct_body(body, write, checkpoint)
    # Both shared helpers must be inlined, with no wrapper/raw word dispatch.
    assert not re.search(r'(?m)^.*\s(?:ReadCached|WriteCached)$', mapping)
    assert re.search(r'(?m)^\s*' + format(checkpoint, 'x') + r':\s+d503201f\s', dis)
    access = body[4 if write else 26]
    result = dict(function_rva=body[0][0], instruction_count=len(body),
                  direct_cache_phase_revision=3, complete_failure_block_checked=True,
                  exact_opcodes_checked=True, no_second_word_callback=True,
                  phase_sync_only_indirect_call=True, cache_context_offset=0xa8,
                  cache_engine_offset=0x80, cache_sync_offset=0x98)
    if write:
        result.update(store_rva=access[0], store_opcode=access[1],
                      single_64bit_store_only=True, no_load_from_candidate=True,
                      barriers=['DSB SY and PoC maintenance at page phase boundary'],
                      checkpoint_write_attempt=257, checkpoint_is_nop=True,
                      post_sync_on_last_word=True, post_sync_counter_offset=0x68)
    else:
        result.update(load_rva=access[0], load_opcode=access[1],
                      single_64bit_load_only=True, no_store_through_candidate=True,
                      pre_sync_before_first_backup_word=True, pre_sync_counter_offset=0x60)
    return result


def inspect_cached_write(build):
    body, mapping, dis = linked_function(build, 'WriteCacheRam64')
    barrier = int(re.search(r'(?m)^([0-9a-f]+)\s+.*\sArmDataSynchronizationBarrier$', mapping)[1], 16)
    calls = [i for i in body if i[2].startswith('bl\t')]
    if any(int(re.search(r'0x([0-9a-f]+)', i[2])[1], 16) == barrier for i in calls):
        # Historical reports keep exactly the original strict schema/audit.
        return inspect_write(build, function='WriteCacheRam64')
    if len(body) == len(_DIRECT_WRITE):
        return inspect_direct_access(build, write=True)
    checkpoint = int(re.search(r'(?m)^([0-9a-f]+)\s+.*\sRaphaelRamWriteCheckpoint$', mapping)[1], 16)
    assert len(calls) == 1 and int(re.search(r'0x([0-9a-f]+)', calls[0][2])[1], 16) == checkpoint
    stores = [i for i in body if i[2] == 'str\tx1, [x0]']
    assert len(stores) == 1 and stores[0][0] < calls[0][0]
    memory = [i for i in body if re.match(r'(?:ld|st)', i[2])]
    assert all('[sp' in i[2] or i[2] in ['str\tx1, [x0]', 'ldr\tx8, [x2, #0x68]'] for i in memory)
    assert any(i[2] == 'cmp\tx8, #0x101' for i in body)
    assert not any(re.match(r'(?:dsb|dmb|dc)\b', i[2]) for i in body)
    assert re.search(r'(?m)^\s*' + format(checkpoint, 'x') + r':\s+d503201f\s', dis)
    return dict(function_rva=body[0][0], store_rva=stores[0][0], store_opcode=stores[0][1],
                single_64bit_store_only=True, no_load_from_candidate=True,
                barriers=['DSB SY and PoC maintenance at page phase boundary'],
                checkpoint_write_attempt=257, checkpoint_is_nop=True,
                instruction_count=len(body), boundary_completion_revision=2)


def inspect_cached_read(build):
    body, _, _ = linked_function(build, 'ReadCacheRam64')
    if len(body) != 4:
        return inspect_direct_access(build)
    assert [i[2].split('//', 1)[0].strip() for i in body] == [
        'ldr\tx8, [x0]', 'mov\tw0, #0x1', 'str\tx8, [x1]', 'ret']
    return dict(function_rva=body[0][0], load_rva=body[0][0], load_opcode=body[0][1],
                single_64bit_load_only=True, no_store_through_candidate=True,
                instruction_count=len(body), boundary_completion_revision=2)


def inspect_cache(build):
    directory = build / 'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
    mapping = (directory / 'RaphaelSec.dll.map').read_text()
    disassembly = subprocess.check_output(['llvm-objdump', '-d', str(directory / 'RaphaelSec.efi')], text=True)
    instructions = [(int(m[1], 16), int(m[2], 16), m[3]) for m in re.finditer(
        r'(?m)^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$', disassembly)]

    def symbol(name):
        match = re.search(r'(?m)^([0-9a-f]+)\s+.*\s' + re.escape(name) + '$', mapping)
        assert match, name
        return int(match[1], 16)

    def body(name):
        # Use the linked contribution's complete extent. Stopping at the first
        # RET would miss SyncCachePage's success block after its early return.
        match = re.search(r'(?m)^([0-9a-f]+)\s+([0-9a-f]+)\s+4\s+.*:\(\.text\)\n\1\s+00000000\s+0\s+'
                          + re.escape(name) + '$', mapping)
        assert match, name
        start, size = int(match[1], 16), int(match[2], 16)
        assert start == symbol(name)
        result = [i for i in instructions if start <= i[0] < start + size]
        assert len(result) * 4 == size
        return result

    def target(i):
        match = re.match(r'(?:bl|b)\t0x([0-9a-f]+)', i[2])
        return int(match[1], 16) if match else None

    sync = body('SyncCachePage')
    text = '\n'.join(i[2] for i in sync)
    assert 'tst\tx0, #0xfff' in text and '#0x1000' in text
    assert 'b.hi\t' in text and 'b.hs\t' in text
    calls = [target(i) for i in sync if i[2].startswith('bl\t')]
    legacy_calls = [symbol('ArmDataCacheLineLength'), symbol('CacheRangeOperation'), symbol('ArmDataSynchronizationBarrier')]
    boundary = calls == [symbol('ArmDataSynchronizationBarrier')] + legacy_calls
    assert boundary or calls == legacy_calls
    # LTO inlines WriteBackInvalidateDataCacheRange. Verify the actual function
    # pointer passed as x2 to the surviving line walker, including its page ADD.
    pointer = None
    for i in sync:
        m = re.match(r'adrp\tx2, 0x([0-9a-f]+)', i[2])
        if m:
            pointer = int(m[1], 16)
        m = re.match(r'add\tx2, x2, #0x([0-9a-f]+)', i[2])
        if m and pointer is not None:
            pointer += int(m[1], 16)
    assert pointer == symbol('ArmCleanInvalidateDataCacheEntryByMVA')
    walker = body('CacheRangeOperation')
    walk_text = '\n'.join(i[2] for i in walker)
    assert all(s in walk_text for s in ['neg\tx8, x3', 'and\tx21, x8, x0', 'add\tx22, x0, x1',
                                      'mov\tx20, x2', 'mov\tx0, x21', 'blr\tx20', 'add\tx21, x21, x19'])
    assert target(walker[-1]) == symbol('ArmDataSynchronizationBarrier')
    op = next(i for i in instructions if i[0] == pointer)
    barrier = next(i for i in instructions if i[0] == symbol('ArmDataSynchronizationBarrier'))
    assert op[1] == 0xd50b7e20 and op[2] == 'dc\tcivac, x0'
    assert barrier[1] == 0xd5033f9f and barrier[2] == 'dsb\tsy'
    mmu = symbol('ArmSetMemoryAttributes')
    updates = [index for index, i in enumerate(instructions) if i[2].startswith('bl\t') and target(i) == mmu]
    assert len(updates) == 2
    snippets = ['\n'.join(i[2] for i in instructions[max(0, index - 8):index]) for index in updates]
    assert sum('mov\tx2, xzr' in s for s in snippets) == 1
    assert sum('mov\tw2, #0x20000' in s for s in snippets) == 1
    restoration = body('RaphaelRestoreRamCacheMap')
    assert any(target(i) == mmu for i in restoration)
    assert any(target(i) == symbol('TranslateMappedRam') for i in restoration)
    result = dict(sync_rva=symbol('SyncCachePage'), sync_bytes=len(sync)*4,
                linked_range_walker_rva=symbol('CacheRangeOperation'), cache_line_operation_rva=pointer,
                dc_civac_opcode=op[1], dsb_sy_opcode=barrier[1], cache_line_length_from_cpu=True,
                full_page_bounds_checked=True, permissions_only_update_and_restore_calls=2,
                restore_queries_translation=True, no_other_board_parameters=True)
    if boundary:
        result.update(boundary_completion_revision=2, dsb_sy_before_maintenance=True,
                      dsb_sy_after_maintenance=True, cached_load=inspect_cached_read(build))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage2', required=True, type=Path)
    parser.add_argument('--stage3', required=True, type=Path)
    args = parser.parse_args()
    reports = {}
    inputs = upstream = pages = None
    for stage, path in [(2, args.stage2.resolve()), (3, args.stage3.resolve())]:
        q = json.loads(path.read_text())
        assert q['qemu_passed'] and q['structure_checked'] and q['ram_mapped_probe'] and q['stop_stage'] == stage
        assert q['ram_cache_write_pages'] in [1, 8, 256, 4096, 16384, 65536] and not q['ram_write_pages']
        if pages is not None:
            assert pages == q['ram_cache_write_pages'] and inputs == q['source_inputs'] and upstream == q['upstream_inputs']
        pages, inputs, upstream = q['ram_cache_write_pages'], q['source_inputs'], q['upstream_inputs']
        for item in inputs + upstream:
            assert sha((ROOT / item['path']).read_bytes()) == item['sha256'], item['path']
        assert q['ram_cache_decoder_sha256'] == sha((ROOT / 'scripts/ram_cache_write.py').read_bytes())
        assert q['ram_mapped_decoder_sha256'] == sha((ROOT / 'scripts/ram_mapped_probe.py').read_bytes())
        normal = q['executions']['normal']
        assert normal['passed'] and normal['ram_mapped']['passed'] and normal['ram_cache']['passed']
        if stage == 2:
            assert not normal['ram_cache']['ram_written'] and normal['ram_cache']['status'] == 1
        else:
            assert normal['ram_cache']['write']['completed_pages'] == pages
            assert normal['ram_cache']['write']['restored_pages'] == pages
            fault = q['executions']['partial_write_udf']
            assert fault['passed'] and not fault['real_data_abort'] and fault['patched_opcode'] == 0
            assert fault['ram_cache']['passed'] and fault['ram_cache']['map_restored'] == 1
            assert fault['ram_cache']['write']['restored_pages'] == 1 and not fault['ram_cache']['write']['dirty']
            assert all('PASS independent MMU-off receiver verifies every restored DRAM word' in case['checks']
                       for case in [normal, fault])
            before_store = q['executions']['load_site_udf']
            assert before_store['passed'] and not before_store['real_data_abort']
            assert 'PASS mapped-load failure precedes all cached stores' in before_store['checks']
        reports[str(stage)] = dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))
    primary = []
    repository = ROOT / 'sources/mu_basecore'
    revision = 'cfb93724a06ff86ff5ba971413368a7809ee42a5'
    for name in ['UefiCpuPkg/Include/Library/ArmMmuLib.h',
                 'UefiCpuPkg/Library/ArmMmuLib/AArch64/ArmMmuLibCore.c',
                 'MdePkg/Include/AArch64/AArch64Mmu.h', 'MdePkg/Include/Library/CacheMaintenanceLib.h',
                 'ArmPkg/Library/ArmCacheMaintenanceLib/ArmCacheMaintenanceLib.c',
                 'MdePkg/Library/ArmLib/AArch64/AArch64Support.S']:
        data = (repository / name).read_bytes()
        assert data == subprocess.check_output(['git', '-C', str(repository), 'show', revision + ':' + name])
        primary.append(dict(repository='sources/mu_basecore', revision=revision, path=name, sha256=sha(data)))
    if inspect_cache(args.stage3.resolve().parent).get('boundary_completion_revision') == 2:
        revision = '663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
        for name in ['Documentation/memory-barriers.txt', 'arch/arm64/mm/cache.S', 'arch/arm64/include/asm/assembler.h']:
            data = subprocess.check_output(['git', '-C', str(ROOT / 'sources/Xiaomi_Kernel_OpenSource'),
                                            'show', revision + ':' + name])
            primary.append(dict(repository='sources/Xiaomi_Kernel_OpenSource', revision=revision,
                                path=name, sha256=sha(data), role='same-PE overlap ordering and range PoC maintenance reference'))
    source_names = ['Sec/RamRead.c', 'Sec/RamReadAdapter.c', 'Sec/RamMapped.c', 'Sec/RamMappedAdapter.c',
                    'Sec/RamCacheAdapter.c', 'Sec/Sec.c', 'Sec/SecEntry.S', 'Sec/RamWriteCheckpoint.S',
                    'Include/RaphaelRamRead.h', 'Include/RaphaelRamMapped.h',
                    'Include/Library/RaphaelRamWriteLib.h', 'Include/Library/RaphaelRamCacheLib.h',
                    'Library/RaphaelRamWriteLib/RamWrite.c', 'Library/RaphaelRamWriteLib/RamCache.c']
    source = ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg'
    result = dict(passed=True, ram_cache_write_pages=pages, qemu_reports=reports,
                  source_inputs=[dict(path=str((source / n).relative_to(ROOT)), sha256=sha((source / n).read_bytes())) for n in source_names],
                  primary_sources=primary, mapped_load=inspect_load(args.stage3.resolve().parent, function='ReadMappedRam64'),
                  store=inspect_cached_write(args.stage3.resolve().parent),
                  cache_instructions=inspect_cache(args.stage3.resolve().parent),
                  translation=inspect_translation(args.stage3.resolve().parent), storage=verify_storage(args.stage3.resolve().parent),
                  decoder_sha256=sha((ROOT / 'scripts/ram_mapped_probe.py').read_bytes()),
                  cache_decoder_sha256=sha((ROOT / 'scripts/ram_cache_write.py').read_bytes()),
                  runner_sha256=sha(Path(__file__).read_bytes()), fatal_mapped_load_udf_return_verified=True,
                  partial_cached_write_udf_recovery_verified=True, real_data_abort_verified=False,
                  handset_executed=False, allocator_enabled=False, ownership_proven=False)
    target = ROOT / ('UniXNU-raphael/evidence/ram-cache-source-audit-pages' + str(pages) + '.json')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(target)
    print(json.dumps(result['cache_instructions'], indent=2))


if __name__ == '__main__':
    main()
