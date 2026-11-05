// SPDX-License-Identifier: BSD-2-Clause-Patent
// Polling explicitly bounded command experiment, cache/MMU off; no PHY or SMMU writes.
extern "C" {
#include <RaphaelUfsRead.h>
#include <Library/FdtLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <RaphaelFdtIdentity.h>
#include <PiPei.h>
#include <Library/PrePiLib.h>
#include <Library/PcdLib.h>
}
#include <RaphaelUfsTransport.h>
#include <RaphaelUfsWritePolicy.h>
#include <RaphaelUfsDmaGate.h>
#include <RaphaelExtentPlan.h>
#include <RaphaelPayloadHash.h>
using namespace RaphaelUfs;
static UINT8 mDma[8192] __attribute__((aligned(4096),section(".data")))={1};
static UINT32 read32(UINT64 a){UINT32 v;__asm__ volatile("dmb sy":::"memory");v=*(volatile UINT32 *)(UINTN)a;__asm__ volatile("dmb sy":::"memory");return v;}
static void write32(UINT64 a,UINT32 v){*(volatile UINT32 *)(UINTN)a=v;__asm__ volatile("dsb sy":::"memory");}
static UINT64 ticks(){UINT64 v;__asm__ volatile("mrs %0,cntpct_el0":"=r"(v));return v;}
static UINT64 cells(const UINT8 *p){return ((UINT64)p[0]<<24)|((UINT64)p[1]<<16)|((UINT64)p[2]<<8)|p[3];}
// All valid entries in the current APPS SMMU must be bypass/fault or a disabled
// stage-1 context with stage-2 bypass. This is a conservative DMA safety gate,
// not proof of the UFS stream ID or permission to reprogram any SMMU context.
static bool noActiveTranslation(const VOID *f,UINT64 *validCount,UINT64 *reason){
 *reason=10;
 INT32 n=FdtPathOffset(f,"/soc/apps-smmu@0x15000000"),l;
 if(n<0)return false;
 const UINT8 *p=(const UINT8 *)FdtGetProp(f,n,"reg-names",&l);
 if(!p||l<5||p[0]!='b'||p[1]!='a'||p[2]!='s'||p[3]!='e'||p[4])return false;
 // The current binding has base plus tcu-base; only the named base tuple is
 // accessed. The auxiliary TCU window is neither mapped nor used.
 p=(const UINT8 *)FdtGetProp(f,n,"reg",&l);if(!p||l<8||l%8)return false;
 *reason=11;
 UINT64 base=cells(p),size=cells(p+4);INT32 parent=FdtParentOffset(f,n);
 if(!base||(base&4095)||size<0x4000||(size&1)||parent<0||!RaphaelFdtRootIdentityRange(f,parent,base,size))return false;
 // Current binding has an always accessible TCU path; do not enable clocks.
 if(FdtGetProp(f,n,"clocks",&l)||FdtGetProp(f,n,"qcom,enable-static-cb",&l)||FdtGetProp(f,n,"calxeda,smmu-secure-config-access",&l))return false;
 uint64_t valid=0,why=0;bool safe=RaphaelUfs::noActiveTranslation(read32,base,size,valid,why);
 *validCount=valid;*reason=why;return safe;
}

static bool allOthersOff(const VOID *f,UINT64 *count,UINT64 *off){
 INT32 psci=FdtPathOffset(f,"/psci"),cpus=FdtPathOffset(f,"/cpus"),l;
 const CHAR8 *method=psci<0?nullptr:(const CHAR8 *)FdtGetProp(f,psci,"method",&l);
 if(!method||l!=4||method[0]!='s'||method[1]!='m'||method[2]!='c'||method[3]||cpus<0||FdtAddressCells(f,cpus)!=2||FdtSizeCells(f,cpus)!=0)return false;
 UINT64 mpidr;__asm__ volatile("mrs %0,mpidr_el1":"=r"(mpidr));mpidr&=0xff00ffffffULL;bool self=false;
 for(INT32 n=FdtFirstSubnode(f,cpus);n>=0;n=FdtNextSubnode(f,n)){
  const UINT8 *p=(const UINT8 *)FdtGetProp(f,n,"reg",&l);if(!p)continue;if(l!=8)return false;
  UINT64 affinity=(cells(p)<<32)|cells(p+4);if(affinity&~0xff00ffffffULL||++*count>8)return false;
  register UINT64 x0 __asm__("x0")=0xc4000004ULL;
  register UINT64 x1 __asm__("x1")=affinity;
  register UINT64 x2 __asm__("x2")=0;
  register UINT64 x3 __asm__("x3")=0;
  __asm__ volatile("smc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
  if(affinity==mpidr){if(self||x0!=0)return false;self=true;}
  else {if(x0!=1)return false;++*off;}
 }
 return self&&*count==8&&*off==7;
}
struct Backend {
 UINT64 base,freq;
 UINT32 read(unsigned off){return read32(base+off);}void write(unsigned off,UINT32 v){write32(base+off,v);}
 bool dmaAllowed(uint64_t a,uint64_t n){UINT64 b=(UINTN)mDma;return a>=b&&a<=b+sizeof(mDma)&&n<=b+sizeof(mDma)-a;}
 bool toDevice(uint64_t a,const void *p,size_t n){if(!dmaAllowed(a,n))return false;CopyMem((VOID *)(UINTN)a,p,n);__asm__ volatile("dsb sy":::"memory");return true;}
 bool fromDevice(uint64_t a,void *p,size_t n){if(!dmaAllowed(a,n))return false;__asm__ volatile("dsb sy":::"memory");CopyMem(p,(VOID *)(UINTN)a,n);return true;}
 uint64_t nowUs(){UINT64 t=ticks();return t/freq*1000000+(t%freq)*1000000/freq;}
 void pause(){__asm__ volatile("yield");}
};
static RaphaelStorage::ExtentPlan mExtentPlan __attribute__((section(".data")))={};
static const RaphaelStorage::ExtentPlan *extentPlan(){
 static EFI_GUID guid __attribute__((aligned(8),section(".data")))={0x74840a8b,0xe26a,0x42d1,{0x96,0x2a,0xdf,0x96,0xcc,0x83,0xcb,0x46}};
 EFI_PEI_FILE_HANDLE file;VOID *found=nullptr;
 UINT64 base=FixedPcdGet64(PcdRaphaelFdBase),end=base+FixedPcdGet32(PcdRaphaelFdSize);
 if(EFI_ERROR(FfsFindFileByName(&guid,(VOID *)(UINTN)base,&file))||EFI_ERROR(FfsFindSectionData(EFI_SECTION_RAW,file,&found)))return nullptr;
 UINT64 at=(UINTN)found;if(at<base+4||at>end||sizeof(RaphaelStorage::ExtentPlan)>end-at)return nullptr;
 auto *h=(EFI_COMMON_SECTION_HEADER *)(UINTN)(at-4);UINT32 n=h->Size[0]|(h->Size[1]<<8)|(h->Size[2]<<16);
 if(h->Type!=EFI_SECTION_RAW||n!=sizeof(RaphaelStorage::ExtentPlan)+4)return nullptr;
 CopyMem(&mExtentPlan,found,sizeof(mExtentPlan));return &mExtentPlan;
}
static RaphaelStorage::UfsWritePolicy mWritePolicy __attribute__((section(".data")))={};
static const RaphaelStorage::UfsWritePolicy *writePolicy(){
 static EFI_GUID guid __attribute__((aligned(8),section(".data")))={0xbedac149,0xd758,0x4984,{0xb0,0xd7,0x50,0x6f,0x21,0xb5,0x1b,0x16}};
 EFI_PEI_FILE_HANDLE file;VOID *found=nullptr;
 UINT64 base=FixedPcdGet64(PcdRaphaelFdBase),end=base+FixedPcdGet32(PcdRaphaelFdSize);
 if(EFI_ERROR(FfsFindFileByName(&guid,(VOID *)(UINTN)base,&file))||EFI_ERROR(FfsFindSectionData(EFI_SECTION_RAW,file,&found)))return nullptr;
 UINT64 at=(UINTN)found;if(at<base+4||at>end||sizeof(mWritePolicy)>end-at)return nullptr;
 auto *h=(EFI_COMMON_SECTION_HEADER *)(UINTN)(at-4);UINT32 n=h->Size[0]|(h->Size[1]<<8)|(h->Size[2]<<16);
 if(h->Type!=EFI_SECTION_RAW||n!=sizeof(mWritePolicy)+4)return nullptr;
 CopyMem(&mWritePolicy,found,sizeof(mWritePolicy));return &mWritePolicy;
}
static const UINT8 *payloadHashes(UINT64 bytes){
 static EFI_GUID guid __attribute__((aligned(8),section(".data")))={0x468ae3b7,0xf083,0x4e2c,{0xb9,0xb3,0xa6,0x72,0xbe,0x5a,0x46,0xd3}};
 EFI_PEI_FILE_HANDLE file;VOID *found=nullptr;
 UINT64 base=FixedPcdGet64(PcdRaphaelFdBase),end=base+FixedPcdGet32(PcdRaphaelFdSize);
 if(!bytes||bytes%4096||bytes>160*1024*1024||bytes<20*1024*1024)return nullptr;
 UINT64 expected=32+(bytes/4096)*32;
 if(EFI_ERROR(FfsFindFileByName(&guid,(VOID *)(UINTN)base,&file))||EFI_ERROR(FfsFindSectionData(EFI_SECTION_RAW,file,&found)))return nullptr;
 UINT64 at=(UINTN)found;if(at<base+4||at>end||expected>end-at)return nullptr;
 auto *h=(EFI_COMMON_SECTION_HEADER *)(UINTN)(at-4);UINT32 n=h->Size[0]|(h->Size[1]<<8)|(h->Size[2]<<16);
 if(h->Type!=EFI_SECTION_RAW||n!=expected+4)return nullptr;
 UINT64 header[4];CopyMem(header,found,32);
 if(header[0]!=0x3148534148505052ULL||header[1]!=1||header[2]!=bytes||header[3]!=bytes/4096)return nullptr;
 return static_cast<const UINT8 *>(found)+32;
}
// Authenticate quarantined staging only after the uncached DMA window ends.
// QEMU preloads the same buffer; it never claims successful phone DMA.
extern "C" BOOLEAN RaphaelVerifyPayloadMemory(UINT64 target,UINT64 bytes){
 if(!FixedPcdGetBool(PcdRaphaelUfsPayload))return FALSE;
 UINT64 sctlr;__asm__ volatile("mrs %0,sctlr_el1":"=r"(sctlr));if((sctlr&0x1005)!=0x1005)return FALSE;
 UINT64 end=FixedPcdGet64(PcdRaphaelArenaBase)+FixedPcdGet32(PcdRaphaelArenaSize);
 if(bytes!=FixedPcdGet32(PcdRaphaelNativeFatBytes)||bytes>end||target!=end-bytes||(target&4095))return FALSE;
 const UINT8 *hashes=payloadHashes(bytes);if(!hashes)return FALSE;
 return RaphaelStorage::verifyPayloadBlocks(reinterpret_cast<UINT8 *>(target),bytes,hashes);
}
static RaphaelStorage::ReadOnlyExtents mExtentDisk __attribute__((section(".data")));
struct ExtentBackend {
 Transport<Backend> &transport;UINT64 watchdog,begin,frequency;UINT64 reads=0;UINT64 budgetSeconds=8;
 bool readPhysicalBlock(uint64_t lba,uint8_t *out){
  if(ticks()-begin>frequency*budgetSeconds)return false;
  write32(watchdog+4,1);++reads;
  return transport.read(0,lba,1,out,4096)==Result::Ok;
 }
};
extern "C" VOID RaphaelUfsReadOnly(CONST VOID *F,CONST RAPHAEL_UFS_HANDOFF *H,UINT64 W,UINT64 Hz,UINT64 Frequency,UINT64 Lba,BOOLEAN QueryOnly,BOOLEAN ResetOnError,UINT64 Target,UINT64 TargetBytes,RAPHAEL_UFS_READ *O){
 ZeroMem(O,sizeof(*O));O->Word[0]=2;O->Word[1]=1;O->Word[30]=QueryOnly?1:0;
 const RaphaelStorage::UfsWritePolicy *write=nullptr;
 if(FixedPcdGetBool(PcdRaphaelUfsWriteProbe)){
  O->Word[0]=6;O->Word[18]=200;O->Word[30]=0;
  if(QueryOnly||FixedPcdGetBool(PcdRaphaelUfsExtents)||FixedPcdGetBool(PcdRaphaelUfsPayload)||Target||TargetBytes)return;
  write=writePolicy();if(!write||!RaphaelStorage::validateWritePolicy(*write,Lba))return;
 }
 const RaphaelStorage::ExtentPlan *plan=nullptr;
 if(FixedPcdGetBool(PcdRaphaelUfsExtents)){
  O->Word[0]=3;plan=extentPlan();
  if(!plan||QueryOnly||Lba||!RaphaelStorage::validatePlan(*plan,mExtentDisk))return;
 }
 const UINT8 *hashes=nullptr;
 if(FixedPcdGetBool(PcdRaphaelUfsPayload)){
  O->Word[0]=5;
  UINT64 end=FixedPcdGet64(PcdRaphaelArenaBase)+FixedPcdGet32(PcdRaphaelArenaSize);
  if(!plan||TargetBytes!=FixedPcdGet32(PcdRaphaelNativeFatBytes)||TargetBytes!=plan->fileBytes||TargetBytes>end||Target!=end-TargetBytes||(Target&4095))return;
  hashes=payloadHashes(TargetBytes);if(!hashes)return;
 }else if(Target||TargetBytes)return;
 if(H->Status!=3||Lba>0x00ffffffffffffffULL)return;O->Word[1]=2;
 UINT64 sctlr,daif;__asm__ volatile("mrs %0,sctlr_el1":"=r"(sctlr));__asm__ volatile("mrs %0,daif":"=r"(daif));
 if((sctlr&0x1005)||(daif&0xc0)!=0xc0||!Frequency||!W||!Hz||Hz>MAX_UINT32/21)return;
 INT32 n=FdtNodeOffsetByCompatible(F,-1,"qcom,msm-watchdog"),l,parent=n<0?-1:FdtParentOffset(F,n);
 const UINT8 *p=n<0?nullptr:(const UINT8 *)FdtGetProp(F,n,"reg",&l);
 if(!p||l!=8||cells(p)!=W||cells(p+4)!=4096||parent<0||!RaphaelFdtRootIdentityRange(F,parent,W,4096))return;
 O->Word[1]=3;O->Word[2]=W;O->Word[3]=read32(W+8);O->Word[4]=read32(W+16);O->Word[5]=read32(W+20);
 if(O->Word[3]&1)return;
 O->Word[27]=1;
 write32(W+8,0);write32(W+16,(UINT32)(Hz*20));write32(W+20,(UINT32)(Hz*21));write32(W+8,1);write32(W+4,1);
 O->Word[6]=read32(W+8)==1&&read32(W+16)==Hz*20&&read32(W+20)==Hz*21;
 if(!O->Word[6])goto watchdogRestore;
 O->Word[1]=4;
 if(!noActiveTranslation(F,&O->Word[7],&O->Word[26]))goto watchdogRestore;
 O->Word[8]=1;
 if(!allOthersOff(F,&O->Word[24],&O->Word[25]))goto watchdogRestore;
 {
  Backend io{H->Base,Frequency};Dma d{(UINTN)mDma,(UINTN)mDma+1024,(UINTN)mDma+4096,4096};Transport<Backend> t(io,d,ReadCommand::Read10);O->Word[29]=(Lba<<8)|10;
  O->Word[9]=d.list;O->Word[10]=d.command;O->Word[11]=d.data;
  // ABL has synchronously handed execution to this Image; IRQ/FIQ remain masked,
  // and no firmware callbacks are made while this list is installed. PSCI confirmed all seven
  // secondary CPUs OFF immediately before takeover. Secure firmware autonomy is
  // outside the observed non-secure contract; no SMC is made while attached.
  O->Word[12]=(UINT64)t.takeOver(true);O->Word[1]=5;
  if(O->Word[12]==(UINT64)Result::Ok){
   UINT8 inquiry[36]{};Result v=t.inquiry(0,inquiry);O->Word[13]=(UINT64)v;CopyMem(O->Inquiry,inquiry,36);O->Word[1]=6;
   if(v==Result::Ok){
    v=t.testUnitReady(0);if(v==Result::ScsiError&&t.last.senseKey==6)v=t.testUnitReady(0);
    O->Word[14]=(UINT64)v;
    if(v==Result::Ok){Geometry g{};v=t.capacity(0,g);O->Word[15]=(UINT64)v;O->Word[16]=g.blocks;O->Word[17]=g.bytes;
     if(v==Result::Ok&&g.bytes==4096&&!QueryOnly){
      if(write){
       if(g.blocks==write->lunBlocks)O->Word[18]=RaphaelStorage::executeWriteProbe(*write,t,O->Block,O->Word[30]);
      }else if(plan){
       O->Word[18]=100+(UINT64)RaphaelStorage::Result::InvalidMap;
       if(g.blocks==plan->lunBytes/4096&&plan->lunBytes%4096==0){
        ExtentBackend backend{t,W,ticks(),Frequency};
        auto result=RaphaelStorage::executePlan(*plan,mExtentDisk,backend,O->Block,O->Word[30]);
        if(result==RaphaelStorage::Result::Ok&&hashes){
         backend.begin=ticks();backend.budgetSeconds=120;
         if(!RaphaelStorage::stagePayloadUnverified(mExtentDisk,backend,TargetBytes/4096,
          reinterpret_cast<UINT8 *>(Target),TargetBytes,O->Word[30]))result=RaphaelStorage::Result::DeviceError;
        }
        // 104 means fully read but still quarantined, never authenticated success.
        O->Word[18]=result==RaphaelStorage::Result::Ok?(hashes?104:0):100+(UINT64)result;
        O->Word[29]=(backend.reads<<8)|10;
       }
      }else O->Word[18]=(UINT64)t.read(0,Lba,1,O->Block,4096);
      O->Word[1]=7;
     }
    }
   }
   O->Word[19]=t.last.ocs;O->Word[28]=((UINT64)t.last.response<<32)|((UINT64)t.last.status<<24)|((UINT64)t.last.senseKey<<16)|((UINT64)t.last.asc<<8)|t.last.ascq;O->Word[20]=(UINT64)t.restore();O->Word[21]=t.dmaMustRemainReserved();
  }
  if(t.dmaMustRemainReserved()){
   // Never resume Android with a live/unproven DMA list. The qualified hardware
   // watchdog resets this boot; the reserved FD/DMA pages remain untouched.
   O->Word[1]=8;
   if(!ResetOnError||t.resetAfterError()!=Result::Ok)for(;;)__asm__ volatile("yield");
   O->Word[31]=2;O->Word[21]=0; // Explicit HCI reset, not inherited-register restoration.

  }
 }
watchdogRestore:
 write32(W+8,0);write32(W+16,(UINT32)O->Word[4]);write32(W+20,(UINT32)O->Word[5]);write32(W+8,(UINT32)O->Word[3]);
 O->Word[22]=read32(W+8)==O->Word[3]&&read32(W+16)==O->Word[4]&&read32(W+20)==O->Word[5];if(O->Word[22])O->Word[27]=0;O->Word[23]=ticks();
}

// Exception recovery is opt-in and valid only in the pre-MMU UFS window.
// Guard against recursive faults, and never hand off with an enabled DMA engine.
extern "C" BOOLEAN RaphaelUfsEmergencyQuiesce(CONST RAPHAEL_UFS_HANDOFF *H,RAPHAEL_UFS_READ *O){
 UINT64 sctlr;__asm__ volatile("mrs %0,sctlr_el1":"=r"(sctlr));
 if(!O->Word[27]||(sctlr&0x1005)||O->Word[31]||H->Status!=3||!O->Word[2])return FALSE;
 O->Word[31]=1;
 if(O->Word[9]){
  write32(H->Base+0x24,0);write32(H->Base+0x34,0);
  UINTN attempts=1000000;while((read32(H->Base+0x34)&1)&&--attempts)__asm__ volatile("yield");
  if(!attempts)return FALSE;
  O->Word[21]=0;O->Word[31]=3;
 }
 UINT64 W=O->Word[2];write32(W+8,0);write32(W+16,(UINT32)O->Word[4]);write32(W+20,(UINT32)O->Word[5]);write32(W+8,(UINT32)O->Word[3]);
 O->Word[22]=read32(W+8)==O->Word[3]&&read32(W+16)==O->Word[4]&&read32(W+20)==O->Word[5];
 if(!O->Word[22])return FALSE;
 O->Word[27]=0;return TRUE;
}
