#!/usr/bin/env python3
"""Create an inspection-only core description from this run's explicit observations."""
import hashlib
import json
from pathlib import Path
import subprocess
from inspect_device import fdt_summary

ROOT = Path(__file__).resolve().parents[1]


def cells(values):
    return '<' + ' '.join(hex(value) for value in values) + '>'


def u64cells(value):
    return [value >> 32, value & 0xffffffff]


def main():
    evidence = ROOT / 'UniXNU-raphael/evidence/hardware-observations.json'
    report = json.loads(evidence.read_text())
    facts = report['facts']
    contract_path=ROOT/'UniXNU-raphael/evidence/interrupt-resource-contract.json'
    contract=json.loads(contract_path.read_text())
    assert contract['passed'] and contract['reference_semantics']['live_and_reference_match']
    assert contract['reference_semantics']['pdc_translation_forwards_to_parent']
    assert contract['reference_semantics']['timer_intids_absent_from_pdc_pin_table']
    gic, = [item for item in facts['peripherals'] if 'arm,gic-v3' in item['compatible']]
    timer, = [item for item in facts['peripherals'] if 'arm,armv8-timer' in item['compatible']]
    assert timer['interrupts']==[cell for item in contract['facts']['timer_interrupts'] for cell in item['specifier']]
    assert timer['clock-frequency']==[contract['facts']['frequency']]
    assert [(item['base'],item['size']) for item in gic['registers']]==[(contract['facts'][key]['base'],contract['facts'][key]['bytes']) for key in ['distributor','redistributors']]
    source = ROOT / 'sources/Xiaomi_Kernel_OpenSource/arch/arm64/boot/dts/qcom/sm8150.dtsi'
    primary = source.read_text()
    # These exact resources must be present in both this handset and Xiaomi's shared SoC source.
    assert gic['reg_cells'] == [0x17a00000, 0x10000, 0x17a60000, 0x100000]
    assert '<0x17a00000 0x10000>' in primary and '<0x17a60000 0x100000>' in primary
    assert timer['clock-frequency'] == [19200000] and '<19200000>' in primary
    lines = ['// SPDX-License-Identifier: BSD-2-Clause-Patent',
             '// Observation fixture only. No platform allocation policy or XNU support claim.',
             '// Source: ../UniXNU-raphael/evidence/hardware-observations.json',
             '// Timer parent is a normalized PDC->GIC projection, not original topology.',
             '// Fixed PDC reference forwards translation; timer INTIDs have no PDC pin.',
             '// See interrupt-resource-contract.json; no UEFI IRQ delivery was tested.',
             '/ {', '  #address-cells = <2>;', '  #size-cells = <2>;',
             '  cpus {', '    #address-cells = <2>;', '    #size-cells = <0>;',
             f'    timebase-frequency = {cells(timer["clock-frequency"])};']
    for cpu in facts['cpus']:
        if not cpu['enabled']:
            continue
        affinity = cpu['affinity']
        compat = ', '.join(json.dumps(item) for item in cpu['compatible'])
        lines.extend([f'    cpu@{affinity:x} {{', '      device_type = "cpu";',
                      f'      compatible = {compat};', f'      reg = {cells(u64cells(affinity))};',
                      '      enable-method = "psci";', '    };'])
    lines.extend(['  };', '  psci { compatible = "arm,psci-1.0"; method = "smc"; };',
                  '  soc {', '    compatible = "simple-bus";', '    #address-cells = <2>;',
                  '    #size-cells = <2>;', '    ranges;',
                  f'    gic: interrupt-controller@{gic["registers"][0]["base"]:x} {{',
                  '      compatible = "arm,gic-v3";', '      #address-cells = <0>;',
                  '      #interrupt-cells = <3>;', '      interrupt-controller;',
                  '      #redistributor-regions = <1>;',
                  f'      redistributor-stride = {cells(gic["redistributor-stride"])};',
                  '      reg = ' + cells([value for item in gic['registers'] for value in u64cells(item['base']) + u64cells(item['size'])]) + ';',
                  f'      interrupts = {cells(gic["interrupts"])};', '      interrupt-parent = <&gic>;',
                  '    };', '  };', '  timer {', '      compatible = "arm,armv8-timer";',
                  '      interrupt-parent = <&gic>;', f'      interrupts = {cells(timer["interrupts"])};',
                  f'      clock-frequency = {cells(timer["clock-frequency"])};', '  };', '};', ''])
    common = ROOT / 'UniXNU-sm8150-common/dts/sm8150.dtsi'
    common.parent.mkdir(parents=True, exist_ok=True)
    common.write_text('\n'.join(lines))
    lines = ['// SPDX-License-Identifier: BSD-2-Clause-Patent',
             '// Inspection fixture. Not an Android firmware DTB or a finished XNU description.',
             f'// Live FDT SHA256: {report["live_fdt_sha256"]}',
             '/dts-v1/;', '/include/ "sm8150.dtsi"', '/ {',
             '  model = "RAPHAEL";',
             '  compatible = "qcom,sm8150-cdp", "qcom,sm8150", "qcom,cdp";',
             f'  qcom,board-id = {cells(facts["qcom_board_id"])};',
             f'  qcom,msm-id = {cells(facts["qcom_msm_id"])};',
             f'  memory@{min(item["base"] for item in facts["memory"]):x} {{', '    device_type = "memory";',
             '    reg = ' + cells([value for item in facts['memory'] for value in u64cells(item['base']) + u64cells(item['size'])]) + ';',
             '  };', '  reserved-memory {', '    #address-cells = <2>;', '    #size-cells = <2>;', '    ranges;']
    for index, item in enumerate(facts['fixed_reservations']):
        name = item['source'].split('/')[-1].split(':')[0].split('@')[0]
        lines.extend([f'    {name}@{item["base"]:x} {{',
                      f'      reg = {cells(u64cells(item["base"]) + u64cells(item["size"]))};'])
        if item['no_map']:
            lines.append('      no-map;')
        if item['reusable']:
            lines.append('      reusable;')
        lines.append('    };')
    lines.extend(['  };', '  // Linux dynamically placed pools are listed in the JSON evidence, not allocated here.', '};', ''])
    board = ROOT / 'UniXNU-raphael/dts/raphael.dts'
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text('\n'.join(lines))
    out = ROOT / 'artifacts/observed-dts'
    out.mkdir(exist_ok=True)
    result = subprocess.run(['dtc', '-I', 'dts', '-O', 'dtb', '-i', str(common.parent),
                             '-o', str(out / 'raphael-observed.dtb'), str(board)], capture_output=True)
    (out / 'dtc.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    assert not result.stderr, result.stderr.decode()
    roundtrip = fdt_summary((out / 'raphael-observed.dtb').read_bytes())
    spans = lambda items: sorted((item['base'], item['size']) for item in items)
    assert spans(roundtrip['memory']) == spans(facts['memory'])
    assert spans(roundtrip['fixed_reservations']) == spans(facts['fixed_reservations'])
    assert [item['affinity'] for item in roundtrip['cpus']] == [item['affinity'] for item in facts['cpus'] if item['enabled']]
    rt_gic, = [item for item in roundtrip['peripherals'] if 'arm,gic-v3' in item['compatible']]
    assert spans(rt_gic['registers']) == spans(gic['registers'])
    manifest = dict(interrupt_contract_sha256=hashlib.sha256(contract_path.read_bytes()).hexdigest(), evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
                    primary_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    dtb_sha256=hashlib.sha256((out / 'raphael-observed.dtb').read_bytes()).hexdigest(),
                    result='host-compiled and resource roundtrip checked; inspection fixture, no handset execution')
    (out / 'report.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
