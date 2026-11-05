/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include <stdint.h>
#include <string.h>
#include <libfdt.h>
#ifndef QEMU_HVC_RESET
#define QEMU_HVC_RESET 0
#endif
static void log_qemu(const char *message) {
#if QEMU_HVC_RESET
 register uint64_t x0 __asm__("x0")=4;
 register const char *x1 __asm__("x1")=message;
 __asm__ volatile("hlt #0xf000":"+r"(x0),"+r"(x1)::"memory");
#else
 (void)message;
#endif
}
static uint32_t psci(uint64_t function,uint64_t argument,int hvc) {
 register uint64_t x0 __asm__("x0")=function,x1 __asm__("x1")=argument;
 register uint64_t x2 __asm__("x2")=0,x3 __asm__("x3")=0;
#if QEMU_HVC_RESET
 if(hvc)__asm__ volatile("hvc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
 else
#else
 (void)hvc;
#endif
 __asm__ volatile("smc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
 return (uint32_t)x0;
}
void reset_main(const void *fdt) {
 if((uintptr_t)fdt&7||fdt_check_header(fdt)||fdt_totalsize(fdt)>1024*1024)return;
 int n=fdt_path_offset(fdt,"/psci"),len=0,conduit=0;
 if(n<0||fdt_node_check_compatible(fdt,n,"arm,psci-1.0"))return;
 const char *method=fdt_getprop(fdt,n,"method",&len);
 if(method&&len==4&&!memcmp(method,"smc",4))conduit=1;
 if(QEMU_HVC_RESET&&method&&len==4&&!memcmp(method,"hvc",4))conduit=2;
 if(!conduit)return;
 uint32_t version=psci(0x84000000,0,conduit==2);
 if(version>>16<1||version>>16>=0x8000||psci(0x8400000a,0x84000009,conduit==2)!=0)return;
 uint64_t frequency,start,now;
 __asm__ volatile("mrs %0,cntfrq_el0":"=r"(frequency));
 __asm__ volatile("mrs %0,cntpct_el0":"=r"(start));
 if(!frequency||frequency>UINT64_MAX/3)return;
 log_qemu("PSCI_RESET_READY three-second counter deadline\n");
 do {__asm__ volatile("mrs %0,cntpct_el0":"=r"(now));__asm__ volatile("yield");}while(now-start<frequency*3);
 log_qemu("PSCI_SYSTEM_RESET_CALL\n");
 psci(0x84000009,0,conduit==2);
 log_qemu("PSCI_RESET_RETURNED_UNEXPECTEDLY\n");
}
