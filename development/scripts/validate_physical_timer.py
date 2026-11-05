#!/usr/bin/env python3
"""Compile the C result ABI and independently corrupt real TimerArch evidence."""
import argparse,datetime as dt,json,re,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from physical_timer import FIELDS,decode,verify_result_storage

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['physical_timer_arch'] and q['stop_stage']==4
 run=q['executions']['normal'];assert run['physical_timer']['physical_only_timer_arch_verified']
 parent=ROOT/'artifacts/physical-timer-host';parent.mkdir(exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 h=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPhysicalTimer.h';members=[]
 for group in re.findall(r'UINT64 ([^;]+);',h.read_text().split('} RAPHAEL_PHYSICAL_TIMER_RESULT')[0]):members += [x.strip() for x in group.split(',')]
 assert [re.sub(r'(?<!^)(?=[A-Z])','_',x).lower() for x in members]==FIELDS
 source=out/'abi.c';source.write_text('#include <RaphaelPhysicalTimer.h>\n'+''.join('_Static_assert(__builtin_offsetof(RAPHAEL_PHYSICAL_TIMER_RESULT,'+x+')=='+str(n*8)+',"'+x+'");\n' for n,x in enumerate(members))+'_Static_assert(sizeof(RAPHAEL_PHYSICAL_TIMER_RESULT)==448,"wire size");\n_Static_assert(sizeof(RAPHAEL_PHYSICAL_TIMER_STATE)==512,"state size");\nint main(void){return 0;}\n')
 core=ROOT/'sources/mu_basecore/MdePkg/Include';cmd=['gcc','-std=c11','-Wall','-Wextra','-Werror','-fshort-wchar','-I'+str(core),'-I'+str(core/'X64'),'-I'+str(h.parent),str(source),'-o',str(out/'abi')]
 c=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(c.stdout+c.stderr);assert c.returncode==0,c.stderr.decode();subprocess.run([str(out/'abi')],check=True)
 wire=bytes.fromhex(re.search(rb'PHYSICAL_TIMER_WIRE ([0-9a-f]+)',(qp.parent/'serial.log').read_bytes())[1].decode())
 g,route,icc=run['gic'],run['timer_route'],run['icc'];r=decode(wire,6,g,route,icc)
 cases=[dict(name='actual QEMU TimerArch and 58 C ABI assertions',passed=True)]
 def reject(name,raw=wire,stage=6,gic=g,rt=route,ic=icc):
  try:decode(raw,stage,gic,rt,ic)
  except (AssertionError,ValueError,KeyError,struct.error):cases.append(dict(name='reject '+name,passed=True))
  else:raise AssertionError(name)
 # Every wire field is load-bearing and must reject independently corrupted data.
 for n,key in enumerate(FIELDS):
  value=r[key]
  if key in ['irq_count','eoi_count','periodic_count','notify_count','relative_ticks','periodic_ticks','cancel_ticks','start_counter','first_counter','last_counter','end_counter']:new=0 if value else (1<<64)-1
  else:new=value^1
  if key=='start_counter':new=r['first_counter']+1
  if key=='first_counter':new=r['start_counter']-1
  if key=='last_counter':new=r['end_counter']+1
  if key=='saved_ctl':new=value^2
  if key=='ctl_after':new=value^2
  if key=='saved_vctl':new=value^2
  if key=='vctl_after':new=value^2
  if key=='pending_after':new=value^(1<<r['intid'])
  bad=bytearray(wire);struct.pack_into('>Q',bad,n*8,new);reject(key,bad)
 reject('short',wire[:-8]);reject('long',wire+b'0')
 reject('wrong phase',stage=3);reject('unvalidated GIC',gic=dict(g,passed=False));reject('unvalidated route',rt=dict(route,passed=False));reject('unvalidated ICC',ic=dict(icc,passed=False))
 paths=[h,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/PhysicalTimerDxe/PhysicalTimer.c',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/DiagnosticReturnDxe/PhysicalTimerTest.c']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,actual_c_abi_assertions=58,wire_bytes=448,result_storage=verify_result_storage(qp.parent),
  qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],decoder_sha256=sha((ROOT/'scripts/physical_timer.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),handset_executed=False)
 data=json.dumps(report,indent=2)+'\n';(out/'report.json').write_text(data);(ROOT/'UniXNU-raphael/evidence/physical-timer-host.json').write_text(data)
 print(len(cases),'independent evidence checks, 58 compiled C ABI assertions');print(out)
if __name__=='__main__':main()
