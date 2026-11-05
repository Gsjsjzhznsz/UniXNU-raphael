#!/usr/bin/env python3
"""Freeze a large native FAT outside the downloaded Image; no device writes."""
import argparse,datetime as dt,json,os,shutil,struct,subprocess,hashlib
from pathlib import Path
from entry_probe import ROOT,sha
MAGIC=0x3148534148505052

def inspect_hashes(raw):
 assert len(raw)>=32
 magic,version,size,count=struct.unpack_from('<4Q',raw)
 assert magic==MAGIC and version==1 and 20*1048576<=size<=160*1048576
 assert size%4096==0 and count==size//4096 and len(raw)==32+count*32
 return dict(bytes=size,blocks=count,sha256=sha(raw))

def validate(report,kernel=None,adt=None):
 m=json.loads(report.read_text());assert m['passed']
 for key in ['payload','hashes','kernel','adt']+(['trust_cache'] if m.get('trust_cache') else [])+(['ramdisk'] if m.get('ramdisk') else []):
  p=ROOT/m[key];assert sha(p.read_bytes())==m[key+'_sha256']
 assert inspect_hashes((ROOT/m['hashes']).read_bytes())['bytes']==m['payload_bytes']
 if kernel is not None:assert sha(kernel.read_bytes())==m['kernel_sha256']
 if adt is not None:assert sha(adt.read_bytes())==m['adt_sha256']
 if m.get('ephemeral_offline_keystore'):
  assert m.get('persistent_data') is False and m.get('ephemeral_data_report')
  from native_display_adt import qualify_kernel
  qualify_kernel(ROOT/m['kernel'],offline_keystore=True)
 return m

def root_matching_from_kernel(path):
 """Select only the OS volume UUID in this kernel's signed root manifest.
 Native vr_open still authenticates the complete envelope before exposing media.
 """
 import uuid
 from native_early import image
 raw=path.read_bytes();segments,symbols=image(raw);va=symbols['_verified_root_manifest']
 hits=[s for s in segments if s['virtual']<=va and va+160<=s['virtual']+s['file_bytes']]
 assert len(hits)==1
 segment=hits[0];offset=segment['offset']+va-segment['virtual'];header=raw[offset:offset+160]
 assert header[:8]==b'VROOT01\0' and struct.unpack_from('<4I',header,8)==(1,160,4096,0)
 size,count=struct.unpack_from('<2Q',header,24)
 assert size>0 and count==(size+4095)//4096 and va+544+count*32<=segment['virtual']+segment['file_bytes']
 assert struct.unpack_from('<Q',header,152)[0]>0 and header[40:56]!=bytes(16)
 volume=str(uuid.UUID(bytes=header[40:56])).upper()
 return ('<dict><key>IOProviderClass</key><string>IOMedia</string>'
         '<key>IOPropertyMatch</key><dict><key>UUID</key><string>'+volume+
         '</string></dict></dict>\0').encode(),volume

def qualify_native_execution(path,payload):
 """Qualify the transport/capacity baseline; each run validates its own loaded image."""
 run=json.loads(path.read_text());assert path.resolve().is_relative_to(ROOT/'evidence/private/android-return-run')
 assert run['passed'] and run['experiment_passed'] and run['stage']>=7 and run['native_load_verified']
 assert run['nonce_matched'] and run['unassisted_android_return'] and run['cleanup_transient_properties_absent'] and run['cleanup_new_android_boot_id']
 assert run['ufs_read_verified'] and run['native_staging_verified']
 build=json.loads((ROOT/run['build']/'report.json').read_text())
 previous=json.loads((ROOT/build['payload']['external_payload_report']).read_text())
 assert build['payload']['bytes']==payload['payload_bytes'], 'Capacity must match the qualified transport'
 os_metadata_only=False;cell_encoding_changed=False;watchdog_budget_changed=False;pmgr_policy_changed=False;memory_budget_changed=False;watchdog_client_changed=False
 if previous['adt_sha256']!=payload['adt_sha256']:
  from native_watchdog_budget import from_adt
  watchdog_budget_changed=from_adt((ROOT/previous['adt']).read_bytes())!=from_adt((ROOT/payload['adt']).read_bytes())
  from validate_handset_adt import parse
  prior_tree,_=parse((ROOT/previous['adt']).read_bytes());next_tree,_=parse((ROOT/payload['adt']).read_bytes())
  from native_pmgr_compat import KEY as PMGR_KEY
  pmgr_policy_changed=prior_tree['nodes']['chosen']['props'].get(PMGR_KEY)!=next_tree['nodes']['chosen']['props'].get(PMGR_KEY)
  from native_watchdog_client import KEY as WATCHDOG_CLIENT_KEY
  watchdog_client_changed=prior_tree['nodes']['chosen']['props'].get(WATCHDOG_CLIENT_KEY)!=next_tree['nodes']['chosen']['props'].get(WATCHDOG_CLIENT_KEY)
  memory_budget_changed=prior_tree['nodes']['chosen']['props'].get('darwinboot-memory-size')!=next_tree['nodes']['chosen']['props'].get('darwinboot-memory-size')
  cell_encoding_changed=any(a['props'].get(k)!=b['props'].get(k) for a,b in [(prior_tree,next_tree),(prior_tree['nodes']['arm-io'],next_tree['nodes']['arm-io'])] for k in ['#address-cells','#size-cells'])
  def hardware_tree(path,kernel,offline_keystore=False):
   raw=(ROOT/path).read_bytes();tree,end=parse(raw);assert end==len(raw)
   for parent,name in [(tree,'product'),(tree['nodes']['chosen'],'manifest-properties')]:
    if name in parent['nodes']:
     n=parent['nodes'].pop(name);assert n==dict(props={'name':name.encode()+b'\0'},nodes={}), 'Only empty OS container nodes may differ'
   from native_watchdog_budget import KEY,qualified
   watchdog=tree['nodes']['cpus']['nodes']['cpu0']['props'].pop(KEY,None)
   if watchdog is not None:qualified(watchdog)
   # Exact 64-bit address/size declarations correct the old omitted defaults.
   # All original register, range and ownership property bytes remain frozen.
   for bus in [tree, tree['nodes']['arm-io']]:
    for key in ['#address-cells','#size-cells']:
     observed=bus['props'].pop(key,None)
     assert observed in (None,struct.pack('<I',2)), 'Only exact 64-bit ADT cell declarations may differ'
   from native_pmgr_compat import KEY as PMGR_KEY,qualify_kernel
   pmgr=tree['nodes']['chosen']['props'].pop(PMGR_KEY,None)
   if pmgr is not None:
    assert pmgr==struct.pack('<I',1), 'Only the audited unsupported-AON diagnostic mode is allowed'
    qualify_kernel(ROOT/kernel)
   from raphael_adt import os_chosen_properties
   for key,value in os_chosen_properties():
    observed=tree['nodes']['chosen']['props'].pop(key,None)
    assert observed in (None,value), 'Only the exact pinned OS ABI policy may be added'
   from native_display_adt import KEY as DISPLAY_KEY,qualify_kernel as qualify_display,strip_display_declaration
   # Only the exact resource-free inherited-display enumeration may differ.
   strip_display_declaration(tree)
   display=tree['nodes']['chosen']['props'].pop(DISPLAY_KEY,None)
   if display is not None:
    assert display==struct.pack('<I',1), 'Only explicit inherited display opt-in is supported'
    qualify_display(ROOT/kernel,offline_keystore=offline_keystore)
   from native_watchdog_client import KEY as WATCHDOG_CLIENT_KEY,qualify_property
   client=tree['nodes']['chosen']['props'].pop(WATCHDOG_CLIENT_KEY,None)
   if client is not None:qualify_property(client,raw,ROOT/kernel,offline_keystore=offline_keystore)
   owned=tree['nodes']['chosen']['props'].pop('darwinboot-memory-size',None)
   assert owned in (None,struct.pack('<Q',512*1048576),struct.pack('<Q',704*1048576)), 'Only explicit512/704MiB extensions of the audited boot grant are supported'
   memory=tree['nodes']['chosen']['nodes'].get('memory-map')
   if memory is not None:
    trust=memory['props'].pop('TrustCache',None)
    assert trust in (None,bytes(16)), 'Only an exact owned TrustCache placeholder may be added'
    packed=memory['props'].pop('PackedRAMDisk',None)
    if packed is not None:
     assert packed==bytes(16), 'Data is a new owned packed sidecar, never a hardware map'
     from native_early import image
     syms=image((ROOT/kernel).read_bytes())[1]
     assert all(k in syms for k in ['_native_ram_block_ready','_native_owner_data_stage','_raphael_data_seed_status'])
   matching=tree['nodes']['chosen']['props'].pop('root-matching',None)
   if matching is not None:
    assert matching==root_matching_from_kernel(ROOT/kernel)[0], 'Root matching must equal this kernel signed OS volume UUID'
   return tree
  assert hardware_tree(previous['adt'],previous['kernel'],bool(previous.get('ephemeral_offline_keystore')))==hardware_tree(payload['adt'],payload['kernel'],bool(payload.get('ephemeral_offline_keystore'))), 'All frozen handset hardware properties must match the qualified transport'
  os_metadata_only=not cell_encoding_changed and not watchdog_budget_changed and not pmgr_policy_changed and not memory_budget_changed and not watchdog_client_changed
 return dict(report=str(path.resolve().relative_to(ROOT)),sha256=sha(path.read_bytes()),kernel_sha256=payload['kernel_sha256'],payload_sha256=payload['payload_sha256'],os_metadata_only=os_metadata_only,experimental_memory_budget_changed=memory_budget_changed,diagnostic_pmgr_policy_changed=pmgr_policy_changed,diagnostic_watchdog_client_changed=watchdog_client_changed,adt_cell_encoding_changed=cell_encoding_changed,diagnostic_watchdog_budget_changed=watchdog_budget_changed,exact_kernel_match=build['staging_kernel_sha256']==payload['kernel_sha256'],exact_payload_match=build['payload']['image_sha256']==payload['payload_sha256'],scope='Prior handset transport/capacity and frozen hardware ADT (explicit same-handset qualified 20s diagnostic watchdog contract, empty OS containers, pinned OS ABI policy and explicit 2/2 ADT cell declarations and exact signed OS UUID root matching and zero TrustCache binding and explicit linked original-PMGR unsupported-AON diagnostic policy may differ); current block authentication and all loaded-segment/args/ADT checks must pass in the same boot before branch; observer pet deadline and hardware restoration require same-run evidence')

def main():
 p=argparse.ArgumentParser();p.add_argument('--offline-keystore',action='store_true',help='Explicit unprotected state service on the ephemeral diagnostic Data only');p.add_argument('--packed-data-report',type=Path);p.add_argument('--inspection',type=Path,required=True);p.add_argument('--adt',type=Path,required=True);p.add_argument('--trust-cache-report',type=Path);p.add_argument('--fat-mib',type=int,choices=[20,128,160],default=128);a=p.parse_args()
 inspection=json.loads(a.inspection.read_text());assert inspection['passed'] and inspection['undefined_symbol_count']==0
 kernel=ROOT/inspection['artifact_directory']/'native-kernel.macho';assert sha(kernel.read_bytes())==inspection['native_macho_sha256']
 assert a.adt.resolve().is_relative_to(ROOT/'evidence/private/handset-storage-adt')
 provenance=json.loads((a.adt.parent/'adt-provenance.json').read_text());assert provenance['adt_sha256']==sha(a.adt.read_bytes()) and 'ufs_storage' in provenance
 out=ROOT/'evidence/private/handset-payload'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,mode=0o700);print(out,flush=True)
 stage=out/'stage/EFI/UniXNU';stage.mkdir(parents=True)
 shutil.copyfile(kernel,stage/'kernel.macho');shutil.copyfile(a.adt,stage/'kernel.macho.adt')
 trust_metadata={}
 if a.trust_cache_report:
  from native_trust import validate_bundle,property_offset
  trust_report=json.loads(a.trust_cache_report.read_text())
  assert trust_report['passed'] and trust_report['original_modules_unchanged'] and not trust_report['added_owner_cdhashes']
  trust_path=ROOT/trust_report['bundle'];bundle=trust_path.read_bytes();assert sha(bundle)==trust_report['sha256'] and len(bundle)==trust_report['bytes']
  observed=validate_bundle(bundle);assert len(observed['modules'])==len(trust_report['modules'])
  for i,module in enumerate(observed['modules']):
   end=observed['modules'][i+1]['offset'] if i+1<len(observed['modules']) else len(bundle)
   assert sha(bundle[module['offset']:end])==trust_report['modules'][i]['module_sha256']
  property_offset(a.adt.read_bytes())
  shutil.copyfile(trust_path,stage/'kernel.macho.trustcache')
  trust_metadata=dict(trust_cache=str(trust_path.relative_to(ROOT)),trust_cache_sha256=sha(bundle),trust_cache_report=str(a.trust_cache_report.resolve().relative_to(ROOT)),trust_cache_modules=observed['modules'],apple_signature_chain_verified=False)

 data_metadata={}
 if a.packed_data_report:
  data=json.loads(a.packed_data_report.read_text());assert data['passed'] and data['adt']==str(a.adt.resolve().relative_to(ROOT))
  packed=ROOT/data['packed'];raw=packed.read_bytes()
  from native_ramdisk import validate_packed
  observed=validate_packed(raw);assert observed['sha256']==data['packed_sha256']
  from native_trust import property_offset
  property_offset(a.adt.read_bytes(),'PackedRAMDisk')
  shutil.copyfile(packed,stage/'data.packed')
  data_metadata=dict(ramdisk=str(packed.relative_to(ROOT)),ramdisk_sha256=observed['sha256'],ramdisk_bytes=len(raw),ramdisk_logical_bytes=observed['logical_bytes'],ephemeral_data_report=str(a.packed_data_report.resolve().relative_to(ROOT)),persistent_data=False)
 if a.offline_keystore:
  assert a.packed_data_report and data_metadata['persistent_data'] is False
  from native_display_adt import qualify_kernel
  qualify_kernel(kernel,offline_keystore=True)
 (stage/'unixnu.toml').write_text('version = 1\n[boot]\ntimeout = 0\ndefault = "diagnostic-exit"\n[kits]\nautoload = false\n[[entry]]\nid = "diagnostic-exit"\ntitle = "Return to diagnostic"\ntype = "action"\naction = "exit"\n')
 for f in [*stage.iterdir(),stage,stage.parent]:os.utime(f,(1793088000,1793088000))
 payload=out/'native-payload.img';env=dict(os.environ,MTOOLS_SKIP_CHECK='1',TZ='UTC')
 commands=[['mformat','-C','-T',str(a.fat_mib*2048),'-v','RAPHDIAG','-N','5250484c','-i',str(payload),'::'],['mcopy','-i',str(payload),'-s','-Q','-m',str(stage.parent),'::/']]
 for command in commands:subprocess.run(command,env=env,check=True,capture_output=True)
 size=payload.stat().st_size;assert size==a.fat_mib*1048576
 hashes=struct.pack('<4Q',MAGIC,1,size,size//4096)
 with payload.open('rb') as f:
  for block in iter(lambda:f.read(4096),b''):assert len(block)==4096;hashes+=hashlib.sha256(block).digest()
 (out/'block-hashes.bin').write_bytes(hashes);inspect_hashes(hashes)
 # Round-trip the exact files through mtools, avoiding a silent FAT-copy mismatch.
 for file in ['kernel.macho','kernel.macho.adt']+(['kernel.macho.trustcache'] if a.trust_cache_report else [])+(['data.packed'] if a.packed_data_report else []):
  content=subprocess.check_output(['mtype','-i',str(payload),'::/EFI/UniXNU/'+file],env=env);assert content==(stage/file).read_bytes()
 report=dict(**data_metadata,**trust_metadata,ephemeral_offline_keystore=a.offline_keystore,passed=True,payload=str(payload.relative_to(ROOT)),payload_bytes=size,payload_sha256=sha(payload.read_bytes()),hashes=str((out/'block-hashes.bin').relative_to(ROOT)),hashes_sha256=sha(hashes),kernel=str(kernel.relative_to(ROOT)),kernel_sha256=sha(kernel.read_bytes()),adt=str(a.adt.resolve().relative_to(ROOT)),adt_sha256=sha(a.adt.read_bytes()),inspection=str(a.inspection.resolve().relative_to(ROOT)),commands=commands,handset_executed=False,disks=[dict(role='Payload',path=str(payload.relative_to(ROOT)),bytes=size,apfs_containers=[])])
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,report=str(out/'report.json'),payload_bytes=size),indent=2))
if __name__=='__main__':main()
