#!/usr/bin/env python3
"""Bind read-only enable map to fixed Arm/MiCode sources and materialized FD."""
import argparse,json,re,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from gic_enable_map import verify_result_storage

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['gic_enable_map'] and not q['icc_fault_test'] and not q['timer_source_test'] and not q['ppi_enable_probe']
 assert q['executions']['normal']['gic_enable_map']['passed']
 assert q['gic_enable_map_decoder_sha256']==sha((ROOT/'scripts/gic_enable_map.py').read_bytes())
 for i in q['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
 repo=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0';name='include/linux/irqchip/arm-gic-v3.h'
 raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+name]);header=raw.decode()
 expected={'GICD_CTLR':0,'GICD_TYPER':4,'GICD_ISENABLER':0x100,'GICR_CTLR':0,'GICR_ISENABLER0':0x100}
 constants={}
 def macro(n):
  m=re.search(r'^#define\s+'+re.escape(n)+r'\s+(0x[0-9a-fA-F]+|[0-9]+|[A-Za-z_][A-Za-z_0-9]*)\b',header,re.M);assert m,n
  value=macro(m[1])[0] if m[1][0].isalpha() else int(m[1],0)
  return value,header[:m.start()].count('\n')+1
 for n,v in expected.items():
  value,line=macro(n);assert value==v;constants[n]=dict(value=value,line=line)
 spec=ROOT/'sources/arm-reference/IHI0069C_GIC_architecture_spec.pdf';text=spec.with_suffix('.txt').read_text();sections={}
 for marker,anchors in [
  ('8.9.24 GICD_TYPER',['ITLinesNumber, bits [4:0]','32(N+1)-1','1020-1023','Bits [15:11]','Bits [9:8]']),
  ('8.9.15 GICD_ISENABLER',['RAZ/WI','GICD_CTLR.DS==0']),
  ('8.11.2 GICR_CTLR',['Enable_LPIs, bit [0]']),
  ('8.11.15 GICR_ISENABLER0',['RAZ/WI','GICD_CTLR.DS == 0']),
  ('8.10 The GIC Redistri butor register map',['two 64KB frames','1. RD_base','2. SGI_base'])]:
  at=text.index(marker);chunk=text[at:at+16000]
  for anchor in anchors:assert anchor in chunk,(marker,anchor)
  sections[marker]=int(re.findall(r'=== PDF PAGE (\d+) ===',text[:at])[-1])
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/GicEnableMap.c';s=source.read_text()
 assert not re.search(r'\b(?:Write|AsmWrite|MmioWrite)\w*\s*\(',s)
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelGicEnableMap.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/Sec.c']
 result=dict(passed=True,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],
  decoder_sha256=sha((ROOT/'scripts/gic_enable_map.py').read_bytes()),primary_header=dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,sha256=sha(raw),constants=constants),
  specification=dict(document='ARM IHI0069C (ID070116)',sha256=sha(spec.read_bytes()),sections_pdf_page=sections),
  spi_enable_bank_first=1,spi_enable_bank_count='GICD_TYPER.ITLinesNumber',redistributor_count='validated dynamic GIC snapshot',passes=2,
  mmio_write_callback=False,atomic_snapshot=False,secure_interrupts_observed=False,complete_gic_ownership_proven=False,
  result_storage=verify_result_storage(qp.parent),handset_executed=False,
  limitations=['Only reviewed standard GICv3 INTID space','Nonsecure RAZ/WI values do not describe secure interrupts','Two matching passes are observations, not an atomic ownership transfer'])
 (ROOT/'UniXNU-raphael/evidence/gic-enable-map-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print('Arm/MiCode enable ranges, read-only interface and materialized SEC result verified')
if __name__=='__main__':main()
