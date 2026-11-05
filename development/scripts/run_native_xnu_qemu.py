#!/usr/bin/env python3
"""Execute the frozen native kernel with pinned DarwinBoot on QEMU/AAVMF only.

Stops at a selected native symbol or the first observed panic/low-vector checkpoint. Kernel
bytes are never patched, and no phone memory or peripheral inputs are used.
"""
import argparse,bisect,datetime as dt,json,os,re,shutil,signal,socket,struct,subprocess,sys,tempfile,time
from pathlib import Path
from entry_probe import ROOT,sha
from run_handoff_fixture import PINS

def main():
 p=argparse.ArgumentParser();p.add_argument('--offline-keystore',action='store_true',help='Ephemeral unprotected QEMU Data state only; no key operations');p.add_argument('--keep-paused',action='store_true',help='Keep this isolated QEMU stopped after observation for continued dependency work; no handset effect');p.add_argument('--capture-data-after',type=int,default=0,help='After this QEMU observation time, capture the owned dense Data RAM once for offline filesystem inspection');p.add_argument('--runtime-main-program',type=Path,help='Unchanged original executable to observe through dyld into actual LC_MAIN');p.add_argument('--progress-seconds',type=int,default=0,help='QEMU-only read-only stopped process snapshots at this interval, then continue');p.add_argument('--desktop-display',action='store_true',help='Enable independent original-family GOP display backend; QEMU only');p.add_argument('--gop',action='store_true',help='QEMU ramfb device; real AAVMF GOP video, not handset display');p.add_argument('--sparse-data',action='store_true',help='Keep lossless packed Data for the existing sparse RAM block backend; QEMU only');p.add_argument('--shared-data-volume',action='store_true',help='Pass the original APFS shared Data policy; requires an isolated scratch Data');p.add_argument('--runtime-process',help='Observe real EL0 execution of this exact process comm after original launchd main; event-filtered, not desktop acceptance');p.add_argument('--scratch-data',type=Path,help='Private NEW emulator scratch APFS preparation report; copied to RAMDisk');p.add_argument('--main-program',type=Path,help='Unchanged original Mach-O; follow LC_MAIN through actual EL0 startup stack');p.add_argument('--user-syscalls',type=int,default=1,help='Bounded number of verified PID1 syscall entries to observe');p.add_argument('--user-abi',type=Path,help='Same-build DWARF ABI report for real PID1 EL0 observation');p.add_argument('--kernel-window-mb',type=int,choices=[256,512,1024,1536],default=256,help='Explicit real DarwinBoot allocation in QEMU, not just machine RAM');p.add_argument('--memory-mb',type=int,choices=[512,1024,2048],default=512,help='Explicit emulator RAM only');p.add_argument('--trust-bundle',type=Path,help='Original trust-cache preparation report');p.add_argument('--system-disks',type=Path,help='Original APFS disk report; QEMU attaches read-only');p.add_argument('--capture-memory',type=Path,help='Read bounded same-image metadata at target; no guest writes');p.add_argument('--os-profile',action='store_true',help='Add selected OS ABI identity only; all emulated hardware remains sourced from QEMU FDT');p.add_argument('--inspection',type=Path,default=ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json');p.add_argument('--stop-at',choices=['arm_init','PE_init_platform','kernel_bootstrap','machine_startup','kernel_bootstrap_thread','PE_init_iokit','bsd_init','platform_configured','cpu_ready','timer_irq','find_root','block_read','mount_root','load_init','user_syscall','launchd_main','data_seed','launchd_runtime','display','display_frame'],default='arm_init');p.add_argument('--boot-cpu',choices=['virtual','physical'],help='Qualify the independent boot CPU on explicit QEMU GICv3 resources');p.add_argument('--observe-seconds',type=int,default=35,help='Bounded debugger observation deadline; captures a stopped CPU on expiry');p.add_argument('--kalloc-zones',type=int,help='Explicit emulator-only Apple kt_fixed_zones tunable; kernel checks remain enabled');a=p.parse_args()
 assert not a.capture_data_after or (a.scratch_data and a.progress_seconds and a.capture_data_after>=60)
 assert a.progress_seconds==0 or 30<=a.progress_seconds<=300
 assert not a.offline_keystore or (a.desktop_display and a.scratch_data and a.shared_data_volume)
 assert not a.desktop_display or a.gop
 assert not a.keep_paused or a.gop
 assert 5<=a.observe_seconds<=1800
 assert 1<=a.user_syscalls<=256
 assert not a.runtime_process or (a.stop_at in ('launchd_runtime','display_frame') and 0<len(a.runtime_process.encode('ascii'))<=15)
 assert a.kernel_window_mb<a.memory_mb
 assert a.stop_at not in ('user_syscall','launchd_main','launchd_runtime') or a.user_abi
 assert a.stop_at not in ('launchd_main','launchd_runtime') or a.main_program
 assert not a.system_disks or (a.os_profile and a.boot_cpu)
 assert not a.scratch_data or a.system_disks
 assert not a.shared_data_volume or a.scratch_data
 assert not a.sparse_data or a.scratch_data
 assert a.stop_at!='data_seed' or a.scratch_data
 if a.kalloc_zones is not None:assert 1<=a.kalloc_zones<=65535
 parent=ROOT/'artifacts/native-xnu-qemu';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 report=dict(passed=False,stop_at=a.stop_at,artifact_directory=str(out.relative_to(ROOT)),handset_executed=False,
  source_revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
  xnu_entry_verified=False,xnu_arm_init_verified=False,full_xnu_boot_verified=False,
  qemu_ram_megabytes=a.memory_mb,qemu_kernel_window_megabytes=a.kernel_window_mb,minimal_emulator_adt=True,runner_sha256=sha(Path(__file__).read_bytes()))
 (out/'runner.py').write_bytes(Path(__file__).read_bytes())
 commands=[];proc=None;sock=Path('/tmp')/('rnx-'+out.name[:22]+'.sock');qmp_sock=sock.with_suffix('.qmp')
 def command(args,**kwargs):
  args=list(map(str,args));commands.append(args);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  return subprocess.run(args,check=True,**kwargs)
 try:
  debugger=Path(shutil.which('gdb-multiarch'));report['debugger_tool']=dict(path=str(debugger),sha256=sha(debugger.read_bytes()),version=command([debugger,'--version'],capture_output=True,text=True).stdout.splitlines()[0])
  inspection=json.loads(a.inspection.read_text());assert inspection['passed'] and inspection['undefined_symbol_count']==0
  frozen=ROOT/inspection['artifact_directory'];kernel=(frozen/'native-kernel.macho').read_bytes()
  assert sha(kernel)==inspection['native_macho_sha256']
  segments=[]
  for segment in inspection['segments']:
   item={k:segment[k] for k in ['name','virtual_address','file_offset','file_bytes']}
   item['sha256']=sha(kernel[item['file_offset']:item['file_offset']+item['file_bytes']]);segments.append(item)
  (out/'kernel-inspection.json').write_bytes(a.inspection.read_bytes());(out/'native-kernel.macho').write_bytes(kernel)
  report.update(kernel_sha256=sha(kernel),kernel_bytes=len(kernel),kernel_unchanged=True)
  snapshot=out/'snapshot';inputs=[];revisions={}
  for repository,expected in PINS.items():
   rev=subprocess.check_output(['git','-C',str(ROOT/repository),'rev-parse','HEAD'],text=True).strip();assert rev==expected
   assert not subprocess.check_output(['git','-C',str(ROOT/repository),'diff','--name-only'],text=True).strip()
   revisions[repository]=rev
  for folder in ['tests/RaphaelTestPkg','sources/UniXNU/package/UniXNUPkg','sources/UniXNU/drivers/DarwinBoot/DarwinBootPkg']:
   for path in sorted((ROOT/folder).rglob('*')):
    if not path.is_file():continue
    relative=path.relative_to(ROOT);raw=path.read_bytes()
    for repository in sorted(PINS,key=len,reverse=True):
     if path.is_relative_to(ROOT/repository):
      assert raw==subprocess.check_output(['git','-C',str(ROOT/repository),'show',revisions[repository]+':'+str(path.relative_to(ROOT/repository))]);break
    dest=snapshot/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    inputs.append(dict(path=str(relative),sha256=sha(raw)))
  observer=ROOT/'scripts/fixtures/native_xnu_gdb.py';observer_raw=observer.read_bytes();(out/'observer.py').write_bytes(observer_raw)
  report.update(source_inputs=inputs,revisions=revisions,observer_sha256=sha(observer_raw))
  core=ROOT/'sources/mu_basecore';conf=out/'Conf';conf.mkdir();toolchain=out/'toolchain';toolchain.mkdir()
  for name in ['target','tools_def','build_rule']:shutil.copyfile(core/'BaseTools/Conf'/(name+'.template'),conf/(name+'.txt'))
  for name in ['clang','clang++','lld-link','llvm-lib','llvm-objcopy']:
   actual=shutil.which(name);assert actual;(toolchain/name).symlink_to(actual)
  env=dict(os.environ,WORKSPACE=str(out),CONF_PATH=str(conf),EDK_TOOLS_PATH=str(core/'BaseTools'),
   PACKAGES_PATH=':'.join(map(str,[snapshot/'tests',snapshot/'sources/UniXNU/package',snapshot/'sources/UniXNU/drivers/DarwinBoot',core])),
   CLANG_BIN=str(toolchain)+'/',PYTHON_COMMAND='python3',SOURCE_DATE_EPOCH='1793088000',
   PATH=str(core/'BaseTools/BinWrappers/PosixLike')+':'+str(core/'BaseTools/Source/C/bin')+':'+os.environ['PATH'])
  with (out/'build.log').open('xb') as log:command(['build','-p','RaphaelTestPkg/NativeXnuFixture.dsc','-a','AARCH64','-b','DEBUG','-t','CLANGPDB','-n','4'],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
  binary=out/'Build/RaphaelNativeXnuFixture/DEBUG_CLANGPDB/AARCH64';report['host_build_passed']=True
  images={}
  for name,subsystem in [('DarwinBoot','IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER'),('NativeXnuFixture','IMAGE_SUBSYSTEM_EFI_APPLICATION')]:
   file=binary/(name+'.efi');headers=command(['llvm-readobj','--file-headers','--sections',file],capture_output=True,text=True).stdout
   (out/(name+'-pe.txt')).write_text(headers);assert 'IMAGE_FILE_MACHINE_ARM64' in headers and subsystem in headers and '.reloc' in headers
   images[name]=dict(sha256=sha(file.read_bytes()),bytes=file.stat().st_size)
  report.update(images=images,image_structure_passed=True)
  sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'));from unixnu.devicetree import node
  from inspect_device import read_fdt,registers
  from unixnu.devicetree import empty_nvram_proxy
  disk_arguments=[];system_disks=None
  display_arguments=['-device','ramfb'] if a.gop else []
  report['qemu_ramfb_requested']=a.gop
  if a.system_disks:
   system_disks=json.loads(a.system_disks.read_text());assert system_disks['passed']
   disk_arguments=['-global','virtio-mmio.force-legacy=false']
   assert {d['role'] for d in system_disks['disks']}=={'OS','SystemOS'}
   for index,disk in enumerate(system_disks['disks']):
    path=(ROOT/disk['path']).resolve();assert path.is_relative_to(ROOT/'artifacts') and path.stat().st_size==disk['bytes']
    disk_arguments+=['-drive',f"if=none,id=system{index},format=raw,readonly=on,file={path}",'-device',f'virtio-blk-device,drive=system{index}']
   os_disk=next(d for d in system_disks['disks'] if d['role']=='OS')
   assert len(os_disk['apfs_containers'])==1 and len(os_disk['apfs_containers'][0]['volumes'])==1
   root_uuid=os_disk['apfs_containers'][0]['volumes'][0]
   report['read_only_system_disks']=system_disks
   report['root_volume_uuid']=root_uuid
  dtb=out/'qemu-generated.dtb'
  machine='virt,gic-version=3' if a.boot_cpu else 'virt'
  command(['qemu-system-aarch64','-machine',machine+',dumpdtb='+str(dtb),'-cpu','cortex-a57','-m',str(a.memory_mb),'-nographic','-net','none',*display_arguments,*disk_arguments],capture_output=True)
  fdt=read_fdt(dtb.read_bytes());nodes=list(fdt.walk())
  ram=[n for n in fdt.children if n.strings('device_type')==['memory']];assert len(ram)==1
  dram=registers(ram[0]);assert len(dram)==1
  dram_base,dram_size=dram[0]
  io=[n for n in nodes if any(c in ['arm,cortex-a15-gic','arm,gic-v3','arm,pl011',*(['virtio,mmio'] if system_disks else [])] for c in n.strings('compatible'))]
  spans=[(a,n) for entry in io for a,n in registers(entry)];assert spans and all(a and n for a,n in spans)
  base=min(a for a,n in spans);end=max(a+n for a,n in spans)
  cpus=next(n for n in fdt.children if n.name=='cpus');cpu=next(n for n in cpus.children if n.strings('device_type')==['cpu'])
  affinity=cpu.cells('reg');assert len(affinity)==1 and affinity[0]==0
  report['emulator_hardware_source']=dict(dtb_sha256=sha(dtb.read_bytes()),io_ranges=spans,arm_io_base=base,arm_io_bytes=end-base,cpu_affinity=affinity[0],dram_base=dram_base,dram_bytes=dram_size)
  cpu_properties=[];io_children=[]
  if a.boot_cpu:
   gics=[n for n in nodes if 'arm,gic-v3' in n.strings('compatible')];assert len(gics)==1
   gic=gics[0];gic_regs=registers(gic);assert len(gic_regs)==2
   timers=[n for n in nodes if 'arm,armv8-timer' in n.strings('compatible')];assert len(timers)==1
   interrupts=timers[0].cells('interrupts');assert len(interrupts)==12
   index=1 if a.boot_cpu=='physical' else 2
   irq_type,irq,flags=interrupts[index*3:index*3+3]
   assert irq_type==1 and 0<=irq<16 and flags&15 in [4,8]
   timer_id=16+irq
   cpu_properties=[('unixnu,boot-cpu',struct.pack('<I',1)),('unixnu,timer-intid',struct.pack('<I',timer_id)),
    ('unixnu,physical-timer',struct.pack('<I',a.boot_cpu=='physical')),('unixnu,timer-flags',struct.pack('<I',flags&15))]
   properties=[('compatible',b'arm,gic-v3\0'),('reg',struct.pack('<4Q',*[value for address,length in gic_regs for value in [address-base,length]]))]
   if 'redistributor-stride' in gic.properties:
    cells=gic.cells('redistributor-stride');stride=0
    for cell in cells:stride=(stride<<32)|cell
    properties.append(('redistributor-stride',struct.pack('<Q',stride)))
   io_children=[node('intc',properties)]
   report['independent_cpu_resources']=dict(gic_registers=gic_regs,timer=a.boot_cpu,timer_fdt_specifier=interrupts[index*3:index*3+3],timer_intid=timer_id,source='same-run qemu-generated.dtb; counter frequency independently checked at EL1')
  root_properties=dict(model=fdt.properties['model'],compatible=fdt.properties['compatible'])
  chosen_properties=[];defaults_properties=[];os_children=[]
  if a.os_profile:
   from unixnu.cli import parser as cli_parser
   from unixnu.config import Context
   from unixnu.devicetree import typed_properties,platform_node
   context=Context(cli_parser().parse_args(['status','-D',str(ROOT/'UniXNU-raphael')]))
   platform=context.board['adt']
   identity=dict(typed_properties(platform.get('root',{})))
   identity['compatible']=identity.get('compatible',b'')+root_properties['compatible']
   root_properties.update(identity)
   chosen_properties=typed_properties(platform.get('chosen',{}))
   defaults_properties=typed_properties(platform.get('defaults',{}))
   # This flag truthfully describes this QEMU runner only. Never export it to the handset ADT.
   assert not any(k=='vmm-present' for k,v in defaults_properties)
   defaults_properties.append(('vmm-present',struct.pack('<I',1)))
   report['qemu_vmm_declared']=True
   os_children=[platform_node('product',platform['product'])]
   report['os_profile_identity']=dict(profile=context.board['board']['os_profile'],root_keys=sorted(root_properties),chosen_keys=[k for k,v in chosen_properties],hardware_source='same-run QEMU FDT; no Apple MMIO, CPU or memory nodes imported')
   report['minimal_emulator_adt']=False
  if system_disks:
   # Match the volume observed in the original image rather than relying on an Apple boot snapshot resource.
   chosen_properties.append(('root-matching',('<dict><key>IOProviderClass</key><string>IOMedia</string><key>IOPropertyMatch</key><dict><key>UUID</key><string>'+root_uuid.upper()+'</string></dict></dict>\0').encode()))
   for index,virtio in enumerate(n for n in nodes if 'virtio,mmio' in n.strings('compatible')):
    [(address,length)]=registers(virtio)
    assert 'dma-coherent' in virtio.properties
    io_children.append(node('virtio-block'+str(index),[('compatible',b'virtio,mmio\0'),('device_type',b'virtio,mmio\0'),('reg',struct.pack('<2Q',address-base,length)),('dma-coherent',b'')]))
  if a.desktop_display:
   # OS enumeration contract read from this candidate's unchanged
   # iomfb_populate_all_display_infos: direct /arm-io child device_type.
   # This describes the existing firmware scanout, not an Apple controller;
   # no reg/MMIO, interrupt or handset resource is fabricated.
   io_children.append(node('raphael-gop',[('device_type',b'display-subsystem\0'),('compatible',b'raphael,firmware-gop\0')]))
   # Explicit logical policy for this firmware mode: one logical pixel per
   # real GOP pixel. Zero is not a valid FBSDisplayMode scale/override pair.
   chosen_properties.append(('display-scale',struct.pack('<I',1)))
   # This stable UUID identifies our isolated emulator, not a handset or Apple SoC.
   # The independent platform consumes it without inventing Apple ECID/chip-id.
   import uuid
   platform_uuid=uuid.uuid5(uuid.NAMESPACE_URL,'urn:unixnu:raphael:fresh:desktop-qemu')
   assert not any(k=='unixnu-platform-uuid' for k,v in chosen_properties)
   chosen_properties.append(('unixnu-platform-uuid',platform_uuid.bytes))
   report['emulator_platform_identity']=dict(uuid=str(platform_uuid),path='/chosen/unixnu-platform-uuid',source='port-assigned UUIDv5 for this isolated development VM',handset_identity=False)

   report['emulator_display_scale_policy']=dict(value=1,meaning='one logical pixel per firmware GOP pixel',handset_hardware_fact=False)
   report['emulator_display_declaration']=dict(path='/arm-io/raphael-gop',device_type='display-subsystem',hardware_registers_declared=False,source='selected original IOMobileFramebuffer iomfb_populate_all_display_infos; firmware GOP resource independently obtained at runtime')
  assert a.kernel_window_mb*1048576+128*1048576<=dram_size
  chosen_properties.append(('darwinboot-memory-size',struct.pack('<Q',a.kernel_window_mb*1048576)))
  mappings=[]
  if a.trust_bundle:
   trust=json.loads(a.trust_bundle.read_text());assert trust['passed'] and trust['original_modules_unchanged'] and not trust['added_owner_cdhashes']
   mappings=[('TrustCache',bytes(16))]
   report['original_trust_cache']=trust
  scratch_data=None
  if a.scratch_data:
   scratch_data=json.loads(a.scratch_data.read_text());assert scratch_data['passed'] and not scratch_data['handset_executed']
   data_image=(ROOT/scratch_data['image']).resolve();assert data_image.is_relative_to(ROOT/'evidence/private/desktop-data') and data_image.is_file() and data_image.stat().st_size==scratch_data['bytes']
   mappings.append(('PackedRAMDisk' if a.sparse_data else 'RAMDisk',bytes(16)))
   report['emulator_scratch_data']=scratch_data
  tree=node('device-tree',list(root_properties.items()),
   [node('chosen',[('dram-base',struct.pack('<Q',dram_base)),('dram-size',struct.pack('<Q',dram_size)),('random-seed',os.urandom(64)),*empty_nvram_proxy(),*chosen_properties],[node('memory-map',mappings),*([node('manifest-properties',[])] if a.os_profile else [])]),
    node('cpus',[],[node('cpu0',[('device_type',b'cpu\0'),('reg',struct.pack('<I',affinity[0])),('state',b'running\0'),
     ('compatible',cpu.properties['compatible']),('timebase-frequency',struct.pack('<I',62500000)),*cpu_properties])]),
    node('arm-io',[('device_type',b'arm-io\0'),('ranges',struct.pack('<3Q',0,base,end-base))],io_children),node('defaults',defaults_properties),node('options',[]),*os_children])
  esp=out/'esp';boot=esp/'EFI/BOOT';boot.mkdir(parents=True);target=esp/'EFI/UniXNU';target.mkdir(parents=True)
  shutil.copyfile(binary/'NativeXnuFixture.efi',boot/'BOOTAA64.EFI');shutil.copyfile(binary/'DarwinBoot.efi',esp/'DarwinBoot.efi')
  (target/'native.macho').write_bytes(kernel);(target/'native.macho.adt').write_bytes(tree)
  if scratch_data:
   if a.sparse_data or scratch_data['bytes']>256*1048576:
    # Reuse the pinned lossless DBRDISK1 loader interface. Omitted pages are
    # restored to real zeroed owned RAM; the XNU device remains dense RAMDisk.
    sys.path.insert(0,str(ROOT/'sources/UniXNU/drivers/DarwinBoot/Test'))
    from packed_ramdisk import pack
    packed=pack(data_image,target/'data.raw')
    report['emulator_data_transport']=dict(kind='DBRDISK1 retained for sparse RAM block' if a.sparse_data else 'DBRDISK1 expanded by original DarwinBoot',metadata=packed,logical_bytes=scratch_data['bytes'],handset_written=False)
   else:shutil.copyfile(data_image,target/'data.raw')
  if a.trust_bundle:shutil.copyfile(ROOT/trust['bundle'],target/'native.macho.trustcache')
  boot_arguments='-v keepsyms=1 cpus=1'+(' kt_fixed_zones='+str(a.kalloc_zones) if a.kalloc_zones is not None else '')
  if system_disks:boot_arguments+=' offline-apfs-load=1'
  if a.offline_keystore:boot_arguments+=' raphael-offline-keystore=1'
  if a.shared_data_volume:boot_arguments+=' -apfs_shared_datavolume'
  if a.desktop_display:boot_arguments+=' raphael-desktop-display=1 offline-mobile-graphics-load=1'
  report['boot_arguments']=boot_arguments;report['kalloc_budget_override']=a.kalloc_zones
  (target/'unixnu.toml').write_text('version = 1\n[boot]\ntimeout = 0\n[kits]\nautoload = false\n[[entry]]\nid = "native-entry"\ntitle = "Native XNU entry diagnostic"\ntype = "xnu"\npath = "native.macho"\nargs = "'+boot_arguments+'"\n'+('initrd = "data.raw"\n' if scratch_data else ''))
  before={str(p.relative_to(esp)):sha(p.read_bytes()) for p in esp.rglob('*') if p.is_file()}
  report['adt']=dict(bytes=len(tree),sha256=sha(tree),hardware_qualified=False)
  shutil.copyfile('/usr/share/AAVMF/AAVMF_VARS.fd',out/'vars.fd')
  report['emulator_firmware']={n:sha(Path('/usr/share/AAVMF',n).read_bytes()) for n in ['AAVMF_CODE.fd','AAVMF_VARS.fd']}
  symbols={}
  nm=command(['llvm-nm','--defined-only',out/'native-kernel.macho'],capture_output=True,text=True).stdout;(out/'symbols.txt').write_text(nm)
  wanted=['_write','_exit','_execve','_posix_spawn','_start_first_cpu','_arm_init','_PE_init_platform','_kernel_bootstrap','_machine_startup','_kernel_bootstrap_thread','_PE_init_iokit','_bsd_init','_kalloc_type_apply_policy','_source_corecrypto14_bootstrap','_corecrypto_kext_start','_fipspost_post','_register_crypto_functions','_panic','_panic_with_options','_LowExceptionVectorBase','__ZN13ArmDTPlatform9configureEP9IOService','__ZN14RaphaelBootCpu5startEP9IOService','__ZN14RaphaelBootCpu9interruptEv','_rtclock_intr','_IOFindBSDRoot','_ml_processor_register','_PE_cpu_machine_init','__ZN9IOService14waitForServiceEP12OSDictionaryP13mach_timespec','_native_virtio_read_checkpoint','_vfs_mountroot','_load_init_program','_thread_setentrypoint','_unix_syscall','_exec_mach_imgact','_native_apfs_probe_checkpoint','_native_owner_root_checkpoint','_native_owner_root_accepted_checkpoint','_raphael_data_seed_checkpoint','_raphael_display_checkpoint','_raphael_display_frame_checkpoint']
  for line in nm.splitlines():
   parts=line.split()
   if len(parts)==3 and parts[2] in wanted:symbols[parts[2]]=int(parts[0],16)
  assert '_arm_init' in symbols and '_start_first_cpu' in symbols
  data_symbols={}
  for line in nm.splitlines():
   parts=line.split()
   if len(parts)==3 and ((parts[2].startswith(('_raphael_display_','_native_ram_block_','_raphael_offline_aks_')) and parts[2]!='_native_ram_block_seed_sha256' and any(seg['name']=='__DATA' and seg['virtual_address']<=int(parts[0],16)<seg['virtual_address']+seg['virtual_bytes'] for seg in inspection['segments'])) or parts[2] in ['_native_pt_attr','_gPhysBase','_gVirtBase','_real_phys_size','_ptov_table','_native_owner_data_seed_base','_native_ram_block_reads','_native_ram_block_writes','_native_ram_block_failures','_allproc','_raphael_display_hardware_stage','_raphael_display_video_status','_raphael_display_row_bytes','_raphael_display_depth','_raphael_display_rotate','_raphael_display_map_length','_raphael_display_stage','_raphael_display_guard','_raphael_display_clients','_raphael_display_surface_status','_raphael_display_family_status','_raphael_display_meta_status','_raphael_display_base','_raphael_display_width','_raphael_display_height','_msgbufp','_initproc','_source_pthread_status','_pthread_functions','_raphael_cpu_stage','_raphael_cpu_registered','_raphael_cpu_intid','_raphael_cpu_physical_timer','_raphael_cpu_last_irq','_raphael_cpu_timer_irqs','_raphael_cpu_ipi_irqs','_raphael_cpu_eois','_raphael_cpu_dist_pa','_raphael_cpu_redist_pa','_raphael_cpu_frequency','_num_kt_sizeclass','_kt_zone_cfg','_g_crypto_funcs','_crypto_init','_source_corecrypto14_status','_gIOPlatformUUIDAndSerialDone','_armdt_platform_configured','_armdt_platform_child_count','_armdt_platform_cpu_count','_armdt_platform_bus_count','_armdt_platform_defaults_count','_armdt_platform_nvram_proxy','_armdt_platform_device_count','_native_virtio_ready','_native_virtio_read_requests','_native_virtio_read_failures','_native_virtio_sectors','_native_virtio_mmio_physical','_native_virtio_first_sector_sha256','_native_apfs_load_status','_native_apfs_registered','_native_apfs_vfsops','_native_owner_root_accepted','_native_owner_root_apple_autherr','_native_owner_root_decision','_native_owner_root_readonly','_native_owner_root_mount_device','_native_owner_root_selected_device','_native_virtio_verified_blocks','_native_virtio_integrity_failures','_native_virtio_manifest_ready','_native_owner_data_status','_native_owner_data_stage','_native_owner_data_source_lookup','_native_owner_data_target_lookup','_native_owner_data_readonly','_native_owner_data_device','_native_owner_data_seed_size','_raphael_data_seed_status','_raphael_data_seed_entries','_raphael_data_seed_index','_raphael_data_seed_written','_raphael_data_seed_readback']):data_symbols[parts[2]]=int(parts[0],16)
  qargs=['qemu-system-aarch64','-machine',machine,'-cpu','cortex-a57','-m',str(a.memory_mb),'-nographic','-monitor','none','-no-reboot','-net','none',
   '-gdb','unix:'+str(sock)+',server=on,wait=off',
   *(['-qmp','unix:'+str(qmp_sock)+',server=on,wait=off'] if a.gop else []),
   '-drive','if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/AAVMF/AAVMF_CODE.fd',
   '-drive','if=pflash,format=raw,unit=1,file='+str(out/'vars.fd'),
   '-drive','if=none,id=esp,format=raw,readonly=on,file=fat:'+str(esp),'-device','virtio-blk-device,drive=esp',*display_arguments,*disk_arguments]
  commands.append(qargs);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  with (out/'serial.log').open('xb') as log:
   proc=subprocess.Popen(qargs,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=a.keep_paused)
   deadline=time.monotonic()+40;gate=None;layout=None
   while time.monotonic()<deadline and proc.poll() is None:
    raw=(out/'serial.log').read_text(errors='replace')
    gate=re.search(r'NATIVE_XNU_GATE ([0-9a-fA-F]+)',raw)
    layout=re.search(r'DARWINBOOT: ARM64 va=0x([0-9a-fA-F]+) pa=0x([0-9a-fA-F]+) args=0x([0-9a-fA-F]+) entry=0x([0-9a-fA-F]+) owned=0x([0-9a-fA-F]+)',raw)
    if gate and layout:break
    time.sleep(.1)
   assert gate and layout,'Native loader did not reach allocation/exit gate'
   cpu=re.search(r'NATIVE_XNU_CPU frequency=([0-9]+) affinity=([0-9a-fA-F]+)',raw);assert cpu and int(cpu[1])==62500000 and int(cpu[2],16)&0xffffff==0
   report['cpu_entry_observation']=dict(counter_frequency=int(cpu[1]),mpidr=int(cpu[2],16),source='same-run EL1 MRS in NativeXnuFixture; ADT values cross-checked')
   video=re.search(r'DARWINBOOT: video base=0x([0-9a-fA-F]+) display=([0-9]+) row=([0-9]+) width=([0-9]+) height=([0-9]+) depth=([0-9]+)',raw)
   if video:report['firmware_boot_video']=dict(zip(['base','display','row_bytes','width','height','depth'],[int(video[1],16),*[int(v) for v in video.groups()[1:]]]))
   if a.gop:
    assert video and report['firmware_boot_video']['base'] and report['firmware_boot_video']['width'] and report['firmware_boot_video']['depth']==32,'Requested ramfb did not provide usable real GOP'
   va,pa,args,entry,window=[int(x,16) for x in layout.groups()]
   assert window==a.kernel_window_mb*1048576 and entry==pa+inspection['entry_virtual_address']-va and pa&0x1fffff==va&0x1fffff
   spec=dict(gate=int(gate[1],16),virtual_base=va,physical_base=pa,args=args,entry=entry,window=window,milestones=symbols,data_symbols=data_symbols,
    stop_at=('_raphael_display_frame_checkpoint' if a.stop_at=='display_frame' else '_raphael_display_checkpoint' if a.stop_at=='display' else '_platform_configure_return' if a.stop_at=='platform_configured' else '_raphael_cpu_start_return' if a.stop_at=='cpu_ready' else '_raphael_irq_return' if a.stop_at=='timer_irq' else '_IOFindBSDRoot' if a.stop_at=='find_root' else '_native_virtio_read_checkpoint' if a.stop_at=='block_read' else '_vfs_mountroot' if a.stop_at=='mount_root' else '_load_init_program' if a.stop_at=='load_init' else '_unix_syscall' if a.stop_at=='user_syscall' else '_original_launchd_main_completed' if a.stop_at=='launchd_main' else '_raphael_data_seed_checkpoint' if a.stop_at=='data_seed' else '_launchd_runtime_sample_complete' if a.stop_at=='launchd_runtime' else '_'+a.stop_at),segments=segments,socket=str(sock),output=str(out/'debugger-observation.json'),register_log=str(out/'registers.log'))
   if a.capture_data_after:spec['capture_data_after']=a.capture_data_after
   if a.progress_seconds:spec['progress_request']=str(out/'continue-after-snapshot.request')
   if scratch_data:spec['expected_data_seed']=dict(entries=scratch_data['entries'],bytes=scratch_data['seed_bytes'],image_bytes=scratch_data['bytes'],sparse=a.sparse_data)
   if a.user_abi:
    abi=json.loads(a.user_abi.read_text());assert abi['passed'] and abi['candidate_sha256']==report['kernel_sha256']
    spec['user_abi']=abi;spec['user_syscall_count']=a.user_syscalls;spec['runtime_observation']=a.stop_at in ('launchd_runtime','display_frame')
    if a.runtime_process:spec['runtime_process']=a.runtime_process
   if a.main_program:
    program=a.main_program.read_bytes();assert struct.unpack_from('<I',program)[0]==0xfeedfacf
    at=32;main_entries=[]
    for _ in range(struct.unpack_from('<I',program,16)[0]):
     cmd,size=struct.unpack_from('<2I',program,at);assert size>=8 and at+size<=len(program)
     if cmd==0x80000028:main_entries.append(struct.unpack_from('<Q',program,at+8)[0])
     at+=size
    assert len(main_entries)==1;main_offset=main_entries[0]
    spec['original_main']=dict(path=str(a.main_program),bytes=len(program),sha256=sha(program),header=program[:32].hex(),entry_offset=main_offset,entry_bytes=program[main_offset:main_offset+16].hex())
   if a.runtime_main_program:
    program=a.runtime_main_program.read_bytes();assert struct.unpack_from('<I',program)[0]==0xfeedfacf
    at=32;entries=[]
    for _ in range(struct.unpack_from('<I',program,16)[0]):
     cmd,size=struct.unpack_from('<2I',program,at);assert size>=8 and at+size<=len(program)
     if cmd==0x80000028:entries.append(struct.unpack_from('<Q',program,at+8)[0])
     at+=size
    assert len(entries)==1
    offset=entries[0];spec['runtime_main']=dict(comm=a.runtime_main_program.name,header=program[:32].hex(),entry_offset=offset,entry_bytes=program[offset:offset+16].hex(),sha256=sha(program))
   if system_disks:
    import hashlib
    os_path=ROOT/os_disk['path']
    with os_path.open('rb') as stream:first_sector=stream.read(512)
    spec['expected_os_block']=dict(sectors=os_disk['bytes']//512,first_sector_sha256=hashlib.sha256(first_sector).hexdigest())
   if a.capture_memory:
    capture=json.loads(a.capture_memory.read_text())
    assert capture['candidate_sha256']==report['kernel_sha256']
    for block in capture['memory']:
     address,size=block['address'],block['bytes']
     assert 0<size<=65536 and any(seg['virtual_address']<=address and address+size<=seg['virtual_address']+seg['virtual_bytes'] for seg in inspection['segments'])
    spec['capture_memory']=capture['memory']
   (out/'debugger-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
   gdbscript=out/'debug.gdb';gdbscript.write_text('python\nSPEC='+repr(str(out/'debugger-spec.json'))+'\nexec(compile(open('+repr(str(out/'observer.py'))+').read(),"observer.py","exec"))\nend\nquit\n')
   with (out/'gdb.log').open('xb') as debuglog:
    debugargs=['gdb-multiarch','--quiet','--nx','--batch','-x',str(gdbscript)]
    commands.append(debugargs);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    debugproc=subprocess.Popen(debugargs,stdout=debuglog,stderr=subprocess.STDOUT)
    try:
     deadline=time.monotonic()+a.observe_seconds
     while debugproc.poll() is None:
      remaining=deadline-time.monotonic()
      if remaining<=0:raise subprocess.TimeoutExpired(debugargs,a.observe_seconds)
      try:debugproc.wait(timeout=min(remaining,a.progress_seconds or remaining))
      except subprocess.TimeoutExpired:
       if time.monotonic()>=deadline:raise
       Path(spec['progress_request']).write_text('Read-only QEMU process snapshot; continue afterwards\n')
       debugproc.send_signal(signal.SIGINT)
    except subprocess.TimeoutExpired:
     report['debugger_timeout']=True
     debugproc.send_signal(signal.SIGINT)
     try:debugproc.wait(timeout=5)
     except subprocess.TimeoutExpired:
      report['debugger_capture_timeout']=True;debugproc.kill();debugproc.wait()
    report['debugger_returncode']=debugproc.returncode
   if (out/'debugger-observation.json').exists():
    observed=json.loads((out/'debugger-observation.json').read_text());report['debugger']=observed
    if observed.get('failure'):report['failure']='Observer: '+observed['failure']
    if 'interrupted_stop' in observed:
     functions=sorted((int(p[0],16),p[2]) for line in nm.splitlines() if len(p:=line.split())==3 and any(seg['virtual_address']<=int(p[0],16)<seg['virtual_address']+seg['file_bytes'] for seg in segments if seg['name']=='__TEXT_EXEC'))
     addresses=[value for value,name in functions]
     def symbolize(address):
      index=bisect.bisect_right(addresses,address)-1
      if index<0:return dict(address=address,symbol=None)
      value,name=functions[index];return dict(address=address,symbol=name,offset=address-value)
     interrupted=observed['interrupted_stop']
     report['interrupted_cpu_symbols']=[symbolize(interrupted[key]) for key in ['pc','lr']]
     report['interrupted_cpu_symbols'] += [symbolize(frame['return_address']) for frame in interrupted.get('frames',[])]
    if a.kalloc_zones is not None and 'kalloc_policy' in observed:assert observed['kalloc_policy']['budget']==a.kalloc_zones
    report['xnu_entry_verified']=observed.get('native_instruction_executed',False) and observed.get('loaded_file_bytes_match',False)
    report['xnu_arm_init_verified']=observed.get('arm_init_reached',False)
   post=report.get('debugger',{}).get('source_crypto_post',{})
   provider=report.get('debugger',{}).get('source_crypto_provider',{})
   report['default_source_crypto_post_and_registration_verified']=bool(post.get('mode')==0 and post.get('returned') and post.get('status')==0 and report.get('debugger',{}).get('source_crypto_start_status')==0 and provider.get('initialized'))
   if report.get('debugger') and not report['debugger'].get('target_reached'):
    report['target_failure']=report['debugger'].get('panic_format','Recorded target was not reached')
   report['dt_platform_configure_verified']=bool(report.get('debugger',{}).get('platform_configure',{}).get('returned_true'))
   report['independent_cpu_start_verified']=bool(report.get('debugger',{}).get('cpu_start',{}).get('returned_true'))
   cpu_state=report.get('debugger',{}).get('cpu_state',{})
   report['independent_cpu_timer_irq_verified']=bool(cpu_state.get('stage')==5 and cpu_state.get('timer_irqs',0)>0 and cpu_state.get('eois',0)>=cpu_state.get('timer_irqs',0))
   root=report.get('debugger',{}).get('owner_root',{})
   report['owner_root_authenticated']=bool(root.get('accepted')==1 and root.get('decision')==1 and root.get('readonly')==1 and root.get('mount_device')==root.get('selected_device'))
   report['init_program_loader_reached']='_load_init_program' in report.get('debugger',{}).get('reached_symbols',[])
   report['pid1_el0_syscall_verified']=bool(report.get('debugger',{}).get('pid1_el0_syscall_verified'))
   report['bounded_launchd_runtime_observed']=bool(report.get('debugger',{}).get('runtime_sample_completed'))
   report['requested_user_process_executed']=bool(report.get('debugger',{}).get('runtime_process_executed'))
   report['emulator_data_seed_verified']=bool(report.get('debugger',{}).get('data_seed_verified'))
   report['original_launchd_main_executed']=bool(report.get('debugger',{}).get('original_launchd_main_executed'))
   report['bsd_init_reached']='_bsd_init' in report.get('debugger',{}).get('reached_symbols',[])
   report['layout']=spec
  if a.gop and qmp_sock.exists() and proc.poll() is None:
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
    client.settimeout(5);client.connect(str(qmp_sock));stream=client.makefile('rwb',buffering=0)
    greeting=json.loads(stream.readline());assert 'QMP' in greeting
    def qmp(execute,arguments=None):
     stream.write((json.dumps(dict(execute=execute,**({'arguments':arguments} if arguments else {})))+'\r\n').encode())
     while True:
      answer=json.loads(stream.readline())
      if 'error' in answer:raise RuntimeError(answer['error'])
      if 'return' in answer:return answer['return']
    qmp('qmp_capabilities')
    if a.keep_paused:
     qmp('stop');status=qmp('query-status');assert status['running'] is False
     report['paused_emulator']=dict(pid=proc.pid,gdb_socket=str(sock),qmp_socket=str(qmp_sock),status=status,scope='Isolated QEMU held stopped for explicit continuation; guest state and RAM disk retained')
    screen=out/'qemu-screen.png'
    qmp('screendump',{'filename':str(screen),'format':'png'})
    report['qemu_scanout_capture']=dict(path=str(screen.relative_to(ROOT)),bytes=screen.stat().st_size,sha256=sha(screen.read_bytes()),desktop_verified=False)
  after={str(p.relative_to(esp)):sha(p.read_bytes()) for p in esp.rglob('*') if p.is_file()}
  report['esp_unchanged']=before==after;assert before==after
  assert sha((out/'native-kernel.macho').read_bytes())==report['kernel_sha256']
  report['passed']=bool(report['xnu_entry_verified'] and report['xnu_arm_init_verified'] and report['debugger'].get('target_reached') and report['debugger'].get('completed') and not report.get('failure'))
  if a.stop_at=='display_frame':
   state=report.get('debugger',{}).get('display_state',{})
   report['original_swap_memory_presentation_verified']=bool(state.get('_raphael_display_frames',0)>0 and state.get('_raphael_display_retired',0)>0 and state.get('_raphael_display_transfer_status')==0 and state.get('_raphael_display_guard')==0)
   report['desktop_verified']=False # Frame origin and continuous updates require separate evidence.
   report['passed']=report['passed'] and report['original_swap_memory_presentation_verified']
  if a.stop_at=='display':
   state=report.get('debugger',{}).get('display_state',{})
   report['display_service_publication_verified']=bool(state.get('_raphael_display_stage')==8 and state.get('_raphael_display_base') and state.get('_raphael_display_width') and state.get('_raphael_display_meta_status')==0 and state.get('_raphael_display_guard')==0)
   report['passed']=report['passed'] and report['display_service_publication_verified']
 except Exception as error:
  import traceback
  report['failure']=type(error).__name__+': '+str(error);(out/'exception.txt').write_text(traceback.format_exc())
 finally:
  if proc and proc.poll() is None and not report.get('paused_emulator'):
   proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
  if not report.get('paused_emulator'):
   if sock.exists():sock.unlink()
   if qmp_sock.exists():qmp_sock.unlink()
  report['qemu_returncode']=proc.returncode if proc else None
  report['limits']=['QEMU/AAVMF only; no handset execution','Debugger observes only the recorded native startup checkpoints',
   'Each report qualifies only its explicit target; no handset, desktop or complete kernel boot claim']
  report['evidence_files']=[dict(path=str(p.relative_to(out)),sha256=sha(p.read_bytes())) for p in [out/'debugger-observation.json',out/'serial.log',out/'gdb.log',out/'registers.log',out/'commands.json',out/'kernel-inspection.json'] if p.exists()]
  prefix='desktop-xnu-qemu-' if a.os_profile else 'native-xnu-qemu-'
  for dest in [out/'report.json',ROOT/'UniXNU-raphael/evidence'/(prefix+out.name.split('-')[0]+'.json'),ROOT/'UniXNU-raphael/evidence'/(prefix+a.stop_at+'.json')]:dest.write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({k:report.get(k) for k in ['passed','artifact_directory','failure','xnu_entry_verified','xnu_arm_init_verified','handset_executed']},indent=2))
 if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
