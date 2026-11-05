#!/usr/bin/env python3
"""Query bootloader state, then return to Android. No flash/erase/unlock commands."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/guo/work/raphael-fresh')
ADB = '/mnt/d/Android/platform-tools/adb.exe'
FB = '/mnt/d/Android/platform-tools/fastboot.exe'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    serial = parser.parse_args().serial
    out = ROOT / 'evidence/private/fastboot' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    records = []

    def run(tool, *args, timeout=20):
        command = [tool, '-s', serial, *args]
        result = subprocess.run(command, capture_output=True, timeout=timeout)
        records.append(dict(command=command, returncode=result.returncode,
                            stdout=result.stdout.decode(errors='replace'),
                            stderr=result.stderr.decode(errors='replace'),
                            utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        (out / 'commands.json').write_text(json.dumps(records, indent=2))
        return result

    assert run(ADB, 'get-state').stdout.strip() == b'device'
    assert run(ADB, 'reboot', 'bootloader').returncode == 0
    for attempt in range(40):
        devices = subprocess.run([FB, 'devices'], capture_output=True, timeout=5)
        if any(line.split()[0] == serial.encode() for line in devices.stdout.splitlines() if line.split()):
            break
        time.sleep(1)
    else:
        raise RuntimeError('Device did not enumerate in fastboot; no further commands issued')
    try:
        for name in ['product', 'unlocked', 'secure', 'anti', 'current-slot', 'has-slot:boot', 'version-bootloader', 'max-download-size']:
            result = run(FB, 'getvar', name)
            print(result.stderr.decode(errors='replace').strip(), flush=True)
        result = run(FB, 'oem', 'device-info')
        print(result.stderr.decode(errors='replace').strip(), flush=True)
    finally:
        result = run(FB, 'reboot')
        assert result.returncode == 0, 'fastboot reboot failed'
    run(ADB, 'wait-for-device', timeout=180)
    for attempt in range(90):
        result = run(ADB, 'shell', 'getprop sys.boot_completed')
        if result.stdout.strip() == b'1':
            print('ANDROID_BOOT_COMPLETED', flush=True)
            break
        time.sleep(1)
    else:
        raise RuntimeError('Android boot completion not observed')
    assert b'uid=0' in run(ADB, 'shell', 'su -c id').stdout
    (out / 'COMPLETE').write_text('Read-only bootloader queries; returned to Android and verified root.\n')
    print(out)


if __name__ == '__main__':
    main()
