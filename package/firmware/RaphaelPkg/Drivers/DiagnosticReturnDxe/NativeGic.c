// SPDX-License-Identifier: BSD-2-Clause-Patent
// Exact boot-CPU recovery for the independently implemented GICv3 driver.
// This path does not claim complete Secure GIC ownership or change any SPI.
#include <RaphaelDiagnostic.h>
#include <Library/BaseMemoryLib.h>
#include <Library/BaseLib.h>
#include <RaphaelPhysicalTimer.h>
#include <Library/HobLib.h>
STATIC UINT32 Read32(UINT64 P){return *(volatile UINT32 *)(UINTN)P;}
STATIC VOID Write32(UINT64 P,UINT32 V){*(volatile UINT32 *)(UINTN)P=V;__asm__ volatile("dsb sy":::"memory");}
STATIC BOOLEAN Wait(UINT64 P,UINT32 Mask){
 UINT64 Begin,Now;__asm__ volatile("mrs %0,cntpct_el0":"=r"(Begin));
 for(UINTN I=0;I<1000000;++I){if(!(Read32(P)&Mask))return TRUE;__asm__ volatile("mrs %0,cntpct_el0":"=r"(Now));if(Now-Begin>RaphaelDiagnostic()->Cntfrq/10)return FALSE;}return FALSE;
}
STATIC VOID Snapshot(RAPHAEL_NATIVE_GIC_RESULT *S,UINT64 *V){
 UINT64 B=S->Rdist+0x10000;V[0]=Read32(S->Dist);V[1]=Read32(S->Rdist+0x14);
 V[2]=Read32(B+0x80);V[3]=Read32(B+0xd00);V[4]=Read32(B+0x100);
 V[5]=Read32(B+0x200);V[6]=Read32(B+0x300);V[7]=Read32(B+0xc04);
 V[8]=Read32(B+0x400);V[9]=Read32(B+0x400+(S->TimerId/4)*4);
 __asm__ volatile("mrs %0,icc_sre_el1":"=r"(V[10]));
 __asm__ volatile("mrs %0,icc_ctlr_el1":"=r"(V[11]));
 __asm__ volatile("mrs %0,icc_pmr_el1":"=r"(V[12]));
 __asm__ volatile("mrs %0,icc_bpr1_el1":"=r"(V[13]));
 __asm__ volatile("mrs %0,icc_igrpen1_el1":"=r"(V[14]));
 __asm__ volatile("mrs %0,icc_hppir1_el1":"=r"(V[15]));
}
EFI_STATUS RaphaelSaveNativeGic(RAPHAEL_NATIVE_GIC_RESULT *S){
 RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();ZeroMem(S,sizeof(*S));S->Version=1;S->Status=1;
 UINT64 Frames=0,Stride=0;
 if(FixedPcdGetBool(PcdRaphaelQemuArchTest)){
  if(D->QemuArch.Version!=1||D->QemuArch.GicDBytes<0x10000||D->QemuArch.GicRBytes<0x20000)return EFI_COMPROMISED_DATA;
  S->Dist=D->QemuArch.GicD;S->Rdist=D->QemuArch.GicR;Frames=D->QemuArch.GicRBytes;S->TimerId=D->QemuArch.PhysicalInt;
 }else{
  if(D->Gic.Status!=4||D->Gic.BootIndex>=D->Gic.FrameCount||D->Gic.GicDBytes<0x10000)return EFI_COMPROMISED_DATA;
  S->Dist=D->Gic.GicD;S->Rdist=D->Gic.Frames[D->Gic.BootIndex].Base;Frames=0x20000;Stride=D->Gic.Stride;
  // Resource ID is the independently qualified physical TimerArch input.
  VOID *H=GetFirstGuidHob(&gRaphaelPhysicalTimerHobGuid);if(!H)return EFI_COMPROMISED_DATA;
  RAPHAEL_PHYSICAL_TIMER_STATE *T=*(VOID **)GET_GUID_HOB_DATA(H);
  if(!T||T->Result.Status!=4||T->Result.GicD!=S->Dist||T->Result.RdBase!=S->Rdist)return EFI_COMPROMISED_DATA;
  S->TimerId=T->Result.Intid;
 }
 if(S->TimerId<16||S->TimerId>31)return EFI_COMPROMISED_DATA;
 UINT64 Affinity=(D->Mpidr&0xffffff)|((D->Mpidr>>8)&0xff000000),Base=S->Rdist;
 BOOLEAN Found=FALSE;
 for(UINT64 Offset=0;Offset<=Frames-0x20000;){
  UINT64 Typer=*(volatile UINT64 *)(UINTN)(Base+Offset+8);
  if((Typer>>32)==Affinity){S->Rdist=Base+Offset;Found=TRUE;break;}
  if(Typer&16)break;UINT64 Step=Stride?Stride:((Typer&2)?0x40000:0x20000);if(Step>Frames-Offset)break;Offset+=Step;
 }
 if(!Found||((Read32(S->Dist+0xffe8)>>4)&15)!=3)return EFI_COMPROMISED_DATA;
 Snapshot(S,S->Saved);
 // Running a handler before recovery would require additional active-state
 // ownership. A later thread checkpoint also requires no active interrupt.
 if(S->Saved[6]||!(S->Saved[10]&1))return EFI_COMPROMISED_DATA;
 return EFI_SUCCESS;
}
BOOLEAN RaphaelRestoreNativeGic(RAPHAEL_NATIVE_GIC_RESULT *S){
 if(S->Version!=1||S->Status!=1)return FALSE;Snapshot(S,S->Observed);
 for(UINTN I=0;I<RAPHAEL_NATIVE_GIC_WORDS;++I)if(S->Saved[I]!=S->Observed[I])++S->ChangedWords;
 UINT64 B=S->Rdist+0x10000,Z=0;UINT32 Owned=1U|(1U<<S->TimerId);
 __asm__ volatile("msr icc_igrpen1_el1,%0; isb"::"r"(Z):"memory");
 Write32(S->Dist,(UINT32)S->Observed[0]&~2U);BOOLEAN Ok=Wait(S->Dist,1U<<31);
 Write32(B+0x180,Owned);Ok=Wait(S->Rdist,8)&&Ok;
 // Never acknowledge or forcibly deactivate an interrupt that we did not own.
 Ok=Read32(B+0x300)==S->Saved[6]&&Ok;
 // DS=0 group registers and WAKER are Secure RAZ/WI to this NS caller.
 if(S->Saved[0]&(1U<<6))Write32(B+0x80,(UINT32)S->Saved[2]);
 Write32(B+0xc04,(UINT32)S->Saved[7]);Write32(B+0x400,(UINT32)S->Saved[8]);Write32(B+0x400+(S->TimerId/4)*4,(UINT32)S->Saved[9]);
 Write32(B+0x280,Owned&~(UINT32)S->Saved[5]);Write32(B+0x200,Owned&(UINT32)S->Saved[5]);
 Write32(B+0x100,Owned&(UINT32)S->Saved[4]);Ok=Wait(S->Rdist,8)&&Ok;
 if(S->Saved[0]&(1U<<6))Write32(S->Rdist+0x14,(UINT32)S->Saved[1]&2U);
 __asm__ volatile("msr icc_ctlr_el1,%0; msr icc_pmr_el1,%1; msr icc_bpr1_el1,%2; isb"::"r"(S->Saved[11]),"r"(S->Saved[12]),"r"(S->Saved[13]):"memory");
 Write32(S->Dist,(UINT32)S->Saved[0]);Ok=Wait(S->Dist,1U<<31)&&Ok;
 __asm__ volatile("msr icc_igrpen1_el1,%0; msr icc_sre_el1,%1; dsb sy; isb"::"r"(S->Saved[14]),"r"(S->Saved[10]):"memory");
 Snapshot(S,S->Restored);
 for(UINTN I=0;I<15;++I)if(S->Restored[I]!=S->Saved[I])Ok=FALSE;
 S->RestoreOk=Ok;S->Status=Ok?3:2;return Ok;
}
