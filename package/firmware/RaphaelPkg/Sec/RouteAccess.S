// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
// Same exact-PC synchronous recovery ABI as TimerAccess; no IAR/EOIR/DIR.
ASM_FUNC(RaphaelWriteRouteIgrpen1)
RaphaelWriteRouteIgrpen1Probe:
 msr icc_igrpen1_el1,x0
 isb
 mov w0,#1
 ret
RaphaelWriteRouteIgrpen1Failed:
 mov w0,#0
 ret
ASM_FUNC(RaphaelRouteInjectedUndefined)
RaphaelRouteInjectedUndefinedProbe:
 .inst 0
 mov w0,#1
 ret
RaphaelRouteInjectedUndefinedFailed:
 mov w0,#0
 ret
.section .rodata.RaphaelRouteAccessSites,"a"
.balign 8
.global RaphaelRouteAccessSites
RaphaelRouteAccessSites:
 .quad RaphaelWriteRouteIgrpen1Probe,RaphaelWriteRouteIgrpen1Failed
 .quad RaphaelRouteInjectedUndefinedProbe,RaphaelRouteInjectedUndefinedFailed
.global RaphaelRouteAccessSitesEnd
RaphaelRouteAccessSitesEnd:
