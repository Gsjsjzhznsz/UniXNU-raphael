#!/usr/bin/env python3
"""Exercise installed native XNU tools without rewriting source/version locks."""
import datetime as dt,json,os,struct,subprocess
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 out=ROOT/'artifacts/native-toolchain'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
 prefix=Path('/opt/unixnu-linux');clt=prefix/'CommandLineTools/usr';commands=[]
 def run(args,stdin=None):
  c=[str(v) for v in args];x=subprocess.run(c,cwd=out,input=stdin,capture_output=True)
  commands.append(dict(command=c,returncode=x.returncode,stdout=x.stdout.decode(errors='replace'),stderr=x.stderr.decode(errors='replace')))
  (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  assert x.returncode==0,(c,x.stderr.decode());return x.stdout
 tools=[prefix/'llvm/bin/clang',*[clt/'bin'/n for n in ['clang','ld','libtool','otool','xnu-host-cc']],clt/'libexec/migcom',prefix/'XcodeDefault.xctoolchain/usr/bin/iig',prefix/'bin/lzfse',Path('/usr/bin/xcrun')]
 assert all(p.is_file() and os.access(p,os.X_OK) for p in tools)
 (out/'probe.c').write_text('\n#if !__has_builtin(__builtin_xnu_type_signature) || !__has_builtin(__builtin_xnu_type_summary) || !__has_builtin(__builtin_xnu_types_compatible)\n#error Missing XNU builtins\n#endif\n_Static_assert(__builtin_xnu_types_compatible(int,int),"compatible");\nconst char *signature=__builtin_xnu_type_signature(int);\nconst unsigned long summary=__builtin_xnu_type_summary(int);\nint probe(void){return 42;}\n')
 version=run([prefix/'llvm/bin/clang','--version']).decode()
 run([clt/'bin/clang','-target','arm64-apple-ios17.0','-ffreestanding','-Wall','-Werror','-c','probe.c','-o','probe.o'])
 run([clt/'bin/ld','-r','-arch','arm64','-o','linked.o','probe.o'])
 run([clt/'bin/libtool','-static','-o','libprobe.a','linked.o'])
 for file in ['probe.o','linked.o']:
  magic,cpu,sub,typ=struct.unpack_from('<4I',(out/file).read_bytes());assert (magic,cpu,typ)==(0xfeedfacf,0x100000c,1)
 assert (out/'libprobe.a').read_bytes().startswith(b'!<arch>\n')
 run([clt/'bin/otool','-hv','linked.o'])
 defs=b'subsystem NativeProbe 42000;\ntype port_t = MACH_MSG_TYPE_COPY_SEND;\ntype word_t = MACH_MSG_TYPE_INTEGER_32;\nroutine ping(server: port_t; value: word_t);\n'
 (out/'probe.defs').write_bytes(defs)
 run([clt/'libexec/migcom','-user','probe-user.c','-server','probe-server.c','-header','probe-user.h','-sheader','probe-server.h'],stdin=defs)
 assert all((out/n).stat().st_size>0 for n in ['probe-user.c','probe-server.c','probe-user.h','probe-server.h'])
 assert b'42000' in (out/'probe-user.c').read_bytes() and b'NativeProbe' in (out/'probe-server.c').read_bytes()
 run([clt/'bin/xnu-host-cc','-x','c','-c','-o','host.o','-'],stdin=b'int host_probe(void){return 0;}\n')
 assert (out/'host.o').read_bytes().startswith(b'\x7fELF')
 data=bytes(range(256))*50;(out/'plain').write_bytes(data)
 run([prefix/'bin/lzfse','-encode','-i','plain','-o','packed']);run([prefix/'bin/lzfse','-decode','-i','packed','-o','roundtrip'])
 assert (out/'roundtrip').read_bytes()==data
 result=dict(passed=True,artifact_directory=str(out.relative_to(ROOT)),clang_version=version,patched_xnu_allocator_builtins=True,arm64_macho_compile_relocatable_link_archive=True,mig_generated=True,host_elf_compile=True,lzfse_roundtrip=True,iig_present_only=True,iig_actual_interface_compilation_verified=False,complete_xnu_build_verified=False,handset_executed=False,tools=[dict(path=str(p),sha256=sha(p.read_bytes())) for p in tools],artifacts=[dict(path=str(p.relative_to(out)),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(out.iterdir()) if p.is_file()],validator_sha256=sha(Path(__file__).read_bytes()))
 for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/native-toolchain-host.json']:p.write_text(json.dumps(result,indent=2)+'\n')
 print('Native XNU builtins, ARM64 Mach-O compile/link/archive, MIG generation, host ELF and LZFSE passed');print(out)
if __name__=='__main__':main()
