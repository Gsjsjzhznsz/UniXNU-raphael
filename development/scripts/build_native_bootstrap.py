#!/usr/bin/env python3
"""Call pinned native compiler backend; retain the real failure and skip OS prelink."""
import argparse,datetime as dt,json,os,shutil,struct,sys,traceback,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from source_pins import locked_revision
UP=ROOT/'sources/UniXNU'
sys.path.insert(0,str(UP/'scripts'))
from unixnu.cli import parser,prepare,cmd_defconfig
from unixnu.config import Context
from unixnu import kernel,feeds,patches,tree

def prepare_local(ctx):
 # Build from resolved pins already on disk. A build never refreshes upstream.
 modules=feeds.resolve(ctx);locked=feeds.lock_read(ctx)
 wanted={'xnu','libplatform','libdispatch','AvailabilityVersions','libpthread','corecrypto-2023','IOStorageFamily'}
 for module in modules.values():
  if module.origin!='git' or (module.kind=='refer' and module.name not in wanted):continue
  revision=feeds.pinned_revision(ctx,module,locked)
  if not revision or len(revision)!=40:raise RuntimeError('Local build requires an exact source pin: '+module.name)
  directory=feeds._clone_dir(ctx,module.source,revision)
  if not (directory/'.git').exists():raise RuntimeError('Pinned dependency is missing locally: '+module.name+' '+revision)
  actual=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
  if actual!=revision:raise RuntimeError('Local dependency differs from its pin: '+module.name)
  feeds._attach([module],directory,actual,{})
 tree.assemble(ctx,modules)
 return modules

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fairplay-aes-trace',action='store_true',help='Observe original SoftwareAES results for fairplay only');ap.add_argument('--observer-budget-ms',type=int,choices=[420000,780000,1860000],default=420000,help='Explicit observer-bound handset window; original hardware20s threshold retained');ap.add_argument('--ufs-console-log-report',type=Path);ap.add_argument('--native-console',action='store_true',help='Show original native text console and service progress on inherited display');ap.add_argument('--service-spawn-waits',action='store_true',help='At the unchanged first-method stop, add one-thread snapshots for at most 64 xpcproxy processes');ap.add_argument('--watchdog-method-checkpoint',nargs='?',const='first-method',choices=['first-method','first-display-client','first-method-plus-5s','observer-bound'],help='Explicit360s bounded diagnostic: stop at the first method, five physical seconds later, or at the first successful display client');ap.add_argument('--native-ufs-write-policy',type=Path,help='Explicit private single-block XNU diagnostic; never enabled by the default profile');ap.add_argument('--service-observer',action='store_true',help='Bounded read-only selected-process thread snapshots at the existing observer deadline');ap.add_argument('--handset-display',action='store_true',help='Explicit inherited handset framebuffer candidate; requires qualified ephemeral Data and same-run full video restoration');ap.add_argument('--handset-data',action='store_true',help='Explicit ephemeral sparse APFS Data candidate; requires handset UFS and private scratch report');ap.add_argument('--handset-ufs',action='store_true',help='Independent handset UFS storage development profile; no handset boot qualification');ap.add_argument('--native-diagnostic',action='store_true',help='Explicit compiled return bridge after full original POST; never a desktop or production image');ap.add_argument('--offline-keystore',action='store_true',help='Explicit ephemeral unprotected scratch Data state service for emulator or handset diagnostics');ap.add_argument('--desktop-display',action='store_true',help='QEMU original-family display on actual firmware GOP; requires desktop Data');ap.add_argument('--desktop-data',action='store_true',help='QEMU-only independent writable scratch APFS with private default var');ap.add_argument('--scratch-data',type=Path);ap.add_argument('--source-crypto',action='store_true',help='Evaluate pinned public source provider with intact POST; no hardware qualification');ap.add_argument('--platform',action='store_true',help='Compile the generic DT platform expert with real source crypto; CPU/GIC remains disabled');ap.add_argument('--cpu',action='store_true',help='Build the independent one-CPU GICv3 provider; QEMU qualification first');ap.add_argument('--desktop',action='store_true',help='Build a separate OS-prelink provider mode; never replace the native-only index');ap.add_argument('--desktop-storage',action='store_true',help='Separate emulator-only VirtIO/APFS integration; requires live storage ABI audit');ap.add_argument('--storage-audit',type=Path);ap.add_argument('--storage-candidate',type=Path);ap.add_argument('--desktop-runtime',action='store_true',help='QEMU-only owner-managed authenticated OS/SystemOS composition');ap.add_argument('--desktop-root',action='store_true',help='QEMU-only owner-authenticated readonly original APFS root');ap.add_argument('--root-policy',type=Path);opt=ap.parse_args()
 if opt.observer_budget_ms!=420000:assert opt.watchdog_method_checkpoint=='observer-bound' and opt.native_console and opt.handset_display
 if opt.native_console:assert opt.service_observer and opt.handset_display
 if opt.watchdog_method_checkpoint=='observer-bound':assert opt.native_console
 os.environ['RAPHAEL_NATIVE_CONSOLE']='1' if opt.native_console else '0'
 log_allocation=None
 if opt.ufs_console_log_report:
  assert opt.native_console and not opt.native_ufs_write_policy
  from ufs_continuous_log import manifest
  log_allocation=manifest(opt.ufs_console_log_report)
 os.environ['RAPHAEL_UFS_CONSOLE_LOG_REPORT']=str(opt.ufs_console_log_report.resolve()) if log_allocation else ''
 if opt.service_spawn_waits:assert opt.service_observer and opt.watchdog_method_checkpoint=='first-method'
 os.environ['RAPHAEL_SERVICE_SPAWN_WAITS']='1' if opt.service_spawn_waits else '0'
 native_write=None
 if opt.native_ufs_write_policy:
  assert opt.handset_ufs and opt.native_diagnostic and not opt.handset_display and not opt.handset_data
  from ufs_write_probe import validate_manifest
  native_write=validate_manifest(opt.native_ufs_write_policy)
 os.environ['RAPHAEL_NATIVE_UFS_WRITE_POLICY']=str(opt.native_ufs_write_policy.resolve()) if native_write else ''
 if opt.watchdog_method_checkpoint:assert opt.service_observer and opt.handset_display and opt.native_diagnostic and not opt.native_ufs_write_policy
 if opt.service_observer:assert opt.handset_display and opt.native_diagnostic
 if opt.handset_display:assert opt.handset_data and opt.handset_ufs and not opt.desktop_display
 if opt.handset_data:
  assert opt.handset_ufs and opt.scratch_data and not opt.desktop_display and not opt.desktop_data
 if opt.handset_ufs:
  assert not opt.desktop_data and not opt.desktop_display
  if opt.handset_data:opt.desktop_data=True
  opt.desktop_runtime=True
 assert not opt.offline_keystore or opt.desktop_display or (opt.handset_display and opt.handset_data and opt.native_diagnostic)
 if opt.desktop_display:opt.desktop_data=True
 if opt.desktop_data:
  assert opt.scratch_data
  opt.desktop_runtime=True
 if opt.desktop_runtime:opt.desktop_root=True
 if opt.desktop_root:
  opt.desktop_storage=True
  assert opt.root_policy
 if opt.desktop_storage:
  opt.desktop=True
  assert opt.storage_audit and opt.storage_candidate
 if opt.native_diagnostic:
  assert opt.handset_ufs or (not opt.desktop and not opt.desktop_storage and not opt.desktop_display)
  opt.cpu=True
 if opt.desktop:opt.cpu=True
 if opt.cpu:opt.platform=True
 if opt.platform:opt.source_crypto=True
 display_enabled=opt.desktop_display or opt.handset_display
 configuration='raphael_handset_display_defconfig' if opt.handset_display else 'raphael_handset_data_defconfig' if opt.handset_data else 'raphael_handset_storage_defconfig' if opt.handset_ufs else 'raphael_desktop_display_defconfig' if opt.desktop_display else 'raphael_desktop_data_defconfig' if opt.desktop_data else 'raphael_desktop_runtime_defconfig' if opt.desktop_runtime else 'raphael_desktop_root_defconfig' if opt.desktop_root else 'raphael_desktop_storage_defconfig' if opt.desktop_storage else 'raphael_desktop_defconfig' if opt.desktop else 'raphael_cpu_defconfig' if opt.cpu else 'raphael_platform_defconfig' if opt.platform else 'raphael_sourcecrypto_defconfig' if opt.source_crypto else 'raphael_bootstrap_defconfig'
 out=ROOT/'artifacts/native-bootstrap-attempt'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
 (out/'runner.py').write_bytes(Path(__file__).read_bytes())
 common=['-D',str(ROOT/'UniXNU-raphael'),'--out',str(ROOT/'artifacts/native-bootstrap'),'-j','4']
 selected=Context(parser().parse_args(['defconfig',configuration,*common]));cmd_defconfig(selected)
 args=parser().parse_args(['build','kernel',*common])
 ctx=Context(args);cfg=ctx.need_config()
 os.environ['RAPHAEL_HANDSET_UFS']='1' if opt.handset_ufs else '0'
 if opt.handset_ufs:
  ctx.board['kernel']['patch_series'] += ['device:patches/xnu/handset-storage.series']
 if opt.native_diagnostic:
  ctx.board['kernel']['patch_series'] += ['device:patches/xnu/native-diagnostic.series']
 if native_write:
  ctx.board['kernel']['patch_series'] += ['device:patches/xnu/native-ufs-write.series']
 if opt.service_observer:
  ctx.board['kernel']['patch_series'] += ['device:patches/xnu/service-observer.series']
  ctx.board['kernel']['archives'] += ['build-raphael-service-observer.py']
 if opt.watchdog_method_checkpoint:
  ctx.board['kernel']['patch_series'] += ['device:patches/xnu/watchdog-method-checkpoint.series']
  if opt.watchdog_method_checkpoint=='first-display-client':
   ctx.board['kernel']['patch_series'] += ['device:patches/xnu/watchdog-display-client-checkpoint.series']
  if opt.watchdog_method_checkpoint=='first-method-plus-5s':
   ctx.board['kernel']['patch_series'] += ['device:patches/xnu/watchdog-service-window.series']
 os.environ['RAPHAEL_NATIVE_DIAGNOSTIC']='1' if opt.native_diagnostic else '0'
 if opt.desktop_storage:
  ctx.board['components']['include'] += ['SoftwareAES','VirtioMmioBlock']
  ctx.board['kernel']['archives'] += ['build-raphael-storage-bindings.py']
  os.environ['RAPHAEL_STORAGE_AUDIT']=str(opt.storage_audit.resolve())
  os.environ['RAPHAEL_STORAGE_CANDIDATE']=str(opt.storage_candidate.resolve())
 if opt.desktop_root:
  ctx.board['components']['include'] += ['VerifiedRoot']
  ctx.board['kernel']['archives'] += ['build-raphael-root-policy.py']
  os.environ['RAPHAEL_ROOT_POLICY']=str(opt.root_policy.resolve())
  os.environ['RAPHAEL_WORKSPACE']=str(ROOT)
 if opt.native_console:
  ctx.board['kernel']['patch_series'] += ['device:patches/xnu/native-console.series']
  if opt.watchdog_method_checkpoint=='observer-bound':
   ctx.board['kernel']['patch_series'] += ['device:patches/xnu/desktop-observer.series']
   if opt.observer_budget_ms in (780000,1860000):ctx.board['kernel']['patch_series'] += ['device:patches/xnu/desktop-extended-observer.series']
   if opt.observer_budget_ms==1860000:ctx.board['kernel']['patch_series'] += ['device:patches/xnu/desktop-scan-observer.series']
 if log_allocation:
  ctx.board['kernel']['patch_series'] += ['device:patches/xnu/ufs-console-log.series']
 if opt.handset_ufs:
  ctx.board['kernel']['archives'] += ['build-raphael-ufs.py']
 if opt.desktop_data:
  ctx.board['kernel']['archives'] += ['build-raphael-data-seed.py']
  os.environ['RAPHAEL_SCRATCH_DATA']=str(opt.scratch_data.resolve())
  ctx.board['components']['include'] += ['RamBlock']
  data_report=json.loads(opt.scratch_data.read_text());assert data_report['passed']
  os.environ['XNU_OWNER_DATA_VOLUME_UUID']=data_report['volume_uuid']
 if display_enabled:
  os.environ['RAPHAEL_HANDSET_DISPLAY']='1' if opt.handset_display else '0'
  os.environ['RAPHAEL_OFFLINE_KEYSTORE']='1' if opt.offline_keystore else '0'
  if opt.offline_keystore:ctx.board['components']['include'] += ['AppleKeyStoreState']
  ctx.board['kernel']['archives'] += ['build-raphael-desktop-display.py']
  os.environ['RAPHAEL_DISPLAY_CANDIDATE']=str(opt.storage_candidate.resolve())
 if opt.fairplay_aes_trace:
  assert opt.service_observer and opt.handset_display
  ctx.board['kernel']['archives'] += ['build-raphael-aes-trace.py']
 assert bool(cfg['XNU_BUILD_ARCHIVES'])==bool(cfg['XNU_SOURCE_CORECRYPTO14'])==opt.source_crypto
 assert cfg['XNU_CRYPTO_BOOTSTRAP']==('prelinked' if opt.desktop else 'source' if opt.source_crypto else 'prelinked')
 assert bool(cfg['XNU_ARM_DT_PLATFORM'])==opt.platform
 assert bool(cfg['XNU_ARMCPU'])==bool(cfg['XNU_NATIVE_ARCH_TIMER'])==opt.cpu
 for k in ['XNU_NATIVE_UFS','XNU_NATIVE_ADRENO']:assert not cfg[k]
 assert cfg['XNU_DT_PANIC_REGION'], 'SM8150 must never use the generic target panic-log address'
 os.environ['RAPHAEL_SOC_SOURCE']=str(ROOT/'UniXNU-sm8150-common')
 revision=subprocess.check_output(['git','-C',str(UP),'rev-parse','HEAD'],text=True).strip();assert revision==locked_revision('UniXNU')
 upstream_changed=subprocess.check_output(['git','-C',str(UP),'diff','--name-only'],text=True).splitlines()
 inputs=[]
 for root in [ROOT/'UniXNU-sm8150-common',ROOT/'UniXNU-raphael']:
  for p in root.rglob('*'):
   if not p.is_file() or p.name=='local.toml' or any(n in p.parts for n in ['evidence','.cache']):continue
   data=p.read_bytes();relative=p.relative_to(ROOT);dest=out/'snapshot'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);inputs.append(dict(path=str(relative),sha256=sha(data)))
 report=dict(passed=False,native_compile_only=True,compiled_diagnostic_return=opt.native_diagnostic,prelink_executed=False,handset_executed=False,source_revision=revision,configuration=configuration,source_crypto_evaluation=opt.source_crypto,crypto_bootstrap_mode=cfg['XNU_CRYPTO_BOOTSTRAP'],desktop_prelink_input=opt.desktop,handset_ufs_development=opt.handset_ufs,emulator_storage_only=opt.desktop_storage and not opt.handset_ufs,emulator_root_only=opt.desktop_root and not opt.handset_ufs,emulator_owner_runtime=opt.desktop_runtime and not opt.handset_ufs,emulator_scratch_data=opt.desktop_data and not opt.handset_data,handset_scratch_data_candidate=opt.handset_data,handset_display_candidate=opt.handset_display,service_observer_candidate=opt.service_observer,watchdog_method_checkpoint=bool(opt.watchdog_method_checkpoint),watchdog_checkpoint_mode=opt.watchdog_method_checkpoint,emulator_gop_display=opt.desktop_display,ephemeral_offline_keystore=opt.offline_keystore,dt_platform_enabled=opt.platform,independent_cpu_enabled=opt.cpu,upstream_armcpu_linked=False,source_pthread_enabled=bool(cfg['XNU_SOURCE_PTHREAD']),module_upstream_sync_executed=False,source_inputs=inputs,artifact_directory=str(out.relative_to(ROOT)),backend='pinned unixnu.kernel.build; no kernel.prelink invocation',runner_sha256=sha(Path(__file__).read_bytes()))
 # Keep the pinned base revision and freeze local source edits consumed through assembled symlinks.
 report['source_tree_dirty']=bool(upstream_changed)
 report['local_source_changes']=[]
 for repository in [UP]+[UP/path for path in upstream_changed if (UP/path/'.git').exists()]:
  changed=subprocess.check_output(['git','-C',str(repository),'diff','--name-only'],text=True).splitlines()
  for name in changed:
   source=repository/name
   if not source.is_file():continue
   relative=source.relative_to(UP);target=out/'snapshot/UniXNU'/relative
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
   report['local_source_changes'].append(str(relative))
 report['service_spawn_waits']=opt.service_spawn_waits
 report['native_console']=opt.native_console
 report['observer_budget_ms']=opt.observer_budget_ms
 report['ufs_console_log_report']=str(opt.ufs_console_log_report.resolve().relative_to(ROOT)) if log_allocation else None
 report['native_ufs_write_probe']=native_write
 if os.environ.get('RAPHAEL_DISPLAY_SOURCE'):
  assert opt.handset_display and (opt.watchdog_method_checkpoint=='first-method-plus-5s' or opt.service_spawn_waits or opt.native_console)
  display_source=Path(os.environ['RAPHAEL_DISPLAY_SOURCE']).resolve()
  assert display_source.is_relative_to(ROOT/'artifacts/native-bootstrap-attempt')
  display_bytes=display_source.read_bytes()
  assert sha(display_bytes)==os.environ['RAPHAEL_DISPLAY_SOURCE_SHA256']
  selected=out/'selected-inputs/RaphaelDesktopDisplay.cpp';selected.parent.mkdir();selected.write_bytes(display_bytes)
  report['selected_display_source']=dict(path=str(display_source.relative_to(ROOT)),sha256=sha(display_bytes),frozen_path=str(selected.relative_to(ROOT)),live_source_preserved=True)
 try:
  modules=prepare_local(ctx)
  report['modules']=[dict(kind=m.kind,name=m.name,path=str(m.path) if m.path else None,commit=subprocess.check_output(['git','-C',str(m.path),'rev-parse','HEAD'],text=True).strip() if m.path else None) for m in modules.values()]
  report['patches']=[dict(path=str(p),sha256=sha(p.read_bytes())) for p in patches.plan(ctx,modules)]
  from cache_native_headers import cache_headers
  report['public_headers']=cache_headers(ctx.tree)
  from cache_native_runtime import cache_runtime
  # Reuse exact existing local caches; no remote operation is involved.
  cache=ctx.tree/'.cache/linux'
  for name in ['llvm-project','Libc']:
   destination=cache/name
   if not (destination/'.git').exists():
    candidates=sorted((ROOT/'artifacts/native-bootstrap/raphael/ipados-17.7.11-21H461').glob('*/tree/.cache/linux/'+name))
    source=next((p for p in candidates if p!=destination and (p/'.git').exists() and subprocess.run(['git','-C',str(p),'rev-parse','HEAD'],capture_output=True).returncode==0),None)
    if source is not None:
     if destination.exists() and not any(destination.iterdir()):destination.rmdir()
     if not destination.exists():shutil.copytree(source,destination,symlinks=True)
  report['runtime_sources']=cache_runtime(ctx.tree)
  kernel.build(ctx,modules)
  image=ctx.tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/mach.development.bcm2837.unstripped.noctf'
  raw=image.read_bytes();magic,cpu,sub,kind,ncmds,sizeofcmds=struct.unpack_from('<6I',raw)
  assert magic==0xfeedfacf and cpu==0x100000c and ncmds>0 and 32+sizeofcmds<=len(raw)
  frozen=out/'native-kernel.macho';frozen.write_bytes(raw)
  records=[];records_root=ctx.tree/'build/xnu/ios-obj';frozen_root=out/'compile-records'
  for record in sorted(records_root.rglob('*.o.json')):
   relative=record.relative_to(records_root);target=frozen_root/relative;target.parent.mkdir(parents=True,exist_ok=True)
   record_raw=record.read_bytes();target.write_bytes(record_raw);records.append(dict(path=str(relative),sha256=sha(record_raw)))
  assert records and sha(frozen.read_bytes())==sha(raw)
  report.update(passed=True,native_macho=dict(path=str(frozen.relative_to(ROOT)),build_path=str(image.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw),filetype=kind,load_commands=ncmds),
   compile_records_root=str(frozen_root.relative_to(ROOT)),frozen_compile_records=records,outputs_frozen=True)
 except Exception as error:
  report['failure']=type(error).__name__+': '+str(error);(out/'exception.txt').write_text(traceback.format_exc())
 finally:
  report['compile_records']=len(report['frozen_compile_records']) if report.get('outputs_frozen') else len(list((ctx.tree/'build/xnu/ios-obj').rglob('*.o.json')))
  report['auxiliary_artifacts']=[]
  crypto=ctx.tree/'build/corecrypto-2023'
  if crypto.is_dir():
   for item in sorted(crypto.iterdir()):
    if not item.is_file() or item.suffix not in ['.a','.json','.h']:continue
    data=item.read_bytes();target=out/'auxiliary/corecrypto-2023'/item.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report['auxiliary_artifacts'].append(dict(path=str(target.relative_to(ROOT)),bytes=len(data),sha256=sha(data)))
  for directory in ['armdt-platform','armcpu','libpthread-kernel','raphael-ufs','storage-abi','verified-root','raphael-data-seed','ram-block','native-legacy-display','raphael-service-observer']:
   auxiliary=ctx.tree/'build'/directory
   if auxiliary.is_dir():
    for item in sorted(auxiliary.iterdir()):
     if item.is_file():
      raw=item.read_bytes();target=out/'auxiliary'/directory/item.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
      report['auxiliary_artifacts'].append(dict(path=str(target.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw)))
  report['logs']=[]
  for source_log in sorted(ctx.logs.glob('*.log')):
   data=source_log.read_bytes();target=out/'logs'/source_log.name;target.parent.mkdir(exist_ok=True);target.write_bytes(data)
   report['logs'].append(dict(path=str(target.relative_to(ROOT)),build_path=str(source_log.relative_to(ROOT)),sha256=sha(data)))
  for p in [out/'report.json',ROOT/('UniXNU-raphael/evidence/handset-display-bootstrap-host.json' if opt.handset_display else 'UniXNU-raphael/evidence/handset-data-bootstrap-host.json' if opt.handset_data else 'UniXNU-raphael/evidence/handset-storage-bootstrap-host.json' if opt.handset_ufs else 'UniXNU-raphael/evidence/native-compiled-return-host.json' if opt.native_diagnostic else 'UniXNU-raphael/evidence/desktop-display-bootstrap-host.json' if opt.desktop_display else 'UniXNU-raphael/evidence/desktop-data-bootstrap-host.json' if opt.desktop_data else 'UniXNU-raphael/evidence/desktop-runtime-bootstrap-host.json' if opt.desktop_runtime else 'UniXNU-raphael/evidence/desktop-root-bootstrap-host.json' if opt.desktop_root else 'UniXNU-raphael/evidence/desktop-storage-bootstrap-host.json' if opt.desktop_storage else 'UniXNU-raphael/evidence/desktop-bootstrap-host.json' if opt.desktop else 'UniXNU-raphael/evidence/native-bootstrap-host.json')]:p.write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(dict(passed=report['passed'],failure=report.get('failure'),compile_records=report['compile_records'],artifact_directory=str(out)),indent=2))
 if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
