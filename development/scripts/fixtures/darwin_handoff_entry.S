/* SPDX-License-Identifier: BSD-2-Clause-Patent */
.section .text.entry,"ax"
.global handoff_start
handoff_start:
 mrs x1,CurrentEL
 mrs x2,sctlr_el1
 mrs x3,daif
 adr x4,handoff_start
 adr x9,handoff_stack_top
 mov sp,x9
 bl handoff_main
1: wfe
 b 1b
.section .bss.stack,"aw",%nobits
.balign 16
.skip 16384
handoff_stack_top:
