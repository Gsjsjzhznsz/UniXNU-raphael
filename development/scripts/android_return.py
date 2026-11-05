#!/usr/bin/env python3
"""Pinned-Mu LZMA return capsule. No network or handset operations."""
import json,lzma,struct,subprocess,zlib
from pathlib import Path
from entry_probe import ROOT,SOURCE,run,sha
RETURN=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/AndroidReturn'
SDK=ROOT/'sources/mu_basecore/MdeModulePkg/Library/LzmaCustomDecompressLib/Sdk/C'
POLICY_GUID='26118CDD-1846-4DDC-B626-B6D6428845E2'
STUB_GUID='075868E9-FBBA-4BAE-92C3-AD2103C264BD'
HOB_GUID='F7C01DAB-24F3-451B-88F1-E01653802B77'
TAIL=0x40000

def capsule(kernel,ramdisk,parameters,conduit):
 compressed=lzma.compress(kernel,format=lzma.FORMAT_ALONE,preset=1)
 assert lzma.decompress(compressed,format=lzma.FORMAT_ALONE)==kernel
 offset=(len(ramdisk)+7)&~7
 expanded=ramdisk+bytes(offset-len(ramdisk))+compressed
 words=[int.from_bytes(b'RPHRET01','little'),1,len(ramdisk),len(compressed),len(kernel),parameters['image_size'],parameters['entry'],parameters['instruction'],zlib.crc32(compressed),zlib.crc32(kernel),zlib.crc32(ramdisk),conduit]
 return expanded,struct.pack('<12Q',*words),dict(format='LZMA_ALONE',preset=1,kernel_sha256=sha(kernel),kernel_bytes=len(kernel),declared_image_bytes=parameters['image_size'],ramdisk_sha256=sha(ramdisk),ramdisk_bytes=len(ramdisk),compressed_sha256=sha(compressed),compressed_bytes=len(compressed),expanded_ramdisk_sha256=sha(expanded),policy_words=words)

def build_stub(out,qemu=False):
 # SDK must match the fixed Mu commit byte for byte.
 revision=subprocess.check_output(['git','-C',str(ROOT/'sources/mu_basecore'),'rev-parse','HEAD'],text=True).strip()
 assert revision=='cfb93724a06ff86ff5ba971413368a7809ee42a5'
 for path in [SDK/'LzmaDec.c',SDK/'LzmaDec.h',SDK/'7zTypes.h',SDK/'Precomp.h',SDK/'Compiler.h']:
  assert path.read_bytes()==subprocess.check_output(['git','-C',str(ROOT/'sources/mu_basecore'),'show',revision+':'+str(path.relative_to(ROOT/'sources/mu_basecore'))])
 flags=['-O2','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector','-fpie','-fvisibility=hidden','-mgeneral-regs-only','-mstrict-align','-ffunction-sections','-fdata-sections','-I'+str(RETURN),'-I'+str(SDK),'-DRPH_RETURN_QEMU='+str(int(qemu))]
 sources=[RETURN/'ReturnStub.S',RETURN/'ReturnStub.c',SDK/'LzmaDec.c',SOURCE/'Runtime.c']
 objects=[]
 for i,source in enumerate(sources):
  obj=out/('return-'+str(i)+'.o');run(out,['aarch64-linux-gnu-gcc',*flags,'-c',source,'-o',obj]);objects.append(obj)
 elf=out/'android-return.elf'
 run(out,['aarch64-linux-gnu-gcc','-nostdlib','-static','-no-pie','-Wl,--build-id=none,--gc-sections,-T,'+str(RETURN/'ReturnStub.ld'),'-o',elf,*objects])
 symbols=run(out,['aarch64-linux-gnu-nm','-u',elf]);assert not symbols.strip(),symbols
 relocs=run(out,['aarch64-linux-gnu-readelf','-rW',elf]);assert b'There are no relocations' in relocs
 sections=run(out,['aarch64-linux-gnu-readelf','-SW',elf]);assert b'.bss' not in sections,sections
 run(out,['aarch64-linux-gnu-objcopy','-O','binary',elf,out/'android-return.bin'])
 raw=(out/'android-return.bin').read_bytes();assert 0<len(raw)<=0x20000
 dis=run(out,['aarch64-linux-gnu-objdump','-d',elf]);(out/'android-return-disassembly.txt').write_bytes(dis)
 if not qemu:assert b'hvc' not in dis and b'hlt' not in dis and b'smc' in dis
 inputs=[]
 for source in [*sources,RETURN/'Wire.h',RETURN/'ReturnStub.ld',Path(__file__)]:
  target=out/'snapshot'/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());inputs.append(dict(path=str(source.relative_to(ROOT)),sha256=sha(source.read_bytes())))
 return raw,dict(bytes=len(raw),sha256=sha(raw),mu_revision=revision,no_undefined_symbols=True,no_relocations=True,no_bss=True,qemu_hvc_enabled=qemu,source_inputs=inputs)
