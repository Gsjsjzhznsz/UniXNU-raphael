#!/usr/bin/env python3
"""Exercise actual current FDT resolution and reject broken resource/IRQ graphs."""
import argparse
import copy
import json
from pathlib import Path
import struct

from derive_interrupt_contract import (ROOT, analyze_tree, android_timer_observation,
    crosscheck_reference, node_path, read_fdt, source_audit, Error, sha)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('collection',type=Path);args=parser.parse_args()
    raw=(args.collection/'live.dtb').read_bytes();root=read_fdt(raw)
    facts=analyze_tree(root);sources,blobs=source_audit();crosscheck_reference(facts,blobs)
    observed=android_timer_observation((args.collection/'interrupts.txt').read_text(),facts)
    assert [entry['intid'] for entry in facts['timer_interrupts']]==[17,18,19,16]
    assert observed['selected_role']=='virtual' and observed['intid']==19
    checks=[dict(name='fresh FDT graph and fixed reference',passed=True),
            dict(name='Android virtual timer observation agrees',passed=True)]
    paths={node_path(node):node for node in root.walk()}
    timer_path=facts['timer_node'];pdc_path=facts['interrupt_chain'][0]['node'];gic_path=facts['gic_node']
    cpu_paths=[path for path,node in paths.items() if node.properties.get('device_type')==b'cpu\0']
    cells=lambda *values:struct.pack('>'+'I'*len(values),*values)
    def node(tree,path):return next(item for item in tree.walk() if node_path(item)==path)
    def change(tree,path,key,value):node(tree,path).properties[key]=value
    def reject(name,mutate):
        tree=copy.deepcopy(root);mutate(tree)
        try:analyze_tree(tree)
        except (ValueError,Error):checks.append(dict(name=name,passed=True))
        else:raise AssertionError('accepted '+name)
    gic_handle=paths[gic_path].cells('phandle')[0]
    pdc_handle=paths[pdc_path].cells('phandle')[0]
    original=paths[timer_path].cells('interrupts')
    def interrupt_value(index,value):
        data=list(original);data[index]=value;return cells(*data)
    mutations=[
      ('duplicate phandle',gic_path,'phandle',cells(pdc_handle)),
      ('conflicting phandle alias',gic_path,'linux,phandle',cells(gic_handle+12345)),
      ('unresolved timer parent',timer_path,'interrupt-parent',cells(0xfffffffe)),
      ('provider cycle',pdc_path,'interrupt-parent',cells(pdc_handle)),
      ('unknown intermediary',pdc_path,'compatible',b'vendor,unknown\0'),
      ('disabled provider',pdc_path,'status',b'disabled\0'),
      ('invalid interrupt cells',pdc_path,'#interrupt-cells',cells(4)),
      ('unreviewed extended interrupts',timer_path,'interrupts-extended',b''),
      ('truncated timer cells',timer_path,'interrupts',cells(*original[:-1])),
      ('timer SPI specifier',timer_path,'interrupts',interrupt_value(0,0)),
      ('PPI out of range',timer_path,'interrupts',interrupt_value(1,16)),
      ('aliased timer IRQs',timer_path,'interrupts',interrupt_value(1,original[4])),
      ('edge timer trigger',timer_path,'interrupts',interrupt_value(2,1)),
      ('unknown timer flags',timer_path,'interrupts',interrupt_value(2,0x10f08)),
      ('zero frequency',timer_path,'clock-frequency',cells(0)),
      ('malformed frequency',timer_path,'clock-frequency',cells(19200000,19200000)),
      ('multiple redistributor regions',gic_path,'#redistributor-regions',cells(2)),
      ('zero redistributor stride',gic_path,'redistributor-stride',cells(0,0)),
      ('misaligned redistributor stride',gic_path,'redistributor-stride',cells(0,0x21000)),
      ('overlapping GIC windows',gic_path,'reg',cells(0x17a00000,0x10000,0x17a00000,0x100000)),
      ('no enabled timer',timer_path,'status',b'disabled\0'),
      ('duplicate CPU affinity',cpu_paths[1],'reg',paths[cpu_paths[0]].properties['reg']),
    ]
    for name,path,key,value in mutations:reject('reject '+name,lambda tree,p=path,k=key,v=value:change(tree,p,k,v))
    reject('reject missing bus translation',lambda tree:node(tree,'/soc').properties.pop('ranges'))
    def duplicate_timer(tree):
        original_node=node(tree,timer_path);other=copy.copy(original_node)
        other.properties=dict(original_node.properties);other.name='timer-duplicate'
        other.children=[];other.parent.children.append(other)
    reject('reject ambiguous timer selection',duplicate_timer)
    def disable_cpus(tree):
        for path in cpu_paths:change(tree,path,'status',b'disabled\0')
    reject('reject missing enabled CPUs',disable_cpus)
    bad_rows=['', '4: 1 2 PDC-GIC 20 Level arch_timer',
              '4: 1 2 PDC-GIC 19 Level arch_timer\n5: 2 3 PDC-GIC 19 Level arch_timer']
    for index,text in enumerate(bad_rows):
        try:android_timer_observation(text,facts)
        except ValueError:checks.append(dict(name='reject invalid runtime IRQ row '+str(index),passed=True))
        else:raise AssertionError('runtime row')
    wrong=copy.deepcopy(facts);wrong['frequency']+=1
    try:crosscheck_reference(wrong,blobs)
    except ValueError:checks.append(dict(name='reject live/reference disagreement',passed=True))
    else:raise AssertionError('reference mismatch')
    result=dict(passed=True,check_count=len(checks),checks=checks,live_fdt_sha256=sha(raw),
      resolver_sha256=sha((ROOT/'scripts/derive_interrupt_contract.py').read_bytes()),
      runner_sha256=sha(Path(__file__).read_bytes()),mmio_accessed=False,handset_rebooted=False,
      command='python3 scripts/validate_interrupt_contract.py '+str(args.collection))
    out=ROOT/'UniXNU-raphael/evidence/interrupt-contract-host.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(str(len(checks))+' interrupt contract checks passed');print(out)


if __name__=='__main__':main()
