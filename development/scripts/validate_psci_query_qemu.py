#!/usr/bin/env python3
"""Execute the PSCI query probe and checked original-kernel continuation."""
import datetime as dt,json,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,SOURCE,LIBFDT,run,sha,image_parameters,compile_probe,instrument

def main():
 parent=ROOT/'artifacts/psci-query-qemu';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 flags=['-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-fpie','-fvisibility=hidden','-mgeneral-regs-only','-mstrict-align','-ffunction-sections','-fdata-sections','-I'+str(LIBFDT)]
 inputs=[ROOT/'scripts/fixtures/entry_probe_kernel.S',ROOT/'scripts/fixtures/psci_query_kernel.c',SOURCE/'Runtime.c']+[LIBFDT/(n+'.c') for n in ['fdt','fdt_ro','fdt_rw','fdt_wip']]
 objects=[]
 for i,source in enumerate(inputs):
  obj=out/('fixture-'+str(i)+'.o');run(out,['aarch64-linux-gnu-gcc',*flags,'-c',source,'-o',obj]);objects.append(obj)
 run(out,['aarch64-linux-gnu-gcc','-nostdlib','-static','-no-pie','-Wl,--build-id=none,--gc-sections,-T,'+str(ROOT/'scripts/fixtures/entry_probe_kernel.ld'),'-o',out/'fixture.elf',*objects])
 run(out,['aarch64-linux-gnu-objcopy','-O','binary',out/'fixture.elf',out/'fixture.Image'])
 original=(out/'fixture.Image').read_bytes();parameters=image_parameters(original)
 probe=compile_probe(out,parameters,'qemu-entry-probe-fixture',main_source=SOURCE/'PsciProbe.c',extra_defines=['-DALLOW_QEMU_HVC=1'])
 image=instrument(original,probe,parameters);(out/'probe.Image').write_bytes(image)
 command=['qemu-system-aarch64','-machine','virt,virtualization=off','-cpu','cortex-a76','-m','512M','-nographic','-no-reboot','-semihosting-config','enable=on,target=native','-kernel',str(out/'probe.Image'),'-append','fixture_cookie=unchanged']
 result=subprocess.run(command,capture_output=True,timeout=15);log=result.stdout+result.stderr;(out/'serial.log').write_bytes(log)
 report=dict(passed=result.returncode==0 and b'ENTRY_PROBE_FIXTURE_OK' in log and b'FAIL ' not in log and b'PASS PSCI FEATURES SYSTEM_RESET' in log,command=command,image_sha256=sha(image),probe_sha256=sha(probe),artifact_directory=str(out.relative_to(ROOT)),handset_executed=False,reset_executed=False,conduit='HVC from same-run emulator FDT; phone uses SMC only',checks=log.decode(errors='replace').splitlines())
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
