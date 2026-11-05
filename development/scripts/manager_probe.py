#!/usr/bin/env python3
"""Validate actual UniXNURun execution under the physical TimerArch."""
import struct
FIELDS='version status start_counter end_counter frequency timeout'.split()
def decode(raw,stage,payload,frequency,visible=False,manual=False):
 assert len(raw)==48
 r=dict(zip(FIELDS,struct.unpack('>6Q',raw)))
 assert r['version']==1 and r['status']==(2 if stage==6 else 1)
 assert r['frequency']==frequency and r['timeout']==(6 if manual else 2)
 assert payload['read_only_payload_checkpoint_verified']
 if stage<6:assert r['start_counter']==r['end_counter']==0
 else:
  assert payload['full_unixnu_invocation_verified'] and payload['crc_before']==payload['crc_after']
  assert r['start_counter']>0 and r['start_counter']<r['end_counter']
  assert (1 if manual else frequency*18//10)<=r['end_counter']-r['start_counter']<=frequency*(8 if manual else 5)
 return dict(**r,passed=True,complete_unixnu_manager_executed=stage==6,countdown_verified=stage==6 and not manual,headless_synthetic_config_only=not visible,darwin_boot_executed=False,xnu_executed=False)
