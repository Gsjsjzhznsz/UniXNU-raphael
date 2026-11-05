#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Reproduce the real UFS Completion merge fault under AArch64 MMU-off, then fix it."""
import datetime,json,subprocess
from pathlib import Path
from entry_probe import ROOT

def main():
 out=ROOT/'artifacts/ufs-alignment'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 out.mkdir(parents=True,exist_ok=False);print(out,flush=True)
 report=dict(passed=False,handset_executed=False,mmu_cache_off=True,explicit_sctlr_alignment_check=True,device_memory_model_claimed=False,cases=[])
 try:
  (out/'fixture.ld').write_text('ENTRY(_start)\nSECTIONS { . = 0x40080000; .text : { *(.text.entry) *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
  sources=[ROOT/'scripts/fixtures/raphael_ufs_alignment.S',ROOT/'scripts/fixtures/raphael_ufs_alignment.cpp']
  for strict in (False,True):
   name='strict' if strict else 'negative-default';elf=out/(name+'.elf')
   cmd=['clang++','--target=aarch64-none-elf','-fuse-ld=lld','-Oz','-flto','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-exceptions','-fno-rtti','-mgeneral-regs-only','-nostdlib','-Wl,--build-id=none,-T,'+str(out/'fixture.ld'),'-I'+str(ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform')]
   if strict:cmd+=['-mstrict-align']
   cmd += [str(s) for s in sources]+['-o',str(elf)]
   built=subprocess.run(cmd,capture_output=True);(out/(name+'-build.log')).write_bytes(built.stdout+built.stderr);assert built.returncode==0,built.stderr.decode()
   disasm=subprocess.check_output(['llvm-objdump','-d','--no-show-raw-insn',str(elf)]);(out/(name+'-disasm.txt')).write_bytes(disasm)
   run=['qemu-system-aarch64','-machine','virt,virtualization=off','-cpu','cortex-a76','-m','128M','-nodefaults','-nographic','-no-reboot','-semihosting-config','enable=on,target=native','-kernel',str(elf)]
   result=subprocess.run(run,capture_output=True,timeout=10);log=result.stdout+result.stderr;(out/(name+'.log')).write_bytes(log)
   passed=result.returncode==(0 if strict else 33) and (b'UFS_ALIGNMENT_OK' if strict else b'UFS_ALIGNMENT_FAULT') in log
   report['cases'].append(dict(strict=strict,passed=passed,compile=cmd,command=run,returncode=result.returncode,log=log.decode(errors='replace')))
   assert passed,log.decode(errors='replace')
  report['passed']=True
 except Exception as e:report['failure']=type(e).__name__+': '+str(e)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
