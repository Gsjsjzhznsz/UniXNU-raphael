// SPDX-License-Identifier: BSD-2-Clause-Patent
.section .text.entry,"ax"
.global _start
_start:
 msr daifset,#0xf
 ldr x0,=stack_top
 mov sp,x0
 adr x0,vectors
 msr vbar_el1,x0
 mrs x0,sctlr_el1
 mov x1,#0x1005
 bic x0,x0,x1
 // QEMU MMU-off defaults permit unaligned RAM; explicitly enforce alignment.
 orr x0,x0,#2
 msr sctlr_el1,x0
 isb
 bl main_entry
 b .
.global invoke
invoke:
 stp x29,x30,[sp,#-16]!
 bl command_entry
 cmp w0,#1
 b.ne exception
 ldp x29,x30,[sp],#16
 ret
.balign 2048
vectors:
.rept 16
 b exception
 .balign 128
.endr
.section .bss,"aw",%nobits
.balign 16
.space 16384
stack_top:
