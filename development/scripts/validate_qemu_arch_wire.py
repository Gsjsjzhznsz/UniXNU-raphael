#!/usr/bin/env python3
"""Check real architecture records independently and reject corrupt provenance."""
import copy
import json
import re
import struct
from pathlib import Path
from entry_probe import ROOT,sha
from qemu_arch_probe import FIELDS,decode,parse_resources,analyze_tree,read_fdt
from inspect_device import Error,node_path


def main():
 selected={};checks=[]
 for path in sorted((ROOT/'artifacts/sec-dxe-qemu').glob('*/report.json')):
  report=json.loads(path.read_text())
  if not report.get('qemu_arch_test') or not report.get('qemu_passed'):continue
  stage=6 if report['stop_stage']==4 else report['stop_stage']
  match=re.search(rb'QEMU_ARCH_WIRE ([0-9a-f]+)',(path.parent/'serial.log').read_bytes());assert match
  blob=(path.parent/'qemu-virt.dtb').read_bytes();assert sha(blob)==report['qemu_arch']['dtb_sha256']
  resources=parse_resources(blob);assert resources==report['qemu_arch']['resources']
  raw=bytes.fromhex(match[1].decode());assert decode(raw,stage,resources)['passed']
  selected[stage]=(path,raw,resources,blob)
 assert set(selected)=={2,3,6}
 for stage,(path,raw,_,_) in sorted(selected.items()):
  checks.append(dict(name='actual stage '+str(stage),passed=True,source=str(path.relative_to(ROOT)),wire_sha256=sha(raw)))
 _,base,resources,blob=selected[6]
 corruptions={'version':2,'status':2,'frequency':0,'saved_ctl':8,'cpu_protocol':0,'interrupt_protocol':0,'timer_protocol':0,
  'period':0,'relative_fired':0,'relative_ticks':0,'periodic_count':0,'periodic_ticks':0,'cancel_stable':0,
  'manager_completed':0,'manager_ticks':0,'sources_disabled':0,'timer_disabled':0,'timer_restored':0,'cval_after':0xffffffffffffffff,'ctl_after':8}
 corruptions.update({name:value+1 for name,value in resources.items()})
 for field,value in corruptions.items():
  damaged=bytearray(base);struct.pack_into('>Q',damaged,FIELDS.index(field)*8,value)
  try:decode(damaged,6,resources)
  except AssertionError:checks.append(dict(name='reject corrupted '+field,passed=True))
  else:raise AssertionError(field)
 for name,raw,stage in [('truncated',base[:-1],6),('trailing',base+b'\0',6),('late at early stage',base,3),('legacy BRK stage',base,4)]:
  try:decode(raw,stage,resources)
  except AssertionError:checks.append(dict(name='reject '+name,passed=True))
  else:raise AssertionError(name)
 root=read_fdt(blob);paths={node_path(n):n for n in root.walk()}
 gic=next(p for p,n in paths.items() if 'arm,gic-v3' in n.strings('compatible'))
 timer=next(p for p,n in paths.items() if 'arm,armv8-timer' in n.strings('compatible'))
 cells=lambda *v:struct.pack('>'+'I'*len(v),*v)
 ints=paths[timer].cells('interrupts')
 mutations=[('root board','/','compatible',b'phone,unknown\0'),('root cells','/','#address-cells',cells(1)),
  ('root parent','/','interrupt-parent',cells(0x123)),('disabled GIC',gic,'status',b'disabled\0'),
  ('GIC cells',gic,'#interrupt-cells',cells(4)),('multiple GICR',gic,'#redistributor-regions',cells(2)),
  ('bus translation',gic,'ranges',cells(1,2,3)),('zero GIC range',gic,'reg',cells(0,0x8000000,0,0,0,0x80a0000,0,0xf60000)),
  ('overlap GIC range',gic,'reg',cells(0,0x8000000,0,0x10000,0,0x8000000,0,0x10000)),
  ('misaligned GIC range',gic,'reg',cells(0,0x8000001,0,0x10000,0,0x80a0000,0,0xf60000)),
  ('disabled timer',timer,'status',b'disabled\0'),('override timer parent',timer,'interrupt-parent',cells(0x8002)),
  ('extended timer',timer,'interrupts-extended',b''),('truncated interrupts',timer,'interrupts',cells(*ints[:-1]))]
 for name,index,value in [('SPI',0,0),('PPI range',1,16),('trigger',2,8),('duplicate PPI',1,ints[4])]:
  changed=list(ints);changed[index]=value;mutations.append((name,timer,'interrupts',cells(*changed)))
 for name,path,key,value in mutations:
  tree=copy.deepcopy(root);node=next(n for n in tree.walk() if node_path(n)==path);node.properties[key]=value
  try:analyze_tree(tree)
  except (AssertionError,Error):checks.append(dict(name='reject resource '+name,passed=True))
  else:raise AssertionError(name)
 report=dict(passed=True,command='python3 scripts/validate_qemu_arch_wire.py',check_count=len(checks),checks=checks,
  decoder_sha256=sha((ROOT/'scripts/qemu_arch_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),
  handset_executed=False,gic_full_restore_tested=False,xnu_executed=False)
 out=ROOT/'UniXNU-raphael/evidence/qemu-arch-wire-host.json';out.write_text(json.dumps(report,indent=2)+'\n')
 print(str(len(checks))+' architecture wire and provenance checks passed');print(out)

if __name__=='__main__':main()
