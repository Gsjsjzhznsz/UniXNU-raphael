#!/usr/bin/env python3
"""Audit frozen Git inputs, original images, QEMU trace and raw handset entry."""
import argparse,datetime as dt,json,lzma,re,struct,subprocess,tempfile,zlib
from pathlib import Path
from entry_probe import ROOT,sha
from validate_native_load_evidence import inspect_build,audit_adt
from validate_native_staging_evidence import git_bytes,file_read
from validate_android_return_evidence import load,chosen
from native_entry import make_contract,decode as decode_entry,FIELDS
from native_load import decode as decode_load
from native_exit import decode_physical
from private_android_image import read_boot,repack
from payload_probe import decode as decode_payload
from kernel_window import check_log

def main():
 p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--qemu-audit',type=Path,required=True);a=p.parse_args()
 revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.revision],text=True).strip()
 parent=ROOT/'artifacts/native-entry-verification';parent.mkdir(exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 report=dict(passed=False,implementation_revision=revision,verifier_sha256=sha(Path(__file__).read_bytes()))
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes())
 try:
  run=a.run.resolve();rr=load(run/'report.json');assert rr['passed'] and rr['stage']==9 and rr['native_entry_verified'] and rr['xnu_executed']
  assert rr['unassisted_android_return'] and not rr.get('auto_recovered_from_bootloader') and not (run/'bootloader-recovery.json').exists()
  build=ROOT/rr['build'];br=load(build/'report.json');assert br['native_entry_test'] and br['native_exit_complete'] and sha((build/'report.json').read_bytes())==rr['build_report_sha256'];bound=set()
  image,kernel,adt=inspect_build(build,br,revision,bound)
  contract=make_contract(kernel,adt,br['kernel_window'],19200000,0);assert contract==br['native_entry_contract']
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
  assert symbols['_start_first_cpu']==contract['first_cpu_virtual'] and symbols['__start']==contract['xnu_entry_virtual']
  original=read_boot(ROOT/'evidence/private/device/20261027T120325Z');assert sha(original['raw'])==br['source_sha256']
  rd=(build/'expanded-ramdisk.bin').read_bytes();cap=br['capsule'];policy=cap['policy_words'];restored=lzma.decompress(rd[(cap['ramdisk_bytes']+7)&~7:],format=lzma.FORMAT_ALONE)
  assert restored==original['image'] and rd[:cap['ramdisk_bytes']]==original['ramdisk'] and zlib.crc32(restored)==policy[9]
  assert repack(original,image,ramdisk=rd)==(build/'boot-android-return.img').read_bytes() and sha((build/'boot-android-return.img').read_bytes())==rr['image_sha256']==br['image_sha256']
  f=chosen((run/'after.dtb').read_bytes());d=struct.unpack('>48Q',f.properties['raphael,sec-dxe']);w=struct.unpack('>10Q',f.properties['raphael,android-return'])
  assert f.strings('raphael,sec-dxe-id')==[br['identifier']] and list(d)==rr['sec_words'] and d[27:29]==(9,0)
  assert list(w)==rr['return_words'] and w[0:2]==(1,3) and w[2]==w[7]==policy[8] and w[3]==w[4]==policy[9] and w[8]==len(restored) and w[9]==1
  assert w[5:7]==(br['kernel_window']['base']+br['kernel_window']['bytes']-0x40000,br['kernel_window']['base']+br['kernel_window']['bytes'])
  assert int.from_bytes(f.properties['linux,initrd-end'],'big')-int.from_bytes(f.properties['linux,initrd-start'],'big')==len(original['ramdisk'])
  rawentry=f.properties['raphael,native-entry'];assert rawentry==(run/'native-entry-wire.bin').read_bytes()
  entry=decode_entry(rawentry,contract,br['layout']);assert entry==rr['native_entry']
  loaded=decode_load(f.properties['raphael,native-load'],br['native_load_contract']);assert loaded==rr['native_load'] and loaded['exit_boot_services_completed']
  physical=decode_physical((run/'after.dtb').read_bytes(),build);assert physical==rr['physical_timer_evidence'] and rr['physical_timer_verified']
  decode_payload(f.properties['raphael,payload-diagnostic'],br['layout'],6,native_staging=True)
  log=f.properties['raphael,sec-dxe-log'];assert log==(run/'sec-dxe.log').read_bytes() and file_read(log,br['layout'],kernel)==rr['staging_file_read'] and check_log(log,br['kernel_window'])['passed']
  assert b'DARWINBOOT: inputs validated; exiting boot services' in log
  darwin=struct.unpack('>18Q',f.properties['raphael,darwin-diagnostic']);assert darwin[3:6]==(1,1,0x20000) and darwin[13]==1
  adt_check=audit_adt(adt,(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes(),br['kernel_window'],19200000,0)
  qp=ROOT/br['qemu_evidence'];q=load(qp);assert q['passed'] and q['stage']==9 and sha(qp.read_bytes())==br['qemu_evidence_sha256']
  _,qkernel,qadt=inspect_build(qp.parent,q,revision,bound);assert qkernel==kernel
  assert make_contract(qkernel,qadt,q['kernel_window'],62500000,0)==q['native_entry_contract']
  qlog=(qp.parent/'serial.log').read_bytes();match=re.search(rb'NATIVE_ENTRY_WIRE ([0-9a-f]+)',qlog);assert match
  assert decode_entry(bytes.fromhex(match[1].decode()),q['native_entry_contract'],q['layout'])==q['native_entry_observation']
  assert b'ANDROID_RETURN_QEMU_OK' in qlog and b'FAIL ' not in qlog
  auditp=a.qemu_audit.resolve();audit=load(auditp);assert audit['passed'] and audit['positive_report']==str(qp.relative_to(ROOT)) and audit['positive_report_sha256']==sha(qp.read_bytes())
  assert (auditp.parent/'runner.py').read_bytes()==git_bytes('scripts/audit_native_entry_qemu.py',revision)
  for item in audit['evidence_files']:assert sha((auditp.parent/item['path']).read_bytes())==item['sha256']
  assert [x['case'] for x in audit['cases']]==['trace','wrong-brk']
  trace=load(auditp.parent/'trace/trace.json');qc=q['native_entry_contract'];expected=[qc['entry']]+[qc['checkpoint']-16+4*i for i in range(5)]
  assert [x['pc'] for x in trace[:6]]==expected and all(x['x0']==qc['args'] and x['x1']==qc['entry'] for x in trace)
  assert trace[4]['x20']==trace[5]['x20']==qc['args'] and trace[5]['x21']==0
  for case in audit['cases']:
   raw=(auditp.parent/case['case']/'serial.log').read_bytes();gdb=(auditp.parent/case['case']/'gdb.log').read_bytes();assert b'Breakpoint 1,' in gdb and b'Traceback' not in gdb
   m=re.search(rb'NATIVE_ENTRY_WIRE ([0-9a-f]+)',raw);assert m;wire=bytes.fromhex(m[1].decode());values=dict(zip(FIELDS,struct.unpack('>40Q',wire)));assert values==case['entry']
   assert b'PASS real high stub decode completed' in raw
   if case['case']=='trace':
    decode_entry(wire,qc,q['layout']);assert b'ANDROID_RETURN_QEMU_OK' in raw and case['returncode']==0
    assert trace[-1]['pc']==values['vbar']+values['vector_slot']*128
   else:
    assert values['status']==2 and values['error'] and values['esr']==0xf2005351 and values['elr']==qc['checkpoint'] and values['patch_restored']==values['mmu_restored']==1
    assert b'ANDROID_RETURN_QEMU_FAILED' in raw and case['returncode']!=0
  for name in ['before.dtb','cleanup.dtb']:assert not any(k.startswith('raphael,') for k in chosen((run/name).read_bytes()).properties)
  commands=load(run/'commands.json');boots=[x for x in commands if 'fastboot.exe' in x['command'][0] and 'boot' in x['command']]
  assert len(boots)==1 and boots[0]['returncode']==0 and not any(set(x['command'])&{'flash','erase','format'} for x in commands)
  for x in commands:
   if x.get('file'):assert sha((run/x['file']).read_bytes())==x['sha256']
  hashes=[x for x in commands if any('sha256sum /dev/block/bootdevice/by-name/boot' in v for v in x['command'])]
  assert len(hashes)>=3 and all(x['returncode']==0 and x['stdout'].split()[0]==br['source_sha256'] for x in hashes)
  assert (run/'before-boot-id.txt').read_bytes()!=(run/'after-boot-id.txt').read_bytes()
  assert all(rr[k] for k in ['cleanup_android_completed','cleanup_root_verified','cleanup_boot_unchanged','cleanup_transient_properties_absent'])
  report.update(passed=True,private_run=str(run.relative_to(ROOT)),private_build=str(build.relative_to(ROOT)),run_report_sha256=sha((run/'report.json').read_bytes()),build_report_sha256=sha((build/'report.json').read_bytes()),image_sha256=br['image_sha256'],firmware_sha256=br['firmware_sha256'],kernel_sha256=sha(kernel),adt=adt_check,loaded_memory=loaded,entry=entry,physical_timer=physical,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),qemu_audit=str(auditp.relative_to(ROOT)),qemu_audit_sha256=sha(auditp.read_bytes()),git_bound_input_count=len(bound),source_paths=sorted(bound),apple_start_source_sha256=sha(source),xnu_handset_instrumented_prefix_executed=True,arm_init_reached=False,full_xnu_boot_verified=False,limits=['Only five original XNU instructions before the temporary BRK','No XNU-owned VBAR, page tables, GIC/timer, root volume or userspace','No UART wiring or output claim; transient in-memory evidence'])
 except Exception as e:
  report['failure']=type(e).__name__+': '+str(e);raise
 finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(passed=report['passed'],git_bound_inputs=len(bound),original_instructions=entry['original_instruction_count']),indent=2))
if __name__=='__main__':main()
