#!/usr/bin/env python3
"""Independent input mapping/protocol and menu diagnostic wire validators."""
import struct
from gop_probe import FIELDS as GOP_FIELDS
FIELDS='version status map_base0 map_base1 map_count mapped_read_verified protocol_installed polls errors events read_calls reset_calls pressed_mask released_mask last_raw last_scan'.split()
MENU_FIELDS='version status start end hold_ticks selected up down enter wait_signals pixels_changed exit_reason'.split()
def decode(raw,mapping,stage,menu_expected=False):
    assert len(raw)==len(FIELDS)*8
    o=dict(zip(FIELDS,struct.unpack('>'+'Q'*len(FIELDS),raw)))
    assert o['version']==1 and o['status']=={2:2,3:3,6:4}[stage]
    pages=sorted(set((mapping['observer_base']+0x10000*mapping['ee']+0x80*mapping[k+'_apid'])&~4095 for k in ['pon','volume']))
    assert o['map_count']==len(pages) and o['map_base0']==pages[0] and o['map_base1']==pages[-1]
    assert o['mapped_read_verified']==int(stage>=3) and o['protocol_installed']==int(stage==6)
    assert o['errors']==0 and o['pressed_mask']<=7 and o['released_mask']<=7 and o['last_raw']<=7
    if stage<6:assert not any(o[k] for k in ['polls','events','read_calls','reset_calls','pressed_mask','released_mask'])
    if stage==6 and menu_expected:assert o['polls']>0 and o['read_calls']>=o['events']
    return dict(**o,checkpoint_verified=True,physical_keys_verified=False,wait_for_key_implementation='EVT_NOTIFY_WAIT, sampled on demand; no periodic interrupt claim')
def decode_menu(raw,gop,frequency):
    assert len(raw)==(len(MENU_FIELDS)+len(GOP_FIELDS))*8
    w=struct.unpack('>'+'Q'*(len(raw)//8),raw);o=dict(zip(MENU_FIELDS,w));restore=dict(zip(GOP_FIELDS,w[len(MENU_FIELDS):]));o['restore']=restore
    assert o['version']==1 and o['status']==3 and o['hold_ticks']==frequency*40
    assert o['selected']<3 and o['pixels_changed']>0 and o['exit_reason'] in [1,2]
    if o['exit_reason']==1:assert (o['end']-o['start'])%(1<<64)>=o['hold_ticks']
    if o['exit_reason']==2:assert o['enter']>=1 and o['selected']==0
    assert o['wait_signals']>=o['up']+o['down']+o['enter']
    assert (restore['base'],restore['width'],restore['height'],restore['stride'])==(gop['base'],gop['width'],gop['height'],gop['stride'])
    assert restore['patch_width']==gop['width'] and restore['patch_height']==gop['height']
    assert restore['patch_restored']==gop['width']*gop['height'] and not any(restore[k] for k in ['active','backup','patch_mismatches','restore_fallback_used'])
    return dict(**o,menu_framebuffer_changed_and_restored=True,human_visibility_verified=False,physical_key_mapping_observation=dict(up=o['up'],down=o['down'],enter=o['enter']),generic_renderer='Pinned unchanged UniXNULib Ui/Font/Logo; counter-bounded port diagnostic controller')
