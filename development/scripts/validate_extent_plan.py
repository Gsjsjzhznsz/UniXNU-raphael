#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Run actual read-only extent mapper under ASan/UBSan; no handset IO."""
import datetime,json,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT

def main():
 parent=ROOT/'artifacts/extent-plan-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 fixture=ROOT/'scripts/fixtures/raphael_extent_plan.cpp';header=ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelReadOnlyExtents.h'
 for p in [fixture,header]: (out/p.name).write_bytes(p.read_bytes())
 command=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(fixture),'-o',str(out/'fixture')]
 report=dict(passed=False,handset_executed=False,media_written=False,compile_command=command)
 try:
  b=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(b.stdout+b.stderr);assert b.returncode==0
  v=subprocess.run([str(out/'fixture')],capture_output=True,timeout=15);(out/'execution.log').write_bytes(v.stdout+v.stderr)
  assert v.returncode==0 and b'RAPHAEL_EXTENT_PLAN_OK' in v.stdout
  report.update(passed=True,case_count=sum(line.startswith(b'PASS ') for line in v.stdout.splitlines()))
 except Exception as error: report['failure']=type(error).__name__+': '+str(error)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
