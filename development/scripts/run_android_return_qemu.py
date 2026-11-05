#!/usr/bin/env python3
"""Own SEC/MMU/DXE -> high LZMA -> restored low receiver; no AAVMF."""
import argparse,datetime as dt,json,struct,subprocess,tempfile,time,re
from pathlib import Path
from entry_probe import ROOT,SOURCE,LIBFDT,run,sha,align,image_parameters
from build_psci_reset import compile_image
from build_sec_dxe import build_firmware
from android_return import build_stub,capsule
from inspect_diagnostic_fd import inspect_fd
from qemu_arch_probe import generate_resources
from inspect_device import read_fdt,registers
from kernel_window import BLOCK,WINDOW,check_log

def build_receiver(out,stage,ramdisk_bytes=12345,native_staging=False,native_fat_bytes=20*1048576):
 sources=[ROOT/'scripts/fixtures/entry_probe_kernel.S',ROOT/'scripts/fixtures/android_return_kernel.c',SOURCE/'Runtime.c']+[LIBFDT/(n+'.c') for n in ['fdt','fdt_ro']]
 flags=['-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-fpie','-fvisibility=hidden','-mgeneral-regs-only','-mstrict-align','-ffunction-sections','-fdata-sections','-I'+str(LIBFDT),'-DRETURN_KERNEL_BYTES='+str(46*1048576),'-DRETURN_IMAGE_BYTES='+str(54*1048576),'-DRETURN_STAGE='+str(stage),'-DRETURN_RAMDISK_BYTES='+str(ramdisk_bytes),'-DRETURN_NATIVE_STAGING='+str(int(native_staging)),'-DRETURN_NATIVE_FAT_BYTES='+str(native_fat_bytes)]
 objects=[]
 for i,source in enumerate(sources):
  obj=out/('receiver-'+str(i)+'.o');run(out,['aarch64-linux-gnu-gcc',*flags,'-c',source,'-o',obj]);objects.append(obj)
 run(out,['aarch64-linux-gnu-gcc','-nostdlib','-static','-no-pie','-Wl,--build-id=none,--gc-sections,-T,'+str(ROOT/'scripts/fixtures/entry_probe_kernel.ld'),'-o',out/'receiver.elf',*objects])
 run(out,['aarch64-linux-gnu-objcopy','-O','binary',out/'receiver.elf',out/'receiver.raw'])
 raw=(out/'receiver.raw').read_bytes();assert len(raw)<=65536
 image=bytearray(bytes((i^(i>>8))&255 for i in range(46*1048576)));image[:65536]=raw+bytes(65536-len(raw));struct.pack_into('<Q',image,16,54*1048576)
 return bytes(image)

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=int,choices=[3,6],default=3);a=p.parse_args()
 parent=ROOT/'artifacts/android-return-qemu';parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
 try:
  resources=generate_resources(out,memory_mb=1024);tree=read_fdt((out/'qemu-virt.dtb').read_bytes());bank=next(n for n in tree.walk() if n.properties.get('device_type')==b'memory\0');[(ram,ram_bytes)]=registers(bank)
  receiver=build_receiver(out,a.stage);parameters=image_parameters(receiver);low,reset_inputs=compile_image(out,True);lp=image_parameters(low);base=ram+lp['text_offset']
  extent=base+65536;fd=extent+65536;stack=fd+3*1048576;arena=max(stack+0x40000,align(base+parameters['image_size'],65536));fdt=arena+12*1048576;end=fdt+0x110000
  values=dict(ImageBase=base,ImageSize=len(low),OriginalEntry=lp['entry'],OriginalInstruction=lp['instruction'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=3*1048576,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=12*1048576,FdtBase=fdt,FdtSize=0x110000,ContextBase=extent)
  kw=dict(base=align(ram+ram_bytes//2,BLOCK),bytes=WINDOW+BLOCK,virtual_base=0xfffffff007004000,guards=[dict(base=base,bytes=end-base)],experimental_boot_grant=True,source='same-run QEMU FDT midpoint',handset_parameters=False)
  stub,stub_report=build_stub(out,qemu=True);rd,policy,cap=capsule(receiver,b'R'*12345,parameters,2);(out/'return-initrd').write_bytes(rd)
  raw,report=build_firmware(out,values,'qemu-android-return-v1','QEMU only',stop_stage=3 if a.stage==3 else 4,kernel_window=kw,android_return=dict(stub=stub,policy=policy,qemu=True))
  structure=inspect_fd(raw,fd);image=bytearray(low+bytes(end-base-len(low)));image[fd-base:fd-base+len(raw)]=raw;struct.pack_into('<I',image,0,0x14000000|((fd-base)//4));struct.pack_into('<Q',image,16,len(image));(out/'diagnostic.Image').write_bytes(image)
  command=['qemu-system-aarch64','-machine','virt,gic-version=3,virtualization=off','-cpu','cortex-a76','-m','1024M','-nographic','-no-reboot','-semihosting-config','enable=on,target=native','-kernel',str(out/'diagnostic.Image'),'-initrd',str(out/'return-initrd'),'-dtb',str(out/'qemu-virt.dtb')]
  start=time.monotonic();result=subprocess.run(command,capture_output=True,timeout=60);log=result.stdout+result.stderr;(out/'serial.log').write_bytes(log)
  passed=result.returncode==0 and b'ANDROID_RETURN_QEMU_OK' in log and b'FAIL ' not in log
  report.update(passed=passed,qemu_passed=passed,command=command,returncode=result.returncode,wall_seconds=time.monotonic()-start,stage=a.stage,layout=values,kernel_window=kw,return_stub=stub_report,capsule=cap,receiver_sha256=sha(receiver),reset_inputs=reset_inputs,firmware_sha256=sha(raw),image_sha256=sha(image),structure_checked=True,checks=log.decode(errors='replace').splitlines(),pass_count=sum(x.startswith(b'PASS ') for x in log.splitlines()),handset_executed=False)
  if passed and a.stage==6:report['allocation_verification']=check_log(log,kw)
  match=re.search(rb'ANDROID_RETURN_WIRE ([0-9a-f]+)',log)
  if match:report['return_wire']=list(struct.unpack('>10Q',bytes.fromhex(match[1].decode())))
  (out/'fd-inspection.json').write_text(json.dumps(structure,indent=2)+'\n')
 except Exception as e:
  report=dict(passed=False,failure=str(e),handset_executed=False);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');raise
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['passed','pass_count','stage','wall_seconds']},indent=2));assert passed,log[-9000:]
if __name__=='__main__':main()
