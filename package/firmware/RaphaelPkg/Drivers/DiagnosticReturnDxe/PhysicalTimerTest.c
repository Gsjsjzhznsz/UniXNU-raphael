// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelPhysicalTimer.h>
#include <Library/ArmLib.h>
#include <Library/HobLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Protocol/Timer.h>
#include <Protocol/HardwareInterrupt.h>
STATIC VOID EFIAPI UnusedNotify(UINT64 Time) {(VOID)Time;}
STATIC VOID EFIAPI PeriodicTick(EFI_EVENT Event,VOID *Context) { (VOID)Event; ++*(volatile UINT64 *)Context; }
EFI_STATUS RaphaelTestPhysicalTimer(VOID) {
  VOID *Hob=GetFirstGuidHob(&gRaphaelPhysicalTimerHobGuid);
  if (!Hob || GET_GUID_HOB_DATA_SIZE(Hob)!=sizeof(RAPHAEL_PHYSICAL_TIMER_STATE *)) return EFI_NOT_FOUND;
  RAPHAEL_PHYSICAL_TIMER_STATE *State=*(RAPHAEL_PHYSICAL_TIMER_STATE **)GET_GUID_HOB_DATA(Hob);
  RAPHAEL_PHYSICAL_TIMER_RESULT *R=&State->Result;
  EFI_TIMER_ARCH_PROTOCOL *Timer=NULL; EFI_EVENT Relative=NULL,Periodic=NULL;
  EFI_STATUS Status=gBS->LocateProtocol(&gEfiTimerArchProtocolGuid,NULL,(VOID **)&Timer);
  if (EFI_ERROR(Status) || R->Status!=3 || R->Reason || !State->Shutdown) return EFI_NOT_READY;
  UINT64 Start,Now,Polls,Period=0;
  Status=Timer->GetTimerPeriod(Timer,&Period); if (EFI_ERROR(Status) || Period!=100000) return EFI_COMPROMISED_DATA;
  // Invalid/unsupported protocol requests must leave the running service intact.
  EFI_HARDWARE_INTERRUPT_PROTOCOL *Interrupt=NULL;
  Status=gBS->LocateProtocol(&gHardwareInterruptProtocolGuid,NULL,(VOID **)&Interrupt);
  if (EFI_ERROR(Status) || Timer->GetTimerPeriod(Timer,NULL)!=EFI_INVALID_PARAMETER ||
      Timer->GenerateSoftInterrupt(Timer)!=EFI_UNSUPPORTED ||
      Timer->RegisterHandler(Timer,UnusedNotify)!=EFI_ALREADY_STARTED ||
      Timer->SetTimerPeriod(Timer,MAX_UINT64)!=EFI_UNSUPPORTED ||
      Timer->SetTimerPeriod(Timer,1)!=EFI_UNSUPPORTED ||
      Interrupt->EnableInterruptSource(Interrupt,0)!=EFI_UNSUPPORTED ||
      Interrupt->DisableInterruptSource(Interrupt,0)!=EFI_UNSUPPORTED ||
      Interrupt->RegisterInterruptSource(Interrupt,0,NULL)!=EFI_UNSUPPORTED ||
      Interrupt->EndOfInterrupt(Interrupt,(UINTN)R->Intid)!=EFI_UNSUPPORTED ||
      R->Period!=Period) {Status=EFI_COMPROMISED_DATA;goto Done;}
  Status=Timer->SetTimerPeriod(Timer,50000); if (EFI_ERROR(Status)) goto Done;
  Status=Timer->GetTimerPeriod(Timer,&Period); if (EFI_ERROR(Status) || Period<50000 || Period>50010) {Status=EFI_COMPROMISED_DATA;goto Done;}
  Status=gBS->CreateEvent(EVT_TIMER,TPL_CALLBACK,NULL,NULL,&Relative); if (EFI_ERROR(Status)) goto Done;
  Start=ArmReadCntPct(); Status=gBS->SetTimer(Relative,TimerRelative,1000000); if (EFI_ERROR(Status)) goto Done;
  for (Polls=0;Polls<20000000;++Polls) {
    Status=gBS->CheckEvent(Relative);
    if (!EFI_ERROR(Status)) {R->RelativeFired=1;break;}
    Now=ArmReadCntPct(); if (Status!=EFI_NOT_READY || Now<Start || Now-Start>=R->Frequency || *(volatile UINT64 *)&R->Reason) break;
    __asm__ volatile("yield");
  }
  R->RelativeTicks=ArmReadCntPct()-Start;
  if (!R->RelativeFired || R->RelativeTicks<R->Frequency*8/100 || R->RelativeTicks>R->Frequency) {Status=EFI_TIMEOUT;goto Done;}
  Status=gBS->CreateEvent(EVT_TIMER|EVT_NOTIFY_SIGNAL,TPL_CALLBACK,PeriodicTick,&R->PeriodicCount,&Periodic);if (EFI_ERROR(Status)) goto Done;
  Start=ArmReadCntPct();Status=gBS->SetTimer(Periodic,TimerPeriodic,200000);if (EFI_ERROR(Status)) goto Done;
  for (Polls=0;Polls<20000000 && *(volatile UINT64 *)&R->PeriodicCount<5;++Polls) {
    Now=ArmReadCntPct();if (Now<Start || Now-Start>=R->Frequency || *(volatile UINT64 *)&R->Reason) break;
    __asm__ volatile("yield");
  }
  R->PeriodicTicks=ArmReadCntPct()-Start;
  if (R->PeriodicCount<5 || R->PeriodicTicks<R->Frequency*8/100 || R->PeriodicTicks>R->Frequency) {Status=EFI_TIMEOUT;goto Done;}
  Status=gBS->SetTimer(Periodic,TimerCancel,0);if (EFI_ERROR(Status)) goto Done;
  UINT64 Saved=R->PeriodicCount;Start=ArmReadCntPct();Now=Start;
  for (Polls=0;Polls<20000000 && Now-Start<R->Frequency/10;++Polls) {
    Now=ArmReadCntPct();if (Now<Start || *(volatile UINT64 *)&R->Reason) break;
    __asm__ volatile("yield");
  }
  R->CancelTicks=Now-Start; R->CancelStable=Saved==*(volatile UINT64 *)&R->PeriodicCount && R->CancelTicks>=R->Frequency/10;
  Status=R->CancelStable && !R->Reason && R->IrqCount>=20 && R->IrqCount==R->EoiCount && R->NotifyCount>0 && !R->Unexpected && !R->Spurious ? EFI_SUCCESS : EFI_COMPROMISED_DATA;
  if (!EFI_ERROR(Status)) {
    Status=Timer->SetTimerPeriod(Timer,0);
    if (EFI_ERROR(Status)) goto Done;
    UINT64 Irqs=R->IrqCount; Start=ArmReadCntPct();Now=Start;
    for (Polls=0;Polls<20000000 && Now-Start<R->Frequency/10;++Polls) {
      Now=ArmReadCntPct();if (Now<Start) break; __asm__ volatile("yield");
    }
    if (Now-Start<R->Frequency/10 || Irqs!=*(volatile UINT64 *)&R->IrqCount || R->Period!=0) Status=EFI_COMPROMISED_DATA;
  }
Done:
  if (Relative) {gBS->SetTimer(Relative,TimerCancel,0);gBS->CloseEvent(Relative);}
  if (Periodic) {gBS->SetTimer(Periodic,TimerCancel,0);gBS->CloseEvent(Periodic);}
  if (Timer) {EFI_STATUS Stop=Timer->SetTimerPeriod(Timer,0);if (EFI_ERROR(Stop))Status=Stop;}
  if (State->Shutdown && !State->Shutdown()) Status=EFI_DEVICE_ERROR;
  if (!EFI_ERROR(Status)) R->Status=4;
  return Status;
}
