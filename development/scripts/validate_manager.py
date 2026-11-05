#!/usr/bin/env python3
"""Compile the manager wire ABI and reject corrupted countdown/FAT evidence."""
import argparse,datetime as dt,json,re,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from manager_probe import FIELDS,decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['physical_timer_arch'] and q['payload_test'] and q['stop_stage']==4
 run=q['executions']['normal'];manual=q.get('manager_keys',False);assert run['manager']['complete_unixnu_manager_executed'] and run['physical_timer']['physical_only_timer_arch_verified']
 parent=ROOT/'artifacts/manager-host';parent.mkdir(exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 names=['Version','Status','StartCounter','EndCounter','Frequency','Timeout']
 src=out/'abi.c';src.write_text('#include <RaphaelPhysicalTimer.h>\n'+''.join('_Static_assert(__builtin_offsetof(RAPHAEL_MANAGER_RESULT,'+n+')=='+str(i*8)+',"'+n+'");\n' for i,n in enumerate(names))+'_Static_assert(sizeof(RAPHAEL_MANAGER_RESULT)==48,"wire");\n_Static_assert(__builtin_offsetof(RAPHAEL_PHYSICAL_TIMER_STATE,Manager)==464,"state");\nint main(void){return 0;}\n')
 core=ROOT/'sources/mu_basecore/MdePkg/Include';cmd=['gcc','-std=c11','-Wall','-Wextra','-Werror','-fshort-wchar','-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),str(src),'-o',str(out/'abi')]
 c=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(c.stdout+c.stderr);assert c.returncode==0,c.stderr.decode();subprocess.run([str(out/'abi')],check=True)
 wire=bytes.fromhex(re.search(rb'MANAGER_WIRE ([0-9a-f]+)',(qp.parent/'serial.log').read_bytes())[1].decode());freq=run['icc']['cntfrq'];payload=run['payload'];r=decode(wire,6,payload,freq,manual=manual)
 cases=[dict(name='actual full UniXNURun with physical TimerArch and 8 C ABI assertions',passed=True)]
 def reject(name,raw=wire,stage=6,pl=payload,fr=freq):
  try:decode(raw,stage,pl,fr,manual=manual)
  except (AssertionError,ValueError,KeyError,struct.error):cases.append(dict(name='reject '+name,passed=True))
  else:raise AssertionError(name)
 for key,value in dict(version=0,status=1,start_counter=r['end_counter']+1,end_counter=r['start_counter'],frequency=freq+1,timeout=0).items():
  bad=bytearray(wire);struct.pack_into('>Q',bad,FIELDS.index(key)*8,value);reject(key,bad)
 reject('short',wire[:-8]);reject('long',wire+b'0');reject('wrong phase',stage=3);reject('wrong frequency',fr=freq+1)
 reject('FAT validation failed',pl=dict(payload,read_only_payload_checkpoint_verified=False));reject('manager invocation missing',pl=dict(payload,full_unixnu_invocation_verified=False));reject('FAT data changed',pl=dict(payload,crc_after=payload['crc_before']^1))
 low,high=(1,freq*8) if manual else (freq*18//10,freq*5)
 for ticks,ok in [(low-1,False),(low,True),(high,True),(high+1,False)]:
  bad=bytearray(wire);struct.pack_into('>Q',bad,3*8,r['start_counter']+ticks)
  if ok:assert decode(bad,6,payload,freq,manual=manual)['passed'];cases.append(dict(name='accept countdown endpoint '+str(ticks),passed=True))
  else:reject('countdown endpoint '+str(ticks),bad)
 paths=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPhysicalTimer.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/DiagnosticReturnDxe/PayloadTest.c',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/Sec.c']
 report=dict(passed=True,case_count=len(cases),cases=cases,manual_key_test=manual,actual_c_abi_assertions=8,command=cmd,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],decoder_sha256=sha((ROOT/'scripts/manager_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),handset_executed=False)
 data=json.dumps(report,indent=2)+'\n';(out/'report.json').write_text(data);(ROOT/'UniXNU-raphael/evidence/manager-host.json').write_text(data)
 print(len(cases),'manager wire/countdown/cross-evidence checks, 8 C ABI assertions');print(out)
if __name__=='__main__':main()
