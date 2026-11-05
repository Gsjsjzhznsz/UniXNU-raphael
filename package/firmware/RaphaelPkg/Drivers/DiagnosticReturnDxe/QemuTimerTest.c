// SPDX-License-Identifier: BSD-2-Clause-Patent
// Runs with actual generic CPU/GIC/TimerDxe in our own QEMU firmware, no AAVMF.
#include <RaphaelDiagnostic.h>
#include <Library/ArmLib.h>
#include <Library/DebugLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Protocol/Cpu.h>
#include <Protocol/HardwareInterrupt.h>
#include <Protocol/Timer.h>

STATIC VOID EFIAPI Tick (EFI_EVENT Event, VOID *Context) {
  (VOID)Event; ++*(volatile UINT64 *)Context;
}
EFI_STATUS RaphaelTestQemuTimer (RAPHAEL_DIAGNOSTIC *D) {
  RAPHAEL_QEMU_ARCH_RESULT *R = &D->QemuArch;
  EFI_CPU_ARCH_PROTOCOL *Cpu = NULL;
  EFI_HARDWARE_INTERRUPT_PROTOCOL *Interrupt = NULL;
  EFI_TIMER_ARCH_PROTOCOL *Timer = NULL;
  EFI_EVENT Relative = NULL, Periodic = NULL;
  EFI_STATUS Status;
  UINTN Index;
  UINT64 Start, Now;
  BOOLEAN State;
  Status = gBS->LocateProtocol (&gEfiCpuArchProtocolGuid,NULL,(VOID **)&Cpu); R->CpuProtocol = !EFI_ERROR(Status);
  Status = gBS->LocateProtocol (&gHardwareInterruptProtocolGuid,NULL,(VOID **)&Interrupt); R->InterruptProtocol = !EFI_ERROR(Status);
  Status = gBS->LocateProtocol (&gEfiTimerArchProtocolGuid,NULL,(VOID **)&Timer); R->TimerProtocol = !EFI_ERROR(Status);
  if (!R->CpuProtocol || !R->InterruptProtocol || !R->TimerProtocol || R->Status != 2) { return EFI_NOT_READY; }
  Status = Timer->GetTimerPeriod(Timer,&R->Period); if(EFI_ERROR(Status) || R->Period == 0)return EFI_DEVICE_ERROR;
  Status = gBS->CreateEvent(EVT_TIMER,TPL_CALLBACK,NULL,NULL,&Relative); if(EFI_ERROR(Status))goto Done;
  Start=ArmReadCntPct(); Status=gBS->SetTimer(Relative,TimerRelative,1000000); // 100 ms design test
  if(EFI_ERROR(Status))goto Done;
  Status=gBS->WaitForEvent(1,&Relative,&Index); R->RelativeTicks=ArmReadCntPct()-Start;
  R->RelativeFired=!EFI_ERROR(Status)&&Index==0;
  if(!R->RelativeFired || R->RelativeTicks<R->Frequency*8/100 || R->RelativeTicks>R->Frequency) {Status=EFI_TIMEOUT;goto Done;}
  Status=gBS->CreateEvent(EVT_TIMER|EVT_NOTIFY_SIGNAL,TPL_CALLBACK,Tick,&R->PeriodicCount,&Periodic);if(EFI_ERROR(Status))goto Done;
  Start=ArmReadCntPct();Status=gBS->SetTimer(Periodic,TimerPeriodic,200000);if(EFI_ERROR(Status))goto Done; // 20 ms
  while(*(volatile UINT64 *)&R->PeriodicCount<5 && ArmReadCntPct()-Start<R->Frequency) {__asm__ volatile("yield");}
  R->PeriodicTicks=ArmReadCntPct()-Start;
  if(R->PeriodicCount<5 || R->PeriodicTicks<R->Frequency*8/100 || R->PeriodicTicks>R->Frequency) {Status=EFI_TIMEOUT;goto Done;}
  Status=gBS->SetTimer(Periodic,TimerCancel,0);if(EFI_ERROR(Status))goto Done;
  UINT64 Saved=R->PeriodicCount;Start=ArmReadCntPct();
  do {Now=ArmReadCntPct();__asm__ volatile("yield");}while(Now-Start<R->Frequency/10);
  R->CancelStable=Saved==*(volatile UINT64 *)&R->PeriodicCount;
  if(!R->CancelStable || !R->ManagerCompleted || R->ManagerTicks<(FixedPcdGetBool(PcdRaphaelNativeBoot)&&FixedPcdGetBool(PcdRaphaelUfsPayload)?1:R->Frequency*18/10) || R->ManagerTicks>R->Frequency*5) {Status=EFI_COMPROMISED_DATA;goto Done;}
  Status=EFI_SUCCESS;
Done:
  if(Relative != NULL){gBS->SetTimer(Relative,TimerCancel,0);gBS->CloseEvent(Relative);}
  if(Periodic != NULL){gBS->SetTimer(Periodic,TimerCancel,0);gBS->CloseEvent(Periodic);}
  if(Timer != NULL){EFI_STATUS Stop=Timer->SetTimerPeriod(Timer,0);R->TimerDisabled=!EFI_ERROR(Stop);if(EFI_ERROR(Stop))Status=Stop;}
  if(Interrupt != NULL){
    UINT64 Sources[4]={R->SecureInt,R->PhysicalInt,R->VirtualInt,R->HypInt}; R->SourcesDisabled=1;
    for(UINTN I=0;I<4;++I) {
      EFI_STATUS Stop=Interrupt->DisableInterruptSource(Interrupt,Sources[I]);
      State=TRUE;
      if(EFI_ERROR(Stop) || EFI_ERROR(Interrupt->GetInterruptSourceState(Interrupt,Sources[I],&State)) || State)R->SourcesDisabled=0;
    }
  }
  if(Cpu != NULL)Cpu->DisableInterrupt(Cpu);
  if(!R->SourcesDisabled || !R->TimerDisabled)Status=EFI_DEVICE_ERROR;
  if(!EFI_ERROR(Status))R->Status=3;
  DEBUG((DEBUG_INFO,"RAPHAEL QEMU timer status=%lu relative=%lu periodic=%lu cancel=%lu manager=%lu error=%r\n",R->Status,R->RelativeFired,R->PeriodicCount,R->CancelStable,R->ManagerCompleted,Status));
  return Status;
}
