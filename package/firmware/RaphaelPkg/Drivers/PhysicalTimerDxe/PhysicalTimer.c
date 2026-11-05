// SPDX-License-Identifier: BSD-2-Clause-Patent
// Independently implemented diagnostic physical timer. No generic GIC init,
// no virtual/secure/hypervisor timer access for writing, no guessed PPI.
#include <RaphaelDiagnostic.h>
#include <RaphaelPhysicalTimer.h>
#include <Library/ArmLib.h>
#include <Library/BaseLib.h>
#include <Library/HobLib.h>
#include <Library/IoLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Protocol/Cpu.h>
#include <Protocol/HardwareInterrupt.h>
#include <Protocol/Timer.h>

STATIC RAPHAEL_PHYSICAL_TIMER_STATE *mState;
STATIC RAPHAEL_PHYSICAL_TIMER_RESULT *mR;
STATIC EFI_CPU_ARCH_PROTOCOL *mCpu;
STATIC EFI_TIMER_NOTIFY mNotify;
STATIC HARDWARE_INTERRUPT_HANDLER mHandler;
STATIC UINT64 mTicks, mLast, mLimit;
STATIC UINTN mAcknowledged = 1023;
STATIC BOOLEAN mVector;
STATIC UINT64 Daif(VOID) { UINT64 V; __asm__ volatile("mrs %0,daif":"=r"(V)); return V; }
STATIC UINT64 Igrpen(VOID) { UINT64 V; __asm__ volatile("mrs %0,icc_igrpen1_el1":"=r"(V)); return V; }
STATIC UINT64 Hppir(VOID) { UINT64 V; __asm__ volatile("mrs %0,icc_hppir1_el1":"=r"(V)); return V; }
STATIC UINT64 Vctl(VOID) { UINT64 V; __asm__ volatile("mrs %0,cntv_ctl_el0":"=r"(V)); return V; }
STATIC UINT64 Vcval(VOID) { UINT64 V; __asm__ volatile("mrs %0,cntv_cval_el0":"=r"(V)); return V; }
STATIC VOID SetIgrpen(UINT64 V) { __asm__ volatile("msr icc_igrpen1_el1,%0\n isb"::"r"(V):"memory"); }
STATIC VOID Barrier(VOID) { __asm__ volatile("dsb sy\n isb":::"memory"); }
STATIC BOOLEAN WaitClear(UINT64 Address, UINT32 Mask) {
  UINT64 Start = ArmReadCntPct();
  for (UINTN N=0; N<1000000; ++N) {
    if (!(MmioRead32((UINTN)Address) & Mask)) return TRUE;
    UINT64 Now=ArmReadCntPct();
    if (Now<Start || Now-Start>=mR->Frequency/10) break;
  }
  return FALSE;
}
STATIC VOID MaskSource(VOID) {
  ArmWriteCntpCtl(2); ArmInstructionSynchronizationBarrier();
  if ((ArmReadCntpCtl()&3)!=2) mR->Reason=1;
}
STATIC EFI_STATUS EFIAPI SourceEnable(EFI_HARDWARE_INTERRUPT_PROTOCOL *This, UINTN Source) {
  (VOID)This;
  if (Source!=mR->Intid) return EFI_UNSUPPORTED;
  if (!mHandler) return EFI_NOT_READY;
  MmioWrite32((UINTN)(mR->SgiBase+0x100), (UINT32)(1ULL<<Source)); Barrier();
  return MmioRead32((UINTN)(mR->SgiBase+0x100))==(1ULL<<Source) ? EFI_SUCCESS : EFI_DEVICE_ERROR;
}
STATIC EFI_STATUS EFIAPI SourceDisable(EFI_HARDWARE_INTERRUPT_PROTOCOL *This, UINTN Source) {
  (VOID)This;
  if (Source!=mR->Intid) return EFI_UNSUPPORTED;
  MmioWrite32((UINTN)(mR->SgiBase+0x180),(UINT32)(1ULL<<Source)); Barrier();
  return WaitClear(mR->RdBase,8) && !MmioRead32((UINTN)(mR->SgiBase+0x100)) ? EFI_SUCCESS : EFI_DEVICE_ERROR;
}
STATIC EFI_STATUS EFIAPI SourceState(EFI_HARDWARE_INTERRUPT_PROTOCOL *This,UINTN Source,BOOLEAN *State) {
  (VOID)This;
  if (!State) return EFI_INVALID_PARAMETER;
  if (Source!=mR->Intid) return EFI_UNSUPPORTED;
  *State=(MmioRead32((UINTN)(mR->SgiBase+0x100))&(1U<<Source))!=0;
  return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI SourceEoi(EFI_HARDWARE_INTERRUPT_PROTOCOL *This,UINTN Source) {
  (VOID)This;
  if (Source!=mR->Intid || mAcknowledged!=Source) return EFI_UNSUPPORTED;
  // EOImode0 was checked before enabling IRQ. Never write DIR.
  __asm__ volatile("dsb sy\n msr icc_eoir1_el1,%0\n isb"::"r"((UINT64)Source):"memory");
  mAcknowledged=1023; ++mR->EoiCount;
  return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI SourceRegister(EFI_HARDWARE_INTERRUPT_PROTOCOL *This,UINTN Source,HARDWARE_INTERRUPT_HANDLER Handler) {
  if (Source!=mR->Intid) return EFI_UNSUPPORTED;
  if (Handler && mHandler) return EFI_ALREADY_STARTED;
  if (!Handler && !mHandler) return EFI_INVALID_PARAMETER;
  EFI_STATUS Status=SourceDisable(This,Source);
  if (!EFI_ERROR(Status)) mHandler=Handler;
  // Registration itself never enables a source. Enable only after vector setup.
  return Status;
}
STATIC EFI_HARDWARE_INTERRUPT_PROTOCOL mInterrupt={SourceRegister,SourceEnable,SourceDisable,SourceState,SourceEoi};
STATIC EFI_STATUS EFIAPI RegisterNotify(EFI_TIMER_ARCH_PROTOCOL *This,EFI_TIMER_NOTIFY Notify) {
  (VOID)This;
  if (!Notify && !mNotify) return EFI_INVALID_PARAMETER;
  if (Notify && mNotify) return EFI_ALREADY_STARTED;
  EFI_TPL Old=gBS->RaiseTPL(TPL_HIGH_LEVEL); mNotify=Notify; gBS->RestoreTPL(Old);
  return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI SetPeriod(EFI_TIMER_ARCH_PROTOCOL *This,UINT64 Period) {
  (VOID)This;
  UINT64 Ticks=0, Actual=0;
  // Bounded diagnostic service: 1us..1s; reject overflow without changing state.
  if (Period) {
    if (Period<10 || Period>10000000 || Period>MAX_UINT64/mR->Frequency) return EFI_UNSUPPORTED;
    Ticks=(Period*mR->Frequency+9999999)/10000000;
    if (!Ticks || Ticks>MAX_UINT64/10000000) return EFI_UNSUPPORTED;
    Actual=(Ticks*10000000+mR->Frequency-1)/mR->Frequency;
  }
  EFI_TPL Old=gBS->RaiseTPL(TPL_HIGH_LEVEL);
  MaskSource(); mR->Period=Actual; mTicks=Ticks; mLast=ArmReadCntPct();
  if (Ticks && !mR->Reason && mLast<=MAX_UINT64-Ticks && mLast<mLimit) {
    ArmWriteCntpCval(mLast+Ticks); ArmWriteCntpCtl(1); ArmInstructionSynchronizationBarrier();
  }
  gBS->RestoreTPL(Old);
  return mR->Reason ? EFI_DEVICE_ERROR : EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI GetPeriod(EFI_TIMER_ARCH_PROTOCOL *This,UINT64 *Period) {
  (VOID)This; if (!Period) return EFI_INVALID_PARAMETER; *Period=mR->Period; return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI SoftInterrupt(EFI_TIMER_ARCH_PROTOCOL *This) { (VOID)This; return EFI_UNSUPPORTED; }
STATIC EFI_TIMER_ARCH_PROTOCOL mTimer={RegisterNotify,SetPeriod,GetPeriod,SoftInterrupt};
STATIC VOID EFIAPI TimerInterrupt(UINTN Source,EFI_SYSTEM_CONTEXT Context) {
  (VOID)Context;
  EFI_TPL Old=gBS->RaiseTPL(TPL_HIGH_LEVEL);
  UINT64 Now=ArmReadCntPct(); UINTN Ctl=ArmReadCntpCtl();
  MaskSource();
  mR->SourceMasked=(ArmReadCntpCtl()&3)==2;
  if (EFI_ERROR(SourceEoi(&mInterrupt,Source))) mR->Reason=2;
  if (!(Ctl&4) || (Ctl&3)!=1 || !mTicks || Now<mLast || Now>=mLimit) mR->Reason=3;
  if (!mR->Reason) {
    UINT64 Delta=Now-mLast;
    // Rearm ahead of current time in O(1), including delayed/coalesced periods.
    UINT64 Next=ArmReadCntpCval();
    if (Next<=Now) Next+=( (Now-Next)/mTicks+1 )*mTicks;
    if (Next<=Now || Next>=mLimit || Delta>mR->Frequency*10) mR->Reason=4;
    else {
      mLast=Now; ArmWriteCntpCval(Next); ArmWriteCntpCtl(1); ArmInstructionSynchronizationBarrier();
      if (mNotify) { ++mR->NotifyCount; mNotify(Delta*10000000/mR->Frequency); }
    }
  }
  if (mR->Reason) MaskSource();
  gBS->RestoreTPL(Old);
}
STATIC VOID EFIAPI IrqException(EFI_EXCEPTION_TYPE Type,EFI_SYSTEM_CONTEXT Context) {
  (VOID)Type;
  UINT64 Id; __asm__ volatile("mrs %0,icc_iar1_el1":"=r"(Id));
  if (Id>=1020 && Id<=1023) { ++mR->Spurious; return; }
  mAcknowledged=(UINTN)Id;
  UINT64 Now=ArmReadCntPct(); ++mR->IrqCount;
  if (!mR->FirstCounter) mR->FirstCounter=Now; mR->LastCounter=Now;
  if (Id==mR->Intid && mHandler) mHandler((UINTN)Id,Context);
  else {
    ++mR->Unexpected; mR->Reason=5; MaskSource();
    __asm__ volatile("dsb sy\n msr icc_eoir1_el1,%0\n isb"::"r"(Id):"memory");
    mAcknowledged=1023; ++mR->EoiCount;
    Context.SystemContextAArch64->SPSR |= 0x80;
  }
}
STATIC BOOLEAN EFIAPI Shutdown(VOID) {
  if (!mState || !mState->Dirty) return TRUE;
  ArmDisableInterrupts(); MaskSource();
  SetIgrpen(mR->SavedIgrpen);
  MmioWrite32((UINTN)mR->GicD,(UINT32)mR->SavedDist); Barrier();
  BOOLEAN Ok=WaitClear(mR->GicD,0x80000000);
  if (EFI_ERROR(SourceDisable(&mInterrupt,(UINTN)mR->Intid))) Ok=FALSE;
  ArmWriteCntpCval(mR->SavedCval); ArmWriteCntpCtl((UINTN)mR->SavedCtl&3); ArmInstructionSynchronizationBarrier();
  UINT64 Start=ArmReadCntPct(); BOOLEAN Withdrawn=FALSE;
  for (UINTN N=0;N<1000000;++N) {
    mR->PendingAfter=MmioRead32((UINTN)(mR->SgiBase+0x200));
    if (!((mR->PendingAfter^mR->SavedPending)&(1ULL<<mR->Intid)) && Hppir()==1023) { Withdrawn=TRUE; break; }
    UINT64 Now=ArmReadCntPct(); if (Now<Start || Now-Start>=mR->Frequency/10) break;
  }
  mR->DistAfter=MmioRead32((UINTN)mR->GicD); mR->IgrpenAfter=Igrpen();
  mR->CtlAfter=ArmReadCntpCtl(); mR->CvalAfter=ArmReadCntpCval();
  mR->EnableAfter=MmioRead32((UINTN)(mR->SgiBase+0x100)); mR->ActiveAfter=MmioRead32((UINTN)(mR->SgiBase+0x300));
  mR->VctlAfter=Vctl(); mR->VcvalAfter=Vcval(); mR->TimerStopped=!(mR->CtlAfter&1);
  if (mVector) { if (EFI_ERROR(mCpu->RegisterInterruptHandler(mCpu,ARM_ARCH_EXCEPTION_IRQ,NULL))) Ok=FALSE; mVector=FALSE; }
  mR->EndCounter=ArmReadCntPct();
  __asm__ volatile("msr daif,%0\n isb"::"r"(mR->SavedDaif):"memory"); mR->DaifAfter=Daif();
  mR->RestoreOk=Ok && Withdrawn && mR->DistAfter==mR->SavedDist && mR->IgrpenAfter==mR->SavedIgrpen &&
    ((mR->CtlAfter^mR->SavedCtl)&3)==0 && mR->CvalAfter==mR->SavedCval && mR->EnableAfter==mR->SavedEnable &&
    mR->ActiveAfter==mR->SavedActive && mR->DaifAfter==mR->SavedDaif &&
    ((mR->VctlAfter^mR->SavedVctl)&3)==0 && mR->VcvalAfter==mR->SavedVcval && mAcknowledged==1023;
  mState->Dirty=0;
  return mR->RestoreOk!=0;
}
STATIC VOID EFIAPI ExitBoot(EFI_EVENT Event,VOID *Context) { (VOID)Event;(VOID)Context;Shutdown(); }
EFI_STATUS EFIAPI PhysicalTimerEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *SystemTable) {
  (VOID)Image;(VOID)SystemTable;
  VOID *Hob=GetFirstGuidHob(&gRaphaelPhysicalTimerHobGuid);
  if (!Hob || GET_GUID_HOB_DATA_SIZE(Hob)!=sizeof(mState)) return EFI_NOT_FOUND;
  mState=*(RAPHAEL_PHYSICAL_TIMER_STATE **)GET_GUID_HOB_DATA(Hob); mR=&mState->Result;
  if (mR->Version!=1 || mR->Status!=2 || !mR->MappedVerified || mState->Dirty || mR->Intid<16 || mR->Intid>=32) return EFI_NOT_READY;
  RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();
  UINT64 Ctlr; __asm__ volatile("mrs %0,icc_ctlr_el1":"=r"(Ctlr));
  if ((Daif()&0x3c0)!=0x3c0 || (Ctlr&2) || Igrpen()!=mR->SavedIgrpen || Hppir()!=1023 ||
      MmioRead32((UINTN)mR->GicD)!=mR->SavedDist || (ArmReadCntpCtl()&3)!=(mR->SavedCtl&3) ||
      ArmReadCntpCval()!=mR->SavedCval || MmioRead32((UINTN)(mR->SgiBase+0x300)) ||
      (MmioRead32((UINTN)(mR->SgiBase+0x200))&(1ULL<<mR->Intid)) ||
      (MmioRead32((UINTN)mR->RdBase)&8) || (MmioRead32((UINTN)(mR->RdBase+0x14))&6)) return EFI_NOT_READY;
  // Repeat the non-atomic NS enable/LPI view immediately before ownership use.
  for (UINTN I=1;I<=(D->Gic.Typer&31);++I) if (MmioRead32((UINTN)(mR->GicD+0x100+4*I))) return EFI_NOT_READY;
  for (UINTN I=0;I<D->Gic.FrameCount;++I) if ((MmioRead32((UINTN)D->Gic.Frames[I].Base)&1) ||
      MmioRead32((UINTN)(D->Gic.Frames[I].Base+0x10100))) return EFI_NOT_READY;
  EFI_STATUS Status=gBS->LocateProtocol(&gEfiCpuArchProtocolGuid,NULL,(VOID **)&mCpu);
  if (EFI_ERROR(Status)) return Status; mR->CpuProtocol=1;
  if (ArmReadCntPct()>MAX_UINT64-mR->Frequency*11) return EFI_UNSUPPORTED;
  mState->Shutdown=Shutdown; mState->Dirty=1;
  Status=mCpu->RegisterInterruptHandler(mCpu,ARM_ARCH_EXCEPTION_IRQ,IrqException);
  if (EFI_ERROR(Status)) goto Failed; mVector=TRUE; mR->IrqRegistered=1;
  Status=SourceRegister(&mInterrupt,(UINTN)mR->Intid,TimerInterrupt); if (EFI_ERROR(Status)) goto Failed;
  Status=SourceEnable(&mInterrupt,(UINTN)mR->Intid); if (EFI_ERROR(Status)) goto Failed;
  MmioWrite32((UINTN)mR->GicD,(UINT32)(mR->SavedDist|2)); Barrier();
  if (MmioRead32((UINTN)mR->GicD)!=(mR->SavedDist|2)) { Status=EFI_DEVICE_ERROR; goto Failed; }
  SetIgrpen(1); if (Igrpen()!=1) { Status=EFI_DEVICE_ERROR; goto Failed; }
  mR->StartCounter=ArmReadCntPct(); mLimit=mR->StartCounter+mR->Frequency*10;
  Status=SetPeriod(&mTimer,100000); if (EFI_ERROR(Status)) goto Failed; // 10ms design period
  EFI_EVENT Event=NULL;
  Status=gBS->CreateEvent(EVT_SIGNAL_EXIT_BOOT_SERVICES,TPL_NOTIFY,ExitBoot,NULL,&Event);
  if (EFI_ERROR(Status)) goto Failed;
  EFI_HANDLE Handle=NULL;
  mR->Status=3;
  Status=gBS->InstallMultipleProtocolInterfaces(&Handle,&gHardwareInterruptProtocolGuid,&mInterrupt,&gEfiTimerArchProtocolGuid,&mTimer,NULL);
  if (EFI_ERROR(Status)) { gBS->CloseEvent(Event); goto Failed; }
  mR->HwProtocol=1; mR->TimerProtocol=1;
  return EFI_SUCCESS;
Failed:
  Shutdown(); return Status;
}
