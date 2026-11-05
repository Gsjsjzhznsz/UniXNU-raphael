#!/usr/bin/env python3
"""Build private standalone watchdog qualification from fresh device resources."""
import argparse,datetime as dt,json,re,struct,tempfile
from pathlib import Path
from entry_probe import ROOT,SOURCE,LIBFDT,run,image_parameters,sha
from inspect_device import read_fdt,registers,physical
from private_android_image import read_boot,repack

def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);p.add_argument('--live-fdt',type=Path,required=True);a=p.parse_args()
 t=read_fdt(a.live_fdt.read_bytes());nodes=[n for n in t.walk() if b'qcom,msm-watchdog\0' in n.properties.get('compatible',b'')];assert len(nodes)==1
 n=nodes[0];[(base,size)]=registers(n);base=physical(n.parent,base,size);assert base%4096==0 and size==4096
 ref=ROOT/'artifacts/watchdog-reference-20261029/watchdog_v2.c';text=ref.read_text()
 for name,off in [('RST',4),('EN',8),('STS',12),('BARK_TIME',16),('BITE_TIME',20)]:assert int(re.search(r'#define WDT0_'+name+r'\s+(0x[0-9A-Fa-f]+)',text)[1],16)==off
 hz=int(re.search(r'static long WDT_HZ = (\d+);',text)[1]);assert hz==32765
 source=ROOT/'sources/Xiaomi_Kernel_OpenSource/arch/arm64/boot/dts/qcom/sm8150.dtsi';assert 'reg = <'+hex(base)+' 0x1000>;' in source.read_text()
 parent=ROOT/'evidence/private/watchdog-build';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 (out/'watchdog-policy.h').write_text('#define WATCHDOG_BASE '+hex(base)+'UL\n#define WATCHDOG_HZ '+str(hz)+'U\n#define WATCHDOG_SECONDS 5U\n')
 sources=[ROOT/'scripts/fixtures/psci_reset_image.S',ROOT/'scripts/fixtures/watchdog_reset_image.c',SOURCE/'Runtime.c']+[LIBFDT/(n+'.c') for n in ['fdt','fdt_ro','fdt_addresses']]
 snapshot=out/'source-snapshot';snapshot.mkdir()
 for src in [*sources,ROOT/'scripts/fixtures/entry_probe_kernel.ld',Path(__file__)]: (snapshot/src.name).write_bytes(src.read_bytes())
 objects=[];flags=['-O2','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector','-fpie','-fvisibility=hidden','-mgeneral-regs-only','-mstrict-align','-ffunction-sections','-fdata-sections','-I'+str(LIBFDT),'-I'+str(out)]
 for i,src in enumerate(sources):
  obj=out/(str(i)+'.o');run(out,['aarch64-linux-gnu-gcc',*flags,'-c',src,'-o',obj]);objects.append(obj)
 run(out,['aarch64-linux-gnu-gcc','-nostdlib','-static','-no-pie','-Wl,--build-id=none,--gc-sections,-T,'+str(ROOT/'scripts/fixtures/entry_probe_kernel.ld'),'-o',out/'watchdog.elf',*objects])
 run(out,['aarch64-linux-gnu-objcopy','-O','binary',out/'watchdog.elf',out/'watchdog.raw']);raw=(out/'watchdog.raw').read_bytes();assert 64<len(raw)<=65536
 image=raw+bytes(65536-len(raw));image_parameters(image);(out/'watchdog.Image').write_bytes(image)
 dis=run(out,['aarch64-linux-gnu-objdump','-d',out/'watchdog.elf']);(out/'disassembly.txt').write_bytes(dis);assert b'hvc' not in dis and b'hlt' not in dis and b'smc' not in dis
 boot=read_boot(a.collection.resolve());packed=repack(boot,image);(out/'boot-watchdog.img').write_bytes(packed)
 report=dict(passed=True,handset_executed=False,hardware_reset_verified=False,base=base,bytes=size,register_source='MiCode 663db50e195a8a54c8565ac4ab0c6d9ba7d80db0 drivers/soc/qcom/watchdog_v2.c',live_fdt=str(a.live_fdt.resolve().relative_to(ROOT)),frequency=hz,frequency_source='driver default; actual watchdog clock not yet measured',bark_seconds=5,bite_seconds=6,software_fallback_seconds=None,no_cpu_reset_instruction=True,source_boot_sha256=sha(boot['raw']),image_sha256=sha(packed),image_bytes=len(packed),runtime_fdt_gated=True,used_flash_or_erase=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
