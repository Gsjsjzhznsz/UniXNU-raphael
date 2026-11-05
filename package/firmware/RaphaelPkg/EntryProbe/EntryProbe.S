/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Temporary Linux-protocol instrumentation. This is not a UEFI SEC.
 * All storage belongs to the extended downloaded Image; no fixed RAM address.
 */
.section .text.entry, "ax"
.global _probe_start
_probe_start:
  /* Reject unexpected MMU/cache state before using any new memory. */
  mrs x9, CurrentEL
  cmp x9, #4
  b.eq 1f
  cmp x9, #8
  b.ne .Lcontinue
  mrs x10, sctlr_el2
  b 2f
1:
  mrs x10, sctlr_el1
2:
  tst x10, #1
  b.ne .Lcontinue
  tst x10, #4
  b.ne .Lcontinue

  mov x11, sp
  adrp x12, probe_stack_end
  add x12, x12, :lo12:probe_stack_end
  mov sp, x12
  sub sp, sp, #128
  stp x0, x1, [sp, #0]
  stp x2, x3, [sp, #16]
  stp x30, x11, [sp, #32]
  stp x9, x10, [sp, #48]
  mrs x11, daif
  mrs x12, cntfrq_el0
  stp x11, x12, [sp, #64]
  mrs x11, cntpct_el0
  mrs x12, mpidr_el1
  stp x11, x12, [sp, #80]
  adr x11, _probe_start
  ldr x12, =PROBE_OFFSET
  sub x12, x11, x12
  stp x11, x12, [sp, #96]
  mov x0, sp
  bl EntryProbeMain
  ldp x1, x2, [sp, #8]
  ldr x3, [sp, #24]
  ldp x30, x11, [sp, #32]
  mov sp, x11
.Lcontinue:
  /* The original entry is a checked, unconditional B instruction. */
  adr x16, _probe_start
  ldr x17, =(ORIGINAL_ENTRY_OFFSET - PROBE_OFFSET)
  add x16, x16, x17
  br x16

.section .data.storage, "aw"
.balign 16
probe_stack:
  .space 16384
probe_stack_end:
.balign 4096
.global probe_fdt
probe_fdt:
  .space 1052672 /* up to 1 MiB source FDT plus bounded editing space */
.global probe_storage_end
probe_storage_end:
.section .note.GNU-stack, "", %progbits
