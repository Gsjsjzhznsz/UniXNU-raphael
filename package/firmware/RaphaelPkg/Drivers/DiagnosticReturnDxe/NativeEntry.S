// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
.balign 2048
.global RaphaelNativeEntryVectors
RaphaelNativeEntryVectors:
  mov x17, #0
  b .Lentry_capture
  .balign 128
  mov x17, #1
  b .Lentry_capture
  .balign 128
  mov x17, #2
  b .Lentry_capture
  .balign 128
  mov x17, #3
  b .Lentry_capture
  .balign 128
  mov x17, #4
  b .Lentry_capture
  .balign 128
  mov x17, #5
  b .Lentry_capture
  .balign 128
  mov x17, #6
  b .Lentry_capture
  .balign 128
  mov x17, #7
  b .Lentry_capture
  .balign 128
  mov x17, #8
  b .Lentry_capture
  .balign 128
  mov x17, #9
  b .Lentry_capture
  .balign 128
  mov x17, #10
  b .Lentry_capture
  .balign 128
  mov x17, #11
  b .Lentry_capture
  .balign 128
  mov x17, #12
  b .Lentry_capture
  .balign 128
  mov x17, #13
  b .Lentry_capture
  .balign 128
  mov x17, #14
  b .Lentry_capture
  .balign 128
  mov x17, #15
  b .Lentry_capture
  .balign 128
.global RaphaelNativeEntryVectorsEnd
RaphaelNativeEntryVectorsEnd:
.Lentry_capture:
  msr daifset,#15
  adrp x16,gRaphaelNativeEntry
  add x16,x16,:lo12:gRaphaelNativeEntry
  stp x0,x1,[x16,#96]
  stp x20,x21,[x16,#112]
  str x17,[x16,#312]
  mov x9,sp
  str x9,[x16,#128]
  mrs x9,esr_el1
  str x9,[x16,#64]
  mrs x9,elr_el1
  str x9,[x16,#72]
  mrs x9,far_el1
  str x9,[x16,#80]
  mrs x9,spsr_el1
  str x9,[x16,#88]
  mrs x9,sctlr_el1
  str x9,[x16,#136]
  mrs x9,CurrentEL
  str x9,[x16,#144]
  mrs x9,daif
  str x9,[x16,#152]
  mrs x9,cntpct_el0
  str x9,[x16,#160]
  mrs x9,vbar_el1
  str x9,[x16,#168]
  mrs x9,tcr_el1
  str x9,[x16,#176]
  mrs x9,ttbr0_el1
  str x9,[x16,#184]
  mrs x9,ttbr1_el1
  str x9,[x16,#192]
  mrs x9,mair_el1
  str x9,[x16,#200]
  ldr x9,[x16,#24]
  cbnz x9,.Lentry_halt
  mov x9,#1
  str x9,[x16,#24]
  // No XNU page-table register changes precede the replaced ADRP.
  // Restore the identity UEFI translation before C or stack accesses.
  ldr x9,[x16,#208]
  dsb sy
  msr sctlr_el1,x9
  isb
  ldr x9,[x16,#216]
  msr vbar_el1,x9
  isb
  msr spsel,#1
  ldr x9,=FixedPcdGet64(PcdRaphaelStackBase)
  ldr x10,=FixedPcdGet32(PcdRaphaelStackSize)
  add x9,x9,x10
  sub x9,x9,#0x1000
  mov sp,x9
  b RaphaelNativeEntryCaptured
.Lentry_halt:
  b .Lentry_halt
