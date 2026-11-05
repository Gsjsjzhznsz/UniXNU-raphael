#!/usr/bin/env python3
"""Observe original post-pmap console and platform prefix, isolated QEMU only."""
import argparse,datetime as dt,json,subprocess,tempfile,time
from pathlib import Path
from entry_probe import ROOT,sha
from native_early import image

def main():
 p=argparse.ArgumentParser();p.add_argument('--pmap-report',type=Path,required=True);a=p.parse_args();qp=a.pmap_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['stage']==12
 parent=ROOT/'artifacts/native-post-pmap-qemu';parent.mkdir(exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 (out/'runner.py').write_bytes(Path(__file__).read_bytes());observer=ROOT/'scripts/fixtures/native_post_pmap_gdb.py';(out/'observer.py').write_bytes(observer.read_bytes());k=subprocess.check_output(['mtype','-i',str(qp.parent/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho']);_,symbols=image(k);assert sha(k)==q['native_mmu_contract']['kernel_sha256']
 names=['_serial_init','_kprintf','_PE_create_console','_PE_init_printf','_cpu_machine_idle_init','_PE_init_platform','_cpu_timebase_init','_PE_init_cpu','_fiq_context_init','_machine_startup','_panic'];sock='/tmp/rpp-'+out.name[:20]+'.sock';spec=dict(output=str(out),socket=sock,contract=q['native_mmu_contract'],segments=q['native_load_contract']['segments'],adt_bytes=q['native_load_contract']['adt_bytes'],targets={n:symbols[n] for n in names})
 (out/'spec.json').write_text(json.dumps(spec,indent=2)+chr(10));(out/'debug.gdb').write_text(chr(10).join(['python','SPEC='+repr(str(out/'spec.json')),'exec(compile(open('+repr(str(out/'observer.py'))+').read(),"observer.py","exec"))','end','quit','']))
 command=q['command']+['-S','-gdb','unix:'+sock+',server=on,wait=off'];(out/'command.json').write_text(json.dumps(command,indent=2)+chr(10));report=dict(passed=False,qemu_only=True,handset_executed=False,positive_report=str(qp.relative_to(ROOT)),positive_report_sha256=sha(qp.read_bytes()),kernel_sha256=sha(k),command=command);proc=None
 try:
  with (out/'serial.log').open('xb') as log:
   proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);time.sleep(.25);g=subprocess.run(['gdb-multiarch','-q','--nx','--batch','-x',str(out/'debug.gdb')],capture_output=True,timeout=55);(out/'gdb.log').write_bytes(g.stdout+g.stderr);assert g.returncode==0 and b'Traceback' not in g.stdout+g.stderr,(g.stdout+g.stderr)[-2500:]
  observation=json.loads((out/'trace.json').read_text());assert observation['target_complete'] and observation['stops'][-1]['pc']==symbols['_machine_startup'];report.update(passed=True,observation=observation,scope='Original post-pmap functions through machine_startup entry; no Android return, normal timer IRQ or handset claim')
 except Exception as e:report['failure']=type(e).__name__+': '+str(e);raise
 finally:
  if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
  report['evidence_files']=[dict(path=str(f.relative_to(out)),sha256=sha(f.read_bytes())) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='report.json'];(out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
 print(json.dumps({k:report[k] for k in ['passed','scope']},indent=2))
if __name__=='__main__':main()
