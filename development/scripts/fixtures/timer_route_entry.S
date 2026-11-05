// SPDX-License-Identifier: BSD-2-Clause-Patent
// Emulator-only initial conditions. Values are generated from QEMU's own DTB.
// This file is not linked into the FD or any handset image.
.text
.global qemu_timer_route_entry
qemu_timer_route_entry:
 mov x9,#0xf0
 msr icc_pmr_el1,x9
 isb
 ldr x9,=QEMU_GICR+0x10080
 mov w10,#QEMU_TIMER_MASK
 str w10,[x9]
 ldr x9,=QEMU_GICR+0x14
 str wzr,[x9]
 dsb sy
 mov x11,#0xffff
1:
 ldr w10,[x9]
 tbz w10,#2,2f
 subs x11,x11,#1
 b.ne 1b
2:
 ldr x9,=QEMU_FD
 br x9
.ltorg
