// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
// x0=value/pointer, x1=ESR, x2=ELR. No stack or callee-saved modification.
ASM_FUNC(RaphaelReadPhysicalCount)
RaphaelReadPhysicalCountProbe:
 mrs x9, cntpct_el0
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadPhysicalCountFailed:
 mov w0,#0
 ret
ASM_FUNC(RaphaelWritePhysicalCtl)
RaphaelWritePhysicalCtlProbe:
 msr cntp_ctl_el0,x0
 isb
 mov w0,#1
 ret
RaphaelWritePhysicalCtlFailed:
 mov w0,#0
 ret
ASM_FUNC(RaphaelWritePhysicalCval)
RaphaelWritePhysicalCvalProbe:
 msr cntp_cval_el0,x0
 isb
 mov w0,#1
 ret
RaphaelWritePhysicalCvalFailed:
 mov w0,#0
 ret
.section .rodata.RaphaelTimerAccessSites,"a"
.balign 8
.global RaphaelTimerAccessSites
RaphaelTimerAccessSites:
 .quad RaphaelReadPhysicalCountProbe,RaphaelReadPhysicalCountFailed
 .quad RaphaelWritePhysicalCtlProbe,RaphaelWritePhysicalCtlFailed
 .quad RaphaelWritePhysicalCvalProbe,RaphaelWritePhysicalCvalFailed
.global RaphaelTimerAccessSitesEnd
RaphaelTimerAccessSitesEnd:
