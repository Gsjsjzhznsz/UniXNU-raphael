#!/usr/bin/env python3
"""Check canonical layout, live source links and official device record; no fetch or device IO."""
import json
from pathlib import Path
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]

def main():
    device = ROOT / 'UniXNU-raphael'
    soc = ROOT / 'UniXNU-sm8150-common'
    required = ['AGENTS.md', 'README.md', '.gitignore', 'board.toml', 'porting.toml',
                '.github/workflows/porting-record.yml', 'feeds.toml', 'configs/raphael_defconfig',
                'dts/raphael.dts', 'patches/xnu/series', 'proprietary-files.txt',
                'package/README.md', 'local.toml.example', 'unixnu.lock',
                'scripts/package.sh', 'scripts/check-packaging.py', '.github/workflows/package.yml',
                'unixnu.local.toml.example', 'docs/PACKAGING.zh-CN.md']
    for name in required:
        assert (device / name).is_file(), name
    for name in ['AGENTS.md', 'README.md', 'soc.toml', 'configs/sm8150.config',
                 'dts/sm8150.dtsi', 'patches/xnu/series', 'kits/Sm8150Platform/RaphaelBootCpu.cpp']:
        assert (soc / name).is_file(), name
    for base in [device, soc]:
        for path in base.rglob('*'):
            if '.cache' in path.parts or '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                assert path.exists(), f'Broken source link: {path}'
    for name in ['RaphaelPayloadHash.h', 'RaphaelReadOnlyExtents.h', 'RaphaelExtentPlan.h',
                 'RaphaelUfsDmaGate.h', 'RaphaelUfsTransport.h', 'RaphaelUfsWritePolicy.h']:
        link = device / 'package/firmware/RaphaelPkg/Include' / name
        assert link.is_symlink() and link.resolve() == soc / 'kits/Sm8150Platform' / name, name
    board = tomllib.loads((device / 'board.toml').read_text())
    assert (device / 'configs' / board['kernel']['defconfig']).is_file()
    assert board['device_tree']['source'] == 'device:dts/raphael.dts'
    # No executable consumer may accidentally use a pre-migration source path.
    stale = ['UniXNU-sm8150-common/' + 'drivers/', 'UniXNU-raphael/' + 'drivers/', 'uefi-' + 'raphael']
    for base in [ROOT / 'scripts', ROOT / 'tests', device / 'scripts']:
        for path in base.rglob('*'):
            if path.suffix not in ['.py', '.c', '.cpp', '.h', '.S', '.sh'] or '__pycache__' in path.parts:
                continue
            assert not any(value in path.read_text() for value in stale), f'Stale consumer: {path}'
    subprocess.run(['python3', str(ROOT / 'sources/UniXNU/scripts/porting-record.py'),
                    'check', '--device', str(device)], check=True)
    subprocess.run(['python3', str(device / 'scripts/check-packaging.py')], check=True)
    print(json.dumps(dict(passed=True, required_device_files=len(required), source_links_checked=True,
                          record_areas=13, network_access=False, handset_io=False), indent=2))

if __name__ == '__main__':
    main()
