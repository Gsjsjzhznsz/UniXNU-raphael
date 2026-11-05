#!/usr/bin/env python3
"""Compile frozen simultaneous-sample C; test distinct DRAM/cache and inspect AArch64 object."""
import datetime as dt
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parent = ROOT / 'artifacts/ram-alias-host'
    parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'), dir=parent))
    snapshot = out/'snapshot'
    package = Path('UniXNU-raphael/package/firmware/RaphaelPkg')
    fixture = Path('scripts/fixtures/ram_alias_host.c')
    engine = package/'Library/RaphaelRamAliasLib/RamAlias.c'
    paths = [ROOT/fixture, ROOT/engine, ROOT/package/'Library/RaphaelRamAliasLib/RaphaelRamAliasLib.inf',
             ROOT/package/'RaphaelPkg.dec', ROOT/package/'RamAlias.dsc', ROOT/'sources.lock.json', ROOT/'toolchain.lock.json', Path(__file__)]
    paths += [p for p in (ROOT/package/'Include').rglob('*') if p.is_file()]
    paths = sorted(set(paths))
    inputs = [dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in paths]
    for source in paths:
        dest = snapshot/source.relative_to(ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(source.read_bytes())
    for item in inputs: assert sha(snapshot/item['path']) == item['sha256']
    lock = json.loads((snapshot/'sources.lock.json').read_text())
    core_revision = next(x['revision'] for x in lock['sources'] if x['name']=='mu_basecore')
    core = ROOT/'sources/mu_basecore'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=core,text=True).strip()==core_revision
    assert not subprocess.check_output(['git','status','--porcelain=v1'],cwd=core,text=True).strip()
    inc = core/'MdePkg/Include'
    package_inc = snapshot/package/'Include'
    command = ['gcc', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fshort-wchar',
               '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
               '-I'+str(inc), '-I'+str(inc/'X64'), '-I'+str(package_inc),
               str(snapshot/fixture), str(snapshot/engine), '-o', str(out/'host')]
    report = dict(passed=False, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), command=command,
                  source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  source_worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True)),
                  source_binding='Frozen source bytes, headers and runner hashes; source_head alone is insufficient',
                  basecore_revision=core_revision, source_inputs=inputs,
                  handset_executed=False, sec_linked=False, candidate_ram_registered=False)
    try:
        for label, cmd in [('build',command), ('execution',[str(out/'host')])]:
            result = subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=300)
            (out/(label+'.log')).write_bytes(result.stdout+result.stderr)
            report[label+'_exit_code'] = result.returncode
            if result.returncode: raise RuntimeError((result.stdout+result.stderr).decode()[-6000:])
        lines = result.stdout.decode().splitlines()
        cases = [line[5:] for line in lines if line.startswith('PASS ')]
        assert lines[-1] == f'RAM_ALIAS_HOST_OK {len(cases)}'
        tool = Path('/usr/bin/clang-18')
        locked = json.loads((snapshot/'toolchain.lock.json').read_text())
        tool_pin = next(x for x in locked['binaries'] if x['path']==str(tool))
        assert sha(tool.resolve()) == tool_pin['sha256']
        native = out/'RamAlias.o'
        native_command = [str(tool), '--target=aarch64-none-elf', '-march=armv8-a', '-mgeneral-regs-only',
                          '-mstrict-align', '-ffreestanding', '-fshort-wchar', '-fno-stack-protector',
                          '-fno-builtin', '-fno-common', '-fstack-usage', '-Wframe-larger-than=1024',
                          '-O2', '-Wall', '-Wextra', '-Werror', '-I'+str(inc), '-I'+str(inc/'AArch64'),
                          '-I'+str(package_inc), '-c', str(snapshot/engine), '-o', str(native)]
        n = subprocess.run(native_command,cwd=ROOT,capture_output=True,timeout=60)
        (out/'aarch64-build.log').write_bytes(n.stdout+n.stderr)
        report['aarch64_compile'] = dict(command=native_command,exit_code=n.returncode,compiler_sha256=tool_pin['sha256'])
        if n.returncode: raise RuntimeError((n.stdout+n.stderr).decode())
        inspect = subprocess.run(['llvm-readobj-18','--file-headers',str(native)],capture_output=True,check=True)
        (out/'aarch64-structure.log').write_bytes(inspect.stdout+inspect.stderr)
        assert b'Arch: aarch64' in inspect.stdout and b'Type: Relocatable' in inspect.stdout
        unresolved = subprocess.check_output(['llvm-nm-18','-u',str(native)])
        assert not unresolved.strip(), unresolved
        report['aarch64_compile'].update(object_sha256=sha(native),object_bytes=native.stat().st_size,
            undefined_symbols=0,format='AArch64 ELF relocatable object, not a bootable image',
            abi_assertions=2, stack_usage=(out/'RamAlias.su').read_text())
        # Build the actual INF/DEC/DSC using pinned Mu Basecore. This is a
        # standalone library archive and still supplies no bootable firmware.
        tools = core/'BaseTools'
        conf = out/'Conf'; conf.mkdir()
        for name in ['target','tools_def','build_rule']:
            shutil.copyfile(tools/'Conf'/(name+'.template'),conf/(name+'.txt'))
        compiler_dir = out/'toolchain'; compiler_dir.mkdir()
        for name in ['clang','clang++','lld-link','llvm-lib','llvm-objcopy']:
            target = shutil.which(name+'-18') or shutil.which(name)
            assert target, name
            (compiler_dir/name).symlink_to(target)
        assert (compiler_dir/'clang').resolve()==tool.resolve()
        env = dict(os.environ, WORKSPACE=str(out), EDK_TOOLS_PATH=str(tools), CONF_PATH=str(conf),
                   PACKAGES_PATH=str(snapshot/'UniXNU-raphael/package/firmware')+':'+str(core), PYTHON_COMMAND='python3',
                   CLANG_BIN=str(compiler_dir)+'/', SOURCE_DATE_EPOCH='1793088000',
                   PATH=str(tools/'BinWrappers/PosixLike')+':'+str(tools/'Source/C/bin')+':'+os.environ['PATH'])
        edk2_command = ['build','-p','RaphaelPkg/RamAlias.dsc','-a','AARCH64','-b','DEBUG','-t','CLANGPDB','-n','2']
        with (out/'edk2-build.log').open('xb') as stream:
            e = subprocess.run(edk2_command,cwd=out,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
        report['edk2_compile'] = dict(command=edk2_command,exit_code=e.returncode,basecore_revision=core_revision,
            bootable_image=False,fd_created=False)
        if e.returncode: raise RuntimeError((out/'edk2-build.log').read_text()[-6000:])
        archives = sorted((out/'Build').rglob('*.lib')); assert archives
        archive_records=[]
        for archive in archives:
            members = subprocess.check_output(['llvm-ar-18','t',str(archive)],text=True).splitlines()
            assert members, 'Empty EDK II archive'
            inspected=[]
            for member in members:
                data = subprocess.check_output(['llvm-ar-18','p',str(archive),member])
                assert data[:4] == b'BC\xc0\xde', 'CLANGPDB library member must be LLVM bitcode'
                ir = subprocess.run(['llvm-dis-18','-o','-'],input=data,capture_output=True,check=True).stdout
                triple = next(line.decode() for line in ir.splitlines() if line.startswith(b'target triple ='))
                assert triple.startswith('target triple = "aarch64-unknown-windows-msvc'), triple
                inspected.append(dict(name=member,sha256=hashlib.sha256(data).hexdigest(),target=triple))
            unresolved = subprocess.check_output(['llvm-nm-18','-u',str(archive)]).decode()
            assert not any(line.strip().startswith('U ') for line in unresolved.splitlines()), unresolved
            archive_records.append(dict(path=str(archive.relative_to(out)),bytes=archive.stat().st_size,sha256=sha(archive),
                                        format='CLANGPDB LLVM bitcode library; no final firmware link',members=inspected))
        report['edk2_compile']['archives']=archive_records
        report['edk2_compile']['build_log_sha256']=sha(out/'edk2-build.log')
        for item in inputs:
            assert sha(snapshot/item['path']) == item['sha256']
            assert sha(ROOT/item['path']) == item['sha256'], 'Live source changed during build; retain logs and rerun'
        report.update(passed=True, case_count=len(cases), cases=cases, executable_sha256=sha(out/'host'),
                      address_sanitizer=True, undefined_behavior_sanitizer=True, abi_assertions=4,
                      separate_cache_and_dram=True, full_window_pages_modelled=65536,
                      compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
                      limits=['Synthetic addresses and sample storage; no phone memory access.',
                              'Callback failures return normally; no synchronous SEC exception path tested.',
                              'Only page head/tail sample aliases covered; no allocator or hidden DMA ownership proven.'])
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(out)
    print(report['case_count'], 'actual C/ASan/UBSan checks passed; AArch64 object inspected')
if __name__ == '__main__': main()
