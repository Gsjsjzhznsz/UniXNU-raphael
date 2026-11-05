#!/usr/bin/env python3
"""Audit every SMMU read offset against pinned primary source; no MMIO access."""
import json
import re
import subprocess
from entry_probe import ROOT, sha
from smmu_probe import recipe, CB_OFFSETS


def main():
    kernel=ROOT/'sources/Xiaomi_Kernel_OpenSource'
    rev=subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()
    assert rev=='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
    constants={
        'ARM_SMMU_GR0_sCR0':0,'ARM_SMMU_GR0_ID0':0x20,'ARM_SMMU_GR0_ID1':0x24,'ARM_SMMU_GR0_ID2':0x28,
        'ID0_S1TS':1<<30,'ID0_S2TS':1<<29,'ID0_SMS':1<<27,'ID0_EXIDS':1<<8,
        'ID0_NUMSMRG_MASK':255,'ID1_PAGESIZE':1<<31,'ID1_NUMPAGENDXB_SHIFT':28,
        'ID1_NUMPAGENDXB_MASK':7,'ID1_NUMCB_MASK':255,'ID1_NUMS2CB_SHIFT':16,'ID1_NUMS2CB_MASK':255,
        'SMR_VALID':1<<31,'SMR_MASK_SHIFT':16,'SMR_MASK_MASK':0x7fff,'SID_MASK':0x7fff,
        'S2CR_CBNDX_MASK':255,'S2CR_TYPE_SHIFT':16,'S2CR_TYPE_MASK':3,'CBAR_TYPE_SHIFT':16,'CBAR_TYPE_MASK':3,
        'CBA2R_RW64_64BIT':1,'SCTLR_M':1,'sCR0_CLIENTPD':1,
        'ARM_SMMU_CB_SCTLR':0,'ARM_SMMU_CB_ACTLR':4,'ARM_SMMU_CB_TTBCR2':0x10,
        'ARM_SMMU_CB_TTBR0':0x20,'ARM_SMMU_CB_TTBR1':0x28,'ARM_SMMU_CB_TTBCR':0x30,
        'ARM_SMMU_CB_CONTEXTIDR':0x34,'ARM_SMMU_CB_S1_MAIR0':0x38,'ARM_SMMU_CB_S1_MAIR1':0x3c}
    anchors={
        'drivers/iommu/arm-smmu-regs.h':list(constants)+['ARM_SMMU_GR0_SMR(n)','ARM_SMMU_GR0_S2CR(n)',
            'ARM_SMMU_GR1_CBAR(n)','ARM_SMMU_GR1_CBA2R(n)','S2CR_TYPE_TRANS','S2CR_TYPE_BYPASS','S2CR_TYPE_FAULT'],
        'drivers/iommu/arm-smmu.c':['ARM_SMMU_GR0_NS(smmu)','? 0x400 : 0','smmu->pgshift =',
            'size = 1 << (((id >> ID1_NUMPAGENDXB_SHIFT)', 'smmu->cb_base = smmu->base + resource_size(res) / 2',
            'qsmmuv500_tbu_probe','qcom,stream-id-range','arm_smmu_init_power_resources(pdev)','clock-names','qcom,regulator-names'],
        'drivers/clk/qcom/gdsc-regulator.c':['PWR_ON_MASK'],
        'arch/arm64/boot/dts/qcom/sm8150-gdsc.dtsi':['mdss_core_gdsc:','tbu','reg =']}
    refs=[];sources={}
    for path,markers in anchors.items():
        raw=subprocess.check_output(['git','-C',str(kernel),'show',rev+':'+path]);text=raw.decode();sources[path]=text
        lines=text.splitlines();found={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers}
        assert all(found.values()),(path,[m for m,v in found.items() if not v])
        refs.append(dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=path,
                         sha256=sha(raw),anchors=found,url='https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/'+rev+'/'+path))
    regs=sources['drivers/iommu/arm-smmu-regs.h']
    for symbol,value in constants.items():
        expression=re.search(r'^#define\s+'+symbol+r'\s+(.+)$',regs,re.M).group(1)
        assert re.fullmatch(r'[0-9a-fA-FxX()<> \t]+',expression),expression
        assert eval(expression,{'__builtins__':{}},{})==value,(symbol,expression,value)
    for symbol,expr in {'ARM_SMMU_GR0_SMR':'(0x800 + ((n) << 2))',
                        'ARM_SMMU_GR0_S2CR':'(0xc00 + ((n) << 2))',
                        'ARM_SMMU_GR1_CBAR':'(0x0 + ((n) << 2))',
                        'ARM_SMMU_GR1_CBA2R':'(0x800 + ((n) << 2))'}.items():
        assert re.search(r'^#define\s+'+symbol+r'\(n\)\s+(.+)$',regs,re.M).group(1)==expr
    assert re.search(r'enum arm_smmu_s2cr_type \{\s*S2CR_TYPE_TRANS,\s*S2CR_TYPE_BYPASS,\s*S2CR_TYPE_FAULT,',regs)
    assert re.search(r'#define PWR_ON_MASK\s+BIT\(31\)',sources['drivers/clk/qcom/gdsc-regulator.c'])
    assert CB_OFFSETS==[constants[s] for s in ['ARM_SMMU_CB_SCTLR','ARM_SMMU_CB_ACTLR','ARM_SMMU_CB_TTBCR2',
        'ARM_SMMU_CB_TTBR0']]+[0x24,0x28,0x2c,0x30,0x34,0x38,0x3c]
    fdt=ROOT/'evidence/private/device/20261027T120325Z/live.dtb';blob=fdt.read_bytes()
    report=dict(kind='read-only SMMUv2 source audit',wire_version=4,passed=True,fdt_sha256=sha(blob),
                recipe=recipe(blob),primary_sources=refs,scalar_constants_verified=constants,
                context_register_offsets=CB_OFFSETS,mmio_writes=False,page_tables_read=False,
                pixel_memory_read_or_written=False,private_modules_linked=False,
                limitations=['Pinned Android P driver describes interfaces, not the exact running ABL',
                    'GDSCR power-on cannot prove global interconnect access; retained root bus vote is an experiment assumption',
                    'No clocks, power controls, ATOS, TLB invalidation, faults or display registers are written',
                    'A translation context does not establish physical mapping without a separate page-table audit'])
    (ROOT/'UniXNU-raphael/evidence/smmu-source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,primary_sources=len(refs),constants=len(constants),recipe=report['recipe']),indent=2))


if __name__=='__main__':main()
