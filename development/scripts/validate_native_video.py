#!/usr/bin/env python3
"""Run the actual native GOP/Boot_Video contract with ASan/UBSan. No phone I/O."""
import datetime,json,subprocess
from pathlib import Path
from entry_probe import ROOT

def main():
 out=ROOT/'artifacts/native-video-host'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
 core=ROOT/'sources/mu_basecore'
 inputs=[ROOT/p for p in ['UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/DiagnosticReturnDxe/NativeVideo.c','UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelFramebufferLib/Framebuffer.c','scripts/fixtures/native_video_host.c']]
 cmd=['gcc','-O1','-g','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=address,undefined','-fno-omit-frame-pointer',
  '-I'+str(core/'MdePkg/Include'),'-I'+str(core/'MdePkg/Include/AArch64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),*map(str,inputs),'-o',str(out/'native-video-host')]
 built=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(built.stdout+built.stderr);assert built.returncode==0,built.stderr.decode()
 ran=subprocess.run([str(out/'native-video-host')],capture_output=True);(out/'execution.log').write_bytes(ran.stdout+ran.stderr);assert ran.returncode==0,(ran.stdout+ran.stderr).decode()
 cases=[x[5:] for x in ran.stdout.decode().splitlines() if x.startswith('PASS ')];assert ran.stdout.decode().splitlines()[-1]=='NATIVE_VIDEO_HOST_OK '+str(len(cases))
 report=dict(passed=True,kind='actual native video and SEC restoration ASan/UBSan',handset_executed=False,case_count=len(cases),cases=cases,command=cmd,artifact_directory=str(out.relative_to(ROOT)))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print('passed',len(cases))
if __name__=='__main__':main()
