#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Reproducible current-device UFS resource inventory; reads supplied files only."""
import argparse,json
from pathlib import Path
from inspect_device import read_fdt,registers,physical,node_path
from entry_probe import ROOT
from ufs_handoff import resources

def inspect(blob):
 root=read_fdt(blob);res=resources(blob);host=next(n for n in root.walk() if node_path(n)==res['node']);handles={}
 for n in root.walk():
  value=n.properties.get('phandle',n.properties.get('linux,phandle'))
  if value:
   assert len(value)==4;h=int.from_bytes(value,'big');assert h not in handles;handles[h]=n
 def node(n):
  ranges=[]
  if 'reg' in n.properties:
   for base,size in registers(n):ranges.append(dict(base=physical(n.parent,base,size),bytes=size,source=node_path(n)+':reg'))
  return dict(node=node_path(n),compatible=n.strings('compatible') if 'compatible' in n.properties else [],registers=ranges)
 def specs(key,cellkey,nameskey):
  if key not in host.properties:return []
  values=host.cells(key);names=host.strings(nameskey) if nameskey in host.properties else [];out=[];i=0
  while i<len(values):
   provider=handles[values[i]];i+=1;nc=provider.cells(cellkey);assert len(nc)==1 and nc[0]<=8 and i+nc[0]<=len(values)
   out.append(dict(name=names[len(out)] if names else None,provider=node(provider),arguments=values[i:i+nc[0]],source=node_path(host)+':'+key));i+=nc[0]
  assert not names or len(names)==len(out)
  return out
 supplies=[]
 for key,value in host.properties.items():
  if key.endswith('-supply'):
   assert len(value)==4;supplies.append(dict(name=key,provider=node(handles[int.from_bytes(value,'big')]),source=node_path(host)+':'+key))
 result=dict(scope='Current Android FDT resource declaration only; not native readiness',controller=node(host),register_names=host.strings('reg-names'),interrupt_cells=host.cells('interrupts'),interrupt_source=node_path(host)+':interrupts',clocks=specs('clocks','#clock-cells','clock-names'),phys=specs('phys','#phy-cells','phy-names'),resets=specs('resets','#reset-cells','reset-names'),supplies=supplies,iommus_declared='iommus' in host.properties,unknown=['UFS stream ID/routing and cold initialization ownership','Native DMA visibility and controller takeover','Root/Data allocation and write recovery policy'])
 result['controller']['properties']={key:value.hex() for key,value in host.properties.items() if key.startswith('vcc') or key in ['lanes-per-direction','freq-table-hz','dma-coherent']}
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fdt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();f=a.fdt.resolve();assert f.is_relative_to(ROOT/'evidence/private')
 d=inspect(f.read_bytes());d['input']=str(f.relative_to(ROOT));lock=json.loads((ROOT/'sources.lock.json').read_text());d['primary_source']=next(dict(name=v['name'],revision=v['revision'],path='arch/arm64/boot/dts/qcom/sm8150.dtsi') for v in lock['sources'] if v['name']=='Xiaomi_Kernel_OpenSource')
 a.output.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(passed=True,controller=d['controller']['registers'],clocks=len(d['clocks']),phys=len(d['phys']),resets=len(d['resets']),iommus_declared=d['iommus_declared'])))
if __name__=='__main__':main()
