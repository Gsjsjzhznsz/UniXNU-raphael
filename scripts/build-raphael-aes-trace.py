#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Rebuild the existing SoftwareAES archive with scoped original-result logs."""
from pathlib import Path
import json,os,subprocess
root=Path(__file__).resolve().parents[1]
out=root/'build/software-aes'
source=root/'drivers/SoftwareAES/NativeAES.cpp'
patch=Path(os.environ['RAPHAEL_WORKSPACE'])/'UniXNU-raphael/patches/software-aes/raphael-fairplay-result-trace.patch'
applied=subprocess.run(['patch','--quiet','--output',str(out/'NativeAES.fairplay.cpp'),str(source),str(patch)],capture_output=True,text=True)
if applied.returncode:raise RuntimeError(applied.stdout+applied.stderr)
command=json.loads((out/'compile-command.json').read_text())
assert command.count(str(source))==1
command[command.index(str(source))]=str(out/'NativeAES.fairplay.cpp')
command+=['-I',str(source.parent)]
(out/'fairplay-compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
record=json.loads((root/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
p=subprocess.run(command,cwd=record['directory'],capture_output=True,text=True)
(out/'fairplay-compile.log').write_text(p.stdout+p.stderr)
if p.returncode:raise RuntimeError(p.stdout+p.stderr)
archive=out/'libSoftwareAES.a'
subprocess.run(['xcrun','ar','rcs',str(archive),str(out/'NativeAES.o')],check=True)
print('SoftwareAES: scoped fairplay original-result observer built; AES behavior preserved')
