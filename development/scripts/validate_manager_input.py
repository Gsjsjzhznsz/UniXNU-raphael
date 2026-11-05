#!/usr/bin/env python3
"""Actual bounded input C with ASan/UBSan and explicit synthetic-key evidence."""
import datetime as dt,json,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 parent=ROOT/'artifacts/manager-input-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 core=ROOT/'sources/mu_basecore/MdePkg/Include'
 paths=[ROOT/'scripts/fixtures/manager_input_host.c',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelManagerUiLib/Input.c']
 cmd=['gcc','-O1','-g','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),*[str(p) for p in paths],'-o',str(out/'host')]
 x=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,x.stderr.decode()
 x=subprocess.run([str(out/'host')],capture_output=True);(out/'execution.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr).decode()
 cases=[l[5:] for l in x.stdout.decode().splitlines() if l.startswith('PASS ')];assert x.stdout.decode().splitlines()[-1]=='MANAGER_INPUT_HOST_OK '+str(len(cases))
 paths+=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/Library/RaphaelManagerInputLib.h',Path(__file__)]
 result=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,address_sanitizer=True,undefined_behavior_sanitizer=True,handset_executed=False,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths])
 for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/manager-input-host.json']:p.write_text(json.dumps(result,indent=2)+'\n')
 print(len(cases),'actual input wrapper C/ASan/UBSan checks');print(out)
if __name__=='__main__':main()
