#!/usr/bin/env python3
"""Reject partial UI transaction records and QEMU absence as handset success."""
import json,struct
from entry_probe import ROOT,sha
from manager_ui import FIELDS,decode

def main():
 vals=[1,4,0x90000000,1080,2340,4320,1080*2340,1,1080*2340,0,1,1,0,0,0,1]
 wire=struct.pack('>16Q',*vals);gop=dict(protocol_installed=1,mapped_read_verified=1,base=vals[2],width=1080,height=2340,stride=4320)
 assert decode(wire,6,gop)['manager_framebuffer_changed_and_restored'];cases=['complete handset-shape framebuffer transaction']
 def reject(label,raw,stage=6,g=gop,q=False):
  try:decode(raw,stage,g,qemu_model=q)
  except (AssertionError,ValueError,KeyError):cases.append('reject '+label)
  else:raise AssertionError(label)
 for key,value in dict(version=0,status=3,base=0,width=1,height=1,stride=1,frame_pixels=1,pixels_changed=0,pixels_restored=1,mismatches=1,input_ready=0,query_verified=0,active=1,backup=1,fallback=1,pixel_format=3).items():
  v=vals.copy();v[FIELDS.index(key)]=value;reject(key,struct.pack('>16Q',*v))
 reject('short',wire[:-8]);reject('long',wire+b'0');reject('wrong phase',wire,stage=2)
 qwire=struct.pack('>16Q',1,5,*([0]*14));assert decode(qwire,6,qemu_model=True)['qemu_missing_hardware_model'];cases.append('explicit QEMU missing-hardware model')
 reject('QEMU model cannot be accepted as handset',qwire)
 for stage in [2,3]:assert decode(struct.pack('>16Q',1,1,*([0]*14)),stage)['passed'];cases.append('pre-DXE phase '+str(stage))
 v=vals.copy();v[7]=vals[6]+1;reject('changed pixels exceed frame',struct.pack('>16Q',*v))
 report=dict(passed=True,case_count=len(cases),cases=cases,decoder_sha256=sha((ROOT/'scripts/manager_ui.py').read_bytes()),runner_sha256=sha(__import__('pathlib').Path(__file__).read_bytes()),handset_executed=False)
 (ROOT/'UniXNU-raphael/evidence/manager-ui-wire-host.json').write_text(json.dumps(report,indent=2)+'\n');print(len(cases),'UI wire and phase checks passed')
if __name__=='__main__':main()
