#!/usr/bin/env python3
"""QEMU/AAVMF positive synthetic Mach-O handoff, never an XNU/phone kernel."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time
import tempfile

from inspect_device import ROOT, sha
from source_pins import locked_revision

PINS = {
    'sources/mu_basecore': 'cfb93724a06ff86ff5ba971413368a7809ee42a5',
    'sources/UniXNU': locked_revision('UniXNU'),
    'sources/UniXNU/drivers/DarwinBoot': '3325e352d7df68a9f9ad74832ed94a6acbbd7390',
}


def synthetic_images(out,snapshot,mode):
    from unixnu.devicetree import node
    from entry_probe import run
    fixtures=snapshot/'scripts/fixtures'
    include=snapshot/'tests/RaphaelTestPkg/Include'
    driver=snapshot/'sources/UniXNU/drivers/DarwinBoot/DarwinBootPkg/Driver'
    core=ROOT/'sources/mu_basecore/MdePkg/Include'
    flags=['-fshort-wchar','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-fpie','-fvisibility=hidden',
           '-mgeneral-regs-only','-mstrict-align','-ffunction-sections','-fdata-sections',
           '-I'+str(include),'-I'+str(driver),'-I'+str(core),'-I'+str(core/'AArch64')]
    objects=[]
    for name in ['darwin_handoff_entry.S','darwin_handoff_kernel.c']:
        target=out/(name+'.o');run(out,['aarch64-linux-gnu-gcc',*flags,'-c',fixtures/name,'-o',target]);objects.append(target)
    elf=out/'receiver.elf'
    run(out,['aarch64-linux-gnu-gcc','-nostdlib','-static','-no-pie','-Wl,--build-id=none,--gc-sections,-T,'+str(fixtures/'darwin_handoff.ld'),'-o',elf,*objects])
    readelf=run(out,['aarch64-linux-gnu-readelf','-h','-r','-s',elf]).decode()
    (out/'receiver-elf.txt').write_text(readelf)
    assert 'There are no relocations' in readelf
    run(out,['aarch64-linux-gnu-objcopy','-O','binary',elf,out/'receiver.bin'])
    code=(out/'receiver.bin').read_bytes();assert len(code)<0x1c000
    virtual=0xffff000000200000
    segment=struct.pack('<II16sQQQQIIII',0x19,72,b'__PROBE',virtual,0x20000,4096,len(code),7,7,0,0)
    thread=bytearray(288);struct.pack_into('<4I',thread,0,5,288,6,68);struct.pack_into('<Q',thread,272,virtual)
    header=struct.pack('<8I',0xfeedfacf,0x100000c,0,2,2,len(segment)+len(thread),0,0)
    macho=header+segment+thread;macho+=bytes(4096-len(macho));macho+=code
    # Minimal structurally valid ADT, intentionally no handset model or OS profile.
    tree=node('fixture-root',[('model',b'QEMU synthetic handoff probe\0')],
              [node('chosen',[('fixture-kind',b'diagnostic-only\0')],[node('memory-map',[('RAMDisk',bytes(16))] if mode!='none' else [])])])
    expected=b'';initrd=b''
    if mode=='raw':initrd=expected=bytes((i*13+7)&255 for i in range(4097))
    if mode=='packed':
        first=bytes((i*7+23)&255 for i in range(4096));last=bytes((i*11+19)&255 for i in range(4096))
        expected=first+bytes(8192)+last
        initrd=struct.pack('<8sIIQQQQQQ',b'DBRDISK1',1,4096,16384,2,0,4096,12288,4096)+first+last
    return macho,tree,initrd,expected


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ramdisk-mode',choices=['none','raw','packed'],default='none');args=parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    parent=ROOT/'artifacts/handoff-fixture-qemu'
    parent.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=stamp+'-',dir=parent))
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
    for name in ['darwin_handoff_entry.S','darwin_handoff_kernel.c','darwin_handoff.ld']:
        path=ROOT/'scripts/fixtures'/name;relative=path.relative_to(ROOT);data=path.read_bytes()
        target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        inputs.append(dict(path=str(relative),sha256=sha(data)))
    macho,tree,initrd,expected=synthetic_images(out,snapshot,args.ramdisk_mode)
    (out/'build.log').rename(out/'receiver-build.log')
    (out/'commands.json').rename(out/'receiver-commands.json')
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

    command = ['build', '-p', 'RaphaelTestPkg/HandoffFixture.dsc', '-a', 'AARCH64',
               '-b', 'DEBUG', '-t', 'CLANGPDB', '-n', '4']
    record(command)
    with (out / 'build.log').open('xb') as log:
        subprocess.run(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    binary = out / 'Build/RaphaelHandoffFixture/DEBUG_CLANGPDB/AARCH64'
    images = {}
    for name, subsystem in [('DarwinBoot', 'IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER'),
                            ('HandoffFixture', 'IMAGE_SUBSYSTEM_EFI_APPLICATION')]:
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
    shutil.copyfile(binary / 'HandoffFixture.efi', boot / 'BOOTAA64.EFI')
    shutil.copyfile(binary / 'DarwinBoot.efi', esp / 'DarwinBoot.efi')
    target=esp/'EFI/UniXNU';target.mkdir(parents=True)
    (target/'probe.macho').write_bytes(macho);(target/'probe.macho.adt').write_bytes(tree)
    if initrd:
        (target/'probe.ramdisk').write_bytes(initrd);(target/'expected.bin').write_bytes(expected)
    config=target/'unixnu.toml'
    config.write_text('version = 1\n[boot]\ntimeout = 0\n[kits]\nautoload = false\n[[entry]]\nid = "synthetic-probe"\ntitle = "Synthetic handoff probe"\ntype = "xnu"\npath = "probe.macho"\n'+('initrd = "probe.ramdisk"\n' if initrd else ''))
    esp_before={str(p.relative_to(esp)):sha(p.read_bytes()) for p in esp.rglob('*') if p.is_file()}
    shutil.copyfile('/usr/share/AAVMF/AAVMF_VARS.fd', out / 'vars.fd')
    firmware = {name: dict(path='/usr/share/AAVMF/' + name, sha256=sha(Path('/usr/share/AAVMF', name).read_bytes()))
                for name in ['AAVMF_CODE.fd', 'AAVMF_VARS.fd']}
    command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a57', '-m', '512',
               '-semihosting-config','enable=on,target=native','-nographic', '-monitor', 'none', '-no-reboot', '-net', 'none',
               '-drive', 'if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/AAVMF/AAVMF_CODE.fd',
               '-drive', 'if=pflash,format=raw,unit=1,file=' + str(out / 'vars.fd'),
               '-drive', 'if=none,id=esp,format=raw,readonly=on,file=fat:' + str(esp),
               '-device', 'virtio-blk-device,drive=esp']
    record(command)
    serial = out / 'serial.log'
    timed_out = False
    with serial.open('xb') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    raw = serial.read_text(errors='replace')
    esp_after={str(p.relative_to(esp)):sha(p.read_bytes()) for p in esp.rglob('*') if p.is_file()}
    checks=re.findall(r'HANDOFF_(?:PASS|FAIL) [^\r\n]*',raw)
    passed=('HANDOFF_RECEIVER_OK' in raw and 'HANDOFF_FAIL' not in raw and 'HANDOFF_FIXTURE_FAIL' not in raw
            and esp_before==esp_after and len(checks)==(25 if initrd else 22) and not timed_out and process.returncode==0)
    report=dict(passed=passed,host_build_passed=True,image_structure_passed=True,
                handset_executed=False,xnu_executed=False,valid_synthetic_macho_supplied=True,
                exit_boot_services_observed=passed,kernel_branch_observed=passed,os_profile_selected=False,
                source_revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
                revisions=revisions,source_inputs=inputs,runner_sha256=sha(Path(__file__).read_bytes()),
                images=images,emulator_firmware=firmware,check_count=len(checks),checks=checks,
                macho=dict(bytes=len(macho),sha256=sha(macho),virtual_base='0xffff000000200000',segment_bytes=0x20000,window_bytes=0x10000000),
                ramdisk_mode=args.ramdisk_mode,initrd=dict(bytes=len(initrd),sha256=sha(initrd)),expected_ramdisk=dict(bytes=len(expected),sha256=sha(expected)),
                esp_unchanged=esp_before==esp_after,esp_files=esp_before,
                adt=dict(bytes=len(tree),sha256=sha(tree),kind='minimal synthetic tree without hardware resources'),
                config_sha256=sha(config.read_bytes()),timeout=timed_out,qemu_returncode=process.returncode,
                limits=['AAVMF supplies CPU, memory map, filesystem, timer and runtime services',
                        'Freestanding synthetic receiver only, never an XNU kernel or selected OS ABI profile',
                        'No handset execution or phone 256MiB memory ownership claim'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=passed, checks=len(checks), timeout=timed_out)))
    print(out)
    assert passed, raw[-6500:]


if __name__ == '__main__':
    main()
