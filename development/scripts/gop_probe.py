#!/usr/bin/env python3
"""Decode separate GOP checkpoints; memory protocol proof is not visible-output proof."""
import struct
FIELDS='version status base width height stride extent map_base map_size mapped_read_verified protocol_installed query_verified invalid_mode_rejected blt_checks patch_written patch_verified patch_restored patch_mismatches start end hold_ticks backup active patch_width patch_height restore_fallback_used'.split()
def decode(raw,pixels,stage,manager_ui=False):
    assert len(raw)==len(FIELDS)*8
    r=dict(zip(FIELDS,struct.unpack('>'+'Q'*len(FIELDS),raw)))
    p=pixels['header'];assert r['version']==1 and r['status']=={2:2,3:3,6:4 if manager_ui else 6}[stage]
    assert (r['base'],r['width'],r['height'],r['stride'],r['extent'])==(p['base_low'],p['width'],p['height'],p['stride'],p['extent'])
    assert r['map_base']==r['base']&~4095
    assert r['map_size']==((r['base']+r['extent']+4095)&~4095)-r['map_base']
    assert r['mapped_read_verified']==int(stage>=3)
    if stage==6 and manager_ui:
        assert r['protocol_installed']==1
        assert all(r[k]==0 for k in FIELDS[11:])
    elif stage==6:
        assert r['protocol_installed']==r['query_verified']==r['invalid_mode_rejected']==1
        assert r['blt_checks']==15
        assert r['patch_width']==256 and r['patch_height']==128
        assert r['patch_written']==r['patch_verified']==r['patch_restored']==32768
        assert r['patch_mismatches']==r['active']==r['backup']==r['restore_fallback_used']==0
        assert r['hold_ticks']==p['counter_frequency']*10
        assert (r['end']-r['start'])%(1<<64)>=r['hold_ticks']
    else:
        assert r['protocol_installed']==r['blt_checks']==r['active']==r['backup']==0
    return dict(r,checkpoint_verified=True,mapping_read_verified=stage>=3,
        protocol_and_blt_memory_verified=stage==6 and not manager_ui,visible_output_verified=False,
        display_mmio_writes=False,persistent_storage_writes=False)
