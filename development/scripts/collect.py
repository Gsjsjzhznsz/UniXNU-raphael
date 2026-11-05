#!/usr/bin/env python3
"""Read-only, binary-safe collection from one explicitly selected Android device."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shlex
import struct
import subprocess

ROOT = Path('/home/guo/work/raphael-fresh')
ADB = '/mnt/d/Android/platform-tools/adb.exe'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    args = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'evidence/private/device' / stamp
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    records = []

    def run(name, command, required=True):
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        result = subprocess.run([ADB, '-s', args.serial, 'exec-out',
                                 'su -c ' + shlex.quote(command)],
                                capture_output=True, timeout=240)
        path = out / name
        with path.open('xb') as stream:
            stream.write(result.stdout)
        with (out / (name + '.stderr')).open('xb') as stream:
            stream.write(result.stderr)
        records.append(dict(file=name, command=command, started_utc=started,
                            returncode=result.returncode, bytes=len(result.stdout),
                            sha256=hashlib.sha256(result.stdout).hexdigest()))
        (out / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
        if required and result.returncode:
            raise RuntimeError(f'{name}: exit {result.returncode}: {result.stderr!r}')
        return result.stdout

    run('identity.txt', 'id; getprop; uname -a; cat /proc/version; cat /sys/devices/soc0/soc_id; cat /sys/devices/soc0/machine; cat /sys/devices/soc0/family; cat /sys/devices/soc0/revision')
    run('cmdline.txt', 'cat /proc/cmdline')
    run('iomem.txt', 'cat /proc/iomem')
    run('meminfo.txt', 'cat /proc/meminfo')
    run('cpuinfo.txt', 'cat /proc/cpuinfo')
    run('input.txt', 'cat /proc/bus/input/devices')
    run('partitions.txt', 'cat /proc/partitions; ls -l /dev/block/bootdevice/by-name')
    run('dmesg.txt', 'dmesg')
    run('display.txt', 'ls -la /sys/class/graphics /sys/class/drm; dumpsys SurfaceFlinger --display-id; wm size; wm density', required=False)
    run('mounts.txt', 'cat /proc/mounts')
    before = run('dt-live-sha-before.txt', 'sha256sum /sys/firmware/fdt')
    fdt = run('live.dtb', 'cat /sys/firmware/fdt')
    assert struct.unpack_from('>I', fdt)[0] == 0xd00dfeed, 'FDT magic mismatch'
    assert struct.unpack_from('>I', fdt, 4)[0] == len(fdt), 'FDT size mismatch'
    after = run('dt-live-sha-after.txt', 'sha256sum /sys/firmware/fdt')
    assert hashlib.sha256(fdt).hexdigest() == after.decode().split()[0] == before.decode().split()[0]
    for name in ['boot', 'dtbo', 'xbl', 'xbl_config', 'abl', 'imagefv', 'uefisecapp']:
        source = '/dev/block/bootdevice/by-name/' + name
        size = int(run(name + '.size.txt', 'blockdev --getsize64 ' + source).strip())
        assert 0 < size <= 256 * 1024 * 1024, f'Unexpected partition size: {name}: {size}'
        before = run(name + '.sha-before.txt', 'sha256sum ' + source).decode().split()[0]
        image = run(name + '.img', 'cat ' + source)
        after = run(name + '.sha-after.txt', 'sha256sum ' + source).decode().split()[0]
        actual = hashlib.sha256(image).hexdigest()
        assert len(image) == size and actual == before == after, f'Partition verification failed: {name}'
        print(f'{name}: {size} bytes sha256={actual}', flush=True)
    (out / 'COMPLETE').write_text('Read-only collection completed; not a restorable phone backup.\n')
    print(out)


if __name__ == '__main__':
    main()
