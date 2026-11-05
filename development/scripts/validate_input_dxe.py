#!/usr/bin/env python3
"""Execute actual driver, callbacks and filter against synthetic observer memory."""
import datetime as dt,json,subprocess
from entry_probe import ROOT,sha

def main():
    out=ROOT/'artifacts/input-dxe-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
    core=ROOT/'sources/mu_basecore/MdePkg/Include'
    inputs=[ROOT/p for p in ['scripts/fixtures/input_dxe_host.c','UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelKeysLib/Keys.c']]
    command=['gcc','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-fshort-wchar','-fsanitize=address,undefined','-fno-omit-frame-pointer',
      '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),*[str(p) for p in inputs],'-o',str(out/'input-host')]
    b=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(b.stdout+b.stderr);assert b.returncode==0,b.stderr.decode()
    x=subprocess.run([str(out/'input-host')],capture_output=True);(out/'execution.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr).decode()
    cases=[l[5:] for l in x.stdout.decode().splitlines() if l.startswith('PASS ')];assert x.stdout.decode().splitlines()[-1]=='INPUT_DXE_HOST_OK '+str(len(cases))
    inputs+=[ROOT/p for p in ['UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/PmicInputDxe/PmicInput.c','UniXNU-raphael/package/firmware/RaphaelPkg/Include/Library/RaphaelKeysLib.h','UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelDiagnostic.h','UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelInputDxe.h','scripts/validate_input_dxe.py']]
    report=dict(passed=True,case_count=len(cases),cases=cases,command=command,handset_executed=False,asan_ubsan=True,synthetic_observer_mmap_in_host_only=True,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs])
    for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/input-dxe-host.json']:p.write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,cases=len(cases)));print(out)
if __name__=='__main__':main()
