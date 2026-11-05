#!/usr/bin/env python3
"""Cross-check the observed route and FDT IOMMU description; never enable GOP."""
import copy
import json
import subprocess
from entry_probe import ROOT, sha
from inspect_device import read_fdt, node_path, registers, physical
from display_probe import decode


def constant_blend(op, alpha):
    """Resolve only the reference driver's constant, unmodulated factors."""
    result = dict(op=op, combined_alpha=alpha, foreground_constant=(alpha >> 16) & 255,
                  background_constant=alpha & 255, supported=False)
    # Reject modulation/transparency/dim-layer and every unmodeled bit.
    if op & ~(3 | (1 << 2) | (3 << 8) | (1 << 10)):
        result['reason'] = 'unsupported blend operation bits'
        return result
    factors=[]
    for selector,invert in [(op & 3, bool(op & 4)), ((op >> 8) & 3, bool(op & (1 << 10)))]:
        if selector >= 2:
            result['reason'] = 'pixel alpha dependence'
            return result
        value=result['foreground_constant' if selector == 0 else 'background_constant']
        factors.append(255 - value if invert else value)
    result.update(supported=True, foreground_factor_255=factors[0], background_factor_255=factors[1],
                  pixel_alpha_used=False, opaque_foreground=factors == [255,0])
    return result


def route_candidate(decoded):
    route=decoded['routing'];pipes=decoded['programmed_pipes']
    issues=[];result=dict(register_configuration_consistent=False, rejection_reasons=issues)
    if len(pipes)!=1 or pipes[0]['index']!=0 or pipes[0]['type']!='vig':
        issues.append('requires sole observed VIG0 source');return result
    stages=[(ctl,lm) for ctl in route['programmed_ctls'] for lm in ctl['mixers']
            if lm['vig0_rect0_stage_code'] or lm['vig0_rect1_stage_code']]
    if len(stages)!=1:
        issues.append('requires unique programmed VIG0 mixer route');return result
    ctl,lm=stages[0];blend_index=lm['vig0_rect0_blend_index']
    mixers=[m for m in route['programmed_mixers'] if m['index']==lm['mixer']]
    if len(mixers)!=1 or blend_index is None or lm['vig0_rect1_stage_code']:
        issues.append('requires one non-base, non-multirect mixer stage');return result
    mixer=mixers[0]
    selected=[i for i in route['interfaces'] if ctl['interface_active_mask'] & (1 << i['index'])]
    if len(selected)!=1 or ctl['interface_active_mask'] != 1 << selected[0]['index']:
        issues.append('requires exactly one described interface');return result
    intf=selected[0];pps=route['pingpong']
    if not 0 <= intf['pingpong_selection'] < len(pps):
        issues.append('interface has no supported pingpong selection');return result
    pp=pps[intf['pingpong_selection']]
    if not 0 <= blend_index < len(mixer['blend_stages']):
        issues.append('blend stage outside description');return result
    blend=mixer['blend_stages'][blend_index]
    alpha=constant_blend(blend['op'],blend['constant_alpha'])
    pipe=pipes[0]
    required=[(ctl['command_mode_bit'],'CTL command mode bit absent'),
              (intf['type']=='dsi','selected interface is not DSI'),
              (intf['pingpong_selection']==mixer['index'],'mux differs from reference catalog LM/PP pairing'),
              (mixer['width']==pipe['output_width'] and mixer['height']==pipe['output_height'],'mixer size mismatch'),
              (intf['tear_check_enable']==1,'interface TE not enabled'),
              (intf['autorefresh_enable'] and intf['autorefresh_frame_count']>0,'autorefresh not programmed'),
              (pp['dsc_mode']==0,'DSC path not supported by this interpretation'),
              (alpha.get('opaque_foreground',False),'blend does not establish opaque constant foreground')]
    issues.extend(reason for passed,reason in required if not passed)
    result.update(register_configuration_consistent=not issues,ctl_index=ctl['index'],mixer_index=mixer['index'],
                  stage_code=lm['vig0_rect0_stage_code'],blend_stage_index=blend_index,
                  border_output=lm['border_output'],interface_index=intf['index'],pingpong_index=pp['index'],
                  command_mode=ctl['command_mode_bit'],width=mixer['width'],height=mixer['height'],blend=alpha,
                  programmed_autorefresh=intf['autorefresh_config'],
                  lm_pp_pairing_source='fixed source catalog assigns nonzero LM offsets to consecutive PPs',
                  pixel_fetch_activity_proven=False,cpu_mapping_proven=False,framebuffer_writable_proven=False,
                  refresh_executed_by_project=False,gop_enabled=False)
    return result


def iommu_description(blob, description):
    tree=read_fdt(blob);nodes=list(tree.walk())
    smmu=next(n for n in nodes if node_path(n)==description['source'])
    sid=description['stream_id'];mask=description['stream_match_mask']
    assert sid <= 65535 and mask <= 65535
    matching=[i for i in range(65536) if (i ^ sid) & (~mask & 65535) == 0]
    relevant=[]
    for n in nodes:
        if n.parent is not smmu or b'qcom,qsmmuv500-tbu' not in n.properties.get('compatible',b'').split(b'\0'):
            continue
        start,count=n.cells('qcom,stream-id-range')
        ids=[i for i in matching if start <= i < start+count]
        if not ids:continue
        handle,=n.cells('vdd-supply');gdsc=next(g for g in nodes if g.cells('phandle')==[handle])
        def resource(node):
            return [dict(base=physical(node.parent,b,s),size=s) for b,s in registers(node)]
        relevant.append(dict(path=node_path(n),declared_sid_start=start,declared_sid_count=count,
             matching_streams=ids,regions=resource(n),reg_names=n.strings('reg-names'),
             power_source=node_path(gdsc),power_regions=resource(gdsc),
             power_name=gdsc.strings('regulator-name'),power_state_sampled=False))
    assert sorted(i for t in relevant for i in t['matching_streams']) == matching
    return dict(**description,matching_stream_ids=matching,relevant_tbus=relevant,
                stream_mask_is_context_bank_index=False,
                actual_smr_s2cr_context_bank=None,table_walk_not_performed=True,
                power_bus_vote_and_early_mapping_access_unverified=True)


def main():
    path=ROOT/'UniXNU-raphael/evidence/sec-display-handoff.json';handoff=json.loads(path.read_text())
    assert all(handoff[k] for k in ['nonce_matched','firmware_checkpoint_passed','root_verified','boot_partition_unchanged'])
    blob=(ROOT/handoff['private_readback']/'after.dtb').read_bytes();assert sha(blob)==handoff['fdt_sha256']
    chosen=next(n for n in read_fdt(blob).walk() if node_path(n)=='/chosen')
    decoded=decode(chosen.properties['raphael,display-snapshot'],blob)
    assert decoded==handoff['display_probe'] and decoded['version']==3 and decoded['status']==7
    candidate=route_candidate(decoded);assert candidate['register_configuration_consistent']
    checks=[dict(name='nonce-bound handset route and constant blend',passed=True)]
    for name,mutate in [
        ('pixel alpha blend',lambda d:d['routing']['programmed_mixers'][0]['blend_stages'][3].update(op=0x402)),
        ('unknown blend bit',lambda d:d['routing']['programmed_mixers'][0]['blend_stages'][3].update(op=0x10400)),
        ('disabled autorefresh',lambda d:d['routing']['interfaces'][1].update(autorefresh_enable=False)),
        ('detached interface mux',lambda d:d['routing']['interfaces'][1].update(pingpong_selection=15)),
        ('unknown interface mask',lambda d:d['routing']['programmed_ctls'][0].update(interface_active_mask=1<<15)),
        ('mixer dimension mismatch',lambda d:d['routing']['programmed_mixers'][0].update(width=1)),
        ('unexpected DSC path',lambda d:d['routing']['pingpong'][0].update(dsc_mode=1))]:
        changed=copy.deepcopy(decoded);mutate(changed)
        assert not route_candidate(changed)['register_configuration_consistent']
        checks.append(dict(name=name+' rejected',passed=True))
    refs=[];kernel=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
    for name,markers in {
        'drivers/gpu/drm/msm/sde/sde_hw_mdss.h':['SDE_BLEND_FG_ALPHA_FG_CONST','SDE_BLEND_BG_ALPHA_FG_CONST','SDE_BLEND_BG_INV_ALPHA'],
        'drivers/gpu/drm/msm/sde/sde_hw_lm.c':['const_alpha = (bg_alpha & 0xFF)','IS_SM8150_TARGET'],
        'drivers/gpu/drm/msm/sde/sde_hw_catalog.c':['mixer->pingpong = pp_count > 0','pp_idx++'],
        'drivers/iommu/arm-smmu.c':['fwid |= (u16)args->args[1] << SMR_MASK_SHIFT','(mask & smrs[i].mask) == mask',
             'tbu->sid_start = of_read_number(cell, 1)','arm_smmu_power_on(smmu->pwr)','arm_smmu_handoff_cbs(smmu)']}.items():
        raw=subprocess.check_output(['git','-C',str(kernel),'show',rev+':'+name]);lines=raw.decode().splitlines()
        anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers};assert all(anchors.values())
        refs.append(dict(path=name,revision=rev,sha256=sha(raw),anchors=anchors))
    result=dict(kind='host interpretation of nonce-bound boot register and FDT description; not pixel validation',
        handoff=str(path.relative_to(ROOT)),handoff_sha256=sha(path.read_bytes()),fdt_sha256=sha(blob),
        candidate=candidate,iommu=iommu_description(blob,decoded['routing']['iommu_description']),
        checks=checks,primary_sources=refs,
        analysis_sources=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes()))
                          for p in [ROOT/'scripts/display_probe.py',ROOT/'scripts/inspect_boot_route.py']],
        limitations=['Configuration consistency does not prove actual DMA, TE edges or panel update',
                     'SMMU register and page-table state, CPU mapping and ownership remain unverified',
                     'No pixel, clock, power, SMMU or refresh register was written'])
    target=ROOT/'UniXNU-raphael/evidence/boot-display-route-observation.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
