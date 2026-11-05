/* SPDX-License-Identifier: BSD-2-Clause-Patent */
ENTRY(fixture_header)
SECTIONS
{
  . = 0;
  .text : { KEEP(*(.text.entry)) *(.text*) }
  .rodata : { *(.rodata*) }
  .data : { *(.data*) *(.got*) }
  .bss : { *(.bss*) *(COMMON) }
  fixture_image_size = ALIGN(., 65536);
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
