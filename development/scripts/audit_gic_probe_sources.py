#!/usr/bin/env python3
"""Pin read-only GIC offsets and topology semantics to primary kernel source."""
import ast
import re
import json
import subprocess
from entry_probe import ROOT, sha
from gic_probe import recipe, SGI_OFFSETS


def main():
    repo=ROOT/'sources/Xiaomi_Kernel_OpenSource'
    rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
    specs={
      'include/linux/irqchip/arm-gic-v3.h':[
        'GICD_CTLR','GICD_TYPER','GICD_IIDR','GICD_PIDR2','GIC_PIDR2_ARCH_MASK',
        'GIC_PIDR2_ARCH_GICv3','GIC_PIDR2_ARCH_GICv4','GICR_CTLR','GICR_IIDR',
        'GICR_TYPER','GICR_WAKER','GICR_TYPER_VLPIS','GICR_TYPER_LAST','GIC_V3_REDIST_SIZE',
        'GICR_IGROUPR0','GICR_ISENABLER0','GICR_ISPENDR0','GICR_ISACTIVER0',
        'GICR_IGRPMODR0','GICR_ICFGR0','GICD_ICFGR','GICR_IPRIORITYR0'],
      'drivers/irqchip/irq-gic-v3.c':[
        'ptr += gic_data.redist_stride','ptr += SZ_64K * 2','typer & GICR_TYPER_VLPIS',
        'typer & GICR_TYPER_LAST','GICR_TYPER bits [63:32]',
        'MPIDR_AFFINITY_LEVEL(mpidr, 3) << 24','if ((typer >> 32) == aff)'],
    }
    expected={'GICD_CTLR':0,'GICD_TYPER':4,'GICD_IIDR':8,'GICD_PIDR2':0xffe8,
      'GIC_PIDR2_ARCH_MASK':0xf0,'GIC_PIDR2_ARCH_GICv3':0x30,'GIC_PIDR2_ARCH_GICv4':0x40,
      'GICR_CTLR':0,'GICR_IIDR':4,'GICR_TYPER':8,'GICR_WAKER':0x14,
      'GICR_TYPER_VLPIS':2,'GICR_TYPER_LAST':16,'GIC_V3_REDIST_SIZE':0x20000,
      'GICR_IGROUPR0':0x80,'GICR_ISENABLER0':0x100,'GICR_ISPENDR0':0x200,
      'GICR_ISACTIVER0':0x300,'GICR_IGRPMODR0':0xd00,'GICR_ICFGR0':0xc00,'GICR_IPRIORITYR0':0x400}
    header=subprocess.check_output(['git','-C',str(repo),'show',rev+':include/linux/irqchip/arm-gic-v3.h'],text=True)
    def macro(name):
        match=re.search(r'^#define\s+'+re.escape(name)+r'\s+([^\n]+)',header,re.M);assert match,name
        text=match[1].split('/*')[0].strip()
        text=re.sub(r'\b(0x[0-9a-fA-F]+|[0-9]+)[uUlL]+\b',r'\1',text)
        text=re.sub(r'\b[A-Za-z_][A-Za-z_0-9]*\b',lambda m:str(macro(m[0])),text)
        expression=ast.parse(text,mode='eval')
        assert all(isinstance(n,(ast.Expression,ast.Constant,ast.BinOp,ast.LShift,ast.BitOr,ast.Add)) for n in ast.walk(expression))
        return eval(compile(expression,'primary-macro','eval'),{'__builtins__':{}})
    constants={name:macro(name) for name in expected};assert constants==expected
    refs=[]
    for name, markers in specs.items():
        raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+name])
        lines=raw.decode().splitlines()
        anchors={m:[i+1 for i,line in enumerate(lines) if m in line] for m in markers}
        assert all(anchors.values()),(name,anchors)
        refs.append(dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,
                         sha256=sha(raw),anchors=anchors))
    contract_path=ROOT/'UniXNU-raphael/evidence/interrupt-resource-contract.json'
    contract=json.loads(contract_path.read_text());assert contract['passed']
    blob=(ROOT/contract['collection']/'live.dtb').read_bytes()
    assert sha(blob)==contract['live_fdt_sha256']
    plan=recipe(blob);facts=contract['facts']
    assert (plan['gicd'],plan['gicd_bytes'])==(facts['distributor']['base'],facts['distributor']['bytes'])
    assert (plan['gicr'],plan['gicr_bytes'],plan['stride'])==(facts['redistributors']['base'],facts['redistributors']['bytes'],facts['redistributors']['stride'])
    report=dict(passed=True,primary_sources=refs,resource_contract=str(contract_path.relative_to(ROOT)),
        resource_contract_sha256=sha(contract_path.read_bytes()),fdt_sha256=sha(blob),recipe=plan,
        verified_architecture_constants=constants,sgi_config_ppi_offset=constants['GICR_ICFGR0']+4,
        sgi_offsets=SGI_OFFSETS,frame_scan_limit=8,
        frame_scan_limit_is_design_bound=True,offsets_from_architecture_not_board_copy=True,
        system_registers_accessed=False,interrupt_acknowledged=False,mmio_write_callback=False,
        snapshot_bytes=640,wire_version=1,handset_executed=False,private_modules_linked=False,
        source_sha256=sha((ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/GicProbe.c').read_bytes()),
        decoder_sha256=sha((ROOT/'scripts/gic_probe.py').read_bytes()))
    path=ROOT/'UniXNU-raphael/evidence/gic-probe-source-audit.json'
    path.write_text(json.dumps(report,indent=2)+'\n');print(path)

if __name__=='__main__':main()
