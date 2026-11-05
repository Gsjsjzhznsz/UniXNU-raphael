#!/usr/bin/env python3
"""Reversible cached pages with independent DRAM receiver and precise exception recovery."""
import datetime as dt,json,tempfile,struct,argparse,re
from pathlib import Path
from entry_probe import ROOT,align,image_parameters,sha
from build_sec_dxe import build_fixture,build_firmware,run_case
from qemu_arch_probe import generate_resources
from inspect_device import read_fdt,registers
from inspect_diagnostic_fd import inspect_fd
from ram_read_probe import encode,policy,verify_result_storage

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=int,choices=[2,3],required=True);ap.add_argument('--pages',type=int,choices=[1,8,256,4096,16384,65536],required=True);a=ap.parse_args();stage=a.stage
 parent=ROOT/'artifacts/sec-dxe-qemu';parent.mkdir(exist_ok=True,parents=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 resources=generate_resources(out,memory_mb=1024)
 defines=['-DEXPECT_RAM_READ=1','-DEXPECT_RAM_MAPPED=1','-DEXPECT_RAM_CACHE_WRITE='+str(a.pages)]
 original=build_fixture(out,expected_stage=stage,extra_defines=defines);p=image_parameters(original)
 tree=read_fdt((out/'qemu-virt.dtb').read_bytes());memory=next(n for n in tree.walk() if n.properties.get('device_type')==b'memory\0');banks=registers(memory);assert len(banks)==1
 ram_start,ram_bytes=banks[0];assert ram_bytes==1024*1024*1024
 base=ram_start+p['text_offset'];extent=base+align(p['image_size'],65536);fd=extent+65536;stack=fd+0x300000;arena=stack+0x40000;fdt=arena+0x1000000;end=fdt+0x110000
 values=dict(ImageBase=base,ImageSize=p['image_size'],OriginalEntry=p['entry'],OriginalInstruction=p['instruction'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=0x300000,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=0x1000000,FdtBase=fdt,FdtSize=0x110000,ContextBase=extent)
 # Emulator design derived from its generated RAM bank; never a phone address.
 candidate=align(ram_start+ram_bytes//2,0x200000)
 raw_policy=encode(candidate,[(base,end-base)])
 probe=dict(policy=policy(raw_policy),source='QEMU generated RAM bank midpoint',sources=[dict(path=str((out/'qemu-virt.dtb').relative_to(ROOT)),sha256=sha((out/'qemu-virt.dtb').read_bytes()))],handset_parameters=False)
 raw,report=build_firmware(out,values,'qemu-sec-dxe-v1','QEMU only',stop_stage=stage,ram_probe=probe,ram_mapped_probe=True,ram_cache_write_pages=a.pages)
 inspection=inspect_fd(raw,fd);(out/'fd-inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
 from ram_mapped_probe import decode
 from ram_cache_write import decode as decode_cache,verify_storage
 storage=verify_storage(out)
 result=run_case(out,original,raw,p,values,dtb=out/'qemu-virt.dtb',expected_stage=stage,ram_probe=probe,memory_mb=1024,ram_seed_pages=a.pages)
 wire=re.search(r'RAM_MAPPED_WIRE ([0-9a-f]+)',(out/'serial.log').read_text());assert wire
 result['ram_mapped']=decode(bytes.fromhex(wire[1]),result['ram_read'],stage)
 wire=re.search(r'RAM_CACHE_WIRE ([0-9a-f]+)',(out/'serial.log').read_text());assert wire
 result['ram_cache']=decode_cache(bytes.fromhex(wire[1]),result['ram_read'],result['ram_mapped'],probe['policy'],a.pages,stage)
 from audit_ram_read import inspect_load
 load=inspect_load(out,function='ReadMappedRam64');fault=None
 if stage==3:
  fault_out=out/'load-site-udf';fault_out.mkdir()
  fault_original=build_fixture(fault_out,expected_stage=stage,expect_fault=3,extra_defines=defines)
  assert image_parameters(fault_original)==p
  patched=bytearray(raw);struct.pack_into('<I',patched,load['load_fd_offset'],0)
  inspect_fd(bytes(patched),fd)
  fault=run_case(fault_out,fault_original,patched,p,values,dtb=out/'qemu-virt.dtb',expected_stage=stage,ram_probe=probe,memory_mb=1024,ram_seed_pages=a.pages)
  fault.update(load_fd_offset=load['load_fd_offset'],patched_opcode=0,patched_firmware_sha256=sha(patched),real_data_abort=False)
 write_fault=None
 if stage==3:
  fault_out=out/'partial-write-udf';fault_out.mkdir()
  fault_original=build_fixture(fault_out,expected_stage=stage,expect_fault=4,extra_defines=defines)
  assert image_parameters(fault_original)==p
  directory=out/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
  mp=(directory/'RaphaelSec.dll.map').read_text();rva=int(re.search(r'(?m)^([0-9a-f]+)\s+.*\sRaphaelRamWriteCheckpoint$',mp)[1],16)
  fdinfo=json.loads((out/'fd-inspection.json').read_text());sec=next(f for f in fdinfo['files'] if f['guid'].startswith('6d94ae07-'));section=next(s for s in sec['sections'] if 'pe' in s);offset=section['offset']+4+rva
  assert struct.unpack_from('<I',raw,offset)[0]==0xd503201f
  damaged=bytearray(raw);struct.pack_into('<I',damaged,offset,0)
  inspect_fd(bytes(damaged),fd)
  write_fault=run_case(fault_out,fault_original,damaged,p,values,dtb=out/'qemu-virt.dtb',expected_stage=stage,ram_probe=probe,memory_mb=1024,ram_seed_pages=a.pages)
  serial=(fault_out/'serial.log').read_text()
  wire=re.search(r'RAM_MAPPED_WIRE ([0-9a-f]+)',serial);assert wire
  mapped=decode(bytes.fromhex(wire[1]),write_fault['ram_read'],stage)
  wire=re.search(r'RAM_CACHE_WIRE ([0-9a-f]+)',serial);assert wire
  write_fault['ram_cache']=decode_cache(bytes.fromhex(wire[1]),write_fault['ram_read'],mapped,probe['policy'],a.pages,stage,fault=True)
  write_fault.update(checkpoint_fd_offset=offset,patched_opcode=0,patched_firmware_sha256=sha(damaged),real_data_abort=False)
 report.update(qemu_passed=result['passed'] and (fault is None or fault['passed']) and (write_fault is None or write_fault['passed']),structure_checked=True,executions=dict(normal=result,**({'load_site_udf':fault,'partial_write_udf':write_fault} if fault else {})),ram_cache_storage=storage,layout=values,ram_probe=probe,firmware_sha256=sha(raw),qemu_resources=resources)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print('QEMU passed:',result['passed'],'checks:',result['pass_count'])
 if not report['qemu_passed']:print((out/'serial.log').read_text());print((fault_out/'serial.log').read_text() if fault else 'stage2');raise SystemExit(1)
 if write_fault:print('Cached partial-write UDF:',write_fault['passed'],'checks:',write_fault['pass_count'])
 if fault:print('Mapped load-site fatal UDF return:',fault['passed'],'checks:',fault['pass_count'])
if __name__=='__main__':main()
