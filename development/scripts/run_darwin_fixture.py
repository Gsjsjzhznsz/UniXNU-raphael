#!/usr/bin/env python3
"""Build unchanged pinned DarwinBoot and test only rejection/lifecycle on AAVMF.

No handset addresses, OS profile, valid kernel, ADT, or ExitBootServices call are
provided. Inputs deliberately cannot pass the kernel parser. All outputs stay
in an ignored artifact directory; the report separates build and execution.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time

from entry_probe import ROOT, sha
from source_pins import locked_revision

PINS = {
    'sources/mu_basecore': 'cfb93724a06ff86ff5ba971413368a7809ee42a5',
    'sources/UniXNU': locked_revision('UniXNU'),
    'sources/UniXNU/drivers/DarwinBoot': '3325e352d7df68a9f9ad74832ed94a6acbbd7390',
}


def invalid_images():
    def header(cpu=0x100000c, count=0, size=0):
        return struct.pack('<8I', 0xfeedfacf, cpu, 0, 2, count, size, 0, 0)
    cases = {
        'empty.macho': b'',
        'tiny.macho': struct.pack('<I', 0xfeedfacf),
        'zero.macho': bytes(32),
        'wrong-cpu.macho': header(cpu=0x1000007),
        'overflow.macho': header(size=0xffffffff),
        'truncated-command.macho': header(count=1),
        'bad-command.macho': header(count=1, size=8) + struct.pack('<2I', 0x19, 72),
        'no-entry.macho': header(),
    }
    # Each fixture is shorter than an ARM64 LC_UNIXTHREAD entry command, so
    # none can contain both a valid segment and entry. No kernel is accepted.
    assert all(len(data) < 32 + 72 + 288 for data in cases.values())
    return cases


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'artifacts/darwin-fixture-qemu' / stamp
    out.mkdir(parents=True, exist_ok=False)
    snapshot = out / 'snapshot'
    inputs, commands = [], []
    revisions = {}
    for repository, expected in PINS.items():
        actual = subprocess.check_output(['git', '-C', str(ROOT / repository), 'rev-parse', 'HEAD'], text=True).strip()
        assert actual == expected, (repository, actual)
        revisions[repository] = actual
    folders = ['tests/RaphaelTestPkg', 'sources/UniXNU/package/UniXNUPkg',
               'sources/UniXNU/drivers/DarwinBoot/DarwinBootPkg']
    for folder in folders:
        for path in sorted((ROOT / folder).rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            data = path.read_bytes()
            for repository in sorted(PINS, key=len, reverse=True):
                try:
                    local = path.relative_to(ROOT / repository)
                except ValueError:
                    continue
                assert data == subprocess.check_output(
                    ['git', '-C', str(ROOT / repository), 'show', revisions[repository] + ':' + str(local)]), relative
                break
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            inputs.append(dict(path=str(relative), sha256=sha(data)))
    core = ROOT / 'sources/mu_basecore'
    conf, toolchain = out / 'Conf', out / 'toolchain'
    conf.mkdir()
    toolchain.mkdir()
    for name in ['target', 'tools_def', 'build_rule']:
        shutil.copyfile(core / 'BaseTools/Conf' / (name + '.template'), conf / (name + '.txt'))
    for name in ['clang', 'clang++', 'lld-link', 'llvm-lib', 'llvm-objcopy']:
        actual = shutil.which(name)
        assert actual, name
        (toolchain / name).symlink_to(actual)
    packages = [snapshot / 'tests', snapshot / 'sources/UniXNU/package',
                snapshot / 'sources/UniXNU/drivers/DarwinBoot', core]
    env = dict(os.environ, WORKSPACE=str(out), CONF_PATH=str(conf),
               EDK_TOOLS_PATH=str(core / 'BaseTools'), PACKAGES_PATH=':'.join(map(str, packages)),
               CLANG_BIN=str(toolchain) + '/', PYTHON_COMMAND='python3', SOURCE_DATE_EPOCH='1793088000',
               PATH=f'{core / "BaseTools/BinWrappers/PosixLike"}:{core / "BaseTools/Source/C/bin"}:' + os.environ['PATH'])

    def record(command):
        commands.append(list(map(str, command)))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')

    command = ['build', '-p', 'RaphaelTestPkg/DarwinFixture.dsc', '-a', 'AARCH64',
               '-b', 'DEBUG', '-t', 'CLANGPDB', '-n', '4']
    record(command)
    with (out / 'build.log').open('xb') as log:
        subprocess.run(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    binary = out / 'Build/RaphaelDarwinFixture/DEBUG_CLANGPDB/AARCH64'
    images = {}
    for name, subsystem in [('DarwinBoot', 'IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER'),
                            ('DarwinFixture', 'IMAGE_SUBSYSTEM_EFI_APPLICATION')]:
        image = binary / (name + '.efi')
        command = ['llvm-readobj', '--file-headers', '--sections', str(image)]
        record(command)
        headers = subprocess.check_output(command, text=True)
        (out / (name + '-pe.txt')).write_text(headers)
        assert 'IMAGE_FILE_MACHINE_ARM64' in headers and subsystem in headers, headers
        assert '.reloc' in headers, 'Expected relocatable EFI image'
        images[name] = dict(bytes=image.stat().st_size, sha256=sha(image.read_bytes()),
                            machine='ARM64', subsystem=subsystem, relocations_present=True)
    esp = out / 'esp'
    boot = esp / 'EFI/BOOT'
    boot.mkdir(parents=True)
    shutil.copyfile(binary / 'DarwinFixture.efi', boot / 'BOOTAA64.EFI')
    shutil.copyfile(binary / 'DarwinBoot.efi', esp / 'DarwinBoot.efi')
    cases = esp / 'EFI/UniXNU/Cases'
    cases.mkdir(parents=True)
    invalid = invalid_images()
    for name, data in invalid.items():
        (cases / name).write_bytes(data)
    config = cases.parent / 'unixnu.toml'
    config.write_text('version = 1\n[boot]\ntimeout = 0\n[ui]\ntitle = "Darwin interface fixture"\n'
                      '[kits]\nautoload = false\n[[entry]]\nid = "invalid-kernel"\n'
                      'title = "Reject invalid kernel"\ntype = "xnu"\npath = "Cases/bad-command.macho"\n'
                      'args = "fixture-invalid-only"\n')
    shutil.copyfile('/usr/share/AAVMF/AAVMF_VARS.fd', out / 'vars.fd')
    firmware = {name: dict(path='/usr/share/AAVMF/' + name, sha256=sha(Path('/usr/share/AAVMF', name).read_bytes()))
                for name in ['AAVMF_CODE.fd', 'AAVMF_VARS.fd']}
    command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a57', '-m', '512',
               '-nographic', '-monitor', 'none', '-no-reboot', '-net', 'none',
               '-drive', 'if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/AAVMF/AAVMF_CODE.fd',
               '-drive', 'if=pflash,format=raw,unit=1,file=' + str(out / 'vars.fd'),
               '-drive', 'if=none,id=esp,format=raw,file=fat:rw:' + str(esp),
               '-device', 'virtio-blk-device,drive=esp']
    record(command)
    serial = out / 'serial.log'
    timed_out = False
    with serial.open('xb') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    raw = serial.read_text(errors='replace')
    checks = re.findall(r'DARWIN_FIXTURE_(?:PASS|FAIL) [^\r\n]*', raw)
    passed = ('DARWIN_FIXTURE_OK' in raw and 'DARWIN_FIXTURE_FAIL' not in raw and
              not timed_out and len(checks) >= 38)
    report = dict(passed=passed, host_build_passed=True, image_structure_passed=True,
                  handset_executed=False, xnu_executed=False, valid_kernel_supplied=False,
                  os_profile_selected=False, source_revision=subprocess.check_output(
                      ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                  revisions=revisions, source_inputs=inputs, runner_sha256=sha(Path(__file__).read_bytes()),
                  images=images, emulator_firmware=firmware, check_count=len(checks), checks=checks,
                  invalid_inputs={name: dict(bytes=len(data), sha256=sha(data)) for name, data in invalid.items()},
                  config_sha256=sha(config.read_bytes()), timeout=timed_out, qemu_returncode=process.returncode,
                  results=re.findall(r'DARWIN_FIXTURE_RESULT[^\r\n]*', raw),
                  limits=['QEMU/AAVMF supplies CPU, memory, filesystem, timer and runtime services',
                          'Only driver lifecycle, protocol ABI and rejected boot requests tested',
                          'No valid kernel, allocation window, ADT, ExitBootServices or kernel handoff tested',
                          'No phone firmware or hardware execution is established'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=passed, checks=len(checks), timeout=timed_out)))
    print(out)
    assert passed, raw[-6500:]


if __name__ == '__main__':
    main()
