#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Inspect a stopped QEMU's captured scratch Data; never reads handset partitions.
Use the workspace venv with pyfsapfs 20260921. Output remains private.
"""
import argparse,json,stat
from pathlib import Path
import pyfsapfs
from entry_probe import ROOT

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--observation',type=Path,required=True);a=p.parse_args()
 source=a.observation.resolve();assert source.is_relative_to(ROOT/'artifacts/native-xnu-qemu')
 d=json.loads(source.read_text());snapshot=d['data_ram_snapshot'];image=source.parent/snapshot['path']
 assert image.parent==source.parent and image.stat().st_size==snapshot['bytes']
 out=source.parent/'data-inspection';out.mkdir(exist_ok=False,mode=0o700)
 c=pyfsapfs.container();c.open(str(image));v=c.get_volume(0);entries=[];logs=[]
 def visit(entry,path):
  if entry is None:return
  row=dict(path=path,bytes=entry.size,mode=entry.file_mode);entries.append(row)
  if stat.S_ISDIR(entry.file_mode):
   for child in entry.sub_file_entries:
    assert child.name not in ('.','..') and '/' not in child.name
    visit(child,path+'/'+child.name)
  elif stat.S_ISREG(entry.file_mode) and (path.startswith('/logs/') or path.startswith('/log/') or path.startswith('/root/Library/Logs/MobileContainerManager/')) and entry.size<=4*1048576:
   content=entry.read(entry.size);target=out/'logs'/path.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);target.write_bytes(content)
   logs.append(dict(path=path,bytes=len(content),extracted=str(target.relative_to(source.parent))))
 visit(v.get_root_directory(),'')
 assert entries,'Captured APFS root was not readable'
 report=dict(source_observation=str(source.relative_to(ROOT)),scope=snapshot['scope'],apfs_metadata_readable=True,entries=entries,private_logs=logs,filesystem_modified=False,persistence_verified=False,handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(artifact_directory=str(out.relative_to(ROOT)),entries=len(entries),private_logs=logs,persistence_verified=False),indent=2))
if __name__=='__main__':main()
