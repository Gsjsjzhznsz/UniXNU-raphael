#!/usr/bin/env python3
"""Build diagnostic/platform libraries through pinned EDK II BaseTools."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['diag', 'memory-contract'], default='diag')
    args = parser.parse_args()
    name = 'RaphaelDiag' if args.platform == 'diag' else 'RaphaelMemoryContract'
    dsc = 'RaphaelDiag' if args.platform == 'diag' else 'MemoryContract'
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / ('artifacts/edk2-' + args.platform) / stamp
    conf = out / 'Conf'
    conf.mkdir(parents=True, exist_ok=False)
    core = ROOT / 'sources/mu_basecore'
    tools = core / 'BaseTools'
    for name in ['target', 'tools_def', 'build_rule']:
        shutil.copyfile(tools / 'Conf' / (name + '.template'), conf / (name + '.txt'))
    clang_dir = out / 'toolchain'
    clang_dir.mkdir()
    for name in ['clang', 'clang++', 'lld-link', 'llvm-lib', 'llvm-objcopy']:
        target = shutil.which(name)
        assert target, name
        (clang_dir / name).symlink_to(target)
    env = dict(os.environ, WORKSPACE=str(out), EDK_TOOLS_PATH=str(tools), CONF_PATH=str(conf),
               PACKAGES_PATH=f'{ROOT / "UniXNU-raphael/package/firmware"}:{core}', PYTHON_COMMAND='python3',
               CLANG_BIN=str(clang_dir) + '/', SOURCE_DATE_EPOCH='1793088000',
               PATH=f'{tools / "BinWrappers/PosixLike"}:{tools / "Source/C/bin"}:' + os.environ['PATH'])
    command = ['build', '-p', 'RaphaelPkg/' + dsc + '.dsc', '-a', 'AARCH64', '-b', 'DEBUG', '-t', 'CLANGPDB', '-n', '4']
    with (out / 'build.log').open('xb') as log:
        result = subprocess.run(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
    report = dict(command=command, returncode=result.returncode,
                  core_revision=subprocess.check_output(['git', '-C', str(core), 'rev-parse', 'HEAD'], text=True).strip(),
                  host_build_only=True, handset_executed=False)
    image = out / ('Build/' + name + '/DEBUG_CLANGPDB/AARCH64/' + name + '.efi')
    if image.is_file():
        report.update(image=str(image), sha256=hashlib.sha256(image.read_bytes()).hexdigest(), bytes=image.stat().st_size)
    report['libraries'] = [dict(file=str(path.relative_to(out)), bytes=path.stat().st_size,
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                           for path in sorted((out / 'Build').rglob('*.lib'))]
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(out)
    if result.returncode:
        print((out / 'build.log').read_text()[-6500:])
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
