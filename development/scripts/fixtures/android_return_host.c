/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "Wire.h"
unsigned char return_scratch[RPH_RETURN_SCRATCH_BYTES];
extern int ReturnStubDecode(struct rph_return_state *);
extern uint32_t ReturnCrc32(const void *,size_t);
static unsigned char *read_file(const char *name,size_t *size){FILE *f=fopen(name,"rb");if(!f)exit(2);fseek(f,0,SEEK_END);*size=ftell(f);rewind(f);unsigned char *p=malloc(*size);if(!p||fread(p,1,*size,f)!=*size)exit(2);fclose(f);return p;}
#define CHECK(v) do{if(!(v)){fprintf(stderr,"failure line %d\n",__LINE__);exit(1);}++checks;}while(0)
int main(int argc,char **argv){if(argc!=3)return 2;size_t n,m;unsigned char *src=read_file(argv[1],&n),*expected=read_file(argv[2],&m),*out=malloc(m+4096);unsigned checks=0;uint64_t wire[10]={0};
struct rph_return_state original={.Magic=RPH_RETURN_STATE_MAGIC,.Version=RPH_RETURN_STATE_VERSION,.Source=(uintptr_t)src,.SourceBytes=n,.SourceCrc=ReturnCrc32(src,n),.Output=(uintptr_t)out,.KernelBytes=m,.ImageBytes=m+4096,.KernelCrc=ReturnCrc32(expected,m),.Wire=(uintptr_t)wire},s;
memset(out,0x55,m+4096);s=original;CHECK(ReturnStubDecode(&s)==0);CHECK(s.DecodedBytes==m);CHECK(!memcmp(out,expected,m));for(unsigned i=0;i<4096;++i)CHECK(out[m+i]==0);
s=original;src[n/2]^=1;memset(out,0x55,m+4096);CHECK(ReturnStubDecode(&s)==2);CHECK(out[0]==0x55);src[n/2]^=1;
s=original;s.SourceBytes-=8;s.SourceCrc=ReturnCrc32(src,s.SourceBytes);CHECK(ReturnStubDecode(&s)==3);
s=original;s.KernelCrc^=1;CHECK(ReturnStubDecode(&s)==4);
s=original;s.KernelBytes-=16;CHECK(ReturnStubDecode(&s)==3);
s=original;s.ImageBytes=m-1;CHECK(ReturnStubDecode(&s)==1);
s=original;s.Magic=0;CHECK(ReturnStubDecode(&s)==1);
s=original;src[0]=255;s.SourceCrc=ReturnCrc32(src,n);CHECK(ReturnStubDecode(&s)==3);
printf("ANDROID_RETURN_HOST_OK %u checks\n",checks);free(out);free(src);free(expected);return 0;}
