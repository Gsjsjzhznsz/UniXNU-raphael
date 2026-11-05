#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/guo/work/raphael-fresh')


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'artifacts/host-audit' / stamp
    out.mkdir(parents=True, exist_ok=False)
    log = []

    def run(args):
        result = subprocess.run(list(map(str, args)), capture_output=True, cwd=out)
        log.append(dict(command=list(map(str, args)), returncode=result.returncode,
                        stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace')))
        (out / 'commands.json').write_text(json.dumps(log, indent=2))
        if result.returncode:
            raise RuntimeError(f'{args}: {result.stderr.decode(errors="replace")}')
        return result.stdout

    prefix = Path('/opt/unixnu-linux')
    for path in [prefix / 'llvm/bin/clang', prefix / 'CommandLineTools/usr/bin/ld',
                 prefix / 'CommandLineTools/usr/bin/libtool', prefix / 'CommandLineTools/usr/bin/otool',
                 prefix / 'CommandLineTools/usr/libexec/migcom', prefix / 'XcodeDefault.xctoolchain/usr/bin/iig',
                 prefix / 'bin/lzfse', Path('/usr/bin/xcrun'), Path('/usr/bin/plutil'), Path('/usr/bin/codesign')]:
        assert path.is_file() and os.access(path, os.X_OK), path
    (out / 'xnu-smoke.c').write_text('''
#if !__has_builtin(__builtin_xnu_type_signature) || !__has_builtin(__builtin_xnu_type_summary) || !__has_builtin(__builtin_xnu_types_compatible)
#error XNU allocator builtins are absent
#endif
_Static_assert(__builtin_xnu_types_compatible(int, int), "type compatibility");
const char *signature = __builtin_xnu_type_signature(int);
const unsigned long summary = __builtin_xnu_type_summary(int);
int probe(void) { return 42; }
''')
    run([prefix / 'llvm/bin/clang', '--version'])
    run([prefix / 'CommandLineTools/usr/bin/clang', '-target', 'arm64-apple-ios17.0', '-ffreestanding', '-Wall', '-Werror', '-c', out / 'xnu-smoke.c', '-o', out / 'xnu-smoke.o'])
    run([prefix / 'CommandLineTools/usr/bin/ld', '-r', '-arch', 'arm64', '-o', out / 'xnu-linked.o', out / 'xnu-smoke.o'])
    run([prefix / 'CommandLineTools/usr/bin/libtool', '-static', '-o', out / 'libsmoke.a', out / 'xnu-linked.o'])
    run([prefix / 'CommandLineTools/usr/bin/otool', '-hv', out / 'xnu-linked.o'])
    run(['file', out / 'xnu-smoke.o', out / 'xnu-linked.o', out / 'libsmoke.a'])
    (out / 'lzfse-input').write_bytes(bytes(range(256)) * 50)
    run([prefix / 'bin/lzfse', '-encode', '-i', out / 'lzfse-input', '-o', out / 'lzfse-encoded'])
    run([prefix / 'bin/lzfse', '-decode', '-i', out / 'lzfse-encoded', '-o', out / 'lzfse-decoded'])
    assert (out / 'lzfse-input').read_bytes() == (out / 'lzfse-decoded').read_bytes()
    required = ['clang', 'lld-link', 'llvm-readobj', 'llvm-objcopy', 'dtc', 'fdtget', 'fdtput', 'iasl', 'nasm', 'aarch64-linux-gnu-gcc']
    import shutil
    assert all(shutil.which(name) for name in required), required
    lock = dict(date_utc=dt.datetime.now(dt.timezone.utc).isoformat(), sources=[])
    for name in ['UniXNU', 'Mu-Silicium', 'mu_basecore', 'Xiaomi_Kernel_OpenSource']:
        path = ROOT / 'sources' / name
        revision = run(['git', '-C', path, 'rev-parse', 'HEAD']).decode().strip()
        remote = run(['git', '-C', path, 'remote', 'get-url', 'origin']).decode().strip()
        lock['sources'].append(dict(name=name, revision=revision, remote=remote))
    lock['sources'].append(dict(name='DarwinBoot', revision=run(['git', '-C', ROOT / 'sources/UniXNU/drivers/DarwinBoot', 'rev-parse', 'HEAD']).decode().strip(), remote='https://github.com/UniXNU/DarwinBoot.git'))
    (ROOT / 'sources.lock.json').write_text(json.dumps(lock, indent=2) + '\n')
    sums = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out / 'SHA256.json').write_text(json.dumps(sums, indent=2))
    print('PASS: patched XNU builtins; arm64 Mach-O compile/relocatable link/archive; LZFSE roundtrip. Not a complete XNU build.')
    print(out)


if __name__ == '__main__':
    main()
