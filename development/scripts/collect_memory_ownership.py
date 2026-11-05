#!/usr/bin/env python3
"""Read-only memory ownership evidence; never publishes allocatable UEFI RAM."""
import argparse
import datetime as dt
import json
import shlex
import subprocess
from pathlib import Path
from entry_probe import ROOT, sha
from inspect_device import read_fdt

ADB = '/mnt/d/Android/platform-tools/adb.exe'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    args = parser.parse_args()
    out = ROOT/'evidence/private/memory-ownership'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    commands = []

    def capture(filename, command, required=True):
        result = subprocess.run([ADB, '-s', args.serial, 'exec-out', 'su -c '+shlex.quote(command)],
                                capture_output=True, timeout=30)
        (out/filename).write_bytes(result.stdout)
        commands.append(dict(file=filename, command=command, returncode=result.returncode,
                             bytes=len(result.stdout), sha256=sha(result.stdout),
                             stderr=result.stderr.decode(errors='replace')))
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        if required:
            assert result.returncode == 0, filename
        return result.stdout

    assert b'uid=0' in capture('root.txt', 'id')
    expected = json.loads((ROOT/'UniXNU-raphael/evidence/entry-handoff.json').read_text())
    expected_hash = json.loads((ROOT/expected['probe_build']/'report.json').read_text())['source_sha256']
    before = capture('boot-before.txt', 'sha256sum /dev/block/bootdevice/by-name/boot').decode().split()[0]
    assert before == expected_hash
    blob = capture('live.dtb', 'cat /sys/firmware/fdt')
    tree = read_fdt(blob)
    chosen = next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
    prefixes = ('raphael,entry-probe', 'raphael,sec-dxe', 'raphael,display-', 'raphael,input-',
                'raphael,payload-', 'raphael,gic-', 'raphael,icc-', 'raphael,timer-',
                'raphael,physical-timer-', 'raphael,manager-', 'raphael,ppi-')
    assert not any(k.startswith(prefixes) for k in chosen.properties)
    capture('iomem.txt', 'cat /proc/iomem')
    capture('meminfo.txt', 'cat /proc/meminfo')
    capture('cmdline.txt', 'cat /proc/cmdline')
    capture('soc-id.txt', 'cat /sys/devices/soc0/soc_id')
    capture('boot-completed.txt', 'getprop sys.boot_completed')
    optional = [('/sys/kernel/debug/memblock/memory', 'memblock-memory.txt'),
                ('/sys/kernel/debug/memblock/reserved', 'memblock-reserved.txt'),
                ('/sys/firmware/memmap', 'firmware-memmap.txt'),
                ('/sys/firmware/efi', 'firmware-efi.txt'),
                ('/sys/devices/system/cpu/cpu0/regs/identification/id_aa64mmfr0_el1', 'cpu-mmfr0.txt'),
                ('/sys/devices/system/cpu/cpu0/regs/identification/id_aa64pfr0_el1', 'cpu-pfr0.txt'),
                ('/sys/devices/system/cpu/cpu0/regs/identification/midr_el1', 'cpu-midr.txt')]
    for path, filename in optional:
        capture(filename, 'if [ -f '+shlex.quote(path)+' ]; then cat '+shlex.quote(path)+
                '; elif [ -d '+shlex.quote(path)+' ]; then ls -la '+shlex.quote(path)+
                '; else echo unavailable; fi', required=False)
    capture('dmesg.txt', 'dmesg', required=False)
    after = capture('boot-after.txt', 'sha256sum /dev/block/bootdevice/by-name/boot').decode().split()[0]
    report = dict(read_only=True, collection_utc=out.name, root_verified=True,
                  android_boot_completed=(out/'boot-completed.txt').read_text().strip()=='1',
                  boot_partition_unchanged=before==after==expected_hash,
                  transient_probe_absent=True, fdt_sha256=sha(blob),
                  collector_sha256=sha(Path(__file__).read_bytes()),
                  files=[dict(file=x['file'], bytes=x['bytes'], sha256=x['sha256'],
                              returncode=x['returncode']) for x in commands],
                  limitations=['Linux runtime ownership is not a complete pre-kernel UEFI map',
                               'No memory writes, allocator registration or MMIO access performed'])
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    assert report['android_boot_completed'] and report['boot_partition_unchanged']
    (out/'COMPLETE').write_text('read-only collection complete\n')
    print(out)
    print('Read-only memory evidence collected; no RAM ownership conclusion')


if __name__ == '__main__':
    main()
