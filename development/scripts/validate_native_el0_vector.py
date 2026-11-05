#!/usr/bin/env python3
"""Execute the final native lower-EL vector branch with actual EL0 BRKs in QEMU."""
import argparse,datetime,json,struct,subprocess
from pathlib import Path
from entry_probe import ROOT
from native_early import image
def branch_target(pc,instruction,opcode):
 assert instruction&0xfc000000==opcode
 delta=instruction&0x3ffffff
 return pc+((delta-(1<<26) if delta&(1<<25) else delta)<<2)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inspection',type=Path,required=True);a=p.parse_args()
 inspection=json.loads(a.inspection.read_text());assert inspection['passed']
 kernel=ROOT/inspection['artifact_directory']/'native-kernel.macho';raw=kernel.read_bytes();segments,symbols=image(raw)
 vector=symbols['_ExceptionVectorsBase']+8*128
 seg=next(s for s in segments if s['virtual']<=vector<vector+4<=s['virtual']+s['file_bytes'])
 instruction=struct.unpack_from('<I',raw,seg['offset']+vector-seg['virtual'])[0]
 target=symbols['el0_synchronous_vector_64_long'];assert branch_target(vector,instruction,0x14000000)==target
 displacement=target-vector;assert 4<=displacement<65536 and displacement%4==0
 out=ROOT/'artifacts/native-el0-vector'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
 source=r"""
.text
.global _start
_start:
 ldr x0,=0x42000000
 mov sp,x0
 adr x0,vectors
 msr vbar_el1,x0
 msr sp_el0,x0
 adr x0,user
 msr elr_el1,x0
 mov x0,#0x3c0
 msr spsr_el1,x0
 mov x0,#0x1234
 mov x17,#0x5678
 mov x19,#0
 isb
 eret
user:
 brk #1
 brk #0x5351
 svc #0
 b fail
.balign 2048
vectors:
 .rept 8
 b fail
 .space 124
 .endr
lower_el_vector:
 .long INSTRUCTION
 .space DISPLACEMENT-4
original_handler:
 mrs x9,spsr_el1
 and x9,x9,#15
 cbnz x9,fail
 mov x9,#0x1234
 cmp x0,x9
 b.ne fail
 mov x9,#0x5678
 cmp x17,x9
 b.ne fail
 mrs x9,esr_el1
 mrs x11,elr_el1
 cbz x19,first_brk
 cmp x19,#1
 b.eq second_brk
 cmp x19,#2
 b.ne fail
 lsr x9,x9,#26
 cmp x9,#0x15
 b.ne fail
 adr x1,passed
 b success
first_brk:
 ldr x10,=0xf2000001
 cmp x9,x10
 b.ne fail
 b resume_user
second_brk:
 ldr x10,=0xf2005351
 cmp x9,x10
 b.ne fail
resume_user:
 add x19,x19,#1
 add x11,x11,#4
 msr elr_el1,x11
 eret
fail:
 adr x1,failed
 mov x0,#4
 hlt #0xf000
 adr x1,bad_exit
 b exit
success:
 mov x0,#4
 hlt #0xf000
 adr x1,good_exit
exit:
 mov x0,#0x20
 hlt #0xf000
 b .
passed: .asciz "EL0_BRK_ORIGINAL_VECTOR_OK\n"
failed: .asciz "EL0_BRK_ORIGINAL_VECTOR_FAIL\n"
.balign 8
good_exit: .quad 0x20026,0
bad_exit: .quad 0x20026,1
""".replace('INSTRUCTION',hex(instruction)).replace('DISPLACEMENT',str(displacement))
 (out/'fixture.S').write_text(source);(out/'fixture.ld').write_text('ENTRY(_start)\nSECTIONS { . = 0x40080000; .text : { *(.text*) } }\n')
 commands=[['clang','--target=aarch64-none-elf','-c',str(out/'fixture.S'),'-o',str(out/'fixture.o')],['ld.lld','-T',str(out/'fixture.ld'),str(out/'fixture.o'),'-o',str(out/'fixture.elf')],['qemu-system-aarch64','-M','virt','-cpu','cortex-a57','-m','128M','-nographic','-monitor','none','-semihosting-config','enable=on,target=native','-kernel',str(out/'fixture.elf')]]
 logs=[]
 for command in commands:
  r=subprocess.run(command,capture_output=True,timeout=20);logs.append(r.stdout+r.stderr);assert r.returncode==0,(command,r.returncode,logs[-1].decode(errors='replace'))
 assert b'EL0_BRK_ORIGINAL_VECTOR_OK' in logs[-1] and b'_FAIL' not in logs[-1]
 (out/'serial.log').write_bytes(logs[-1]);report=dict(passed=True,inspection=str(a.inspection),kernel=str(kernel.relative_to(ROOT)),vector=hex(vector),original_handler=hex(target),final_branch_instruction=hex(instruction),original_branch_bytes_executed=True,actual_el0_brk_immediates=[1,0x5351],user_registers_preserved=True,original_path_resumed_user=True,commands=commands,scope='Exact final lower-EL branch relocated with identical relative displacement, actual EL0 exceptions and return; original handler represented by a checked fixture. Full XNU kernel checkpoint/restore gate is separate. No handset service success claim.')
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out)
if __name__=='__main__':main()
