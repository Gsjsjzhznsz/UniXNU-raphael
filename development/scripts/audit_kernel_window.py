#!/usr/bin/env python3
"""Compare sourced RAM descriptions without enabling a firmware allocator."""
import argparse
import datetime as dt
import json
import re
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from entry_probe import ROOT, sha
from inspect_device import fdt_summary, read_fdt, number

MAX_U64 = (1 << 64)-1


@dataclass(frozen=True, order=True)
class Span:
    base: int
    end: int

    def __post_init__(self):
        # Match the existing C memory contract: a representable exclusive end.
        assert 0 <= self.base < self.end <= MAX_U64


def merge(spans):
    result = []
    for span in sorted(spans):
        if result and span.base <= result[-1].end:
            result[-1] = Span(result[-1].base, max(result[-1].end, span.end))
        else:
            result.append(span)
    return result


def intersection(left, right):
    return merge([Span(max(a.base,b.base), min(a.end,b.end))
                  for a in left for b in right if max(a.base,b.base) < min(a.end,b.end)])


def subtract(spans, guards):
    result = merge(spans)
    for guard in merge(guards):
        parts = []
        for span in result:
            if guard.end <= span.base or guard.base >= span.end:
                parts.append(span)
                continue
            if span.base < guard.base:
                parts.append(Span(span.base, guard.base))
            if guard.end < span.end:
                parts.append(Span(guard.end, span.end))
        result = parts
    return result


def candidate(span, size, alignment, offset=0):
    assert 0 < size <= MAX_U64
    assert alignment > 0 and alignment & (alignment-1) == 0
    assert 0 <= offset < alignment
    base = ((span.base+alignment-1)//alignment)*alignment+offset
    if base > MAX_U64-size or base+size > span.end:
        return None
    return Span(base, base+size)


def memblock(text):
    result = []
    for line in text.splitlines():
        match = re.fullmatch(r'\s*([0-9]+): 0x([0-9a-fA-F]+)\.\.0x([0-9a-fA-F]+)\s*', line)
        assert match, 'Unrecognized memblock line'
        assert int(match[1]) == len(result), 'Unexpected memblock order'
        result.append(Span(int(match[2],16), int(match[3],16)+1))
    assert result
    return result


def iomem(text):
    result = []
    for line in text.splitlines():
        match = re.fullmatch(r'( *)([0-9a-fA-F]+)-([0-9a-fA-F]+) : (.+)', line)
        assert match, 'Unrecognized iomem line'
        result.append((Span(int(match[2],16), int(match[3],16)+1), match[4], len(match[1])))
    assert result
    return result


def describe(span):
    return dict(base=span.base, end_exclusive=span.end, bytes=span.end-span.base,
                base_hex=hex(span.base), end_exclusive_hex=hex(span.end))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', required=True, type=Path)
    args = parser.parse_args()
    collection = args.collection.resolve()
    assert collection.is_relative_to(ROOT/'evidence/private/memory-ownership')
    assert (collection/'COMPLETE').is_file()
    record = json.loads((collection/'report.json').read_text())
    assert all(record[k] for k in ['read_only','root_verified','android_boot_completed',
                                   'boot_partition_unchanged','transient_probe_absent'])
    assert record['collector_sha256'] == sha((ROOT/'scripts/collect_memory_ownership.py').read_bytes())
    for item in record['files']:
        path=collection/item['file']; assert path.parent == collection
        assert sha(path.read_bytes()) == item['sha256']
    blob=(collection/'live.dtb').read_bytes(); observed=fdt_summary(blob)
    fdt_ram=[Span(x['base'],x['end_exclusive']) for x in observed['memory']]
    memory=memblock((collection/'memblock-memory.txt').read_text())
    reserved=memblock((collection/'memblock-reserved.txt').read_text())
    resources=iomem((collection/'iomem.txt').read_text())
    system=[s for s,name,indent in resources if name=='System RAM']
    assert system and merge(system)==merge(memory), 'Linux memory views differ'
    available=intersection(intersection(fdt_ram,memory),system)
    guards=[]
    def guard(span, source, kind):
        guards.append(dict(**describe(span),source=source,kind=kind))
    for x in observed['fixed_reservations']+observed['header_reservations']:
        guard(Span(x['base'],x['end_exclusive']),x['source'],'FDT declaration')
    for n,span in enumerate(reserved):
        guard(span,f'memblock/reserved entry {n}','Linux runtime reservation')
    for span,name,indent in resources:
        if name!='System RAM' and intersection([span],fdt_ram):
            guard(span,'/proc/iomem: '+name,'Linux runtime resource')
    vendor_path=ROOT/'UniXNU-raphael/evidence/vendor-declared-layout.json'
    vendor=json.loads(vendor_path.read_text())
    for x in vendor['entries']:
        if x['section']=='MemoryMap':
            guard(Span(x['base'],x['base']+x['size']),
                  f"XBL uefiplat.cfg line {x['source_line']}: {x['label']}",
                  'Vendor declaration; lifetime unknown')
    plan_path=ROOT/'UniXNU-raphael/evidence/memory-plan-check.json'
    plan=json.loads(plan_path.read_text()); assert plan['passed'] and not plan['boot_enabled']
    for x in plan['regions']:
        guard(Span(x['base'],x['base']+x['length']), 'diagnostic plan: '+x['name'], 'Preserved diagnostic layout')
    tree=read_fdt(blob);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
    initrd_start=number(chosen.cells('linux,initrd-start'));initrd_end=number(chosen.cells('linux,initrd-end'))
    guard(Span(initrd_start,initrd_end),'/chosen:linux,initrd-start/end','Original Android continuation')
    guard_spans=[Span(x['base'],x['end_exclusive']) for x in guards]
    runs=subtract(available,guard_spans)
    driver=ROOT/'sources/UniXNU/drivers/DarwinBoot'
    rev=subprocess.check_output(['git','-C',str(driver),'rev-parse','HEAD'],text=True).strip()
    assert rev=='3325e352d7df68a9f9ad74832ed94a6acbbd7390'
    primary=[]
    for repo,revision,name,markers in [
        (driver,rev,'DarwinBootPkg/Driver/WindowSize.h',['0x10000000ULL','0x200000000ULL','0x1fffffULL']),
        (driver,rev,'DarwinBootPkg/Driver/DarwinBoot.c',['#define WINDOW_SIZE  SIZE_256MB','#define BLOCK_SIZE   SIZE_2MB','AllocateWindow (','Kernel->Base & (BLOCK_SIZE - 1)']),
        (ROOT/'sources/Xiaomi_Kernel_OpenSource','663db50e195a8a54c8565ac4ab0c6d9ba7d80db0','Documentation/arm64/booting.txt',['Any memory described to the kernel','will be considered as available to','Quiesce all DMA capable devices'])]:
        raw=(repo/name).read_bytes()
        assert raw==subprocess.check_output(['git','-C',str(repo),'show',revision+':'+name])
        text=raw.decode()
        for marker in markers:assert marker in text,marker
        primary.append(dict(repository=str(repo.relative_to(ROOT)),revision=revision,path=name,sha256=sha(raw),
                            lines={m:text[:text.index(m)].count('\n')+1 for m in markers}))
    minimum=0x10000000;alignment=0x200000
    possibilities=[]
    for span in runs:
        window=candidate(span,minimum,alignment)
        worst=candidate(span,minimum,alignment,alignment-1)
        if window:
            assert all(not intersection([window],[g]) for g in guard_spans)
            possibilities.append(dict(run=describe(span),aligned_example=describe(window),
                                      every_kernel_offset_fits=worst is not None,
                                      actual_kernel_physical_base_selected=False))
    root=ROOT/'artifacts/kernel-window-audit';root.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=root))
    result=dict(passed=True,kind='Read-only structural candidates; allocator remains disabled',
                collection=str(collection.relative_to(ROOT)),collection_report_sha256=sha((collection/'report.json').read_bytes()),
                source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in
                               [Path(__file__),ROOT/'scripts/collect_memory_ownership.py',vendor_path,plan_path]],
                primary_sources=primary,dt_described_ram_bytes=sum(s.end-s.base for s in fdt_ram),
                linux_memory_bytes=sum(s.end-s.base for s in merge(memory)),
                memory_views_agree=True,available_description= [describe(s) for s in available],
                excluded_ranges=guards,structural_unreserved_runs=[describe(s) for s in runs],
                darwin_minimum_window_bytes=minimum,darwin_alignment_bytes=alignment,
                actual_macho_kernel_offset_known=False,candidates=possibilities,
                cpu_mmfr0_available=(collection/'cpu-mmfr0.txt').read_text().strip()!='unavailable',
                firmware_efi_map_available=(collection/'firmware-memmap.txt').read_text().strip()!='unavailable',
                address_bits_required_by_fdt=(max(s.end for s in fdt_ram)-1).bit_length(),
                current_diagnostic_arena_bytes=next(x['length'] for x in plan['regions'] if 'DXE arena' in x['name']),
                dynamic_fdt_pool_declarations=observed['dynamic_pools'],
                boot_enabled=False,new_uefi_memory_registered=False,ram_written=False,
                hardware_window_access_verified=False,full_ownership_proven=False,
                limitations=['Linux memblock is sampled after Linux allocations, not at ABL handoff',
                             'Vendor config may be overridden; it does not cover every runtime allocation',
                             'Dynamic pool declarations and DMA lifetimes need separate entry analysis',
                             'An interval fitting the descriptions is not a proof of RAM access or ownership',
                             'Candidate addresses are derived here; no other board configuration is used'])
    assert result['current_diagnostic_arena_bytes']<minimum
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(out)
    print('Structural candidates:',len(possibilities))
    for item in possibilities:
        print(item['aligned_example']['base_hex'],item['aligned_example']['end_exclusive_hex'],
              'all kernel offsets fit:',item['every_kernel_offset_fits'])


if __name__ == '__main__':
    main()
