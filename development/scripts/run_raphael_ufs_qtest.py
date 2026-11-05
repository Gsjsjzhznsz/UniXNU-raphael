#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Exercise the actual read-only transport against QEMU 8.2 PCI UFS, no phone IO."""
import argparse,datetime,json,subprocess,sys,time,os
from pathlib import Path
from entry_probe import ROOT
from qemu_arch_probe import generate_resources
from inspect_device import read_fdt,registers

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--diagnostic-writes',action='store_true',help='Allow only synthetic model media writes, then restart and read back; never phone IO')
 parser.add_argument('--qemu',default='qemu-system-aarch64',help='Explicit independent UFS model binary')
 args=parser.parse_args()
 out=ROOT/'artifacts/ufs-qtest'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False);print(out,flush=True)
 report=dict(passed=False,handset_executed=False,handset_dma_verified=False,source_hardware_constants_imported=False)
 model_source=ROOT/'artifacts/host-qemu-ufs/source.json'
 if Path(args.qemu).resolve()==ROOT/'artifacts/host-qemu-ufs/build/qemu-system-aarch64' and model_source.exists():report['isolated_model_source']=json.loads(model_source.read_text())
 process=None;sock=Path('/tmp')/('rufs-'+str(os.getpid())+'.sock')
 try:
  generate_resources(out,memory_mb=256,qemu=args.qemu);root=read_fdt((out/'qemu-virt.dtb').read_bytes())
  pci=next(n for n in root.walk() if b'pci-host-ecam-generic' in n.properties.get('compatible',b'').split(b'\0'));[(ecam,ecam_bytes)]=registers(pci);assert ecam_bytes>=1<<20
  cells=pci.cells('ranges');assert len(cells)%7==0
  windows=[cells[i:i+7] for i in range(0,len(cells),7) if cells[i]>>24==2];assert len(windows)==1
  w=windows[0];child=w[1]<<32|w[2];parent=w[3]<<32|w[4];size=w[5]<<32|w[6];assert child==parent and size>0x200000
  bar=(parent+0x100000+0xffff)&~0xffff
  ramnode=next(n for n in root.walk() if n.properties.get('device_type')==b'memory\0');[(ram,ram_bytes)]=registers(ramnode);assert ram_bytes>=0x20000
  fixture=ROOT/'scripts/fixtures/raphael_ufs_qtest.cpp';header=ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelUfsTransport.h'
  (out/fixture.name).write_bytes(fixture.read_bytes());(out/header.name).write_bytes(header.read_bytes())
  mapping=ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelReadOnlyExtents.h';(out/mapping.name).write_bytes(mapping.read_bytes())
  policy=ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelUfsWritePolicy.h';(out/policy.name).write_bytes(policy.read_bytes())
  compile=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform'),str(fixture),'-o',str(out/'ufs-qtest')]
  built=subprocess.run(compile,capture_output=True);(out/'build.log').write_bytes(built.stdout+built.stderr);assert built.returncode==0,built.stderr.decode()
  disk=out/'synthetic.raw'
  with disk.open('xb') as f:f.truncate(8*1024*1024);f.seek(7*4096);f.write(bytes((i*29+7)&255 for i in range(4096)))
  command=[args.qemu,'-machine','virt,gic-version=3,virtualization=off','-cpu','cortex-a76','-m','256M','-nodefaults','-nographic','-S','-qtest','unix:'+str(sock)+',server=on,wait=off','-device','ufs,id=ufs0,addr=01.0','-drive','if=none,id=ufsDisk,file='+str(disk)+',format=raw,readonly='+('off' if args.diagnostic_writes else 'on'),'-device','ufs-lu,bus=ufs0,drive=ufsDisk,lun=0']
  report.update(qemu_command=command,compile_command=compile,resources=dict(ecam=ecam,bar=bar,ram=ram,source='same emulator generated FDT'),qemu_version=subprocess.check_output([args.qemu,'--version'],text=True).splitlines()[0])
  with (out/'qemu.log').open('wb') as log:
   process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
   for _ in range(100):
    if sock.exists():break
    assert process.poll() is None,'QEMU exited before qtest socket';time.sleep(.05)
   assert sock.exists()
   result=subprocess.run([str(out/'ufs-qtest'),str(sock),hex(ecam),hex(bar),hex(ram)]+(['--diagnostic-writes'] if args.diagnostic_writes else []),capture_output=True,timeout=30)
   (out/'execution.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,(result.stdout+result.stderr).decode()
   assert b'RAPHAEL_UFS_QTEST_OK' in result.stdout
   count=sum(line.startswith(b'PASS ') for line in result.stdout.splitlines())
   if args.diagnostic_writes:
    process.terminate();process.wait(timeout=5);sock.unlink(missing_ok=True)
    raw=disk.read_bytes();pattern=bytes((i*13+0x63)&255 for i in range(4096));expected=bytearray(8*1024*1024);expected[7*4096:8*4096]=bytes((i*29+7)&255 for i in range(4096));expected[11*4096:12*4096]=pattern
    assert raw==expected,'Model media changed outside declared diagnostic allocation'
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    for _ in range(100):
     if sock.exists():break
     assert process.poll() is None;time.sleep(.05)
    again=subprocess.run([str(out/'ufs-qtest'),str(sock),hex(ecam),hex(bar),hex(ram),'--verify-persisted-write'],capture_output=True,timeout=30)
    (out/'restart-execution.log').write_bytes(again.stdout+again.stderr);assert again.returncode==0,(again.stdout+again.stderr).decode()
    report.update(diagnostic_write_verified=True,synchronous_flush_verified=True,media_unchanged_outside_write_window=True,persisted_after_process_restart=True,restart_case_count=sum(line.startswith(b'PASS ') for line in again.stdout.splitlines()),handset_persistence_verified=False)
   report.update(passed=True,case_count=count,real_model_dma_read_verified=True,known_block_bytes_verified=4096)
 except Exception as e:
  report['failure']=type(e).__name__+': '+str(e)
 finally:
  if process is not None:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait()
  sock.unlink(missing_ok=True)
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
