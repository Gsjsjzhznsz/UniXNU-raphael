// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelIccProbe.h>
VOID RaphaelCollectIcc(CONST RAPHAEL_GIC_SNAPSHOT *G,RAPHAEL_ICC_SNAPSHOT *O,
 RAPHAEL_ICC_READ Read,VOID *C) {
 if(!O)return;
 for(UINTN I=0;I<sizeof(*O);++I)((UINT8 *)O)[I]=0;
 O->Version=1;O->Status=1;O->FailedSelector=MAX_UINT64;
 if(!G||!Read||G->Version!=1||G->Status!=4||!G->FrameCount||
   G->FrameCount>RAPHAEL_GIC_MAX_FRAMES||G->BootIndex>=G->FrameCount||
   (G->Frames[G->BootIndex].Typer>>32)!=G->Affinity)return;
 for(UINT32 I=0;I<RAPHAEL_ICC_REGISTER_COUNT;++I) {
  UINT64 Value=0;O->FailedSelector=I;++O->Attempted;
  if(!Read(I,&Value,&O->TrapEsr,&O->TrapElr,C)){O->Status=4;return;}
  O->Values[I]=Value;++O->Completed;
  if((I==RaphaelSysCurrentEl&&Value!=4)||
     (I==RaphaelSysDaif&&(Value&0x3c0)!=0x3c0)||
     (I==RaphaelSysMpidr&&Value!=G->Mpidr)){O->Status=2;return;}
  if(I==RaphaelSysSre&&!(Value&1)){O->Status=3;return;}
 }
 O->Status=5;O->FailedSelector=MAX_UINT64;
}
