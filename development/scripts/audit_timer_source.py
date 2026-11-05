#!/usr/bin/env python3
"""Audit actual CNTP access instructions and pinned primary timer semantics."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
from entry_probe import ROOT,sha
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--qemu-report',required=True,type=Path);parser.add_argument('--fault-qemu-report',required=True,type=Path);args=parser.parse_args()
 qp=args.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['timer_source_test'] and not q['icc_fault_test']
 assert q['executions']['normal']['timer_source']['passed']
 fp=args.fault_qemu_report.resolve();f=json.loads(fp.read_text())
 assert f['qemu_passed'] and f['timer_source_test'] and f['icc_fault_test']
 assert f['source_inputs']==q['source_inputs'] and f['upstream_inputs']==q['upstream_inputs']
 assert f['executions']['normal']['timer_source']['passed'] and f['executions']['normal']['timer_source']['simulated_write_failure']
 for item in q['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
 obj=qp.parent/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/TimerAccess.obj'
 dis=subprocess.check_output(['llvm-objdump','-d',str(obj)],text=True)
 instructions=re.findall(r'(?m)^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s+(mrs|msr)\s+(.+)',dis)
 assert [(op,operands.lower()) for word,op,operands in instructions]==[('mrs','x9, cntpct_el0'),('msr','cntp_ctl_el0, x0'),('msr','cntp_cval_el0, x0')]
 assert not re.search(r'\b(sys|dc|ic)\b',dis,re.I)
 assert not re.search(r'\b(?:x(?:18|19|2[0-9]|30)|sp)\b',dis)
 assert len(re.findall(r'\bisb\b',dis))==2
 syms=subprocess.check_output(['llvm-nm',str(obj)],text=True)
 def value(name):return int(re.search(r'(?m)^([0-9a-f]+) [A-Za-z] '+name+r'$',syms)[1],16)
 assert value('RaphaelTimerAccessSitesEnd')-value('RaphaelTimerAccessSites')==3*16
 parent=ROOT/'artifacts/timer-source-audit';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 asm=out/'timer-access.S';asm.write_text('.text\nmrs x9,cntpct_el0\nmsr cntp_ctl_el0,x0\nmsr cntp_cval_el0,x0\n')
 commands=[['aarch64-linux-gnu-as','-o',str(out/'timer-access.o'),str(asm)],['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.text',str(out/'timer-access.o'),str(out/'timer-access.bin')]]
 for command in commands:subprocess.run(command,check=True,capture_output=True)
 assert list(struct.unpack('<3I',(out/'timer-access.bin').read_bytes()))==[int(word,16) for word,op,operands in instructions]
 repo=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
 sources=[]
 for name,anchors in [
  ('include/clocksource/arm_arch_timer.h',['#define ARCH_TIMER_CTRL_ENABLE\t\t(1 << 0)','#define ARCH_TIMER_CTRL_IT_MASK\t\t(1 << 1)','#define ARCH_TIMER_CTRL_IT_STAT\t\t(1 << 2)']),
  ('arch/arm64/include/asm/arch_timer.h',['write_sysreg(val, cntp_ctl_el0);','read_sysreg(cntp_ctl_el0);','isb();']),
  ('arch/arm64/include/asm/sysreg.h',['#define Op0_shift\t19','#define Op1_shift\t16','#define CRn_shift\t12','#define CRm_shift\t8','#define Op2_shift\t5'])]:
  raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+name]);s=raw.decode()
  locations={}
  for anchor in anchors:
   assert anchor in s
   locations[anchor]=[n+1 for n,line in enumerate(s.splitlines()) if anchor in line]
  sources.append(dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,sha256=sha(raw),anchors=locations))
 inputs=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg'/name for name in ['Sec/TimerSource.c','Sec/TimerSourceAdapter.c','Sec/TimerAccess.S','Sec/SecEntry.S','Include/RaphaelTimerSource.h']]
 report=dict(passed=True,fault_qemu_report=str(fp.relative_to(ROOT)),fault_qemu_report_sha256=sha(fp.read_bytes()),qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),compiled_access_object_sha256=sha(obj.read_bytes()),
  actual_register_instructions=[dict(hex=word,operation=op,operands=operands) for word,op,operands in instructions],independent_gnu_assembler_matched=True,
  physical_timer_msr_count=2,physical_counter_mrs_count=1,recovery_site_count=3,recovery_table_bytes=48,
  gic_accesses_in_source_test=False,virtual_timer_writes=False,primary_sources=sources,commands=commands,
  source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],decoder_sha256=sha((ROOT/'scripts/timer_source.py').read_bytes()),
  design=dict(expiration_seconds='1/100',timeout_seconds='1/10',max_polls=1000000,irq_masked=True,timer_enabled_only_with_imask=True),
  handset_executed=False,limits=['Normal QEMU verifies actual CNTP writes/expiration/restoration','Fault QEMU uses an ABI-controlled UDF to simulate one failed CTL write after an actual CVAL change; not a real trapped MSR','No IRQ delivery or GIC takeover established'])
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/timer-source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('3 compiled CNTP/counter access sites and primary timer bits verified');print(out)
if __name__=='__main__':main()
