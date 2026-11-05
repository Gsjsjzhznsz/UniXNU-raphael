/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Standalone raphael watchdog reset qualification, not a kernel driver.
 * Register semantics: pinned MiCode watchdog_v2.c; address: fresh live FDT.
 */
#include <stdint.h>
#include <string.h>
#include <libfdt.h>
#include "watchdog-policy.h"
static uint32_t read32(uint32_t offset) { return *(volatile uint32_t *)(uintptr_t)(WATCHDOG_BASE+offset); }
static void write32(uint32_t offset,uint32_t value) {
 *(volatile uint32_t *)(uintptr_t)(WATCHDOG_BASE+offset)=value;
 __asm__ volatile("dsb sy" ::: "memory");
}
void reset_main(const void *fdt) {
 if((uintptr_t)fdt&7||fdt_check_header(fdt)||fdt_totalsize(fdt)>1024*1024)return;
 int n=fdt_node_offset_by_compatible(fdt,-1,"qcom,msm-watchdog"),length=0;
 if(n<0||fdt_node_offset_by_compatible(fdt,n,"qcom,msm-watchdog")!=-FDT_ERR_NOTFOUND)return;
 int parent=fdt_parent_offset(fdt,n);
 if(parent<0||fdt_address_cells(fdt,parent)!=1||fdt_size_cells(fdt,parent)!=1)return;
 const fdt32_t *reg=fdt_getprop(fdt,n,"reg",&length);
 if(!reg||length!=8||fdt32_to_cpu(reg[0])!=WATCHDOG_BASE||fdt32_to_cpu(reg[1])!=4096)return;
 // Do not change secure-watchdog policy, PMIC, reset routing or dump controls.
 write32(0x08,0);
 write32(0x10,WATCHDOG_HZ*WATCHDOG_SECONDS);
 write32(0x14,WATCHDOG_HZ*(WATCHDOG_SECONDS+1));
 write32(0x08,1); // EN only; UNMASKED_INT_EN is deliberately clear.
 write32(0x04,1);
 if((read32(0x08)&3)!=1||read32(0x10)!=WATCHDOG_HZ*WATCHDOG_SECONDS||read32(0x14)!=WATCHDOG_HZ*(WATCHDOG_SECONDS+1))return;
 // No SMC, HVC or software deadline exists in this qualification Image.
 // The CPU stays here until external hardware resets it.
 for(;;)__asm__ volatile("yield");
}
