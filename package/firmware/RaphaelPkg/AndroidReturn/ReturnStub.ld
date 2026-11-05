/* SPDX-License-Identifier: BSD-2-Clause-Patent */
ENTRY(ReturnStubEntry)
SECTIONS {
 . = 0;
 .text : { KEEP(*(.text.entry)) *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) *(.got*) }
 .bss : { *(.bss*) *(COMMON) }
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
