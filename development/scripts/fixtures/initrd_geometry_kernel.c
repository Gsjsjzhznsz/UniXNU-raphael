/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#define fixture_main BaseFixture
#include "entry_probe_kernel.c"
#undef fixture_main
void fixture_main(const void *fdt,const unsigned char *image){
 int len,n=fdt_node_offset_by_compatible(fdt,-1,"arm,pl011");const fdt32_t *reg=fdt_getprop(fdt,n,"reg",&len);if(!reg||len<16)for(;;)__asm__ volatile("wfe");uart=(void *)(uintptr_t)(((uint64_t)fdt32_to_cpu(reg[0])<<32)|fdt32_to_cpu(reg[1]));
 n=fdt_path_offset(fdt,"/chosen");const fdt64_t *g=fdt_getprop(fdt,n,"raphael,initrd-geometry",&len);check(g&&len==48,"initrd geometry wire");if(g&&len==48){
 check(fdt64_to_cpu(g[0])==1&&fdt64_to_cpu(g[2])-fdt64_to_cpu(g[1])==12345+16*1024*1024,"original expanded initrd recorded");
 const fdt64_t *end=fdt_getprop(fdt,n,"linux,initrd-end",&len);check(end&&len==8&&fdt64_to_cpu(end[0])==fdt64_to_cpu(g[1])+12345,"original ramdisk span restored");
 }
 if(!failures)text("INITRD_GEOMETRY_OK\n");BaseFixture(fdt,image);
}
