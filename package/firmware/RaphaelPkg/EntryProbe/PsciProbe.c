/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Standard PSCI query only, no reset or hardware-specific register accesses.
 * IDs: pinned MdePkg/Include/IndustryStandard/ArmStdSmc.h; conduit: live FDT.
 */
#define EntryProbeMain OriginalEntryProbeMain
#include "EntryProbe.c"
#undef EntryProbeMain
#include <string.h>
#ifndef ALLOW_QEMU_HVC
#define ALLOW_QEMU_HVC 0
#endif
static uint64_t query(uint64_t id,uint64_t argument,int hvc) {
 register uint64_t x0 __asm__("x0")=id,x1 __asm__("x1")=argument;
 register uint64_t x2 __asm__("x2")=0,x3 __asm__("x3")=0;
 if(hvc) {
#if ALLOW_QEMU_HVC
  __asm__ volatile("hvc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
#else
  return UINT64_MAX;
#endif
 } else {
  __asm__ volatile("smc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
 }
 return (uint32_t)x0;
}
void *EntryProbeMain(const struct entry_state *s) {
 void *fdt=OriginalEntryProbeMain(s);
 if(fdt!=probe_fdt||s->current_el!=4)return fdt;
 int psci=fdt_path_offset(fdt,"/psci"),len=0;
 if(psci<0||fdt_node_check_compatible(fdt,psci,"arm,psci-1.0"))return fdt;
 const char *method=fdt_getprop(fdt,psci,"method",&len);int conduit=0;
 if(method&&len==4&&!memcmp(method,"smc",4))conduit=1;
 if(ALLOW_QEMU_HVC&&method&&len==4&&!memcmp(method,"hvc",4))conduit=2;
 if(!conduit)return fdt;
 uint64_t version=query(0x84000000,0,conduit==2),feature=UINT32_MAX;
 if((version>>16)>=1&&(version>>16)<0x8000)feature=query(0x8400000a,0x84000009,conduit==2);
 fdt64_t record[]={cpu_to_fdt64(1),cpu_to_fdt64(conduit),cpu_to_fdt64(version),cpu_to_fdt64(feature),cpu_to_fdt64(s->current_el),cpu_to_fdt64(0)};
 size_t capacity=(size_t)(probe_storage_end-probe_fdt);
 if(fdt_open_into(fdt,fdt,(int)capacity))return fdt;
 int chosen=fdt_path_offset(fdt,"/chosen");
 if(chosen>=0)fdt_setprop(fdt,chosen,"raphael,psci-query",record,sizeof(record));
 fdt_pack(fdt);return fdt;
}
