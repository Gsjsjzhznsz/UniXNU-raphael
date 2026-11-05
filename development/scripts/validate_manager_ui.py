#!/usr/bin/env python3
"""Run actual framebuffer transaction under ASan/UBSan with failure recovery."""
import datetime as dt,json,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 parent=ROOT/'artifacts/manager-ui-host';parent.mkdir(exist_ok=True,parents=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));core=ROOT/'sources/mu_basecore/MdePkg/Include'
 inputs=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelManagerUiLib/ManagerUi.c',ROOT/'scripts/fixtures/manager_ui_host.c']
 cmd=['gcc','-O1','-g','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(core),'-I'+str(core/'AArch64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include')]+[str(p) for p in inputs]+['-o',str(out/'host')]
 p=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
 p=subprocess.run([str(out/'host')],capture_output=True);(out/'execution.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr).decode()
 cases=[x[5:] for x in p.stdout.decode().splitlines() if x.startswith('PASS ')];assert p.stdout.decode().splitlines()[-1]=='MANAGER_UI_HOST_OK '+str(len(cases))
 inputs+=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/Library/RaphaelManagerUiLib.h',Path(__file__)]
 report=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,address_sanitizer=True,undefined_behavior_sanitizer=True,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],handset_executed=False)
 for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/manager-ui-host.json']:p.write_text(json.dumps(report,indent=2)+'\n')
 print(len(cases),'actual C/ASan/UBSan checks passed');print(out)
if __name__=='__main__':main()
