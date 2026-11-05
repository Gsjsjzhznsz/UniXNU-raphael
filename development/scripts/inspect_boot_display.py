#!/usr/bin/env python3
"""Interpret a nonce-verified entry snapshot, keeping GOP enablement disabled."""
import json
import subprocess
from pathlib import Path
from entry_probe import ROOT, sha
from inspect_device import read_fdt, node_path, registers, physical
from display_probe import decode


def linear_candidate(pipe, reservation):
    # sde_hw_sspp.c format packing + sde_formats.c ARGB8888 tuple.
    expected_format = sum(3 << shift for shift in [0,2,4,6]) | (1 << 8) | (3 << 9) | (3 << 12) | (1 << 17)
    expected_unpack = sum(value << (8*i) for i,value in enumerate([1,0,2,3]))
    failures=[]
    def require(condition, reason):
        if not condition: failures.append(reason)
    w,h=pipe['source_width'],pipe['source_height']; stride=pipe['stride0']
    addresses=pipe['plane_address_registers'];base=addresses[0]; size=stride*h
    require(pipe['source_format']==expected_format, 'not the verified linear ARGB8888 format tuple')
    require(pipe['unpack_pattern']==expected_unpack, 'unexpected component order')
    require(pipe['op_mode']==0x80000000, 'unexpected flips, compression or source processing flags')
    require(w>0 and h>0 and w==pipe['output_width'] and h==pipe['output_height'], 'zero dimensions or scaling')
    require(pipe['source_xy']==pipe['output_xy']==0, 'nonzero crop or output origin')
    require(stride>=w*4 and stride%4==0, 'invalid or undersized stride')
    require(pipe['stride1']==0 and addresses[1:]==[0,0,0] and pipe['multirect_opmode']==0, 'multiple planes or rectangles')
    require(pipe['secure_address_status']==0, 'secure address state is not clear')
    require(size>0 and reservation['base']<=base and base+size<=reservation['base']+reservation['size'],
            'pixel extent is not wholly in the sourced splash reservation')
    return dict(candidate_valid=not failures, rejection_reasons=failures,
                address_register_value=base, address_register_value_hex=hex(base),
                width=w,height=h,stride_bytes=stride,pixels_per_scanline=stride//4,
                pixel_bytes=size,end_exclusive=base+size,
                interpreted_format='DRM_FORMAT_ARGB8888, little-endian B G R A bytes' if not failures else None,
                alpha_enabled=True if not failures else None,
                uefi_byte_order_compatible='PixelBlueGreenRedReserved8BitPerColor' if not failures else None,
                reservation=reservation, active_routing_verified=False,
                physical_mapping_verified=False, panel_refresh_verified=False, gop_enabled=False,
                limits=['UEFI Reserved byte and active alpha blending are not interchangeable without a blend audit',
                        'The source address register may be an IOVA; this record does not establish its CPU mapping',
                        'No generated GOP PCD, framebuffer write, cache operation or display kickoff is authorized by this record'])


def main():
    path=ROOT/'UniXNU-raphael/evidence/sec-display-handoff.json'
    handoff=json.loads(path.read_text())
    assert all(handoff[k] for k in ['nonce_matched','firmware_checkpoint_passed','root_verified','boot_partition_unchanged'])
    fdt_path=ROOT/handoff['private_readback']/'after.dtb'
    blob=fdt_path.read_bytes(); assert sha(blob)==handoff['fdt_sha256']
    tree=read_fdt(blob)
    chosen=next(n for n in tree.walk() if node_path(n)=='/chosen')
    decoded=decode(chosen.properties['raphael,display-snapshot'],blob)
    assert decoded==handoff['display_probe'] and decoded['status']==7
    splash=next(n for n in tree.walk() if node_path(n)=='/reserved-memory/cont_splash_region')
    base,size=registers(splash)[0]
    reservation=dict(base=physical(splash.parent,base,size),size=size,source=node_path(splash)+':reg[0]')
    candidates=[linear_candidate(pipe,reservation) for pipe in decoded['programmed_pipes']]
    refs=[];kernel=ROOT/'sources/Xiaomi_Kernel_OpenSource'
    rev=subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()
    assert rev=='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
    for name,markers in {
        'drivers/gpu/drm/msm/sde/sde_formats.c':['#define INTERLEAVED_RGB_FMT(', 'INTERLEAVED_RGB_FMT(ARGB8888,'],
        'drivers/gpu/drm/msm/sde/sde_hw_mdss.h':['C0_G_Y = 0','C1_B_Cb = 1','C2_R_Cr = 2','C3_ALPHA = 3'],
        'drivers/gpu/drm/msm/sde/sde_hw_sspp.c':['src_format = (chroma_samp','unpack = (fmt->element','fmt->unpack_count - 1']}.items():
        raw=subprocess.check_output(['git','-C',str(kernel),'show',rev+':'+name]);lines=raw.decode().splitlines()
        anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers};assert all(anchors.values())
        refs.append(dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,
                         sha256=sha(raw),anchors=anchors))
    # Check real data plus corruptions that must never yield a usable candidate.
    checks=[dict(name='real observed tuple is recognized',passed=len(candidates)==1 and candidates[0]['candidate_valid'])]
    original=decoded['programmed_pipes'][0]
    for name,key,value in [('compressed fetch','source_format',original['source_format']|(2<<30)),
                           ('truncated stride','stride0',4),('wrong byte order','unpack_pattern',0),
                           ('crop active','source_xy',1),('multiple rectangles','multirect_opmode',1),
                           ('secure source','secure_address_status',1),
                           ('address beyond reservation','plane_address_registers',[base+size,0,0,0])]:
        changed=dict(original);changed[key]=value
        checks.append(dict(name=name+' rejected',passed=not linear_candidate(changed,reservation)['candidate_valid']))
    assert all(x['passed'] for x in checks)
    report=dict(kind='interpretation of observed boot display registers; not a GOP driver',
                handoff=str(path.relative_to(ROOT)),handoff_sha256=sha(path.read_bytes()),
                fdt_sha256=sha(blob),hardware_revision=hex(decoded['hardware_revision']),
                candidates=candidates,primary_sources=refs,interpretation_checks=checks,
                framebuffer_written=False,full_display_validated=False)
    target=ROOT/'UniXNU-raphael/evidence/boot-display-observation.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(candidates=candidates,interpretation_checks=len(checks)),indent=2))


if __name__=='__main__': main()
