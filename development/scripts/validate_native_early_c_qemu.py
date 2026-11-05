#!/usr/bin/env python3
"""Independently compare every saved early-C segment with original Mach-O bytes."""
import argparse,datetime as dt,json,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);a=p.parse_args();rp=a.report.resolve();r=json.loads(rp.read_text());base=rp.parent
 assert r['passed'] and r['qemu_only'] and not r['handset_executed']
 for item in r['evidence_files']:assert sha((base/item['path']).read_bytes())==item['sha256']
 qp=ROOT/r['positive_mmu_report'];q=json.loads(qp.read_text());assert q['passed'] and sha(qp.read_bytes())==r['positive_mmu_report_sha256']
 inspection=json.loads((ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json').read_text());k=(ROOT/inspection['artifact_directory']/'native-kernel.macho').read_bytes();assert sha(k)==r['kernel_sha256']==q['native_mmu_contract']['kernel_sha256']
 count=struct.unpack_from('<I',k,16)[0];at=32;segments=[]
 for i in range(count):
  cmd,size=struct.unpack_from('<II',k,at)
  if cmd==0x19:
   name=k[at+8:at+24].rstrip(b'\0').decode();va,length,offset,data=struct.unpack_from('<4Q',k,at+24)
   if length:segments.append(dict(name=name,va=va,bytes=length,file_offset=offset,file_bytes=data,protection=struct.unpack_from('<I',k,at+60)[0]))
  at+=size
 segments=[s for s in segments if s['file_bytes']];assert len(segments)==10
 p=q['native_mmu_contract']['policy'];instrumented=[(p['low_vectors'],4096),(p['high_vectors'],2048),(p['tables'],65536)]
 trace=json.loads((base/'trace.json').read_text());assert trace==r['observation'] and trace['target_complete']
 assert [s['label'] for s in trace['stops']]==['arm-init','platform-first','platform-returned','rtclock-entry','arm-vm-entry']
 spec=json.loads((base/'spec.json').read_text());assert spec['contract']==q['native_mmu_contract'] and spec['segments']==q['native_load_contract']['segments']
 assert trace['stops'][0]['pc']==p['arm_init'] and trace['stops'][1]['pc']==spec['targets']['_PE_init_platform'] and trace['stops'][1]['x0']==0
 assert trace['stops'][2]['pc']==trace['stops'][1]['lr'] and trace['stops'][3]['pc']==spec['targets']['_rtclock_early_init'] and trace['stops'][4]['pc']==spec['targets']['_arm_vm_init']
 assert len({s['table_sha256'] for s in trace['stops']})==1
 baselines={};results=[]
 for stop in trace['stops']:
  changes=[]
  assert len(stop['segments'])==len(segments)
  for i,(desc,segment) in enumerate(zip(stop['segments'],segments)):
   raw=(base/desc['file']).read_bytes();assert len(raw)==desc['bytes']==segment['bytes'] and sha(raw)==desc['sha256'] and desc['virtual_address']==segment['va'] and desc['protection']==segment['protection']
   if stop['label']=='arm-init':
    baselines[i]=raw;expected=k[segment['file_offset']:segment['file_offset']+segment['file_bytes']]+bytes(segment['bytes']-segment['file_bytes'])
    cursor=0
    for start,length in sorted(instrumented):
     lo=max(start-segment['va'],0);hi=min(start+length-segment['va'],len(raw))
     if hi<=lo:continue
     assert raw[cursor:lo]==expected[cursor:lo];cursor=hi
    assert raw[cursor:]==expected[cursor:]
   original=baselines[i];dirty=[offset for offset in range(0,len(raw),4096) if raw[offset:offset+4096]!=original[offset:offset+4096]];changed=sum(x!=y for x,y in zip(raw,original))
   assert dirty==desc['dirty_pages'] and changed==desc['changed_bytes']
   table_lo=p['tables']-segment['va'];table_hi=table_lo+65536
   if 0<=table_lo and table_hi<=len(raw):assert sha(raw[table_lo:table_hi])==stop['table_sha256']
   if changed:
    assert segment['name'] in ['__DATA_CONST','__DATA','__BOOTDATA'],segment['name']
    changes.append(dict(name=segment['name'],changed_bytes=changed,dirty_pages=len(dirty),segment_bytes=len(raw),protection=segment['protection']))
  results.append(dict(label=stop['label'],changes=changes))
 parent=ROOT/'artifacts/native-early-c-verification';parent.mkdir(exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes());report=dict(passed=True,qemu_only=True,handset_executed=False,source_report=str(rp.relative_to(ROOT)),source_report_sha256=sha(rp.read_bytes()),kernel_sha256=sha(k),stops=results,baseline_all_original_except_declared_mmu_instrumentation=True,all_bootstrap_tables_unchanged=True,mutable_segments=[s for s in segments if s['name'] in ['__DATA_CONST','__DATA','__BOOTDATA']],scope='Observed original C up to arm_vm_init entry; no C-stage phone or Android-return verification')
 (out/'report.json').write_text(json.dumps(report,indent=2)+chr(10));print(out);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
