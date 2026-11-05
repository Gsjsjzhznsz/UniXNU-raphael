#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Compile independent UFS classes against a pinned prepared kernel/storage ABI."""
import argparse,datetime as dt,json,os,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--tree',type=Path,required=True);a=p.parse_args();tree=a.tree.resolve()
 assert tree.is_relative_to(ROOT/'artifacts/native-bootstrap')
 record=json.loads((tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
 parent=ROOT/'artifacts/raphael-ufs-object';parent.mkdir(exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 source=ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelUfsBlock.cpp';target=out/'RaphaelUfsBlock.o'
 files=[source,*[source.parent/x for x in ['RaphaelUfsTransport.h','RaphaelUfsDmaGate.h','RaphaelReadOnlyExtents.h','RaphaelExtentPlan.h','RaphaelDeviceBuffer.h','RaphaelUfsWritePolicy.h','RaphaelUfsLogPolicy.h']]]
 for file in files:(out/file.name).write_bytes(file.read_bytes())
 native_write=None
 policy_path=os.environ.get('RAPHAEL_NATIVE_UFS_WRITE_POLICY')
 if policy_path:
  from ufs_write_probe import validate_manifest
  native_write=validate_manifest(Path(policy_path))
  policy=Path(policy_path).read_bytes()
  template=ROOT/'UniXNU-raphael/package/drivers/RaphaelUfsWriteProbe.inc'
  (out/template.name).write_bytes(template.read_bytes());files.append(template)
  declaration='extern "C" { extern const unsigned char raphael_ufs_write_probe_policy[8256] __attribute__((aligned(8))) = {'+','.join(str(b) for b in policy)+'}; }\n'
  (out/'RaphaelUfsWriteProbePolicy.h').write_text(declaration)
  with (out/source.name).open('a') as f:f.write('\n#include "RaphaelUfsWriteProbePolicy.h"\n#include "RaphaelUfsWriteProbe.inc"\n')
 command=[];args=record['arguments'];i=0
 while i<len(args):
  value=args[i]
  if value==record['file']:command.append(str(out/source.name))
  elif value=='-o':command.extend(['-o',str(target)]);i+=1
  elif value=='-Xclang' and args[i+1].startswith('-W'):i+=1
  elif not value.startswith('-W'):command.append(value)
  i+=1
 command.extend(['-Wall','-Wextra','-Werror','-Wno-missing-designated-field-initializers','-Wno-unused-parameter','-Wno-c99-designator','-Wno-reorder-init-list','-Wno-deprecated-enum-enum-conversion','-Wno-unnecessary-virtual-specifier','-mgeneral-regs-only','-I',str(tree/'.cache/xnu-work/osfmk'),'-I',str(tree/'build/storage-abi/include'),'-I',str(out),'-I',str(ROOT/'sources/UniXNU/kits/VerifiedRoot/include'),'-I',str(ROOT/'sources/UniXNU/drivers/VirtioMmioBlock')])
 env=os.environ.copy();env['PATH']='/opt/unixnu-linux/bin:'+env['PATH']
 report=dict(passed=False,handset_executed=False,linked_in_kernel=False,tree=str(tree.relative_to(ROOT)),sources=[dict(path=str(f.relative_to(ROOT)),sha256=sha(f.read_bytes())) for f in files],command=command)
 report['native_ufs_write_probe']=native_write
 try:
  v=subprocess.run(command,cwd=record['directory'],env=env,capture_output=True);(out/'build.log').write_bytes(v.stdout+v.stderr);assert v.returncode==0,(v.stdout+v.stderr).decode(errors='replace')[-5000:]
  raw=target.read_bytes();assert struct.unpack_from('<4I',raw)==(0xfeedfacf,0x100000c,0,1)
  report.update(passed=True,object_sha256=sha(raw),object_bytes=len(raw))
 except Exception as e:report['failure']=repr(e)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
