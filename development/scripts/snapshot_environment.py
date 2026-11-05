#!/usr/bin/env python3
"""Record exact source/submodule identities and executable hashes without reinstalling tools."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def main():
    sources = []
    for name in ['UniXNU', 'Mu-Silicium', 'mu_basecore', 'Xiaomi_Kernel_OpenSource', 'abl-reference']:
        path = ROOT / 'sources' / name
        modules = []
        for line in git(path, 'submodule', 'status', '--recursive').splitlines():
            if not line.startswith('-'):
                fields = line.split()
                modules.append(dict(revision=fields[0].lstrip('+'), path=fields[1]))
        sources.append(dict(name=name, remote=git(path, 'remote', 'get-url', 'origin'),
                            revision=git(path, 'rev-parse', 'HEAD'),
                            tracked_changes=git(path, 'status', '--porcelain', '--untracked-files=no'),
                            initialized_submodules=modules))
    (ROOT / 'sources.lock.json').write_text(json.dumps(dict(recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                                                         sources=sources), indent=2) + '\n')
    paths = [Path('/opt/unixnu-linux/llvm/bin/clang'), Path('/opt/unixnu-linux/CommandLineTools/usr/bin/clang'),
             Path('/opt/unixnu-linux/CommandLineTools/usr/bin/ld'), Path('/opt/unixnu-linux/CommandLineTools/usr/bin/libtool'),
             Path('/opt/unixnu-linux/CommandLineTools/usr/bin/xnu-host-cc'), Path('/opt/unixnu-linux/CommandLineTools/usr/libexec/migcom'),
             Path('/opt/unixnu-linux/XcodeDefault.xctoolchain/usr/bin/iig'), Path('/opt/unixnu-linux/bin/lzfse'),
             Path('/usr/bin/xcrun'), Path('/usr/bin/plutil'), Path('/usr/bin/codesign'),
             Path('/usr/bin/clang-18'), Path('/usr/bin/lld-link'), Path('/usr/bin/dtc')]
    binaries = []
    for path in paths:
        raw = path.read_bytes()
        binaries.append(dict(path=str(path), resolved=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    report = dict(recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(), binaries=binaries,
                  clang_version=subprocess.check_output(['/opt/unixnu-linux/llvm/bin/clang', '--version'], text=True),
                  kernel=subprocess.check_output(['uname', '-r'], text=True).strip(),
                  distro=Path('/etc/os-release').read_text(),
                  installed_packages=subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\t${Version}\n',
                    'clang-18', 'lld-18', 'llvm-18', 'device-tree-compiler', 'qemu-system-arm', 'qemu-efi-aarch64',
                    'mtools', 'acpica-tools', 'nasm', 'gcc-aarch64-linux-gnu', 'ripgrep'], text=True).splitlines(),
                  limits='MIG/IIG are present; full XNU compilation and target ABI are not yet verified')
    (ROOT / 'toolchain.lock.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Recorded upstream repositories, initialized submodules, tool hashes and package versions.')


if __name__ == '__main__':
    main()
