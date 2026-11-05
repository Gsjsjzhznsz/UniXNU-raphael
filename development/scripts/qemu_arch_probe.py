#!/usr/bin/env python3
"""QEMU-only FDT resource provenance and independent architecture wire checks."""
import json
import struct
import subprocess
from inspect_device import read_fdt, registers, node_path, sha

MACHINE = 'virt,gic-version=3,virtualization=off'
FIELDS = ('version status gicd gicd_bytes gicr gicr_bytes timer_sec timer_phys timer_virt timer_hyp '
          'saved_ctl saved_cval frequency cpu_protocol interrupt_protocol timer_protocol period '
          'relative_fired relative_ticks periodic_count periodic_ticks cancel_stable '
          'manager_completed manager_ticks sources_disabled timer_disabled timer_restored cval_after ctl_after').split()


def parse_resources(blob):
    return analyze_tree(read_fdt(blob))


def analyze_tree(root):
    assert root.strings('compatible') == ['linux,dummy-virt'], 'Only generated QEMU virt'
    assert root.cells('#address-cells') == root.cells('#size-cells') == [2]
    nodes = list(root.walk())
    gics = [n for n in nodes if 'arm,gic-v3' in n.strings('compatible')]
    timers = [n for n in nodes if 'arm,armv8-timer' in n.strings('compatible')]
    assert len(gics) == len(timers) == 1
    gic, timer = gics[0], timers[0]
    assert gic.parent is root and timer.parent is root and gic.enabled() and timer.enabled()
    assert gic.properties.get('ranges') == b'' and gic.cells('#redistributor-regions') == [1]
    assert 'interrupt-controller' in gic.properties and gic.cells('#interrupt-cells') == [3]
    assert root.cells('interrupt-parent') == gic.cells('phandle') and len(gic.cells('phandle')) == 1
    assert not any(k in timer.properties for k in ['interrupt-parent', 'interrupts-extended'])
    spans = registers(gic)
    assert len(spans) == 2
    for a, size in spans:
        assert a > 0 and size > 0 and (a | size) % 4096 == 0 and a + size < 1 << 64
    assert spans[0][0] + spans[0][1] <= spans[1][0] or spans[1][0] + spans[1][1] <= spans[0][0]
    values = timer.cells('interrupts')
    assert len(values) == 12
    ids = []
    for i in range(4):
        kind, ppi, flags = values[i*3:i*3+3]
        assert kind == 1 and 0 <= ppi < 16 and flags == 4
        ids.append(ppi + 16)
    assert len(set(ids)) == 4
    return dict(gicd=spans[0][0],gicd_bytes=spans[0][1],gicr=spans[1][0],gicr_bytes=spans[1][1],
                **dict(zip(['timer_sec','timer_phys','timer_virt','timer_hyp'],ids)))


def generate_resources(out,memory_mb=512,qemu='qemu-system-aarch64'):
    path = out/'qemu-generated.dtb'
    command = [qemu,'-machine',MACHINE+',dumpdtb='+str(path),
               '-cpu','cortex-a76','-m',str(memory_mb)+'M','-nographic','-net','none','-monitor','none']
    result = subprocess.run(command,capture_output=True,timeout=10)
    (out/'qemu-dumpdtb.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode == 0
    raw_blob=path.read_bytes()
    packed=out/'qemu-virt.dtb'
    compact_command=['dtc','-I','dtb','-O','dtb','-o',str(packed),str(path)]
    compact=subprocess.run(compact_command,capture_output=True,timeout=10)
    (out/'qemu-pack-dtb.log').write_bytes(compact.stdout+compact.stderr)
    assert compact.returncode==0
    blob=packed.read_bytes()
    assert parse_resources(blob)==parse_resources(raw_blob)
    report = dict(scope='QEMU only; never handset resources',resources=parse_resources(blob),
                  command=command,compact_command=compact_command,generated_dtb_sha256=sha(raw_blob),generated_dtb_bytes=len(raw_blob),dtb_sha256=sha(blob),dtb_bytes=len(blob),dtb_file=packed.name,
                  qemu_version=subprocess.check_output(['qemu-system-aarch64','--version'],text=True).strip())
    (out/'qemu-resources.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def decode(raw, stage, resources):
    assert stage in (2,3,6), 'Legacy injected BRK unsupported with real CpuDxe vectors'
    assert len(raw) == len(FIELDS)*8
    r = dict(zip(FIELDS,struct.unpack('>'+len(FIELDS)*'Q',raw)))
    assert r['version'] == 1 and r['status'] == {2:1,3:2,6:3}[stage]
    for name,value in resources.items():assert r[name] == value, name
    assert r['frequency'] > 0 and r['saved_ctl'] & ~7 == 0
    if stage < 6:
        assert not any(r[name] for name in FIELDS[13:]), 'Drivers have not run yet'
    else:
        for name in ['cpu_protocol','interrupt_protocol','timer_protocol','relative_fired','cancel_stable',
                     'manager_completed','sources_disabled','timer_disabled','timer_restored']:
            assert r[name] == 1, name
        assert r['period'] == 100000, '10 ms diagnostic design period'
        assert r['frequency']*8//100 <= r['relative_ticks'] <= r['frequency']
        assert 5 <= r['periodic_count'] <= 50
        assert r['frequency']*8//100 <= r['periodic_ticks'] <= r['frequency']
        assert r['frequency']*18//10 <= r['manager_ticks'] <= r['frequency']*5
        assert r['cval_after'] == r['saved_cval'] and ((r['ctl_after'] ^ r['saved_ctl']) & 3) == 0
        assert r['ctl_after'] & ~7 == 0
    return dict(**r,passed=True,handset_executed=False,gic_state_restored=False,
                xnu_executed=False,valid_kernel_handoff_verified=False)
