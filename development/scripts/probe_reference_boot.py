#!/usr/bin/env python3
"""Test RAM-only fastboot boot with the freshly captured, unchanged current boot image."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
ADB = '/mnt/d/Android/platform-tools/adb.exe'
FB = '/mnt/d/Android/platform-tools/fastboot.exe'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--collection', type=Path, required=True)
    args = parser.parse_args()
    image = args.collection.resolve() / 'boot.img'
    assert (image.parent / 'COMPLETE').is_file()
    image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
    out = ROOT / 'evidence/private/reference-boot' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    records = []

    def run(tool, *arguments, timeout=20):
        command = [tool, '-s', args.serial, *arguments]
        result = subprocess.run(command, capture_output=True, timeout=timeout)
        records.append(dict(command=command, returncode=result.returncode,
                            stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace'),
                            utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        (out / 'commands.json').write_text(json.dumps(records, indent=2))
        return result

    assert run(ADB, 'get-state').stdout.strip() == b'device'
    partition_hash = run(ADB, 'shell', 'su -c "sha256sum /dev/block/bootdevice/by-name/boot"').stdout.decode().split()[0]
    assert partition_hash == image_hash, 'Fresh image no longer matches current installed boot; do not boot'
    assert run(ADB, 'reboot', 'bootloader').returncode == 0
    for attempt in range(40):
        result = subprocess.run([FB, 'devices'], capture_output=True, timeout=5)
        if any(line.split()[0] == args.serial.encode() for line in result.stdout.splitlines() if line.split()):
            break
        time.sleep(1)
    else:
        raise RuntimeError('Fastboot device absent')
    state = run(FB, 'getvar', 'unlocked')
    assert b'unlocked: yes' in state.stderr
    # Windows fastboot needs a Windows path. wslpath performs conversion of this exact fresh file.
    windows_path = subprocess.check_output(['wslpath', '-w', str(image)], text=True).strip()
    boot = run(FB, 'boot', windows_path, timeout=90)
    accepted = boot.returncode == 0
    print(boot.stderr.decode(errors='replace'), flush=True)
    if not accepted:
        assert run(FB, 'reboot').returncode == 0
    assert run(ADB, 'wait-for-device', timeout=180).returncode == 0
    complete = False
    for attempt in range(120):
        if run(ADB, 'shell', 'getprop sys.boot_completed').stdout.strip() == b'1':
            complete = True
            break
        time.sleep(1)
    root = run(ADB, 'shell', 'su -c id')
    kernel = run(ADB, 'shell', 'uname -a')
    final_hash = run(ADB, 'shell', 'su -c "sha256sum /dev/block/bootdevice/by-name/boot"').stdout.decode().split()[0]
    report = dict(test='reference Android image only; not a new UEFI image', image_sha256=image_hash,
                  fastboot_boot_accepted=accepted, android_boot_completed=complete,
                  root_verified=b'uid=0' in root.stdout, boot_partition_unchanged=final_hash == image_hash,
                  kernel=kernel.stdout.decode().strip(), source='fresh source-device image; not old backup',
                  used_flash_or_erase=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(out)
    assert complete and report['root_verified'] and report['boot_partition_unchanged']


if __name__ == '__main__':
    main()
