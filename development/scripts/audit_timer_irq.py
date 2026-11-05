#!/usr/bin/env python3
"""Audit the bounded SPx IRQ assembly and fixed primary IAR/EOIR encodings."""
import argparse,json,re,struct,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from timer_irq import verify_result_storage

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['timer_irq_test'] and not q['timer_route_fault_test']
 assert q['executions']['normal']['timer_irq']['single_irq_handler_verified']
 for i in q['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
 obj=qp.parent/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/TimerIrq.obj'
 dis=subprocess.check_output(['llvm-objdump','-d',str(obj)],text=True);handler=dis.split('<RaphaelTimerIrqHandler>:',1)[1]
 assert not re.search(r'\b(?:bl|blr)\s',dis)
 assert not re.search(r'\b[wx](?:[0-7]|18|19|2[0-9]|30)\b',handler)
 assert len(re.findall(r'\bmsr\s+DAIFClr, #0x2',dis))==1 and len(re.findall(r'\bmsr\s+DAIFSet, #0x2',dis))==1
 assert 'msr\tDAIF,' not in dis and not re.search(r'ICC_(?:DIR|IGRPEN|CTLR).*?,',dis)
 pairs=re.findall(r'\b(stp|ldp)\s+(x\d+), (x\d+), \[sp(?:, #(0x[0-9a-f]+))?\]',handler)
 expected=[('x'+str(n),'x'+str(n+1),offset) for n,offset in zip(range(8,18,2),[0,16,32,48,64])]
 for op in ['stp','ldp']:assert [(x,y,int(off,0) if off else 0) for name,x,y,off in pairs if name==op]==expected
 assert len(re.findall(r'\bsub\s+sp, sp, #0x50',handler))==len(re.findall(r'\badd\s+sp, sp, #0x50',handler))==1
 assert len(re.findall(r'\bmrs\s+x10, ICC_IAR1_EL1',handler))==len(re.findall(r'\bmsr\s+ICC_EOIR1_EL1, x10',handler))==1
 assert handler.index('msr\tCNTP_CTL_EL0, x12')<handler.index('msr\tICC_EOIR1_EL1, x10')
 assert 'mrs\tx12, CNTP_CTL_EL0' in handler and 'msr\tSPSR_EL1, x11' in handler
 repo=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0';name='arch/arm64/include/asm/sysreg.h'
 raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+name]);text=raw.decode();encodings={}
 asm_lines=[];opcodes=[]
 for op,reg,index in [('mrs','ICC_IAR1_EL1',10),('msr','ICC_EOIR1_EL1',10)]:
  pattern=r'(?m)^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s+'+op+(r'\s+x10, '+reg if op=='mrs' else r'\s+'+reg+r', x10')
  found=re.findall(pattern,dis);assert len(found)==1
  m=re.search(r'#define SYS_'+reg+r'\s+sys_reg\((\d+), (\d+), (\d+), (\d+), (\d+)\)',text);assert m
  fields=list(map(int,m.groups()));word=(0xd5200000 if op=='mrs' else 0xd5000000)|sum(v<<s for v,s in zip(fields,[19,16,12,8,5]))|index
  assert word==int(found[0],16);opcodes.append(word)
  encodings[reg]=dict(fields=fields,opcode=hex(word),line=text[:m.start()].count('\n')+1)
  asm_lines.append(op+' '+('x10, '+reg if op=='mrs' else reg+', x10'))
 asm=qp.parent/'irq-independent.S';asm.write_text('.text\n'+'\n'.join(asm_lines)+'\n')
 subprocess.run(['aarch64-linux-gnu-as','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
 subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.text',str(asm.with_suffix('.o')),str(asm.with_suffix('.bin'))],check=True,capture_output=True)
 assert list(struct.unpack('<2I',asm.with_suffix('.bin').read_bytes()))==opcodes
 spec=ROOT/'sources/arm-reference/IHI0069C_GIC_architecture_spec.pdf';text=spec.with_suffix('.txt').read_text();sections={}
 for marker,anchors in [
  ('8.2.14 ICC_IAR1_EL1',['acknowledge for the interrupt','1020, 1021, or 1023']),
  ('8.2.10 ICC_EOIR1_EL1',['priority','EOImode']),
  ('4.3.3 Interrupt deactivation',[])]:
  if marker not in text and marker.startswith('4.3.3'):continue
  at=text.index(marker);chunk=text[at:at+18000]
  for anchor in anchors:assert anchor in chunk,(marker,anchor)
  sections[marker]=int(re.findall(r'=== PDF PAGE (\d+) ===',text[:at])[-1])
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/TimerIrq.S';s=source.read_text()
 assert 'tb' in s and 'icc_ctlr_el1' in s and 'RaphaelIrqWindowOpen' in s and 'RaphaelIrqWindowClose' in s
 vector=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/SecEntry.S';v=vector.read_text().split('RaphaelVectors:',1)[1].split('RaphaelReadException:',1)[0]
 assert v.count('b RaphaelTimerIrqHandler')==1 and v.index('b RaphaelTimerIrqHandler')>v.rindex('b RaphaelReadException')
 paths=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelTimerIrq.h',source.with_name('TimerRoute.c'),source.with_name('Sec.c'),vector]
 result=dict(passed=True,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],
  decoder_sha256=sha((ROOT/'scripts/timer_irq.py').read_bytes()),compiled_object_sha256=sha(obj.read_bytes()),stack_spill_bytes=80,saved_scratch_registers=list(range(8,18)),callee_saved_registers_modified=False,
  active_pointer_and_instruction_range_required=True,current_el_spx_irq_only=True,eoi_mode_zero_only=True,one_iar_and_one_eoir_site=True,special_ids_not_eoid=True,source_mask_readback_before_eoi=True,
  independent_gnu_assembler_matched=True,primary_encoding_source=dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,sha256=sha(raw),encodings=encodings),
  specification=dict(document='ARM IHI0069C (ID070116)',sha256=sha(spec.read_bytes()),sections_pdf_page=sections),result_storage=verify_result_storage(qp.parent),handset_executed=False,
  limitations=['One pending target PPI only, not general TimerArch','Unknown/spurious IDs make the window fail; valid acknowledged IDs are EOId to avoid leaking active state','IRQs outside the guarded leaf use fatal diagnostic return','EL2/EL3 trap recovery is not guaranteed'])
 (ROOT/'UniXNU-raphael/evidence/timer-irq-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print('bounded SPx handler, preserved scratch frame, source-before-EOI and fixed IAR/EOIR encodings verified')
if __name__=='__main__':main()
