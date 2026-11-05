#!/usr/bin/env python3
"""Execute the actual probe before a receiving kernel fixture in QEMU."""
import datetime as dt
import argparse
import json
import subprocess
import tomllib
from entry_probe import ROOT, SOURCE, LIBFDT, image_parameters, compile_probe, instrument, run, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate-extent', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'artifacts/entry-probe-qemu' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    fixture = ROOT / 'scripts/fixtures'
    flags = ['-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-fpie',
             '-fvisibility=hidden', '-mgeneral-regs-only', '-mstrict-align',
             '-ffunction-sections', '-fdata-sections', '-I' + str(LIBFDT)]
    inputs = [fixture / 'entry_probe_kernel.S', fixture / 'entry_probe_kernel.c', SOURCE / 'Runtime.c']
    inputs += [LIBFDT / (name + '.c') for name in ['fdt', 'fdt_ro', 'fdt_rw', 'fdt_wip']]
    objects = []
    for i, source in enumerate(inputs):
        obj = out / f'fixture-{i}.o'
        run(out, ['aarch64-linux-gnu-gcc', *flags, '-c', source, '-o', obj])
        objects.append(obj)
    elf = out / 'fixture.elf'
    run(out, ['aarch64-linux-gnu-gcc', '-nostdlib', '-static', '-no-pie',
              '-Wl,--build-id=none,--gc-sections,-T,' + str(fixture / 'entry_probe_kernel.ld'),
              '-o', elf, *objects])
    original = out / 'fixture.Image'
    run(out, ['aarch64-linux-gnu-objcopy', '-O', 'binary', elf, original])
    parameters = image_parameters(original.read_bytes())
    payload = compile_probe(out, parameters, 'qemu-entry-probe-fixture')
    if args.candidate_extent:
        geometry = tomllib.loads((ROOT / 'UniXNU-raphael/package/firmware/Resources/memory-plan.toml').read_text())['geometry']
        extent = sum(geometry[key] for key in ['bridge_size', 'fd_capacity', 'sec_stack_size', 'dxe_arena_size', 'fdt_copy_capacity'])
        assert extent >= len(payload)
        payload += bytes(extent - len(payload))
    image = instrument(original.read_bytes(), payload, parameters)
    (out / 'instrumented.Image').write_bytes(image)
    executions = []
    for virtualization in ['off', 'on']:
        command = ['qemu-system-aarch64', '-machine', 'virt,virtualization=' + virtualization,
                   '-cpu', 'cortex-a76', '-m', '512M', '-nographic', '-no-reboot',
                   '-semihosting-config', 'enable=on,target=native',
                   '-kernel', str(out / 'instrumented.Image'), '-append', 'fixture_cookie=unchanged']
        try:
            result = subprocess.run(command, capture_output=True, timeout=15)
            log = result.stdout + result.stderr
            success = result.returncode == 0 and b'ENTRY_PROBE_FIXTURE_OK' in log and b'FAIL ' not in log
        except subprocess.TimeoutExpired as exc:
            log = (exc.stdout or b'') + (exc.stderr or b'')
            success = False
        (out / ('serial-' + virtualization + '.log')).write_bytes(log)
        executions.append(dict(command=command, passed=success, checks=log.decode(errors='replace').splitlines()))
    report = dict(executions=executions, passed=all(x['passed'] for x in executions),
                  instrumented_sha256=sha(image), parameters=parameters,
                  downloaded_image_bytes=len(image), candidate_extent_padding=args.candidate_extent,
                  handset_executed=False, full_uefi=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(out)
    assert report['passed']


if __name__ == '__main__':
    main()
