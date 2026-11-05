#!/usr/bin/env python3
"""Audit two PPI write-one offsets, architecture RWP and XIP result storage."""
import argparse,ast,json,re,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from ppi_probe import resource,verify_result_storage

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['ppi_enable_probe'] and not q['icc_fault_test'] and not q['timer_source_test']
 assert q['executions']['normal']['ppi']['passed']
 assert q['ppi_decoder_sha256']==sha((ROOT/'scripts/ppi_probe.py').read_bytes())
 for i in q['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
 repo=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0';name='include/linux/irqchip/arm-gic-v3.h'
 raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+name]);header=raw.decode()
 def macro(n):
  m=re.search(r'^#define\s+'+re.escape(n)+r'\s+([^\n]+)',header,re.M);assert m,n
  s=m[1].split('/*')[0].strip();s=re.sub(r'\b(0x[0-9a-fA-F]+|[0-9]+)[uUlL]+\b',r'\1',s)
  s=re.sub(r'\b[A-Za-z_][A-Za-z_0-9]*\b',lambda m:str(macro(m[0])),s);e=ast.parse(s,mode='eval')
  assert all(isinstance(n,(ast.Expression,ast.Constant,ast.BinOp,ast.LShift,ast.BitOr,ast.Add)) for n in ast.walk(e))
  return eval(compile(e,'primary-macro','eval'),{'__builtins__':{}})
 expected={'GICR_CTLR':0,'GICR_ISENABLER0':0x100,'GICR_ICENABLER0':0x180,'GICR_ISPENDR0':0x200,'GICR_ISACTIVER0':0x300,'GICD_CTLR_RWP':1<<31}
 constants={n:macro(n) for n in expected};assert constants==expected
 spec=ROOT/'sources/arm-reference/IHI0069C_GIC_architecture_spec.pdf';text=spec.with_suffix('.txt').read_text()
 sections={}
 for marker,anchors in [
  ('8.10 The GIC Redistri butor register map',['two 64KB frames','1. RD_base','2. SGI_base']),
  ('8.9.4 GICD_CTLR',['EnableGrp1A, bit [1]','ARE_NS, bit [4]']),
  ('8.11.2 GICR_CTLR',['RWP, bit [3]','GICR_ICENABLER0']),
  ('8.11.4 GICR_ICENABLER0',['When GICD_CTLR.DS == 0','RAZ/WI']),
  ('8.11.15 GICR_ISENABLER0',['When GICD_CTLR.DS == 0','After a write of 1 to this bit, a subsequent read of this bit returns 1.'])]:
  at=text.index(marker);chunk=text[at:at+18000 if '8.9.' in marker else at+10000]
  for anchor in anchors:assert anchor in chunk,(marker,anchor)
  sections[marker]=int(re.findall(r'=== PDF PAGE (\d+) ===',text[:at])[-1])
 contract_path=ROOT/'UniXNU-raphael/evidence/interrupt-resource-contract.json';contract=json.loads(contract_path.read_text());assert contract['passed']
 blob=(ROOT/contract['collection']/'live.dtb').read_bytes();assert sha(blob)==contract['live_fdt_sha256']
 intid,flags=resource(blob);assert intid==contract['facts']['timer_interrupts'][1]['intid'] and flags==contract['facts']['timer_interrupts'][1]['specifier'][2]
 legacy_path='drivers/irqchip/irq-gic-v3.c';legacy_raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+legacy_path]);legacy=legacy_raw.decode()
 assert 'while (readl_relaxed_no_log(base + GICD_CTLR) & GICD_CTLR_RWP)' in legacy
 assert 'gic_do_wait_for_rwp(gic_data_rdist_rd_base());' in legacy
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/PpiProbe.c';s=source.read_text()
 assert re.findall(r'\bWrite\(([^;]+)\);',s)==['O->SgiBase+0x100,(UINT32)O->Mask,C','O->SgiBase+0x180,(UINT32)O->Mask,C']
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPpiProbe.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/Sec.c']
 result=dict(passed=True,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],
  decoder_sha256=sha((ROOT/'scripts/ppi_probe.py').read_bytes()),primary_header=dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,sha256=sha(raw),constants=constants),
  specification=dict(document='ARM IHI0069C (ID070116)',sha256=sha(spec.read_bytes()),sections_pdf_page=sections,redistributor_rwp_bit=3),
  legacy_vendor_wait_uses_distributor_rwp_bit31=True,legacy_wait_copied=False,legacy_wait_source=dict(path=legacy_path,revision=rev,sha256=sha(legacy_raw)),
  resource_contract=str(contract_path.relative_to(ROOT)),resource_contract_sha256=sha(contract_path.read_bytes()),timer_intid=intid,timer_flags=flags,
  permitted_write_offsets=[0x100,0x180],write_one_mask_only=True,distributor_written=False,group_or_priority_written=False,irq_unmasked=False,
  result_storage=verify_result_storage(qp.parent),handset_executed=False,limitations=['PPI enable permission only; no IRQ routing or delivery','Write-ignored result is preserved as status3, never a writable permission claim'])
 (ROOT/'UniXNU-raphael/evidence/ppi-probe-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PPI write offsets, Arm RWP.bit3, local resource and materialized SEC result verified')
if __name__=='__main__':main()
