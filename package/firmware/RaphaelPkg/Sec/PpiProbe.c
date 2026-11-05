// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelPpiProbe.h>
#include <Library/FdtLib.h>
STATIC UINT32 Be32(CONST VOID *P){CONST UINT8 *B=P;return ((UINT32)B[0]<<24)|((UINT32)B[1]<<16)|((UINT32)B[2]<<8)|B[3];}
STATIC BOOLEAN Eq(CONST CHAR8 *P,INT32 N,CONST CHAR8 *S){INT32 I=0;while(I<N&&S[I]&&P[I]==S[I])++I;return I==N&&!S[I];}
STATIC INT32 Compatible(CONST VOID *F,INT32 N,CONST CHAR8 *S){
 INT32 L;CONST CHAR8 *P=FdtGetProp(F,N,"compatible",&L);BOOLEAN Found=FALSE;
 if(!P)return 0;
 for(INT32 I=0;I<L;){INT32 J=I;while(J<L&&P[J])++J;if(Eq(P+I,J-I,S))Found=TRUE;if(J==L)return Found?-1:0;I=J+1;}
 return Found?1:0;
}
STATIC BOOLEAN Enabled(CONST VOID *F,INT32 N){INT32 L;CONST CHAR8 *P=FdtGetProp(F,N,"status",&L);return !P||(L==5&&Eq(P,4,"okay")&&!P[4])||(L==3&&Eq(P,2,"ok")&&!P[2]);}
STATIC INT32 HandleNode(CONST VOID *F,UINT32 H){
 INT32 N=-1,D=-1,Found=-1,L;CONST UINT8 *P,*A;
 if(!H||H==MAX_UINT32)return -1;
 while((N=FdtNextNode(F,N,&D))>=0&&D>=0){
  P=FdtGetProp(F,N,"phandle",&L);BOOLEAN Match=P&&L==4&&Be32(P)==H;
  A=FdtGetProp(F,N,"linux,phandle",&L);Match=Match||(A&&L==4&&Be32(A)==H);
  if(!Match)continue;
  if(Found>=0)return -1;
  if(P){P=FdtGetProp(F,N,"phandle",&L);if(L!=4||Be32(P)!=H)return -1;}
  if(A){A=FdtGetProp(F,N,"linux,phandle",&L);if(L!=4||Be32(A)!=H)return -1;}
  Found=N;
 }
 return Found;
}
STATIC INT32 IrqParent(CONST VOID *F,INT32 N){
 for(UINTN Depth=0;N>=0&&Depth<64;++Depth){INT32 L;CONST UINT8 *P=FdtGetProp(F,N,"interrupt-parent",&L);
  if(P)return L==4?HandleNode(F,Be32(P)):-1;
  N=FdtParentOffset(F,N);}
 return -1;
}
BOOLEAN RaphaelResolvePhysicalPpi(CONST VOID *F,UINT64 Frequency,UINT64 *Id,UINT64 *Flags){
 if(!F||FdtCheckHeader(F))return FALSE;
 INT32 Phone=Compatible(F,0,"qcom,sm8150"),Qemu=Compatible(F,0,"linux,dummy-virt");
 if(Phone<0||Qemu<0||(!Phone&&!Qemu)||(Phone&&Qemu))return FALSE;
 INT32 N=-1,D=-1,Timer=-1,Gic=-1,L;CONST UINT8 *P;
 while((N=FdtNextNode(F,N,&D))>=0&&D>=0){
  INT32 T=Compatible(F,N,"arm,armv8-timer"),G=Compatible(F,N,"arm,gic-v3");
  if(T<0||G<0)return FALSE;
  if(T){if(Timer>=0||!Enabled(F,N))return FALSE;Timer=N;}
  if(G){if(Gic>=0||!Enabled(F,N))return FALSE;Gic=N;}
 }
 if(Timer<0||Gic<0||FdtGetProp(F,Timer,"interrupts-extended",&L))return FALSE;
 P=FdtGetProp(F,Timer,"clock-frequency",&L);if(P?(L!=4||Be32(P)!=Frequency):Phone)return FALSE;
 P=FdtGetProp(F,Timer,"interrupts",&L);if(!P||L!=48)return FALSE;
 UINT32 Ids[4];
 for(UINTN J=0;J<4;++J){UINT32 Kind=Be32(P+J*12),Off=Be32(P+J*12+4),F=Be32(P+J*12+8);
  if(Kind!=1||Off>=16||((F&15)!=4&&(F&15)!=8)||(F&~0xff0fU))return FALSE;
  Ids[J]=16+Off;for(UINTN K=0;K<J;++K)if(Ids[K]==Ids[J])return FALSE;
 }
 *Id=Ids[1];*Flags=Be32(P+20);
 INT32 Provider=IrqParent(F,Timer);
 if(Phone){
  if(Provider<0||Compatible(F,Provider,"qcom,pdc-sm8150")!=1||!Enabled(F,Provider))return FALSE;
  P=FdtGetProp(F,Provider,"#interrupt-cells",&L);if(!P||L!=4||Be32(P)!=3)return FALSE;
  if(!FdtGetProp(F,Provider,"interrupt-controller",&L)||L)return FALSE;
  INT32 Parent=IrqParent(F,Provider);if(Parent==Provider)return FALSE;Provider=Parent;
 }
 if(Provider!=Gic)return FALSE;
 P=FdtGetProp(F,Gic,"#interrupt-cells",&L);if(!P||L!=4||Be32(P)!=3)return FALSE;
 return FdtGetProp(F,Gic,"interrupt-controller",&L)!=NULL&&L==0;
}
STATIC UINT32 ReadAt(RAPHAEL_PPI_RESULT *O,RAPHAEL_GIC_READ32 R,VOID *C,UINT64 A){++O->ReadCount;return R(A,C);}
VOID RaphaelProbePhysicalPpi(CONST VOID *F,CONST RAPHAEL_GIC_SNAPSHOT *G,CONST RAPHAEL_ICC_SNAPSHOT *I,
 RAPHAEL_PPI_RESULT *O,RAPHAEL_GIC_READ32 Read,RAPHAEL_PPI_WRITE32 Write,RAPHAEL_PPI_COUNTER Counter,VOID *C){
 if(!O)return;
 for(UINTN N=0;N<sizeof(*O);++N)((UINT8 *)O)[N]=0;
 O->Version=1;O->Status=1;
 if(!G||!I||!Read||!Write||!Counter||G->Version!=1||G->Status!=4||!G->FrameCount||G->FrameCount>8||G->BootIndex>=G->FrameCount||
    I->Version!=1||I->Status!=5||I->Attempted!=16||I->Completed!=16||I->FailedSelector!=MAX_UINT64||I->TrapEsr||I->TrapElr||
    I->Values[RaphaelSysMpidr]!=G->Mpidr||I->Values[RaphaelSysCurrentEl]!=4||(I->Values[RaphaelSysDaif]&0x3c0)!=0x3c0||
    !(I->Values[RaphaelSysSre]&1)||I->Values[RaphaelSysIgrpen1]||(I->Values[RaphaelSysCntpCtl]&1)||
    I->Values[RaphaelSysCntpCtl]>7||I->Values[RaphaelSysCntfrq]<1000||I->Values[RaphaelSysCntfrq]>1000000000||
    !G->GicD||G->GicDBytes<0x10000||!G->GicR||G->GicRBytes<0x20000||G->GicR>MAX_UINT64-G->GicRBytes)return;
 UINT64 Base=G->Frames[G->BootIndex].Base;
 if((Base&0xffff)||Base<G->GicR||Base>G->GicR+G->GicRBytes-0x20000||(G->Frames[G->BootIndex].Typer>>32)!=G->Affinity)return;
 O->Status=2;O->Reason=1;
 if(!RaphaelResolvePhysicalPpi(F,I->Values[RaphaelSysCntfrq],&O->Intid,&O->Flags))return;
 O->SgiBase=Base+0x10000;O->Mask=1ULL<<O->Intid;O->Reason=2;
 O->CtlrBefore=ReadAt(O,Read,C,G->GicD);
 O->EnabledBefore=ReadAt(O,Read,C,O->SgiBase+0x100);
 O->PendingBefore=ReadAt(O,Read,C,O->SgiBase+0x200);
 O->ActiveBefore=ReadAt(O,Read,C,O->SgiBase+0x300);
 UINT32 RdCtlr=ReadAt(O,Read,C,Base);
 if(O->CtlrBefore!=G->Ctlr||(O->CtlrBefore&0x80000003)||!(O->CtlrBefore&0x10)||
    O->EnabledBefore!=G->Sgi[1]||((O->EnabledBefore|O->PendingBefore|O->ActiveBefore)&O->Mask)||(RdCtlr&8))return;
 // Write-one set/clear of exactly the dynamically selected PPI. No RMW.
 ++O->WriteCount;Write(O->SgiBase+0x100,(UINT32)O->Mask,C);
 O->EnabledDuring=ReadAt(O,Read,C,O->SgiBase+0x100);
 O->Status=O->EnabledDuring==(O->EnabledBefore|O->Mask)?6:O->EnabledDuring==O->EnabledBefore?3:4;
 ++O->WriteCount;Write(O->SgiBase+0x180,(UINT32)O->Mask,C);
 UINT64 Start=Counter(C);BOOLEAN Done=FALSE;
 for(UINTN N=0;N<1000000;++N){
  ++O->RwpPolls;if(!(ReadAt(O,Read,C,Base)&8)){Done=TRUE;break;}
  UINT64 Now=Counter(C);if(Now<Start||Now-Start>=I->Values[RaphaelSysCntfrq]/10)break;
 }
 O->EnabledAfter=ReadAt(O,Read,C,O->SgiBase+0x100);O->CtlrAfter=ReadAt(O,Read,C,G->GicD);
 O->PendingAfter=ReadAt(O,Read,C,O->SgiBase+0x200);O->ActiveAfter=ReadAt(O,Read,C,O->SgiBase+0x300);
 O->RestoreOk=Done&&O->EnabledAfter==O->EnabledBefore&&O->CtlrAfter==O->CtlrBefore&&
  !((O->PendingAfter^O->PendingBefore)&O->Mask)&&!((O->ActiveAfter^O->ActiveBefore)&O->Mask);
 if(!O->RestoreOk)O->Status=5;
 O->Reason=0;
}
