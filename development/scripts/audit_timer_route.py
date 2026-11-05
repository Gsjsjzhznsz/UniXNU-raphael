#!/usr/bin/env python3
"""Audit the single ICC group write and source withdrawal/restore contract."""
import argparse,json,re,struct,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from timer_route import verify_result_storage

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);p.add_argument('--fault-qemu-report',required=True,type=Path);a=p.parse_args()
 qp,fp=a.qemu_report.resolve(),a.fault_qemu_report.resolve();q,f=[json.loads(p.read_text()) for p in [qp,fp]]
 assert q['qemu_passed'] and f['qemu_passed'] and q['timer_route_test'] and f['timer_route_test']
 assert not q['timer_route_fault_test'] and f['timer_route_fault_test'] and q['source_inputs']==f['source_inputs']
 assert q['executions']['normal']['timer_route']['physical_timer_route_observed']
 fault=f['executions']['normal']['timer_route'];assert fault['injected_undefined_recovered'] and fault['registers_restored'] and not fault['physical_timer_route_observed']
 for item in q['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
 assert q['timer_route_decoder_sha256']==f['timer_route_decoder_sha256']==sha((ROOT/'scripts/timer_route.py').read_bytes())
 obj=qp.parent/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RouteAccess.obj'
 dis=subprocess.check_output(['llvm-objdump','-d',str(obj)],text=True)
 writes=re.findall(r'(?m)^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s+msr\s+(\w+), x0',dis)
 assert len(writes)==1 and writes[0][1].lower()=='icc_igrpen1_el1'
 assert not re.search(r'\b(?:mrs|sys|dc|ic)\b',dis,re.I)
 assert not re.search(r'\b(?:x(?:19|2[0-9]|30)|sp)\b',dis)
 assert not re.search(r'\b(?:icc_iar|icc_eoir|icc_dir|daifclr)',dis,re.I)
 symbols=subprocess.check_output(['llvm-nm',str(obj)],text=True)
 def symbol(name):
  m=re.search(r'(?m)^([0-9a-f]+) [A-Za-z] '+name+r'$',symbols);assert m,name;return int(m[1],16)
 assert symbol('RaphaelRouteAccessSitesEnd')-symbol('RaphaelRouteAccessSites')==32
 asm=qp.parent/'route-msr-independent.S';asm.write_text('.text\nmsr icc_igrpen1_el1,x0\n')
 subprocess.run(['aarch64-linux-gnu-as','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
 subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.text',str(asm.with_suffix('.o')),str(asm.with_suffix('.bin'))],check=True,capture_output=True)
 opcode=struct.unpack('<I',asm.with_suffix('.bin').read_bytes())[0];assert opcode==int(writes[0][0],16)
 repo=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0';name='arch/arm64/include/asm/sysreg.h'
 raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+name]);header=raw.decode()
 m=re.search(r'#define SYS_ICC_IGRPEN1_EL1\s+sys_reg\((\d+), (\d+), (\d+), (\d+), (\d+)\)',header);assert m
 values=list(map(int,m.groups()));assert 0xd5000000|sum(v<<s for v,s in zip(values,[19,16,12,8,5]))==opcode
 spec=ROOT/'sources/arm-reference/IHI0069C_GIC_architecture_spec.pdf';text=spec.with_suffix('.txt').read_text();sections={}
 for marker,anchors in [
  ('8.9.4 GICD_CTLR',['EnableGrp1A, bit [1]','ARE_NS, bit [4]']),
  ('8.2.12 ICC_HPPIR1_EL1',['highest priority pending Group 1 interrupt','1020, 1021, or 1023']),
  ('8.2.16 ICC_IGRPEN1_EL1',['Enable, bit [0]']),
  ('8.11.2 GICR_CTLR',['RWP, bit [3]'])]:
  at=text.index(marker);chunk=text[at:at+18000]
  for anchor in anchors:assert anchor in chunk,(marker,anchor)
  sections[marker]=int(re.findall(r'=== PDF PAGE (\d+) ===',text[:at])[-1])
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/TimerRoute.c';s=source.read_text()
 assert re.findall(r'Mw\(O,W,C,([^;]+)\);',s)==['O->SgiBase+0x100,(UINT32)Mask','G->GicD,(UINT32)(O->OriginalDist|2)','G->GicD,(UINT32)O->OriginalDist','O->SgiBase+0x180,(UINT32)Mask']
 assert not re.search(r'\b(?:AsmEnableInterrupts|ArmEnableInterrupts|asm|__asm__)\b',s)
 files=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelTimerRoute.h',source.with_name('TimerRouteAdapter.c'),source.with_name('RouteAccess.S'),source.with_name('SecEntry.S'),source.with_name('Sec.c'),source.with_name('PpiProbe.c')]
 for entry in [q,f]:
  setup=entry['executions']['normal']['qemu_entry_setup'];assert setup['pmr']==0xf0 and setup['waker']==0
  assert sha((ROOT/setup['source']).read_bytes())==setup['source_sha256']
 result=dict(passed=True,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),fault_qemu_report=str(fp.relative_to(ROOT)),fault_qemu_report_sha256=sha(fp.read_bytes()),
  source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in files],decoder_sha256=sha((ROOT/'scripts/timer_route.py').read_bytes()),
  compiled_route_access_sha256=sha(obj.read_bytes()),actual_msr_registers=[r for word,r in writes],recovery_site_count=2,
  independent_gnu_assembler_matched=True,primary_encoding_source=dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,sha256=sha(raw),fields=values,line=header[:m.start()].count('\n')+1,opcode=hex(opcode)),
  specification=dict(document='ARM IHI0069C (ID070116)',sha256=sha(spec.read_bytes()),sections_pdf_page=sections),
  distributor_write_mask=2,local_enable_write_one=True,cpu_irq_mask_preserved=True,acknowledge_register_access=False,priority_group_trigger_written=False,
  result_storage=verify_result_storage(qp.parent),qemu_entry_setup_is_not_handset_firmware=True,handset_executed=False,
  limitations=['HPPIR plus timer/pending source observation only, no IRQ handler','Two matching nonsecure enable passes are not atomic ownership proof','Recovery at EL1 cannot recover an exception taken to EL2 or EL3','Intentional EC0 UDF recovery tested; no actual hardware EC0x18 trap claim'])
 (ROOT/'UniXNU-raphael/evidence/timer-route-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print('single ICC group MSR, two exact recovery sites, HPPIR-only observation and FD storage verified')
if __name__=='__main__':main()
