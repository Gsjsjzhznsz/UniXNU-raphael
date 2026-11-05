// SPDX-License-Identifier: BSD-2-Clause-Patent
// Bounded first instructions of the original XNU. Only a loaded ADRP is
// temporarily replaced, after all original file/zero/args CRC checks pass.
#include <RaphaelDiagnostic.h>
#include <Library/ArmLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
RAPHAEL_NATIVE_ENTRY_RESULT gRaphaelNativeEntry;
extern UINT8 RaphaelNativeEntryVectors[], RaphaelNativeEntryVectorsEnd[];
STATIC UINT64 mArgs;
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Version) == 0, "entry ABI Version");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Status) == 8, "entry ABI Status");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,ArmedCount) == 16, "entry ABI ArmedCount");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,TrapCount) == 24, "entry ABI TrapCount");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Entry) == 32, "entry ABI Entry");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Checkpoint) == 40, "entry ABI Checkpoint");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,OriginalInstruction) == 48, "entry ABI OriginalInstruction");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,ProbeInstruction) == 56, "entry ABI ProbeInstruction");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Esr) == 64, "entry ABI Esr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Elr) == 72, "entry ABI Elr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Far) == 80, "entry ABI Far");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Spsr) == 88, "entry ABI Spsr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,X0) == 96, "entry ABI X0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,X1) == 104, "entry ABI X1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,X20) == 112, "entry ABI X20");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,X21) == 120, "entry ABI X21");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Sp) == 128, "entry ABI Sp");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Sctlr) == 136, "entry ABI Sctlr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,CurrentEl) == 144, "entry ABI CurrentEl");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Daif) == 152, "entry ABI Daif");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Counter) == 160, "entry ABI Counter");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Vbar) == 168, "entry ABI Vbar");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Tcr) == 176, "entry ABI Tcr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Ttbr0) == 184, "entry ABI Ttbr0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Ttbr1) == 192, "entry ABI Ttbr1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Mair) == 200, "entry ABI Mair");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,SavedSctlr) == 208, "entry ABI SavedSctlr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,SavedVbar) == 216, "entry ABI SavedVbar");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,SavedTcr) == 224, "entry ABI SavedTcr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,SavedTtbr0) == 232, "entry ABI SavedTtbr0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,SavedTtbr1) == 240, "entry ABI SavedTtbr1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,SavedMair) == 248, "entry ABI SavedMair");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Frequency) == 256, "entry ABI Frequency");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Affinity) == 264, "entry ABI Affinity");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,PatchRestored) == 272, "entry ABI PatchRestored");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,MmuRestored) == 280, "entry ABI MmuRestored");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,ExitCompleted) == 288, "entry ABI ExitCompleted");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,Error) == 296, "entry ABI Error");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,PrefixInstructions) == 304, "entry ABI PrefixInstructions");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_ENTRY_RESULT,VectorSlot) == 312, "entry ABI VectorSlot");
STATIC_ASSERT(sizeof(RAPHAEL_NATIVE_ENTRY_RESULT)==320,"entry wire size");
#define MRS(Name,Reg) STATIC UINT64 Name(VOID){UINT64 V;__asm__ volatile("mrs %0," #Reg :"=r"(V));return V;}
MRS(Sctlr,sctlr_el1) MRS(Vbar,vbar_el1) MRS(Tcr,tcr_el1)
MRS(Ttbr0,ttbr0_el1) MRS(Ttbr1,ttbr1_el1) MRS(Mair,mair_el1)
MRS(CurrentEl,CurrentEL)
EFI_STATUS RaphaelArmNativeEntry(UINT64 Entry,UINT64 Args) {
  if(FixedPcdGetBool(PcdRaphaelNativeMmuTest))return RaphaelArmNativeMmu(Entry,Args);
  RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();
  RAPHAEL_NATIVE_ENTRY_RESULT *R=&gRaphaelNativeEntry;
  if(!FixedPcdGetBool(PcdRaphaelNativeEntryTest)||CurrentEl()!=4||
     R->ArmedCount||!D->NativeLoadResult)return EFI_UNSUPPORTED;
  RAPHAEL_NATIVE_LOAD_RESULT *L=(VOID *)(UINTN)D->NativeLoadResult;
  if(L->Version!=2||L->Status!=4||L->Error||L->Entry!=Entry||L->Args!=Args||
     !RaphaelNativeEntryRange(Entry,4))return EFI_COMPROMISED_DATA;
  UINT32 Branch=*(CONST UINT32 *)(UINTN)Entry;
  if((Branch&0xfc000000U)!=0x14000000U)return EFI_COMPROMISED_DATA;
  INT64 Offset=((INT64)(INT32)(Branch<<6))>>4;
  UINT64 Target=Entry+Offset;
  // Require the exact range to be in an original executable file segment.
  if(!RaphaelNativeEntryRange(Target,20))return EFI_COMPROMISED_DATA;
  CONST UINT32 *Code=(VOID *)(UINTN)Target;
  if(Code[0]!=0xd510109fU||Code[1]!=0xd5034fdfU||Code[2]!=0xaa0003f4U||
     Code[3]!=0xd2800015U||Code[4]!=0xf0ffffe0U)return EFI_COMPROMISED_DATA;
  ZeroMem(R,sizeof(*R));mArgs=Args;D->NativeEntryResult=(UINTN)R;
  R->Version=1;R->Status=1;R->ArmedCount=1;R->Entry=Entry;R->Checkpoint=Target+16;
  R->OriginalInstruction=Code[4];R->ProbeInstruction=0xd42a6a00U; // BRK #0x5350
  R->SavedSctlr=Sctlr();R->SavedVbar=Vbar();R->SavedTcr=Tcr();
  R->SavedTtbr0=Ttbr0();R->SavedTtbr1=Ttbr1();R->SavedMair=Mair();
  R->Frequency=D->Cntfrq;R->Affinity=D->Mpidr&0xff00ffffffULL;
  R->ExitCompleted=1;R->PrefixInstructions=5;
  if((R->SavedSctlr&0x1005)!=0x1005||((UINTN)RaphaelNativeEntryVectors&2047)||
     RaphaelNativeEntryVectorsEnd-RaphaelNativeEntryVectors!=2048)return EFI_COMPROMISED_DATA;
  *(volatile UINT32 *)(UINTN)R->Checkpoint=(UINT32)R->ProbeInstruction;
  WriteBackDataCacheRange((VOID *)(UINTN)R->Checkpoint,4);
  InvalidateInstructionCacheRange((VOID *)(UINTN)R->Checkpoint,4);
  // Handler reads/writes this record with caches off, before restoring UEFI.
  WriteBackInvalidateDataCacheRange(R,sizeof(*R));
  __asm__ volatile("dsb sy\n msr vbar_el1,%0\n isb"::"r"(RaphaelNativeEntryVectors):"memory");
  return EFI_SUCCESS;
}
VOID EFIAPI RaphaelNativeEntryCaptured(VOID) {
  RAPHAEL_NATIVE_ENTRY_RESULT *R=&gRaphaelNativeEntry;
  BOOLEAN Valid=R->Version==1&&R->ArmedCount==1&&R->TrapCount==1&&
    R->Esr==((0x3cULL<<26)|(1ULL<<25)|0x5350)&&R->Elr==R->Checkpoint&&
    R->X0==mArgs&&R->X20==mArgs&&R->X21==0&&R->X1==R->Entry&&
    R->CurrentEl==4&&(R->Sctlr&0x1005)==0&&(R->Spsr&0x3df)==0x3c5&&
    (R->VectorSlot==0||R->VectorSlot==4)&&R->Vbar==(UINTN)RaphaelNativeEntryVectors;
  R->MmuRestored=Sctlr()==R->SavedSctlr&&Vbar()==R->SavedVbar&&
    R->Tcr==R->SavedTcr&&R->Ttbr0==R->SavedTtbr0&&R->Ttbr1==R->SavedTtbr1&&R->Mair==R->SavedMair;
  Valid=Valid&&R->MmuRestored&&*(volatile UINT32 *)(UINTN)R->Checkpoint==R->ProbeInstruction;
  *(volatile UINT32 *)(UINTN)R->Checkpoint=(UINT32)R->OriginalInstruction;
  WriteBackDataCacheRange((VOID *)(UINTN)R->Checkpoint,4);
  InvalidateInstructionCacheRange((VOID *)(UINTN)R->Checkpoint,4);
  R->PatchRestored=*(volatile UINT32 *)(UINTN)R->Checkpoint==R->OriginalInstruction;
  Valid=Valid&&R->PatchRestored;
  R->Status=Valid?3:2;R->Error=Valid?0:1;
  RaphaelNativeEntryFinish(Valid);
}
