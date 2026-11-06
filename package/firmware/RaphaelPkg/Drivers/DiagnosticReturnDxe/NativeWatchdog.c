// SPDX-License-Identifier: BSD-2-Clause-Patent
// SM8150 watchdog register semantics: pinned MiCode watchdog_v2.c.
// SEC accepts the mapping only from the current boot FDT and generated policy.
#include <RaphaelDiagnostic.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/BaseLib.h>
#include <Library/ArmLib.h>
STATIC UINT32 Read(UINT64 Base,UINT32 Offset){return *(volatile UINT32 *)(UINTN)(Base+Offset);}
STATIC VOID Write(UINT64 Base,UINT32 Offset,UINT32 Value){
 *(volatile UINT32 *)(UINTN)(Base+Offset)=Value;__asm__ volatile("dsb sy":::"memory");
}
// Explicit diagnostic return mode: preserve the already armed hardware dog.
// Persisted UFS records survive the reset; no full FDT checkpoint is returned.
VOID RaphaelNativeWatchdogResetReturn(VOID){
 if(!FixedPcdGetBool(PcdRaphaelHardwareWatchdogReturn))return;
 RAPHAEL_NATIVE_WATCHDOG_RESULT *R=RaphaelNativeWatchdogResult();
 // Use only this image's existing, qualified resource and thresholds.
 if(!R->Armed||!R->Base||R->Seconds!=20||!R->Frequency)return;
 Write(R->Base,8,0);
 Write(R->Base,16,(UINT32)(R->Frequency*R->Seconds));
 Write(R->Base,20,(UINT32)(R->Frequency*(R->Seconds+1)));
 Write(R->Base,8,1);Write(R->Base,4,1);
 DEBUG((DEBUG_INFO,"NATIVE_WATCHDOG_RESET_RETURN armed; waiting for hardware bite\n"));
 ArmDisableInterrupts();
 for(;;)CpuPause();
}
BOOLEAN RaphaelNativeWatchdogStop(VOID){
 RAPHAEL_NATIVE_WATCHDOG_RESULT *R=RaphaelNativeWatchdogResult();
 if(!R->Armed)return TRUE;
 Write(R->Base,8,0);Write(R->Base,16,(UINT32)R->SavedBark);Write(R->Base,20,(UINT32)R->SavedBite);
 Write(R->Base,8,(UINT32)R->SavedEnable);
 R->RestoredEnable=Read(R->Base,8);R->RestoredBark=Read(R->Base,16);R->RestoredBite=Read(R->Base,20);
 R->RestoreOk=R->RestoredEnable==R->SavedEnable&&R->RestoredBark==R->SavedBark&&R->RestoredBite==R->SavedBite;
 if(R->RestoreOk){R->Armed=0;R->Status=3;}else R->Status=4;
 return R->RestoreOk;
}
EFI_STATUS RaphaelNativeWatchdogArm(VOID){
 UINT64 Base=FixedPcdGet64(PcdRaphaelNativeWatchdogBase);
 if(!Base)return EFI_SUCCESS;
 RAPHAEL_NATIVE_WATCHDOG_RESULT *R=RaphaelNativeWatchdogResult();
 ZeroMem(R,sizeof(*R));R->Version=1;R->Status=1;R->Base=Base;
 R->Frequency=FixedPcdGet32(PcdRaphaelNativeWatchdogHz);R->Seconds=FixedPcdGet32(PcdRaphaelNativeWatchdogSeconds);
 if(!R->Frequency||R->Seconds!=20||R->Frequency>MAX_UINT32/(R->Seconds+1))return EFI_INVALID_PARAMETER;
 R->SavedEnable=Read(Base,8);R->SavedBark=Read(Base,16);R->SavedBite=Read(Base,20);
 // Never replace a running firmware watchdog; its ownership is unknown.
 if(R->SavedEnable&1)return EFI_ACCESS_DENIED;
 Write(Base,8,0);Write(Base,16,(UINT32)(R->Frequency*R->Seconds));Write(Base,20,(UINT32)(R->Frequency*(R->Seconds+1)));
 R->Armed=1;Write(Base,8,1);Write(Base,4,1);
 R->ReadbackEnable=Read(Base,8);R->ReadbackBark=Read(Base,16);R->ReadbackBite=Read(Base,20);
 DEBUG((DEBUG_INFO,"NATIVE_WATCHDOG seconds=%lu hz=%lu requested=%lu/%lu readback=%lu/%lu/%lu saved=%lu/%lu/%lu\n",R->Seconds,R->Frequency,R->Frequency*R->Seconds,R->Frequency*(R->Seconds+1),R->ReadbackEnable,R->ReadbackBark,R->ReadbackBite,R->SavedEnable,R->SavedBark,R->SavedBite));
 if(R->ReadbackEnable!=1||R->ReadbackBark!=R->Frequency*R->Seconds||R->ReadbackBite!=R->Frequency*(R->Seconds+1)){
  RaphaelNativeWatchdogStop();return EFI_DEVICE_ERROR;
 }
 R->Status=2;return EFI_SUCCESS;
}
