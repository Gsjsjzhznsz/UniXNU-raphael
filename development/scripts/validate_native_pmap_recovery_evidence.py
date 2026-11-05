#!/usr/bin/env python3
"""Bind post-pmap handset recovery to frozen source and original raw evidence."""
import argparse,datetime as dt,json,lzma,re,struct,subprocess,tempfile,zlib
from pathlib import Path
from entry_probe import ROOT,sha
from validate_native_load_evidence import inspect_build,audit_adt,parse_adt
from validate_native_staging_evidence import git_bytes,file_read
from validate_android_return_evidence import load,chosen
from native_mmu import make_policy,decode as decode_mmu,audit_tables,FIELDS
from native_early import make_policy as early_policy,decode as decode_early
from native_pmap import decode as decode_pmap,FIELDS as PF
from inspect_diagnostic_fd import inspect_fd,NATIVE_MMU_GUID,NATIVE_EARLY_GUID
from native_load import decode as decode_load
from native_exit import decode_physical
from private_android_image import read_boot,repack
from payload_probe import decode as decode_payload
from kernel_window import check_log

def contract(kernel,adt,br):
 raw,c=make_policy(kernel,adt,br['kernel_window'],br['native_mmu_contract']['frequency'],br['native_mmu_contract']['affinity']);ep,e=early_policy(kernel,c,pmap=True);c['early']=e;c['instrumentation']=e['instrumentation'];assert c==br['native_mmu_contract'];return raw,ep,c

def policies(image,br,policy,early):
 l=br['layout'];fd=image[l['FdBase']-l['ImageBase']:l['FdBase']-l['ImageBase']+l['FdSize']];s=inspect_fd(fd,l['FdBase'])
 for guid,raw in [(NATIVE_MMU_GUID,policy),(NATIVE_EARLY_GUID,early)]:
  [f]=[f for f in s['files'] if f['guid']==guid];[sec]=f['sections'];assert fd[sec['offset']+4:sec['offset']+sec['bytes']]==raw

def properties(f,base,kernel,adt,c):
 names={'mmu-wire':'raphael,native-mmu','bootstrap-tables':'raphael,native-mmu-tables','early-wire':'raphael,native-early-c','early-delta':'raphael,native-early-delta','pmap-wire':'raphael,native-pmap','pmap-tables':'raphael,native-pmap-tables','pmap-transition':'raphael,native-pmap-transition','pmap-adt':'raphael,native-pmap-adt'}
 raw={k:f.properties[v] for k,v in names.items()}
 for key,data in raw.items():
  name={'mmu-wire':'native-mmu-wire.bin','bootstrap-tables':'native-mmu-tables.bin','early-wire':'native-early-wire.bin','early-delta':'native-early-delta.bin'}.get(key,'native-'+key+'.bin');assert (base/name).read_bytes()==data,name
 mmu=decode_mmu(raw['mmu-wire'],c);bootstrap=audit_tables(raw['bootstrap-tables'],mmu,c);early=decode_early(raw['early-wire'],raw['early-delta'],kernel,c,mmu,raw['bootstrap-tables']);pmap=decode_pmap(raw['pmap-wire'],raw['pmap-tables'],raw['pmap-transition'],raw['pmap-adt'],adt,c,mmu)
 return mmu,bootstrap,early,pmap

def audit_qemu(qp,ap,kernel,adt,c,revision):
 a=load(ap);assert a['passed'] and a['positive_report']==str(qp.relative_to(ROOT)) and a['positive_report_sha256']==sha(qp.read_bytes())
 assert (ap.parent/'runner.py').read_bytes()==git_bytes('scripts/audit_native_pmap_recovery_qemu.py',revision)
 for f in a['evidence_files']:assert sha((ap.parent/f['path']).read_bytes())==f['sha256']
 assert [x['case'] for x in a['cases']]==['trace','wrong-brk','bad-active-table','transition-corrupt','backup-corrupt']
 for case in a['cases']:
  base=ap.parent/case['case'];assert case['passed'] and (base/'observer.py').read_bytes()==git_bytes('scripts/fixtures/native_pmap_recovery_gdb.py',revision)
  log=(base/'serial.log').read_bytes();g=(base/'gdb.log').read_bytes();assert b'Traceback' not in g and b'PASS real high stub decode completed' in log
  def raw(tag,name):
   m=re.search(tag.encode()+rb' ([0-9a-f]+)',log);assert m;b=bytes.fromhex(m[1].decode());assert b==(base/name).read_bytes();return b
  mw=raw('NATIVE_MMU_WIRE','mmu-wire.bin');ts=raw('NATIVE_MMU_TABLES','bootstrap-tables.bin');ew=raw('NATIVE_EARLY_WIRE','early-wire.bin');ed=raw('NATIVE_EARLY_DELTA','early-delta.bin');pw=raw('NATIVE_PMAP_WIRE','pmap-wire.bin');ps=raw('NATIVE_PMAP_TABLES','pmap-tables.bin');pt=raw('NATIVE_PMAP_TRANSITION','pmap-transition.bin');pa=raw('NATIVE_PMAP_ADT','pmap-adt.bin')
  mmu=dict(zip(FIELDS,struct.unpack('>72Q',mw)));pmap=dict(zip(PF,struct.unpack('>32Q',pw)));assert mmu==case['mmu'] and pmap==case['pmap_words'];assert audit_tables(ts,mmu,c)==case['bootstrap']
  assert all(mmu[k]==1 for k in ['trap_count','patch_restored','tables_restored','mmu_restored']) and pmap['adt_restored']==pmap['adt_backup_ok']==1
  t=load(base/'trace.json');assert t==case['trace']
  if case['case']=='trace':
   decoded=decode_pmap(pw,ps,pt,pa,adt,c,decode_mmu(mw,c));assert decoded==case['pmap'];assert case['returncode']==0 and b'ANDROID_RETURN_QEMU_OK' in log and b'FAIL ' not in log
   assert [x['label'] for x in t]==['arm-vm-entry','ttbr1-entry','ttbr1-return','ttbr0-entry','ttbr0-return','arm-vm-returned','checkpoint','exception-vector','high-prefix','before-transition','after-transition','physical-body','clean-first-line','cache-off','captured']
   old0=t[3]['x0'];old1=t[1]['x0'];transition=decoded['transition_base'];assert t[0]['ttbr0']==c['tables_pa'] and t[0]['ttbr1']==c['tables_pa']+4096
   assert t[2]['ttbr1']==old1 and t[4]['ttbr0']==old0 and t[5]['pc']==t[0]['lr'] and t[6]['pc']==c['early']['policy']['checkpoint'] and t[6]['lr']==c['early']['policy']['return_va']
   assert t[8]['pc']==c['policy']['low_vectors']+2048 and t[8]['ttbr0']==old0
   assert t[9]['x8']==old0 and t[9]['x16']==transition and t[10]['ttbr0']==t[11]['ttbr0']==transition and t[11]['ttbr1']==old1
   assert t[12]['x13']==c['physical_base'] and t[12]['x14']==c['physical_base']+c['window_bytes'] and t[12]['x10'] in [16,32,64,128,256,512,1024,2048]
   assert t[13]['sctlr']&0x1005==0 and t[13]['x8']==old0 and t[13]['ttbr0']==transition
   blob=(base/'active-tables.bin').read_bytes();assert sha(blob)==decoded['table_snapshot_sha256'];pages=load(base/'active-pages.json');assert len(pages)==decoded['table_pages']
   bypa={x['physical']:x for x in decoded['pages']}
   for i,page in enumerate(pages):assert page['offset']==i*4096 and sha(blob[i*4096:(i+1)*4096])==page['sha256']==bypa[page['physical']]['sha256'] and page['level']==bypa[page['physical']]['level']
   assert (base/'transition.bin').read_bytes()==pt and (base/'adt.bin').read_bytes()==pa
  else:
   assert mmu['status']==2 and mmu['error']==2 and case['returncode']!=0 and b'ANDROID_RETURN_QEMU_FAILED' in log
   assert mmu['elr']==c['early']['policy']['checkpoint'] and mmu['esr']==(0xf2005352 if case['case']=='wrong-brk' else 0xf2005351)
   try:decode_mmu(mw,c)
   except AssertionError:pass
   else:raise AssertionError('Negative MMU accepted')
   if case['case'] in ['bad-active-table','transition-corrupt']:
    assert pmap['status']==2 and pmap['error']==1
    try:decode_pmap(pw,ps,pt,pa,adt,c,mmu)
    except AssertionError:pass
    else:raise AssertionError('Negative pmap accepted')
    if case['case']=='bad-active-table':assert pmap['high_data_pages']==643 and t[-1]['before']^t[-1]['after']==4096
    else:assert pmap['transition_ok']==0 and t[-1]['before']==0 and t[-1]['after']==1 and pmap['transition_crc_before']!=pmap['transition_crc_after']
   else:assert decode_pmap(pw,ps,pt,pa,adt,c,mmu)==case['pmap']
  if case['case']=='backup-corrupt':
   ev=struct.unpack('>40Q',ew);assert ev[1:3]==(2,1) and ev[14]==2 and mmu['segments_ok']==9 and t[-1]['before']^t[-1]['after']==1
  else:
   early=decode_early(ew,ed,kernel,c,mmu,ts);assert early==case['early']
   if case['case']=='trace':
    for i,rg in enumerate(early['ranges']):assert sha((base/('range-'+str(i)+'.bin')).read_bytes())==rg['snapshot_sha256']
 return dict(passed=True,cases=5,report=str(ap.relative_to(ROOT)),sha256=sha(ap.read_bytes()))

def main():
 p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--run',type=Path);p.add_argument('--qemu-report',type=Path);p.add_argument('--qemu-audit',type=Path,required=True);a=p.parse_args();revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.revision],text=True).strip()
 parent=ROOT/'artifacts/native-pmap-recovery-verification';parent.mkdir(exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True);(out/'verifier.py').write_bytes(Path(__file__).read_bytes());report=dict(passed=False,implementation_revision=revision,handset_executed=bool(a.run));bound=set()
 try:
  rr=None;br=None
  if a.run:
   run=a.run.resolve();rr=load(run/'report.json');assert rr['passed'] and rr['stage']==12 and rr['native_pmap_verified'] and rr['native_mmu_verified'] and rr['native_early_verified'] and rr['xnu_executed'] and rr['unassisted_android_return'] and not rr.get('auto_recovered_from_bootloader') and not (run/'bootloader-recovery.json').exists()
   build=ROOT/rr['build'];br=load(build/'report.json');assert br['native_pmap_test'] and sha((build/'report.json').read_bytes())==rr['build_report_sha256'];im,kernel,adt=inspect_build(build,br,revision,bound);mp,ep,c=contract(kernel,adt,br);policies(im,br,mp,ep)
   mmu,bt,early,pmap=properties(chosen((run/'after.dtb').read_bytes()),run,kernel,adt,c)
   assert mmu==rr['native_mmu'] and bt==rr['native_mmu_tables'] and early==rr['native_early'] and pmap==rr['native_pmap']
   original=read_boot(ROOT/'evidence/private/device/20261027T120325Z');assert sha(original['raw'])==br['source_sha256'];rd=(build/'expanded-ramdisk.bin').read_bytes();cap=br['capsule'];policy=cap['policy_words'];restored=lzma.decompress(rd[(cap['ramdisk_bytes']+7)&~7:],format=lzma.FORMAT_ALONE);assert restored==original['image'] and rd[:cap['ramdisk_bytes']]==original['ramdisk'] and repack(original,im,ramdisk=rd)==(build/'boot-android-return.img').read_bytes();assert sha((build/'boot-android-return.img').read_bytes())==br['image_sha256']==rr['image_sha256']
   f=chosen((run/'after.dtb').read_bytes());sec=struct.unpack('>48Q',f.properties['raphael,sec-dxe']);ret=struct.unpack('>10Q',f.properties['raphael,android-return']);assert list(sec)==rr['sec_words'] and sec[27:29]==(12,0) and list(ret)==rr['return_words'] and ret[0:2]==(1,3) and ret[2]==ret[7]==policy[8] and ret[3]==ret[4]==zlib.crc32(restored)==policy[9] and ret[8]==len(restored) and ret[9]==1
   assert decode_load(f.properties['raphael,native-load'],br['native_load_contract'])==rr['native_load'] and rr['native_load']['exit_boot_services_completed'];assert decode_physical((run/'after.dtb').read_bytes(),build)==rr['physical_timer_evidence'] and rr['physical_timer_verified'];decode_payload(f.properties['raphael,payload-diagnostic'],br['layout'],6,native_staging=True)
   log=f.properties['raphael,sec-dxe-log'];assert log==(run/'sec-dxe.log').read_bytes() and file_read(log,br['layout'],kernel)==rr['staging_file_read'] and check_log(log,br['kernel_window'])['passed'];assert b'DARWINBOOT: inputs validated; exiting boot services' in log
   audit_adt(adt,(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes(),br['kernel_window'],19200000,0)
   commands=load(run/'commands.json');boots=[x for x in commands if 'fastboot.exe' in x['command'][0] and 'boot' in x['command']];assert len(boots)==1 and boots[0]['returncode']==0 and not any(set(x['command'])&{'flash','erase','format'} for x in commands)
   for x in commands:
    if x.get('file'):assert sha((run/x['file']).read_bytes())==x['sha256']
   hashes=[x for x in commands if any('sha256sum /dev/block/bootdevice/by-name/boot' in y for y in x['command'])];assert len(hashes)>=3 and all(x['returncode']==0 and x['stdout'].split()[0]==br['source_sha256'] for x in hashes)
   for name in ['before.dtb','cleanup.dtb']:assert not any(k.startswith('raphael,') for k in chosen((run/name).read_bytes()).properties)
   assert (run/'before-boot-id.txt').read_bytes()!=(run/'after-boot-id.txt').read_bytes() and all(rr[k] for k in ['cleanup_android_completed','cleanup_root_verified','cleanup_boot_unchanged','cleanup_transient_properties_absent'])
   qp=ROOT/br['qemu_evidence'];assert sha(qp.read_bytes())==br['qemu_evidence_sha256'] and br['qemu_mmu_audit']==str(a.qemu_audit.resolve().relative_to(ROOT)) and br['qemu_mmu_audit_sha256']==sha(a.qemu_audit.read_bytes())
   report.update(run=str(run.relative_to(ROOT)),boot_sha256=br['image_sha256'],firmware_sha256=br['firmware_sha256'],mmu=mmu,early=early,pmap=pmap,unassisted_android_return=True,cleanup_verified=True,fdt_bytes=len((run/'after.dtb').read_bytes()))
  else:assert a.qemu_report;qp=a.qemu_report.resolve()
  q=load(qp);assert q['passed'] and q['stage']==12 and q['native_pmap_test'];qi,qk,qa=inspect_build(qp.parent,q,revision,bound);mp,ep,qc=contract(qk,qa,q);policies(qi,q,mp,ep)
  if rr:assert qk==kernel
  raw=(qp.parent/'serial.log').read_bytes();assert b'ANDROID_RETURN_QEMU_OK' in raw and b'FAIL ' not in raw
  def lograw(tag):
   m=re.search(tag.encode()+rb' ([0-9a-f]+)',raw);assert m;return bytes.fromhex(m[1].decode())
  qm=decode_mmu(lograw('NATIVE_MMU_WIRE'),qc);assert qm==q['native_mmu_observation'];qt=lograw('NATIVE_MMU_TABLES');assert audit_tables(qt,qm,qc)==q['native_mmu_tables'];assert decode_early(lograw('NATIVE_EARLY_WIRE'),lograw('NATIVE_EARLY_DELTA'),qk,qc,qm,qt)==q['native_early_observation'];assert decode_pmap(lograw('NATIVE_PMAP_WIRE'),lograw('NATIVE_PMAP_TABLES'),lograw('NATIVE_PMAP_TRANSITION'),lograw('NATIVE_PMAP_ADT'),qa,qc,qm)==q['native_pmap_observation']
  audit=audit_qemu(qp,a.qemu_audit.resolve(),qk,qa,qc,revision)
  apple=ROOT/'sources/apple-xnu-native';assert subprocess.check_output(['git','-C',str(apple),'rev-parse','HEAD'],text=True).strip()=='d8b80295118ef25ac3a784134bcf95cd8e88109f'
  for name in ['osfmk/arm64/arm_vm_init.c','pexpert/gen/pe_gen.c','pexpert/pexpert/arm/consistent_debug.h']:
   assert (apple/name).read_bytes()==subprocess.check_output(['git','-C',str(apple),'show','HEAD:'+name])
  assert b'*src_random_seed = (unsigned char)0;' in (apple/'pexpert/gen/pe_gen.c').read_bytes() and b'PE_consistent_debug_inherit(void);' in (apple/'pexpert/pexpert/arm/consistent_debug.h').read_bytes()
  report.update(passed=True,source_files_bound=len(bound),qemu_audit=audit,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),kernel_sha256=sha(qk),full_xnu_boot_verified=False,scope='Original arm_vm_init return and bounded table/data/ADT diagnostics; no normal XNU IRQ, root volume or userland claim')
 except Exception as e:report['failure']=type(e).__name__+': '+str(e);raise
 finally:(out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
 print(json.dumps({k:report[k] for k in ['passed','handset_executed','source_files_bound']},indent=2))
if __name__=='__main__':main()
