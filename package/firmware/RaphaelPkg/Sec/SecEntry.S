// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>

ASM_FUNC (_ModuleEntryPoint)
  // Fixed-base XIP: reject a relocated download before using PCD addresses.
  adr x9, _ModuleEntryPoint
  ldr x10, =_ModuleEntryPoint
  cmp x9, x10
  b.ne .Lbypass
  mrs x9, CurrentEL
  cmp x9, #4
  b.ne .Lbypass
  mrs x10, sctlr_el1
  tst x10, #1
  b.ne .Lbypass
  tst x10, #4
  b.ne .Lbypass
  tst x10, #0x1000
  b.ne .Lbypass

  ldr x8, =FixedPcdGet64 (PcdRaphaelContextBase)
  stp x0, x1, [x8, #0]
  stp x2, x3, [x8, #16]
  mov x11, sp
  stp x30, x11, [x8, #32]
  stp x9, x10, [x8, #48]
  mrs x9, daif
  mrs x10, cntfrq_el0
  stp x9, x10, [x8, #64]
  msr daifset, #15
  mrs x9, cntpct_el0
  mrs x10, mpidr_el1
  stp x9, x10, [x8, #80]
  mrs x9, vbar_el1
  mrs x10, tpidr_el0
  stp x9, x10, [x8, #96]
  mrs x9, tcr_el1
  mrs x10, ttbr0_el1
  stp x9, x10, [x8, #112]
  mrs x9, ttbr1_el1
  mrs x10, mair_el1
  stp x9, x10, [x8, #128]
  mrs x9, cpacr_el1
  str x9, [x8, #144]
  ldr x9, =FixedPcdGet64 (PcdRaphaelStackBase)
  ldr x10, =FixedPcdGet32 (PcdRaphaelStackSize)
  add x9, x9, x10
  mov sp, x9
  mov x29, xzr
  adrp x9, RaphaelVectors
  add x9, x9, :lo12:RaphaelVectors
  msr vbar_el1, x9
  bl ArmEnableVFP
  isb
  bl SecMain
  b .

.Lbypass:
  // Compute the original target from this PC even if the download moved.
  adr x16, _ModuleEntryPoint
  ldr x17, =_ModuleEntryPoint
  sub x16, x16, x17
  ldr x17, =(FixedPcdGet64 (PcdRaphaelImageBase) + FixedPcdGet64 (PcdRaphaelOriginalEntry))
  add x16, x16, x17
  br x16

ASM_FUNC (RaphaelResume)
  // Leaf cleanup: do not spill after cleaning the stack. Only our identity-
  // mapped extension can contain dirty writes made by this experiment.
  mov x8, x0
  mrs x9, sctlr_el1
  tst x9, #1
  b.ne .Lcache_cleanup
  tst x9, #4
  b.ne .Lcache_cleanup
  tst x9, #0x1000
  b.ne .Lcache_cleanup
  // SEC-only return: translation registers have never been changed. Avoid
  // whole-extension maintenance and TLB operations in this diagnostic phase.
  ldr x9, [x8, #96]
  msr vbar_el1, x9
  ldr x9, [x8, #144]
  msr cpacr_el1, x9
  isb
  b .Lrestore_header
.Lcache_cleanup:
  ldp x9, x10, [x8, #192]
  mrs x11, ctr_el0
  ubfx x11, x11, #16, #4
  mov x12, #4
  lsl x12, x12, x11
  sub x11, x12, #1
  bic x9, x9, x11
0:
  dc civac, x9
  add x9, x9, x12
  cmp x9, x10
  b.lo 0b
  dsb sy
  mrs x9, sctlr_el1
  bic x9, x9, #1
  bic x9, x9, #4
  bic x9, x9, #0x1000
  msr sctlr_el1, x9
  isb
  ldp x9, x10, [x8, #96]
  msr vbar_el1, x9
  msr tpidr_el0, x10
  ldp x9, x10, [x8, #112]
  msr tcr_el1, x9
  msr ttbr0_el1, x10
  ldp x9, x10, [x8, #128]
  msr ttbr1_el1, x9
  msr mair_el1, x10
  ldr x9, [x8, #144]
  msr cpacr_el1, x9
  ldr x9, [x8, #56]
  msr sctlr_el1, x9
  dsb sy
  tlbi vmalle1
  dsb sy
  isb
.Lrestore_header:
  ldp x16, x17, [x8, #152]
  ldr w9, [x8, #176]
  str w9, [x16]
  str x17, [x16, #16]
  dc cvac, x16
  dsb sy
  // This is the only original Image instruction modified by the diagnostic.
  // Match the range operation already validated by the entry-only probe.
  ic ivau, x16
  dsb sy
  isb
  ldr x17, [x8, #168]
  add x16, x16, x17
  ldr x0, [x8, #184]
  cbnz x0, 1f
  ldr x0, [x8, #0]
1:
  ldp x1, x2, [x8, #8]
  ldr x3, [x8, #24]
  ldp x30, x9, [x8, #32]
  mov sp, x9
  ldr x9, [x8, #64]
  msr daif, x9
  br x16

.balign 2048
RaphaelVectors:
  // Only current-EL synchronous slots (SP0/SPx) may use local MRS recovery.
  b RaphaelReadException
  .balign 128
.rept 3
  b RaphaelException
  .balign 128
.endr
  b RaphaelReadException
  .balign 128
  // Only the current-EL SPx IRQ slot can reach the bounded one-shot leaf.
  b RaphaelTimerIrqHandler
  .balign 128
.rept 10
  b RaphaelException
  .balign 128
.endr
RaphaelReadException:
  // These leaf reader functions promise that x8-x17 are caller-saved scratch.
  // No stack access or general exception resume is introduced here.
  mrs x16, esr_el1
  lsr x17, x16, #26
  cmp x17, #0x18
  b.eq .Lread_site_search
  cbnz x17, .Ldiagnostic_exception
.Lread_site_search:
  mrs x8, elr_el1
  adrp x10, RaphaelIccReadSites
  add x10, x10, :lo12:RaphaelIccReadSites
  adrp x11, RaphaelIccReadSitesEnd
  add x11, x11, :lo12:RaphaelIccReadSitesEnd
.Lread_site_next:
  cmp x10, x11
  b.hs .Ltimer_site_begin
  ldp x12, x13, [x10], #16
  cmp x8, x12
  b.ne .Lread_site_next
  b .Laccess_site_found
.Ltimer_site_begin:
  adrp x10, RaphaelTimerAccessSites
  add x10, x10, :lo12:RaphaelTimerAccessSites
  adrp x11, RaphaelTimerAccessSitesEnd
  add x11, x11, :lo12:RaphaelTimerAccessSitesEnd
.Ltimer_site_next:
  cmp x10, x11
  b.hs .Lroute_site_begin
  ldp x12, x13, [x10], #16
  cmp x8, x12
  b.ne .Ltimer_site_next
  b .Laccess_site_found
.Lroute_site_begin:
  adrp x10, RaphaelRouteAccessSites
  add x10, x10, :lo12:RaphaelRouteAccessSites
  adrp x11, RaphaelRouteAccessSitesEnd
  add x11, x11, :lo12:RaphaelRouteAccessSitesEnd
.Lroute_site_next:
  cmp x10, x11
  b.hs .Ldiagnostic_exception
  ldp x12, x13, [x10], #16
  cmp x8, x12
  b.ne .Lroute_site_next
.Laccess_site_found:
  // Only these exact ABI-controlled sites supply valid x1/x2 output pointers.
  str x16, [x1]
  str x8, [x2]
  msr elr_el1, x13
  eret
.Ldiagnostic_exception:
.global RaphaelException
RaphaelException:
  ldr x8, =FixedPcdGet64 (PcdRaphaelContextBase)
  mrs x9, esr_el1
  str x9, [x8, #264]
  mrs x9, elr_el1
  str x9, [x8, #272]
  mrs x9, far_el1
  str x9, [x8, #280]
  // Reset to the known SEC stack if the fault damaged the current stack.
  ldr x9, =FixedPcdGet64 (PcdRaphaelStackBase)
  ldr x10, =FixedPcdGet32 (PcdRaphaelStackSize)
  add x9, x9, x10
  sub x9, x9, #0x1000
  mov sp, x9
  mov x0, #0xe1
  bl SecFinish
  b .
