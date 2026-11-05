// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
// x0: 3 checked identity-mapped [base,end) ranges; x1: no-argument callback.
// Clean/invalidate every owned dirty line, including this live stack, then
// change SCTLR without further stack writes. The callback uses uncached DRAM.
// No translation table, TCR, MAIR or interrupt setting changes in this leaf.
ASM_FUNC (RaphaelCallUfsUncached)
  stp x19, x20, [sp, #-32]!
  stp x21, x30, [sp, #16]
  mov x19, x0
  mov x20, x1
  mrs x21, sctlr_el1
  mrs x9, ctr_el0
  ubfx x9, x9, #16, #4
  mov x10, #4
  lsl x10, x10, x9
  mov x11, #3
.Lufs_range:
  ldp x12, x13, [x19], #16
.Lufs_line:
  dc civac, x12
  add x12, x12, x10
  cmp x12, x13
  b.lo .Lufs_line
  subs x11, x11, #1
  b.ne .Lufs_range
  dsb sy
  mov x9, #0x1005
  bic x9, x21, x9
  msr sctlr_el1, x9
  isb
  blr x20
  dsb sy
  // The range table is itself in owned data. Reading it while cleaning later
  // ranges can refill an already-cleaned cache line. Discard such stale lines
  // after the uncached callback, while M/C remain off; never clean them back
  // over callback writes. Re-read the ranges without allocating cache lines.
  sub x19, x19, #48
  mrs x9, ctr_el0
  ubfx x9, x9, #16, #4
  mov x10, #4
  lsl x10, x10, x9
  mov x11, #3
.Lufs_invalidate_range:
  ldp x12, x13, [x19], #16
.Lufs_invalidate_line:
  dc ivac, x12
  add x12, x12, x10
  cmp x12, x13
  b.lo .Lufs_invalidate_line
  subs x11, x11, #1
  b.ne .Lufs_invalidate_range
  dsb sy
  msr sctlr_el1, x21
  isb
  ldp x21, x30, [sp, #16]
  ldp x19, x20, [sp], #32
  ret
