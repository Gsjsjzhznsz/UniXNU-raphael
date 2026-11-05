#!/usr/bin/env python3
"""Pin primary generic GOP/MMU and SoC route semantics; no binary modules used."""
import json
import subprocess
from entry_probe import ROOT,sha

def main():
    sources=[]
    specifications={
      'sources/mu_basecore':{
        'MdePkg/Include/Protocol/GraphicsOutput.h':['clears the visible portions','EFI_GRAPHICS_OUTPUT_PROTOCOL_QUERY_MODE'],
        'MdeModulePkg/Include/Library/FrameBufferBltLib.h':['FrameBufferBltConfigure','FrameBufferBlt ('],
        'MdeModulePkg/Library/FrameBufferBltLib/FrameBufferBltLib.c':['Source      += Height * LineStride;','Destination += Height * LineStride;','PixelBlueGreenRedReserved8BitPerColor'],
        'UefiCpuPkg/Library/ArmMmuLib/AArch64/ArmMmuLibCore.c':['case ARM_MEMORY_REGION_ATTRIBUTE_UNCACHED_UNBUFFERED:','return TT_ATTR_INDX_MEMORY_NON_CACHEABLE | Permissions;']},
      'sources/Xiaomi_Kernel_OpenSource':{
        'drivers/gpu/drm/msm/sde/sde_hw_ctl.c':['CTL_LAYER_EXT','CTL_LAYER'],
        'drivers/gpu/drm/msm/sde/sde_hw_lm.c':['const_alpha = (bg_alpha & 0xFF)','IS_SM8150_TARGET'],
        'drivers/gpu/drm/msm/sde/sde_hw_pingpong.c':['PP_DSC_MODE'],
        'drivers/gpu/drm/msm/sde/sde_hw_intf.c':['INTF_MUX','AUTOREFRESH'],
        'drivers/gpu/drm/msm/sde/sde_hw_catalog.c':['mixer->pingpong = pp_count > 0','pp_idx++']}}
    for repo,items in specifications.items():
        root=ROOT/repo;rev=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        for name,markers in items.items():
            raw=subprocess.check_output(['git','-C',str(root),'show',rev+':'+name]);lines=raw.decode().splitlines()
            anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers}
            assert all(anchors.values()),(name,anchors)
            if (root/name).exists():assert (root/name).read_bytes()==raw
            sources.append(dict(repository=repo,revision=rev,path=name,sha256=sha(raw),anchors=anchors))
    report=dict(passed=True,primary_sources=sources,private_modules_linked=False,
      framebuffer_geometry_source='same entry gated PixelProbe and local FDT; no fixed board addresses',
      map_attribute='ArmMmuLib normal non-cacheable; framebuffer separately reserved from allocator',
      overlap_copy='port wrapper uses correct descending last row; generic upstream unchanged',
      limitations=['Inherited single mode only; no panel or clock reinitialization','No SetMode(0) handset claim until independently tested'])
    p=ROOT/'UniXNU-raphael/evidence/gop-source-audit.json';p.write_text(json.dumps(report,indent=2)+'\n');print(p)

if __name__=='__main__':main()
