#!/usr/bin/env python3
"""Independent 64KiB Image, with query-gated PSCI reset recovery only."""
import argparse,datetime as dt,json,subprocess,tempfile,time
from pathlib import Path
from entry_probe import ROOT,SOURCE,LIBFDT,sha,run,image_parameters
from private_android_image import read_boot,repack

def compile_image(out,qemu):
 sources=[ROOT/'scripts/fixtures/psci_reset_image.S',ROOT/'scripts/fixtures/psci_reset_image.c',SOURCE/'Runtime.c']+[LIBFDT/(n+'.c') for n in ['fdt','fdt_ro']]
 flags=['-O2','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector','-fpie','-fvisibility=hidden','-mgeneral-regs-only','-mstrict-align','-ffunction-sections','-fdata-sections','-I'+str(LIBFDT),'-DQEMU_HVC_RESET='+str(int(qemu))]
 objects=[]
 for i,source in enumerate(sources):
  obj=out/('reset-'+str(i)+'.o');run(out,['aarch64-linux-gnu-gcc',*flags,'-c',source,'-o',obj]);objects.append(obj)
 linker=ROOT/'scripts/fixtures/entry_probe_kernel.ld'
 run(out,['aarch64-linux-gnu-gcc','-nostdlib','-static','-no-pie','-Wl,--build-id=none,--gc-sections,-T,'+str(linker),'-o',out/'reset.elf',*objects])
 run(out,['aarch64-linux-gnu-objcopy','-O','binary',out/'reset.elf',out/'reset.raw'])
 raw=(out/'reset.raw').read_bytes();assert 64<len(raw)<=65536;image=raw+bytes(65536-len(raw));image_parameters(image);(out/'reset.Image').write_bytes(image)
 dis=run(out,['aarch64-linux-gnu-objdump','-d',out/'reset.elf']);(out/'reset-disassembly.txt').write_bytes(dis)
 if not qemu:assert b'hvc' not in dis and b'hlt' not in dis and b'smc' in dis
 inputs=[]
 for source in [*sources,linker,Path(__file__)]:
  relative=source.relative_to(ROOT);raw=source.read_bytes();target=out/'snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);inputs.append(dict(path=str(relative),sha256=sha(raw)))
 return image,inputs

def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path);p.add_argument('--query-report',type=Path);a=p.parse_args()
 qemu=a.collection is None
 parent=ROOT/('artifacts/psci-reset-qemu' if qemu else 'evidence/private/psci-reset-build');parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 try:image,inputs=compile_image(out,qemu)
 except Exception as error:
  (out/"report.json").write_text(json.dumps(dict(passed=False,failure=str(error),handset_executed=False),indent=2)+"\n");raise
 report=dict(passed=False,artifact_directory=str(out.relative_to(ROOT)),source_inputs=inputs,standalone_image_sha256=sha(image),image_bytes=len(image),handset_executed=False,qemu_hvc_enabled=qemu,timeout_seconds=3,contains_original_android_kernel=False)
 if qemu:
  command=['qemu-system-aarch64','-machine','virt,virtualization=off','-cpu','cortex-a76','-m','512M','-nographic','-no-reboot','-semihosting-config','enable=on,target=native','-kernel',str(out/'reset.Image')]
  start=time.monotonic();result=subprocess.run(command,capture_output=True,timeout=12);log=result.stdout+result.stderr;(out/'serial.log').write_bytes(log)
  elapsed=time.monotonic()-start
  report.update(command=command,returncode=result.returncode,wall_seconds=elapsed,passed=result.returncode==0 and 2.8<=elapsed<10 and b'PSCI_SYSTEM_RESET_CALL' in log and b'RETURNED_UNEXPECTEDLY' not in log,reset_executed_in_qemu=True)
 else:
  assert a.query_report
  query=json.loads(a.query_report.read_text());assert query['passed'] and query['observation']['conduit']==1 and query['observation']['system_reset_feature']==0
  qemu_reports=sorted((ROOT/'artifacts/psci-reset-qemu').glob('*/report.json'));assert qemu_reports and json.loads(qemu_reports[-1].read_text())['passed']
  for item in inputs:
   if item['path'].endswith(('psci_reset_image.c','psci_reset_image.S')):assert sha((qemu_reports[-1].parent/'snapshot'/item['path']).read_bytes())==item['sha256']
  boot=read_boot(a.collection.resolve());packed=repack(boot,image);(out/'boot-psci-reset.img').write_bytes(packed)
  report.update(passed=True,source_boot_sha256=sha(boot['raw']),packed_image_sha256=sha(packed),unchanged_dtbs=boot['dtbs'],unchanged_ramdisk_sha256=sha(boot['ramdisk']),query_report=str(a.query_report.resolve().relative_to(ROOT)),query_report_sha256=sha(a.query_report.read_bytes()),qemu_report=str(qemu_reports[-1].relative_to(ROOT)),qemu_report_sha256=sha(qemu_reports[-1].read_bytes()))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(json.dumps({k:report.get(k) for k in ['passed','wall_seconds','standalone_image_sha256','packed_image_sha256']},indent=2));assert report['passed']
if __name__=='__main__':main()
