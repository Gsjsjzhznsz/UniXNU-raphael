#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Derive a stopped-QEMU sparse Data reader from this build's C++ DWARF."""
import argparse,json,subprocess
from pathlib import Path
from entry_probe import ROOT
from prepare_user_observer_abi import parse_dies,member

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--object',type=Path,required=True);p.add_argument('--inspection',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 inspection=json.loads(a.inspection.read_text());assert inspection['passed']
 nodes={}
 for name in ('NativeRamBlock','RamSparseDisk'):
  nodes.update(parse_dies(subprocess.check_output(['llvm-dwarfdump','--name='+name,'--show-children',a.object],text=True)))
 def typ(name):
  rows=[n for n in nodes.values() if n.get('name')==name and n['tag'] in ('DW_TAG_class_type','DW_TAG_structure_type') and 'byte_size' in n]
  assert len(rows)==1;return rows[0]
 block=typ('NativeRamBlock');sparse=typ('RamSparseDisk')
 fields={n:member(nodes,block,[n]) for n in ('memory','capacity','online','sparse','isBig')}
 sparse_fields={n:member(nodes,sparse,[n]) for n in ('pages','bytes','resident')}
 kernel=ROOT/inspection['artifact_directory']/('kernel.macho' if inspection.get('prelink_executed') else 'native-kernel.macho')
 symbols=[x.split() for x in subprocess.check_output(['llvm-nm','--defined-only',kernel],text=True).splitlines()]
 def address(test):
  rows=[int(x[0],16) for x in symbols if len(x)==3 and test(x[2])];assert len(rows)==1;return rows[0]
 report=dict(candidate_sha256=inspection['native_macho_sha256'],source_object=str(a.object.resolve().relative_to(ROOT)),provenance='Matching compiled C++ DWARF and frozen candidate defined symbols',fields=fields,sparse_fields=sparse_fields,object_bytes=block['byte_size'],vtable=address(lambda n:n=='__ZTV14NativeRamBlock')+16,io_entry=address(lambda n:n.startswith('__ZN14NativeRamBlock16doAsyncReadWrite')),handset_executed=False,guest_modified=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
