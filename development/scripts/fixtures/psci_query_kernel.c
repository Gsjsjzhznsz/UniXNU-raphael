/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#define fixture_main StandardFixture
#include "entry_probe_kernel.c"
#undef fixture_main
void fixture_main(const void *fdt,const unsigned char *image) {
 int len,n=fdt_node_offset_by_compatible(fdt,-1,"arm,pl011");
 const fdt32_t *reg=fdt_getprop(fdt,n,"reg",&len);
 if(!reg||len!=16)for(;;)__asm__ volatile("wfe");
 uart=(volatile uint32_t *)(uintptr_t)(((uint64_t)fdt32_to_cpu(reg[0])<<32)|fdt32_to_cpu(reg[1]));
 n=fdt_path_offset(fdt,"/chosen");const fdt64_t *q=fdt_getprop(fdt,n,"raphael,psci-query",&len);
 check(q&&len==48,"PSCI query record");
 if(q&&len==48){
  check(fdt64_to_cpu(q[0])==1&&fdt64_to_cpu(q[1])==2,"QEMU FDT HVC conduit");
  uint64_t v=fdt64_to_cpu(q[2]);check((v>>16)>=1&&(v>>16)<0x8000,"PSCI VERSION >= 1.0");
  check(fdt64_to_cpu(q[3])==0,"PSCI FEATURES SYSTEM_RESET");
  check(fdt64_to_cpu(q[4])==4&&fdt64_to_cpu(q[5])==0,"EL1 query, no reset call");
 }
 StandardFixture(fdt,image);
}
