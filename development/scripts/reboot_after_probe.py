#!/usr/bin/env python3
"""Normal reboot after RAM-only testing; verify the transient probe disappears."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import subprocess
import time
from entry_probe import ROOT, sha
from inspect_device import read_fdt

ADB = '/mnt/d/Android/platform-tools/adb.exe'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--verify-only', action='store_true', help='Audit a manual reboot without rebooting again')
    args = parser.parse_args()
    handoff = json.loads((ROOT / 'UniXNU-raphael/evidence/entry-handoff.json').read_text())
    previous = ROOT / handoff['probe_build'] / 'report.json'
    source_hash = json.loads(previous.read_text())['source_sha256']
    out = ROOT / 'evidence/private/entry-probe-cleanup' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(*arguments, timeout=10, binary=False):
        result = subprocess.run([ADB, '-s', args.serial, *arguments], capture_output=True, timeout=timeout)
        commands.append(dict(arguments=list(arguments), returncode=result.returncode,
                             stdout_sha256=sha(result.stdout) if binary else None,
                             stdout=None if binary else result.stdout.decode(errors='replace'),
                             stderr=result.stderr.decode(errors='replace')))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result

    def root(command, **kwargs):
        return run('exec-out', 'su -c ' + shlex.quote(command), **kwargs)

    assert root('sha256sum /dev/block/bootdevice/by-name/boot').stdout.decode().split()[0] == source_hash
    if not args.verify_only:
        assert run('reboot').returncode == 0
    complete = False
    for _ in range(100):
        state = run('get-state')
        if state.returncode == 0 and state.stdout.strip() == b'device':
            if run('shell', 'getprop sys.boot_completed').stdout.strip() == b'1':
                complete = True
                break
        time.sleep(1)
    assert complete
    root_ok = b'uid=0' in root('id').stdout
    current_hash = root('sha256sum /dev/block/bootdevice/by-name/boot').stdout.decode().split()[0]
    fdt = root('cat /sys/firmware/fdt', binary=True).stdout
    (out / 'baseline.dtb').write_bytes(fdt)
    tree = read_fdt(fdt)
    chosen = next(node for node in tree.walk() if node.name == 'chosen' and node.parent is tree)
    absent = not any(key.startswith(('raphael,darwin-', 'raphael,entry-probe', 'raphael,sec-dxe', 'raphael,display-', 'raphael,input-', 'raphael,payload-', 'raphael,gic-', 'raphael,icc-', 'raphael,timer-', 'raphael,physical-timer-', 'raphael,manager-', 'raphael,ppi-', 'raphael,ram-')) for key in chosen.properties)
    report = dict(normal_android_reboot=not args.verify_only, recovery_audit_without_extra_reboot=args.verify_only,
                  android_boot_completed=complete,
                  root_verified=root_ok, boot_partition_unchanged=current_hash == source_hash,
                  transient_probe_absent=absent, fdt_sha256=sha(fdt),
                  flash_or_restore_performed=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(out)
    assert root_ok and current_hash == source_hash and absent


if __name__ == '__main__':
    main()
