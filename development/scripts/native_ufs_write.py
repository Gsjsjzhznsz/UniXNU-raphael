#!/usr/bin/env python3
"""Bind a private native write diagnostic to its exact compiled single-block policy."""
import struct
from entry_probe import ROOT
from ufs_write_probe import validate_manifest

def qualify_kernel(path,metadata):
 from native_early import image
 raw=path.read_bytes();segments,symbols=image(raw)
 policy=ROOT/metadata['policy'];assert validate_manifest(policy)==metadata
 expected=policy.read_bytes()
 def read(va,n):
  matches=[s for s in segments if s['virtual']<=va and va+n<=s['virtual']+s['file_bytes']]
  assert len(matches)==1
  s=matches[0];at=s['offset']+va-s['virtual'];return raw[at:at+n]
 assert read(symbols['_raphael_ufs_write_probe_policy'],8256)==expected,'Linked native policy differs from allocation'
 caller=symbols['_raphael_native_root_observer'];target=symbols['_raphael_ufs_diagnostic_write_once']
 hits=0
 for i,(w,) in enumerate(struct.iter_unpack('<I',read(caller,0x800))):
  if w&0xfc000000!=0x94000000:continue
  imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm
  hits+=caller+i*4+imm*4==target
 assert hits==1,'Expected one explicit normal-thread observer call'
 assert all(k in symbols for k in ['_raphael_ufs_diagnostic_write','_raphael_ufs_write_probe_record','_raphael_ufs_write_request_record'])
 return dict(verified=True,exact_policy_bytes=8256,observer_calls=hits,policy_sha256=metadata['policy_sha256'],handset_executed=False)

def verify_result(probe,metadata):
 assert probe and probe['immediate_readback_verified'] and probe['permission_revoked']
 assert probe['stages']==63 and probe['result']==probe['ocs']==0
 w=metadata['write_window'];assert probe['lba']==w['lba'] and probe['lun_blocks']==w['lun_blocks']
 caller=probe['caller'];assert caller['finished'] and caller['result']==0 and caller['stages']==63
 return True
