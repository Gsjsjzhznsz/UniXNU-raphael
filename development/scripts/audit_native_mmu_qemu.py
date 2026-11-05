#!/usr/bin/env python3
"""Independently trace and corrupt the same bounded XNU MMU QEMU Image."""
import argparse,datetime as dt,json,re,struct,subprocess,tempfile,time
from pathlib import Path
from entry_probe import ROOT,sha
from native_mmu import decode,audit_tables,FIELDS

def main():
 p=argparse.ArgumentParser();p.add_argument('--positive-report',type=Path,required=True);a=p.parse_args()
 qp=a.positive_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['stage'] in [10,11] and q['native_mmu_test'] and q['android_return_qemu']
 parent=ROOT/'artifacts/native-mmu-qemu-audit';parent.mkdir(exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 (out/'runner.py').write_bytes(Path(__file__).read_bytes());c=q['native_mmu_contract']
 report=dict(passed=False,positive_report=str(qp.relative_to(ROOT)),positive_report_sha256=sha(qp.read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),cases=[],handset_executed=False)
 try:
  cases=['trace','wrong-brk','bad-table']+(['backup-corrupt'] if q.get('native_early_test') else [])
  for case in cases:
   work=out/case;work.mkdir();sock='/tmp/rnm-'+out.name[:20]+'-'+case+'.sock'
   spec=dict(case=case,contract=c,output=str(work/'trace.json'),socket=sock)
   (work/'spec.json').write_text(json.dumps(spec,indent=2)+chr(10))
   observer=ROOT/'scripts/fixtures/native_mmu_gdb.py';(work/'observer.py').write_bytes(observer.read_bytes())
   (work/'debug.gdb').write_text(chr(10).join(['python','SPEC='+repr(str(work/'spec.json')),'exec(compile(open('+repr(str(work/'observer.py'))+').read(),"observer.py","exec"))','end','quit','']))
   command=q['command']+['-S','-gdb','unix:'+sock+',server=on,wait=off'];(work/'command.json').write_text(json.dumps(command,indent=2)+chr(10));proc=None
   try:
    with (work/'serial.log').open('xb') as log:
     proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);time.sleep(.25)
     g=subprocess.run(['gdb-multiarch','-q','--nx','--batch','-x',str(work/'debug.gdb')],capture_output=True,timeout=45)
     (work/'gdb.log').write_bytes(g.stdout+g.stderr);assert g.returncode==0 and b'Breakpoint 1,' in g.stdout and b'Traceback' not in g.stdout+g.stderr,(g.stdout+g.stderr)[-3000:]
     code=proc.wait(timeout=30)
    raw=(work/'serial.log').read_bytes();m=re.search(rb'NATIVE_MMU_WIRE ([0-9a-f]+)',raw);t=re.search(rb'NATIVE_MMU_TABLES ([0-9a-f]+)',raw);assert m and t
    wire=bytes.fromhex(m[1].decode());tables=bytes.fromhex(t[1].decode());(work/'wire.bin').write_bytes(wire);(work/'tables.bin').write_bytes(tables)
    words=dict(zip(FIELDS,struct.unpack('>72Q',wire)));trace=json.loads((work/'trace.json').read_text())
    assert b'PASS real high stub decode completed' in raw
    assert words['patch_restored']==words['tables_restored']==words['mmu_restored']==words['trap_count']==1
    if case=='trace':
     assert code==0 and b'ANDROID_RETURN_QEMU_OK' in raw
     d=decode(wire,c);ta=audit_tables(tables,d,c)
     assert [x['label'] for x in trace]==['before-enable','after-enable-msr','after-enable-isb','checkpoint' if q.get('native_early_test') else 'arm-init','exception-vector','vector-mov','vector-ldr','physical-relay','relay-cache-off']
     assert trace[0]['pc']==c['mmu_enable_pa'] and trace[0]['sctlr']&0x1005==0
     assert trace[1]['sctlr']==trace[2]['sctlr']==c['policy']['sctlr']
     assert trace[3]['pc']==(c['early']['policy']['checkpoint'] if q.get('native_early_test') else c['policy']['arm_init']) and trace[3]['x0']==(0 if q.get('native_early_test') else c['args']-c['physical_delta'])
     assert trace[4]['pc']==c['policy']['high_vectors'] and trace[7]['pc']==d['relay_pa'] and trace[8]['sctlr']&0x1005==0
    else:
     assert code!=0 and b'ANDROID_RETURN_QEMU_FAILED' in raw and words['status']==2 and words['error']==2
     assert words['elr']==(c['early']['policy']['checkpoint'] if q.get('native_early_test') else c['policy']['arm_init']) and words['esr']==(0xf2005352 if case=='wrong-brk' else 0xf2005351)
     try:decode(wire,c)
     except AssertionError:pass
     else:raise AssertionError('Corrupt state accepted')
     if case=='bad-table':
      try:audit_tables(tables,words,c)
      except AssertionError:pass
      else:raise AssertionError('Corrupt final block accepted')
     ta=None
    early_result=None
    if q.get('native_early_test'):
     from native_early import decode as decode_early,FIELDS as EARLY_FIELDS
     ew=re.search(rb'NATIVE_EARLY_WIRE ([0-9a-f]+)',raw);ed=re.search(rb'NATIVE_EARLY_DELTA ([0-9a-f]+)',raw);assert ew and ed
     early_wire=bytes.fromhex(ew[1].decode());delta=bytes.fromhex(ed[1].decode());(work/'early-wire.bin').write_bytes(early_wire);(work/'early-delta.bin').write_bytes(delta)
     ev=struct.unpack('>40Q',early_wire)
     if case=='backup-corrupt':
      assert ev[1:3]==(2,1) and ev[14]==2 and ev[16+7]==0 and words['segments_ok']==9
      early_result=dict(expected_backup_rejected=True,restored_ranges=ev[14])
     else:
      kernel=subprocess.check_output(['mtype','-i',str(qp.parent/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho'])
      early_result=decode_early(early_wire,delta,kernel,c,words,tables)
      if case=='trace':
       for i,r in enumerate(early_result['ranges']):assert sha((work/('early-range-'+str(i)+'.bin')).read_bytes())==r['snapshot_sha256']
    report['cases'].append(dict(case=case,passed=True,returncode=code,mmu=words,trace=trace,tables=ta,early=early_result))
   finally:
    if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
  report['passed']=len(report['cases'])==len(cases)
 except Exception as e:report['failure']=type(e).__name__+': '+str(e);raise
 finally:
  report['evidence_files']=[dict(path=str(p.relative_to(out)),sha256=sha(p.read_bytes())) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='report.json']
  (out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
 print(json.dumps(dict(passed=report['passed'],cases=len(report['cases'])),indent=2))
if __name__=='__main__':main()
