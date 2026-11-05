#!/usr/bin/env python3
"""Actual C memory-contract preflight for disjoint native staging grants."""
import argparse
import ctypes as c
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path
from entry_probe import ROOT, sha
from inspect_device import fdt_summary
from check_memory_plan import Range, Allocation

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--fdt', type=Path, required=True)
    a = p.parse_args(); build = a.build.resolve(); br = json.loads((build / 'report.json').read_text())
    assert br['passed'] and br['sparse_arena'] and not br['native_handoff']
    parent = ROOT / 'artifacts/native-staging-plan'; parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'), dir=parent))
    source = ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelMemoryContractLib/RaphaelMemoryContractLib.c'
    command = ['gcc', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror', '-fshort-wchar',
        '-I' + str(ROOT / 'sources/mu_basecore/MdePkg/Include'),
        '-I' + str(ROOT / 'sources/mu_basecore/MdePkg/Include/X64'),
        '-I' + str(ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg/Include'), str(source), '-o', str(out / 'contract.so')]
    result = subprocess.run(command, capture_output=True)
    (out / 'build.log').write_bytes(result.stdout + result.stderr); assert result.returncode == 0
    fn = c.CDLL(str(out / 'contract.so')).RaphaelCheckMemoryPlan
    fn.argtypes = [c.c_uint64, Range, c.POINTER(Allocation), c.c_uint64, c.POINTER(Range), c.c_uint64, c.POINTER(Range), c.c_uint64, c.POINTER(c.c_uint64)]
    fn.restype = c.c_uint32
    obs = fdt_summary(a.fdt.read_bytes()); memory = [(x['base'], x['size']) for x in obs['memory']]
    geometry = json.loads((ROOT / br['geometry_evidence']).read_text()); entry = geometry['entry']
    guards = [(x['base'], x['size']) for x in obs['fixed_reservations'] + obs['header_reservations']]
    l = br['layout']; base = l['ImageBase']; arena = l['ArenaBase']; end = l['ExtentEnd']
    download = l['StackBase'] + l['StackSize']
    first = geometry['initrd_geometry'][1]
    guards += [(base, l['ImageSize']), (entry['x0_fdt'], 2 * 1048576),
        (entry['sp'] & ~4095, 4096), (entry['lr'] & ~4095, 4096),
        (first, len((build / 'expanded-ramdisk.bin').read_bytes()))]
    cases = []
    def check(name, expected, outer, allocations, protected):
        aa = (Allocation * len(allocations))(*[Allocation(Range(*x), 4096) for x in allocations])
        rr = (Range * len(memory))(*[Range(*x) for x in memory])
        gg = (Range * len(protected))(*[Range(*x) for x in protected]); rejected = c.c_uint64()
        actual = fn(outer[0], Range(*outer), aa, len(aa), rr, len(rr), gg, len(gg), c.byref(rejected))
        cases.append(dict(name=name, expected=expected, actual=actual, passed=actual == expected))
    low = [(l['ExtentBase'], l['FdBase'] - l['ExtentBase']), (l['FdBase'], l['FdSize']), (l['StackBase'], l['StackSize'])]
    high = [(arena, l['ArenaSize']), (l['FdtBase'], l['FdtSize'])]
    check('actual downloaded allocations', 0, (base, download-base), low, guards)
    check('separate audited arena and FDT', 0, (arena, end-arena), high, guards)
    w = br['kernel_window']; wg = guards + [(x['base'], x['bytes']) for x in w['guards']]
    check('kernel window with distinct low and high grants', 0, (w['base'], w['bytes']), [(w['base'], w['bytes'])], wg + [(base, download-base), (arena, end-arena)])
    check('old broad footprint wrongly excludes window', 7, (w['base'], w['bytes']), [(w['base'], w['bytes'])], wg + [(base, end-base)])
    rejected = first + len((build / 'expanded-ramdisk.bin').read_bytes())
    rejected = ((rejected + 1048576 + 2097151) // 2097152) * 2097152
    check('old initrd-derived arena overlaps actual reserved memory', 7, (rejected, l['ArenaSize']), [(rejected, l['ArenaSize'])], guards)
    report = dict(passed=all(x['passed'] for x in cases), cases=cases, build=str(build.relative_to(ROOT)), build_report_sha256=sha((build / 'report.json').read_bytes()), fdt=str(a.fdt.resolve().relative_to(ROOT)), fdt_sha256=sha(a.fdt.read_bytes()), geometry_report_sha256=sha((ROOT / br['geometry_evidence']).read_bytes()), actual_c_source_sha256=sha(source.read_bytes()), arena_selection=br['arena_selection'], handset_executed=False, limits=['Host preflight uses the observed geometry snapshot; actual next-boot FDT/SP/LR checks remain mandatory'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(out); print(json.dumps(dict(passed=report['passed'], checks=len(cases)), indent=2)); assert report['passed'], cases

if __name__ == '__main__':
    main()
