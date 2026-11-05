#!/usr/bin/env python3
"""Record interface references and token observations, not binary equivalence."""
import json
from pathlib import Path
import subprocess
from entry_probe import ROOT, sha


def main():
    interface = ROOT / 'sources/abl-reference'
    refs = []
    for relative, needle, interpretation in [
        ('QcomModulePkg/Include/Library/BootLinux.h', '#define PATCHED_KERNEL_HEADER_SIZE', '20-byte uncompressed wrapper interface'),
        ('QcomModulePkg/Library/BootLib/BootLinux.c', 'LinuxKernel ((UINT64)', 'FDT in x0, reserved zero arguments'),
        ('QcomModulePkg/Library/BootLib/BootLinux.c', 'Status = ShutdownUefiBootServices', 'expected original boot-services exit before kernel'),
        ('QcomModulePkg/Library/BootLib/ShutdownServices.c', 'ArmDisableMmu ();', 'expected MMU/cache-off transition'),
        ('QcomModulePkg/Include/Library/BootLinux.h', '#define DT_SIZE_2MB', 'interface guard for original FDT window')]:
        path = interface / relative
        lines = path.read_text().splitlines()
        matches = [i + 1 for i, line in enumerate(lines) if needle in line]
        assert matches
        refs.append(dict(file=relative, file_sha256=sha(path.read_bytes()), lines=matches, purpose=interpretation))
    primary = ROOT / 'sources/Xiaomi_Kernel_OpenSource/Documentation/arm64/booting.txt'
    metadata = json.loads((ROOT / 'UniXNU-raphael/evidence/abl-module-metadata.json').read_text())[0]
    collection = ROOT / 'evidence/private/device/20261027T120325Z'
    files = list((collection / 'abl-extracted').rglob('section1.pe'))
    assert len(files) == 1
    raw = files[0].read_bytes()
    assert sha(raw) == metadata['images'][0]['sha256']
    tokens = []
    for needle in ['UNCOMPRESSED_IMG', 'Shutting Down UEFI Boot Services', 'Kernel Load Address',
                   'linux,initrd-start', 'linux,initrd-end']:
        position = raw.find(needle.encode())
        assert position >= 0
        tokens.append(dict(public_interface_token=needle, file_offset=position))
    report = dict(interface_reference=dict(remote=subprocess.check_output(['git', '-C', str(interface), 'remote', 'get-url', 'origin'], text=True).strip(),
                                          revision=subprocess.check_output(['git', '-C', str(interface), 'rev-parse', 'HEAD'], text=True).strip(),
                                          role='Qualcomm-authored interface code in a third-party mirror; not a handset board port',
                                          binary_source_match=False, files=refs),
                  arm64_protocol_primary=dict(repository='MiCode/Xiaomi_Kernel_OpenSource',
                                              revision='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0',
                                              file=str(primary.relative_to(ROOT / 'sources/Xiaomi_Kernel_OpenSource')),
                                              sha256=sha(primary.read_bytes())),
                  source_device_abl=dict(partition_sha256=metadata['source_partition_sha256'],
                                         pe_sha256=sha(raw), token_observations=tokens),
                  limits=['Matching strings establish interface presence, not complete code equivalence or executed control flow',
                          'Entry probe independently verified actual EL, SCTLR, registers and FDT on this handset',
                          'Original UEFI services and runtime memory ownership are not established by these references'])
    path = ROOT / 'UniXNU-raphael/evidence/handoff-source-references.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(path)


if __name__ == '__main__':
    main()
