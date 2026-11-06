#!/usr/bin/env python3
"""Temporary boot with independently decoded nonce/CRC and cleanup evidence."""
import argparse,datetime as dt,json,shlex,struct,subprocess,time
from pathlib import Path
from entry_probe import ROOT,sha
from inspect_device import read_fdt
ADB='/mnt/d/Android/platform-tools/adb.exe';FB='/mnt/d/Android/platform-tools/fastboot.exe'

def clean_hardware_return_verified(desc, report):
 return bool(desc.get('hardware_watchdog_return') and
             report.get('android_boot_completed') and report.get('root_verified') and
             report.get('new_android_boot_id') and
             report.get('return_transient_property_names') == [])

def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--runtime-only',action='store_true',help='Check execution and recovery without repeating source or boot-partition hashes');p.add_argument('--resume-readback',type=Path,help='Re-decode an already saved matching handset readback, then perform normal cleanup; no new temporary boot');p.add_argument('--resume-live-return',type=Path,help='Collect a late Android return from an already accepted boot; never boot an image');a=p.parse_args();assert not (a.resume_readback and a.resume_live_return)
 build=a.build.resolve();assert build.is_relative_to(ROOT/'evidence/private/android-return-build');desc=json.loads((build/'report.json').read_text());assert desc['passed'] and desc['structure_checked'] and not desc['android_return_qemu']
 image=build/'boot-android-return.img';assert image.stat().st_size==desc['image_bytes']
 if not a.runtime_only:assert sha(image.read_bytes())==desc['image_sha256']
 qp=ROOT/desc['qemu_evidence'];q=json.loads(qp.read_text());assert q['passed'] and q['stage']==desc['stage']
 if not a.runtime_only:assert sha(qp.read_bytes())==desc['qemu_evidence_sha256']
 out=ROOT/'evidence/private/android-return-run'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(mode=0o700,parents=True,exist_ok=False);print(out,flush=True)
 commands=[];report=dict(passed=False,build=str(build.relative_to(ROOT)),build_report_sha256=sha((build/'report.json').read_bytes()),image_sha256=desc['image_sha256'],identifier=desc['identifier'],stage=desc['stage'],fastboot_boot_accepted=False,android_boot_completed=False,used_flash_or_erase=False,xnu_executed=None,runtime_only=a.runtime_only,boot_partition_check_performed=not a.runtime_only)
 if a.resume_readback:
  import shutil
  source=a.resume_readback.resolve();assert source.is_relative_to(ROOT/'evidence/private/android-return-run') and source!=out
  old=json.loads((source/'report.json').read_text());assert old['build']==report['build'] and old['identifier']==desc['identifier'] and old.get('android_boot_completed') and old.get('root_verified') and old.get('nonce_matched')
  report=old.copy();report.pop('failure',None);report['replayed_readback_source']=str(source.relative_to(ROOT));report['new_temporary_boot_performed']=False
  for name in ['before-boot-id.txt','after-boot-id.txt','before.dtb','after.dtb']:shutil.copyfile(source/name,out/name)
 if a.resume_live_return:
  import shutil
  source=a.resume_live_return.resolve();assert source.is_relative_to(ROOT/'evidence/private/android-return-run') and source!=out
  old=json.loads((source/'report.json').read_text())
  assert a.runtime_only and old.get('runtime_only') and old.get('fastboot_boot_accepted') and old['build']==report['build'] and old['identifier']==desc['identifier']
  assert not (source/'after.dtb').exists(),'Use --resume-readback for an already saved return'
  report=old.copy();report['original_failure']=report.pop('failure',None)
  report.update(resumed_live_return_source=str(source.relative_to(ROOT)),new_temporary_boot_performed=False,late_return_collection=True)
  for name in ['before-boot-id.txt','before.dtb']:shutil.copyfile(source/name,out/name)
 def save(): (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 def call(tool,*args,timeout=15,file=None):
  command=[tool,'-s',a.serial,*args];stamp=dt.datetime.now(dt.timezone.utc).isoformat()
  try:result=subprocess.run(command,capture_output=True,timeout=timeout)
  except subprocess.TimeoutExpired:
   commands.append(dict(command=command,utc=stamp,timed_out=True));(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return None
  record=dict(command=command,utc=stamp,returncode=result.returncode,stderr=result.stderr.decode(errors='replace'))
  if file:(out/file).write_bytes(result.stdout);record.update(file=file,sha256=sha(result.stdout),bytes=len(result.stdout))
  else:record['stdout']=result.stdout.decode(errors='replace')
  commands.append(record);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return result
 def root(command,**kwargs):return call(ADB,'exec-out','su -c '+shlex.quote(command),**kwargs)
 def android(deadline,recover_bootloader=False,prior_boot_id=None):
  bootloader_hits=0;last_check=0;started=time.monotonic()
  while time.monotonic()<deadline:
   v=call(ADB,'get-state',timeout=3)
   if v and v.returncode==0 and v.stdout.strip()==b'device':
    v=call(ADB,'shell','getprop sys.boot_completed',timeout=3)
    if v and v.returncode==0 and v.stdout.strip()==b'1':
     if prior_boot_id is None:return True
     boot=root('cat /proc/sys/kernel/random/boot_id',timeout=3)
     if boot and boot.returncode==0 and boot.stdout.strip() and boot.stdout!=prior_boot_id:return True
   if recover_bootloader and time.monotonic()-started>=20 and time.monotonic()-last_check>=5:
    last_check=time.monotonic();fb=call(FB,'getvar','unlocked',timeout=3)
    bootloader_hits=bootloader_hits+1 if fb and fb.returncode==0 and b'unlocked: yes' in fb.stderr else 0
    if bootloader_hits>=2:
     report['auto_recovered_from_bootloader']=True;save();call(FB,'reboot',timeout=5);recover_bootloader=False
   time.sleep(1)
  return False
 save()
 try:
  if not a.resume_readback:
   if a.resume_live_return:
    report['late_collection_wait_started_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    report['android_boot_completed']=android(time.monotonic()+140)
    report['late_collection_observed_utc']=dt.datetime.now(dt.timezone.utc).isoformat();save()
   else:
    if not a.runtime_only:
     before=root('sha256sum /dev/block/bootdevice/by-name/boot');assert before and before.returncode==0 and before.stdout.decode().split()[0]==desc['source_sha256']
    root('cat /proc/sys/kernel/random/boot_id',file='before-boot-id.txt');v=root('cat /sys/firmware/fdt',file='before.dtb');assert v and v.returncode==0
    tree=read_fdt(v.stdout);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree);assert not any(k.startswith('raphael,') for k in chosen.properties),'Normal reboot cleanup required before this experiment'
    if desc.get('ufs_extent_plan_sha256'):
     from ufs_extent_plan import validate_current
     report['extent_preflight_verified']=validate_current(dict(desc['ufs_reference'],serial=a.serial),root);save()
    if desc.get('ufs_console_log'):
     from ufs_continuous_log import check_live as check_log_allocation
     report['ufs_console_log_preflight']=check_log_allocation(desc['ufs_console_log'],a.serial);save()
    if desc.get('ufs_write_probe'):
     from ufs_write_probe import check_live
     report['ufs_write_preflight']=check_live(desc['ufs_write_probe'],root,a.serial);save()
    if desc.get('native_ufs_write_probe'):
     from ufs_write_probe import check_live
     report['native_ufs_write_preflight']=check_live(desc['native_ufs_write_probe'],root,a.serial);save()
    v=call(ADB,'reboot','bootloader');assert v and v.returncode==0
    ready=False;deadline=time.monotonic()+45
    while time.monotonic()<deadline:
     v=call(FB,'getvar','unlocked',timeout=3)
     if v and v.returncode==0 and b'unlocked: yes' in v.stderr:ready=True;break
     time.sleep(1)
    assert ready,'Unlocked fastboot did not appear'
    path=subprocess.check_output(['wslpath','-w',str(image)],text=True).strip();start=time.monotonic();v=call(FB,'boot',path,timeout=90)
    report['fastboot_boot_accepted']=bool(v and v.returncode==0);save();print('Temporary boot accepted:',report['fastboot_boot_accepted'],flush=True)
    if not report['fastboot_boot_accepted']:call(FB,'reboot',timeout=5)
    pet_budget=desc.get('native_mmu_contract',{}).get('early',{}).get('diagnostic_watchdog_budget',{}).get('budget_ms',0)
    return_timeout=max(300,240+pet_budget/1000) if desc.get('payload',{}).get('external_payload_report') else 140
    report['android_return_timeout_seconds']=return_timeout
    report['android_boot_completed']=android(time.monotonic()+return_timeout,recover_bootloader=True);report['wall_seconds_to_android']=time.monotonic()-start;save()
   assert report['android_boot_completed'],'Android return not established; no further handset experiments'
   v=root('id');report['root_verified']=bool(v and v.returncode==0 and b'uid=0' in v.stdout)
   report['boot_partition_unchanged']=None
   if not a.runtime_only:
    v=root('sha256sum /dev/block/bootdevice/by-name/boot');report['boot_partition_unchanged']=bool(v and v.returncode==0 and v.stdout.decode().split()[0]==desc['source_sha256'])
   root('cat /proc/sys/kernel/random/boot_id',file='after-boot-id.txt');v=root('cat /sys/firmware/fdt',file='after.dtb');assert v and v.returncode==0
   if a.resume_live_return:
    late_tree=read_fdt(v.stdout);late_chosen=next(n for n in late_tree.walk() if n.name=='chosen' and n.parent is late_tree)
    assert late_chosen.strings('raphael,sec-dxe-id')==[desc['identifier']],'Late return nonce differs; preserve readback without rebooting'
  else:
   from types import SimpleNamespace
   v=SimpleNamespace(stdout=(out/'after.dtb').read_bytes(),returncode=0)
  try:
   tree=read_fdt(v.stdout);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
   report['return_transient_property_names']=[k for k in chosen.properties if k.startswith('raphael,')]
   report['nonce_matched']=chosen.strings('raphael,sec-dxe-id')==[desc['identifier']]
   wire=chosen.properties.get('raphael,android-return');d=chosen.properties.get('raphael,sec-dxe')
   report['return_record_found']=bool(wire and len(wire)==80);report['sec_record_found']=bool(d and len(d)==48*8)
   if report['return_record_found']:
    w=struct.unpack('>10Q',wire);(out/'android-return-wire.bin').write_bytes(wire);report['return_words']=w;cap=desc['capsule']['policy_words']
    report['decode_verified']=w[0:2]==(1,3) and w[2]==w[7]==cap[8] and w[3]==w[4]==cap[9] and w[8]==cap[4] and w[9]==1
    report['high_tail_verified']=(w[5],w[6])==(desc['kernel_window']['base']+desc['kernel_window']['bytes']-0x40000,desc['kernel_window']['base']+desc['kernel_window']['bytes'])
   if report['sec_record_found']:
    words=struct.unpack('>48Q',d);report['sec_words']=words;report['stage_verified']=words[27:29]==(desc['stage'],0) and words[6]==4 and words[30]&0x1005==0x1005
    report['page_table_and_fdt_survive_output']=words[31]>=desc['layout']['ImageBase']+desc['capsule']['declared_image_bytes'] and words[23]>=desc['layout']['ImageBase']+desc['capsule']['declared_image_bytes']
   if desc.get('ufs_handoff'):
    from ufs_handoff import decode, decode_observation
    report['ufs_handoff']=decode_observation(chosen.properties.get('raphael,ufs-handoff',b''),report['nonce_matched'],decode,v.stdout)
    report['ufs_handoff_verified']=report['ufs_handoff']['passed']
   if desc.get('ufs_read') and desc.get('ufs_uncached_required'):
    raw=chosen.properties.get('raphael,ufs-uncached',b'');report['ufs_uncached_verified']=False
    if report['nonce_matched'] and len(raw)==40:
     w=struct.unpack('>5Q',raw);report['ufs_uncached']=dict(version=w[0],before=w[1],inside=w[2],after=w[3],callback_count=w[4])
     report['ufs_uncached_verified']=w[0]==1 and w[1]&0x1005==0x1005 and w[2]==w[1]&~0x1005 and w[3]==w[1] and w[4]==1
   if desc.get('ufs_read'):
    from ufs_handoff import decode_read, decode_observation
    reference=(ROOT/desc['ufs_reference']['path']).read_bytes()
    report['ufs_read']=decode_observation(chosen.properties.get('raphael,ufs-read',b''),report['nonce_matched'],decode_read,reference,desc['ufs_reference'])
    report['ufs_read_verified']=report['ufs_read']['passed']
   if 'raphael,sec-dxe-log' in chosen.properties:(out/'sec-dxe.log').write_bytes(chosen.properties['raphael,sec-dxe-log'])
   first=chosen.properties.get('linux,initrd-start');last=chosen.properties.get('linux,initrd-end');report['original_ramdisk_span_restored']=bool(first and last and int.from_bytes(last,'big')-int.from_bytes(first,'big')==desc['capsule']['ramdisk_bytes'])
   if desc.get('native_boot'):
    from payload_probe import decode
    payload=chosen.properties.get('raphael,payload-diagnostic')
    report['native_staging_verified']=False
    if payload:
     report['native_payload']=decode(payload,desc['layout'],6 if desc.get('native_load_test') else desc['stage'],native_staging=True,fat_bytes=desc['payload']['bytes'],external_payload=bool(desc['payload'].get('external_payload_report')))
     report['native_staging_verified']=True
    if payload and desc['stage']>=6:
     import re,zlib
     rawlog=chosen.properties.get('raphael,sec-dxe-log',b'')
     match=re.search(rb'NATIVE_STAGING kernel bytes=(\d+) buffer=([0-9a-f]+) crc=([0-9a-f]+) expected=([0-9a-f]+) status=Success',rawlog,re.I)
     kernel_file=subprocess.check_output(['mtype','-i',str(ROOT/json.loads((ROOT/desc['payload']['external_payload_report']).read_text())['payload']) if desc['payload'].get('external_payload_report') else str(build/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho']);assert sha(kernel_file)==desc['staging_kernel_sha256']
     report['native_staging_verified']=bool(match and int(match[1])==len(kernel_file)==desc['staging_kernel_bytes'] and int(match[3],16)==int(match[4],16)==zlib.crc32(kernel_file) and b'NATIVE_STAGING window_restore=Success' in rawlog)
     if match:
      at=int(match[2],16);arena=desc['layout']['ArenaBase'];end=arena+desc['layout']['ArenaSize']-desc['payload']['bytes']
      report['native_staging_verified'] &= arena<=at<=end and int(match[1])<=end-at
      report['staging_file_read']=dict(bytes=int(match[1]),buffer=at,crc32=int(match[3],16))
   if desc.get('native_load_test'):
    from native_load import decode as decode_load
    report['native_load_verified']=False
    loadwire=chosen.properties.get('raphael,native-load')
    if loadwire:
     (out/'native-load-wire.bin').write_bytes(loadwire)
     try:
      report['native_load']=decode_load(loadwire,desc['native_load_contract'])
      report['native_load_verified']=True
     except (AssertionError,ValueError,KeyError) as error:report['native_load_decode_error']=str(error) or type(error).__name__
   if desc.get('native_entry_test') and not desc.get('native_mmu_test'):
    from native_entry import decode as decode_entry
    report['native_entry_verified']=False
    try:
     entrywire=chosen.properties['raphael,native-entry'];(out/'native-entry-wire.bin').write_bytes(entrywire)
     report['native_entry']=decode_entry(entrywire,desc['native_entry_contract'],desc['layout'])
     report['native_entry_verified']=True;report['xnu_executed']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_entry_decode_error']=str(error) or type(error).__name__
   if desc.get('native_mmu_test'):
    from native_mmu import decode as decode_mmu
    report['native_mmu_verified']=False
    try:
     raw=chosen.properties['raphael,native-mmu'];(out/'native-mmu-wire.bin').write_bytes(raw)
     from native_mmu import FIELDS as mmu_fields
     observed=dict(zip(mmu_fields,struct.unpack('>72Q',raw)));report['native_mmu_raw_observation']=observed
     if observed['esr']==0xf2005353:
      from native_early import image as parse_kernel
      segments,symbols=parse_kernel(kernel_file);names={v:k for k,v in symbols.items() if k in ['_panic','_panic_with_options']}
      fault=dict(pc=observed['elr'],esr=observed['esr'],function=names.get(observed['elr'],'unknown'),x0=observed['x0'])
      if fault['function']=='_panic':
       addr=observed['x0']
       for seg in segments:
        if seg['virtual']<=addr<seg['virtual']+seg['file_bytes']:
         at=seg['offset']+addr-seg['virtual'];fault['format']=kernel_file[at:at+512].split(bytes(1),1)[0].decode(errors='replace');break
      if '_raphael_native_panic_record' in symbols:
       from native_early import decode_compiled_panic
       try:
        fault.update(decode_compiled_panic(chosen.properties['raphael,native-early-c'],chosen.properties['raphael,native-early-delta'],kernel_file,desc['native_mmu_contract']))
        report['xnu_executed']=True
        report['xnu_execution_evidence']='Matching nonce and validated compiled native panic snapshot; requested checkpoint still failed'
       except (AssertionError,ValueError,KeyError) as error:fault['compiled_record_error']=str(error) or type(error).__name__
      report['native_panic']=fault
     report['native_mmu']=decode_mmu(raw,desc['native_mmu_contract'])
     from native_mmu import audit_tables
     tables=chosen.properties['raphael,native-mmu-tables'];(out/'native-mmu-tables.bin').write_bytes(tables)
     report['native_mmu_tables']=audit_tables(tables,report['native_mmu'],desc['native_mmu_contract'])
     report['native_mmu_verified']=True;report['xnu_executed']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_mmu_decode_error']=str(error) or type(error).__name__
   if desc.get('native_early_test'):
    from native_early import decode as decode_early
    report['native_early_verified']=False
    try:
     early=chosen.properties['raphael,native-early-c'];delta=chosen.properties['raphael,native-early-delta']
     (out/'native-early-wire.bin').write_bytes(early);(out/'native-early-delta.bin').write_bytes(delta)
     report['native_early']=decode_early(early,delta,kernel_file,desc['native_mmu_contract'],report['native_mmu'],tables,chosen.properties.get('raphael,native-pmap-tables'))
     report['native_early_verified']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_early_decode_error']=str(error) or type(error).__name__
   if desc.get('native_early_test') and not report.get('native_early_verified') and report['nonce_matched']:
    try:
     from native_early import decode_recovered_globals
     report['native_verified_globals']=decode_recovered_globals(chosen.properties['raphael,native-early-c'],chosen.properties['raphael,native-early-delta'],kernel_file,desc['native_mmu_contract'])
     report['xnu_executed']=True
     report['xnu_execution_evidence']='Matching nonce and fully restored mutable-segment CRCs; full checkpoint remains rejected'
    except (AssertionError,ValueError,KeyError) as error:report['native_globals_decode_error']=str(error) or type(error).__name__
   if desc.get('native_platform_test') and desc['native_mmu_contract']['early']['policy']['reserved2']>=13:
    report['native_gic_verified']=False
    try:
     from native_gic import decode as decode_gic
     raw=chosen.properties['raphael,native-gic'];(out/'native-gic-wire.bin').write_bytes(raw)
     report['native_gic']=decode_gic(raw,desc['adt_provenance']);report['native_gic_verified']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_gic_decode_error']=str(error) or type(error).__name__
   if desc.get('native_watchdog'):
    report['native_watchdog_verified']=False
    try:
     raw=chosen.properties['raphael,native-watchdog'];(out/'native-watchdog-wire.bin').write_bytes(raw)
     fields='version status base frequency seconds saved_enable saved_bark saved_bite armed readback_enable readback_bark readback_bite restored_enable restored_bark restored_bite restore_ok'.split()
     w=dict(zip(fields,struct.unpack('>16Q',raw)));report['native_watchdog']=w
     assert w['version']==1 and w['status']==3 and w['restore_ok']==1 and w['armed']==0
     assert w['base']==desc['native_watchdog']['base'] and w['frequency']==desc['native_watchdog']['frequency'] and w['seconds']==desc['native_watchdog'].get('seconds',20) and w['seconds'] in (20,90)
     assert w['saved_enable']&1==0 and w['readback_enable']==1 and w['readback_bark']==w['frequency']*w['seconds'] and w['readback_bite']==w['frequency']*(w['seconds']+1)
     assert all(w['saved_'+n]==w['restored_'+n] for n in ['enable','bark','bite'])
     report['native_watchdog_verified']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_watchdog_decode_error']=str(error) or type(error).__name__
   if desc.get('native_platform_test'):
    from native_platform import decode as decode_platform
    report['native_platform_verified']=False
    try:
     raw=chosen.properties['raphael,native-platform'];(out/'native-platform-wire.bin').write_bytes(raw)
     report['native_platform']=decode_platform(raw,desc['native_mmu_contract']['early']['policy']['reserved2']);report['native_platform_verified']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_platform_decode_error']=str(error) or type(error).__name__
   if desc.get('native_pmap_test'):
    from native_pmap import decode as decode_pmap
    report['native_pmap_verified']=False
    try:
     values={name:chosen.properties['raphael,native-pmap'+suffix] for name,suffix in [('wire',''),('tables','-tables'),('transition','-transition'),('adt','-adt')]}
     for name,raw in values.items():(out/('native-pmap-'+name+'.bin')).write_bytes(raw)
     original_adt=(ROOT/json.loads((ROOT/desc['payload']['external_payload_report']).read_text())['adt']).read_bytes() if desc.get('payload',{}).get('external_payload_report') else (build/'kernel.macho.adt').read_bytes()
     report['native_pmap']=decode_pmap(values['wire'],values['tables'],values['transition'],values['adt'],original_adt,desc['native_mmu_contract'],report['native_mmu'])
     report['native_pmap_verified']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_pmap_decode_error']=str(error) or type(error).__name__
   if desc.get('native_exit_complete'):
    from native_exit import decode_physical
    report['physical_timer_verified']=False
    try:
     report['physical_timer_evidence']=decode_physical(v.stdout,build)
     report['physical_timer_verified']=True
    except (AssertionError,ValueError,KeyError) as error:report['physical_timer_decode_error']=str(error) or type(error).__name__
   if desc.get('native_video'):
    report['native_video_verified']=False
    try:
     from gop_probe import FIELDS as video_fields
     raw=chosen.properties['raphael,display-gop'];(out/'native-video-wire.bin').write_bytes(raw)
     video=dict(zip(video_fields,struct.unpack('>'+str(len(video_fields))+'Q',raw)))
     report['native_video']=video
     assert video['version']==1 and video['status']==4
     assert video['mapped_read_verified']==video['protocol_installed']==video['query_verified']==1
     assert video['width'] and video['height'] and video['stride']>=video['width']*4
     assert video['extent']==video['height']*video['stride'] and video['base']
     assert video['map_base']==video['base']&~4095 and video['map_size']==((video['base']+video['extent']+4095)&~4095)-video['map_base']
     assert (video['patch_width'],video['patch_height'])==(video['width'],video['height'])
     assert video['patch_restored']==video['width']*video['height'] and video['patch_mismatches']==video['active']==video['backup']==0
     import re
     match=re.search(rb'NATIVE_VIDEO args_match=1 base=([0-9a-f]+) (\d+)x(\d+) stride=(\d+) depth=(\d+)',chosen.properties.get('raphael,sec-dxe-log',b''),re.I)
     assert match and (int(match[1],16),*map(int,match.groups()[1:]))==(video['base'],video['width'],video['height'],video['stride'],32)
     assert report.get('native_load_verified')
     report['native_video_verified']=True
    except (AssertionError,ValueError,KeyError) as error:report['native_video_decode_error']=str(error) or type(error).__name__
   if desc.get('native_ufs_write_probe'):
    from native_ufs_write import verify_result
    probe=report.get('native_early',{}).get('storage',{}).get('write_probe')
    report['native_ufs_write_verified']=verify_result(probe,desc['native_ufs_write_probe'])
   report['new_android_boot_id']=(out/'before-boot-id.txt').read_bytes()!=(out/'after-boot-id.txt').read_bytes()
   required=['fastboot_boot_accepted','android_boot_completed','root_verified','nonce_matched','return_record_found','sec_record_found','decode_verified','high_tail_verified','stage_verified','page_table_and_fdt_survive_output','original_ramdisk_span_restored','new_android_boot_id']
   if desc.get('native_ufs_write_probe'):required.append('native_ufs_write_verified')
   if not a.runtime_only:required.append('boot_partition_unchanged')
   if desc.get('native_platform_test') and desc['native_mmu_contract']['early']['policy']['reserved2']>=13:required.append('native_gic_verified')
   if desc.get('native_watchdog'):required.append('native_watchdog_verified')
   if desc.get('ufs_uncached_required'):required.append('ufs_uncached_verified')
   if desc.get('native_video'):required.append('native_video_verified')
   report['unassisted_android_return']=not report.get('auto_recovered_from_bootloader',False) and not (out/'bootloader-recovery.json').exists()
   report['experiment_passed']=(not desc.get('ufs_read') or report.get('ufs_read_verified',False)) and (not desc.get('ufs_handoff') or report.get('ufs_handoff_verified',False)) and report['unassisted_android_return'] and all(report.get(k,False) for k in required) and (not desc.get('native_boot') or report.get('native_staging_verified',False)) and (not desc.get('native_load_test') or report.get('native_load_verified',False)) and (not desc.get('native_exit_complete') or report.get('physical_timer_verified',False)) and (not desc.get('native_mmu_test') or report.get('native_mmu_verified',False)) and (not desc.get('native_early_test') or report.get('native_early_verified',False)) and (not desc.get('native_platform_test') or report.get('native_platform_verified',False)) and (not desc.get('native_pmap_test') or report.get('native_pmap_verified',False)) and (not desc.get('native_entry_test') or desc.get('native_mmu_test') or report.get('native_entry_verified',False));save()
  except Exception as error:
   # Keep raw observations and always reach recovery cleanup after a decoder error.
   report["decode_failure"]=type(error).__name__+": "+str(error)
   report["experiment_passed"]=False;save()
  # Saved readback is immutable; a normal reboot clears all transient FDT data.
  # adbd may disconnect before the Windows client returns, including a host
  # timeout after the reboot was accepted. Establish cleanup from the new boot
  # and FDT instead of treating the transport return code as handset state.
  if clean_hardware_return_verified(desc, report):
   # Hardware reset already produced a new rooted Android boot with a clean FDT.
   # This is independent return evidence, not a recovered native checkpoint.
   report.update(cleanup_reboot_performed=False, cleanup_new_boot_required=False,
       cleanup_reboot_command_returned_ok=None, cleanup_android_completed=True,
       cleanup_new_android_boot_id=None, cleanup_root_verified=True,
       cleanup_transient_properties_absent=True, cleanup_boot_unchanged=None,
       clean_hardware_return_verified=True)
  else:
   report['cleanup_reboot_performed']=True
   v=call(ADB,'reboot');report['cleanup_reboot_command_returned_ok']=bool(v and v.returncode==0)
   time.sleep(2);report['cleanup_android_completed']=android(time.monotonic()+140,prior_boot_id=(out/'after-boot-id.txt').read_bytes())
   if report['cleanup_android_completed']:
    v=root('cat /proc/sys/kernel/random/boot_id',file='cleanup-boot-id.txt')
    report['cleanup_new_android_boot_id']=bool(v and v.returncode==0 and v.stdout.strip() and v.stdout!=(out/'after-boot-id.txt').read_bytes())
    v=root('id');report['cleanup_root_verified']=bool(v and b'uid=0' in v.stdout)
    report['cleanup_boot_unchanged']=None
    if not a.runtime_only:
     v=root('sha256sum /dev/block/bootdevice/by-name/boot');report['cleanup_boot_unchanged']=bool(v and v.stdout.decode().split()[0]==desc['source_sha256'])
    v=root('cat /sys/firmware/fdt',file='cleanup.dtb')
    if v and v.returncode==0:
     tree=read_fdt(v.stdout);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree);report['cleanup_transient_properties_absent']=not any(k.startswith('raphael,') for k in chosen.properties)
  if desc.get('ufs_write_probe') and report.get('cleanup_root_verified'):
   try:
    from ufs_write_probe import check_live
    report['ufs_write_persistence']=check_live(desc['ufs_write_probe'],root,a.serial,after=True)
   except Exception as error:
    report['ufs_write_persistence']=dict(verified=False,error=type(error).__name__+': '+str(error));report['experiment_passed']=False
   save()
  if desc.get('native_ufs_write_probe'):
   try:
    assert report.get('cleanup_root_verified') and report.get('cleanup_new_android_boot_id')
    from ufs_write_probe import check_live
    report['native_ufs_write_persistence']=check_live(desc['native_ufs_write_probe'],root,a.serial,after=True)
   except Exception as error:
    report['native_ufs_write_persistence']=dict(verified=False,error=type(error).__name__+': '+str(error));report['experiment_passed']=False
   save()
  report['passed']=report['experiment_passed'] and all(report.get(k) for k in ['cleanup_android_completed','cleanup_new_android_boot_id','cleanup_root_verified','cleanup_transient_properties_absent']) and (a.runtime_only or report.get('cleanup_boot_unchanged',False));save()
 except Exception as e:
  report['failure']=type(e).__name__+': '+str(e);save();raise
 print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
