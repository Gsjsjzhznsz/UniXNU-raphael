/* SPDX-License-Identifier: BSD-2-Clause-Patent */
.section .text.entry,"ax"
.global ReturnStubEntry
ReturnStubEntry:
 msr tpidr_el0,x0
 adrp x9,return_vectors
 add x9,x9,:lo12:return_vectors
 msr vbar_el1,x9
 isb
 adrp x9,return_stack_end
 add x9,x9,:lo12:return_stack_end
 mov sp,x9
 bl ReturnStubMain
1: wfe
 b 1b
.global ReturnStubResume
ReturnStubResume:
 mov x8,x0
 // This leaf makes no stack writes after range maintenance begins.
 mrs x11,ctr_el0
 ubfx x11,x11,#16,#4
 mov x12,#4
 lsl x12,x12,x11
 ldp x9,x10,[x8,#96]
 bl .Lclean
 ldp x9,x10,[x8,#112]
 bl .Lclean
 ldp x9,x10,[x8,#328]
 cbz x9,.Laux_done
 bl .Lclean
.Laux_done:
 dsb sy
 // Original kernel bytes replace low firmware code, requiring I-cache eviction.
 mrs x11,ctr_el0
 and x11,x11,#15
 mov x12,#4
 lsl x12,x12,x11
 ldp x9,x10,[x8,#96]
2: ic ivau,x9
 add x9,x9,x12
 cmp x9,x10
 b.lo 2b
 dsb sy
 isb
 mrs x9,sctlr_el1
 bic x9,x9,#1
 bic x9,x9,#4
 bic x9,x9,#0x1000
 msr sctlr_el1,x9
 isb
 ldp x9,x10,[x8,#224]
 msr vbar_el1,x9
 msr tpidr_el0,x10
 ldp x9,x10,[x8,#240]
 msr tcr_el1,x9
 msr ttbr0_el1,x10
 ldp x9,x10,[x8,#256]
 msr ttbr1_el1,x9
 msr mair_el1,x10
 ldr x9,[x8,#272]
 msr cpacr_el1,x9
 ldr x9,[x8,#184]
 msr sctlr_el1,x9
 dsb sy
 tlbi vmalle1
 dsb sy
 isb
 ldr x16,[x8,#48]
 ldr x0,[x8,#16]
 ldp x1,x2,[x8,#136]
 ldr x3,[x8,#152]
 ldp x30,x9,[x8,#160]
 mov sp,x9
 ldr x9,[x8,#192]
 msr daif,x9
 br x16
.Lclean:
 sub x11,x12,#1
 bic x9,x9,x11
3: dc civac,x9
 add x9,x9,x12
 cmp x9,x10
 b.lo 3b
 ret
// All unexpected exceptions stay in the high image and issue PSCI reset.
.balign 2048
return_vectors:
.rept 16
 mrs x0,tpidr_el0
 b ReturnStubAbort
 .balign 128
.endr
.section .data.storage,"aw"
.balign 16
 .space 16384
return_stack_end:
.balign 16
.global return_scratch
return_scratch:
 .space 65536
.section .note.GNU-stack,"",%progbits
