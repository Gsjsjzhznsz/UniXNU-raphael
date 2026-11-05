// SPDX-License-Identifier: BSD-2-Clause-Patent
// Profile-scoped restoration of this device's freshly collected Android Image.
#include <PiPei.h>
#include "AndroidReturn.h"
#include <RaphaelKernelWindow.h>
#include <Library/ArmLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/FdtLib.h>
#include <Library/HobLib.h>
#include <Library/PrePiLib.h>
STATIC struct rph_return_policy mPolicy;
STATIC UINT64 mInitrd,mInitrdEnd,mHigh,mStubBytes;
STATIC CONST VOID *mStub;
STATIC struct rph_return_state *mState;
STATIC_ASSERT(sizeof(struct rph_return_policy)==96,"return policy ABI");
STATIC_ASSERT(sizeof(struct rph_return_state)==344,"return state ABI");
STATIC BOOLEAN Raw(EFI_GUID *Guid,CONST VOID **Data,UINTN *Bytes) {
 EFI_PEI_FILE_HANDLE File;VOID *Found=NULL;
 UINT64 Fd=FixedPcdGet64(PcdRaphaelFdBase),End=Fd+FixedPcdGet32(PcdRaphaelFdSize),At;
 if(EFI_ERROR(FfsFindFileByName(Guid,(VOID *)(UINTN)Fd,&File))||EFI_ERROR(FfsFindSectionData(EFI_SECTION_RAW,File,&Found)))return FALSE;
 At=(UINTN)Found;if(At<Fd+4||At>End)return FALSE;
 CONST EFI_COMMON_SECTION_HEADER *H=(VOID *)(UINTN)(At-4);
 *Bytes=H->Size[0]|(H->Size[1]<<8)|(H->Size[2]<<16);
 if(H->Type!=EFI_SECTION_RAW||*Bytes<4||*Bytes==0xffffff||*Bytes-4>End-At)return FALSE;
 *Bytes-=4;*Data=Found;return TRUE;
}
STATIC BOOLEAN Value(CONST VOID *Fdt,INT32 Node,CONST CHAR8 *Name,UINT64 *Result) {
 INT32 Len;CONST UINT32 *P=FdtGetProp(Fdt,Node,Name,&Len);if(!P||(Len!=4&&Len!=8))return FALSE;
 *Result=SwapBytes32(ReadUnaligned32(P));if(Len==8)*Result=(*Result<<32)|SwapBytes32(ReadUnaligned32(P+1));return TRUE;
}
STATIC BOOLEAN Overlap(UINT64 A,UINT64 B,UINT64 C,UINT64 D){return A<D&&C<B;}
STATIC UINT32 Crc(CONST VOID *Data,UINTN Bytes){
 // Table once per call, with caches enabled. No allocator or services required.
 UINT32 Table[256];for(UINTN I=0;I<256;++I){UINT32 V=(UINT32)I;for(UINTN J=0;J<8;++J)V=(V>>1)^((V&1)?0xedb88320U:0);Table[I]=V;}
 CONST UINT8 *P=Data;UINT32 V=MAX_UINT32;while(Bytes--)V=(V>>8)^Table[(V^*P++)&255];return ~V;
}
BOOLEAN RaphaelPrepareAndroidReturn(RAPHAEL_DIAGNOSTIC *D,CONST VOID *Fdt,CONST RAPHAEL_RANGE *Ram,UINTN Rc,CONST RAPHAEL_RANGE *Guard,UINTN Gc){
 if(!FixedPcdGetBool(PcdRaphaelAndroidReturn))return TRUE;
 EFI_GUID Pg={0x26118cdd,0x1846,0x4ddc,{0xb6,0x26,0xb6,0xd6,0x42,0x88,0x45,0xe2}};
 EFI_GUID Sg={0x075868e9,0xfbba,0x4bae,{0x92,0xc3,0xad,0x21,0x03,0xc2,0x64,0xbd}};
 CONST VOID *P;UINTN Bytes;
 if(!FixedPcdGetBool(PcdRaphaelKernelWindow)||FixedPcdGet32(PcdRaphaelStopAfterStage)<3||
    !Raw(&Pg,&P,&Bytes)||Bytes!=sizeof(mPolicy)||!Raw(&Sg,&mStub,&Bytes)||!Bytes||Bytes>RPH_RETURN_STUB_MAX)return FALSE;
 CopyMem(&mPolicy,P,sizeof(mPolicy));mStubBytes=Bytes;
 if(mPolicy.Magic!=RPH_RETURN_POLICY_MAGIC||mPolicy.Version!=1||!mPolicy.RamdiskBytes||
    mPolicy.SourceBytes<13||mPolicy.SourceBytes>SIZE_32MB||mPolicy.KernelBytes<64||mPolicy.KernelBytes>mPolicy.KernelImageBytes||
    mPolicy.KernelImageBytes>FixedPcdGet64(PcdRaphaelArenaBase)-D->ImageBase||
    mPolicy.KernelImageBytes>FixedPcdGet64(PcdRaphaelFdtBase)-D->ImageBase||mPolicy.EntryOffset>=mPolicy.KernelBytes||
    (mPolicy.EntryOffset&3)||mPolicy.ImageInstruction>MAX_UINT32||mPolicy.SourceCrc>MAX_UINT32||mPolicy.KernelCrc>MAX_UINT32||mPolicy.RamdiskCrc>MAX_UINT32||
    D->ImageSize!=SIZE_64KB||D->ExtentBase!=D->ImageBase+SIZE_64KB||
    mPolicy.Conduit!=(FixedPcdGetBool(PcdRaphaelAndroidReturnQemu)?2U:1U))return FALSE;
 INT32 Chosen=FdtPathOffset(Fdt,"/chosen"),Psci=FdtPathOffset(Fdt,"/psci"),Len;
 CONST CHAR8 *Method=FdtGetProp(Fdt,Psci,"method",&Len);
 if(!Method||Len!=4||CompareMem(Method,mPolicy.Conduit==2?"hvc":"smc",4)||
    !Value(Fdt,Chosen,"linux,initrd-start",&mInitrd)||!Value(Fdt,Chosen,"linux,initrd-end",&mInitrdEnd)||mInitrdEnd<=mInitrd||
    mInitrd>MAX_UINT64-EFI_PAGE_MASK||mInitrdEnd>MAX_UINT64-EFI_PAGE_MASK||mPolicy.RamdiskBytes>mInitrdEnd-mInitrd||
    ALIGN_VALUE(mPolicy.RamdiskBytes,8)+mPolicy.SourceBytes!=mInitrdEnd-mInitrd||
    (!FixedPcdGetBool(PcdRaphaelSparseArena)&&Overlap(mInitrd&~(UINT64)EFI_PAGE_MASK,ALIGN_VALUE(mInitrdEnd,EFI_PAGE_SIZE),D->ImageBase,D->ExtentEnd))||
    mInitrd<D->ImageBase+mPolicy.KernelImageBytes)return FALSE;
 if(FixedPcdGetBool(PcdRaphaelSparseArena)&&
    (mInitrd<FixedPcdGet64(PcdRaphaelDownloadedEnd)||ALIGN_VALUE(mInitrdEnd,EFI_PAGE_SIZE)>FixedPcdGet64(PcdRaphaelArenaBase)))return FALSE;
 BOOLEAN InRam=FALSE;for(UINTN I=0;I<Rc;++I)if(mInitrd>=Ram[I].Base&&mInitrdEnd<=Ram[I].Base+Ram[I].Length)InRam=TRUE;
 if(!InRam)return FALSE;
 for(UINTN I=0;I<Gc;++I)if(!(Guard[I].Base==mInitrd&&Guard[I].Length==mInitrdEnd-mInitrd)&&
    Overlap(mInitrd,mInitrdEnd,Guard[I].Base,Guard[I].Base+Guard[I].Length))return FALSE;
 RAPHAEL_KERNEL_WINDOW *W=RaphaelKernelWindow();if(W->Status!=1||W->Bytes<RPH_RETURN_TAIL_BYTES)return FALSE;
 mHigh=W->Base+W->Bytes-RPH_RETURN_TAIL_BYTES;
 if(W->Candidate>mHigh||W->WindowBytes>mHigh-W->Candidate)return FALSE;
 return TRUE;
}
BOOLEAN RaphaelMapAndroidOutput(ARM_MEMORY_REGION_DESCRIPTOR *M){
 if(!mStub||!mPolicy.KernelImageBytes)return FALSE;
 M->PhysicalBase=M->VirtualBase=FixedPcdGet64(PcdRaphaelImageBase);
 M->Length=MAX(ALIGN_VALUE(mPolicy.KernelImageBytes,EFI_PAGE_SIZE),FixedPcdGet64(PcdRaphaelDownloadedEnd)-M->PhysicalBase);
 M->Attributes=ARM_MEMORY_REGION_ATTRIBUTE_WRITE_BACK;return TRUE;
}
BOOLEAN RaphaelMapAndroidReturn(ARM_MEMORY_REGION_DESCRIPTOR *M){
 if(!mStub||!mInitrd||!mHigh)return FALSE;
 M->PhysicalBase=M->VirtualBase=mInitrd&~(UINT64)EFI_PAGE_MASK;
 M->Length=ALIGN_VALUE(mInitrdEnd,EFI_PAGE_SIZE)-M->PhysicalBase;M->Attributes=ARM_MEMORY_REGION_ATTRIBUTE_WRITE_BACK_RO;return TRUE;
}
STATIC BOOLEAN ArmAndroidReturn(RAPHAEL_DIAGNOSTIC *D,BOOLEAN PublishHob){
 if(!FixedPcdGetBool(PcdRaphaelAndroidReturn))return TRUE;
 if(mState&&mState->Armed==1){
  UINT64 At=(UINTN)mState;return !PublishHob||BuildGuidDataHob(&gRaphaelAndroidReturnHobGuid,&At,sizeof(At))!=NULL;
 }
 if(!mStub||!mHigh||Crc((VOID *)(UINTN)mInitrd,mPolicy.RamdiskBytes)!=mPolicy.RamdiskCrc)return FALSE;
 CopyMem((VOID *)(UINTN)mHigh,mStub,mStubBytes);mState=(VOID *)(UINTN)(mHigh+RPH_RETURN_STUB_MAX);ZeroMem(mState,sizeof(*mState));
 mState->Magic=RPH_RETURN_STATE_MAGIC;mState->Version=RPH_RETURN_STATE_VERSION;mState->Output=D->ImageBase;
 mState->KernelBytes=mPolicy.KernelBytes;mState->ImageBytes=mPolicy.KernelImageBytes;mState->Entry=D->ImageBase+mPolicy.EntryOffset;
 mState->Source=mInitrd+ALIGN_VALUE(mPolicy.RamdiskBytes,8);mState->SourceBytes=mPolicy.SourceBytes;
 mState->SourceCrc=mPolicy.SourceCrc;mState->KernelCrc=mPolicy.KernelCrc;mState->LowBase=D->ImageBase;mState->LowEnd=D->ExtentEnd;
 if(FixedPcdGetBool(PcdRaphaelSparseArena)){
  ARM_MEMORY_REGION_DESCRIPTOR Output;if(!RaphaelMapAndroidOutput(&Output))return FALSE;
  mState->LowEnd=Output.PhysicalBase+Output.Length;
  mState->AuxBase=FixedPcdGet64(PcdRaphaelArenaBase);mState->AuxEnd=D->ExtentEnd;
 }
 mState->HighBase=mHigh;mState->HighEnd=mHigh+RPH_RETURN_TAIL_BYTES;CopyMem(mState->Arch,D,19*8);mState->Conduit=mPolicy.Conduit;mState->Armed=1;
 WriteBackDataCacheRange((VOID *)(UINTN)mHigh,mStubBytes);InvalidateInstructionCacheRange((VOID *)(UINTN)mHigh,mStubBytes);
 UINT64 At=(UINTN)mState;return !PublishHob||BuildGuidDataHob(&gRaphaelAndroidReturnHobGuid,&At,sizeof(At))!=NULL;
}
// Early UFS faults need a return capsule before any allocator, MMU or DMA.
// The audited geometry was already prepared; HOB publication waits for MMU setup.
BOOLEAN RaphaelArmAndroidReturnEarly(RAPHAEL_DIAGNOSTIC *D){
 if(!FixedPcdGetBool(PcdRaphaelAndroidReturnQemu))return FALSE;
 return ArmAndroidReturn(D,FALSE);
}
BOOLEAN RaphaelArmAndroidReturn(RAPHAEL_DIAGNOSTIC *D){return ArmAndroidReturn(D,TRUE);}
BOOLEAN RaphaelExportAndroidReturn(VOID *Fdt){
 if(!mState||mState->Armed!=1)return FALSE;
 INT32 Chosen=FdtPathOffset(Fdt,"/chosen"),Len;CONST VOID *Old=FdtGetProp(Fdt,Chosen,"linux,initrd-end",&Len);
 UINT64 End=mInitrd+mPolicy.RamdiskBytes,Be=SwapBytes64(End);UINT32 Be32=SwapBytes32((UINT32)End);
 if(!Old||(Len!=4&&Len!=8)||(Len==4&&End>MAX_UINT32)||FdtSetProp(Fdt,Chosen,"linux,initrd-end",Len==8?(VOID *)&Be:(VOID *)&Be32,Len))return FALSE;
 UINT64 Words[10]={1,2,mPolicy.SourceCrc,mPolicy.KernelCrc,0,mHigh,mHigh+RPH_RETURN_TAIL_BYTES,0,0,0};
 for(UINTN I=0;I<10;++I)Words[I]=SwapBytes64(Words[I]);
 return FdtSetProp(Fdt,Chosen,"raphael,android-return",Words,sizeof(Words))==0;
}
VOID RaphaelFinishAndroidReturn(RAPHAEL_DIAGNOSTIC *D){
 if(!mState||mState->Armed!=1||!D->FdtCopy)return;
 INT32 Len,Chosen=FdtPathOffset((VOID *)(UINTN)D->FdtCopy,"/chosen");
 CONST VOID *Wire=FdtGetProp((VOID *)(UINTN)D->FdtCopy,Chosen,"raphael,android-return",&Len);
 if(!Wire||Len!=80)return;
 mState->Wire=(UINTN)Wire;mState->Fdt=D->FdtCopy;
 ((VOID (EFIAPI *)(struct rph_return_state *))(UINTN)mHigh)(mState);
 CpuDeadLoop();
}
