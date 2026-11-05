#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Extract observer ABI from the matching compiled XNU object, not guessed offsets."""
import argparse, datetime as dt, hashlib, json, re, subprocess, tempfile
from pathlib import Path
from entry_probe import ROOT

def parse_dies(raw):
 nodes = {}; stack = []; current = None
 for line in raw.splitlines():
  m = re.match(r"(0x[0-9a-f]+):( +)(DW_TAG_\w+|NULL)", line)
  if m:
   ident, spaces, tag = m.groups(); depth = len(spaces)
   while stack and stack[-1]['depth'] >= depth: stack.pop()
   if tag == 'NULL': current = None; continue
   current = dict(id=ident, depth=depth, tag=tag, children=[])
   nodes[ident] = current
   if stack: stack[-1]['children'].append(current)
   stack.append(current); continue
  if current:
   m = re.search(r'DW_AT_name\s+\("([^"\n]*)"\)', line)
   if m: current['name'] = m[1]
   m = re.search(r'DW_AT_(type|data_member_location|byte_size)\s+\((0x[0-9a-f]+)', line)
   if m: current[m[1]] = m[2] if m[1] == 'type' else int(m[2], 16)
 return nodes

def member(nodes, typ, path):
 candidates = []
 for child in typ['children']:
  if child['tag'] != 'DW_TAG_member' or 'data_member_location' not in child: continue
  offset = child['data_member_location']
  if child.get('name') == path[0]:
   value = offset if len(path) == 1 else offset + member(nodes, nodes[child['type']], path[1:])
   candidates.append(value)
  elif not child.get('name'):
   try: candidates.append(offset + member(nodes, nodes[child['type']], path))
   except KeyError: pass
 if len(candidates) != 1: raise KeyError((typ.get('name'), path, candidates))
 return candidates[0]

def main():
 a = argparse.ArgumentParser(); a.add_argument('--inspection', type=Path, required=True); a.add_argument('--object', type=Path, required=True); a=a.parse_args()
 inspection=json.loads(a.inspection.read_text()); assert inspection['passed']
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=ROOT/'artifacts'))
 nodes={}
 for name in ['proc','arm_saved_state','arm_saved_state64','arm_state_hdr']:
  raw=subprocess.check_output(['llvm-dwarfdump','--name='+name,'--show-children',a.object],text=True)
  (out/(name+'.dwarf.txt')).write_text(raw); nodes.update(parse_dies(raw))
 def typ(name):
  found=[n for n in nodes.values() if n.get('name')==name and n['tag']=='DW_TAG_structure_type']
  assert len(found)==1,(name,len(found));return found[0]
 proc=typ('proc'); state=typ('arm_saved_state')
 offsets={name:member(nodes,state,['uss','ss_64',name]) for name in ['x','fp','lr','sp','pc','cpsr','far','esr']}
 report=dict(passed=True, artifact_directory=str(out.relative_to(ROOT)), candidate_sha256=inspection['native_macho_sha256'],
  source_object=str(a.object.resolve().relative_to(ROOT)), source_object_sha256=hashlib.sha256(a.object.read_bytes()).hexdigest(),
  provenance='llvm-dwarfdump of this XNU build; includes anonymous member parent offsets',
  proc=dict(bytes=proc['byte_size'],pid=member(nodes,proc,['p_pid']),comm=member(nodes,proc,['p_comm'])),
  saved_state=dict(bytes=state['byte_size'],**offsets))
 log_object=a.object.parent/'subr_log.o'
 if log_object.is_file():
  raw=subprocess.check_output(['llvm-dwarfdump','--name=msgbuf','--show-children',log_object],text=True)
  (out/'msgbuf.dwarf.txt').write_text(raw);log_nodes=parse_dies(raw)
  found=[n for n in log_nodes.values() if n.get('name')=='msgbuf' and n['tag']=='DW_TAG_structure_type'];assert len(found)==1
  typ=found[0]
  report['msgbuf']=dict(bytes=typ['byte_size'],magic=0x063061,fields={name:member(log_nodes,typ,[name]) for name in ['msg_magic','msg_size','msg_bufx','msg_bufr','msg_bufc']},source_object=str(log_object.resolve().relative_to(ROOT)),source_object_sha256=hashlib.sha256(log_object.read_bytes()).hexdigest())
 report['bsd_arguments']={}
 for name,object_name,fields in [('write_args','sys_generic.o',{'fd':4,'cbuf':8,'nbyte':8}),('exit_args','kern_exit.o',{'rval':4}),('execve_args','kern_exec.o',{'fname':8}),('posix_spawn_args','kern_exec.o',{'path':8})]:
  source_object=a.object.parent/object_name
  raw=subprocess.check_output(['llvm-dwarfdump','--name='+name,'--show-children',source_object],text=True)
  (out/(name+'.dwarf.txt')).write_text(raw);argument_nodes=parse_dies(raw)
  found=[n for n in argument_nodes.values() if n.get('name')==name and n['tag']=='DW_TAG_structure_type'];assert len(found)==1
  argument_type=found[0]
  layout={name:dict(offset=member(argument_nodes,argument_type,[name]),bytes=size) for name,size in fields.items()}
  assert all(value['offset']+value['bytes']<=argument_type['byte_size'] for value in layout.values())
  report['bsd_arguments'][name]=dict(bytes=argument_type['byte_size'],fields=layout,source_object=str(source_object.resolve().relative_to(ROOT)),source_object_sha256=hashlib.sha256(source_object.read_bytes()).hexdigest())
 # Process/thread snapshot layouts are also derived from this exact build.
 # They let a failed display run identify an actual blocked dependency instead
 # of interpreting the absence of one sampled SVC as a missing process.
 objects=a.object.parents[2]
 def structure(source,name):
  raw=subprocess.check_output(['llvm-dwarfdump','--name='+name,'--show-children',source],text=True)
  (out/(name+'.snapshot.dwarf.txt')).write_text(raw);n=parse_dies(raw)
  matches=[v for v in n.values() if v.get('name')==name and v['tag']=='DW_TAG_structure_type' and 'byte_size' in v]
  assert len(matches)==1,(name,len(matches));return n,matches[0]
 snapshot={}
 for label,source,name,fields in [
  ('proc',a.object,'proc',{'next':['p_list','le_next'],'ro':['p_proc_ro'],'stat':['p_stat']}),
  ('proc_ro',objects/'bsd/DEVELOPMENT/kern_proc.o','proc_ro',{'task':['pr_task'],'proc':['pr_proc']}),
  ('task',objects/'osfmk/DEVELOPMENT/task.o','task',{'threads':['threads'],'thread_count':['thread_count'],'shared_region':['shared_region'],'map':['map']}),
  ('shared_region',objects/'osfmk/DEVELOPMENT/vm_shared_region.o','vm_shared_region',{'slide':['sr_slide'],'base':['sr_base_address'],'size':['sr_size']}),
  ('vm_map',objects/'osfmk/DEVELOPMENT/vm_map.o','_vm_map',{'pmap':['pmap']}),
  ('pmap',objects/'osfmk/DEVELOPMENT/pmap.o','pmap',{'tte':['tte'],'ttep':['ttep'],'min':['min'],'max':['max']}),
  ('page_table_attr',objects/'osfmk/DEVELOPMENT/pmap.o','page_table_attr',{'root_level':['pta_root_level'],'max_level':['pta_max_level'],'page_size':['pta_page_size']}),
  ('thread',objects/'osfmk/DEVELOPMENT/thread.o','thread',{'task_links':['task_threads'],'ro':['t_tro'],'state':['state'],'wait_event':['wait_event'],'continuation':['continuation'],'machine':['machine']}),
  ('thread_ro',objects/'osfmk/DEVELOPMENT/thread.o','thread_ro',{'proc':['tro_proc'],'task':['tro_task']}),
  ('machine_thread',objects/'osfmk/DEVELOPMENT/thread.o','machine_thread',{'upcb':['upcb'],'kstackptr':['kstackptr']}),
  ('kernel_state',objects/'osfmk/DEVELOPMENT/pcb.o','arm_kernel_saved_state',{'fp':['fp'],'lr':['lr'],'sp':['sp']}),
  ('queue_entry',objects/'osfmk/DEVELOPMENT/thread.o','queue_entry',{'next':['next'],'prev':['prev']})]:
  n,t=structure(source,name)
  snapshot[label]=dict(bytes=t['byte_size'],fields={k:member(n,t,path) for k,path in fields.items()},source_object=str(source.resolve().relative_to(ROOT)),source_object_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
 report['process_snapshot']=snapshot
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
