#!/usr/bin/env python3
"""Audit linked store, bounded write callback, source and restoration fixtures."""
import argparse,json,re,struct,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from ram_write_probe import verify_storage

def inspect_write(build,function="WriteRam64"):
 d=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT'
 mp=(d/'RaphaelSec.dll.map').read_text();dis=subprocess.check_output(['llvm-objdump','-d',str(d/'RaphaelSec.efi')],text=True)
 def symbol(n):return int(re.search(r'(?m)^([0-9a-f]+)\s+.*\s'+n+r'$',mp)[1],16)
 at=symbol(function);ins=[]
 for m in re.finditer(r'(?m)^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$',dis):
  if int(m[1],16)<at:continue
  ins.append((int(m[1],16),int(m[2],16),m[3]))
  if m[3].strip()=='ret':break
 text='\n'.join(i[2] for i in ins)
 assert all(x in text for x in ['mov\tx21, x0','mov\tx20, x1','mov\tx19, x2','cmp\tx8, #0x101'])
 memory=[i for i in ins if re.match(r'(?:ld|st)',i[2])]
 assert all('[sp' in i[2] or i[2] in ['str\tx20, [x21]','ldr\tx8, [x19, #0x68]'] for i in memory)
 stores=[i for i in ins if i[2]=='str\tx20, [x21]'];assert len(stores)==1
 calls=[i for i in ins if i[2].startswith('bl\t')];assert len(calls)==3
 targets=[int(re.search(r'0x([0-9a-f]+)',i[2])[1],16) for i in calls]
 assert targets==[symbol('ArmDataSynchronizationBarrier')]*2+[symbol('RaphaelRamWriteCheckpoint')]
 assert calls[0][0]<stores[0][0]<calls[1][0]<calls[2][0]
 for name,opcode in [('ArmDataSynchronizationBarrier',0xd5033f9f),('RaphaelRamWriteCheckpoint',0xd503201f)]:
  assert re.search(r'(?m)^\s*'+format(symbol(name),'x')+r':\s+'+format(opcode,'08x')+r'\s',dis)
 return dict(function_rva=at,store_rva=stores[0][0],store_opcode=stores[0][1],single_64bit_store_only=True,no_load_from_candidate=True,barriers=['dsb sy before store','dsb sy after store'],checkpoint_write_attempt=257,checkpoint_is_nop=True,instruction_count=len(ins))
def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',type=Path,required=True);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['ram_write_pages'] and q['executions']['normal']['ram_write']['passed'] and q['executions']['partial_write_udf']['ram_write']['passed'] and q['executions']['load_site_udf']['passed']
 for i in q['source_inputs']+q['upstream_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
 paths=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg'/n for n in ['Sec/RamReadAdapter.c','Sec/RamWriteCheckpoint.S','Sec/Sec.c','Sec/SecEntry.S','Library/RaphaelRamWriteLib/RamWrite.c','Include/Library/RaphaelRamWriteLib.h']]
 result=dict(passed=True,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],decoder_sha256=sha((ROOT/'scripts/ram_write_probe.py').read_bytes()),store=inspect_write(qp.parent),result_storage=verify_storage(qp.parent),partial_page_udf_recovery_verified=True,real_data_abort_verified=False,handset_executed=False)
 (ROOT/'UniXNU-raphael/evidence/ram-write-source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['store'],indent=2))
if __name__=='__main__':main()
