#!/usr/bin/env python3
"""Real SEC and sparse read execution in a separately described 1GiB QEMU RAM."""
import datetime as dt,json,tempfile,struct
from pathlib import Path
from entry_probe import ROOT,align,image_parameters,sha
from build_sec_dxe import build_fixture,build_firmware,run_case
from qemu_arch_probe import generate_resources
from inspect_device import read_fdt,registers
from inspect_diagnostic_fd import inspect_fd
from ram_read_probe import encode,policy,verify_result_storage

def main():
 parent=ROOT/'artifacts/sec-dxe-qemu';parent.mkdir(exist_ok=True,parents=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 resources=generate_resources(out,memory_mb=1024)
 original=build_fixture(out,expected_stage=2,extra_defines=['-DEXPECT_RAM_READ=1']);p=image_parameters(original)
 tree=read_fdt((out/'qemu-virt.dtb').read_bytes());memory=next(n for n in tree.walk() if n.properties.get('device_type')==b'memory\0');banks=registers(memory);assert len(banks)==1
 ram_start,ram_bytes=banks[0];assert ram_bytes==1024*1024*1024
 base=ram_start+p['text_offset'];extent=base+align(p['image_size'],65536);fd=extent+65536;stack=fd+0x300000;arena=stack+0x40000;fdt=arena+0x1000000;end=fdt+0x110000
 values=dict(ImageBase=base,ImageSize=p['image_size'],OriginalEntry=p['entry'],OriginalInstruction=p['instruction'],ExtentBase=extent,ExtentEnd=end,FdBase=fd,FdSize=0x300000,StackBase=stack,StackSize=0x40000,ArenaBase=arena,ArenaSize=0x1000000,FdtBase=fdt,FdtSize=0x110000,ContextBase=extent)
 # Emulator design derived from its generated RAM bank; never a phone address.
 candidate=align(ram_start+ram_bytes//2,0x200000)
 raw_policy=encode(candidate,[(base,end-base)])
 probe=dict(policy=policy(raw_policy),source='QEMU generated RAM bank midpoint',sources=[dict(path=str((out/'qemu-virt.dtb').relative_to(ROOT)),sha256=sha((out/'qemu-virt.dtb').read_bytes()))],handset_parameters=False)
 raw,report=build_firmware(out,values,'qemu-sec-dxe-v1','QEMU only',stop_stage=2,ram_probe=probe)
 inspection=inspect_fd(raw,fd);(out/'fd-inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
 storage=verify_result_storage(out)
 result=run_case(out,original,raw,p,values,dtb=out/'qemu-virt.dtb',expected_stage=2,ram_probe=probe,memory_mb=1024)
 from audit_ram_read import inspect_load
 load=inspect_load(out);fault_out=out/'load-site-udf';fault_out.mkdir()
 fault_original=build_fixture(fault_out,expected_stage=2,expect_fault=3,extra_defines=['-DEXPECT_RAM_READ=1'])
 assert image_parameters(fault_original)==p
 patched=bytearray(raw);struct.pack_into('<I',patched,load['load_fd_offset'],0)
 inspect_fd(bytes(patched),fd)
 fault=run_case(fault_out,fault_original,patched,p,values,dtb=out/'qemu-virt.dtb',expected_stage=2,memory_mb=1024)
 fault.update(load_fd_offset=load['load_fd_offset'],patched_opcode=0,patched_firmware_sha256=sha(patched),real_data_abort=False)
 report.update(qemu_passed=result['passed'] and fault['passed'],structure_checked=True,executions=dict(normal=result,load_site_udf=fault),ram_result_storage=storage,layout=values,ram_probe=probe,firmware_sha256=sha(raw),qemu_resources=resources)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print('QEMU passed:',result['passed'],'checks:',result['pass_count'])
 if not report['qemu_passed']:print((out/'serial.log').read_text());print((fault_out/'serial.log').read_text());raise SystemExit(1)
 print('Load-site fatal UDF return:',fault['passed'],'checks:',fault['pass_count'])
if __name__=='__main__':main()
