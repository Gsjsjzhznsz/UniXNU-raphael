#!/usr/bin/env python3
"""Verify the pinned, unchanged loader ABI and refusal/lifecycle source anchors."""
import json
import subprocess
from entry_probe import ROOT, sha
from source_pins import locked_revision

SPECS = {
    'sources/mu_basecore': (
        'cfb93724a06ff86ff5ba971413368a7809ee42a5', {
            'MdePkg/Library/UefiLib/UefiLibPrint.c': ['ASSERT (Console != NULL)', 'InternalPrint', 'gST->ConOut'],
            'MdePkg/Include/Protocol/SimpleTextOut.h': ['EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL', 'EFI_TEXT_STRING'],
            'MdeModulePkg/Core/Dxe/Image/Image.c': ['CoreLoadImage', 'CoreStartImage', 'CoreUnloadImage'],
            'MdePkg/Library/DxeServicesLib/DxeServicesLib.c': ['GetSectionFromAnyFv'],
        }),
    'sources/UniXNU/drivers/DarwinBoot': (
        '3325e352d7df68a9f9ad74832ed94a6acbbd7390', {
            'DarwinBootPkg/Driver/DarwinBoot.inf': ['UEFI_DRIVER', 'DarwinBootEntry', 'UniXNULoader'],
            'DarwinBootPkg/Driver/DarwinBoot.c': ['ParseKernel', 'EFI_INVALID_PARAMETER', 'EFI_BAD_BUFFER_SIZE',
                'DarwinCurrentEl () != 4', 'DarwinEnter (', 'EFI_ALREADY_STARTED', 'Loaded->Unload = Unload'],
            'DarwinBootPkg/Driver/PackedRamdisk.h': ['RamdiskLayout', 'DBRDISK1', 'SIZE_MAX_LOGICAL'],
            'DarwinBootPkg/Driver/Entry.S': ['DarwinCurrentEl', 'DarwinEnter'],
        }),
    'sources/UniXNU': (
        locked_revision('UniXNU'), {
            'package/UniXNUPkg/Include/Protocol/UniXNULoader.h': ['UNIXNU_LOADER_REVISION', 'UNIXNU_LOADER_BOOT_REQUEST'],
            'package/UniXNUPkg/Library/UniXNULib/Boot.c': ['RunXnu', 'Loader->Boot', 'Request.Volume', 'UniXNUBootEntry'],
        }),
}


def main():
    sources = []
    for repository, (revision, files) in SPECS.items():
        root = ROOT / repository
        assert subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() == revision
        for name, markers in files.items():
            raw = subprocess.check_output(['git', '-C', str(root), 'show', revision + ':' + name])
            assert raw == (root / name).read_bytes(), name
            lines = raw.decode().splitlines()
            anchors = {marker: [i + 1 for i, line in enumerate(lines) if marker in line] for marker in markers}
            assert all(anchors.values()), (name, anchors)
            sources.append(dict(repository=repository, revision=revision, path=name, sha256=sha(raw), anchors=anchors))
    out = ROOT / 'UniXNU-raphael/evidence/darwin-source-audit.json'
    out.write_text(json.dumps(dict(passed=True, primary_sources=sources, os_profile_selected=False,
        hardware_parameters_used=False, upstream_modified=False,
        scope='Fixed v2 loader protocol and negative boot request checks; no XNU or handset handoff claim'), indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    main()
