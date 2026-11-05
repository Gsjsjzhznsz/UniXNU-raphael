#!/usr/bin/env python3
"""Native large FAT/pool read with a sparse Image and preserved initrd hole."""
import argparse,datetime as dt,json,struct,subprocess,tempfile,time,re
from pathlib import Path
from entry_probe import ROOT,image_parameters,sha,align,run
from android_return import build_stub,capsule
from build_psci_reset import compile_image
from build_sec_dxe import build_firmware
from run_android_return_qemu import build_receiver
from inspect_diagnostic_fd import inspect_fd
from native_staging import freeze_workflow, NATIVE_RETURN_FDT_BYTES
from qemu_arch_probe import generate_resources
from inspect_device import read_fdt,registers
from kernel_window import BLOCK,WINDOW,check_log

def main():
 p=argparse.ArgumentParser();p.add_argument('--watchdog-client-abi-fixture',action='store_true',help='Original abstract-class ancestry and service publication only; no simulated hardware qualification');p.add_argument('--inherited-display-fixture',action='store_true',help='Exercise exact display opt-in and original-family loading with headless QEMU Boot_Video; no panel or frame proof');p.add_argument('--kernel-window-mib',type=int,choices=[256,512,704],default=256);p.add_argument('--unaligned-io-bus-fixture',action='store_true',help='Rebase the synthetic IO bus by 16KiB; actual QEMU GIC physical addresses stay unchanged');p.add_argument('--dt-platform-fixture',action='store_true',help='Select generic ArmDTPlatform with an explicit QEMU policy identity, retaining actual QEMU hardware resources');p.add_argument('--pmgr-nub-fixture',action='store_true');p.add_argument('--no-vmm-policy',action='store_true',help='Exercise OS non-VMM policy with unchanged actual QEMU hardware resources');p.add_argument('--debug-socket',type=Path);p.add_argument('--external-load-report',type=Path);p.add_argument('--external-payload-report',type=Path);p.add_argument('--kernel-inspection',type=Path,default=ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json');p.add_argument('--stage',type=int,choices=[3,6],default=3);p.add_argument('--arena-mib',type=int,choices=[56,72,320],default=56);p.add_argument('--load-test',action='store_true');p.add_argument('--exit-complete',action='store_true');p.add_argument('--entry-test',action='store_true');p.add_argument('--mmu-test',action='store_true');p.add_argument('--early-test',action='store_true');p.add_argument('--pmap-test',action='store_true');p.add_argument('--platform-test',action='store_true');p.add_argument('--platform-stop',choices=['startup','console','idle','timebase','cpu','serial','bootstrap','vm-ready','vm-entry','vm-memory','load-context','first-thread','iokit-entry','iokit-return','irq-enabled','irq-compiled','pre-lockdown','post-lockdown','iokit-matched','bsd-scheduling','root-observer'],default='startup');p.add_argument('--kalloc-zones',type=int,choices=[0,200],default=0);p.add_argument('--watchdog-seconds',type=int,choices=[20],default=20);p.add_argument('--ufs-handoff',action='store_true');p.add_argument('--ufs-read',action='store_true');p.add_argument('--ufs-early-return',action='store_true');p.add_argument('--ufs-watchdog-map-fixture',action='store_true');p.add_argument('--ufs-query-only',action='store_true');p.add_argument('--ufs-read-lba',type=lambda v:int(v,0),default=0);p.add_argument('--ufs-reset-on-error',action='store_true');p.add_argument('--ufs-write-policy',type=Path);p.add_argument('--ufs-extent-plan',type=Path);a=p.parse_args()
 assert a.watchdog_seconds==20 or (a.ufs_watchdog_map_fixture and a.platform_test and a.platform_stop=="root-observer")
 owned=a.kernel_window_mib*1048576
 external=None
 if a.external_payload_report:
  from prepare_handset_payload import validate
  external=validate(a.external_payload_report)
  assert a.ufs_read and a.ufs_extent_plan and a.arena_mib==(72 if external['payload_bytes']==20*1048576 else 320)
  if a.entry_test or a.mmu_test or a.early_test or a.pmap_test or a.platform_test:
   from prepare_handset_payload import qualify_native_execution
   assert a.external_load_report, 'Native execution requires the completed handset transport/capacity baseline report'
   qualify_native_execution(a.external_load_report,external)
 assert not a.ufs_early_return or (a.ufs_read and a.stage==3 and not a.load_test)
 assert not a.ufs_watchdog_map_fixture or (a.ufs_read and (a.stage==3 or external) and not a.ufs_early_return and (not a.load_test or external))
 assert not a.ufs_query_only or a.ufs_read
 assert not a.ufs_reset_on_error or a.ufs_read
 assert not a.platform_test or a.pmap_test
 assert not a.pmap_test or a.early_test
 assert not a.early_test or a.mmu_test
 assert not a.mmu_test or a.entry_test
 assert not a.entry_test or a.exit_complete
 assert not a.exit_complete or a.load_test
 if a.load_test:
  assert a.stage==6
  a.stage=13 if a.platform_test else 12 if a.pmap_test else 11 if a.early_test else 10 if a.mmu_test else 9 if a.entry_test else 8 if a.exit_complete else 7
 parent=ROOT/'artifacts/native-staging-qemu';parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 report=dict(passed=False,handset_executed=False,xnu_executed=False,os_vmm_policy=not a.no_vmm_policy,qemu_dt_platform_fixture=a.dt_platform_fixture,pmgr_nub_fixture=a.pmgr_nub_fixture,qemu_rootless_observer_deadline_ms=40000 if a.dt_platform_fixture else None)
 try:
  workflow=freeze_workflow(out)
  if a.external_load_report:
   from prepare_handset_payload import qualify_native_execution
   report_qualification=qualify_native_execution(a.external_load_report,external)
   report['external_load_qualification']=report_qualification
   (out/'external-load-qualification.json').write_text(json.dumps(report_qualification,indent=2)+'\n')
  report['kernel_inspection']=str(a.kernel_inspection.resolve().relative_to(ROOT))
  memory_mb=1536 if a.arena_mib==320 else 1024
  resource=generate_resources(out,memory_mb=memory_mb);tree=read_fdt((out/'qemu-virt.dtb').read_bytes());bank=next(n for n in tree.walk() if n.properties.get('device_type')==b'memory\0');[(ram,ram_bytes)]=registers(bank)
  original_rd=b'R'*(16*1048576);receiver=build_receiver(out,2 if a.ufs_early_return else a.stage,ramdisk_bytes=len(original_rd),native_staging=True,native_fat_bytes=external['payload_bytes'] if external else 20*1048576);params=image_parameters(receiver);low,reset_inputs=compile_image(out,True);lp=image_parameters(low);base=ram+lp['text_offset'];stub,stub_report=build_stub(out,True);rd,policy,cap=capsule(receiver,original_rd,params,2);(out/'return-initrd').write_bytes(rd)
  src=align(base+192*1048576,BLOCK);window=align(ram+min(ram_bytes//2,(256 if owned>=512*1048576 else 512)*1048576),BLOCK);arena=align(window+owned+BLOCK+1048576,BLOCK);extent=base+65536;fd=extent+65536;stack=fd+24*1048576;download_end=stack+0x40000;fdt=arena+a.arena_mib*1048576;end=fdt+NATIVE_RETURN_FDT_BYTES
  values=dict(ImageBase=base,ImageSize=65536,OriginalEntry=lp['entry'],OriginalInstruction=lp['instruction'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=24*1048576,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=a.arena_mib*1048576,FdtBase=fdt,FdtSize=NATIVE_RETURN_FDT_BYTES,ContextBase=extent)
  selected_inspection=json.loads(a.kernel_inspection.read_text())
  virtual_base=min(v['virtual_address'] for v in selected_inspection['segments'] if v['virtual_bytes'])
  kw=dict(base=window,bytes=owned+BLOCK,window_bytes=owned,virtual_base=virtual_base,guards=[dict(base=base,bytes=download_end-base),dict(base=arena,bytes=end-arena)],experimental_boot_grant=True,source='same-run QEMU FDT bank with an explicit <=512MiB offset; keeps the exact 256/512/704MiB allocation inside one 1GiB recovery-table span',handset_parameters=False)
  inspection=json.loads(a.kernel_inspection.read_text());assert inspection['passed'];kernel=ROOT/inspection['artifact_directory']/'native-kernel.macho';assert sha(kernel.read_bytes())==inspection['native_macho_sha256']
  adt=out/'staging-only.adt';adt.write_bytes(b'INVALID_ADT_STAGING_ONLY_NO_HANDOFF')
  provenance=None
  if a.load_test:
   from raphael_adt import make_adt
   adt,provenance=make_adt(out,(out/'qemu-virt.dtb').read_bytes(),kw,62500000,0,False,qemu_vmm_policy=not a.no_vmm_policy,qemu_dt_platform=a.dt_platform_fixture,qemu_io_bias=0x4000 if a.unaligned_io_bus_fixture else 0,qemu_pmgr_nub=a.pmgr_nub_fixture)
  if a.inherited_display_fixture or a.watchdog_client_abi_fixture:
   assert a.dt_platform_fixture and a.platform_test and a.platform_stop=='root-observer' and external
   from validate_handset_adt import parse
   from native_display_adt import KEY,qualify_kernel
   if a.inherited_display_fixture:qualify_kernel(kernel,offline_keystore=bool(external.get('ephemeral_offline_keystore')))
   if a.watchdog_client_abi_fixture:
    from native_watchdog_client import qualify_kernel as qualify_watchdog
    qualify_watchdog(kernel,offline_keystore=bool(external.get('ephemeral_offline_keystore')))
   tree,adt_end=parse(adt.read_bytes());assert adt_end==adt.stat().st_size
   if a.inherited_display_fixture:tree['nodes']['chosen']['props'][KEY]=struct.pack('<I',1)
   if a.watchdog_client_abi_fixture:tree['nodes']['chosen']['props']['unixnu,qemu-watchdog-abi']=struct.pack('<I',1)
   import sys
   sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'));from unixnu.devicetree import node
   def encode(t):return node(t['props']['name'].rstrip(b'\0').decode(),[(k,v) for k,v in t['props'].items() if k!='name'],[encode(c) for c in t['nodes'].values()])
   adt.write_bytes(encode(tree));provenance['adt_sha256']=sha(adt.read_bytes())
   report['inherited_display_fixture']=a.inherited_display_fixture
   report['watchdog_client_abi_fixture']=a.watchdog_client_abi_fixture
  if external:
   source_external=external
   if a.platform_test and a.platform_stop!='startup':
    from qemu_external_payload import make_fixture
    a.external_payload_report,external=make_fixture(out,external,adt)
    report['external_payload_source_sha256']=source_external['payload_sha256']
    report['qemu_external_payload_fixture']=dict(report=str(a.external_payload_report.relative_to(ROOT)),scope=external['scope'])
   else:
    adt=ROOT/external['adt'];provenance=dict(frozen_payload_adt=True,handset_hardware_not_executed=True)
  assert not a.ufs_read or a.ufs_handoff
  native=dict(external_payload_report=a.external_payload_report,kernel=kernel,adt=adt,handoff=False,load_test=a.load_test,exit_complete=a.exit_complete,entry_test=a.entry_test,mmu_test=a.mmu_test,early_test=a.early_test,pmap_test=a.pmap_test,platform_test=a.platform_test,platform_stop=a.platform_stop,kalloc_zones=a.kalloc_zones,frequency=62500000,affinity=0)
  if a.ufs_watchdog_map_fixture:
   watchdog_fixture=ram+128*1048576
   native['watchdog']=dict(base=watchdog_fixture,frequency=1,seconds=a.watchdog_seconds,mapping_fixture=True,source='QEMU reserved RAM register-storage fixture; mapping/readback/restore only, no hardware timer or reset proof')
  raw,build=build_firmware(out,values,'qemu-android-return-v1','QEMU only',stop_stage=3 if a.stage==3 else 4,payload_test=True,darwin_test=a.load_test,qemu_arch=resource if a.exit_complete else None,kernel_window=kw,native_boot=native,android_return=dict(stub=stub,policy=policy,qemu=True),sparse_arena=True,ufs_handoff=a.ufs_handoff,ufs_read=a.ufs_read,ufs_query_only=a.ufs_query_only,ufs_reset_on_error=a.ufs_reset_on_error,ufs_read_lba=a.ufs_read_lba,ufs_extent_plan=a.ufs_extent_plan,ufs_write_policy=a.ufs_write_policy)
  structure=inspect_fd(raw,fd);image=bytearray(low+bytes(download_end-base-len(low)));image[fd-base:fd-base+len(raw)]=raw;struct.pack_into('<I',image,0,0x14000000|((fd-base)//4));struct.pack_into('<Q',image,16,len(image));(out/'diagnostic.Image').write_bytes(image);assert len(image)<end-base
  dtb=out/'qemu-virt.dtb'
  for prop,value in [('linux,initrd-start',src),('linux,initrd-end',src+len(rd))]:run(out,['fdtput','-t','x',dtb,'/chosen',prop,hex(value>>32)[2:],hex(value&0xffffffff)[2:]])
  if a.ufs_watchdog_map_fixture:
   # Explicit QEMU RAM register fixture, disjoint from Image/source/grants.
   # UFS rejects this root; native watchdog readback uses fixture storage only.
   assert download_end <= watchdog_fixture and watchdog_fixture+4096 <= src
   bus='/raphael-watchdog-map-fixture';node=bus+'/watchdog@'+format(watchdog_fixture,'x')
   run(out,['fdtput','-c',dtb,bus]);run(out,['fdtput','-c',dtb,node])
   for path,prop,vals in [(bus,'#address-cells',['1']),(bus,'#size-cells',['1']),(bus,'ranges',['0','0','0','80000000']),(node,'reg',[format(watchdog_fixture,'x'),'1000'])]:run(out,['fdtput','-t','x',dtb,path,prop,*vals])
   run(out,['fdtput','-t','s',dtb,node,'compatible','qcom,msm-watchdog'])
  if a.ufs_early_return:run(out,['fdtput',dtb,'/chosen','raphael,qemu-ufs-early-return'])
  command=['qemu-system-aarch64','-machine','virt,gic-version=3,virtualization=off','-cpu','cortex-a76','-m',str(memory_mb)+'M','-nographic','-no-reboot','-semihosting-config','enable=on,target=native','-kernel',str(out/'diagnostic.Image'),'-dtb',str(dtb),'-device','loader,file='+str(out/'return-initrd')+',addr='+hex(src)+',force-raw=on']
  if external:command += ['-device','loader,file='+str(ROOT/external['payload'])+',addr='+hex(arena+a.arena_mib*1048576-external['payload_bytes'])+',force-raw=on']
  if a.debug_socket:command += ['-gdb','unix:'+str(a.debug_socket)+',server=on,wait=off']
  observer_limit=build.get('native_mmu_contract',{}).get('early',{}).get('observer_limit_polls',0) or 0
  qemu_timeout=max(180,observer_limit*0.2+60) if external else 60
  report['qemu_timeout_seconds']=qemu_timeout
  started=time.monotonic();result=subprocess.run(command,capture_output=True,timeout=qemu_timeout);log=result.stdout+result.stderr;(out/'serial.log').write_bytes(log);passed=result.returncode==0 and b'ANDROID_RETURN_QEMU_OK' in log and b'FAIL ' not in log
  if not passed and external:
   try:
    from native_early import decode_compiled_panic
    def failure_wire(name):
     w=re.search(name.encode()+rb' ([0-9a-f]+)',log);assert w
     return bytes.fromhex(w[1].decode())
    report['native_panic']=decode_compiled_panic(failure_wire('NATIVE_EARLY_WIRE'),failure_wire('NATIVE_EARLY_DELTA'),kernel.read_bytes(),build['native_mmu_contract'])
   except (AssertionError,ValueError,KeyError) as error:report['failure_snapshot_error']=str(error) or type(error).__name__
  if passed and a.ufs_watchdog_map_fixture:
   assert ('NATIVE watchdog resource accepted base=%X bytes=4096'%watchdog_fixture).encode().lower() in log.lower()
   report['ufs_watchdog_mapping_verified']=True
   report['native_watchdog_seconds']=a.watchdog_seconds
  if passed and a.ufs_read and not a.ufs_early_return:
   m=re.search(rb'UFS uncached before=([0-9a-f]+) inside=([0-9a-f]+) after=([0-9a-f]+) callback=(\d+) stage=(\d+)',log,re.I);assert m
   before,inside,after=int(m[1],16),int(m[2],16),int(m[3],16)
   assert before&0x1005==0x1005 and inside==before&~0x1005 and after==before and int(m[4])==1
   report['ufs_uncached_transition']=dict(before=before,inside=inside,after=after,callback_count=1,phone_mmio_accessed=False)
  if passed and a.ufs_handoff and not a.ufs_early_return:
   assert re.search(rb'UFS handoff status=1 base=0 bytes=0 reads=0',log)
   report['ufs_handoff_qemu_scope']='Unsupported non-SM8150 root: no phone MMIO; actual-C host fixture checks phone FDT boundaries'
  if passed and external:
   assert b'UFS_PAYLOAD_MEMORY verified=1' in log
   report['external_payload_memory_fixture_verified']=True
   report['external_payload_sha256']=external['payload_sha256']
  if passed and a.stage>=6:
   import zlib
   expected=zlib.crc32(kernel.read_bytes());match=re.search(rb'NATIVE_STAGING kernel bytes=(\d+) buffer=([0-9a-f]+) crc=([0-9a-f]+) expected=([0-9a-f]+) status=Success',log,re.I);assert match and int(match[1])==kernel.stat().st_size and int(match[3],16)==int(match[4],16)==expected
   assert check_log(log,kw)['passed']
  if passed and a.load_test:
   from native_load import decode
   wire=re.search(rb'NATIVE_LOAD_WIRE ([0-9a-f]+)',log);assert wire
   report['native_load_observation']=decode(bytes.fromhex(wire[1].decode()),build['native_load_contract'])
  if passed and a.entry_test and not a.mmu_test:
   from native_entry import decode as decode_entry
   wire=re.search(rb'NATIVE_ENTRY_WIRE ([0-9a-f]+)',log);assert wire
   report['native_entry_observation']=decode_entry(bytes.fromhex(wire[1].decode()),build['native_entry_contract'],values)
   report['xnu_executed']=True
  if passed and a.mmu_test:
   from native_mmu import decode as decode_mmu
   wire=re.search(rb'NATIVE_MMU_WIRE ([0-9a-f]+)',log);assert wire
   report['native_mmu_observation']=decode_mmu(bytes.fromhex(wire[1].decode()),build['native_mmu_contract'])
   from native_mmu import audit_tables
   t=re.search(rb'NATIVE_MMU_TABLES ([0-9a-f]+)',log);assert t
   report['native_mmu_tables']=audit_tables(bytes.fromhex(t[1].decode()),report['native_mmu_observation'],build['native_mmu_contract'])
   report['xnu_executed']=True
   if a.early_test:
    from native_early import decode as decode_early
    e=re.search(rb'NATIVE_EARLY_WIRE ([0-9a-f]+)',log);delta=re.search(rb'NATIVE_EARLY_DELTA ([0-9a-f]+)',log);assert e and delta
    report['native_early_observation']=decode_early(bytes.fromhex(e[1].decode()),bytes.fromhex(delta[1].decode()),kernel.read_bytes(),build['native_mmu_contract'],report['native_mmu_observation'],bytes.fromhex(t[1].decode()),bytes.fromhex(re.search(rb'NATIVE_PMAP_TABLES ([0-9a-f]+)',log)[1].decode()) if a.pmap_test else None)
  if passed and a.pmap_test:
   from native_pmap import decode as decode_pmap
   pw=re.search(rb'NATIVE_PMAP_WIRE ([0-9a-f]+)',log);ps=re.search(rb'NATIVE_PMAP_TABLES ([0-9a-f]+)',log);pt=re.search(rb'NATIVE_PMAP_TRANSITION ([0-9a-f]+)',log);pa=re.search(rb'NATIVE_PMAP_ADT ([0-9a-f]+)',log);assert pw and ps and pt and pa
   report['native_pmap_observation']=decode_pmap(bytes.fromhex(pw[1].decode()),bytes.fromhex(ps[1].decode()),bytes.fromhex(pt[1].decode()),bytes.fromhex(pa[1].decode()),adt.read_bytes(),build['native_mmu_contract'],report['native_mmu_observation'])
  if passed and a.platform_test:
   from native_platform import decode as decode_platform
   pw=re.search(rb'NATIVE_PLATFORM_WIRE ([0-9a-f]+)',log);assert pw
   report['native_platform_observation']=decode_platform(bytes.fromhex(pw[1].decode()),build['native_mmu_contract']['early']['policy']['reserved2'])
  if passed and a.platform_stop in ('iokit-return','irq-enabled','irq-compiled','pre-lockdown','post-lockdown','iokit-matched'):
   from native_gic import decode as decode_gic
   gw=re.search(rb'NATIVE_GIC_WIRE ([0-9a-f]+)',log);assert gw
   report['native_gic_observation']=decode_gic(bytes.fromhex(gw[1].decode()),provenance)
  if passed and a.inherited_display_fixture:
   display=report['native_early_observation']['init']['display']
   assert display['stage']==2 and display['family_status']==display['surface_status']==display['meta_status']==0 and display['frames']==display['guard']==0, 'Headless display fixture must exercise exact opt-in, original family/IOSurface and metaclass registration without frame presentation'
   report['inherited_display_headless_branch_verified']=True
   if external.get('ephemeral_offline_keystore'):
    aks=report['native_early_observation']['init']['offline_keystore']
    assert aks['stage']==2,'Explicit scratch-Data state service must actually publish in QEMU'
    report['offline_keystore_publication_verified']=True
  if passed and a.watchdog_client_abi_fixture:
   client=report['native_early_observation']['init']['watchdog_client']
   assert client['stage']==3 and client['metaclass'] and client['service'] and not client['initial_hardware_armed'] and client['checkins']==0,'Rootless QEMU must actually register the subclass and publish original ancestry without claiming hardware checkins'
   report['watchdog_original_ancestry_publication_verified']=True
   registry=report['native_early_observation']['init']['watchdog_registry']
   assert registry['primary_marker']==1 and registry['property_match_verified'] and not registry['hardware_pmu_verified'] and not registry['property_writes_supported']
   report['watchdog_original_pmu_property_match_verified']=True
  services=report.get('native_early_observation',{}).get('init',{}).get('services')
  if services is not None:
   assert services['captured'] and services['scanned_through_pid']==255, 'Linked bounded observer must actually complete its bounded scan'
   assert services['kernel_probe']['thread'] and services['kernel_probe']['stack_captured'], 'Original referenced kernel-thread saved-stack capture must execute in rootless QEMU'
   report['bounded_service_snapshot_verified']=True
  report.update(build,adt_provenance=provenance,workflow_inputs=workflow,passed=passed,qemu_passed=passed,command=command,returncode=result.returncode,wall_seconds=time.monotonic()-started,stage=2 if a.ufs_early_return else a.stage,early_ufs_return=a.ufs_early_return,layout=values,source_range=dict(base=src,bytes=len(rd),dtb_sha256=sha(dtb.read_bytes()),placement='Explicit QEMU fixture budget at 192MiB; all actual input guards remain checked'),kernel_sha256=sha(kernel.read_bytes()),return_stub=stub_report,capsule=cap,reset_inputs=reset_inputs,grant_footprint_bytes=end-base,downloaded_image_bytes=len(image),firmware_sha256=sha(raw),image_sha256=sha(image),structure_checked=True,pass_count=sum(x.startswith(b'PASS ') for x in log.splitlines()),limits=['Experimental arena is distinct from downloaded bytes',f'Original platform prefix through {a.platform_stop} entry; timer registers restored' if a.platform_test else 'Original pmap replaced TTBR1 and emptied original TTBR0; bounded post-pmap recovery' if a.pmap_test else 'Original C up to arm_vm_init entry; no pmap rebuild' if a.early_test else 'Original bootstrap MMU and arm_init entry only; C body not executed' if a.mmu_test else 'Instrumented first five original XNU instructions only' if a.entry_test else 'No kernel branch; service boundary is profile dependent'])
  (out/'fd-inspection.json').write_text(json.dumps(structure,indent=2)+'\n')
 except Exception as e:
  if isinstance(e,subprocess.TimeoutExpired):
   (out/'serial.log').write_bytes((e.stdout or b'')+(e.stderr or b''))
   report['timeout_output_preserved']=True
  report.update(failure=str(e));(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');raise
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['passed','stage','pass_count','downloaded_image_bytes','grant_footprint_bytes']},indent=2));assert passed,log[-6000:]
if __name__=='__main__':main()
