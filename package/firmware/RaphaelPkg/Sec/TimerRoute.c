// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelTimerRoute.h>
STATIC UINT32 Mr(RAPHAEL_TIMER_ROUTE_RESULT *O,RAPHAEL_GIC_READ32 R,VOID *C,UINT64 A) {
 ++O->MmioReads;return R(A,C);
}
STATIC VOID Mw(RAPHAEL_TIMER_ROUTE_RESULT *O,RAPHAEL_PPI_WRITE32 W,VOID *C,UINT64 A,UINT32 V) {
 ++O->MmioWrites;W(A,V,C);
}
STATIC BOOLEAN Sr(RAPHAEL_TIMER_ROUTE_RESULT *O,RAPHAEL_ICC_READ R,VOID *C,UINT32 N,UINT64 *V) {
 ++O->SysReads;return R(N,V,&O->TrapEsr,&O->TrapElr,C);
}
STATIC BOOLEAN Sw(RAPHAEL_TIMER_ROUTE_RESULT *O,RAPHAEL_TIMER_WRITE W,VOID *C,UINT32 N,UINT64 V) {
 ++O->SysWrites;return W(N,V,&O->TrapEsr,&O->TrapElr,C);
}
STATIC BOOLEAN WaitRwp(RAPHAEL_TIMER_ROUTE_RESULT *O,RAPHAEL_GIC_READ32 M,
 RAPHAEL_ICC_READ R,VOID *C,UINT64 A,UINT32 Mask) {
 UINT64 Start,Now;
 if(!Sr(O,R,C,RAPHAEL_TIMER_COUNTER,&Start))return FALSE;
 for(UINTN N=0;N<1000000;++N) {
  ++O->RwpPolls;if(!(Mr(O,M,C,A)&Mask))return TRUE;
  if(!Sr(O,R,C,RAPHAEL_TIMER_COUNTER,&Now)||Now<Start||Now-Start>=O->Frequency/10)return FALSE;
 }
 return FALSE;
}
VOID RaphaelTestTimerRouteWithIrq(CONST VOID *F,CONST RAPHAEL_GIC_SNAPSHOT *G,
 CONST RAPHAEL_ICC_SNAPSHOT *I,CONST RAPHAEL_GIC_ENABLE_MAP *Map,RAPHAEL_TIMER_ROUTE_RESULT *O,
 RAPHAEL_GIC_READ32 M,RAPHAEL_PPI_WRITE32 W,RAPHAEL_ICC_READ R,RAPHAEL_TIMER_WRITE S,VOID *C,
 RAPHAEL_TIMER_IRQ_WINDOW Window,VOID *IrqResult) {
 UINT64 FreshCtl=0,FreshCval=0,Daif=0,Mask=0,Base=0,FreshIgrpen=0;
 BOOLEAN Restore=TRUE,Withdrawn=FALSE;
 if(!O)return;
 for(UINTN N=0;N<sizeof(*O);++N)((UINT8 *)O)[N]=0;
 O->Version=1;O->Status=1;
 if((Window&&!IrqResult)||!G||!I||!Map||!M||!W||!R||!S||G->Version!=1||G->Status!=4||
   !G->FrameCount||G->FrameCount>8||G->BootIndex>=G->FrameCount||
   (G->Ctlr!=0x10&&G->Ctlr!=0x50)||!G->GicD||G->GicDBytes<0x10000||
   !G->GicR||G->GicRBytes<0x20000||G->GicR>MAX_UINT64-G->GicRBytes||
   (G->GicD&0xffff)||G->GicD>MAX_UINT64-G->GicDBytes||(G->GicR&0xffff)||
   (G->Pidr2&0xf0)!=0x30||(G->Typer&0xfb00)||G->Typer>MAX_UINT32||Map->Version!=1||Map->Status!=3||!Map->AllObservedDisabled||Map->ChangedWords||
   Map->EnabledSpiOr||Map->EnabledLocalOr||Map->LpiEnabledOr||
   Map->DistributorBefore!=G->Ctlr||Map->DistributorAfter!=G->Ctlr||
   Map->SpiWords!=(G->Typer&31)||Map->FrameCount!=G->FrameCount||
   Map->ReadCount!=3+2*(Map->SpiWords+2*Map->FrameCount)||
   I->Version!=1||I->Status!=5||I->Attempted!=16||I->Completed!=16||I->FailedSelector!=MAX_UINT64||I->TrapEsr||I->TrapElr||
   I->Values[RaphaelSysCurrentEl]!=4||(I->Values[RaphaelSysDaif]&0x3c0)!=0x3c0||
   I->Values[RaphaelSysMpidr]!=G->Mpidr||!(I->Values[RaphaelSysSre]&1)||
   I->Values[RaphaelSysIgrpen1]||I->Values[RaphaelSysHppir1]!=1023||I->Values[RaphaelSysRpr]!=255||
   !I->Values[RaphaelSysPmr]||I->Values[RaphaelSysCntpCtl]>7||(I->Values[RaphaelSysCntpCtl]&1)||
   I->Values[RaphaelSysCntfrq]<1000||I->Values[RaphaelSysCntfrq]>1000000000)return;
 for(UINTN N=0;N<31;++N)if(Map->Spi[N])return;
 for(UINTN N=0;N<8;++N)if(Map->Local[N]||(Map->LocalCtlr[N]&1))return;
 Base=G->Frames[G->BootIndex].Base;
 if((Base&0xffff)||Base<G->GicR||Base>G->GicR+G->GicRBytes-0x20000||
   G->Frames[G->BootIndex].Typer>>32!=G->Affinity||!RaphaelResolvePhysicalPpi(F,I->Values[RaphaelSysCntfrq],&O->Intid,&O->Flags))return;
 Mask=1ULL<<O->Intid;O->SgiBase=Base+0x10000;O->Frequency=I->Values[RaphaelSysCntfrq];
 O->OriginalCtl=I->Values[RaphaelSysCntpCtl];O->OriginalCval=I->Values[RaphaelSysCntpCval];
 O->Status=2;O->Reason=1;
 if(!Sr(O,R,C,RAPHAEL_ROUTE_DAIF,&Daif)||!Sr(O,R,C,RAPHAEL_ROUTE_IGRPEN1,&FreshIgrpen)||
    !Sr(O,R,C,RAPHAEL_ROUTE_HPPIR1,&O->HppirBefore)||!Sr(O,R,C,RAPHAEL_TIMER_CTL,&FreshCtl)||
    !Sr(O,R,C,RAPHAEL_TIMER_CVAL,&FreshCval))return;
 O->DaifBefore=Daif;O->OriginalIgrpen=FreshIgrpen;O->OriginalDist=Mr(O,M,C,G->GicD);
 O->EnabledBefore=Mr(O,M,C,O->SgiBase+0x100);
 O->PendingBefore=Mr(O,M,C,O->SgiBase+0x200);O->ActiveBefore=Mr(O,M,C,O->SgiBase+0x300);
 if((Daif&0x3c0)!=0x3c0||FreshIgrpen||O->HppirBefore!=1023||FreshCtl>7||
    ((FreshCtl^O->OriginalCtl)&3)||FreshCval!=O->OriginalCval||O->OriginalDist!=G->Ctlr||O->EnabledBefore||
    (O->PendingBefore&Mask)||O->ActiveBefore||(Mr(O,M,C,Base)&8)||(Mr(O,M,C,Base+0x14)&6))return;
 if(!Sr(O,R,C,RAPHAEL_TIMER_COUNTER,&O->StartCounter)||O->StartCounter>MAX_UINT64-O->Frequency/10)return;
 O->Deadline=O->StartCounter+O->Frequency/100;O->Status=3;O->Reason=2;
 // CPU DAIF stays masked throughout. Only this local PPI becomes enabled.
 if(!Sw(O,S,C,RAPHAEL_TIMER_CVAL,O->Deadline))goto Restore;
 Mw(O,W,C,O->SgiBase+0x100,(UINT32)Mask);
 O->EnabledDuring=Mr(O,M,C,O->SgiBase+0x100);
 if(O->EnabledDuring!=Mask)goto Restore;
 Mw(O,W,C,G->GicD,(UINT32)(O->OriginalDist|2));
 O->DistDuring=Mr(O,M,C,G->GicD);
 if(O->DistDuring!=(O->OriginalDist|2))goto Restore;
 if(!Sw(O,S,C,RAPHAEL_ROUTE_IGRPEN1,1)||!Sr(O,R,C,RAPHAEL_ROUTE_IGRPEN1,&O->IgrpenDuring)||O->IgrpenDuring!=1)goto Restore;
 if(!Sw(O,S,C,RAPHAEL_TIMER_CTL,1))goto Restore;
 O->Status=4;O->Reason=3;
 for(UINTN N=0;N<1000000;++N) {
  ++O->Polls;
  if(!Sr(O,R,C,RAPHAEL_TIMER_CTL,&O->CtlDuring)||!Sr(O,R,C,RAPHAEL_ROUTE_HPPIR1,&O->HppirDuring)||
     !Sr(O,R,C,RAPHAEL_TIMER_COUNTER,&O->EndCounter)){O->Status=3;break;}
  if(O->CtlDuring>7||(O->CtlDuring&3)!=1||O->EndCounter<O->StartCounter||
     (O->HppirDuring!=1023&&O->HppirDuring!=O->Intid)){O->Status=3;break;}
  if(O->HppirDuring==O->Intid) {
   // CTL was sampled before HPPIR; expiration can occur between the reads.
   // Confirm the source and counter after observing the target pending ID.
   if(!Sr(O,R,C,RAPHAEL_TIMER_CTL,&O->CtlDuring)||!Sr(O,R,C,RAPHAEL_TIMER_COUNTER,&O->EndCounter)){O->Status=3;break;}
   O->PendingDuring=Mr(O,M,C,O->SgiBase+0x200);
   if(O->CtlDuring==5&&O->EndCounter>=O->Deadline&&O->EndCounter-O->StartCounter<=O->Frequency/10&&(O->PendingDuring&Mask))O->Status=6;
   else O->Status=3;
   break;
  }
  if(O->EndCounter-O->StartCounter>=O->Frequency/10)break;
 }
 if(O->Status==6&&Window&&!Window(IrqResult,O->Intid,O->Frequency)){O->Status=3;O->Reason=4;}
Restore:
 // Withdraw the level source first; disable both forwarding gates and the PPI.
 // Every restoring operation is attempted even after an earlier access failed.
 if(!Sw(O,S,C,RAPHAEL_TIMER_CTL,2))Restore=FALSE;
 if(!Sw(O,S,C,RAPHAEL_ROUTE_IGRPEN1,O->OriginalIgrpen))Restore=FALSE;
 Mw(O,W,C,G->GicD,(UINT32)O->OriginalDist);
 if(!WaitRwp(O,M,R,C,G->GicD,0x80000000))Restore=FALSE;
 Mw(O,W,C,O->SgiBase+0x180,(UINT32)Mask);
 if(!WaitRwp(O,M,R,C,Base,8))Restore=FALSE;
 if(!Sw(O,S,C,RAPHAEL_TIMER_CVAL,O->OriginalCval))Restore=FALSE;
 if(!Sw(O,S,C,RAPHAEL_TIMER_CTL,O->OriginalCtl&3))Restore=FALSE;
 // Source withdrawal is asynchronous. Observe pending return without ACK/clear.
 UINT64 Start=0,Now=0;
 if(!Sr(O,R,C,RAPHAEL_TIMER_COUNTER,&Start))Restore=FALSE;
 else for(UINTN N=0;N<1000000;++N) {
  ++O->ClearPolls;O->PendingAfter=Mr(O,M,C,O->SgiBase+0x200);
  if(!Sr(O,R,C,RAPHAEL_ROUTE_HPPIR1,&O->HppirAfter)||!Sr(O,R,C,RAPHAEL_TIMER_COUNTER,&Now)){Restore=FALSE;break;}
  if(!((O->PendingAfter^O->PendingBefore)&Mask)&&O->HppirAfter==O->HppirBefore){Withdrawn=TRUE;break;}
  if(Now<Start||Now-Start>=O->Frequency/10)break;
 }
 O->EnabledAfter=Mr(O,M,C,O->SgiBase+0x100);O->RestoredDist=Mr(O,M,C,G->GicD);O->ActiveAfter=Mr(O,M,C,O->SgiBase+0x300);
 if(!Sr(O,R,C,RAPHAEL_ROUTE_IGRPEN1,&O->RestoredIgrpen)||!Sr(O,R,C,RAPHAEL_TIMER_CTL,&O->RestoredCtl)||
    !Sr(O,R,C,RAPHAEL_TIMER_CVAL,&O->RestoredCval)||!Sr(O,R,C,RAPHAEL_ROUTE_DAIF,&Daif))Restore=FALSE;
 O->DaifAfter=Daif;
 O->RestoreOk=Restore&&Withdrawn&&O->EnabledAfter==O->EnabledBefore&&O->RestoredDist==O->OriginalDist&&
   O->ActiveAfter==O->ActiveBefore&&O->RestoredIgrpen==O->OriginalIgrpen&&O->RestoredCtl<=7&&
   !((O->RestoredCtl^O->OriginalCtl)&3)&&O->RestoredCval==O->OriginalCval&&(Daif&0x3c0)==0x3c0;
 if(!O->RestoreOk)O->Status=5;
 if(O->Status==6)O->Reason=0;
}

VOID RaphaelTestTimerRoute(CONST VOID *F,CONST RAPHAEL_GIC_SNAPSHOT *G,CONST RAPHAEL_ICC_SNAPSHOT *I,
 CONST RAPHAEL_GIC_ENABLE_MAP *Map,RAPHAEL_TIMER_ROUTE_RESULT *O,RAPHAEL_GIC_READ32 M,
 RAPHAEL_PPI_WRITE32 W,RAPHAEL_ICC_READ R,RAPHAEL_TIMER_WRITE S,VOID *C) {
 RaphaelTestTimerRouteWithIrq(F,G,I,Map,O,M,W,R,S,C,NULL,NULL);
}
