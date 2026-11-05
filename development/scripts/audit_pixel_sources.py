#!/usr/bin/env python3
"""Bind CPU read candidate and interface counter semantics to primary sources."""
import json
import re
import subprocess
from entry_probe import ROOT,sha
from inspect_device import read_fdt,node_path,registers,physical


def main():
    rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0';kernel=ROOT/'sources/Xiaomi_Kernel_OpenSource'
    assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==rev
    refs=[]
    for path,markers in {
        'drivers/gpu/drm/msm/sde/sde_hw_intf.c':['INTF_STATUS','INTF_FRAME_COUNT','INTF_TEAR_INT_COUNT_VAL',
            'INTF_TEAR_LINE_COUNT','rd_ptr_frame_count =','wr_ptr_line_count ='],
        'drivers/iommu/arm-smmu.c':['DOMAIN_ATTR_S1_BYPASS','DOMAIN_ATTR_EARLY_MAP','reg |= SCTLR_M',
            'banks operate in bypass mode'],
        'drivers/iommu/arm-smmu-regs.h':['CBAR_TYPE_S1_TRANS_S2_BYPASS','SCTLR_M','CBA2R_RW64_64BIT']}.items():
        raw=subprocess.check_output(['git','-C',str(kernel),'show',rev+':'+path]);lines=raw.decode().splitlines()
        anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers};assert all(anchors.values())
        refs.append(dict(revision=rev,path=path,sha256=sha(raw),anchors=anchors))
        if path.endswith('sde_hw_intf.c'):
            for symbol,value in {'INTF_STATUS':0x26c,'INTF_FRAME_COUNT':0xac,
                                 'INTF_TEAR_INT_COUNT_VAL':0x298,'INTF_TEAR_LINE_COUNT':0x2b0}.items():
                assert int(re.search(r'^#define\s+'+symbol+r'\s+(0x[0-9a-fA-F]+)',raw.decode(),re.M).group(1),16)==value
    fdt=(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes()
    n=next(n for n in read_fdt(fdt).walk() if node_path(n)=='/reserved-memory/cont_splash_region')
    base,size=registers(n)[0];base=physical(n.parent,base,size)
    smmu=ROOT/'UniXNU-raphael/evidence/boot-smmu-observation.json';s=json.loads(smmu.read_text())
    assert s['firmware_checkpoint_passed'] and s['smmu']['all_declared_streams_uniquely_matched']
    assert all(c['cbar_type']==1 and not c['translation_enabled'] for c in s['smmu']['contexts'])
    arm=ROOT/'sources/mu_basecore/MdePkg/Library/ArmLib/AArch64/AArch64ArchTimerSupport.S'
    assert 'cntpct_el0' in arm.read_text().lower()
    report=dict(kind='bounded read-only CPU splash and interface counter source audit',passed=True,wire_version=1,
        fdt_sha256=sha(fdt),primary_sources=refs,
        splash=dict(base=base,size=size,source=node_path(n)+':reg',no_map_present='no-map' in n.properties),
        prior_handset_smmu=dict(path=str(smmu.relative_to(ROOT)),sha256=sha(smmu.read_bytes()),
                               source_revision='9d2fb86365b30f68375fa5d837ba47209bea8444'),
        timer=dict(path=str(arm.relative_to(ROOT)),sha256=sha(arm.read_bytes()),frequency_source='CNTFRQ_EL0 at this entry'),
        design_choices=dict(grid=[64,64],rounds=32,spacing_seconds=0.002,maximum_timer_poll_iterations=10000000),
        mmio_writes=False,pixel_writes=False,page_table_walk=False,
        limitations=['CPU uses MMU/cache-disabled entry; bounded accesses test the sourced candidate physical memory',
            'S1 disabled and CBAR stage2 bypass are configuration evidence, not proof against hidden fabric/security remapping',
            'The live cont_splash reserved-memory node has no no-map property; do not assert it does',
            'Counter movement may reflect an internal VSYNC counter and cannot by itself prove panel update',
            'Pixel samples and raw readbacks stay private; only hashes/counts are public'])
    (ROOT/'UniXNU-raphael/evidence/pixel-source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,primary_sources=len(refs),splash=report['splash']))


if __name__=='__main__':main()
