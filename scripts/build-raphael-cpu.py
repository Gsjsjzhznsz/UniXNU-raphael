#!/usr/bin/env python3
"""Compile the independent CPU implementation using this XNU's actual ABI."""
import hashlib,json,os,struct,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if os.environ.get('XNU_ARMCPU')!='1':
 print('RaphaelBootCpu: disabled by the selected configuration');raise SystemExit(0)
source=Path(os.environ['RAPHAEL_SOC_SOURCE'])/'kits/Sm8150Platform/RaphaelBootCpu.cpp'
record=json.loads((root/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
out=root/'build/armcpu';out.mkdir(parents=True,exist_ok=True)
# The fixed backend uses this archive path as its CPU provider integration slot.
# No object from the upstream ArmCpu repository is copied or linked.
obj=out/'RaphaelBootCpu.o';command=[];args=record['arguments'];i=0
while i<len(args):
 value=args[i]
 if value==record['file']:command.append(str(source))
 elif value=='-o':command.extend(['-o',str(obj)]);i+=1
 elif value=='-Xclang' and args[i+1].startswith('-W'):i+=1
 elif not value.startswith('-W'):command.append(value)
 i+=1
command.extend(['-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-c99-designator','-Wno-reorder-init-list','-Wno-deprecated-enum-enum-conversion','-Wno-unnecessary-virtual-specifier','-I',str(root/'.cache/xnu-work/osfmk')])
(out/'compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
(out/'RaphaelBootCpu.cpp').write_bytes(source.read_bytes())
(out/'RaphaelGicLocal.h').write_bytes((source.parent/'RaphaelGicLocal.h').read_bytes())
result=subprocess.run(command,cwd=record['directory'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/'compile.log').write_text(result.stdout)
if result.returncode:raise SystemExit(result.stdout[-4000:])
raw=obj.read_bytes();assert struct.unpack_from('<4I',raw)==(0xfeedfacf,0x100000c,0,1)
archive=out/'libArmCpu.a';archive.unlink(missing_ok=True)
objects=[obj]
if os.environ.get('RAPHAEL_NATIVE_DIAGNOSTIC')=='1':
 asm=source.parent/'RaphaelNativeReturn.S';extra=out/'RaphaelNativeReturn.o'
 cmd=['xcrun','clang','-target','arm64-apple-ios17.0','-c',str(asm),'-o',str(extra)]
 if os.environ.get('RAPHAEL_HANDSET_UFS')=='1':cmd += ['-DRAPHAEL_HANDSET_UFS=1']
 subprocess.run(cmd,check=True);objects.append(extra)
 (out/'RaphaelNativeReturn.S').write_bytes(asm.read_bytes())
 diagnostic=source.parent/'RaphaelDiagnosticWatchdog.cpp';diagnostic_obj=out/'RaphaelDiagnosticWatchdog.o'
 diagnostic_cmd=[str(diagnostic) if v==str(source) else str(diagnostic_obj) if v==str(obj) else v for v in command]
 watchdog_bind=root/'scripts/bind-raphael-watchdog.py'
 handset=os.environ.get('RAPHAEL_HANDSET_UFS')=='1'
 if handset:
  watchdog_args=['python3',str(watchdog_bind),'--candidate',os.environ['RAPHAEL_STORAGE_CANDIDATE'],'--out',str(out)]
  subprocess.run(watchdog_args,check=True)
  diagnostic_cmd+=['-DRAPHAEL_HANDSET_UFS=1','-I'+str(out)]
  if os.environ.get('RAPHAEL_UFS_CONSOLE_LOG_REPORT'):diagnostic_cmd+=['-DRAPHAEL_UFS_CONSOLE_LOG=1']
 subprocess.run(diagnostic_cmd,cwd=record['directory'],check=True)
 if handset:
  subprocess.run([*watchdog_args,'--object',str(diagnostic_obj)],check=True)
  objects += [out/'RaphaelDiagnosticWatchdog.late.o',out/'original-watchdog-bindings.o']
 else:objects.append(diagnostic_obj)
 import shutil
 disassembly=subprocess.check_output([shutil.which('llvm-objdump') or '/usr/bin/llvm-objdump','-d',str(diagnostic_obj)],text=True)
 (out/'diagnostic-watchdog-disassembly.txt').write_text(disassembly)
 assert disassembly.count('CNTPCT_EL0')>=3, 'Begin, pet and end must each emit a real physical-counter read'
 (out/diagnostic.name).write_bytes(diagnostic.read_bytes())
 (out/'RaphaelDiagnosticWatchdog.h').write_bytes((source.parent/'RaphaelDiagnosticWatchdog.h').read_bytes())
if os.environ.get('RAPHAEL_HANDSET_UFS')=='1':
 pmgr=source.parent/'RaphaelPmgrCompat.cpp';pmgr_obj=out/'RaphaelPmgrCompat.o'
 pmgr_cmd=[str(pmgr) if v==str(source) else str(pmgr_obj) if v==str(obj) else v for v in command]
 subprocess.run(pmgr_cmd,cwd=record['directory'],check=True);objects.append(pmgr_obj)
 (out/pmgr.name).write_bytes(pmgr.read_bytes())
subprocess.run(['xcrun','ar','rcs',str(archive),*[str(x) for x in objects]],check=True)
(out/'provenance.json').write_text(json.dumps(dict(implementation='independent RaphaelBootCpu',source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),upstream_armcpu_linked=False),indent=2)+'\n')
print('RaphaelBootCpu: real XNU ABI -Werror ARM64 object and archive build passed')
