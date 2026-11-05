#!/usr/bin/env python3
"""Audit final linked candidate-read instructions, result storage and primary PA map."""
import argparse,json,re,struct,subprocess
from entry_probe import ROOT,sha
from ram_read_probe import verify_result_storage

def inspect_load(build,function="ReadRam64"):
 directory=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
 mp=(directory/'RaphaelSec.dll.map').read_text()
 dis=subprocess.check_output(['llvm-objdump','-d',str(directory/'RaphaelSec.efi')],text=True)
 rva=int(re.search(r'(?m)^([0-9a-f]+)\s+.*\s'+re.escape(function)+'$',mp)[1],16)
 instructions=[]
 for m in re.finditer(r'(?m)^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$',dis):
  at=int(m[1],16)
  if at<rva:continue
  instructions.append((at,int(m[2],16),m[3]))
  if m[3].strip()=='ret':break
 text='\n'.join(i[2] for i in instructions)
 # Address x0 is copied to x20, output x1 to x19. Stack spills are independent.
 assert 'mov\tx20, x0' in text and 'mov\tx19, x1' in text
 assert len(re.findall(r'ldr\s+x8, \[x20\]',text))==1 and len(re.findall(r'str\s+x8, \[x19\]',text))==1
 memory=[i for i in instructions if re.match(r'(?:ld|st)',i[2])]
 assert all('[sp' in i[2] or i[2] in ['ldr\tx8, [x20]','str\tx8, [x19]'] for i in memory)
 calls=[i for i in instructions if i[2].startswith('bl\t')];assert len(calls)==2
 for call,symbol,word in zip(calls,['ArmDataSynchronizationBarrier','ArmDataMemoryBarrier'],[0xd5033f9f,0xd5033fbf]):
  target=int(re.search(r'0x([0-9a-f]+)',call[2])[1],16)
  assert target==int(re.search(r'(?m)^([0-9a-f]+)\s+.*\s'+symbol+'$',mp)[1],16)
  assert re.search(r'(?m)^\s*'+format(target,'x')+r':\s+'+format(word,'08x')+r'\s',dis)
 load=next(i for i in instructions if i[2]=='ldr\tx8, [x20]')
 f=json.loads((build/'fd-inspection.json').read_text());sec=next(fil for fil in f['files'] if fil['guid'].startswith('6d94ae07-'));section=next(s for s in sec['sections'] if 'pe' in s)
 offset=section['offset']+4+load[0];fd=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes()
 assert struct.unpack_from('<I',fd,offset)[0]==load[1] and not fd[sec['offset']+19]&0x40
 return dict(function_rva=rva,load_rva=load[0],load_fd_offset=offset,load_opcode=load[1],no_store_through_candidate=True,only_store_targets=['own stack','output pointer'],barriers=['dsb sy','dmb sy'],instruction_count=len(instructions))
def main():
 from pathlib import Path
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',type=Path,required=True);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['ram_read_probe'] and q['executions']['normal']['ram_read']['passed'] and q['executions']['load_site_udf']['passed']
 for i in q['source_inputs']+q['upstream_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
 repo=ROOT/'sources/mu_basecore';revision='cfb93724a06ff86ff5ba971413368a7809ee42a5';name='MdePkg/Library/ArmLib/AArch64/ArmLibSupport.S'
 raw=(repo/name).read_bytes();assert raw==subprocess.check_output(['git','-C',str(repo),'show',revision+':'+name])
 text=raw.decode();part=text.split('.LPARanges:',1)[1];assert re.findall(r'\d+',part.split('.byte',1)[1].split('\n',1)[0])[:7]==['32','36','40','42','44','48','52']
 src=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec'/n for n in ['RamRead.c','RamReadAdapter.c','Sec.c']]+[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelRamRead.h']
 result=dict(passed=True,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in src],decoder_sha256=sha((ROOT/'scripts/ram_read_probe.py').read_bytes()),load=inspect_load(qp.parent),result_storage=verify_result_storage(qp.parent),primary_sources=[dict(repository='sources/mu_basecore',revision=revision,path=name,sha256=sha(raw))],fatal_load_site_udf_return_verified=True,real_data_abort_verified=False,handset_executed=False)
 (ROOT/'UniXNU-raphael/evidence/ram-read-source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['load'],indent=2))
if __name__=='__main__':main()
