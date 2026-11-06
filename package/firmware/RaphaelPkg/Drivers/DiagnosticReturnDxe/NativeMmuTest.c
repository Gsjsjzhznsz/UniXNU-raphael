// SPDX-License-Identifier: BSD-2-Clause-Patent
// Recover after the original XNU MMU switch, before arm_init writes a stack.
#include <RaphaelDiagnostic.h>
#include <Library/ArmLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/DxeServicesLib.h>
STATIC RAPHAEL_NATIVE_MMU_STATE mMmuState;
#define gRaphaelNativeMmu mMmuState.Result
RAPHAEL_NATIVE_WATCHDOG_RESULT *RaphaelNativeWatchdogResult(VOID) { return &mMmuState.Watchdog; }
STATIC RAPHAEL_NATIVE_MMU_POLICY mP;
STATIC UINT8 mLow[4096],mHigh[2048],mTables[65536],mTablesAfter[65536];
STATIC UINT64 mArgs,mLowPa,mHighPa,mArmPa,mCheckpoint,mOpcode;
extern UINT8 RaphaelMmuRelayBody[],RaphaelMmuRelayTransition[],RaphaelMmuRelayPhysicalBody[],RaphaelMmuRelayPmap[];
extern UINT8 RaphaelMmuRelay[],RaphaelMmuRelayEnd[],RaphaelMmuRelayState[],RaphaelMmuRelayStack[],RaphaelMmuRelayHandler[],RaphaelMmuRelayRanges[];
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Version)==0,"MMU ABI Version");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Status)==8,"MMU ABI Status");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Armed)==16,"MMU ABI Armed");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TrapCount)==24,"MMU ABI TrapCount");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Entry)==32,"MMU ABI Entry");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,CheckpointVa)==40,"MMU ABI CheckpointVa");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,OriginalInstruction)==48,"MMU ABI OriginalInstruction");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ProbeInstruction)==56,"MMU ABI ProbeInstruction");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Esr)==64,"MMU ABI Esr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Elr)==72,"MMU ABI Elr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Far)==80,"MMU ABI Far");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Spsr)==88,"MMU ABI Spsr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X0)==96,"MMU ABI X0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X1)==104,"MMU ABI X1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X20)==112,"MMU ABI X20");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X21)==120,"MMU ABI X21");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X22)==128,"MMU ABI X22");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X23)==136,"MMU ABI X23");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X24)==144,"MMU ABI X24");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,X25)==152,"MMU ABI X25");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Sp)==160,"MMU ABI Sp");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Lr)==168,"MMU ABI Lr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Sctlr)==176,"MMU ABI Sctlr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Vbar)==184,"MMU ABI Vbar");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Tcr)==192,"MMU ABI Tcr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Ttbr0)==200,"MMU ABI Ttbr0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Ttbr1)==208,"MMU ABI Ttbr1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Mair)==216,"MMU ABI Mair");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedSctlr)==224,"MMU ABI SavedSctlr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedVbar)==232,"MMU ABI SavedVbar");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedTcr)==240,"MMU ABI SavedTcr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedTtbr0)==248,"MMU ABI SavedTtbr0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedTtbr1)==256,"MMU ABI SavedTtbr1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedMair)==264,"MMU ABI SavedMair");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedCpacr)==272,"MMU ABI SavedCpacr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedTpidrEl0)==280,"MMU ABI SavedTpidrEl0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedTpidrro)==288,"MMU ABI SavedTpidrro");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedTpidrEl1)==296,"MMU ABI SavedTpidrEl1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SavedSpEl0)==304,"MMU ABI SavedSpEl0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Frequency)==312,"MMU ABI Frequency");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Affinity)==320,"MMU ABI Affinity");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,VectorSlot)==328,"MMU ABI VectorSlot");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,CacheOffSctlr)==336,"MMU ABI CacheOffSctlr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,RelayPa)==344,"MMU ABI RelayPa");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Tables)==352,"MMU ABI Tables");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TablesBytes)==360,"MMU ABI TablesBytes");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TablesCrcBefore)==368,"MMU ABI TablesCrcBefore");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TablesCrcAfter)==376,"MMU ABI TablesCrcAfter");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,PhysicalTranslation)==384,"MMU ABI PhysicalTranslation");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,VirtualTranslation)==392,"MMU ABI VirtualTranslation");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,PatchRestored)==400,"MMU ABI PatchRestored");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TablesRestored)==408,"MMU ABI TablesRestored");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,MmuRestored)==416,"MMU ABI MmuRestored");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ArgsOk)==424,"MMU ABI ArgsOk");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,SegmentsOk)==432,"MMU ABI SegmentsOk");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ZeroOk)==440,"MMU ABI ZeroOk");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Error)==448,"MMU ABI Error");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ExpectedTcr)==456,"MMU ABI ExpectedTcr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ExpectedMair)==464,"MMU ABI ExpectedMair");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ExpectedSctlr)==472,"MMU ABI ExpectedSctlr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ExpectedPhysBase)==480,"MMU ABI ExpectedPhysBase");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ExpectedVirtBase)==488,"MMU ABI ExpectedVirtBase");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,ExpectedMemBytes)==496,"MMU ABI ExpectedMemBytes");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TablesChangedCount)==504,"MMU ABI TablesChangedCount");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,InterruptedSp)==512,"MMU ABI InterruptedSp");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,CurrentEl)==520,"MMU ABI CurrentEl");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Daif)==528,"MMU ABI Daif");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Cpacr)==536,"MMU ABI Cpacr");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TpidrEl0)==544,"MMU ABI TpidrEl0");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Tpidrro)==552,"MMU ABI Tpidrro");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,TpidrEl1)==560,"MMU ABI TpidrEl1");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_MMU_RESULT,Counter)==568,"MMU ABI Counter");
STATIC_ASSERT(sizeof(RAPHAEL_NATIVE_MMU_RESULT)==576,"MMU wire");
STATIC_ASSERT(sizeof(RAPHAEL_NATIVE_MMU_POLICY)==168,"MMU policy");
#define MRS(Name,Reg) STATIC UINT64 Name(VOID){UINT64 V;__asm__ volatile("mrs %0," #Reg :"=r"(V));return V;}
MRS(Sctlr,sctlr_el1) MRS(Vbar,vbar_el1) MRS(Tcr,tcr_el1) MRS(Ttbr0,ttbr0_el1) MRS(Ttbr1,ttbr1_el1) MRS(Mair,mair_el1)
MRS(Cpacr,cpacr_el1) MRS(Tpidr0,tpidr_el0) MRS(TpidrRo,tpidrro_el0) MRS(Tpidr1,tpidr_el1) MRS(Sp0,sp_el0)
MRS(PhysicalControl,cntp_ctl_el0) MRS(PhysicalCompare,cntp_cval_el0)
MRS(VirtualControl,cntv_ctl_el0) MRS(VirtualCompare,cntv_cval_el0) MRS(KernelControl,cntkctl_el1)
STATIC_ASSERT(sizeof(RAPHAEL_NATIVE_PLATFORM_RESULT)==144,"platform timer ABI");
STATIC VOID SavePlatform(VOID) {
 RAPHAEL_NATIVE_PLATFORM_RESULT *P=&mMmuState.Platform;ZeroMem(P,sizeof(*P));P->Version=1;P->Status=1;
 P->SavedPhysicalControl=PhysicalControl();P->SavedPhysicalCompare=PhysicalCompare();
 P->SavedVirtualControl=VirtualControl();P->SavedVirtualCompare=VirtualCompare();P->SavedKernelControl=KernelControl();
}
STATIC BOOLEAN RestorePlatform(VOID) {
 RAPHAEL_NATIVE_PLATFORM_RESULT *P=&mMmuState.Platform;
 P->ObservedPhysicalControl=PhysicalControl();P->ObservedPhysicalCompare=PhysicalCompare();
 P->ObservedVirtualControl=VirtualControl();P->ObservedVirtualCompare=VirtualCompare();P->ObservedKernelControl=KernelControl();
 // DAIF is masked by the synchronous exception. Mask both sources before
 // restoring their deadlines, then restore the original writable controls.
 __asm__ volatile("msr cntp_ctl_el0,%0\n msr cntv_ctl_el0,%0\n isb"::"r"(2ULL):"memory");
 __asm__ volatile("msr cntp_cval_el0,%0\n msr cntv_cval_el0,%1\n msr cntkctl_el1,%2\n isb"::
   "r"(P->SavedPhysicalCompare),"r"(P->SavedVirtualCompare),"r"(P->SavedKernelControl):"memory");
 __asm__ volatile("msr cntp_ctl_el0,%0\n msr cntv_ctl_el0,%1\n isb"::
   "r"(P->SavedPhysicalControl&3),"r"(P->SavedVirtualControl&3):"memory");
 P->RestoredPhysicalControl=PhysicalControl();P->RestoredPhysicalCompare=PhysicalCompare();
 P->RestoredVirtualControl=VirtualControl();P->RestoredVirtualCompare=VirtualCompare();P->RestoredKernelControl=KernelControl();
 P->RestoreOk=(P->RestoredPhysicalControl&3)==(P->SavedPhysicalControl&3)&&P->RestoredPhysicalCompare==P->SavedPhysicalCompare&&
  (P->RestoredVirtualControl&3)==(P->SavedVirtualControl&3)&&P->RestoredVirtualCompare==P->SavedVirtualCompare&&P->RestoredKernelControl==P->SavedKernelControl;
 BOOLEAN Valid=P->RestoreOk&&(RaphaelNativePlatformStop()!=0||((P->ObservedPhysicalControl&3)==2&&(P->ObservedVirtualControl&3)==1&&P->ObservedPhysicalCompare==P->SavedPhysicalCompare))&&(P->ObservedKernelControl&15)==15&&((P->ObservedKernelControl^P->SavedKernelControl)&~255ULL)==0;
 P->Status=Valid?3:2;return Valid;
}
STATIC UINT64 Pa(UINT64 Va){return RaphaelNativePhysical(Va);}
EFI_STATUS RaphaelPrepareNativeMmu(VOID) {
  EFI_GUID Guid={0xa43a362c,0x77b4,0x45a9,{0x93,0x13,0xa0,0x67,0xdd,0x84,0xd7,0x26}};
  VOID *Raw;UINTN Bytes;
  if(!FixedPcdGetBool(PcdRaphaelNativeMmuTest)||!FixedPcdGetBool(PcdRaphaelNativeEntryTest)||!FixedPcdGetBool(PcdRaphaelNativeExitComplete))return EFI_UNSUPPORTED;
  EFI_STATUS S=GetSectionFromAnyFv(&Guid,EFI_SECTION_RAW,0,&Raw,&Bytes);
  if(EFI_ERROR(S))return S;
  if(Bytes!=sizeof(mP))return EFI_COMPROMISED_DATA;
  CopyMem(&mP,Raw,sizeof(mP));
  if(mP.Magic!=SIGNATURE_64('R','P','H','M','M','U','0','1')||mP.Version!=2||mP.Flags!=1||mP.BootstrapSkip>=SIZE_256MB-SIZE_2MB||(mP.BootstrapSkip&4095)||mP.TablesBytes!=sizeof(mTables)||
     !mP.StartBytes||mP.StartBytes>4096||mP.TtbBytes!=16||mP.ArmOpcode>MAX_UINT32||mP.StartCrc>MAX_UINT32||mP.TtbCrc>MAX_UINT32||
     (mP.LowVectors&4095)||(mP.HighVectors&2047)||(mP.Tables&4095)||
     !RaphaelNativeEntryRange(Pa(mP.ArmInit),4)||!RaphaelNativeEntryRange(Pa(mP.LowVectors),sizeof(mLow))||
     !RaphaelNativeEntryRange(Pa(mP.HighVectors),sizeof(mHigh))||!RaphaelNativeMemoryRange(Pa(mP.Tables),sizeof(mTables))||
     !RaphaelNativeEntryRange(Pa(mP.Start),mP.StartBytes)||!RaphaelNativeEntryRange(Pa(mP.Ttb),mP.TtbBytes))return EFI_COMPROMISED_DATA;
  if(FixedPcdGetBool(PcdRaphaelNativePlatformTest)&&!FixedPcdGetBool(PcdRaphaelNativePmapTest))return EFI_COMPROMISED_DATA;
  if(FixedPcdGetBool(PcdRaphaelNativePmapTest)){
    if(!FixedPcdGetBool(PcdRaphaelNativeEarlyTest))return EFI_COMPROMISED_DATA;
    S=RaphaelPrepareNativePmap();if(EFI_ERROR(S))return S;
  }
  return FixedPcdGetBool(PcdRaphaelNativeEarlyTest)?RaphaelPrepareNativeEarly():EFI_SUCCESS;
}
STATIC VOID Coherent(UINT64 At,UINTN Bytes){WriteBackDataCacheRange((VOID *)(UINTN)At,Bytes);InvalidateInstructionCacheRange((VOID *)(UINTN)At,Bytes);}
STATIC VOID Vectors(UINT64 Base,UINT64 Relay) {
  UINT32 *P=(VOID *)(UINTN)Base;
  BOOLEAN SyncOnly=RaphaelNativePlatformStop()>=14;
  if(!SyncOnly)for(UINTN I=0;I<2048/4;++I)P[I]=0xd503201fU;
  for(UINTN I=0;I<16;++I) {
    if(SyncOnly&&(I%4))continue;
    UINT32 *Slot=P+I*32;Slot[0]=0xd2800011U|((UINT32)I<<5);
    Slot[1]=0x58000070U;Slot[2]=0xd61f0200U;
    WriteUnaligned64((VOID *)(Slot+4),Relay);
  }
}
STATIC BOOLEAN Translate(UINT64 Root,UINT64 Address,BOOLEAN High,UINT64 *Physical) {
  // Exactly the generated 4KiB, 38-bit bootstrap regime. No guessed map.
  RAPHAEL_NATIVE_MMU_RESULT *R=&gRaphaelNativeMmu;
  UINT64 TcrValue=R->Tcr;UINTN Bits=64-((TcrValue>>(High?16:0))&63);
  if(Bits!=38||((TcrValue>>14)&3)!=0||((TcrValue>>30)&3)!=2)return FALSE;
  Address&=(1ULL<<Bits)-1; // Only 38 significant VA bits index the shortened L1.
  UINT64 Table=Root&0x0000fffffffff000ULL;
  for(UINTN Level=1;Level<=3;++Level) {
    if(Table<R->Tables||Table-R->Tables>R->TablesBytes-EFI_PAGE_SIZE)return FALSE;
    UINTN Shift=12+9*(3-Level);UINT64 E=((CONST UINT64 *)(UINTN)Table)[(Address>>Shift)&511];
    if(!(E&1))return FALSE;
    if(Level<3&&(E&3)==3){Table=E&0x0000fffffffff000ULL;continue;}
    if((Level<3&&(E&3)!=1)||(Level==3&&(E&3)!=3))return FALSE;
    UINT64 Mask=(1ULL<<Shift)-1;*Physical=(E&0x0000fffffffff000ULL&~Mask)|(Address&Mask);return TRUE;
  }
  return FALSE;
}
STATIC BOOLEAN ExactTables(VOID) {
  RAPHAEL_NATIVE_MMU_RESULT *R=&gRaphaelNativeMmu;
  return RaphaelNativeBootstrapTablesMatch((CONST UINT64 *)mTablesAfter,R->Tables,
    R->ExpectedPhysBase,R->ExpectedVirtBase,R->ExpectedMemBytes,mP.BootstrapSkip);
}
EFI_STATUS RaphaelArmNativeMmu(UINT64 Entry,UINT64 Args) {
  RAPHAEL_NATIVE_MMU_RESULT *R=&gRaphaelNativeMmu;RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();
  RAPHAEL_NATIVE_LOAD_RESULT *L=(VOID *)(UINTN)D->NativeLoadResult;
  if(R->Armed||!L||L->Version!=2||L->Status!=4||L->Entry!=Entry||L->Args!=Args)return EFI_COMPROMISED_DATA;
  CONST RAPHAEL_NATIVE_COMPILED_POLICY *Compiled=RaphaelNativeCompiledPolicy();
  mArgs=Args;mLowPa=Pa(mP.LowVectors);mHighPa=Pa(mP.HighVectors);mCheckpoint=FixedPcdGetBool(PcdRaphaelNativeEarlyTest)?RaphaelNativeEarlyCheckpoint():mP.ArmInit;mOpcode=FixedPcdGetBool(PcdRaphaelNativeEarlyTest)?RaphaelNativeEarlyOpcode():mP.ArmOpcode;mArmPa=Pa(mCheckpoint);
  UINT64 Tables=Pa(mP.Tables);UINTN RelayBytes=RaphaelMmuRelayEnd-RaphaelMmuRelay;
  if(!Tables||!mArmPa||!mLowPa||!mHighPa||RelayBytes>sizeof(mLow)-2048||
     *(UINT32 *)(UINTN)mArmPa!=mOpcode||
     CalculateCrc32((VOID *)(UINTN)Pa(mP.Start),mP.StartBytes)!=mP.StartCrc||
     CalculateCrc32((VOID *)(UINTN)Pa(mP.Ttb),mP.TtbBytes)!=mP.TtbCrc)return EFI_COMPROMISED_DATA;
  if(FixedPcdGetBool(PcdRaphaelNativeEarlyTest)){EFI_STATUS S=RaphaelSaveNativeEarly(Args);if(EFI_ERROR(S))return S;mMmuState.Early=RaphaelNativeEarlyState();}
  CopyMem(mLow,(VOID *)(UINTN)mLowPa,sizeof(mLow));CopyMem(mHigh,(VOID *)(UINTN)mHighPa,sizeof(mHigh));CopyMem(mTables,(VOID *)(UINTN)Tables,sizeof(mTables));
  for(UINTN I=0;I<sizeof(mTables);++I)if(mTables[I])return EFI_COMPROMISED_DATA;
  ZeroMem(R,sizeof(*R));D->NativeMmuResult=(UINTN)R;mMmuState.Snapshot=(UINTN)mTablesAfter;
  R->Version=FixedPcdGetBool(PcdRaphaelNativePmapTest)?2:1;R->Status=1;R->Armed=1;R->Entry=Entry;R->CheckpointVa=mCheckpoint;
  R->OriginalInstruction=mOpcode;R->ProbeInstruction=0xd42a6a20U; // BRK #0x5351
  R->SavedSctlr=Sctlr();R->SavedVbar=Vbar();R->SavedTcr=Tcr();R->SavedTtbr0=Ttbr0();R->SavedTtbr1=Ttbr1();R->SavedMair=Mair();
  R->SavedCpacr=Cpacr();R->SavedTpidrEl0=Tpidr0();R->SavedTpidrro=TpidrRo();R->SavedTpidrEl1=Tpidr1();R->SavedSpEl0=Sp0();
  if(FixedPcdGetBool(PcdRaphaelNativePlatformTest))SavePlatform();
  if(RaphaelNativePlatformStop()>=13){EFI_STATUS S=RaphaelSaveNativeGic(&mMmuState.Gic);if(EFI_ERROR(S))return S;}
  R->Frequency=D->Cntfrq;R->Affinity=D->Mpidr&0xff00ffffffULL;R->RelayPa=Compiled?Pa(Compiled->Relay):mLowPa+2048;
  R->Tables=Tables;R->TablesBytes=sizeof(mTables);R->TablesCrcBefore=CalculateCrc32(mTables,sizeof(mTables));
  R->ExpectedTcr=mP.Tcr;R->ExpectedMair=mP.Mair;R->ExpectedSctlr=mP.Sctlr;
  R->ExpectedVirtBase=ReadUnaligned64((VOID *)(UINTN)(Args+8));R->ExpectedPhysBase=L->PhysicalBase;R->ExpectedMemBytes=L->WindowBytes;
  if((R->SavedSctlr&0x1005)!=0x1005)return EFI_COMPROMISED_DATA;
  if(FixedPcdGetBool(PcdRaphaelNativePmapTest)){
    EFI_STATUS S=RaphaelArmNativePmap(R->ExpectedPhysBase,R->ExpectedMemBytes,R->RelayPa,Compiled?Compiled->Bytes:RelayBytes,mP.Tcr,Args);if(EFI_ERROR(S))return S;
    mMmuState.Pmap=RaphaelNativePmapState();
  }
  if(Compiled){
    // The diagnostic vectors, relay and checkpoint are part of the final
    // linked kernel and its original POST HMAC. Only mutable __DATA is set.
    UINT64 *Config=(VOID *)(UINTN)Pa(Compiled->Config);
    if(ReadUnaligned64(Config)!=SIGNATURE_64('R','P','H','D','C','F','G','1')||mOpcode!=0xd42a6a20U)return EFI_COMPROMISED_DATA;
    ZeroMem(Config,128);Config[0]=Pa(Compiled->Config);Config[1]=(UINTN)R;
    Config[2]=FixedPcdGet64(PcdRaphaelStackBase)+FixedPcdGet32(PcdRaphaelStackSize)-0x1000;
    extern VOID RaphaelMmuCaptured(VOID);Config[3]=(UINTN)RaphaelMmuCaptured;
    Config[4]=RaphaelNativePmapRoot();Config[5]=Pa(Compiled->Body);Config[6]=mMmuState.Pmap;Config[7]=RaphaelNativePlatformStop();
    Config[8]=R->ExpectedPhysBase;Config[9]=R->ExpectedMemBytes;
    WriteBackDataCacheRange(Config,128);
  }else{
  Vectors(mLowPa,R->RelayPa);Vectors(mHighPa,FixedPcdGetBool(PcdRaphaelNativePmapTest)?mP.LowVectors+2048:R->RelayPa);
  if(RaphaelNativePlatformStop()>=14)for(UINTN I=0;I<16;++I)if(I%4){
    if(CompareMem((VOID *)(UINTN)(mHighPa+I*128),mHigh+I*128,128)||
       CompareMem((VOID *)(UINTN)(mLowPa+I*128),mLow+I*128,128))return EFI_COMPROMISED_DATA;
  }
  CopyMem((VOID *)(UINTN)R->RelayPa,RaphaelMmuRelay,RelayBytes);
  WriteUnaligned64((VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayState-RaphaelMmuRelay)),(UINTN)R);
  WriteUnaligned64((VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayStack-RaphaelMmuRelay)),FixedPcdGet64(PcdRaphaelStackBase)+FixedPcdGet32(PcdRaphaelStackSize)-0x1000);
  extern VOID RaphaelMmuCaptured(VOID);
  WriteUnaligned64((VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayHandler-RaphaelMmuRelay)),(UINTN)RaphaelMmuCaptured);
  if(FixedPcdGetBool(PcdRaphaelNativeEarlyTest)) {
    RAPHAEL_NATIVE_EARLY_STATE *E=(VOID *)(UINTN)mMmuState.Early;
    UINT64 *Ranges=(VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayRanges-RaphaelMmuRelay));
    for(UINTN I=0;I<3;++I){Ranges[I*2]=E->Result.Ranges[I].Virtual;Ranges[I*2+1]=E->Result.Ranges[I].Bytes;}
  }
  if(FixedPcdGetBool(PcdRaphaelNativePmapTest)){
    WriteUnaligned64((VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayTransition-RaphaelMmuRelay)),RaphaelNativePmapRoot());
    WriteUnaligned64((VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayPhysicalBody-RaphaelMmuRelay)),R->RelayPa+(RaphaelMmuRelayBody-RaphaelMmuRelay));
    WriteUnaligned64((VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayPmap-RaphaelMmuRelay)),mMmuState.Pmap);
    UINT64 *Ranges=(VOID *)(UINTN)(R->RelayPa+(RaphaelMmuRelayRanges-RaphaelMmuRelay));ZeroMem(Ranges,8*sizeof(UINT64));Ranges[0]=R->ExpectedPhysBase;Ranges[1]=R->ExpectedMemBytes;
  }
  if(FixedPcdGetBool(PcdRaphaelNativePlatformTest))RaphaelArmNativePanics();
  *(UINT32 *)(UINTN)mArmPa=(UINT32)R->ProbeInstruction;
  Coherent(mLowPa,sizeof(mLow));Coherent(mHighPa,sizeof(mHigh));Coherent(mArmPa,4);
  }
  // DarwinEnter cleans its kernel grant, while our snapshots and pointers
  // live in the separate owned UEFI heap. Preserve those before caches stop.
  WriteBackInvalidateDataCacheRange((VOID *)(UINTN)FixedPcdGet64(PcdRaphaelArenaBase),
    FixedPcdGet32(PcdRaphaelArenaSize)-RAPHAEL_NATIVE_FAT_BYTES);
  WriteBackInvalidateDataCacheRange(D,sizeof(*D));
  // Handle faults before XNU installs its own low vector too.
  __asm__ volatile("dsb sy\n msr vbar_el1,%0\n isb"::"r"(mLowPa):"memory");
  return EFI_SUCCESS;
}
VOID RaphaelMmuCaptured(VOID) {
  RAPHAEL_NATIVE_MMU_RESULT *R=&gRaphaelNativeMmu;
  RaphaelNativeWatchdogResetReturn();
  BOOLEAN WatchdogOk=RaphaelNativeWatchdogStop();
  BOOLEAN PlatformOk=!FixedPcdGetBool(PcdRaphaelNativePlatformTest)||RestorePlatform();
  if(RaphaelNativePlatformStop()>=13)PlatformOk=RaphaelRestoreNativeGic(&mMmuState.Gic)&&PlatformOk;
  PlatformOk=PlatformOk&&WatchdogOk;
  R->MmuRestored=Sctlr()==R->SavedSctlr&&Vbar()==R->SavedVbar&&Tcr()==R->SavedTcr&&Ttbr0()==R->SavedTtbr0&&Ttbr1()==R->SavedTtbr1&&Mair()==R->SavedMair&&Cpacr()==R->SavedCpacr&&Tpidr0()==R->SavedTpidrEl0&&TpidrRo()==R->SavedTpidrro&&Tpidr1()==R->SavedTpidrEl1&&Sp0()==R->SavedSpEl0;
  CopyMem(mTablesAfter,(VOID *)(UINTN)R->Tables,sizeof(mTablesAfter));
  R->TablesCrcAfter=CalculateCrc32(mTablesAfter,sizeof(mTablesAfter));
  for(UINTN I=0;I<R->TablesBytes;++I)if(((UINT8 *)(UINTN)R->Tables)[I]!=mTables[I])++R->TablesChangedCount;
  BOOLEAN PT;
  if(FixedPcdGetBool(PcdRaphaelNativePmapTest))PT=RaphaelCaptureNativePmap(R->Ttbr0,R->Ttbr1,mCheckpoint,&R->VirtualTranslation);
  else PT=Translate(R->Ttbr0,mArmPa,FALSE,&R->PhysicalTranslation)&&Translate(R->Ttbr1,mCheckpoint,TRUE,&R->VirtualTranslation);
  R->ArgsOk=(FixedPcdGetBool(PcdRaphaelNativeEarlyTest)?RaphaelNativeEarlyArgs(R->X0,R->X1,mArgs):(R->X0==mP.ArmInit-mArmPa+mArgs&&R->X20==mArgs&&R->X21==0))&&
    (FixedPcdGetBool(PcdRaphaelNativeEarlyTest)||(R->X22==R->ExpectedVirtBase+mP.BootstrapSkip&&R->X23==R->ExpectedPhysBase+mP.BootstrapSkip&&R->X24==R->ExpectedMemBytes-mP.BootstrapSkip&&R->X25==R->Tables));
  BOOLEAN StackOk=RaphaelNativePlatformStop()>=11?
    RaphaelNativeEarlyStack(R->TpidrEl1,R->InterruptedSp,R->X20):
    R->InterruptedSp==mP.InterruptSp-(FixedPcdGetBool(PcdRaphaelNativeEarlyTest)?RaphaelNativeEarlyFrame():0);
  BOOLEAN Valid=R->Version==(FixedPcdGetBool(PcdRaphaelNativePmapTest)?2:1)&&R->Armed==1&&R->TrapCount==1&&R->Esr==0xf2005351ULL&&R->Elr==mCheckpoint&&
    R->VectorSlot==0&&(R->Spsr&0x3df)==(RaphaelNativePlatformStop()>=14&&RaphaelNativePlatformStop()!=20?0x204:0x3c4)&&(RaphaelNativePlatformStop()>=17?RaphaelNativeEarlyExceptionStack(R->Sp):R->Sp==mP.ExceptionSp)&&StackOk&&R->Lr==(FixedPcdGetBool(PcdRaphaelNativeEarlyTest)?RaphaelNativeEarlyReturn():mP.ArmInit)&&R->CurrentEl==4&&R->Vbar==mP.HighVectors&&
    R->Sctlr==mP.Sctlr&&(R->CacheOffSctlr&0x1005)==0&&R->Tcr==mP.Tcr&&R->Mair==mP.Mair&&
    (FixedPcdGetBool(PcdRaphaelNativePmapTest)?(R->PhysicalTranslation==0):(R->Ttbr0==R->Tables&&R->Ttbr1==R->Tables+4096&&R->PhysicalTranslation==mArmPa))&&PT&&R->VirtualTranslation==mArmPa&&
    PlatformOk&&R->MmuRestored&&R->ArgsOk&&ExactTables()&&R->TablesChangedCount&&R->TablesCrcBefore!=R->TablesCrcAfter;
  if(FixedPcdGetBool(PcdRaphaelNativeEarlyTest))Valid=RaphaelRestoreNativeEarly()&&Valid;
  if(!RaphaelNativeCompiledPolicy()){
  CopyMem((VOID *)(UINTN)mLowPa,mLow,sizeof(mLow));CopyMem((VOID *)(UINTN)mHighPa,mHigh,sizeof(mHigh));
  *(UINT32 *)(UINTN)mArmPa=(UINT32)R->OriginalInstruction;
  Coherent(mLowPa,sizeof(mLow));Coherent(mHighPa,sizeof(mHigh));Coherent(mArmPa,4);
  }
  R->PatchRestored=CompareMem((VOID *)(UINTN)mLowPa,mLow,sizeof(mLow))==0&&CompareMem((VOID *)(UINTN)mHighPa,mHigh,sizeof(mHigh))==0&&*(UINT32 *)(UINTN)mArmPa==R->OriginalInstruction;
  CopyMem((VOID *)(UINTN)R->Tables,mTables,sizeof(mTables));WriteBackDataCacheRange((VOID *)(UINTN)R->Tables,sizeof(mTables));
  R->TablesRestored=CompareMem((VOID *)(UINTN)R->Tables,mTables,sizeof(mTables))==0;
  R->Status=Valid&&R->PatchRestored&&R->TablesRestored?3:2;R->Error=R->Status==3?0:1;
  RaphaelNativeMmuFinish(R->Status==3);
}

UINT64 RaphaelNativeLowVectorVa(VOID){return mP.LowVectors;}
UINT64 RaphaelNativeHighVectorVa(VOID){return mP.HighVectors;}
