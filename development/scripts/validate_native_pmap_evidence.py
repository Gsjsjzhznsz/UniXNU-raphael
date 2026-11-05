#!/usr/bin/env python3
"""Independently verify original XNU pmap observations; no handset claim."""
import argparse,datetime as dt,json,struct,subprocess,tempfile,zlib
from pathlib import Path
from entry_probe import ROOT,sha
from native_early import image,make_policy as early_policy
from native_mmu import make_policy
from validate_native_load_evidence import inspect_build
MASK=0x0000fffffffff000

def verify(run,revision):
 report=json.loads((run/'report.json').read_text());spec=json.loads((run/'spec.json').read_text());trace=json.loads((run/'trace.json').read_text())
 assert report['passed'] and report['qemu_only'] and not report['handset_executed'] and trace['target_complete'] and trace==report['observation']
 for f in report['evidence_files']:
  path=(run/f['path']).resolve();assert path.is_relative_to(run) and sha(path.read_bytes())==f['sha256'],f['path']
 for name,source in [('runner.py','scripts/audit_native_pmap_qemu.py'),('observer.py','scripts/fixtures/native_pmap_gdb.py')]:assert (run/name).read_bytes()==(ROOT/source).read_bytes()
 qp=ROOT/report['positive_mmu_report'];q=json.loads(qp.read_text());assert sha(qp.read_bytes())==report['positive_mmu_report_sha256'] and q['passed'] and q['stage']==11
 bound=set();loaded,kernel,adt=inspect_build(qp.parent,q,revision,bound)
 assert sha(kernel)==report['kernel_sha256'];_,c=make_policy(kernel,adt,q['kernel_window'],62500000,0);_,early=early_policy(kernel,c);c['early']=early;c['instrumentation']=early['instrumentation']
 assert c==spec['contract']==q['native_mmu_contract'];assert spec['segments']==q['native_load_contract']['segments']
 command=q['command'];assert report['command']==command+['-S','-gdb','unix:'+spec['socket']+',server=on,wait=off']
 for option,expected in [('-kernel',loaded),('-dtb',(qp.parent/'qemu-virt.dtb').read_bytes())]:assert Path(command[command.index(option)+1]).read_bytes()==expected
 segments,symbols=image(kernel)
 def read(va,n):
  hits=[s for s in segments if s['virtual']<=va and va+n<=s['virtual']+s['file_bytes']];assert len(hits)==1
  s=hits[0];return kernel[s['offset']+va-s['virtual']:s['offset']+va-s['virtual']+n]
 def instruction(va):return struct.unpack('<I',read(va,4))[0]
 def bl_return(va,target):
  w=instruction(va-4);assert w>>26==0x25
  imm=w&0x3ffffff;imm-=0x4000000 if imm&0x2000000 else 0;assert va-4+4*imm==target
 names=['_set_mmu_ttb_alternate','_set_mmu_ttb','_PE_consistent_debug_inherit'];assert spec['targets']=={n:symbols[n] for n in names}
 assert list(struct.unpack('<4I',read(symbols[names[0]],16)))==[0xd5033f9f,0xd5182020,0xd5033fdf,0xd65f03c0]
 assert list(struct.unpack('<4I',read(symbols[names[1]],16)))==[0xd5033b9f,0xd5182000,0xd5033fdf,0xd65f03c0]
 stops=trace['stops'];assert [s['label'] for s in stops]==['arm-vm-entry','ttbr1-entry','ttbr1-return','ttbr0-entry','ttbr0-return','arm-vm-returned','pre-debug-inherit']
 assert [s['pc'] for s in stops]==[symbols['_arm_vm_init'],symbols[names[0]],stops[1]['lr'],symbols[names[1]],stops[3]['lr'],early['policy']['return_va'],symbols[names[2]]]
 for i,target in [(2,names[0]),(4,names[1]),(6,names[2])]:bl_return(stops[i]['pc'] if i!=6 else stops[i]['lr'],symbols[target])
 bl_return(stops[5]['pc'],symbols['_arm_vm_init'])
 new0=stops[3]['x0'];new1=stops[1]['x0'];assert new0!=new1 and new0&4095==new1&4095==0
 for i,s in enumerate(stops):
  assert s['ttbr0']==(c['tables_pa'] if i<4 else new0) and s['ttbr1']==(c['tables_pa']+4096 if i<2 else new1)
  assert all(s[n]==c['policy'][n] for n in ['tcr','mair','sctlr']) and s['vbar']==c['policy']['high_vectors'] and s['cpsr']&0x3df==0x3c4
  assert s['sp']==c['policy']['interrupt_sp']-early['policy']['frame_bytes']-(400 if 1<=i<=4 else 0)
 assert stops[0]['x0']==0 and stops[0]['x1']==early['policy']['const_args'] and stops[0]['lr']==early['policy']['return_va']
 a=trace['active_tables'];blob=(run/'active-tables.bin').read_bytes();assert len(blob)==a['bytes']==len(a['pages'])*4096 and sha(blob)==a['sha256']
 pages={};levels={};assert len(a['pages'])<=512
 for i,p in enumerate(a['pages']):
  pa=p['physical'];assert p['offset']==i*4096 and pa%4096==0 and pa not in pages and c['physical_base']<=pa<pa+4096<=c['physical_base']+c['window_bytes']
  raw=blob[i*4096:(i+1)*4096];assert sha(raw)==p['sha256'];pages[pa]=raw;levels[pa]=p['level']
 assert list(pages)==sorted(pages)
 reached={};descriptors=0
 def visit(pa,level):
  nonlocal descriptors
  assert pa in pages and levels[pa]==level and 1<=level<=3
  if pa in reached:assert reached[pa]==level;return
  reached[pa]=level
  for val in struct.unpack('<512Q',pages[pa]):
   if val==0:continue
   descriptors+=1;assert val&1
   if level<3 and val&3==3:visit(val&MASK,level+1)
   else:assert val&3==(3 if level==3 else 1)
 visit(new0,1);visit(new1,1);assert reached.keys()==pages.keys()
 def walk(va,high):
  tcr=stops[-1]['tcr'];assert ((tcr>>14)&3)==0 and ((tcr>>30)&3)==2
  bits=64-((tcr>>(16 if high else 0))&63);assert bits==38;va&=(1<<bits)-1;pa=new1 if high else new0
  for level in range(1,4):
   shift=12+9*(3-level);v=struct.unpack_from('<Q',pages[pa],8*((va>>shift)&511))[0]
   if not v&1:return None
   if level<3 and v&3==3:pa=v&MASK;continue
   assert v&3==(3 if level==3 else 1);low=(1<<shift)-1;return (v&MASK&~low)|(va&low)
  raise AssertionError('Incomplete walk')
 assert pages[new0]==bytes(4096) and a['root0_empty'] and not a['physical_relay_mapped']
 assert walk(c['low_vectors_pa']+2048,False) is None
 probes=[c['policy']['low_vectors'],c['policy']['high_vectors'],early['policy']['checkpoint'],symbols[names[2]]]
 assert a['high_probes']==[dict(virtual=va,physical=va+c['physical_delta']) for va in probes]
 for va in probes:assert walk(va,True)==va+c['physical_delta']
 count=0
 for seg in early['ranges']:
  for offset in range(0,seg['bytes'],4096):
   va=seg['virtual']+offset;assert walk(va,True)==va+c['physical_delta'];count+=1
 assert count==a['original_high_data_pages_verified']==644
 changes=[];baseline=[]
 for i,stop in enumerate(stops):
  per=[]
  for j,(segment,meta) in enumerate(zip(early['ranges'],stop['segments'])):
   original=kernel[segment['offset']:segment['offset']+segment['file_bytes']]+bytes(segment['bytes']-segment['file_bytes'])
   raw=(run/meta['file']).read_bytes();assert len(raw)==segment['bytes']==meta['bytes'] and meta['virtual']==segment['virtual'] and sha(raw)==meta['sha256']
   if i==0:baseline.append(raw)
   assert sum(x!=y for x,y in zip(baseline[j],raw))==meta['changed_bytes']
   assert sum(baseline[j][at:at+8]!=raw[at:at+8] for at in range(0,len(raw),8))==meta['changed_words']
   words=sum(original[at:at+8]!=raw[at:at+8] for at in range(0,len(raw),8))
   per.append(dict(name=segment['name'],bytes=len(raw),sha256=sha(raw),crc32=zlib.crc32(raw),words_changed_from_original=words,delta_bytes=words*12))
  delta=sum(x['delta_bytes'] for x in per);assert delta<=early['policy']['delta_capacity'];changes.append(dict(label=stop['label'],segments=per,delta_bytes=delta))
 assert b'Traceback' not in (run/'gdb.log').read_bytes()
 return dict(passed=True,qemu_only=True,handset_executed=False,full_xnu_boot_verified=False,implementation_revision=revision,source_files_bound=len(bound),observation_report=str((run/'report.json').relative_to(ROOT)),observation_report_sha256=sha((run/'report.json').read_bytes()),kernel_sha256=sha(kernel),stops=[{k:s[k] for k in ['label','pc','sp','lr','sctlr','tcr','mair','ttbr0','ttbr1']} for s in stops],active_table_pages=len(pages),active_table_bytes=len(blob),active_table_sha256=sha(blob),nonzero_descriptors=descriptors,high_data_pages_verified=count,ttbr0_empty=True,physical_relay_mapped=False,snapshots=changes,scope='Original arm_vm_init returned and original pmap active; no post-pmap Android return or handset execution')

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--revision',required=True);a=p.parse_args();revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.revision],text=True).strip()
 parent=ROOT/'artifacts/native-pmap-verification';parent.mkdir(exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True);(out/'verifier.py').write_bytes(Path(__file__).read_bytes())
 result=dict(passed=False)
 try:result=verify(a.run.resolve(),revision)
 except Exception as e:result['failure']=type(e).__name__+': '+str(e);raise
 finally:(out/'report.json').write_text(json.dumps(result,indent=2)+chr(10))
 print(json.dumps({k:result[k] for k in ['passed','source_files_bound','active_table_pages','high_data_pages_verified']},indent=2))
if __name__=='__main__':main()
