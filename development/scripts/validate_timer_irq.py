#!/usr/bin/env python3
"""Compile the C wire layout and corrupt an actual QEMU IRQ record independently."""
import argparse,datetime as dt,json,re,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from timer_irq import FIELDS,decode,linked_window,verify_result_storage

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['timer_irq_test'];run=q['executions']['normal'];assert run['timer_irq']['passed']
 parent=ROOT/'artifacts/timer-irq-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 h=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelTimerIrq.h';text=h.read_text();members=[]
 for group in re.findall(r'UINT64 ([^;]+);',text.split('typedef struct {')[1].split('} RAPHAEL')[0]):members.extend(group.split(','))
 assert len(members)==24 and [x.lower() for x in members]==[x.replace('_','') for x in FIELDS]
 source=out/'wire-layout.c';source.write_text('#include <RaphaelTimerIrq.h>\n'+''.join('_Static_assert(__builtin_offsetof(RAPHAEL_TIMER_IRQ_RESULT,'+name+')=='+str(n*8)+',"'+name+'");\n' for n,name in enumerate(members))+'_Static_assert(sizeof(RAPHAEL_TIMER_IRQ_RESULT)==192,"size");\nint main(void){return 0;}\n')
 core=ROOT/'sources/mu_basecore/MdePkg/Include';command=['gcc','-std=c11','-Wall','-Wextra','-Werror','-fshort-wchar','-I'+str(core),'-I'+str(core/'X64'),'-I'+str(h.parent),str(source),'-o',str(out/'wire-layout')]
 c=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(c.stdout+c.stderr);assert c.returncode==0,c.stderr.decode();subprocess.run([str(out/'wire-layout')],check=True)
 serial=(qp.parent/'serial.log').read_bytes();match=re.search(rb'TIMER_IRQ_WIRE ([0-9a-f]+)',serial);assert match;wire=bytes.fromhex(match[1].decode())
 layout=json.loads((qp.parent/'layout.json').read_text())['values'];window=linked_window(qp.parent);route=run['timer_route'];icc=run['icc'];assert decode(wire,route,icc,layout,window)['passed']
 result=dict(zip(FIELDS,struct.unpack('>24Q',wire)));cases=[dict(name='actual C wire layout and real QEMU record',passed=True)]
 bad={'version':2,'status':4,'expected_id':0,'frequency':1,'start_counter':0,'deadline':0,'end_counter':result['deadline']+1,'polls':1000001,'entries':2,'observed_id':0,'irq_counter':result['start_counter']-1,'irq_elr':window['close']+4,'irq_spsr':result['irq_spsr']|0x80,'daif_before':0,'daif_unmasked':0,'daif_after':0,'eoi_count':0,'source_masked':0,'spurious_count':1,'unexpected_id':1,'spsel':0,'stack_pointer':result['stack_pointer']+16,'handler_sp':result['handler_sp']-8,'active_cleared':0}
 def reject(name,raw=wire,route=route,icc=icc,layout=layout,window=window):
  try:decode(raw,route,icc,layout,window)
  except (AssertionError,ValueError):cases.append(dict(name='reject '+name,passed=True))
  else:raise AssertionError(name)
 for key,value in bad.items():
  raw=bytearray(wire);struct.pack_into('>Q',raw,FIELDS.index(key)*8,value);reject(key,raw)
 reject('short',wire[:-8]);reject('long',wire+b'0')
 reject('EOImode1',icc=dict(icc,eoi_mode=1));reject('route failed',route=dict(route,passed=False));reject('restore failed',route=dict(route,restore_ok=0))
 reject('stack lower bound',layout=dict(layout,StackBase=result['handler_sp']+16))
 reject('instruction window excludes interrupt return',window=dict(window,open=result['irq_elr']+4))
 paths=[h,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/TimerIrq.S']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=command,wire_bytes=192,actual_c_offset_assertions=25,
  qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],
  decoder_sha256=sha((ROOT/'scripts/timer_irq.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),result_storage=verify_result_storage(qp.parent),handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/timer-irq-host.json').write_text(json.dumps(report,indent=2)+'\n')
 print(len(cases),'independent wire/boundary checks and 25 compiled C layout assertions passed');print(out)
if __name__=='__main__':main()
