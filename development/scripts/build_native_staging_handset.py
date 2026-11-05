#!/usr/bin/env python3
"""Private native staging: sparse download and explicit separate experimental arena."""
import argparse,datetime as dt,json,struct,tempfile,uuid
from pathlib import Path
from entry_probe import ROOT,image_parameters,align,sha,run
from android_return import build_stub,capsule
from build_psci_reset import compile_image
from build_sec_dxe import build_firmware
from private_android_image import read_boot,repack
from inspect_diagnostic_fd import inspect_fd
from native_staging import freeze_workflow, NATIVE_RETURN_FDT_BYTES
from kernel_window import BLOCK,WINDOW,encode_policy

def main():
 p=argparse.ArgumentParser();p.add_argument('--ufs-console-log-report',type=Path);p.add_argument('--native-ufs-write-policy',type=Path);p.add_argument('--kernel-window-mib',type=int,choices=[256,512,704],default=256);p.add_argument('--external-load-report',type=Path);p.add_argument('--external-payload-report',type=Path);p.add_argument('--kernel-inspection',type=Path,default=ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json');p.add_argument('--collection',type=Path,required=True);p.add_argument('--qemu-report',type=Path,required=True);p.add_argument('--stage',type=int,choices=[3,6],default=3);p.add_argument('--arena-mib',type=int,choices=[56,72,320],default=56);p.add_argument('--load-test',action='store_true');p.add_argument('--native-video',action='store_true');p.add_argument('--video-host-report',type=Path);p.add_argument('--exit-complete',action='store_true');p.add_argument('--entry-test',action='store_true');p.add_argument('--mmu-test',action='store_true');p.add_argument('--early-test',action='store_true');p.add_argument('--pmap-test',action='store_true');p.add_argument('--platform-test',action='store_true');p.add_argument('--platform-stop',choices=['startup','console','idle','timebase','cpu','serial','bootstrap','vm-ready','vm-entry','vm-memory','load-context','first-thread','iokit-entry','iokit-return','irq-enabled','irq-compiled','pre-lockdown','post-lockdown','iokit-matched','bsd-scheduling','root-observer'],default='startup');p.add_argument('--kalloc-zones',type=int,choices=[0,200],default=0);p.add_argument('--watchdog-seconds',type=int,choices=[20],default=20);p.add_argument('--watchdog-report',type=Path);p.add_argument('--qemu-audit',type=Path);p.add_argument('--ufs-handoff',action='store_true');p.add_argument('--ufs-read',action='store_true');p.add_argument('--ufs-query-only',action='store_true');p.add_argument('--ufs-read-lba',type=lambda v:int(v,0),default=0);p.add_argument('--ufs-reset-on-error',action='store_true');p.add_argument('--ufs-write-policy',type=Path);p.add_argument('--ufs-extent-plan',type=Path);p.add_argument('--ufs-reference',type=Path);a=p.parse_args()
 external=None
 if a.external_payload_report:
  from prepare_handset_payload import validate
  external=validate(a.external_payload_report)
  assert a.ufs_read and a.ufs_extent_plan and a.arena_mib==(72 if external['payload_bytes']==20*1048576 else 320)
  if a.entry_test or a.mmu_test or a.early_test or a.pmap_test or a.platform_test:
   from prepare_handset_payload import qualify_native_execution
   assert a.external_load_report, 'Native execution requires the completed handset transport/capacity baseline report'
   qualify_native_execution(a.external_load_report,external)
 if external:
  from validate_handset_adt import parse
  from native_display_adt import KEY as DISPLAY_KEY
  tree,end=parse((ROOT/external['adt']).read_bytes())
  if DISPLAY_KEY in tree['nodes']['chosen']['props']:
   assert a.native_video and a.video_host_report, 'Handset display requires same-run full framebuffer backup and restoration'
   prior=json.loads(a.external_load_report.read_text());data=prior['native_early']['init'].get('ephemeral_data',{})
   assert prior['experiment_passed'] and prior['cleanup_root_verified'] and prior['cleanup_transient_properties_absent']
   assert data.get('native_owner_data_stage')==4 and data.get('native_owner_data_status')==0 and data.get('native_owner_data_readonly')==0
 assert not a.ufs_query_only or a.ufs_read
 assert not a.ufs_reset_on_error or a.ufs_read
 assert not a.ufs_read or (a.ufs_handoff and a.watchdog_report and a.ufs_reference and a.ufs_reference.resolve().is_relative_to(ROOT/'evidence/private/ufs-readonly') and a.ufs_reference.stat().st_size==4096)
 native_log=None
 if a.ufs_console_log_report:
  assert a.platform_test and a.platform_stop=='root-observer' and external and a.native_video and not a.native_ufs_write_policy
  from ufs_continuous_log import qualify_kernel as qualify_log
  native_log=qualify_log(ROOT/external['kernel'],a.ufs_console_log_report)
 native_write=None
 if a.native_ufs_write_policy:
  assert a.platform_test and a.platform_stop=='root-observer' and external and not a.ufs_write_policy and not a.native_video
  from ufs_write_probe import validate_manifest
  from native_ufs_write import qualify_kernel
  native_write=validate_manifest(a.native_ufs_write_policy)
  qualify_kernel(ROOT/external['kernel'],native_write)
 if external:
  from native_early import image as native_image
  native_symbols=native_image((ROOT/external['kernel']).read_bytes())[1]
  assert ('_raphael_ufs_log_allocation' in native_symbols)==bool(native_log), 'Compiled console logger requires its prepared allocation'
  has_native_writer='_raphael_ufs_write_probe_policy' in native_symbols
  assert has_native_writer==bool(native_write), 'Compiled native writer requires its exact preflight and persistence policy'
 write_probe=None
 if a.ufs_write_policy:
  assert a.ufs_read and a.stage==3 and not a.load_test and not a.ufs_query_only and not a.ufs_extent_plan
  from ufs_write_probe import validate_manifest
  write_probe=validate_manifest(a.ufs_write_policy,a.ufs_read_lba)
 if a.ufs_extent_plan:
  assert a.ufs_read and not a.ufs_query_only and not a.ufs_read_lba
  from ufs_extent_plan import validate_manifest
  extent_metadata=validate_manifest(a.ufs_extent_plan,a.ufs_reference)
 if a.ufs_read_lba:
  source_path=a.ufs_reference.parent/'read-source.json';source=json.loads(source_path.read_text())
  assert source['passed'] and source['file_encryption_policy_absent'] and source['extent_stable_across_collection'] and source['lba']==a.ufs_read_lba
  assert sha(a.ufs_reference.read_bytes())==source['sha256'] and source['bytes']==4096
 video_host=None
 if a.native_video:
  assert a.load_test and a.video_host_report, 'Native video requires the real loader path and explicit actual-C validation'
  video_host=json.loads(a.video_host_report.read_text());assert video_host['passed'] and video_host['kind']=='actual native video and SEC restoration ASan/UBSan'
 assert not a.platform_test or a.pmap_test
 assert not a.pmap_test or a.early_test
 assert not a.early_test or a.mmu_test
 assert not a.mmu_test or a.entry_test
 assert not a.entry_test or a.exit_complete
 assert not a.exit_complete or a.load_test
 if a.load_test:
  assert a.stage==6
  a.stage=13 if a.platform_test else 12 if a.pmap_test else 11 if a.early_test else 10 if a.mmu_test else 9 if a.entry_test else 8 if a.exit_complete else 7
 qp=a.qemu_report.resolve();q=json.loads(qp.read_text());assert q['layout']['FdtSize']==NATIVE_RETURN_FDT_BYTES, 'Matching expanded-FDT QEMU qualification required'
 if a.ufs_read and a.stage==3:assert q.get('ufs_watchdog_mapping_verified'), 'Stage-3 UFS must qualify watchdog mapping without the XNU MMU profile'
 if external:assert q.get('external_payload_memory_fixture_verified') and q.get('external_payload_source_sha256',q['external_payload_sha256'])==external['payload_sha256']
 assert q.get('ufs_extent_plan_sha256')==(sha(a.ufs_extent_plan.read_bytes()) if a.ufs_extent_plan else None), 'Matching extent-policy QEMU qualification required'
 assert q.get('ufs_write_policy_sha256')==(sha(a.ufs_write_policy.read_bytes()) if a.ufs_write_policy else None),'Matching UFS write-policy QEMU qualification required'
 assert q.get('ufs_read_lba',0)==a.ufs_read_lba, 'Matching UFS read address qualification required'
 assert bool(q.get('ufs_reset_on_error'))==a.ufs_reset_on_error, 'Matching explicit UFS reset recovery required'
 assert bool(q.get('ufs_query_only'))==a.ufs_query_only, 'Matching UFS command boundary qualification required'
 assert bool(q.get('ufs_read'))==a.ufs_read, 'Matching UFS read probe QEMU profile required'
 assert bool(q.get('ufs_handoff'))==a.ufs_handoff, 'Matching UFS enabled/disabled QEMU qualification required'
 assert q['passed'] and q['stage']==a.stage and q['structure_checked'] and q['layout']['ArenaSize']==a.arena_mib*1048576 and q['sparse_arena'] and q['native_boot'] and not q['native_handoff']
 assert a.watchdog_seconds==20 or (a.watchdog_report and a.platform_test and a.platform_stop=="root-observer"), "Extended watchdog budget is restricted to bounded root/service observation"
 assert q.get("native_watchdog_seconds",20)==a.watchdog_seconds, "Matching watchdog-budget QEMU qualification required"
 watchdog=None
 if a.watchdog_report:
  wr=json.loads(a.watchdog_report.read_text());assert wr['passed'] and wr['hardware_reset_verified'] and (a.platform_test or (a.ufs_read and (not a.load_test and a.stage==3 or external)))
  wb=json.loads((ROOT/wr['build']/'report.json').read_text());assert wb.get('no_cpu_reset_instruction')
  watchdog=dict(base=wb['base'],frequency=wb['frequency'],qualification=str(a.watchdog_report.resolve().relative_to(ROOT)),seconds=a.watchdog_seconds,clock_measured=False)
 qa=None
 if a.mmu_test and not a.platform_test:
  assert a.qemu_audit,'MMU handset build requires independent trace and negative cases'
  qa=a.qemu_audit.resolve();qr=json.loads(qa.read_text())
  assert qr['passed'] and qr['positive_report']==str(qp.relative_to(ROOT)) and qr['positive_report_sha256']==sha(qp.read_bytes())
  assert [x['case'] for x in qr['cases']]==(['trace','wrong-brk','bad-active-table','transition-corrupt','backup-corrupt'] if a.pmap_test else ['trace','wrong-brk','bad-table','backup-corrupt'] if a.early_test else ['trace','wrong-brk','bad-table']) and all(x['passed'] for x in qr['cases'])
  assert (qa.parent/'runner.py').read_bytes()==(ROOT/('scripts/audit_native_pmap_recovery_qemu.py' if a.pmap_test else 'scripts/audit_native_mmu_qemu.py')).read_bytes()
  for item in qr['evidence_files']:assert sha((qa.parent/item['path']).read_bytes())==item['sha256']
 if a.platform_test:
  assert q['native_platform_test'] and q['native_platform_observation']['restore_ok']==1
  assert q.get('native_kalloc_zones',0)==a.kalloc_zones
  assert q['native_mmu_contract']['early']['policy']['reserved2']=={'startup':0,'console':1,'idle':2,'timebase':3,'cpu':4,'serial':5,'bootstrap':6,'vm-ready':7,'vm-entry':8,'vm-memory':9,'load-context':10,'first-thread':11,'iokit-entry':12,'iokit-return':13,'irq-enabled':14,'irq-compiled':15,'pre-lockdown':16,'post-lockdown':17,'iokit-matched':18,'bsd-scheduling':19,'root-observer':20}[a.platform_stop]
 geometry_path=ROOT/'UniXNU-raphael/evidence/initrd-geometry.json';geometry=json.loads(geometry_path.read_text());assert geometry['initrd_geometry_verified'] and geometry['nonce_matched']
 query_path=ROOT/'evidence/private/psci-query/20261028T194116Z/report.json';query=json.loads(query_path.read_text());assert query['passed'] and query['observation']['conduit']==1 and query['observation']['system_reset_feature']==0
 owned=a.kernel_window_mib*1048576
 assert q['kernel_window']['window_bytes']==owned, 'QEMU must qualify the same actual kernel window'
 if a.load_test:assert q['native_load_contract']['window_bytes']==owned, 'Loaded kernel allocation must match QEMU'
 audit_path=ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json';audit=json.loads(audit_path.read_text());assert audit['passed'] and audit['memory_views_agree'];candidate=next(c for c in audit['candidates'] if c['every_kernel_offset_fits']);window=candidate['aligned_example']['base'];assert window+owned+BLOCK<=candidate['run']['end_exclusive']
 entry_path=ROOT/'UniXNU-raphael/evidence/entry-handoff.json';entry=json.loads(entry_path.read_text())['entry'];base=entry['image_base']
 boot=read_boot(a.collection.resolve());original=image_parameters(boot['image']);assert original['image_size']==entry['original_image_size'] and original['entry']==entry['original_entry_offset']
 parent=ROOT/'evidence/private/android-return-build';parent.mkdir(mode=0o700,parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 try:
  workflow=freeze_workflow(out)
  report_qualification=None
  if a.external_load_report:
   from prepare_handset_payload import qualify_native_execution
   report_qualification=qualify_native_execution(a.external_load_report,external)
   (out/'external-load-qualification.json').write_text(json.dumps(report_qualification,indent=2)+'\n')
  low,reset_inputs=compile_image(out,False);lp=image_parameters(low);stub,stub_report=build_stub(out,False);rd,policy,cap=capsule(boot['image'],boot['ramdisk'],original,1)
  (out/'expanded-ramdisk.bin').write_bytes(rd)
  # Run the real SDK against this freshly collected private kernel too.
  host=sorted((ROOT/'artifacts/android-return-host').glob('*/report.json'))[-1];h=json.loads(host.read_text());assert h['passed']
  assert sha((ROOT/'scripts/fixtures/android_return_host.c').read_bytes())==h['host_fixture_sha256']
  (out/'original.Image').write_bytes(boot['image']);compressed=rd[align(len(boot['ramdisk']),8):];(out/'original.Image.lzma').write_bytes(compressed)
  host_log=run(out,[host.parent/'host-test',out/'original.Image.lzma',out/'original.Image']);(out/'host-decoder.log').write_bytes(host_log);assert b'ANDROID_RETURN_HOST_OK' in host_log
  extent=base+65536;fd=extent+65536;stack=fd+24*1048576;arena_bytes=a.arena_mib*1048576;grant_bytes=arena_bytes+NATIVE_RETURN_FDT_BYTES
  choices=[]
  for span in audit['structural_unreserved_runs']:
   start=align(max(span['base'],window+owned+BLOCK+1048576),BLOCK)
   if start+grant_bytes<=span['end_exclusive']:choices.append((start,span))
  assert choices,'No independently audited staging grant remains outside kernel window'
  arena,grant_source=choices[0];fdt=arena+arena_bytes;end=fdt+NATIVE_RETURN_FDT_BYTES
  for guard in audit['excluded_ranges']:
   assert not(arena<guard['end_exclusive'] and guard['base']<end),guard['source']
  values=dict(ImageBase=base,ImageSize=65536,OriginalEntry=lp['entry'],OriginalInstruction=lp['instruction'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=24*1048576,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=arena_bytes,FdtBase=fdt,FdtSize=NATIVE_RETURN_FDT_BYTES,ContextBase=extent)
  kw=dict(base=window,bytes=owned+BLOCK,window_bytes=owned,virtual_base=q['kernel_window']['virtual_base'],guards=[dict(base=g['base'],bytes=g['bytes']) for g in audit['excluded_ranges']],experimental_boot_grant=True,handset_parameters=True,source=str(audit_path.relative_to(ROOT)),source_sha256=sha(audit_path.read_bytes()),limits=['Explicit experimental boot grant, not hidden DMA or firmware ownership proof','Recovery stub uses the final 256KiB alignment tail; actual kernel allocation equals the explicit 256/512/704MiB policy'])
  encode_policy(kw);identifier='raphael-native-staging-v1-'+uuid.uuid4().hex
  inspection=json.loads(a.kernel_inspection.read_text());assert inspection['passed'] and inspection['undefined_symbol_count']==0
  kernel=ROOT/inspection['artifact_directory']/'native-kernel.macho';assert sha(kernel.read_bytes())==inspection['native_macho_sha256']==q['kernel_sha256']
  adt=out/'staging-only.adt';adt.write_bytes(b'INVALID_ADT_STAGING_ONLY_NO_HANDOFF');provenance=None
  if a.load_test:
   from raphael_adt import make_adt
   adt,provenance=make_adt(out,(a.collection.resolve()/'live.dtb').read_bytes(),kw,entry['cntfrq'],entry['mpidr']&0xff00ffffff,True)
   assert q['native_load_test'] and q['native_load_observation']['original_loader_loaded_memory_verified']
  if external:
   adt=ROOT/external['adt'];provenance=json.loads((adt.parent/'adt-provenance.json').read_text())
  native=dict(external_payload_report=a.external_payload_report,video=a.native_video,watchdog=watchdog,kernel=kernel,adt=adt,handoff=False,load_test=a.load_test,exit_complete=a.exit_complete,entry_test=a.entry_test,mmu_test=a.mmu_test,early_test=a.early_test,pmap_test=a.pmap_test,platform_test=a.platform_test,platform_stop=a.platform_stop,kalloc_zones=a.kalloc_zones,frequency=entry['cntfrq'],affinity=entry['mpidr']&0xff00ffffff)
  raw,report=build_firmware(out,values,identifier,('private handset Android return; one explicitly bounded diagnostic storage write' if a.ufs_write_policy else 'private handset Android return; RAM-only'),stop_stage=3 if a.stage==3 else 4,payload_test=True,experimental_gop=a.native_video,display_probe=a.native_video,smmu_probe=a.native_video,pixel_probe=a.native_video,darwin_test=a.load_test,physical_timer_arch=a.exit_complete,timer_irq_test=a.exit_complete,timer_route_test=a.exit_complete,gic_enable_map=a.exit_complete,icc_probe=a.exit_complete,gic_probe=a.exit_complete,kernel_window=kw,native_boot=native,android_return=dict(stub=stub,policy=policy,qemu=False),sparse_arena=True,ufs_handoff=a.ufs_handoff,ufs_read=a.ufs_read,ufs_query_only=a.ufs_query_only,ufs_reset_on_error=a.ufs_reset_on_error,ufs_read_lba=a.ufs_read_lba,ufs_extent_plan=a.ufs_extent_plan,ufs_write_policy=a.ufs_write_policy)
  if report_qualification:report['external_load_qualification']=report_qualification
  if a.ufs_read:
   gp=a.ufs_reference.parent/'lun0-geometry.txt';lines=gp.read_text().splitlines();assert lines[0].endswith('/0:0:0:0')
   sectors,logical=map(int,lines[-2:]);assert logical==4096 and sectors*512%logical==0
   report['ufs_reference']=dict(path=str(a.ufs_reference.resolve().relative_to(ROOT)),bytes=4096,sha256=sha(a.ufs_reference.read_bytes()),geometry_source=str(gp.resolve().relative_to(ROOT)),blocks=sectors*512//logical,logical_bytes=logical,lba=a.ufs_read_lba,purpose=('Expected bounded diagnostic WRITE10 readback; preimage required and persistence checked after normal reboot' if a.ufs_write_policy else 'Fresh root Android LUN0 declared block read; exact byte comparison, no firmware write'))
  if a.ufs_extent_plan:
   report['ufs_reference'].update(extent_metadata)
   if external:
    report['ufs_reference']['payload_blocks']=external['payload_bytes']//4096
    report['ufs_reference']['extent_physical_reads']+=external['payload_bytes']//4096
    report['ufs_reference']['probe_goal']='verified_boot_payload'
  structure=inspect_fd(raw,fd);download_end=stack+0x40000;image=bytearray(low+bytes(download_end-base-len(low)));image[fd-base:fd-base+len(raw)]=raw;struct.pack_into('<I',image,0,0x14000000|((fd-base)//4));struct.pack_into('<Q',image,16,len(image));packed=repack(boot,image,ramdisk=rd);assert repack(boot,boot['image'])==boot['raw'],'Original repack must remain exact'
  (out/'boot-android-return.img').write_bytes(packed);(out/'diagnostic.Image').write_bytes(image)
  report['ufs_write_probe']=write_probe
  report['native_ufs_write_probe']=native_write
  report['ufs_console_log']=native_log
  report.update(kernel_inspection=str(a.kernel_inspection.resolve().relative_to(ROOT)),native_video_host_report=str(a.video_host_report.resolve().relative_to(ROOT)) if a.video_host_report else None,qemu_video_coverage='No display hardware model; QEMU covers the headless loader/recovery path only' if a.native_video else None,qemu_mmu_audit=str(qa.relative_to(ROOT)) if qa else None,qemu_mmu_audit_sha256=sha(qa.read_bytes()) if qa else None,workflow_inputs=workflow,passed=True,stage=a.stage,identifier=identifier,layout=values,capsule=cap,return_stub=stub_report,reset_inputs=reset_inputs,qemu_evidence=str(qp.relative_to(ROOT)),qemu_evidence_sha256=sha(qp.read_bytes()),query_evidence=str(query_path.relative_to(ROOT)),query_evidence_sha256=sha(query_path.read_bytes()),structure_checked=True,source_sha256=sha(boot['raw']),image_sha256=sha(packed),image_bytes=len(packed),arm64_image_bytes=len(image),grant_footprint_bytes=end-base,geometry_evidence=str(geometry_path.relative_to(ROOT)),geometry_evidence_sha256=sha(geometry_path.read_bytes()),staging_kernel_sha256=sha(kernel.read_bytes()),staging_kernel_bytes=kernel.stat().st_size,invalid_adt_placeholder=not a.load_test,adt_provenance=provenance,arena_selection=dict(base=arena,bytes=grant_bytes,audited_run=grant_source,source=str(audit_path.relative_to(ROOT)),source_sha256=sha(audit_path.read_bytes()),design='First aligned audited unreserved run after kernel window and 1MiB design separation; live SEC guards remain mandatory'),firmware_sha256=sha(raw),unchanged_dtbs=boot['dtbs'],original_kernel_restored_at_runtime=True,proprietary=True,publicly_redistributable=False,handset_executed=False,xnu_executed=False)
  (out/'fd-inspection.json').write_text(json.dumps(structure,indent=2)+'\n')
 except Exception as e:
  (out/'failure.json').write_text(json.dumps(dict(passed=False,failure=str(e)),indent=2)+'\n');raise
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['passed','stage','image_sha256','arm64_image_bytes','grant_footprint_bytes']},indent=2))
if __name__=='__main__':main()
