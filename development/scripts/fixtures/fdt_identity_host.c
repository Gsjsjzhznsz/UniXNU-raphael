// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libfdt.h>
typedef uint64_t UINT64;
typedef uint32_t UINT32;
typedef size_t UINTN;
typedef int32_t INT32;
typedef int BOOLEAN;
#define STATIC static
#define CONST const
#define VOID void
#define TRUE 1
#define FALSE 0
#define MAX_UINT64 UINT64_MAX
#define FdtParentOffset fdt_parent_offset
#define FdtAddressCells fdt_address_cells
#define FdtSizeCells fdt_size_cells
#define FdtGetProp fdt_getprop
#define SwapBytes32 __builtin_bswap32
static uint32_t ReadUnaligned32(const uint32_t *p) { uint32_t v; memcpy(&v,p,4); return v; }
#include <RaphaelFdtIdentity.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line %d failed\n",__LINE__);return 1;}++checks;}while(0)
int main(int argc,char **argv) {
 if(argc!=2)return 2;
 FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
 void *source=malloc(n),*tree=malloc(n+4096);if(!source||!tree)return 2;
 if(fread(source,1,n,f)!=(size_t)n)return 2;fclose(f);
 unsigned checks=0;CHECK(!fdt_open_into(source,tree,n+4096));
 int node=fdt_node_offset_by_compatible(tree,-1,"qcom,msm-watchdog");CHECK(node>=0);
 int bus=fdt_parent_offset(tree,node),len;const fdt32_t *reg=fdt_getprop(tree,node,"reg",&len);
 CHECK(reg&&len==8);uint64_t base=fdt32_to_cpu(reg[0]),bytes=fdt32_to_cpu(reg[1]);
 const void *ranges=fdt_getprop(tree,bus,"ranges",&len);CHECK(ranges&&len==16);
 CHECK(RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 fdt32_t identity[8]={0,0,0,cpu_to_fdt32(UINT32_MAX),0,0,0,cpu_to_fdt32(UINT32_MAX)};
 CHECK(!fdt_setprop(tree,bus,"ranges",identity,16));CHECK(RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 CHECK(!fdt_setprop(tree,bus,"ranges",NULL,0));CHECK(RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 CHECK(!fdt_delprop(tree,bus,"ranges"));CHECK(!RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 CHECK(!fdt_setprop(tree,bus,"ranges",identity,12));CHECK(!RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 identity[2]=cpu_to_fdt32(4096);
 CHECK(!fdt_setprop(tree,bus,"ranges",identity,16));CHECK(!RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 identity[2]=0;identity[3]=cpu_to_fdt32(base+bytes-1);
 CHECK(!fdt_setprop(tree,bus,"ranges",identity,16));CHECK(!RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 identity[3]=cpu_to_fdt32(UINT32_MAX);
 CHECK(!fdt_setprop(tree,bus,"ranges",identity,32));CHECK(!RaphaelFdtRootIdentityRange(tree,bus,base,bytes));
 CHECK(!RaphaelFdtRootIdentityRange(tree,node,base,bytes));
 CHECK(!RaphaelFdtRootIdentityRange(tree,bus,UINT64_MAX-1,4096));
 printf("FDT_IDENTITY_OK %u checks; live watchdog base=0x%llx\n",checks,(unsigned long long)base);
 free(tree);free(source);return 0;
}
