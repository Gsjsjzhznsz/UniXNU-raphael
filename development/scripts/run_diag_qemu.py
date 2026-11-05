#!/usr/bin/env python3
"""Execute the diagnostic under AAVMF. Evidence is explicitly emulated, not handset."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=Path)
    parser.add_argument('--graphics', action='store_true')
    args = parser.parse_args()
    image = args.image.resolve()
    out = ROOT / 'artifacts/qemu-diag' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    volume = out / 'esp'
    boot = volume / 'EFI/BOOT'
    boot.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(image, boot / 'BOOTAA64.EFI')
    shutil.copyfile('/usr/share/AAVMF/AAVMF_VARS.fd', out / 'vars.fd')
    serial = out / 'serial.log'
    command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a57', '-m', '512',
               '-nographic', '-monitor', 'none', '-no-reboot', '-net', 'none',
               '-drive', 'if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/AAVMF/AAVMF_CODE.fd',
               '-drive', f'if=pflash,format=raw,unit=1,file={out / "vars.fd"}',
               '-drive', f'if=none,id=esp,format=raw,file=fat:rw:{volume}',
               '-device', 'virtio-blk-device,drive=esp']
    if args.graphics:
        command.extend(['-device', 'virtio-gpu-pci', '-display', 'none'])
    (out / 'command.json').write_text(json.dumps(command, indent=2))
    result = dict(kind='emulator-runtime', handset_executed=False, image=str(image),
                  image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                  firmware_sha256=hashlib.sha256(Path('/usr/share/AAVMF/AAVMF_CODE.fd').read_bytes()).hexdigest(),
                  firmware_package=subprocess.check_output(['dpkg-query', '-W', 'qemu-efi-aarch64'], text=True).strip())
    with serial.open('xb') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
        sent = False
        try:
            for tick in range(100):
                time.sleep(0.5)
                data = serial.read_bytes()
                if b'RAPHAEL:MENU: G=' in data and not sent:
                    # Exercise three menu paths through the emulated console.
                    process.stdin.write(b'gmq')
                    process.stdin.flush()
                    sent = True
                if b'RAPHAEL:DIAG:return-to-firmware' in data:
                    break
                if process.poll() is not None:
                    break
            else:
                result['failure'] = 'No diagnostic return marker within 50 seconds'
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    data = serial.read_bytes()
    markers = [b'RAPHAEL:DIAG:entered', b'RAPHAEL:CPU:counter-frequency=', b'RAPHAEL:MEMORY:count=',
               b'RAPHAEL:MENU: G=', b'RAPHAEL:INPUT:unicode=', b'RAPHAEL:DIAG:return-to-firmware']
    result['markers'] = {marker.decode(): marker in data for marker in markers}
    result['passed'] = all(result['markers'].values())
    result['gop_available'] = b'RAPHAEL:GOP:width=' in data
    if args.graphics:
        result['passed'] = result['passed'] and result['gop_available']
    result['limits'] = 'AAVMF services and emulated CPU; no Raphael SEC/DRAM/MMIO/GOP/physical keys validation'
    (out / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print(out)
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
