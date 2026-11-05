#!/usr/bin/env python3
"""Pin PMIC observer read semantics and the prerequisite handset APID evidence."""
import json,subprocess,re
from entry_probe import ROOT,sha

def main():
    k=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev=subprocess.check_output(['git','-C',str(k),'rev-parse','HEAD'],text=True).strip();assert rev=='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
    specs={
      'drivers/spmi/spmi-pmic-arb.c':['PMIC_ARB_CMD','PMIC_ARB_STATUS','PMIC_ARB_RDATA0','PMIC_ARB_OP_EXT_READL = 1','PMIC_ARB_TIMEOUT_US','PMIC_ARB_STATUS_DONE','PMIC_ARB_STATUS_FAILURE','PMIC_ARB_STATUS_DENIED','PMIC_ARB_STATUS_DROPPED','0x10000 * pmic_arb->ee + 0x80 * apid','(opc << 27) | ((addr & 0xff) << 4) | (bc & 0x7)','pmic_arb_set_rd_cmd(pmic_arb, offset + PMIC_ARB_CMD, cmd)'],
      'drivers/pinctrl/qcom/pinctrl-spmi-gpio.c':['PMIC_GPIO_REG_TYPE','PMIC_GPIO_REG_SUBTYPE','PMIC_GPIO_REG_MODE_CTL','PMIC_GPIO_REG_EN_CTL','PMIC_GPIO_TYPE','PMIC_GPIO_REG_LV_MV_MODE_DIR_MASK','PMIC_GPIO_PHYSICAL_OFFSET','PMIC_MPP_REG_RT_STS_VAL_MASK'],
      'drivers/input/misc/qpnp-power-on.c':['QPNP_PON_KPDPWR_N_SET','QPNP_PON_RESIN_N_SET','QPNP_PON_RT_STS(pon)']}
    refs=[]
    for path,markers in specs.items():
        raw=subprocess.check_output(['git','-C',str(k),'show',rev+':'+path]);lines=raw.decode().splitlines()
        anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers};assert all(anchors.values()),(path,anchors)
        refs.append(dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=path,sha256=sha(raw),anchors=anchors))
    prior=ROOT/'UniXNU-raphael/evidence/boot-input-map-observation.json';obs=json.loads(prior.read_text());assert obs['nonce_matched'] and obs['input_probe']['targets_verified']
    report=dict(passed=True,primary_sources=refs,prerequisite=str(prior.relative_to(ROOT)),prerequisite_sha256=sha(prior.read_bytes()),
      command_writes='Only EXT_READL one byte to validated observer CMD; no RW channel, WDATA, IRQ or PMIC write opcode',
      register_reads=['GPIO type+0x04','GPIO subtype+0x05','GPIO mode+0x40','GPIO enable+0x46','GPIO RT_STS+0x10','PON RT_STS+0x10'],
      timeout='One millisecond from primary driver; an additional 100000 iteration cap is a diagnostic design bound',
      private_modules_linked=False,physical_keys_verified=False)
    p=ROOT/'UniXNU-raphael/evidence/key-read-source-audit.json';p.write_text(json.dumps(report,indent=2)+'\n');print(p)
if __name__=='__main__':main()
