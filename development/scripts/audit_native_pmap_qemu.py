#!/usr/bin/env python3
"""Observe original pmap replacement and relay mappings, QEMU only."""
import argparse,datetime as dt,json,subprocess,tempfile,time,struct
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--mmu-report',type=Path,required=True);a=p.parse_args();qp=a.mmu_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['stage']==11
 parent=ROOT/'artifacts/native-pmap-qemu';parent.mkdir(exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 (out/'runner.py').write_bytes(Path(__file__).read_bytes());observer=ROOT/'scripts/fixtures/native_pmap_gdb.py';(out/'observer.py').write_bytes(observer.read_bytes())
 inspection=json.loads((ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json').read_text());kernel=ROOT/inspection['artifact_directory']/'native-kernel.macho';assert sha(kernel.read_bytes())==q['native_mmu_contract']['kernel_sha256']
 symbols={v[2]:int(v[0],16) for line in subprocess.check_output(['llvm-nm','--defined-only',str(kernel)],text=True).splitlines() if len(v:=line.split())==3}
 names=['_set_mmu_ttb_alternate','_set_mmu_ttb','_PE_consistent_debug_inherit'];sock='/tmp/rnc-'+out.name[:20]+'.sock'
 spec=dict(output=str(out),socket=sock,contract=q['native_mmu_contract'],segments=q['native_load_contract']['segments'],targets={n:symbols[n] for n in names})
 (out/'spec.json').write_text(json.dumps(spec,indent=2)+chr(10));(out/'debug.gdb').write_text(chr(10).join(['python','SPEC='+repr(str(out/'spec.json')),'exec(compile(open('+repr(str(out/'observer.py'))+').read(),"observer.py","exec"))','end','quit','']))
 command=q['command']+['-S','-gdb','unix:'+sock+',server=on,wait=off'];(out/'command.json').write_text(json.dumps(command,indent=2)+chr(10));report=dict(passed=False,qemu_only=True,handset_executed=False,positive_mmu_report=str(qp.relative_to(ROOT)),positive_mmu_report_sha256=sha(qp.read_bytes()),kernel_sha256=sha(kernel.read_bytes()),command=command);proc=None
 try:
  with (out/'serial.log').open('xb') as log:
   proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);time.sleep(.25)
   g=subprocess.run(['gdb-multiarch','-q','--nx','--batch','-x',str(out/'debug.gdb')],capture_output=True,timeout=55);(out/'gdb.log').write_bytes(g.stdout+g.stderr)
   assert g.returncode==0 and b'Traceback' not in g.stdout+g.stderr,(g.stdout+g.stderr)[-3000:]
  observation=json.loads((out/'trace.json').read_text());assert observation['target_complete'] and len(observation['stops'])==7
  report.update(passed=True,observation=observation,scope='Original arm_vm_init returned after TTBR1 replacement and invalid TTBR0; no Android return or handset claim')
 except Exception as e:report['failure']=type(e).__name__+': '+str(e);raise
 finally:
  if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
  report['evidence_files']=[dict(path=str(p.relative_to(out)),sha256=sha(p.read_bytes())) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='report.json']
  (out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
 print(json.dumps({k:report[k] for k in ['passed','scope']},indent=2))
if __name__=='__main__':main()
