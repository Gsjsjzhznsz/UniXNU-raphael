#!/usr/bin/env python3
"""Real SEC dirty-page recovery; QEMU RAM is independently seeded and checked."""
import argparse,datetime as dt,json,tempfile,struct,re,subprocess
from pathlib import Path
from entry_probe import ROOT,align,image_parameters,sha
from build_sec_dxe import build_fixture,build_firmware,run_case
from qemu_arch_probe import generate_resources
from inspect_device import read_fdt,registers
from inspect_diagnostic_fd import inspect_fd
from ram_read_probe import encode,policy,verify_result_storage
from ram_write_probe import verify_storage

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--pages',type=int,choices=[1,8,256],default=1);a=parser.parse_args()
 parent=ROOT/'artifacts/sec-dxe-qemu';parent.mkdir(exist_ok=True,parents=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 resources=generate_resources(out,memory_mb=1024)
 defines=['-DEXPECT_RAM_READ=1','-DEXPECT_RAM_WRITE='+str(a.pages)]
 original=build_fixture(out,expected_stage=2,extra_defines=defines);p=image_parameters(original)
 tree=read_fdt((out/'qemu-virt.dtb').read_bytes());memory=next(n for n in tree.walk() if n.properties.get('device_type')==b'memory\0');banks=registers(memory);assert len(banks)==1
 ram_start,ram_bytes=banks[0];assert ram_bytes==1024*1024*1024
 base=ram_start+p['text_offset'];extent=base+align(p['image_size'],65536);fd=extent+65536;stack=fd+0x300000;arena=stack+0x40000;fdt=arena+0x1000000;end=fdt+0x110000
 values=dict(ImageBase=base,ImageSize=p['image_size'],OriginalEntry=p['entry'],OriginalInstruction=p['instruction'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=0x300000,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=0x1000000,FdtBase=fdt,FdtSize=0x110000,ContextBase=extent)
 candidate=align(ram_start+ram_bytes//2,0x200000)
 raw_policy=encode(candidate,[(base,end-base)])
 probe=dict(policy=policy(raw_policy),source='QEMU generated RAM bank midpoint',sources=[dict(path=str((out/'qemu-virt.dtb').relative_to(ROOT)),sha256=sha((out/'qemu-virt.dtb').read_bytes()))],handset_parameters=False)
 raw,report=build_firmware(out,values,'qemu-sec-dxe-v1','QEMU only',stop_stage=2,ram_probe=probe,ram_write_pages=a.pages)
 (out/'fd-inspection.json').write_text(json.dumps(inspect_fd(raw,fd),indent=2)+'\n')
 storage=verify_storage(out);read_storage=verify_result_storage(out)
 result=run_case(out,original,raw,p,values,dtb=out/'qemu-virt.dtb',expected_stage=2,ram_probe=probe,memory_mb=1024,ram_write_pages=a.pages)
 directory=out/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
 mp=(directory/'RaphaelSec.dll.map').read_text()
 rva=int(re.search(r'(?m)^([0-9a-f]+)\s+.*\sRaphaelRamWriteCheckpoint$',mp)[1],16)
 inspection=json.loads((out/'fd-inspection.json').read_text());sec=next(x for x in inspection['files'] if x['guid'].startswith('6d94ae07-'));section=next(s for s in sec['sections'] if 'pe' in s);offset=section['offset']+4+rva
 assert struct.unpack_from('<I',raw,offset)[0]==0xd503201f
 fault_out=out/'partial-write-udf';fault_out.mkdir()
 fault_original=build_fixture(fault_out,expected_stage=2,expect_fault=4,extra_defines=defines)
 assert image_parameters(fault_original)==p
 patched=bytearray(raw);struct.pack_into('<I',patched,offset,0);inspect_fd(bytes(patched),fd)
 fault=run_case(fault_out,fault_original,patched,p,values,dtb=out/'qemu-virt.dtb',expected_stage=2,ram_probe=probe,memory_mb=1024,ram_write_pages=a.pages,ram_write_fault=True)
 fault.update(checkpoint_fd_offset=offset,patched_opcode=0,patched_firmware_sha256=sha(patched),real_data_abort=False)
 from audit_ram_read import inspect_load
 load=inspect_load(out);load_out=out/'load-site-udf';load_out.mkdir()
 load_original=build_fixture(load_out,expected_stage=2,expect_fault=3,extra_defines=['-DEXPECT_RAM_READ=1'])
 assert image_parameters(load_original)==p
 damaged=bytearray(raw);struct.pack_into('<I',damaged,load['load_fd_offset'],0)
 load_fault=run_case(load_out,load_original,damaged,p,values,dtb=out/'qemu-virt.dtb',expected_stage=2,memory_mb=1024)
 load_fault.update(load_fd_offset=load['load_fd_offset'],patched_opcode=0,real_data_abort=False)
 report.update(qemu_passed=result['passed'] and fault['passed'] and load_fault['passed'],structure_checked=True,executions=dict(normal=result,partial_write_udf=fault,load_site_udf=load_fault),ram_write_storage=storage,ram_result_storage=read_storage,layout=values,ram_probe=probe,firmware_sha256=sha(raw),qemu_resources=resources)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print('QEMU:',result['passed'],result['pass_count'],'partial-write UDF:',fault['passed'],fault['pass_count'])
 if not report['qemu_passed']:print((out/'serial.log').read_text());print((fault_out/'serial.log').read_text());print((load_out/'serial.log').read_text());raise SystemExit(1)
if __name__=='__main__':main()
