#!/usr/bin/env python3
"""Exercise the actual C memory contract using handset evidence and bad plans.

This emits a design report only; it never emits boot-enabled addresses/PCDs.
"""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import subprocess
import tomllib
from entry_probe import ROOT, align, sha
from inspect_device import fdt_summary, read_fdt


class Range(c.Structure):
    _fields_ = [('base', c.c_uint64), ('length', c.c_uint64)]


class Allocation(c.Structure):
    _fields_ = [('span', Range), ('alignment', c.c_uint64)]


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'artifacts/memory-contract' / stamp
    out.mkdir(parents=True, exist_ok=False)
    evidence_path = ROOT / 'UniXNU-raphael/evidence/entry-handoff.json'
    handoff = json.loads(evidence_path.read_text())
    assert handoff['nonce_matched'] and handoff['boot_partition_unchanged']
    entry = handoff['entry']
    run = ROOT / handoff['private_readback']
    blob = (run / 'after.dtb').read_bytes()
    assert sha(blob) == handoff['fdt_sha256']
    observed = fdt_summary(blob)
    tree = read_fdt(blob)
    chosen = next(node for node in tree.walk() if node.name == 'chosen' and node.parent is tree)
    cells = chosen.cells('linux,initrd-start')
    initrd_start = sum(value << (32 * (len(cells) - i - 1)) for i, value in enumerate(cells))
    cells = chosen.cells('linux,initrd-end')
    initrd_end = sum(value << (32 * (len(cells) - i - 1)) for i, value in enumerate(cells))
    design = tomllib.loads((ROOT / 'UniXNU-raphael/package/firmware/Resources/memory-plan.toml').read_text())
    assert not design['boot_enabled']
    geometry = design['geometry']
    base = entry['image_base']
    offset = align(entry['original_image_size'], 65536)
    regions = []
    for name, key, alignment in [('entry bridge', 'bridge_size', 65536),
                                 ('new FD capacity', 'fd_capacity', 65536),
                                 ('new SEC stack', 'sec_stack_size', 4096),
                                 ('new DXE arena including page tables', 'dxe_arena_size', 4096),
                                 ('new FDT copy capacity', 'fdt_copy_capacity', 4096)]:
        size = geometry[key]
        regions.append(dict(name=name, base=base + offset, length=size, alignment=alignment,
                            source='entry-handoff + original Image header + explicit design budget'))
        offset += size
    ram = [(x['base'], x['size']) for x in observed['memory']]
    protected = [(base, entry['original_image_size']), (entry['x0_fdt'], 2 * 1024 * 1024),
                 (initrd_start, initrd_end - initrd_start),
                 (entry['sp'] & ~4095, 4096), (entry['lr'] & ~4095, 4096)]
    protected += [(x['base'], x['size']) for x in observed['fixed_reservations']]
    # The only new reservation in the readback was inserted by this known probe.
    # It does not exist before instrumentation on the next fresh original-kernel boot.
    removed_probe_reservations = []
    for x in observed['header_reservations']:
        if (x['base'], x['size']) == (entry['probe_base'], entry['probe_extent']):
            removed_probe_reservations.append(x)
        else:
            protected.append((x['base'], x['size']))
    assert len(removed_probe_reservations) == 1
    vendor = json.loads((ROOT / 'UniXNU-raphael/evidence/vendor-declared-layout.json').read_text())
    kernel_window = next(x for x in vendor['entries'] if x['section'] == 'MemoryMap' and x['label'] == 'Kernel')
    assert base >= kernel_window['base'] and base + offset <= kernel_window['base'] + kernel_window['size']
    protected += [(x['base'], x['size']) for x in vendor['entries'] if x['section'] == 'MemoryMap' and x['label'] != 'Kernel']
    source = ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelMemoryContractLib/RaphaelMemoryContractLib.c'
    command = ['gcc', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror', '-fshort-wchar',
               '-I' + str(ROOT / 'sources/mu_basecore/MdePkg/Include'),
               '-I' + str(ROOT / 'sources/mu_basecore/MdePkg/Include/X64'),
               '-I' + str(ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),
               str(source), '-o', str(out / 'memory-contract.so')]
    result = subprocess.run(command, capture_output=True)
    (out / 'build.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    lib = c.CDLL(str(out / 'memory-contract.so'))
    function = lib.RaphaelCheckMemoryPlan
    function.argtypes = [c.c_uint64, Range, c.POINTER(Allocation), c.c_uint64,
                        c.POINTER(Range), c.c_uint64, c.POINTER(Range), c.c_uint64,
                        c.POINTER(c.c_uint64)]
    function.restype = c.c_uint32
    cases = []

    def check(name, expected, spans=regions, image_base=base, image_size=offset, memory=ram, guards=protected):
        allocations = (Allocation * len(spans))(*[Allocation(Range(x['base'], x['length']), x['alignment']) for x in spans])
        memory_array = (Range * len(memory))(*[Range(*x) for x in memory])
        guards_array = (Range * len(guards))(*[Range(*x) for x in guards])
        rejected = c.c_uint64()
        actual = function(base, Range(image_base, image_size), allocations, len(spans),
                          memory_array, len(memory), guards_array, len(guards), c.byref(rejected))
        cases.append(dict(name=name, expected=expected, actual=actual, passed=actual == expected,
                          rejected_index=rejected.value if rejected.value != (1 << 64) - 1 else None))

    check('candidate geometry within sourced guards', 0)
    check('entry base drift rejected', 2, image_base=base + 4096)
    check('loaded Image extent overflow rejected', 3, image_size=(1 << 64) - base + 1)
    changed = [dict(x) for x in regions]
    changed[0]['base'] += 1
    check('unaligned entry bridge rejected', 4, spans=changed)
    check('arena outside declared Image rejected', 5, image_size=entry['original_image_size'])
    check('RAM hole rejected', 6, memory=[(base, entry['original_image_size'])])
    check('source FDT collision rejected', 7, guards=[(regions[1]['base'], 4096)])
    changed = [dict(x) for x in regions]
    changed[2]['base'] = changed[1]['base']
    check('FD and SEC stack collision rejected', 8, spans=changed)
    changed = [dict(x) for x in regions]
    changed[1]['base'] = base
    check('fallback Android kernel protected', 7, spans=changed)
    report = dict(kind='design geometry and C validator tests only; not ownership proof',
                  passed=all(x['passed'] for x in cases), cases=cases, command=command,
                  source_sha256=sha(source.read_bytes()), evidence_sha256=sha(evidence_path.read_bytes()),
                  requested_image_base=base, requested_image_size=offset,
                  requested_image_end=base + offset, regions=regions,
                  original_fdt_guard_bytes=2 * 1024 * 1024,
                  fdt_guard_source='Qualcomm BootLinux.h DT_SIZE_2MB; interface reference, not exact source match',
                  original_initrd=dict(base=initrd_start, end=initrd_end),
                  excluded_known_probe_reservations=removed_probe_reservations,
                  boot_enabled=False, complete_uefi_platform_built=False, full_arena_handset_verified=False,
                  unresolved=['Runtime uefiplatLA.cfg override and full original firmware memory ownership',
                              'Expanded Image download accepted; zero-padded tail was not tested for writes/readback',
                              'C validator caller must supply complete live protected ranges at real entry'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    safe = {key: value for key, value in report.items() if key != 'command'}
    (ROOT / 'UniXNU-raphael/evidence/memory-plan-check.json').write_text(json.dumps(safe, indent=2) + '\n')
    print(json.dumps(safe, indent=2))
    print(out)
    assert report['passed']


if __name__ == '__main__':
    main()
