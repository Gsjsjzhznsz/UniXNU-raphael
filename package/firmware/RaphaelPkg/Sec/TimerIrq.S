// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
// All persistent state is backed by the current SEC .data. The IRQ vector is
// only used while this leaf is active. No C call, x18 or callee-saved clobber.
ASM_FUNC(RaphaelRunTimerIrqWindow)
 mov x9,x0
 mov x10,#24
1:
 str xzr,[x9],#8
 subs x10,x10,#1
 b.ne 1b
 mov x9,#1
 str x9,[x0,#0]
 mov x9,#2
 str x9,[x0,#8]
 str x1,[x0,#16]
 str x2,[x0,#24]
 cmp x1,#16
 b.lo .Lirq_reject
 cmp x1,#32
 b.hs .Lirq_reject
 cmp x2,#1000
 b.lo .Lirq_reject
 mrs x9,CurrentEL
 cmp x9,#4
 b.ne .Lirq_reject
 mrs x9,daif
 str x9,[x0,#104]
 and x10,x9,#0x3c0
 cmp x10,#0x3c0
 b.ne .Lirq_reject
 mrs x9,spsel
 str x9,[x0,#160]
 cmp x9,#1
 b.ne .Lirq_reject
 mrs x9,icc_ctlr_el1
 tbnz x9,#1,.Lirq_reject
 mov x9,sp
 str x9,[x0,#168]
 mrs x9,cntpct_el0
 str x9,[x0,#32]
 mov x10,#10
 udiv x10,x2,x10
 adds x10,x9,x10
 b.cs .Lirq_reject
 str x10,[x0,#40]
 adrp x9,RaphaelActiveIrqResult
 add x9,x9,:lo12:RaphaelActiveIrqResult
 str x0,[x9]
 dsb sy
.global RaphaelIrqWindowOpen
RaphaelIrqWindowOpen:
 msr daifclr,#2
 isb
 mov x11,#0
 mov x12,#0x4240
 movk x12,#0xf,lsl #16
.Lirq_wait:
 ldr x9,[x0,#64]
 cbnz x9,.Lirq_close
 mrs x9,cntpct_el0
 str x9,[x0,#48]
 ldr x10,[x0,#40]
 cmp x9,x10
 b.hs .Lirq_close
 add x11,x11,#1
 cmp x11,x12
 b.hs .Lirq_close
 b .Lirq_wait
.Lirq_close:
 msr daifset,#2
 isb
.global RaphaelIrqWindowClose
RaphaelIrqWindowClose:
 str x11,[x0,#56]
 mrs x9,daif
 str x9,[x0,#120]
 mrs x9,cntpct_el0
 str x9,[x0,#48]
 adrp x9,RaphaelActiveIrqResult
 add x9,x9,:lo12:RaphaelActiveIrqResult
 str xzr,[x9]
 dsb sy
 mov x9,#1
 str x9,[x0,#184]
 ldr x9,[x0,#64]
 cbz x9,.Lirq_timeout
 cmp x9,#1
 b.ne .Lirq_bad
 ldr x9,[x0,#72]
 ldr x10,[x0,#16]
 cmp x9,x10
 b.ne .Lirq_bad
 ldr x9,[x0,#128]
 cmp x9,#1
 b.ne .Lirq_bad
 ldr x9,[x0,#136]
 cmp x9,#1
 b.ne .Lirq_bad
 ldr x9,[x0,#144]
 cbnz x9,.Lirq_bad
 ldr x9,[x0,#152]
 cbnz x9,.Lirq_bad
 mov x9,#5
 str x9,[x0,#8]
 mov w0,#1
 ret
.Lirq_timeout:
 mov x9,#3
 b .Lirq_failed
.Lirq_bad:
 mov x9,#4
.Lirq_failed:
 str x9,[x0,#8]
.Lirq_reject:
 mov w0,#0
 ret

ASM_FUNC(RaphaelTimerIrqHandler)
 // Save only the scratch registers used here. x0-x7, x18-x30 are untouched.
 sub sp,sp,#80
 stp x8,x9,[sp,#0]
 stp x10,x11,[sp,#16]
 stp x12,x13,[sp,#32]
 stp x14,x15,[sp,#48]
 stp x16,x17,[sp,#64]
 adrp x9,RaphaelActiveIrqResult
 add x9,x9,:lo12:RaphaelActiveIrqResult
 ldr x9,[x9]
 cbz x9,.Lirq_fatal
 mrs x10,elr_el1
 adr x11,RaphaelIrqWindowOpen
 cmp x10,x11
 b.lo .Lirq_fatal
 adr x11,RaphaelIrqWindowClose
 cmp x10,x11
 b.hi .Lirq_fatal
 str x10,[x9,#88]
 mrs x11,spsr_el1
 str x11,[x9,#96]
 and x12,x11,#0x3c0
 str x12,[x9,#112]
 mov x12,sp
 str x12,[x9,#176]
 ldr x12,[x9,#64]
 add x12,x12,#1
 str x12,[x9,#64]
 mrs x10,icc_iar1_el1
 str x10,[x9,#72]
 mrs x12,cntpct_el0
 str x12,[x9,#80]
 // Withdraw the only enabled level source before EOI. EOImode0 is required.
 mov x12,#2
 msr cntp_ctl_el0,x12
 isb
 mrs x12,cntp_ctl_el0
 and x12,x12,#3
 cmp x12,#2
 cset x12,eq
 str x12,[x9,#136]
 ldr x12,[x9,#16]
 cmp x10,x12
 b.eq .Lirq_eoi
 str x10,[x9,#152]
 cmp x10,#1020
 b.lo .Lirq_eoi
 cmp x10,#1023
 b.hi .Lirq_eoi
 // Special IDs were not acknowledged and must not be EOI'd.
 mov x12,#1
 str x12,[x9,#144]
 b .Lirq_return
.Lirq_eoi:
 msr icc_eoir1_el1,x10
 isb
 mov x12,#1
 str x12,[x9,#128]
.Lirq_return:
 // Return to the bounded leaf with IRQ masked after this first exception.
 orr x11,x11,#0x80
 msr spsr_el1,x11
 ldp x8,x9,[sp,#0]
 ldp x10,x11,[sp,#16]
 ldp x12,x13,[sp,#32]
 ldp x14,x15,[sp,#48]
 ldp x16,x17,[sp,#64]
 add sp,sp,#80
 eret
.Lirq_fatal:
 b RaphaelException
.section .data.RaphaelActiveIrqResult,"aw"
.balign 8
.global RaphaelActiveIrqResult
RaphaelActiveIrqResult:
 .quad 0
