// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
// Explicit bodies: BaseTools Trim excludes assembler include-file bodies.
// x0=value, x1=ESR, x2=ELR; only ABI caller-saved registers may be clobbered.

ASM_FUNC(RaphaelReadCurrentEl)
RaphaelReadCurrentElProbe:
 mrs x9, CurrentEL
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCurrentElFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadDaif)
RaphaelReadDaifProbe:
 mrs x9, DAIF
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadDaifFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadMpidr)
RaphaelReadMpidrProbe:
 mrs x9, MPIDR_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadMpidrFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadSre)
RaphaelReadSreProbe:
 mrs x9, ICC_SRE_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadSreFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadCtlr)
RaphaelReadCtlrProbe:
 mrs x9, ICC_CTLR_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCtlrFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadPmr)
RaphaelReadPmrProbe:
 mrs x9, ICC_PMR_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadPmrFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadBpr1)
RaphaelReadBpr1Probe:
 mrs x9, ICC_BPR1_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadBpr1Failed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadIgrpen1)
RaphaelReadIgrpen1Probe:
 mrs x9, ICC_IGRPEN1_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadIgrpen1Failed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadRpr)
RaphaelReadRprProbe:
 mrs x9, ICC_RPR_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadRprFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadHppir1)
RaphaelReadHppir1Probe:
 mrs x9, ICC_HPPIR1_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadHppir1Failed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadCntpCtl)
RaphaelReadCntpCtlProbe:
 mrs x9, CNTP_CTL_EL0
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCntpCtlFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadCntpCval)
RaphaelReadCntpCvalProbe:
 mrs x9, CNTP_CVAL_EL0
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCntpCvalFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadCntvCtl)
RaphaelReadCntvCtlProbe:
 mrs x9, CNTV_CTL_EL0
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCntvCtlFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadCntvCval)
RaphaelReadCntvCvalProbe:
 mrs x9, CNTV_CVAL_EL0
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCntvCvalFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadCntkctl)
RaphaelReadCntkctlProbe:
 mrs x9, CNTKCTL_EL1
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCntkctlFailed:
 mov w0,#0
 ret

ASM_FUNC(RaphaelReadCntfrq)
RaphaelReadCntfrqProbe:
 mrs x9, CNTFRQ_EL0
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadCntfrqFailed:
 mov w0,#0
 ret

// QEMU-only intentional fault; handset builders forbid enabling this call.
ASM_FUNC(RaphaelReadInjectedUndefined)
RaphaelReadInjectedUndefinedProbe:
 udf #0
 str x9,[x0]
 mov w0,#1
 ret
RaphaelReadInjectedUndefinedFailed:
 mov w0,#0
 ret
.section .rodata.RaphaelIccReadSites,"a"
.balign 8
.global RaphaelIccReadSites
RaphaelIccReadSites:
 .quad RaphaelReadCurrentElProbe, RaphaelReadCurrentElFailed
 .quad RaphaelReadDaifProbe, RaphaelReadDaifFailed
 .quad RaphaelReadMpidrProbe, RaphaelReadMpidrFailed
 .quad RaphaelReadSreProbe, RaphaelReadSreFailed
 .quad RaphaelReadCtlrProbe, RaphaelReadCtlrFailed
 .quad RaphaelReadPmrProbe, RaphaelReadPmrFailed
 .quad RaphaelReadBpr1Probe, RaphaelReadBpr1Failed
 .quad RaphaelReadIgrpen1Probe, RaphaelReadIgrpen1Failed
 .quad RaphaelReadRprProbe, RaphaelReadRprFailed
 .quad RaphaelReadHppir1Probe, RaphaelReadHppir1Failed
 .quad RaphaelReadCntpCtlProbe, RaphaelReadCntpCtlFailed
 .quad RaphaelReadCntpCvalProbe, RaphaelReadCntpCvalFailed
 .quad RaphaelReadCntvCtlProbe, RaphaelReadCntvCtlFailed
 .quad RaphaelReadCntvCvalProbe, RaphaelReadCntvCvalFailed
 .quad RaphaelReadCntkctlProbe, RaphaelReadCntkctlFailed
 .quad RaphaelReadCntfrqProbe, RaphaelReadCntfrqFailed
 .quad RaphaelReadInjectedUndefinedProbe, RaphaelReadInjectedUndefinedFailed
.global RaphaelIccReadSitesEnd
RaphaelIccReadSitesEnd:
