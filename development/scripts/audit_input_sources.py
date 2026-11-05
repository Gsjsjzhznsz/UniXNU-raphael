#!/usr/bin/env python3
"""Pin primary input register semantics and current-device resources."""
import json,subprocess
from entry_probe import ROOT,sha
from input_probe import recipe

def main():
    kernel=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev=subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()
    assert rev=='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
    markers={
      'drivers/spmi/spmi-pmic-arb.c':['PMIC_ARB_VERSION','PMIC_ARB_VERSION_V5_MIN','SPMI_OWNERSHIP_TABLE_REG(N)','SPMI_OWNERSHIP_PERIPH2OWNER(X)','PMIC_ARB_CHAN_IS_IRQ_OWNER(reg)','pmic_arb_read_apid_map_v5','return 0x900 + 0x4 * n;','0x10000 * pmic_arb->ee + 0x80 * apid','(opc << 27) | ((addr & 0xff) << 4) | (bc & 0x7)'],
      'drivers/pinctrl/qcom/pinctrl-spmi-gpio.c':['PMIC_GPIO_ADDRESS_RANGE','PMIC_GPIO_PHYSICAL_OFFSET','PMIC_MPP_REG_RT_STS','pad->base = start + i * PMIC_GPIO_ADDRESS_RANGE','pad->gpio_idx = i + PMIC_GPIO_PHYSICAL_OFFSET'],
      'drivers/input/misc/qpnp-power-on.c':['QPNP_PON_RT_STS(pon)','QPNP_PON_KPDPWR_N_SET','QPNP_PON_RESIN_N_SET','key_status = pon_rt_sts & pon_rt_bit;'],
      'Documentation/devicetree/bindings/pinctrl/qcom,pmic-gpio.txt':['gpio','reg'],
      'Documentation/devicetree/bindings/spmi/qcom,spmi-pmic-arb.txt':['core','obsrvr','qcom,ee'],
      'Documentation/devicetree/bindings/input/qpnp-power-on.txt':['qcom,pon-type','linux,code']}
    refs=[];texts={}
    for path,ms in markers.items():
        raw=subprocess.check_output(['git','-C',str(kernel),'show',rev+':'+path]);lines=raw.decode().splitlines();texts[path]=raw.decode()
        anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in ms};assert all(anchors.values()),(path,anchors)
        refs.append(dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=path,sha256=sha(raw),anchors=anchors))
    import re
    constants={
      'drivers/spmi/spmi-pmic-arb.c':{'PMIC_ARB_VERSION':0,'PMIC_ARB_VERSION_V5_MIN':0x50000000,'PMIC_ARB_MAX_PERIPHS':512},
      'drivers/pinctrl/qcom/pinctrl-spmi-gpio.c':{'PMIC_GPIO_ADDRESS_RANGE':0x100,'PMIC_GPIO_PHYSICAL_OFFSET':1,'PMIC_MPP_REG_RT_STS':0x10,'PMIC_MPP_REG_RT_STS_VAL_MASK':1}}
    for path,items in constants.items():
        for name,value in items.items():assert int(re.search(r'^#define\s+'+name+r'\s+(0x[0-9a-fA-F]+|\d+)',texts[path],re.M).group(1),0)==value
    blob=(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes()
    report=dict(passed=True,wire_version=1,fdt_sha256=sha(blob),recipe=recipe(blob),primary_sources=refs,scalar_constants_verified=constants,
      implemented_scope='read-only version/APID map/owner registers; no PMIC command, interrupt/reset/clock/power writes',private_modules_linked=False,
      assumptions=['Retained arbiter interconnect is accessible at this boot handoff; configuration reads can still fault or stall'],
      unknowns=['Actual arbiter version/APID/owner until handset readback','Observer PMIC transaction accessibility','Physical key state, debounce and visible menu'])
    p=ROOT/'UniXNU-raphael/evidence/input-source-audit.json';p.write_text(json.dumps(report,indent=2)+'\n');print(p)
if __name__=='__main__':main()
