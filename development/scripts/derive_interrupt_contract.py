#!/usr/bin/env python3
"""Resolve fresh handset interrupt resources without reading or writing MMIO.

This is a source/data contract, never permission to enable CPU/GIC/timer drivers.
The only supported intermediary is the pinned SM8150 PDC translation to GICv3.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import struct
import subprocess

from inspect_device import ROOT, read_fdt, registers, physical, node_path, number, sha, Error

KERNEL_REVISION = '663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
ROLES = ['secure_physical', 'nonsecure_physical', 'virtual', 'hypervisor']


def require(good, message):
    if not good:
        raise ValueError(message)


def analyze_tree(root):
    nodes = list(root.walk())
    handles = {}
    for node in nodes:
        values = []
        for key in ['phandle', 'linux,phandle']:
            if key in node.properties:
                require(len(node.cells(key)) == 1, 'Malformed phandle')
                values.append(node.cells(key)[0])
        if values:
            require(all(value == values[0] for value in values), 'Conflicting phandle aliases')
            value = values[0]
            require(0 < value < 0xffffffff and value not in handles, 'Invalid or duplicate phandle')
            handles[value] = node

    def parent(node):
        current = node
        while current is not None:
            if 'interrupt-parent' in current.properties:
                values = current.cells('interrupt-parent')
                require(len(values) == 1 and values[0] in handles, 'Unresolved interrupt parent')
                return handles[values[0]], node_path(current) + ':interrupt-parent'
            current = current.parent
        raise ValueError('Missing interrupt parent')

    timers = [node for node in nodes if b'arm,armv8-timer' in node.properties.get('compatible',b'').split(b'\0') and node.enabled()]
    for node in timers:node.strings('compatible')
    require(len(timers) == 1, 'Need exactly one enabled architectural timer')
    timer = timers[0]
    require('interrupts-extended' not in timer.properties, 'Extended timer interrupts not reviewed')
    specs = timer.cells('interrupts')
    require(len(specs) == 12, 'Expected four three-cell timer interrupts')
    frequency = timer.cells('clock-frequency')
    require(len(frequency) == 1 and frequency[0] > 0, 'Missing explicit observed timer frequency')
    entries = []
    for i, role in enumerate(ROLES):
        kind, offset, flags = specs[i*3:i*3+3]
        require(kind == 1 and offset < 16, 'Timer must reference a PPI')
        require(flags & 15 in (4, 8), 'Expected level timer trigger')
        require(flags & ~0xff0f == 0, 'Unreviewed timer flag bits')
        entries.append(dict(role=role, specifier=[kind, offset, flags], intid=16+offset,
                            trigger_flags=flags & 15, legacy_cpu_mask=(flags >> 8) & 255))
    require(len({entry['intid'] for entry in entries}) == 4, 'Timer interrupt aliases')
    provider, inherited_source = parent(timer)
    chain, seen = [], set()
    while True:
        path = node_path(provider)
        require(path not in seen, 'Interrupt provider cycle')
        seen.add(path)
        require(provider.enabled() and 'interrupt-controller' in provider.properties, 'Disabled or invalid controller')
        require(provider.cells('#interrupt-cells') == [3], 'Unreviewed interrupt cell count')
        compatible = provider.strings('compatible')
        chain.append(dict(node=path, compatible=compatible))
        if 'arm,gic-v3' in compatible:
            break
        require('qcom,pdc-sm8150' in compatible and len(chain) == 1, 'Unreviewed interrupt intermediary')
        provider, source = parent(provider)
        chain[-1]['parent_source'] = source
    gic = provider
    spans = [(physical(gic.parent, base, size), size) for base, size in registers(gic)]
    require(len(spans) == 2 and spans[0][1] >= 0x10000, 'Expected GICD and single GICR range')
    require(gic.cells('#redistributor-regions') == [1], 'Unreviewed redistributor region count')
    stride = number(gic.cells('redistributor-stride'))
    require(stride >= 0x20000 and stride % 0x10000 == 0 and spans[1][1] % stride == 0,
            'Invalid redistributor stride/range')
    for a, size in spans:
        require(size > 0 and a % 0x10000 == 0 and a + size <= 1 << 64, 'GIC range alignment/overflow')
    require(spans[0][0] + spans[0][1] <= spans[1][0] or spans[1][0] + spans[1][1] <= spans[0][0], 'GIC windows overlap')
    cpus = [node for node in nodes if node.properties.get('device_type') == b'cpu\0' and node.enabled()]
    affinities = [number(node.cells('reg')) for node in cpus]
    require(affinities and len(set(affinities)) == len(affinities), 'Missing or duplicate CPU affinities')
    require(len(cpus) <= spans[1][1] // stride, 'Insufficient declared redistributor slots')
    return dict(timer_node=node_path(timer), inherited_parent_source=inherited_source,
                interrupt_chain=chain, frequency=frequency[0], timer_interrupts=entries,
                gic_node=node_path(gic), distributor=dict(base=spans[0][0], bytes=spans[0][1]),
                redistributors=dict(base=spans[1][0], bytes=spans[1][1], stride=stride,
                                    declared_slots=spans[1][1]//stride, boot_cpu_frame_verified=False),
                enabled_cpu_affinities=affinities, irq_delivery_verified=False, boot_enabled=False)


def source_audit():
    repo = ROOT/'sources/Xiaomi_Kernel_OpenSource'
    require(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip() == KERNEL_REVISION,
            'Kernel source pin changed')
    specs = {
        'arch/arm64/boot/dts/qcom/sm8150.dtsi': ['interrupt-parent = <&pdc>', 'intc: interrupt-controller', 'redistributor-stride', 'compatible = "arm,armv8-timer"'],
        'Documentation/devicetree/bindings/arm/arch_timer.txt': ['secure, non-secure, virtual', 'clock-frequency'],
        'Documentation/devicetree/bindings/interrupt-controller/qti,pdc.txt': ['hierarchical irq', 'same as described'],
        'Documentation/devicetree/bindings/interrupt-controller/arm,gic-v3.txt': ['PPI interrupts', 'GIC Distributor interface', 'redistributor-stride'],
        'drivers/irqchip/qcom/pdc.c': ['qcom_pdc_translate', 'd->parent->ops->translate', 'get_pdc_pin', 'fwd_to_parent'],
        'drivers/irqchip/qcom/pdc-sm8150.c': ['sm8150_data', 'qcom_pdc_init'],
        'drivers/irqchip/irq-gic-v3.c': ['gic_irq_domain_translate', '*hwirq = fwspec->param[1] + 16', 'SPIs have restrictions'],
        'drivers/clocksource/arm_arch_timer.c': ['arch_timer_select_ppi', 'irq_of_parse_and_map(np, i)', 'ARCH_TIMER_VIRT_PPI'],
    }
    sources, blobs = [], {}
    for path, markers in specs.items():
        raw = subprocess.check_output(['git','-C',str(repo),'show',KERNEL_REVISION+':'+path])
        lines = raw.decode().splitlines()
        anchors = {marker: [i+1 for i,line in enumerate(lines) if marker in line] for marker in markers}
        require(all(anchors.values()), 'Missing primary source anchor: '+path)
        sources.append(dict(repository='sources/Xiaomi_Kernel_OpenSource', revision=KERNEL_REVISION,
                            path=path, sha256=sha(raw), anchors=anchors))
        blobs[path] = raw.decode()
    return sources, blobs


def crosscheck_reference(facts, blobs):
    source = blobs['arch/arm64/boot/dts/qcom/sm8150.dtsi']
    # Narrow fixed source blocks, not another board's configuration.
    def block(marker):
        at=source.index(marker); start=source.index('{',at); depth=1; end=start+1
        while depth:
            require(end < len(source), 'Unterminated primary DTS block')
            depth += (source[end]=='{') - (source[end]=='}'); end+=1
        return source[start+1:end-1]
    timer=block('\ttimer {')
    triples=re.findall(r'<\s*(1)\s+(\d+)\s+(0x[0-9a-fA-F]+)\s*>', timer)
    expected=[[int(kind),int(offset),int(flags,16)] for kind,offset,flags in triples]
    require(expected == [entry['specifier'] for entry in facts['timer_interrupts']], 'Live/reference timer interrupt mismatch')
    frequency=re.search(r'clock-frequency\s*=\s*<(\d+)>',timer)
    require(frequency and int(frequency[1])==facts['frequency'], 'Live/reference timer frequency mismatch')
    gic=block('intc: interrupt-controller')
    ranges=re.search(r'\breg\s*=\s*<(0x[0-9a-f]+)\s+(0x[0-9a-f]+)>\s*,\s*/\* GICD \*/\s*<(0x[0-9a-f]+)\s+(0x[0-9a-f]+)>',gic)
    require(ranges is not None,'Unrecognized pinned GIC reg syntax')
    require([int(value,16) for value in ranges.groups()] == [facts['distributor']['base'],facts['distributor']['bytes'],facts['redistributors']['base'],facts['redistributors']['bytes']], 'Live/reference GIC range mismatch')
    stride=re.search(r'redistributor-stride\s*=\s*<0x0\s+(0x[0-9a-f]+)>',gic)
    require(stride and int(stride[1],16)==facts['redistributors']['stride'],'Live/reference redistributor stride mismatch')
    require([item['compatible'] for item in facts['interrupt_chain']]==[['qcom,pdc-sm8150'],['arm,gic-v3']], 'Unexpected current interrupt hierarchy')
    pin_pairs=re.findall(r'\{\s*(\d+)\s*,\s*(\d+)\s*\}',blobs['drivers/irqchip/qcom/pdc-sm8150.c'])
    pdc_hwirqs={int(hwirq) for _,hwirq in pin_pairs}
    require(pdc_hwirqs and all(entry['intid'] not in pdc_hwirqs for entry in facts['timer_interrupts']), 'Timer matches a PDC-configured pin')
    return dict(live_and_reference_match=True, pdc_translation_forwards_to_parent=True,
                timer_intids_absent_from_pdc_pin_table=True, current_custom_kernel_identical_to_reference=False,
                trigger_flags_preserved=True,
                warning='Vendor DTS uses legacy 0xf08 (low-level plus CPU mask). Do not silently replace it with 4 or copy AAVMF PPI defaults.')


def android_timer_observation(text, facts):
    rows=[]
    for line in text.splitlines():
        if not line.rstrip().endswith('arch_timer') or ':' not in line:
            continue
        irq,rest=line.split(':',1); tokens=rest.split(); i=0
        while i<len(tokens) and tokens[i].isdigit():i+=1
        require(i>0 and len(tokens[i:])>=4 and tokens[i+1].isdigit(),'Malformed Android timer IRQ row')
        intid=int(tokens[i+1]); roles=[item['role'] for item in facts['timer_interrupts'] if item['intid']==intid]
        require(len(roles)==1,'Android timer IRQ does not match fresh FDT')
        rows.append(dict(linux_irq=int(irq), irqchip=tokens[i], intid=intid, trigger=tokens[i+2],
                         selected_role=roles[0], counter_columns=i, source='/proc/interrupts:arch_timer'))
    require(len(rows)==1,'Expected one Android architectural timer IRQ')
    return rows[0]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('collection',type=Path,help='Private current read-only interrupt collection')
    args=parser.parse_args()
    collection=args.collection.resolve()
    require(collection.is_relative_to(ROOT/'evidence/private'),'Expected private collection')
    blob=(collection/'live.dtb').read_bytes()
    before=(collection/'fdt-sha-before.txt').read_text().split()[0]
    after=(collection/'fdt-sha-after.txt').read_text().split()[0]
    require(before==after==sha(blob),'Fresh FDT source hash mismatch')
    facts=analyze_tree(read_fdt(blob))
    sources,blobs=source_audit()
    semantics=crosscheck_reference(facts,blobs)
    observed=android_timer_observation((collection/'interrupts.txt').read_text(),facts)
    entry=json.loads((ROOT/'UniXNU-raphael/evidence/entry-handoff.json').read_text())
    require(entry['entry']['cntfrq']==facts['frequency'],'Historical counter frequency differs')
    report=dict(passed=True,kind='Read-only source and data contract; no MMIO or interrupt programming',
        captured_utc=collection.name,collection=str(collection.relative_to(ROOT)),live_fdt_sha256=sha(blob),
        interrupts_sha256=sha((collection/'interrupts.txt').read_bytes()),facts=facts,reference_semantics=semantics,
        android_runtime=observed,historical_entry_frequency_agrees=True,primary_sources=sources,
        parser_sha256=sha(Path(__file__).read_bytes()),handset_rebooted=False,uefi_timer_arch_verified=False,
        unknowns=['GICD/GICR version and boot CPU redistributor register state at ABL handoff',
                  'ICC system-register access, grouping, priority and original firmware ownership',
                  'Nonsecure physical timer interrupt delivery in new firmware',
                  'Safe GIC/timer takeover and complete restoration before Android continuation'],
        command='python3 scripts/derive_interrupt_contract.py '+str(collection.relative_to(ROOT)))
    out=ROOT/'UniXNU-raphael/evidence/interrupt-resource-contract.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,chain=[item['node'] for item in facts['interrupt_chain']],
        timer_intids={item['role']:item['intid'] for item in facts['timer_interrupts']},android=observed),indent=2))
    print(out)


if __name__=='__main__':main()
