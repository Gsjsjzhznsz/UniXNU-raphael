/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Emulator-only Linux-protocol receiver. Contains no handset addresses.
 */
.section .text.entry, "ax"
.global fixture_header
fixture_header:
  b fixture_entry
  .long 0
  .quad 0x80000
  .quad fixture_image_size
  .quad 0xa
  .quad 0, 0, 0
  .ascii "ARM\x64"
  .long 0
fixture_entry:
  adrp x1, fixture_header
  add x1, x1, :lo12:fixture_header
  adrp x9, fixture_stack_end
  add x9, x9, :lo12:fixture_stack_end
  mov sp, x9
  bl fixture_main
1: wfe
  b 1b
.section .data.storage, "aw"
.balign 16
  .space 16384
fixture_stack_end:
.section .note.GNU-stack, "", %progbits
