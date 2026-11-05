/* SPDX-License-Identifier: BSD-2-Clause-Patent */
/* Freestanding QEMU diagnostic receiver. Never an XNU kernel or phone payload. */
#include <stdint.h>
#include "BootArgs.h"
#include "HandoffState.h"
static unsigned failures,passes;
static void text(const char *s) {
 register uint64_t op __asm__("x0")=4;
 register const char *p __asm__("x1")=s;
 __asm__ volatile("hlt #0xf000":"+r"(op),"+r"(p)::"memory");
}
static void check(int ok,const char *name) {
 text(ok?"HANDOFF_PASS ":"HANDOFF_FAIL ");text(name);text("\n");
 if(ok)++passes;else ++failures;
}
static uint32_t crc32(const unsigned char *p,UINTN n,UINTN zero_at) {
 uint32_t crc=~0U;
 for(UINTN i=0;i<n;++i){crc^=(i>=zero_at&&i-zero_at<16)?0:p[i];for(unsigned b=0;b<8;++b)crc=(crc>>1)^(0xedb88320U&-(crc&1));}
 return ~crc;
}
static uint64_t probe_pointer(const char *s) {
 const char prefix[]="probe=";for(unsigned i=0;i<6;++i)if(s[i]!=prefix[i])return 0;
 uint64_t value=0;
 for(unsigned i=6;i<22;++i){unsigned c=(unsigned char)s[i],v;if(c>='0'&&c<='9')v=c-'0';else if(c>='a'&&c<='f')v=c-'a'+10;else if(c>='A'&&c<='F')v=c-'A'+10;else return 0;value=(value<<4)|v;}
 return s[22]==0?value:0;
}
static uint32_t u32(const unsigned char *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t u64(const unsigned char *p) {return u32(p)|(uint64_t)u32(p+4)<<32;}
static int eq(const unsigned char *p,UINTN n,const char *s) {UINTN i=0;while(i<n&&s[i]&&p[i]==(unsigned char)s[i])++i;return i<n&&p[i]==0&&s[i]==0&&i+1==n;}
static int adt_node(const unsigned char *p,UINTN n,UINTN *off,unsigned depth,unsigned parent,UINTN *ram) {
 if(depth>64||*off>n||n-*off<8)return 0;
 unsigned props=u32(p+*off),children=u32(p+*off+4);*off+=8;
 if(props>(n-*off)/36)return 0;
 unsigned path=3;const unsigned char *name=0;UINTN namelen=0,candidate=(UINTN)-1;
 for(unsigned i=0;i<props;++i) {
  if(n-*off<36)return 0;const unsigned char *key=p+*off;UINTN len=u32(key+32);*off+=36;
  if(len>n-*off)return 0;
  if(eq(key,5,"name")){if(name)return 0;name=p+*off;namelen=len;}
  if(eq(key,8,"RAMDisk")){if(candidate!=(UINTN)-1||len!=16)return 0;candidate=*off;}
  *off=(*off+len+3)&~(UINTN)3;if(*off>n)return 0;
 }
 if(!name)return 0;
 if(depth==0)path=0;
 if(depth==1&&parent==0&&eq(name,namelen,"chosen"))path=1;
 if(depth==2&&parent==1&&eq(name,namelen,"memory-map"))path=2;
 if(candidate!=(UINTN)-1){if(path!=2||*ram!=(UINTN)-1)return 0;*ram=candidate;}
 if(children>(n-*off)/8)return 0;
 for(unsigned i=0;i<children;++i)if(!adt_node(p,n,off,depth+1,path,ram))return 0;
 return 1;
}
void handoff_main(const DARWIN_BOOT_ARGS *a,uint64_t el,uint64_t sctlr,uint64_t daif,uint64_t pc) {
 check(el==4,"entry at EL1");
 check((sctlr&0x1005)==0,"MMU data and instruction caches disabled");
 check((daif&0x3c0)==0x3c0,"debug SError IRQ FIQ masked");
 check(((uintptr_t)a&0x3fff)==0,"x0 boot_args 16KiB aligned");
 check(a->Revision==2&&a->Version==2,"boot_args ABI revision and version 2");
 check(a->VirtualBase==HANDOFF_VIRTUAL_BASE,"synthetic virtual base preserved");
 check(a->PhysicalBase==pc&&(pc&0x1fffff)==0,"branch at relocated 2MiB aligned segment base");
 check(a->MemorySize==HANDOFF_WINDOW_BYTES&&a->MemorySizeActual==HANDOFF_WINDOW_BYTES,"real owned 256MiB allocation window");
 check((uintptr_t)a==pc+HANDOFF_SEGMENT_BYTES,"boot_args follows synthetic segment");
 check(a->TopOfKernelData>(uintptr_t)a&&a->TopOfKernelData<=pc+HANDOFF_WINDOW_BYTES&&!(a->TopOfKernelData&0x3fff),"kernel data top within window and aligned");
 check(a->DeviceTree>a->VirtualBase&&a->DeviceTree-a->VirtualBase<HANDOFF_WINDOW_BYTES,"ADT virtual pointer bounded");
 uint64_t state_pa=probe_pointer(a->CommandLine);
 check(state_pa!=0&&!(state_pa&4095),"command line notice pointer copied");
 const HANDOFF_STATE *state=(const void *)(uintptr_t)state_pa;
 if(state_pa) {
  check(state->Magic==HANDOFF_MAGIC&&state->Version==1&&state->Bytes==sizeof(*state),"independent notice page intact");
  check(state->ExitCount==1,"ExitBootServices notification observed exactly once");
  uint64_t tree_pa=pc+a->DeviceTree-a->VirtualBase;
  check(tree_pa==(uintptr_t)a+4096,"ADT physical relocation matches boot_args");
  check(a->DeviceTreeLength==state->TreeBytes&&a->DeviceTreeLength>0&&a->DeviceTreeLength<=4096,"ADT length preserved");
  if(a->DeviceTreeLength&&a->DeviceTreeLength<=4096) {
   const unsigned char *tree=(const void *)(uintptr_t)tree_pa;UINTN off=0,ram=(UINTN)-1;
   int valid=adt_node(tree,a->DeviceTreeLength,&off,0,3,&ram)&&off==a->DeviceTreeLength;
   check(valid,"independent ADT structure and RAMDisk path parser");
   check(crc32(tree,a->DeviceTreeLength,ram)==state->TreeCrc,"ADT CRC matches original with only RAMDisk pair patched");
   if(state->RamdiskBytes) {
    check(valid&&ram!=(UINTN)-1,"RAMDisk property present under chosen memory-map");
    if(valid&&ram!=(UINTN)-1) {
     uint64_t base=u64(tree+ram),bytes=u64(tree+ram+8),expected=(state->RamdiskBytes+4095)&~4095ULL;
     int bounded=base>=pc&&base-pc<HANDOFF_WINDOW_BYTES&&bytes<=HANDOFF_WINDOW_BYTES-(base-pc)&&bytes==expected;
     check(bounded&&base==((tree_pa+a->DeviceTreeLength+4095)&~4095ULL),"RAMDisk pair uses physical relocated bounded allocation");
     if(bounded) {
      const unsigned char *data=(const void *)(uintptr_t)base;
      check(crc32(data,state->RamdiskBytes,(UINTN)-1)==state->RamdiskCrc,"raw or sparse-expanded RAMDisk matches independent expected bytes");
      int zero=1;for(UINTN i=state->RamdiskBytes;i<bytes;++i)if(data[i])zero=0;
      check(zero,"RAMDisk page padding is zero");
     }
    }
   }else check(valid&&ram==(UINTN)-1,"no RAMDisk property when request has no initrd");
  }
 }
 int video_zero=1;for(unsigned i=0;i<6;++i)if(a->Video[i])video_zero=0;
 check(video_zero,"headless firmware video fields zero");
 check(a->MachineType==0&&a->BootFlags==0,"unspecified machine and flags remain zero");
 check(*(volatile const uint64_t *)(uintptr_t)(pc+HANDOFF_SEGMENT_BYTES-8)==0,"zero-filled segment tail");
 text(failures?"HANDOFF_RECEIVER_FAILED\n":"HANDOFF_RECEIVER_OK\n");
 uint64_t status[2]={0x20026,failures};
 register uint64_t op __asm__("x0")=0x20;
 register void *p __asm__("x1")=status;
 __asm__ volatile("hlt #0xf000":"+r"(op),"+r"(p)::"memory");
 for(;;)__asm__ volatile("wfe");
}
