// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
.balign 8
.global RaphaelMmuRelay
RaphaelMmuRelay:
  // The optional high-VA prefix works even after original TTBR0 is empty.
  // Preserve original TTBR0 separately from the diagnostic transition root.
  mrs x8,ttbr0_el1
  mrs x15,sctlr_el1
  tbz x15,#0,.Lmmu_physical_body
  ldr x16,RaphaelMmuRelayTransition
  cbz x16,.Lmmu_physical_body
  dsb sy
  msr ttbr0_el1,x16
  isb
  tlbi vmalle1
  dsb sy
  isb
  ldr x16,RaphaelMmuRelayPhysicalBody
  br x16
.global RaphaelMmuRelayBody
RaphaelMmuRelayBody:
.Lmmu_physical_body:
  mrs x15,sctlr_el1
  // Early C has dirty WB globals/stacks. Clean by the current mapped VAs
  // before disabling caches; CTR supplies the actual D-cache line size.
  tbz x15,#0,.Lmmu_clean_done
  tbz x15,#2,.Lmmu_clean_done
  mrs x9,ctr_el0
  ubfx x9,x9,#16,#4
  mov x10,#4
  lsl x10,x10,x9
  adr x11,RaphaelMmuRelayRanges
  mov x12,#4
.Lmmu_clean_range:
  ldp x13,x14,[x11],#16
  cbz x14,.Lmmu_clean_next
  add x14,x13,x14
.Lmmu_clean_line:
  dc civac,x13
  add x13,x13,x10
  cmp x13,x14
  b.lo .Lmmu_clean_line
.Lmmu_clean_next:
  subs x12,x12,#1
  b.ne .Lmmu_clean_range
  dsb sy
.Lmmu_clean_done:
  bic x16,x15,#1
  bic x16,x16,#4
  bic x16,x16,#0x1000
  dsb sy
  msr sctlr_el1,x16
  isb
  tlbi vmalle1
  dsb sy
  isb
  ldr x16,RaphaelMmuRelayState
  str x0,[x16,#96]
  str x1,[x16,#104]
  str x20,[x16,#112]
  str x21,[x16,#120]
  str x22,[x16,#128]
  str x23,[x16,#136]
  str x24,[x16,#144]
  str x25,[x16,#152]
  str x30,[x16,#168]
  str x15,[x16,#176]
  str x17,[x16,#328]
  mov x9,sp
  str x9,[x16,#160]
  mrs x9,esr_el1
  str x9,[x16,#64]
  mrs x9,elr_el1
  str x9,[x16,#72]
  mrs x9,far_el1
  str x9,[x16,#80]
  mrs x9,spsr_el1
  str x9,[x16,#88]
  mrs x9,vbar_el1
  str x9,[x16,#184]
  mrs x9,tcr_el1
  str x9,[x16,#192]
  str x8,[x16,#200]
  mrs x9,ttbr1_el1
  str x9,[x16,#208]
  mrs x9,mair_el1
  str x9,[x16,#216]
  mrs x9,sctlr_el1
  str x9,[x16,#336]
  mrs x9,sp_el0
  str x9,[x16,#512]
  mrs x9,CurrentEL
  str x9,[x16,#520]
  mrs x9,daif
  str x9,[x16,#528]
  mrs x9,cpacr_el1
  str x9,[x16,#536]
  mrs x9,tpidr_el0
  str x9,[x16,#544]
  mrs x9,tpidrro_el0
  str x9,[x16,#552]
  mrs x9,tpidr_el1
  str x9,[x16,#560]
  mrs x9,cntpct_el0
  str x9,[x16,#568]
  ldr x10,RaphaelMmuRelayPmap
  cbz x10,.Lmmu_pmap_saved
  mrs x9,ttbr0_el1
  str x9,[x10,#80]
.Lmmu_pmap_saved:
  ldr x9,[x16,#24]
  cbnz x9,.Lmmu_halt
  mov x9,#1
  str x9,[x16,#24]
  ldr x9,[x16,#240]
  msr tcr_el1,x9
  ldr x9,[x16,#248]
  msr ttbr0_el1,x9
  ldr x9,[x16,#256]
  msr ttbr1_el1,x9
  ldr x9,[x16,#264]
  msr mair_el1,x9
  ldr x9,[x16,#272]
  msr cpacr_el1,x9
  ldr x9,[x16,#280]
  msr tpidr_el0,x9
  ldr x9,[x16,#288]
  msr tpidrro_el0,x9
  ldr x9,[x16,#296]
  msr tpidr_el1,x9
  ldr x9,[x16,#304]
  msr sp_el0,x9
  ldr x9,[x16,#232]
  msr vbar_el1,x9
  dsb sy
  tlbi vmalle1
  dsb sy
  isb
  ldr x9,[x16,#224]
  msr sctlr_el1,x9
  isb
  msr spsel,#1
  ldr x9,RaphaelMmuRelayStack
  mov sp,x9
  ldr x9,RaphaelMmuRelayHandler
  br x9
.Lmmu_halt:
  b .Lmmu_halt
.balign 8
.global RaphaelMmuRelayState
RaphaelMmuRelayState: .quad 0
.global RaphaelMmuRelayStack
RaphaelMmuRelayStack: .quad 0
.global RaphaelMmuRelayHandler
RaphaelMmuRelayHandler: .quad 0
.global RaphaelMmuRelayRanges
RaphaelMmuRelayRanges: .quad 0,0,0,0,0,0,0,0
.global RaphaelMmuRelayTransition
RaphaelMmuRelayTransition: .quad 0
.global RaphaelMmuRelayPhysicalBody
RaphaelMmuRelayPhysicalBody: .quad 0
.global RaphaelMmuRelayPmap
RaphaelMmuRelayPmap: .quad 0
.global RaphaelMmuRelayEnd
RaphaelMmuRelayEnd:
