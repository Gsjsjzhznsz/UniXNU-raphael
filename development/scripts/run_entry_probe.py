#!/usr/bin/env python3
"""Nonpersistent fastboot boot and nonce-checked Android/FDT readback."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import struct
import subprocess
import time
from entry_probe import ROOT, FIELDS, sha
from inspect_device import fdt_summary, read_fdt

ADB = '/mnt/d/Android/platform-tools/adb.exe'
FB = '/mnt/d/Android/platform-tools/fastboot.exe'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--evidence-name', choices=['entry-handoff','extent-download','native-layout-download','initrd-geometry'], help='Explicit result index; historical handset records are not overwritten by a new layout experiment')
    args = parser.parse_args()
    build = args.build.resolve()
    assert build.is_relative_to(ROOT / 'evidence/private/entry-probe-build')
    description = json.loads((build / 'report.json').read_text())
    if description.get('initrd_geometry_probe'):
        qp=ROOT/description['qemu_evidence'];assert sha(qp.read_bytes())==description['qemu_evidence_sha256']
        q=json.loads(qp.read_text());assert q['passed'] and q['geometry_verified']
        for item in description['probe_inputs']['inputs']:assert sha((ROOT/item['file']).read_bytes())==item['sha256']
    image = build / 'boot-entry-probe.img'
    assert sha(image.read_bytes()) == description['image_sha256']
    qemu = sorted((ROOT / 'artifacts/entry-probe-qemu').glob('*/report.json'))
    assert qemu and json.loads(qemu[-1].read_text())['passed'], 'Latest emulator check must pass'
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'evidence/private/entry-probe-run' / stamp
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    records = []

    def run(tool, *arguments, timeout=15, save=None):
        command = [tool, '-s', args.serial, *arguments]
        try:
            result = subprocess.run(command, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            records.append(dict(command=command, timed_out=True))
            (out / 'commands.json').write_text(json.dumps(records, indent=2))
            return None
        item = dict(command=command, returncode=result.returncode,
                    utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                    stderr=result.stderr.decode(errors='replace'))
        if save:
            (out / save).write_bytes(result.stdout)
            item.update(file=save, bytes=len(result.stdout), sha256=sha(result.stdout))
        else:
            item['stdout'] = result.stdout.decode(errors='replace')
        records.append(item)
        (out / 'commands.json').write_text(json.dumps(records, indent=2))
        return result

    def root(command, **options):
        return run(ADB, 'exec-out', 'su -c ' + shlex.quote(command), **options)

    result = run(ADB, 'get-state')
    assert result and result.stdout.strip() == b'device'
    result = root('sha256sum /dev/block/bootdevice/by-name/boot')
    assert result and result.returncode == 0
    before = result.stdout.decode().split()[0]
    assert before == description['source_sha256'], 'Installed boot differs from probe source'
    root('cat /sys/firmware/fdt', save='before.dtb')
    result = run(ADB, 'reboot', 'bootloader')
    assert result and result.returncode == 0
    ready = False
    for _ in range(45):
        result = run(FB, 'getvar', 'unlocked', timeout=3)
        if result and b'unlocked: yes' in result.stderr:
            ready = True
            break
        time.sleep(1)
    assert ready, 'Unlocked fastboot device did not appear'
    windows_path = subprocess.check_output(['wslpath', '-w', str(image)], text=True).strip()
    result = run(FB, 'boot', windows_path, timeout=90)
    accepted = bool(result and result.returncode == 0)
    if not accepted:
        run(FB, 'reboot')
    print('Fastboot boot accepted:', accepted, flush=True)
    complete = False
    for _ in range(100):
        result = run(ADB, 'get-state', timeout=3)
        if result and result.returncode == 0 and result.stdout.strip() == b'device':
            result = run(ADB, 'shell', 'getprop sys.boot_completed')
            if result and result.stdout.strip() == b'1':
                complete = True
                break
        time.sleep(1)
    report = dict(kind='new Linux-entry probe on handset; not UEFI execution',
                  image_sha256=description['image_sha256'], identifier=description['identifier'],
                  fastboot_boot_accepted=accepted, android_boot_completed=complete,
                  used_flash_or_erase=False, uefi_executed=False)
    report['candidate_extent_download_test'] = description.get('candidate_extent_download_test', False)
    report['downloaded_arm64_image_bytes'] = description['extended_arm64_image_bytes']
    report['zero_tail_padding_bytes'] = description.get('zero_tail_padding_bytes', 0)
    report['padded_tail_written_or_read_by_probe'] = False
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    assert complete, 'Android return not established; keep private logs and inspect connection'
    result = root('id')
    report['root_verified'] = bool(result and b'uid=0' in result.stdout)
    result = root('sha256sum /dev/block/bootdevice/by-name/boot')
    report['boot_partition_unchanged'] = bool(result and result.stdout.decode().split()[0] == before)
    root('cat /sys/firmware/fdt', save='after.dtb')
    root('cat /proc/cmdline; uname -a', save='android.txt')
    root('cat /sys/kernel/debug/dri/0/fb; cat /sys/kernel/debug/dri/0/state', save='android-drm.txt')
    blob = (out / 'after.dtb').read_bytes()
    assert struct.unpack_from('>II', blob) == (0xd00dfeed, len(blob))
    tree = read_fdt(blob)
    chosen = next(node for node in tree.walk() if node.name == 'chosen' and node.parent is tree)
    identifier = chosen.strings('raphael,entry-probe-id')
    report['nonce_matched'] = identifier == [description['identifier']]
    data = chosen.properties.get('raphael,entry-probe')
    report['entry_record_found'] = data is not None and len(data) == 160
    if report['entry_record_found']:
        values = struct.unpack('>20Q', data)
        report['entry'] = dict(zip(FIELDS, values))
        report['entry_hex'] = {key: hex(value) for key, value in report['entry'].items()}
    if description.get('initrd_geometry_probe'):
        raw_geometry=chosen.properties.get('raphael,initrd-geometry')
        report['initrd_geometry_record_found']=bool(raw_geometry and len(raw_geometry)==48)
        if report['initrd_geometry_record_found']:
            values=struct.unpack('>6Q',raw_geometry);report['initrd_geometry']=values
            report['initrd_geometry_verified']=values[0]==1 and values[2]-values[1]==description['expanded_ramdisk_bytes'] and values[3]==description['original_ramdisk_bytes']
    observed = fdt_summary(blob)
    (out / 'hardware-observations.json').write_text(json.dumps(observed, indent=2) + '\n')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(out)
    assert all(report.get(key) for key in ['root_verified', 'boot_partition_unchanged', 'nonce_matched', 'entry_record_found'])
    if description.get('initrd_geometry_probe'):assert report.get('initrd_geometry_verified')
    safe = dict(report)
    safe.update(source='fresh temporary fastboot image plus nonce-matched current-device FDT readback',
                fdt_sha256=sha(blob), probe_build=str(build.relative_to(ROOT)),
                private_readback=str(out.relative_to(ROOT)),
                limits=['Does not prove UEFI execution or reusable original boot services',
                        'Captured original SP/LR are historical observations, not new allocation authority'])
    filename = (args.evidence_name+'.json') if args.evidence_name else ('extent-download.json' if report['candidate_extent_download_test'] else 'entry-handoff.json')
    (ROOT / 'UniXNU-raphael/evidence' / filename).write_text(json.dumps(safe, indent=2) + '\n')


if __name__ == '__main__':
    main()
