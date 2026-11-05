#!/usr/bin/env python3
"""Trace original instructions and wrong-BRK refusal in identical QEMU image."""
import argparse, datetime as dt, json, re, struct, subprocess, tempfile, time
from pathlib import Path
from entry_probe import ROOT,sha
from native_entry import decode,FIELDS

def main():
 p=argparse.ArgumentParser();p.add_argument('--positive-report',type=Path,required=True);a=p.parse_args()
 qp=a.positive_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['stage']==9 and q['native_entry_test'] and q['android_return_qemu']
 parent=ROOT/'artifacts/native-entry-qemu-audit';parent.mkdir(exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 (out/'runner.py').write_bytes(Path(__file__).read_bytes());contract=q['native_entry_contract']
 report=dict(passed=False,positive_report=str(qp.relative_to(ROOT)),positive_report_sha256=sha(qp.read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),cases=[],handset_executed=False)
 try:
  for case in ['trace','wrong-brk']:
   work=out/case;work.mkdir();sock='/tmp/rne-'+out.name[:20]+'-'+case+'.sock'
   spec=dict(case=case,contract=contract,output=str(work/'trace.json'),socket=sock)
   (work/'spec.json').write_text(json.dumps(spec,indent=2)+chr(10))
   py=r"""import gdb,json,struct
s=json.load(open(SPEC));c=s['contract'];trace=[]
def reg(n):return int(gdb.parse_and_eval('$'+n))
def record(label):
 d=dict(label=label,pc=reg('pc'),x0=reg('x0'),x1=reg('x1'),x20=reg('x20'),x21=reg('x21'),cpsr=reg('cpsr'))
 trace.append(d);json.dump(trace,open(s['output'],'w'),indent=2);return d
gdb.execute('set pagination off');gdb.execute('set architecture aarch64');gdb.execute('target remote '+s['socket'])
at=c['entry'] if s['case']=='trace' else c['checkpoint']
b=gdb.Breakpoint('*'+hex(at),type=gdb.BP_HARDWARE_BREAKPOINT);gdb.execute('continue')
assert reg('pc')==at
b.delete()
if s['case']=='trace':
 expected=[c['entry']]+[c['checkpoint']-16+i*4 for i in range(5)]
 for i,pc in enumerate(expected):
  d=record('original-prefix-'+str(i));assert d['pc']==pc and d['x1']==c['entry']
  if i>=4:assert d['x20']==c['args']
  if i==5:assert d['x21']==0
  gdb.execute('stepi')
 d=record('exception-vector');assert d['pc']!=c['checkpoint']
else:
 record('before-wrong-brk');gdb.selected_inferior().write_memory(c['checkpoint'],struct.pack('<I',c['probe_instruction']+32));record('after-wrong-brk')
gdb.execute('detach')
"""
   (work/'observer.py').write_text(py)
   (work/'debug.gdb').write_text(chr(10).join(['python','SPEC='+repr(str(work/'spec.json')),'exec(compile(open('+repr(str(work/'observer.py'))+').read(),"observer.py","exec"))','end','quit','']))
   command=q['command']+['-S','-gdb','unix:'+sock+',server=on,wait=off'];(work/'command.json').write_text(json.dumps(command,indent=2)+chr(10));proc=None
   try:
    with (work/'serial.log').open('xb') as log:
     proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);time.sleep(.25)
     g=subprocess.run(['gdb-multiarch','-q','--nx','--batch','-x',str(work/'debug.gdb')],capture_output=True,timeout=40)
     (work/'gdb.log').write_bytes(g.stdout+g.stderr);assert g.returncode==0 and b'Breakpoint 1,' in g.stdout and b'Traceback' not in g.stdout+g.stderr
     code=proc.wait(timeout=30)
    raw=(work/'serial.log').read_bytes();m=re.search(rb'NATIVE_ENTRY_WIRE ([0-9a-f]+)',raw);assert m
    wire=bytes.fromhex(m[1].decode());words=dict(zip(FIELDS,struct.unpack('>40Q',wire)))
    assert b'PASS real high stub decode completed' in raw
    if case=='trace':
     assert code==0 and b'ANDROID_RETURN_QEMU_OK' in raw
     decoded=decode(wire,contract,q['layout']);trace=json.loads((work/'trace.json').read_text());assert len(trace)==7
     assert trace[-1]['pc']==decoded['vbar']+decoded['vector_slot']*128
    else:
     assert code!=0 and b'ANDROID_RETURN_QEMU_FAILED' in raw
     assert words['status']==2 and words['error'] and words['esr']==0xf2005351 and words['elr']==contract['checkpoint']
     assert words['patch_restored']==words['mmu_restored']==1 and words['trap_count']==1
     try:decode(wire,contract,q['layout'])
     except AssertionError:pass
     else:raise AssertionError('Wrong marker was accepted')
    report['cases'].append(dict(case=case,passed=True,returncode=code,entry=words,trace=json.loads((work/'trace.json').read_text())))
   finally:
    if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
  report['passed']=len(report['cases'])==2
 finally:
  report['evidence_files']=[dict(path=str(p.relative_to(out)),sha256=sha(p.read_bytes())) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='report.json']
  (out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
 print(json.dumps(dict(passed=report['passed'],cases=len(report['cases'])),indent=2))
if __name__=='__main__':main()
