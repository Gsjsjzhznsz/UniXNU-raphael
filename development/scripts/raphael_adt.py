#!/usr/bin/env python3
"""Source-derived single-CPU ADT. Not a whole-device hardware description."""
import json
import os
import struct
import sys
from entry_probe import ROOT, sha
from inspect_device import read_fdt, registers, physical, node_path
sys.path.insert(0, str(ROOT / 'sources/UniXNU/scripts'))
from unixnu.devicetree import node, empty_nvram_proxy

def storage_properties(fdt, plans):
    """Explicit immutable-media contract; runtime driver must recheck ownership."""
    from ufs_extent_plan import inspect_policy, validate_manifest
    assert set(plans) == {'OS', 'SystemOS'}, 'Both original system volumes are required'
    cpus = next(n for n in fdt.children if n.name == 'cpus')
    affinities = [int.from_bytes(n.properties['reg'], 'big') for n in cpus.children
                  if n.strings('device_type') == ['cpu']]
    assert len(affinities) == len(set(affinities)) == 8
    assert all(n & ~0xff00ffffff == 0 for n in affinities)
    psci = [n for n in fdt.children if n.name == 'psci']
    assert len(psci) == 1 and psci[0].strings('method') == ['smc']
    hosts = [n for n in fdt.walk() if b'qcom,ufshc' in n.properties.get('compatible', b'').split(b'\0')]
    smmus = [n for n in fdt.walk() if n.name.startswith('apps-smmu@') and
             b'qcom,qsmmu-v500' in n.properties.get('compatible', b'').split(b'\0')]
    assert len(hosts) == len(smmus) == 1
    host, smmu = hosts[0], smmus[0]
    assert host.enabled() and smmu.enabled()
    assert host.strings('reg-names')[0] == 'ufs_mem'
    assert smmu.strings('reg-names')[0] == 'base'
    assert not any(k in smmu.properties for k in
                   ['clocks', 'qcom,enable-static-cb', 'calxeda,smmu-secure-config-access'])
    resources = []
    for source in [host, smmu]:
        base, size = registers(source)[0]
        base = physical(source.parent, base, size)
        assert base > 0 and base % 4096 == 0 and size >= (0x84 if source is host else 0x4000)
        resources.append((base, size))
    assert all(a+n <= b or b+m <= a for i, (a,n) in enumerate(resources)
               for b,m in resources[i+1:])
    props = [('compatible', b'unixnu,raphael-ufs-ro\0'),
             ('unixnu,ufs-owner-contract', struct.pack('<I', 1)),
             ('unixnu,cpu-affinities', struct.pack('<8Q', *affinities))]
    provenance = dict(source_nodes=dict(hci=node_path(host), smmu=node_path(smmu), psci='/psci'),
                      registers=resources, cpu_affinities=affinities, plans={},
                      runtime_ownership_verified=False, handset_storage_execution_verified=False)
    geometry = None
    sizes = []
    for role, key in [('OS', 'unixnu,os-extents'), ('SystemOS', 'unixnu,systemos-extents')]:
        path = plans[role].resolve()
        validate_manifest(path, path.parent/'lun0-known-block.bin')
        raw = path.read_bytes(); info = inspect_policy(raw)
        bounds = struct.unpack_from('<3Q', raw, 24)
        assert geometry is None or geometry == bounds, 'Volumes must share the same physical LUN/partition'
        geometry = bounds; sizes.append(info['file_bytes'])
        props.append((key, raw))
        provenance['plans'][role] = dict(path=str(path.relative_to(ROOT)), **info)
    assert len(set(sizes)) == 2, 'Root verification selects a unique signed image capacity'
    return resources, props, provenance

def os_chosen_properties():
    # OS ABI policy from the pinned profile; no hardware identity or MMIO.
    import tomllib
    from unixnu.devicetree import typed_properties
    profile=ROOT/'sources/UniXNU/profiles/os/ipados-17.7.11-21H461/profile.toml'
    return typed_properties(tomllib.loads(profile.read_text())['adt']['chosen'])

def make_adt(out, blob, window, frequency, affinity, handset, ufs_plans=None, qemu_vmm_policy=True, qemu_dt_platform=False, qemu_io_bias=0, qemu_pmgr_nub=False):
    fdt = read_fdt(blob); nodes = list(fdt.walk())
    cpus = next(n for n in fdt.children if n.name == 'cpus')
    matches = [n for n in cpus.children if n.strings('device_type') == ['cpu'] and
        int.from_bytes(n.properties['reg'], 'big') == affinity]
    assert len(matches) == 1
    cpu = matches[0]
    gics = [n for n in nodes if b'arm,gic-v3' in n.properties.get('compatible', b'').split(b'\0') and n.strings('status') in ([], ['ok'], ['okay'])]
    assert len(gics) == 1
    gic = gics[0]; assert 'arm,gic-v3' in gic.strings('compatible')
    regs = registers(gic); assert len(regs) == 2
    timers = [n for n in nodes if b'arm,armv8-timer' in n.properties.get('compatible', b'').split(b'\0')]
    assert len(timers) == 1
    timer = timers[0]; assert 'arm,armv8-timer' in timer.strings('compatible')
    ints = timer.cells('interrupts'); assert len(ints) >= 9
    kind, irq, flags = ints[3:6]
    assert kind == 1 and 0 <= irq < 16 and flags & 15 in [4, 8]
    if 'clock-frequency' in timer.properties:
        assert int.from_bytes(timer.properties['clock-frequency'], 'big') == frequency
    banks = [reg for n in fdt.children if n.strings('device_type') == ['memory'] for reg in registers(n)]
    selected = [(base, size) for base, size in banks if base <= window['base'] and window['base'] + window['bytes'] <= base + size]
    assert len(selected) == 1
    dram_base, dram_size = selected[0]
    storage = None; storage_regs = []; storage_props = []
    if ufs_plans is not None:
        assert handset, 'Real handset storage must never appear in a QEMU ADT'
        storage_regs, storage_props, storage = storage_properties(fdt, ufs_plans)
    all_regs = regs + storage_regs
    assert qemu_io_bias in (0, 0x4000) and not (handset and qemu_io_bias)
    io_base = min(a for a, n in all_regs)-qemu_io_bias; io_end = max(a+n for a, n in all_regs)
    if storage is not None:
        storage_props.append(('reg', struct.pack('<4Q', *[v for a,n in storage_regs for v in (a-io_base,n)])))
    props = [('compatible', b'arm,gic-v3\0'), ('reg', struct.pack('<4Q', *[v for a, n in regs for v in [a-io_base, n]]))]
    if 'redistributor-stride' in gic.properties:
        props.append(('redistributor-stride', struct.pack('<Q', int.from_bytes(gic.properties['redistributor-stride'], 'big'))))
    assert not (handset and (qemu_dt_platform or qemu_pmgr_nub))
    root_model=b'unixnu,raphael-dt-policy-fixture\0' if qemu_dt_platform else fdt.properties['model']
    root_compatible=root_model if qemu_dt_platform else fdt.properties['compatible']
    tree = node('device-tree', [('model', root_model), ('compatible', root_compatible), ('#address-cells', struct.pack('<I', 2)), ('#size-cells', struct.pack('<I', 2))], [
        node('chosen', [('dram-base', struct.pack('<Q', dram_base)), ('dram-size', struct.pack('<Q', dram_size)),
            ('random-seed', os.urandom(64)), *os_chosen_properties(), *empty_nvram_proxy(),
            *([('unixnu,diagnostic-pmgr-nub', struct.pack('<I',1))] if qemu_pmgr_nub else []),
            *([('darwinboot-memory-size', struct.pack('<Q',window['window_bytes']))] if window.get('window_bytes',256*1048576)!=256*1048576 else []),
            *([('unixnu,qemu-root-observer-ms', struct.pack('<I',40000))] if qemu_dt_platform else [])], [node('memory-map', []), node('manifest-properties', [])]),
        node('cpus', [], [node('cpu0', [('device_type', b'cpu\0'), ('reg', struct.pack('<I', affinity)),
            ('state', b'running\0'), ('compatible', cpu.properties['compatible']),
            ('timebase-frequency', struct.pack('<I', frequency)), ('unixnu,boot-cpu', struct.pack('<I', 1)),
            ('unixnu,timer-intid', struct.pack('<I', 16+irq)), ('unixnu,physical-timer', struct.pack('<I', 1)),
            ('unixnu,timer-flags', struct.pack('<I', flags & 15))])]),
        node('arm-io', [('device_type', b'arm-io\0'), ('#address-cells', struct.pack('<I', 2)), ('#size-cells', struct.pack('<I', 2)), ('ranges', struct.pack('<3Q', 0, io_base, io_end-io_base))], [node('intc', props)] + ([node('ufs', storage_props)] if storage else [])),
        node('defaults', [] if handset or not qemu_vmm_policy else [('vmm-present', struct.pack('<I', 1))]), node('options', []), node('product', [])])
    path = out / 'kernel.macho.adt'; path.write_bytes(tree)
    report = dict(source_fdt_sha256=sha(blob), source_nodes=dict(cpu=cpu.name, gic=gic.name, timer=timer.name),
        adt_sha256=sha(tree), adt_bytes=len(tree), cpu_affinity=affinity, timebase_frequency=frequency,
        timer_fdt_specifier=ints[3:6], timer_intid=16+irq, gic_registers=regs,
        declared_banks=banks, selected_physical_bank=[dram_base, dram_size],
        memory_policy='Report only the declared bank containing the grant; boot_args alone grants 256MiB. No flattening of holes or grant of other bank bytes.',
        entropy_source='64 bytes host os.urandom; no hardware RNG claim',
        volatile_nvram='generic CHRP synthetic empty bank, no handset NVRAM read or write',
        handset_parameters=handset, os_vmm_policy=(not handset and qemu_vmm_policy), qemu_dt_platform_fixture=qemu_dt_platform, qemu_io_bias=qemu_io_bias, qemu_pmgr_nub_fixture=qemu_pmgr_nub, handset_kernel_hardware_execution_verified=False)
    if storage is not None: report['ufs_storage'] = storage
    if handset:
        facts = json.loads((ROOT / 'UniXNU-raphael/evidence/hardware-observations.json').read_text())['facts']
        assert sorted(banks) == sorted((x['base'], x['size']) for x in facts['memory'])
        assert frequency == 19200000 and affinity == 0 and 16+irq == 18
    (out / 'adt-provenance.json').write_text(json.dumps(report, indent=2)+'\n')
    return path, report
