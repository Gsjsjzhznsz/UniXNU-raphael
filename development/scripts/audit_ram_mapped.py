#!/usr/bin/env python3
"""Audit mapped-reader code, immutable primary sources and both real QEMU phases."""
import argparse,json,re,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from ram_mapped_probe import verify_storage
from audit_ram_read import inspect_load

def inspect_translation(build):
 directory=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
 mp=(directory/'RaphaelSec.dll.map').read_text();dis=subprocess.check_output(['llvm-objdump','-d',str(directory/'RaphaelSec.efi')],text=True)
 def body(name):
  match=re.search(r'(?m)^([0-9a-f]+)\s+.*\s'+name+'$',mp);assert match,name
  rva=int(match[1],16);instructions=[]
  for m in re.finditer(r'(?m)^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$',dis):
   if int(m[1],16)<rva:continue
   instructions.append((int(m[1],16),int(m[2],16),m[3]))
   if m[3].strip()=='ret':break
  return rva,instructions
 at,query=body('TranslateMappedRam');restore_at,restore=body('RaphaelRestoreMappedPar')
 text='\n'.join(i[2] for i in query);restore_text='\n'.join(i[2] for i in restore)
 assert text.count('at\ts1e1r, x0')==text.count('at\ts1e1w, x0')==1
 assert not re.search(r'\[x0(?:,|\])',text)
 assert sum(i[1]==0xd5033fdf for i in query)>=2
 assert sum('msr\tPAR_EL1' in i[2] for i in restore)==1 and any(i[1]==0xd5033fdf for i in restore)
 calls=[i for i in query if i[2].startswith('bl\t')]
 assert len(calls)==1 and int(re.search(r'0x([0-9a-f]+)',calls[0][2])[1],16)==restore_at
 return dict(query_rva=at,restore_rva=restore_at,s1e1r_queries=1,s1e1w_queries=1,permission_query_has_no_candidate_load_or_store=True,
             original_par_restored_with_isb=True,query_instructions=len(query),restore_instructions=len(restore))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage2',required=True,type=Path);ap.add_argument('--stage3',required=True,type=Path);a=ap.parse_args()
 reports={};inputs=None
 for stage,path in [(2,a.stage2.resolve()),(3,a.stage3.resolve())]:
  q=json.loads(path.read_text());assert q['qemu_passed'] and q['structure_checked'] and q['ram_mapped_probe'] and q['stop_stage']==stage
  assert q['executions']['normal']['ram_mapped']['passed']
  if stage==3:assert q['executions']['load_site_udf']['passed'] and not q['executions']['load_site_udf']['real_data_abort']
  if inputs is not None:assert inputs==q['source_inputs']
  inputs=q['source_inputs']
  for item in q['source_inputs']+q['upstream_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
  assert q['ram_mapped_decoder_sha256']==sha((ROOT/'scripts/ram_mapped_probe.py').read_bytes())
  reports[str(stage)]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
 primary=[]
 for repository,revision,names in [
  ('sources/mu_basecore','cfb93724a06ff86ff5ba971413368a7809ee42a5',['MdePkg/Include/Library/ArmLib.h','MdePkg/Include/AArch64/AArch64Mmu.h','UefiCpuPkg/Library/ArmMmuLib/AArch64/ArmMmuLibCore.c']),
  ('sources/apple-xnu-native','d8b80295118ef25ac3a784134bcf95cd8e88109f',['osfmk/arm64/machine_routines_asm.s','osfmk/arm64/proc_reg.h'])]:
  for name in names:
   data=(ROOT/repository/name).read_bytes();assert data==subprocess.check_output(['git','-C',str(ROOT/repository),'show',revision+':'+name])
   primary.append(dict(repository=repository,revision=revision,path=name,sha256=sha(data)))
 source_names=['UniXNU-raphael/package/firmware/RaphaelPkg/Sec/'+name for name in ['RamRead.c','RamReadAdapter.c','RamMapped.c','RamMappedAdapter.c','Sec.c']]+['UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelRamMapped.h']
 result=dict(passed=True,qemu_reports=reports,source_inputs=[dict(path=name,sha256=sha((ROOT/name).read_bytes())) for name in source_names],
  mapped_load=inspect_load(a.stage3.resolve().parent,function='ReadMappedRam64'),pre_map_load=inspect_load(a.stage3.resolve().parent),
  translation=inspect_translation(a.stage3.resolve().parent),storage=verify_storage(a.stage3.resolve().parent),
  primary_sources=primary,decoder_sha256=sha((ROOT/'scripts/ram_mapped_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),
  fatal_mapped_load_udf_return_verified=True,real_data_abort_verified=False,handset_executed=False,allocator_enabled=False)
 assert result['mapped_load']['load_rva']!=result['pre_map_load']['load_rva']
 target=ROOT/'UniXNU-raphael/evidence/ram-mapped-source-audit.json';target.write_text(json.dumps(result,indent=2)+'\n');print(target);print(json.dumps(result['translation'],indent=2))
if __name__=='__main__':main()
