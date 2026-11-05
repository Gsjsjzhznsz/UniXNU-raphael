/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Standalone Linux ARM64 Image receiver; no vendor or Android kernel code.
 */
.section .text.entry,"ax"
.global fixture_header
fixture_header:
 b reset_entry
 .long 0
 .quad 0x80000
 .quad 65536
 .quad 0xa
 .quad 0,0,0
 .ascii "ARM\x64"
 .long 0
reset_entry:
 mrs x9,CurrentEL
 cmp x9,#4
 b.ne 1f
 mrs x9,sctlr_el1
 tst x9,#1
 b.ne 1f
 tst x9,#4
 b.ne 1f
 msr daifset,#0xf
 adrp x9,reset_stack_end
 add x9,x9,:lo12:reset_stack_end
 mov sp,x9
 bl reset_main
1: wfe
 b 1b
.section .data.storage,"aw"
.balign 16
 .space 16384
reset_stack_end:
.section .note.GNU-stack,"",%progbits
