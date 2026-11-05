#!/usr/bin/env python3
"""Isolate ABL expanded-initrd placement while retaining the original kernel."""
import argparse,datetime as dt,json,struct,subprocess,tempfile,uuid
from pathlib import Path
from entry_probe import ROOT,run,image_parameters,compile_probe,instrument,sha
from build_sec_dxe import build_fixture
from android_return import capsule
from private_android_image import read_boot,repack

def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path);p.add_argument('--qemu-report',type=Path);a=p.parse_args();qemu=a.collection is None
 parent=ROOT/('artifacts/initrd-geometry-qemu' if qemu else 'evidence/private/entry-probe-build');parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 if qemu:
  # Existing independent entry fixture supplies full architectural and FDT checks.
  from validate_entry_probe import SOURCE,LIBFDT
  fixtures=ROOT/'scripts/fixtures';inputs=[fixtures/'entry_probe_kernel.S',fixtures/'initrd_geometry_kernel.c',SOURCE/'Runtime.c']+[LIBFDT/(n+'.c') for n in ['fdt','fdt_ro','fdt_rw','fdt_wip']]
  objects=[]
  for i,source in enumerate(inputs):
   obj=out/('fixture-'+str(i)+'.o');run(out,['aarch64-linux-gnu-gcc','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-fpie','-fvisibility=hidden','-mgeneral-regs-only','-mstrict-align','-ffunction-sections','-fdata-sections','-I'+str(LIBFDT),'-c',source,'-o',obj]);objects.append(obj)
  run(out,['aarch64-linux-gnu-gcc','-nostdlib','-static','-no-pie','-Wl,--build-id=none,--gc-sections,-T,'+str(fixtures/'entry_probe_kernel.ld'),'-o',out/'fixture.elf',*objects]);run(out,['aarch64-linux-gnu-objcopy','-O','binary',out/'fixture.elf',out/'fixture.Image']);original=(out/'fixture.Image').read_bytes();rd=b'R'*12345+b'Z'*(16*1048576);original_rd=12345;identifier='qemu-entry-probe-fixture'
 else:
  assert a.qemu_report;qp=a.qemu_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['geometry_verified']
  for item in q['probe_inputs']['inputs']:assert sha((ROOT/item['file']).read_bytes())==item['sha256']
  boot=read_boot(a.collection.resolve());original=boot['image'];rd,policy,cap=capsule(original,boot['ramdisk'],image_parameters(original),1);original_rd=len(boot['ramdisk']);identifier='raphael-initrd-geometry-'+uuid.uuid4().hex
 params=image_parameters(original);probe=compile_probe(out,params,identifier,main_source=ROOT/'scripts/fixtures/initrd_geometry_probe.c',extra_defines=['-DPROBE_EXPANDED_RAMDISK_BYTES='+str(len(rd)),'-DPROBE_ORIGINAL_RAMDISK_BYTES='+str(original_rd)])
 image=instrument(original,probe,params);(out/'instrumented.Image').write_bytes(image);(out/'expanded-ramdisk.bin').write_bytes(rd);inputs=json.loads((out/'probe-inputs.json').read_text())
 report=dict(passed=False,identifier=identifier,parameters=params,probe_inputs=inputs,initrd_geometry_probe=True,expanded_ramdisk_bytes=len(rd),original_ramdisk_bytes=original_rd,handset_executed=False,uefi_executed=False)
 if qemu:
  # GDB captures the added wire at receiver entry, before fixture changes registers.
  command=['qemu-system-aarch64','-machine','virt,virtualization=off','-cpu','cortex-a76','-m','512M','-nographic','-no-reboot','-semihosting-config','enable=on,target=native','-kernel',str(out/'instrumented.Image'),'-initrd',str(out/'expanded-ramdisk.bin'),'-append','fixture_cookie=unchanged']
  result=subprocess.run(command,capture_output=True,timeout=15);log=result.stdout+result.stderr;(out/'serial.log').write_bytes(log)
  # Receiver extension below prints/validates wire while retaining entry assertions.
  report.update(passed=result.returncode==0 and b'ENTRY_PROBE_FIXTURE_OK' in log and b'INITRD_GEOMETRY_OK' in log and b'FAIL ' not in log,geometry_verified=b'INITRD_GEOMETRY_OK' in log,command=command)
 else:
  packed=repack(boot,image,ramdisk=rd);(out/'boot-entry-probe.img').write_bytes(packed)
  report.update(passed=True,source_sha256=sha(boot['raw']),image_sha256=sha(packed),image_bytes=len(packed),extended_arm64_image_bytes=len(image),qemu_evidence=str(qp.relative_to(ROOT)),qemu_evidence_sha256=sha(qp.read_bytes()),unchanged_dtbs=boot['dtbs'])
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report.get(k) for k in ['passed','geometry_verified','image_sha256']},indent=2));assert report['passed']
if __name__=='__main__':main()
