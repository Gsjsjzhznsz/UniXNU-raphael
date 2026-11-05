#!/usr/bin/env python3
"""Trace and inject into the exact post-pmap recovery Image, isolated QEMU."""
import argparse,datetime as dt,json,re,struct,subprocess,tempfile,time
from pathlib import Path
from entry_probe import ROOT,sha
from native_mmu import decode as decode_mmu,audit_tables,FIELDS
from native_early import image,decode as decode_early
from native_pmap import decode as decode_pmap,FIELDS as PF

def main():
 p=argparse.ArgumentParser();p.add_argument('--positive-report',type=Path,required=True);a=p.parse_args();qp=a.positive_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['stage']==12
 parent=ROOT/'artifacts/native-pmap-recovery-qemu-audit';parent.mkdir(exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 kernel=subprocess.check_output(['mtype','-i',str(qp.parent/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho']);_,symbols=image(kernel);adt=(qp.parent/'kernel.macho.adt').read_bytes();c=q['native_mmu_contract'];assert sha(kernel)==c['kernel_sha256']
 (out/'runner.py').write_bytes(Path(__file__).read_bytes());report=dict(passed=False,handset_executed=False,positive_report=str(qp.relative_to(ROOT)),positive_report_sha256=sha(qp.read_bytes()),cases=[])
 try:
  for case in ['trace','wrong-brk','bad-active-table','transition-corrupt','backup-corrupt']:
   work=out/case;work.mkdir();sock='/tmp/rpr-'+out.name[:20]+'-'+case+'.sock';spec=dict(case=case,output=str(work),contract=c,socket=sock,symbols={n:symbols[n] for n in ['_arm_vm_init','_set_mmu_ttb_alternate','_set_mmu_ttb']})
   (work/'spec.json').write_text(json.dumps(spec,indent=2)+chr(10));observer=ROOT/'scripts/fixtures/native_pmap_recovery_gdb.py';(work/'observer.py').write_bytes(observer.read_bytes());(work/'debug.gdb').write_text(chr(10).join(['python','SPEC='+repr(str(work/'spec.json')),'exec(compile(open('+repr(str(work/'observer.py'))+').read(),"observer.py","exec"))','end','quit','']))
   command=q['command']+['-S','-gdb','unix:'+sock+',server=on,wait=off'];(work/'command.json').write_text(json.dumps(command,indent=2)+chr(10));proc=None
   try:
    with (work/'serial.log').open('xb') as log:
     proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);time.sleep(.25);g=subprocess.run(['gdb-multiarch','-q','--nx','--batch','-x',str(work/'debug.gdb')],capture_output=True,timeout=55);(work/'gdb.log').write_bytes(g.stdout+g.stderr)
     assert g.returncode==0 and b'Traceback' not in g.stdout+g.stderr,(g.stdout+g.stderr)[-2200:];code=proc.wait(timeout=30)
    log=(work/'serial.log').read_bytes();trace=json.loads((work/'trace.json').read_text())
    def raw(tag,name):
     m=re.search(tag.encode()+rb' ([0-9a-f]+)',log);assert m,tag;b=bytes.fromhex(m[1].decode());(work/name).write_bytes(b);return b
    mw=raw('NATIVE_MMU_WIRE','mmu-wire.bin');tables=raw('NATIVE_MMU_TABLES','bootstrap-tables.bin');ew=raw('NATIVE_EARLY_WIRE','early-wire.bin');delta=raw('NATIVE_EARLY_DELTA','early-delta.bin');pw=raw('NATIVE_PMAP_WIRE','pmap-wire.bin');ps=raw('NATIVE_PMAP_TABLES','pmap-tables.bin');pt=raw('NATIVE_PMAP_TRANSITION','pmap-transition.bin');pa=raw('NATIVE_PMAP_ADT','pmap-adt.bin')
    mmu=dict(zip(FIELDS,struct.unpack('>72Q',mw)));pm=dict(zip(PF,struct.unpack('>32Q',pw)));ev=struct.unpack('>40Q',ew)
    assert b'PASS real high stub decode completed' in log and all(mmu[n]==1 for n in ['patch_restored','tables_restored','mmu_restored','trap_count'])
    bt=audit_tables(tables,mmu,c);early=None;decoded=None
    if case=='trace':
     assert code==0 and b'ANDROID_RETURN_QEMU_OK' in log and b'FAIL ' not in log;decode_mmu(mw,c);decoded=decode_pmap(pw,ps,pt,pa,adt,c,mmu)
     assert [x['label'] for x in trace]==['arm-vm-entry','ttbr1-entry','ttbr1-return','ttbr0-entry','ttbr0-return','arm-vm-returned','checkpoint','exception-vector','high-prefix','before-transition','after-transition','physical-body','clean-first-line','cache-off','captured']
     assert sha((work/'active-tables.bin').read_bytes())==decoded['table_snapshot_sha256'] and (work/'transition.bin').read_bytes()==pt and (work/'adt.bin').read_bytes()==pa
    else:
     assert code!=0 and b'ANDROID_RETURN_QEMU_FAILED' in log and mmu['status']==2 and mmu['error']==2
     try:decode_mmu(mw,c)
     except AssertionError:pass
     else:raise AssertionError('Negative MMU state accepted')
     assert mmu['elr']==c['early']['policy']['checkpoint'] and mmu['esr']==(0xf2005352 if case=='wrong-brk' else 0xf2005351)
     if case in ['bad-active-table','transition-corrupt']:
      assert pm['status']==2 and pm['error']==1 and pm['adt_restored']==1
      try:decode_pmap(pw,ps,pt,pa,adt,c,mmu)
      except AssertionError:pass
      else:raise AssertionError('Negative pmap accepted')
      if case=='transition-corrupt':assert pm['transition_ok']==0 and pm['transition_crc_after']!=pm['transition_crc_before']
      else:assert pm['high_data_pages']==643 and pm['capture_ok']==1
     else:decoded=decode_pmap(pw,ps,pt,pa,adt,c,mmu)
    if case=='backup-corrupt':assert ev[1:3]==(2,1) and ev[14]==2 and mmu['segments_ok']==9
    else:
     early=decode_early(ew,delta,kernel,c,mmu,tables)
     if case=='trace':
      for i,x in enumerate(early['ranges']):assert sha((work/('range-'+str(i)+'.bin')).read_bytes())==x['snapshot_sha256']
    report['cases'].append(dict(case=case,passed=True,returncode=code,trace=trace,mmu=mmu,early=early,pmap=decoded,pmap_words=pm,bootstrap=bt))
   finally:
    if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
  report['passed']=len(report['cases'])==5
 except Exception as e:report['failure']=type(e).__name__+': '+str(e);raise
 finally:
  report['evidence_files']=[dict(path=str(f.relative_to(out)),sha256=sha(f.read_bytes())) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='report.json'];(out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
 print(json.dumps(dict(passed=report['passed'],cases=len(report['cases'])),indent=2))
if __name__=='__main__':main()
