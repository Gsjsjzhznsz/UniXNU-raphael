#!/usr/bin/env python3
"""Replay a privately captured FDT's structure through an existing QEMU FD.

QEMU owns all hardware in this test. It updates /memory and /chosen for its
Linux boot protocol. A serial node is copied from QEMU's own generated FDT.
This is not an exact handset CPU-state or memory-ownership reproduction.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess

from build_sec_dxe import run_case, build_fixture
from entry_probe import ROOT, image_parameters, sha
from inspect_device import read_fdt
from inspect_diagnostic_fd import inspect_fd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--firmware-build', required=True, type=Path)
    parser.add_argument('--fdt', required=True, type=Path)
    args = parser.parse_args()
    build, source = args.firmware_build.resolve(), args.fdt.resolve()
    assert build.is_relative_to(ROOT / 'artifacts/sec-dxe-qemu')
    assert source.is_relative_to(ROOT / 'evidence/private')
    previous = json.loads((build / 'report.json').read_text())
    assert previous['qemu_passed'] and previous['stop_stage'] == 2
    values = json.loads((build / 'layout.json').read_text())['values']
    raw = (build / 'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
    assert sha(raw) == previous['firmware_sha256']
    inspect_fd(raw, values['FdBase'])
    out = ROOT / 'evidence/private/sec-fdt-replay' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    original = build_fixture(out, expected_stage=2,
                             extra_defines=[f'-DREPLAY_CONTEXT_BASE={values["ContextBase"]}ULL'])
    parameters = image_parameters(original)
    assert (parameters['image_size'], parameters['entry'], parameters['instruction']) == (
        values['ImageSize'], values['OriginalEntry'], values['OriginalInstruction'])
    emulator_fdt = out / 'emulator.dtb'
    commands = []

    def run(command):
        result = subprocess.run([str(x) for x in command], capture_output=True, timeout=20)
        commands.append(dict(command=[str(x) for x in command], returncode=result.returncode))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert result.returncode == 0, result.stderr.decode(errors='replace')

    run(['qemu-system-aarch64', '-machine', f'virt,virtualization=off,dumpdtb={emulator_fdt}',
         '-cpu', 'cortex-a76', '-m', '512M', '-nographic'])
    tree = read_fdt(emulator_fdt.read_bytes())
    uart = next(n for n in tree.walk() if 'arm,pl011' in n.strings('compatible'))
    reg = uart.properties['reg']
    target = out / 'replay.dtb'
    shutil.copyfile(source, target)
    # The receiver only uses this emulator-derived UART for PASS/FAIL output.
    run(['fdtput', '-p', '-t', 's', target, '/raphael-qemu-uart', 'compatible', 'arm,pl011'])
    run(['fdtput', '-t', 'x', target, '/raphael-qemu-uart', 'reg',
         *[hex(int.from_bytes(reg[i:i+4], 'big')) for i in range(0, len(reg), 4)]])
    execution = run_case(out, original, raw, image_parameters(original), values, dtb=target)
    report = dict(kind='QEMU SEC/FDT structural replay of private handset capture',
                  source_fdt_sha256=sha(source.read_bytes()), source_fdt=str(source.relative_to(ROOT)),
                  firmware_build=str(build.relative_to(ROOT)), firmware_sha256=sha(raw),
                  replay_input_sha256=sha(target.read_bytes()), execution=execution,
                  handset_executed=False, exact_handset_state_reproduced=False,
                  limits=['QEMU edits memory and chosen; UART is copied from its own FDT',
                          'Does not establish handset SEC execution or identify a hardware failure cause'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(execution, indent=2))
    print(out)
    assert execution['passed']


if __name__ == '__main__':
    main()
