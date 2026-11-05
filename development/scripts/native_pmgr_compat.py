#!/usr/bin/env python3
"""Opt in to the original PMGR nub's audited unsupported-AON diagnostic ABI."""
import argparse,datetime,json,struct,sys
from pathlib import Path
from entry_probe import ROOT,sha
KEY='unixnu,diagnostic-pmgr-nub'
def qualify_kernel(path):
 from native_early import image
 raw=path.read_bytes();segments,symbols=image(raw)
 assert all(n in symbols for n in ['_raphael_native_pmgr_run','_raphael_native_pmgr_record']), 'Explicit PMGR diagnostic ABI needs its linked implementation and telemetry'
 def read(va,n):
  matches=[s for s in segments if s['virtual']<=va and va+n<=s['virtual']+s['file_bytes']]
  assert len(matches)==1
  t=matches[0];at=t['offset']+va-t['virtual'];return raw[at:at+n]
 # The fixed OS ABI is audited in the pinned audit-amfi-pmgr-contract.py.
 contracts={0xfffffff004a24adc:(0xf9404400,0xb4000080,0xf9400008,0xf9450101,0xd61f0020,0x12800000,0xd65f03c0),
            0xfffffff004a230ec:(0xf9404400,0xb4000080,0xf9400008,0xf9450502,0xd61f0040,0xd65f03c0),
            0xfffffff004a20fbc:(0x12800000,0xd65f03c0,0xd65f03c0)}
 for va,words in contracts.items():
  assert struct.unpack('<'+'I'*len(words),read(va,4*len(words)))==words, 'Original PMGR unsupported-AON instructions changed'
 return dict(original_read='UINT32_MAX with no AON provider',original_write='returns with no AON provider',hardware_mmio=False,original_instruction_contracts_checked=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--adt',type=Path,required=True);a=p.parse_args()
 from native_watchdog_budget import from_adt
 assert from_adt(a.adt.read_bytes()), 'Only the explicitly budgeted handset diagnostic ADT is eligible'
 from validate_handset_adt import parse
 tree,end=parse(a.adt.read_bytes());assert end==a.adt.stat().st_size
 provenance=json.loads((a.adt.parent/'adt-provenance.json').read_text())
 assert provenance['handset_parameters'] and 'vmm-present' not in tree['nodes']['defaults']['props']
 props=tree['nodes']['chosen']['props'];assert KEY not in props;props[KEY]=struct.pack('<I',1)
 sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'));from unixnu.devicetree import node
 def encode(t):return node(t['props']['name'].rstrip(b'\0').decode(),[(k,v) for k,v in t['props'].items() if k!='name'],[encode(c) for c in t['nodes'].values()])
 out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-pmgr-compat');out.mkdir(parents=True,mode=0o700)
 raw=encode(tree);path=out/'kernel.macho.adt';path.write_bytes(raw)
 provenance.update(adt_sha256=sha(raw),adt_bytes=len(raw),diagnostic_pmgr_nub=dict(mode=1,source_adt=str(a.adt),aon_policy='Original target unsupported semantics: read UINT32_MAX, write no-op; original nub own AON provider remains null',hardware_power_management_verified=False))
 (out/'adt-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 print(out)
if __name__=='__main__':main()
