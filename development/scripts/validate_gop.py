#!/usr/bin/env python3
"""Actual GOP library and framebuffer plan under ASan/UBSan; no phone I/O."""
import datetime as dt
import json
import subprocess
from pathlib import Path
from entry_probe import ROOT,sha

def main():
    out=ROOT/'artifacts/gop-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    core=ROOT/'sources/mu_basecore'
    inputs=[ROOT/p for p in ['UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelGopLib/Gop.c',
      'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelFramebufferLib/Framebuffer.c',
      'scripts/fixtures/gop_host.c']]
    generic=core/'MdeModulePkg/Library/FrameBufferBltLib/FrameBufferBltLib.c'
    command=['gcc','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare',
      '-fshort-wchar','-fsanitize=address,undefined','-fno-omit-frame-pointer',
      '-I'+str(core/'MdePkg/Include'),'-I'+str(core/'MdePkg/Include/AArch64'),
      '-I'+str(core/'MdeModulePkg/Include'),'-I'+str(core/'ArmPkg/Include'),
      '-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),*[str(p) for p in inputs],str(generic),'-o',str(out/'gop-host')]
    built=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(built.stdout+built.stderr)
    assert built.returncode==0,built.stderr.decode()
    ran=subprocess.run([str(out/'gop-host')],capture_output=True);(out/'execution.log').write_bytes(ran.stdout+ran.stderr)
    assert ran.returncode==0,(ran.stdout+ran.stderr).decode()
    lines=ran.stdout.decode().splitlines();cases=[line[5:] for line in lines if line.startswith('PASS ')]
    assert lines[-1]=='GOP_HOST_OK '+str(len(cases))
    inputs += [ROOT/p for p in ['UniXNU-raphael/package/firmware/RaphaelPkg/Include/Library/RaphaelGopLib.h',
      'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelFramebuffer.h','UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPixelProbe.h',
      'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelDisplayProbe.h','scripts/validate_gop.py']]
    report=dict(passed=True,kind='actual port GOP plus pinned generic Blt under ASan and UBSan',
      handset_executed=False,case_count=len(cases),cases=cases,command=command,
      source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],
      upstream_inputs=[dict(path=str(generic.relative_to(ROOT)),sha256=sha(generic.read_bytes()))],
      core_revision=subprocess.check_output(['git','-C',str(core),'rev-parse','HEAD'],text=True).strip())
    for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/gop-host.json']:p.write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,cases=len(cases)));print(out)

if __name__=='__main__':main()
