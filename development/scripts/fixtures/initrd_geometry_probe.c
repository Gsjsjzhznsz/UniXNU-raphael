/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#define EntryProbeMain BaseEntryProbeMain
#include "../../UniXNU-raphael/package/firmware/RaphaelPkg/EntryProbe/EntryProbe.c"
#undef EntryProbeMain
static uint64_t address(const void *fdt,int node,const char *name){int len;const fdt32_t *p=fdt_getprop(fdt,node,name,&len);if(!p||(len!=4&&len!=8))return 0;return len==8?((uint64_t)fdt32_to_cpu(p[0])<<32)|fdt32_to_cpu(p[1]):fdt32_to_cpu(p[0]);}
void *EntryProbeMain(const struct entry_state *s){
 void *copy=BaseEntryProbeMain(s);if(copy==(void *)(uintptr_t)s->x0)return copy;
 int chosen=fdt_path_offset(copy,"/chosen");uint64_t start=address(copy,chosen,"linux,initrd-start"),end=address(copy,chosen,"linux,initrd-end");
 if(!start||end<=start||end-start!=PROBE_EXPANDED_RAMDISK_BYTES)return copy;
 uint64_t words[6]={cpu_to_fdt64(1),cpu_to_fdt64(start),cpu_to_fdt64(end),cpu_to_fdt64(PROBE_ORIGINAL_RAMDISK_BYTES),cpu_to_fdt64(s->x0),cpu_to_fdt64(s->image_base)};
 if(fdt_open_into(copy,copy,(int)(probe_storage_end-probe_fdt)))return copy;
 chosen=fdt_path_offset(copy,"/chosen");int len;const void *old=fdt_getprop(copy,chosen,"linux,initrd-end",&len);uint64_t be=cpu_to_fdt64(start+PROBE_ORIGINAL_RAMDISK_BYTES);uint32_t be32=cpu_to_fdt32((uint32_t)(start+PROBE_ORIGINAL_RAMDISK_BYTES));
 if(!old||(len!=4&&len!=8)||fdt_setprop(copy,chosen,"linux,initrd-end",len==8?(void *)&be:(void *)&be32,len)||fdt_setprop(copy,chosen,"raphael,initrd-geometry",words,sizeof(words))||fdt_pack(copy))return copy;
 return copy;
}
