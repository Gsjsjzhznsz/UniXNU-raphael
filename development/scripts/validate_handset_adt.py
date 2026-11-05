#!/usr/bin/env python3
"""Check actual handset ADT generation and explicit ownership-input rejection."""
import argparse,datetime,json,struct,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from raphael_adt import make_adt,storage_properties
from inspect_device import read_fdt

def parse(raw,offset=0):
 count,children=struct.unpack_from('<2I',raw,offset);offset+=8;props={};nodes={}
 for _ in range(count):
  name=raw[offset:offset+32].split(b'\0')[0].decode();size=struct.unpack_from('<I',raw,offset+32)[0];offset+=36
  assert name not in props;props[name]=raw[offset:offset+size];offset+=(size+3)&~3
 for _ in range(children):
  child,offset=parse(raw,offset);name=child['props']['name'].rstrip(b'\0').decode();assert name not in nodes;nodes[name]=child
 return dict(props=props,nodes=nodes),offset

def validate_mmio_cells(tree,provenance):
 # XNU IODTGetCellCounts defaults to address=2,size=1. Our serialized Q words
 # require explicit 2/2 at each bus, as used by the pinned generic ADT writer.
 for bus in [tree,tree['nodes']['arm-io']]:
  assert all(bus['props'].get(key)==struct.pack('<I',2) for key in ['#address-cells','#size-cells'])
 io=tree['nodes']['arm-io'];ranges=io['props']['ranges'];assert len(ranges)==24
 child,physical,span=struct.unpack('<3Q',ranges);assert child==0 and physical>0 and span>0
 regs=io['nodes']['ufs']['props']['reg'];assert len(regs)==32
 values=struct.unpack('<4Q',regs)
 actual=[]
 for i in [0,2]:
  off,length=values[i:i+2];assert length>0 and off<span and length<=span-off
  actual.append((physical+off,length))
 assert actual==[tuple(v) for v in provenance['ufs_storage']['registers']]
 return actual

def main():
 p=argparse.ArgumentParser();p.add_argument('--fdt',type=Path,required=True);p.add_argument('--os-plan',type=Path,required=True);p.add_argument('--systemos-plan',type=Path,required=True);a=p.parse_args()
 out=ROOT/'evidence/private/handset-adt-host'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,mode=0o700)
 blob=a.fdt.read_bytes();plans={'OS':a.os_plan,'SystemOS':a.systemos_plan};checks=[]
 def check(name,body,rejected=False):
  try:body()
  except (AssertionError,KeyError,ValueError):assert rejected,name
  else:assert not rejected,name
  checks.append(name)
 path,provenance=make_adt(out,blob,{'base':0xc0000000,'bytes':0x10200000},19200000,0,True,plans)
 tree,end=parse(path.read_bytes());assert end==path.stat().st_size
 io=tree['nodes']['arm-io'];start,size,total=struct.unpack('<3Q',io['props']['ranges']);assert start==0
 ufs=io['nodes']['ufs'];regs=struct.unpack('<4Q',ufs['props']['reg']);absolute=[(regs[i]+size,regs[i+1]) for i in [0,2]]
 assert absolute==[tuple(v) for v in provenance['ufs_storage']['registers']]
 assert all(n+length<=total for n,length in [regs[:2],regs[2:]])
 assert ufs['props']['compatible']==b'unixnu,raphael-ufs-ro\0'
 assert ufs['props']['unixnu,os-extents']==a.os_plan.read_bytes() and ufs['props']['unixnu,systemos-extents']==a.systemos_plan.read_bytes()
 checks.append('serialized relative MMIO ranges, properties, both exact plans')
 check('XNU address/size cell widths resolve both exact MMIO resources',lambda:validate_mmio_cells(tree,provenance))
 import copy
 def malformed_cell(bus,key,value):
  altered=copy.deepcopy(tree);props=(altered if bus=='root' else altered['nodes']['arm-io'])['props']
  if value is None:props.pop(key)
  else:props[key]=struct.pack('<I',value)
  return validate_mmio_cells(altered,provenance)
 check('old omitted arm-io size declaration rejected',lambda:malformed_cell('io','#size-cells',None),True)
 check('wrong root address declaration rejected',lambda:malformed_cell('root','#address-cells',1),True)
 check('wrong arm-io size declaration rejected',lambda:malformed_cell('io','#size-cells',1),True)
 check('both media required',lambda:storage_properties(read_fdt(blob),{'OS':a.os_plan}),True)
 check('handset MMIO rejected from QEMU profile',lambda:make_adt(out,blob,{'base':0xc0000000,'bytes':0x10200000},19200000,0,False,plans),True)
 def altered(name,key,value):
  fdt=read_fdt(blob);n=next(n for n in fdt.walk() if n.name==name);n.properties[key]=value;return storage_properties(fdt,plans)
 check('HVC rejected',lambda:altered('psci','method',b'hvc\0'),True)
 check('SMMU resource name rejected',lambda:altered('apps-smmu@0x15000000','reg-names',b'unknown\0tcu-base\0'),True)
 check('SMMU clock dependency rejected',lambda:altered('apps-smmu@0x15000000','clocks',bytes(4)),True)
 check('secondary affinity duplicate rejected',lambda:altered('cpu@100','reg',bytes(8)),True)
 check('disabled UFS rejected',lambda:altered('ufshc@1d84000','status',b'disabled\0'),True)
 report=dict(passed=True,checks=checks,source_fdt_sha256=sha(blob),generator_sha256=sha((ROOT/'scripts/raphael_adt.py').read_bytes()),handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,checks=len(checks),report=str(out/'report.json')),indent=2))
if __name__=='__main__':main()
