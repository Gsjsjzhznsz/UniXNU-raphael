// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelGicEnableMap.h>
STATIC UINT32 At(RAPHAEL_GIC_ENABLE_MAP *O,RAPHAEL_GIC_READ32 R,VOID *C,UINT64 A){++O->ReadCount;return R(A,C);}
VOID RaphaelCollectGicEnableMap(CONST RAPHAEL_GIC_SNAPSHOT *G,RAPHAEL_GIC_ENABLE_MAP *O,
 RAPHAEL_GIC_READ32 Read,VOID *C){
 if(!O)return;
 for(UINTN N=0;N<sizeof(*O);++N)((UINT8 *)O)[N]=0;
 O->Version=1;O->Status=1;
 // Deliberately limited to the reviewed GICv3 standard INTID range. Reserved
 // TYPER[9:8]/[15:11] must be zero; no claim about extended-INTID revisions.
 if(!G||!Read||G->Version!=1||G->Status!=4||(G->Pidr2&0xf0)!=0x30||
    (G->Typer&0xfb00)||G->Typer>MAX_UINT32||!G->FrameCount||G->FrameCount>8||
    G->BootIndex>=G->FrameCount||!G->GicD||(G->GicD&0xffff)||G->GicDBytes<0x10000||
    G->GicD>MAX_UINT64-G->GicDBytes||!G->GicR||(G->GicR&0xffff)||G->GicRBytes<0x20000||
    G->GicR>MAX_UINT64-G->GicRBytes)return;
 if(G->GicD<G->GicR+G->GicRBytes&&G->GicR<G->GicD+G->GicDBytes)return;
 for(UINTN N=0;N<G->FrameCount;++N){UINT64 B=G->Frames[N].Base;
  if((B&0xffff)||B<G->GicR||B>G->GicR+G->GicRBytes-0x20000)return;
  for(UINTN J=0;J<N;++J)if(B==G->Frames[J].Base)return;
 }
 O->SpiWords=G->Typer&31;O->FrameCount=G->FrameCount;O->Status=2;
 O->DistributorBefore=At(O,Read,C,G->GicD);
 if(At(O,Read,C,G->GicD+4)!=G->Typer||O->DistributorBefore!=G->Ctlr)return;
 for(UINTN Pass=0;Pass<2;++Pass){
  for(UINTN N=0;N<O->SpiWords;++N){UINT32 V=At(O,Read,C,G->GicD+0x100+(N+1)*4);
   O->EnabledSpiOr|=V;if(!Pass)O->Spi[N]=V;else if(O->Spi[N]!=V)++O->ChangedWords;
  }
  for(UINTN N=0;N<O->FrameCount;++N){
   UINT32 V=At(O,Read,C,G->Frames[N].Base+0x10100),Ctl=At(O,Read,C,G->Frames[N].Base);
   O->EnabledLocalOr|=V;O->LpiEnabledOr|=Ctl&1;
   if(!Pass){O->Local[N]=V;O->LocalCtlr[N]=Ctl;}
   else{if(O->Local[N]!=V)++O->ChangedWords;if(O->LocalCtlr[N]!=Ctl)++O->ChangedWords;}
  }
 }
 O->DistributorAfter=At(O,Read,C,G->GicD);
 if(O->DistributorAfter!=O->DistributorBefore)++O->ChangedWords;
 O->Status=O->ChangedWords?4:3;
 O->AllObservedDisabled=O->Status==3&&!(O->DistributorBefore&0x80000003)&&
   (O->DistributorBefore&0x10)&&!O->EnabledSpiOr&&!O->EnabledLocalOr&&!O->LpiEnabledOr;
}
