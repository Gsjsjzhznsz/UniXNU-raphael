// SPDX-License-Identifier: BSD-2-Clause-Patent
// Verify this entry's sampled route before advertising a BGR-reserved GOP.
// Register offsets/bit meanings: pinned MiCode sde_hw_ctl/lm/intf/catalog.
#include <RaphaelFramebuffer.h>
#include <Library/FdtLib.h>
STATIC UINT32 Be32(CONST VOID *P) {CONST UINT8 *B=P;return (UINT32)B[0]<<24|(UINT32)B[1]<<16|(UINT32)B[2]<<8|B[3];}
STATIC BOOLEAN Get(CONST RAPHAEL_DISPLAY_SNAPSHOT *S,UINT64 A,UINT32 *V) {
  *V=0; UINTN N=0;for(UINTN I=0;I<S->Count;++I)if(S->Samples[I][0]==A){*V=(UINT32)S->Samples[I][1];++N;}return N==1;
}
STATIC CONST UINT32 *List(CONST VOID *F,INT32 N,CONST CHAR8 *K,UINT32 Max,UINT32 *Count) {
  INT32 L;CONST UINT32 *P=FdtGetProp(F,N,K,&L);
  if(!P||L<=0||L%4||(UINT32)L/4>Max)return NULL;
  *Count=(UINT32)L/4;return P;
}
#define READ(A,V) do{if(!Get(S,(A),&(V)))return FALSE;}while(0)
BOOLEAN RaphaelSplashRouteReady(CONST VOID *F,CONST RAPHAEL_DISPLAY_SNAPSHOT *S,
  CONST RAPHAEL_PIXEL_SNAPSHOT *P) {
  if(!F||!S||!P||P->Status!=6||S->Version!=4||S->Status!=RaphaelSmmuCollected||S->Count>RAPHAEL_DISPLAY_MAX_SAMPLES)return FALSE;
  INT32 N=FdtNodeOffsetByCompatible(F,-1,"qcom,sde-kms"),L;
  CONST VOID *Reg=FdtGetProp(F,N,"reg",&L);if(!Reg||L<8)return FALSE;
  UINT64 Base=Be32(Reg);UINT32 Nc=0,Nm=0,Ni=0,Np=0,Nb=0;
  CONST UINT32 *C=List(F,N,"qcom,sde-ctl-off",6,&Nc),*M=List(F,N,"qcom,sde-mixer-off",6,&Nm),
    *I=List(F,N,"qcom,sde-intf-off",4,&Ni),*Q=List(F,N,"qcom,sde-pp-off",6,&Np),
    *B=List(F,N,"qcom,sde-mixer-blend-op-off",11,&Nb);
  if(!C||!M||!I||!Q||!B)return FALSE;
  UINT32 Routes=0,ActiveCt=0,ChosenCt=0,ChosenLm=0,Stage=0,Active=0,V,Top;
  for(UINT32 Ct=0;Ct<Nc;++Ct) {
    UINT64 At=Base+Be32(C+Ct);READ(At+0xf4,V);
    if(V) {++ActiveCt;Active=V;ChosenCt=Ct;READ(At+0x14,Top);if(!(Top&(1U<<17)))return FALSE;}
    for(UINT32 Lm=0;Lm<Nm;++Lm) {
      UINT32 Layer,Ext,Rect1;
      READ(At+(Lm==5?0x24:Lm*4),Layer);READ(At+0x40+Lm*4,Ext);READ(At+0xa0+Lm*4,Rect1);
      UINT32 Code=(Layer&7)|((Ext&1)<<3);
      if(Rect1&15)return FALSE;
      if(Code) {++Routes;ChosenLm=Lm;Stage=Code; if(!V||(V&(V-1)))return FALSE;}
    }
  }
  if(Routes!=1||ActiveCt!=1||!Active||(Active&(Active-1))||Stage<2||Stage-2>=Nb)return FALSE;
  // The unique VIG0 route must belong to the active CTL.
  UINT64 Ct=Base+Be32(C+ChosenCt);UINT32 Layer,Ext;
  READ(Ct+(ChosenLm==5?0x24:ChosenLm*4),Layer);READ(Ct+0x40+ChosenLm*4,Ext);
  if(((Layer&7)|((Ext&1)<<3))!=Stage)return FALSE;
  UINT32 Intf=0;while((Active>>Intf)!=1)++Intf;
  if(Intf>=Ni)return FALSE;
  CONST CHAR8 *Types=FdtGetProp(F,N,"qcom,sde-intf-type",&L);if(!Types||L<=0)return FALSE;
  INT32 Pos=0;
  for(UINT32 J=0;J<Intf;++J){while(Pos<L&&Types[Pos])++Pos;if(++Pos>=L)return FALSE;}
  if(Pos+4>L||Types[Pos]!='d'||Types[Pos+1]!='s'||Types[Pos+2]!='i'||Types[Pos+3])return FALSE;
  UINT64 Lm=Base+Be32(M+ChosenLm),Int=Base+Be32(I+Intf);
  READ(Lm+4,V);if((V&65535)!=P->Width||(V>>16)!=P->Height)return FALSE;
  UINT32 Op,Alpha;UINT64 Blend=Lm+Be32(B+Stage-2);READ(Blend,Op);READ(Blend+4,Alpha);
  if(Op&~(3U|4U|(3U<<8)|(1U<<10)))return FALSE;
  UINT32 Fg=Op&3,Bg=(Op>>8)&3;if(Fg>=2||Bg>=2)return FALSE;
  Fg=Fg?(Alpha&255):((Alpha>>16)&255);Bg=Bg?(Alpha&255):((Alpha>>16)&255);
  if(Op&4)Fg=255-Fg;
  if(Op&(1U<<10))Bg=255-Bg;
  if(Fg!=255||Bg)return FALSE;
  READ(Int+0x25c,V);V&=15;if(V>=Np||V!=ChosenLm)return FALSE;
  UINT32 Dsc;READ(Base+Be32(Q+V)+0xa0,Dsc);if(Dsc)return FALSE;
  READ(Int+0x284,V);if(V!=1)return FALSE;
  READ(Int+0x2b4,V);if(!(V&(1U<<31))||!(V&65535))return FALSE;
  return P->InterfaceBase==Int;
}
