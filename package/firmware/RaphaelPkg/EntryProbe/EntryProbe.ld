/* SPDX-License-Identifier: BSD-2-Clause-Patent */
ENTRY(_probe_start)
SECTIONS
{
  . = 0;
  .text : { KEEP(*(.text.entry)) *(.text*) }
  .rodata : { *(.rodata*) }
  .data : { *(.data*) }
  .got : { *(.got*) }
  .bss : { *(.bss*) *(COMMON) }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
ASSERT(SIZEOF(.bss) == 0, "Probe requires fully materialized image storage")
ASSERT(SIZEOF(.got) == 0, "Probe cannot use absolute GOT pointers")
