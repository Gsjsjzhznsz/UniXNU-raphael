/* SPDX-License-Identifier: BSD-2-Clause-Patent */
ENTRY(handoff_start)
SECTIONS {
 . = 0;
 .text : { KEEP(*(.text.entry)) *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) *(.got*) }
 .bss : { *(.bss*) *(COMMON) }
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
 ASSERT(. <= 0x1c000, "Synthetic receiver must fit segment and keep final 16 KiB untouched")
}
