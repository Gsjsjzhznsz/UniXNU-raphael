#!/usr/bin/env python3
"""Bind the read-only display recipe to local handset FDT and pinned primary source."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from entry_probe import ROOT, sha
from display_probe import recipe, OFFSETS, INTF_OFFSETS, PP_OFFSETS, route_addresses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fdt', type=Path, default=ROOT/'evidence/private/device/20261027T120325Z/live.dtb')
    args = parser.parse_args()
    kernel = ROOT/'sources/Xiaomi_Kernel_OpenSource'
    revision = subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'], text=True).strip()
    assert revision == '663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
    requirements = {
        'drivers/gpu/drm/msm/sde/sde_hw_ctl.c': ['CTL_TOP','CTL_INTF_ACTIVE','CTL_LAYER(lm)',
            'CTL_LAYER_EXT(lm)','CTL_LAYER_EXT2(lm)','CTL_LAYER_EXT3(lm)',
            'sspp_reg_cfg_tbl', 'SSPP_VIG0 */', 'mode_sel |= BIT(17)', 'mix = (i + 1)'],
        'drivers/gpu/drm/msm/sde/sde_hw_lm.c': ['LM_OP_MODE','LM_OUT_SIZE','LM_BLEND0_OP','LM_BLEND0_CONST_ALPHA',
            'IS_SM8150_TARGET', 'const_alpha = (bg_alpha & 0xFF)', 'blendstage_base[stage - SDE_STAGE_0]'],
        'drivers/gpu/drm/msm/sde/sde_hw_intf.c': ['INTF_TIMING_ENGINE_EN','INTF_CONFIG','INTF_CONFIG2',
            'INTF_DSI_CMD_MODE_TRIGGER_EN','INTF_PANEL_FORMAT','INTF_FRAME_COUNT','INTF_MUX',
            'INTF_TEAR_TEAR_CHECK_EN','INTF_TEAR_SYNC_CONFIG_VSYNC','INTF_TEAR_AUTOREFRESH_CONFIG',
            'mux_cfg |= (pp - PINGPONG_0)', 'cfg->enable = (val & BIT(31))'],
        'drivers/gpu/drm/msm/sde/sde_hw_pingpong.c': ['PP_DSC_MODE','PP_DCE_DATA_IN_SWAP','PP_DCE_DATA_OUT_SWAP'],
        'drivers/gpu/drm/msm/sde/sde_hw_mdss.h': ['SDE_BLEND_FG_ALPHA_FG_CONST','SDE_BLEND_FG_ALPHA_FG_PIXEL',
            'SDE_BLEND_BG_ALPHA_BG_CONST','SDE_STAGE_BASE = 0'],
        'drivers/iommu/arm-smmu.c': ['fwid |= (u16)args->args[0]', 'fwid |= (u16)args->args[1] << SMR_MASK_SHIFT',
            'arm_smmu_handoff_cbs', 's2cr.type != S2CR_TYPE_TRANS'],
        'drivers/gpu/drm/msm/sde/sde_hw_sspp.c': ['SSPP_SRC_SIZE','SSPP_SRC_XY','SSPP_OUT_SIZE','SSPP_OUT_XY',
          'SSPP_SRC0_ADDR','SSPP_SRC1_ADDR','SSPP_SRC2_ADDR','SSPP_SRC3_ADDR','SSPP_SRC_YSTRIDE0','SSPP_SRC_YSTRIDE1',
          'SSPP_SRC_FORMAT','SSPP_SRC_UNPACK_PATTERN','SSPP_SRC_OP_MODE','SSPP_SRC_ADDR_SW_STATUS',
          'SSPP_MULTIRECT_OPMODE','SSPP_SRC_FORMAT_REC1','SSPP_SRC_UNPACK_PATTERN_REC1','SSPP_SRC_OP_MODE_REC1'],
        'drivers/clk/qcom/gcc-sm8150.c': ['gcc_disp_ahb_clk'],
        'drivers/clk/qcom/dispcc-sm8150.c': ['disp_cc_mdss_ahb_clk','disp_cc_mdss_mdp_clk'],
        'drivers/clk/qcom/clk-branch.c': ['BRANCH_CLK_OFF', 'clk_branch_in_hwcg_mode', 'Skip checking halt bit'],
        'drivers/clk/qcom/gdsc-regulator.c': ['PWR_ON_MASK'],
        'drivers/gpu/drm/msm/sde/sde_kms.c': ['caller api needs to turn on clock', 'one to one mapping',
                                                 '_sde_kms_release_splash_buffer'],
        'drivers/gpu/drm/msm/sde/sde_hw_catalog.c': ['sblk = kzalloc', 'sspp->base =', 'sblk->src_blk.id',
            'set_bit(SDE_CTL_ACTIVE_CFG', 'set_bit(SDE_INTF_INPUT_CTRL', 'set_bit(SDE_INTF_TE',
            'major_version < SDE_HW_MAJOR(SDE_HW_VER_500)', 'sde_cfg->ctl_rev = SDE_CTL_CFG_VERSION_1_0_0'],
        'arch/arm64/boot/dts/qcom/sm8150-sde.dtsi': ['mdss_mdp:','qcom,sde-sspp-off'],
        'arch/arm64/boot/dts/qcom/sm8150-gdsc.dtsi': ['mdss_core_gdsc:'],
    }
    refs=[]; sources={}
    for name, markers in requirements.items():
        raw = subprocess.check_output(['git','-C',str(kernel),'show',revision+':'+name])
        text = raw.decode(); sources[name] = text
        lines=text.splitlines()
        anchors={marker:[i+1 for i,line in enumerate(lines) if marker in line] for marker in markers}
        assert all(anchors.values()), (name, anchors)
        refs.append(dict(repository='MiCode/Xiaomi_Kernel_OpenSource', revision=revision, path=name,
                         sha256=sha(raw), anchors=anchors,
                         url='https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/'+revision+'/'+name))
    sspp=sources['drivers/gpu/drm/msm/sde/sde_hw_sspp.c']
    symbols=requirements['drivers/gpu/drm/msm/sde/sde_hw_sspp.c']
    actual=[int(re.search(r'^#define\s+'+symbol+r'\s+(0x[0-9a-fA-F]+)',sspp,re.M).group(1),16) for symbol in symbols]
    assert actual == OFFSETS
    # Independently resolve every scalar register used by the route extension.
    def constants(path, symbols):
        return [int(re.search(r'^#define\s+'+symbol+r'\s+(0x[0-9a-fA-F]+)',sources[path],re.M).group(1),16)
                for symbol in symbols]
    intf_symbols=requirements['drivers/gpu/drm/msm/sde/sde_hw_intf.c'][:10]
    pp_symbols=requirements['drivers/gpu/drm/msm/sde/sde_hw_pingpong.c']
    assert constants('drivers/gpu/drm/msm/sde/sde_hw_intf.c',intf_symbols)==INTF_OFFSETS
    assert constants('drivers/gpu/drm/msm/sde/sde_hw_pingpong.c',pp_symbols)==PP_OFFSETS
    assert constants('drivers/gpu/drm/msm/sde/sde_hw_ctl.c',['CTL_TOP','CTL_INTF_ACTIVE'])==[0x14,0xf4]
    assert constants('drivers/gpu/drm/msm/sde/sde_hw_lm.c',
                     ['LM_OP_MODE','LM_OUT_SIZE','LM_BLEND0_OP','LM_BLEND0_CONST_ALPHA'])==[0,4,0,4]
    ctl=sources['drivers/gpu/drm/msm/sde/sde_hw_ctl.c']
    assert '(((lm) == LM_5) ? (0x024) : (((lm) - LM_0) * 0x004))' in ctl
    for offset in ['0x40','0x70','0xA0']:
        assert '('+offset+' + (((lm) - LM_0) * 0x004))' in ctl
    for name, symbol, value in [('gcc-sm8150.c','gcc_disp_ahb_clk',0xb00c),
                               ('dispcc-sm8150.c','disp_cc_mdss_ahb_clk',0x2080),
                               ('dispcc-sm8150.c','disp_cc_mdss_mdp_clk',0x200c)]:
        text=sources['drivers/clk/qcom/'+name]
        match=re.search(r'static struct clk_branch '+symbol+r' = \{(.+?)\n\};',text,re.S)
        assert int(re.search(r'\.halt_reg = (0x[0-9a-f]+)',match.group(1)).group(1),16)==value
        assert int(re.search(r'\.enable_reg = (0x[0-9a-f]+)',match.group(1)).group(1),16)==value
    gcc_source = sources['drivers/clk/qcom/gcc-sm8150.c']
    gcc_branch = re.search(r'static struct clk_branch gcc_disp_ahb_clk = \{(.+?)\n\};', gcc_source, re.S).group(1)
    assert re.search(r'\.hwcg_reg = 0xb00c', gcc_branch) and re.search(r'\.hwcg_bit = 1', gcc_branch)
    blob=args.fdt.read_bytes(); plan=recipe(blob)
    metadata=json.loads((ROOT/'UniXNU-raphael/evidence/vendor-module-metadata.json').read_text())
    display=next(m for m in metadata if m['name']=='DisplayDxe')
    known={'157a5c45-21b2-43c5-ba7c-822fee5fe599':'PlatformInfo',
           'b0760469-970c-487a-a4b5-28db7b45cef1':'ChipInfo',
           '241afae6-885f-4f6c-a7ea-c28eab79c3e5':'Clock'}
    deps=[dict(guid=t['guid'], identified_interface=known.get(t['guid']), provider_verified=False)
          for d in display['dependencies'] for t in d['tokens'] if t['op']=='PUSH']
    report=dict(kind='read-only early display probe source audit', wire_version=3,
                route_register_scalar_offsets_verified=19, route_sample_count=len(route_addresses(plan)),
                legacy_pp_te_registers_read=False, smmu_registers_read=False,
                gcc_hwcg_bit=1, gcc_hwcg_idle_clk_off_allowed=True, fdt_sha256=sha(blob),
                private_fdt=str(args.fdt.resolve().relative_to(ROOT)), recipe=plan, primary_sources=refs,
                display_dxe_reference=display, declared_protocol_prerequisites=deps,
                private_modules_linked=False, clock_or_power_writes=False, passed=True,
                limitations=['Android P public driver is an interface reference, not proof of exact current bootloader implementation',
                             'Only three of nine DisplayDxe prerequisite GUIDs have identified public interfaces',
                             'DEPEX is incomplete evidence of runtime dependencies; DisplayDxe is not loaded',
                             'A clock gate check cannot prove absence of all hidden firmware access restrictions'])
    path=ROOT/'UniXNU-raphael/evidence/display-source-audit.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True, source_count=len(refs), offsets_verified=len(actual),
                         protocol_prerequisites=len(deps), recipe=plan),indent=2))


if __name__=='__main__': main()
