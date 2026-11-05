#!/usr/bin/env python3
"""One bounded QEMU desktop display cycle, using locally pinned source only."""
import argparse,json,subprocess
from pathlib import Path
from entry_probe import ROOT
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--keep-paused',action='store_true')
p.add_argument('--scratch-data',type=Path,default=Path('evidence/private/desktop-data/20261030T101301Z/report.json'),help='Explicit private emulator Data report; must match frozen kernel volume/seed contract')
p.add_argument('--sparse-data',action='store_true',help='Use original packed sparse RAM backend; no contiguous Data snapshot')
p.add_argument('--kernel-window-mb',type=int,choices=[1024,1536],default=1024,help='Explicit isolated QEMU allocation')
p.add_argument('--capture-data-after',type=int,default=0)
p.add_argument('--runtime-main-program',type=Path)
p.add_argument('--progress-seconds',type=int,default=0)
p.add_argument('--until-frame',action='store_true',help='Run original userland until a real framebuffer swap has copied and retired; not desktop acceptance')
p.add_argument('--runtime-process',help='Follow original launchd and exact process first SVC; not desktop acceptance')
p.add_argument('--observe-seconds',type=int,default=120)
p.add_argument('--inspection',type=Path,help='Run an already frozen candidate without rebuilding')
p.add_argument('--user-abi',type=Path,help='Matching frozen candidate DWARF report')
a=p.parse_args()
def run(args):
 r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if r.returncode:
  print((r.stdout+r.stderr)[-5000:],flush=True);raise SystemExit(r.returncode)
 return r.stdout
if a.inspection:
 assert a.user_abi
 inspection=a.inspection;abi=a.user_abi
else:
 run(['python3','scripts/build_native_bootstrap.py','--desktop-display','--scratch-data',a.scratch_data,'--root-policy','evidence/private/desktop-root-policy/20261030T081351Z/report.json','--storage-audit','artifacts/native-bootstrap/raphael/ipados-17.7.11-21H461/raphael_desktop/tree/build/storage-abi/interface-audit.json','--storage-candidate','artifacts/desktop-prelink/20261030T072416Z/kernel.macho'])
 build=json.loads((ROOT/'UniXNU-raphael/evidence/desktop-display-bootstrap-host.json').read_text())
 print('build',build['artifact_directory'],flush=True)
 run(['python3','scripts/inspect_native_kernel.py','--build-report',build['artifact_directory']+'/report.json','--index','artifacts/desktop-display-kernel-structure.json'])
 pre=run(['python3','scripts/prepare_desktop_kernel.py','--kernelcache','artifacts/desktop-system/ipsw/21H461/kernelcache.decompressed','--inspection','artifacts/desktop-display-kernel-structure.json'])
 candidate=Path(pre.splitlines()[0]);inspection=candidate/'inspection.json';print('prelink',candidate,flush=True)
 user=json.loads(run(['python3','scripts/prepare_user_observer_abi.py','--inspection',inspection,'--object','artifacts/native-bootstrap/raphael/ipados-17.7.11-21H461/raphael_desktop_display/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/systemcalls.o']))
 abi=Path(user['artifact_directory'])/'report.json';print('abi',abi,flush=True)
cmd=['python3','scripts/run_native_xnu_qemu.py','--inspection',inspection,'--os-profile','--gop','--desktop-display','--system-disks','artifacts/desktop-disks/20261030T075713Z/report.json','--trust-bundle','artifacts/desktop-trust/20261030T081913Z/report.json','--scratch-data',a.scratch_data,'--shared-data-volume','--user-abi',abi,'--stop-at','display_frame' if a.until_frame else 'launchd_runtime' if a.runtime_process else 'display','--boot-cpu','physical','--kalloc-zones','200','--memory-mb','2048','--kernel-window-mb',str(a.kernel_window_mb),'--observe-seconds',str(a.observe_seconds)]
if a.keep_paused:cmd+=['--keep-paused']
if a.sparse_data:cmd+=['--sparse-data']
if a.capture_data_after:cmd+=['--capture-data-after',str(a.capture_data_after)]
if a.runtime_main_program:cmd+=['--runtime-main-program',a.runtime_main_program]
if a.progress_seconds:cmd+=['--progress-seconds',str(a.progress_seconds)]
if a.runtime_process or a.until_frame:cmd+=['--runtime-process',a.runtime_process or '__frame__','--main-program','artifacts/desktop-disks/20261030T074616Z/OS-mount/sbin/launchd']
print(run(cmd),flush=True)
