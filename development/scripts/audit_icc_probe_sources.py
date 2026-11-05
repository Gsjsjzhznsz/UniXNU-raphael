#!/usr/bin/env python3
"""Audit compiled MRS whitelist, fixed primary encodings and exception recovery."""
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
 parser=argparse.ArgumentParser();parser.add_argument('--qemu-report',required=True,type=Path);args=parser.parse_args()
 qpath=args.qemu_report.resolve();q=json.loads(qpath.read_text())
 assert q['qemu_passed'] and q['icc_probe'] and not q['icc_fault_test']
 for item in q['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
 obj=qpath.parent/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/IccRead.obj'
 dis=subprocess.check_output(['llvm-objdump','-d',str(obj)],text=True)
 reads=re.findall(r'(?m)^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s+mrs\s+x9, (\w+)',dis)
 sites=(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/IccReadSites.inc').read_text()
 entries=re.findall(r'RAPHAEL_READ_SITE\((\d+),(\w+),(\w+)\)',sites)
 assert [int(i) for i,n,reg in entries]==list(range(16)) and len(reads)==16
 assert [reg.lower() for code,reg in reads]==[reg.lower() for i,n,reg in entries]
 assert not re.search(r'\b(msr|sys|dc|ic)\b',dis,re.I)
 assert not any(any(x in reg for x in ['IAR','EOIR','DIR']) for code,reg in reads)
 assert not re.search(r'\b(?:x(?:19|2[0-9]|30)|sp)\b',dis)
 symbols=subprocess.check_output(['llvm-nm',str(obj)],text=True)
 def symbol(name):
  match=re.search(r'(?m)^([0-9a-f]+) [A-Za-z] '+name+r'$',symbols);assert match,name
  return int(match[1],16)
 assert symbol('RaphaelIccReadSitesEnd')-symbol('RaphaelIccReadSites')==17*16
 for i,name,reg in entries:
  assert re.search(r'(?m)^[0-9a-f]+ T '+name+r'$',symbols),name
 # An independent GNU assembler must produce the same sixteen MRS opcodes.
 parent=ROOT/'artifacts/icc-source-audit';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 asm=out/'mrs-whitelist.S';asm.write_text('.text\n'+''.join('mrs x9, '+reg+'\n' for i,name,reg in entries))
 commands=[['aarch64-linux-gnu-as','-o',str(out/'mrs-whitelist.o'),str(asm)],
           ['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.text',str(out/'mrs-whitelist.o'),str(out/'mrs-whitelist.bin')]]
 for command in commands:subprocess.run(command,check=True,capture_output=True)
 assert list(struct.unpack('<16I',(out/'mrs-whitelist.bin').read_bytes()))==[int(code,16) for code,reg in reads]
 repo=ROOT/'sources/Xiaomi_Kernel_OpenSource';rev='663db50e195a8a54c8565ac4ab0c6d9ba7d80db0'
 name='arch/arm64/include/asm/sysreg.h';raw=subprocess.check_output(['git','-C',str(repo),'show',rev+':'+name]);text=raw.decode()
 assert '#define Op0_shift\t19' in text and '#define Op1_shift\t16' in text
 assert '#define CRn_shift\t12' in text and '#define CRm_shift\t8' in text and '#define Op2_shift\t5' in text and '0xd5200000' in text
 encoded={}
 for code,register in reads:
  match=re.search(r'#define SYS_'+register+r'\s+sys_reg\((\d+), (\d+), (\d+), (\d+), (\d+)\)',text)
  if not match:continue
  fields=list(map(int,match.groups()));word=0xd5200000|sum(n<<shift for n,shift in zip(fields,[19,16,12,8,5]))|9
  assert word==int(code,16),(register,word,code)
  encoded[register]=dict(encoding_fields=fields,instruction_hex=code,line=text[:match.start()].count('\n')+1)
 assert len(encoded)==12
 spec=ROOT/'sources/arm-reference/IHI0069C_GIC_architecture_spec.pdf'
 spec_text=(spec.with_suffix('.txt')).read_text()
 assert 'ARM IHI 0069C (ID070116)' in spec_text[:400]
 sections={}
 for marker in ['8.2.12 ICC_HPPIR1_EL1','8.2.14 ICC_IAR1_EL1','8.2.22 ICC_SRE_EL1']:
  at=spec_text.index(marker);before=spec_text[:at];page=re.findall(r'=== PDF PAGE (\d+) ===',before)[-1]
  sections[marker]=int(page)
 report=dict(passed=True,qemu_report=str(qpath.relative_to(ROOT)),qemu_report_sha256=sha(qpath.read_bytes()),
  compiled_reader_object_sha256=sha(obj.read_bytes()),actual_mrs_registers=[reg for code,reg in reads],
  independent_gnu_assembler_matched=True,gnu_assembler_version=subprocess.check_output(['aarch64-linux-gnu-as','--version'],text=True).splitlines()[0],
  commands=commands,primary_encoding_source=dict(repository='MiCode/Xiaomi_Kernel_OpenSource',revision=rev,path=name,sha256=sha(raw),verified_registers=encoded),
  architecture_specification=dict(title='Arm Generic Interrupt Controller Architecture Specification GICv3/v4',document='ARM IHI 0069C (ID070116)',
   url='https://documentation-service.arm.com/static/6012f442773bb020e3de7aa5',sha256=sha(spec.read_bytes()),pdf_pages=788,sections_pdf_page=sections),
  recovery_site_count=17,register_read_site_count=16,injected_undefined_site_count=1,read_whitelist_has_no_acknowledge_registers=True,
  cpu_register_writes_in_reader=False,callee_saved_registers_modified_by_reader=False,
  recovery_scope='Current-EL synchronous slots only; exact read PC plus EC 0 or 0x18; ABI caller-saved scratch; separate physical-timer access table is audited by audit_timer_source.py; exceptions outside both tables use the existing fatal diagnostic path',
  source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in [ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/IccRead.S',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/IccReadAdapter.c',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/IccReadSites.inc',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/SecEntry.S']],
  decoder_sha256=sha((ROOT/'scripts/icc_probe.py').read_bytes()),handset_executed=False,
  limitations=['EL2/EL3 traps are not locally recoverable at EL1','EC 0 injected UDF recovery is tested; no claim of an actual EC 0x18 hardware trap'])
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/icc-probe-source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('16 compiled MRS sites, 12 fixed primary encodings and 17 recovery entries verified');print(out)

if __name__=='__main__':main()
