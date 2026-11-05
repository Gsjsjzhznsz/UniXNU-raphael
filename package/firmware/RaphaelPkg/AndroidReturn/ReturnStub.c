/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Relocatable Android diagnostic return. Decoder is the pinned unmodified Mu
 * LZMA SDK; all physical ranges are validated by SEC before this code is copied.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "Wire.h"
#include "LzmaDec.h"
_Static_assert(sizeof(struct rph_return_policy)==96,"policy ABI");
_Static_assert(offsetof(struct rph_return_state,Arch)==128,"arch ABI");
_Static_assert(offsetof(struct rph_return_state,LowBase)==96,"cache ABI");
_Static_assert(offsetof(struct rph_return_state,HighBase)==112,"high ABI");
_Static_assert(offsetof(struct rph_return_state,Conduit)==280,"conduit ABI");
_Static_assert(offsetof(struct rph_return_state,AuxBase)==328,"aux cache ABI");
_Static_assert(sizeof(struct rph_return_state)==344,"state ABI");
extern unsigned char return_scratch[] __attribute__((visibility("hidden")));
extern void ReturnStubResume(struct rph_return_state *) __attribute__((visibility("hidden"),noreturn));
struct allocator {ISzAlloc Interface;size_t Used;};
static void *reserve(ISzAllocPtr p,size_t bytes) {
 struct allocator *a=(struct allocator *)(uintptr_t)p;
 size_t at=(a->Used+15U)&~15U;
 if(at>RPH_RETURN_SCRATCH_BYTES||bytes>RPH_RETURN_SCRATCH_BYTES-at)return NULL;
 a->Used=at+bytes;return return_scratch+at;
}
static void release(ISzAllocPtr p,void *address){(void)p;(void)address;}
uint32_t ReturnCrc32(const void *data,size_t bytes) {
 uint32_t table[256];
 for(unsigned i=0;i<256;++i){uint32_t v=i;for(unsigned j=0;j<8;++j)v=(v>>1)^((v&1U)?0xedb88320U:0);table[i]=v;}
 const unsigned char *p=data;uint32_t crc=~0U;
 while(bytes--)crc=(crc>>8)^table[(crc^*p++)&255U];
 return ~crc;
}
static void wire(struct rph_return_state *s,unsigned index,uint64_t value) {
 unsigned char *p=(void *)(uintptr_t)s->Wire;
 if(!p)return;
 for(unsigned i=0;i<8;++i)p[index*8+i]=(unsigned char)(value>>(56-i*8));
}
int ReturnStubDecode(struct rph_return_state *s) {
 if(!s||s->Magic!=RPH_RETURN_STATE_MAGIC||s->Version!=RPH_RETURN_STATE_VERSION||s->SourceBytes<13||!s->KernelBytes||s->KernelBytes>s->ImageBytes)return 1;
 const unsigned char *source=(void *)(uintptr_t)s->Source;unsigned char *dest=(void *)(uintptr_t)s->Output;
 s->ActualSourceCrc=ReturnCrc32(source,(size_t)s->SourceBytes);wire(s,7,s->ActualSourceCrc);
 if(s->ActualSourceCrc!=s->SourceCrc)return 2;
 struct allocator allocator={{reserve,release},0};
 SizeT output=(SizeT)s->KernelBytes,input=(SizeT)s->SourceBytes-13;ELzmaStatus status=LZMA_STATUS_NOT_SPECIFIED;
 SRes result=LzmaDecode(dest,&output,source+13,&input,source,5,LZMA_FINISH_END,&status,&allocator.Interface);
 s->DecodedBytes=output;s->DecoderStatus=(uint64_t)(unsigned)status;wire(s,8,output);wire(s,9,(uint64_t)(unsigned)status);
 if(result!=SZ_OK||output!=s->KernelBytes||input!=s->SourceBytes-13||status!=LZMA_STATUS_FINISHED_WITH_MARK)return 3;
 s->ActualKernelCrc=ReturnCrc32(dest,(size_t)s->KernelBytes);wire(s,4,s->ActualKernelCrc);
 if(s->ActualKernelCrc!=s->KernelCrc)return 4;
 // Recreate the original Image's zero tail before Android clears its own BSS.
 memset(dest+output,0,(size_t)(s->ImageBytes-output));wire(s,1,3);
 return 0;
}
#if defined(__aarch64__)
static __attribute__((noreturn)) void reset_failed(struct rph_return_state *s) {
 register uint64_t x0 __asm__("x0")=0x84000009U;
 register uint64_t x1 __asm__("x1")=0,x2 __asm__("x2")=0,x3 __asm__("x3")=0;
#if RPH_RETURN_QEMU
 if(s->Conduit==2)__asm__ volatile("hvc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
 else
#else
 (void)s;
#endif
 __asm__ volatile("smc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
 for(;;)__asm__ volatile("wfe");
}
void ReturnStubAbort(struct rph_return_state *s) { reset_failed(s); }
void ReturnStubMain(struct rph_return_state *s) {
 if(ReturnStubDecode(s))reset_failed(s);
 ReturnStubResume(s);
}
#endif
