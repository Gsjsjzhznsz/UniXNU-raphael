#!/usr/bin/env python3
"""Audit frozen Git inputs, original images, full bootstrap tables, QEMU trace and handset MMU."""
import argparse,datetime as dt,json,lzma,re,struct,subprocess,tempfile,zlib
from pathlib import Path
from entry_probe import ROOT,sha
from validate_native_load_evidence import inspect_build,audit_adt
from validate_native_staging_evidence import git_bytes,file_read
from validate_android_return_evidence import load,chosen
from native_mmu import make_policy,decode as decode_mmu,audit_tables,FIELDS
from inspect_diagnostic_fd import inspect_fd,NATIVE_MMU_GUID
from native_load import decode as decode_load
from native_exit import decode_physical
from private_android_image import read_boot,repack
from payload_probe import decode as decode_payload
from kernel_window import check_log

def main():
 p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--qemu-audit',type=Path,required=True);a=p.parse_args()
 revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.revision],text=True).strip()
 parent=ROOT/'artifacts/native-mmu-verification';parent.mkdir(exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 report=dict(passed=False,implementation_revision=revision,verifier_sha256=sha(Path(__file__).read_bytes()))
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes())
 try:
  run=a.run.resolve();rr=load(run/'report.json');assert rr['passed'] and rr['stage']==10 and rr['native_mmu_verified'] and rr['xnu_executed']
  assert rr['unassisted_android_return'] and not rr.get('auto_recovered_from_bootloader') and not (run/'bootloader-recovery.json').exists()
  build=ROOT/rr['build'];br=load(build/'report.json');assert br['native_mmu_test'] and br['native_entry_test'] and br['native_exit_complete'] and sha((build/'report.json').read_bytes())==rr['build_report_sha256'];bound=set()
  image,kernel,adt=inspect_build(build,br,revision,bound)
  policy,contract=make_policy(kernel,adt,br['kernel_window'],19200000,0);assert contract==br['native_mmu_contract']
  def policy_in_image(image,desc,expected):
   l=desc['layout'];fd=image[l['FdBase']-l['ImageBase']:l['FdBase']-l['ImageBase']+l['FdSize']];structure=inspect_fd(fd,l['FdBase'])
   f=next(f for f in structure['files'] if f['guid']==NATIVE_MMU_GUID);[section]=f['sections']
   assert fd[section['offset']+4:section['offset']+section['bytes']]==expected
  assert policy==(build/'native-mmu-policy.bin').read_bytes();policy_in_image(image,br,policy)
  # Cross-check instruction names and symbols with both pinned Apple source
  # and the exact frozen kernel symbol table, independent of runtime records.
  apple=ROOT/'sources/apple-xnu-native'
  apple_revision=subprocess.check_output(['git','-C',str(apple),'rev-parse','HEAD'],text=True).strip();assert apple_revision=='d8b80295118ef25ac3a784134bcf95cd8e88109f'
  source=subprocess.check_output(['git','-C',str(apple),'show',apple_revision+':osfmk/arm64/start.s']);assert (apple/'osfmk/arm64/start.s').read_bytes()==source
  fragment=source.split(b'LEXT(start_first_cpu)',1)[1].split(b'// Get the kernel memory parameters',1)[0]
  assert re.search(rb'msr\s+OSLAR_EL1, xzr',fragment) and re.search(rb'msr\s+DAIFSet, #\(DAIFSC_ALL\)',fragment)
  assert re.search(rb'mov\s+x20, x0',fragment) and re.search(rb'mov\s+x21, #0',fragment)
  inspection=load(ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json');original_kernel=ROOT/inspection['artifact_directory']/'native-kernel.macho';assert original_kernel.read_bytes()==kernel
  nm=subprocess.check_output(['llvm-nm','--defined-only',str(original_kernel)],text=True);symbols={x[2]:int(x[0],16) for line in nm.splitlines() if len(x:=line.split())==3}
  assert symbols['_start_first_cpu']==contract['policy']['start'] and symbols['_arm_init']==contract['policy']['arm_init']
  for name,key in [('_LowExceptionVectorBase','low_vectors'),('_ExceptionVectorsBase','high_vectors'),('_bootstrap_pagetables','tables'),('_excepstack_top','exception_sp'),('_intstack_top','interrupt_sp')]:assert symbols[name]==contract['policy'][key]
  original=read_boot(ROOT/'evidence/private/device/20261027T120325Z');assert sha(original['raw'])==br['source_sha256']
  rd=(build/'expanded-ramdisk.bin').read_bytes();cap=br['capsule'];policy=cap['policy_words'];restored=lzma.decompress(rd[(cap['ramdisk_bytes']+7)&~7:],format=lzma.FORMAT_ALONE)
  assert restored==original['image'] and rd[:cap['ramdisk_bytes']]==original['ramdisk'] and zlib.crc32(restored)==policy[9]
  assert repack(original,image,ramdisk=rd)==(build/'boot-android-return.img').read_bytes() and sha((build/'boot-android-return.img').read_bytes())==rr['image_sha256']==br['image_sha256']
  f=chosen((run/'after.dtb').read_bytes());d=struct.unpack('>48Q',f.properties['raphael,sec-dxe']);w=struct.unpack('>10Q',f.properties['raphael,android-return'])
  assert f.strings('raphael,sec-dxe-id')==[br['identifier']] and list(d)==rr['sec_words'] and d[27:29]==(10,0)
  assert list(w)==rr['return_words'] and w[0:2]==(1,3) and w[2]==w[7]==policy[8] and w[3]==w[4]==policy[9] and w[8]==len(restored) and w[9]==1
  assert w[5:7]==(br['kernel_window']['base']+br['kernel_window']['bytes']-0x40000,br['kernel_window']['base']+br['kernel_window']['bytes'])
  assert int.from_bytes(f.properties['linux,initrd-end'],'big')-int.from_bytes(f.properties['linux,initrd-start'],'big')==len(original['ramdisk'])
  rawmmu=f.properties['raphael,native-mmu'];assert rawmmu==(run/'native-mmu-wire.bin').read_bytes()
  mmu=decode_mmu(rawmmu,contract);assert mmu==rr['native_mmu']
  tables=f.properties['raphael,native-mmu-tables'];assert tables==(run/'native-mmu-tables.bin').read_bytes()
  table_check=audit_tables(tables,mmu,contract);assert table_check==rr['native_mmu_tables']
  loaded=decode_load(f.properties['raphael,native-load'],br['native_load_contract']);assert loaded==rr['native_load'] and loaded['exit_boot_services_completed']
  physical=decode_physical((run/'after.dtb').read_bytes(),build);assert physical==rr['physical_timer_evidence'] and rr['physical_timer_verified']
  decode_payload(f.properties['raphael,payload-diagnostic'],br['layout'],6,native_staging=True)
  log=f.properties['raphael,sec-dxe-log'];assert log==(run/'sec-dxe.log').read_bytes() and file_read(log,br['layout'],kernel)==rr['staging_file_read'] and check_log(log,br['kernel_window'])['passed']
  assert b'DARWINBOOT: inputs validated; exiting boot services' in log
  darwin=struct.unpack('>18Q',f.properties['raphael,darwin-diagnostic']);assert darwin[3:6]==(1,1,0x20000) and darwin[13]==1
  adt_check=audit_adt(adt,(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes(),br['kernel_window'],19200000,0)
  qp=ROOT/br['qemu_evidence'];q=load(qp);assert q['passed'] and q['stage']==10 and sha(qp.read_bytes())==br['qemu_evidence_sha256']
  qi,qkernel,qadt=inspect_build(qp.parent,q,revision,bound);assert qkernel==kernel
  qpolicy,qc=make_policy(qkernel,qadt,q['kernel_window'],62500000,0);assert qc==q['native_mmu_contract']
  assert qpolicy==(qp.parent/'native-mmu-policy.bin').read_bytes();policy_in_image(qi,q,qpolicy)
  qlog=(qp.parent/'serial.log').read_bytes();m=re.search(rb'NATIVE_MMU_WIRE ([0-9a-f]+)',qlog);t=re.search(rb'NATIVE_MMU_TABLES ([0-9a-f]+)',qlog);assert m and t
  qm=decode_mmu(bytes.fromhex(m[1].decode()),qc);assert qm==q['native_mmu_observation']
  assert audit_tables(bytes.fromhex(t[1].decode()),qm,qc)==q['native_mmu_tables']
  assert b'ANDROID_RETURN_QEMU_OK' in qlog and b'FAIL ' not in qlog
  auditp=a.qemu_audit.resolve();assert br['qemu_mmu_audit']==str(auditp.relative_to(ROOT)) and br['qemu_mmu_audit_sha256']==sha(auditp.read_bytes());audit=load(auditp);assert audit['passed'] and audit['positive_report']==str(qp.relative_to(ROOT)) and audit['positive_report_sha256']==sha(qp.read_bytes())
  assert (auditp.parent/'runner.py').read_bytes()==git_bytes('scripts/audit_native_mmu_qemu.py',revision)
  for item in audit['evidence_files']:assert sha((auditp.parent/item['path']).read_bytes())==item['sha256']
  assert [x['case'] for x in audit['cases']]==['trace','wrong-brk','bad-table']
  for case in audit['cases']:
   base=auditp.parent/case['case'];raw=(base/'serial.log').read_bytes();gdb=(base/'gdb.log').read_bytes();assert b'Breakpoint 1,' in gdb and b'Traceback' not in gdb
   assert (base/'observer.py').read_bytes()==git_bytes('scripts/fixtures/native_mmu_gdb.py',revision)
   m=re.search(rb'NATIVE_MMU_WIRE ([0-9a-f]+)',raw);t=re.search(rb'NATIVE_MMU_TABLES ([0-9a-f]+)',raw);assert m and t
   wire=bytes.fromhex(m[1].decode());ts=bytes.fromhex(t[1].decode());values=dict(zip(FIELDS,struct.unpack('>72Q',wire)))
   assert values==case['mmu'] and wire==(base/'wire.bin').read_bytes() and ts==(base/'tables.bin').read_bytes()
   assert b'PASS real high stub decode completed' in raw
   assert all(values[n]==1 for n in ['patch_restored','tables_restored','mmu_restored','trap_count'])
   trace=load(base/'trace.json');assert trace==case['trace']
   if case['case']=='trace':
    decode_mmu(wire,qc);assert audit_tables(ts,values,qc)==case['tables'] and b'ANDROID_RETURN_QEMU_OK' in raw and case['returncode']==0
    assert len(trace)==9 and trace[0]['pc']==qc['mmu_enable_pa'] and trace[0]['sctlr']&0x1005==0
    assert trace[0]['tcr']==qc['policy']['tcr'] and trace[0]['ttbr0']==qc['tables_pa'] and trace[0]['ttbr1']==qc['tables_pa']+4096
    assert trace[1]['sctlr']==trace[2]['sctlr']==qc['policy']['sctlr']
    assert trace[3]['pc']==qc['policy']['arm_init'] and trace[3]['x0']==qc['args']-qc['physical_delta'] and trace[3]['sp']==qc['policy']['interrupt_sp']
    assert trace[4]['pc']==qc['policy']['high_vectors'] and trace[7]['pc']==qc['low_vectors_pa']+2048 and trace[8]['sctlr']&0x1005==0
   else:
    assert values['status']==2 and values['error']==2 and values['esr']==(0xf2005352 if case['case']=='wrong-brk' else 0xf2005351) and values['elr']==qc['policy']['arm_init']
    assert b'ANDROID_RETURN_QEMU_FAILED' in raw and case['returncode']!=0
    try:decode_mmu(wire,qc)
    except AssertionError:pass
    else:raise AssertionError('Negative state accepted')
    if case['case']=='bad-table':
     damaged=trace[-1];assert damaged['original_descriptor']^damaged['corrupt_descriptor']==0x200000
     offset=damaged['corrupt_address']-values['tables'];assert struct.unpack_from('<Q',ts,offset)[0]==damaged['corrupt_descriptor']
     try:audit_tables(ts,values,qc)
     except AssertionError:pass
     else:raise AssertionError('Damaged snapshot accepted')
  for name in ['before.dtb','cleanup.dtb']:assert not any(k.startswith('raphael,') for k in chosen((run/name).read_bytes()).properties)
  commands=load(run/'commands.json');boots=[x for x in commands if 'fastboot.exe' in x['command'][0] and 'boot' in x['command']]
  assert len(boots)==1 and boots[0]['returncode']==0 and not any(set(x['command'])&{'flash','erase','format'} for x in commands)
  for x in commands:
   if x.get('file'):assert sha((run/x['file']).read_bytes())==x['sha256']
  hashes=[x for x in commands if any('sha256sum /dev/block/bootdevice/by-name/boot' in v for v in x['command'])]
  assert len(hashes)>=3 and all(x['returncode']==0 and x['stdout'].split()[0]==br['source_sha256'] for x in hashes)
  assert (run/'before-boot-id.txt').read_bytes()!=(run/'after-boot-id.txt').read_bytes()
  assert all(rr[k] for k in ['cleanup_android_completed','cleanup_root_verified','cleanup_boot_unchanged','cleanup_transient_properties_absent'])
  report.update(passed=True,private_run=str(run.relative_to(ROOT)),private_build=str(build.relative_to(ROOT)),run_report_sha256=sha((run/'report.json').read_bytes()),build_report_sha256=sha((build/'report.json').read_bytes()),image_sha256=br['image_sha256'],firmware_sha256=br['firmware_sha256'],kernel_sha256=sha(kernel),adt=adt_check,loaded_memory=loaded,mmu=mmu,bootstrap_tables=table_check,physical_timer=physical,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),qemu_audit=str(auditp.relative_to(ROOT)),qemu_audit_sha256=sha(auditp.read_bytes()),git_bound_input_count=len(bound),source_paths=sorted(bound),apple_start_source_sha256=sha(source),xnu_handset_instrumented_bootstrap_executed=True,arm_init_reached=True,arm_init_c_body_executed=False,full_xnu_boot_verified=False,limits=['Original bootstrap MMU reaches first arm_init instruction, temporarily replaced by BRK','Original vector entries relay to diagnostic code; not normal XNU fault handling','No arm_init C body, platform GIC/timer, root volume or userspace','No UART wiring or output claim; transient in-memory evidence'])
 except Exception as e:
  report['failure']=type(e).__name__+': '+str(e);raise
 finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(passed=report['passed'],git_bound_inputs=len(bound),arm_init_reached=mmu['arm_init_entry_reached'],table_bytes=table_check['bytes']),indent=2))
if __name__=='__main__':main()
