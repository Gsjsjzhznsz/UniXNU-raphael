// SPDX-License-Identifier: BSD-2-Clause-Patent
// Read-only CPU memory thumbnail and interface counters. No write callback.
#include <RaphaelPixelProbe.h>
#include <Library/FdtLib.h>

STATIC UINT32 Be32 (CONST VOID *P) {
  CONST UINT8 *B=P; return ((UINT32)B[0]<<24)|((UINT32)B[1]<<16)|((UINT32)B[2]<<8)|B[3];
}
STATIC BOOLEAN Prop (CONST VOID *F, INT32 N, CONST CHAR8 *K, UINT32 *V) {
  INT32 L; CONST VOID *P=FdtGetProp(F,N,K,&L);
  if (!P || L!=4) return FALSE;
  *V=Be32(P); return TRUE;
}
STATIC BOOLEAN Value (CONST RAPHAEL_DISPLAY_SNAPSHOT *S, UINT64 A, UINT32 *V) {
  UINT32 Matches=0;
  *V=0;
  for (UINTN I=0; I<S->Count; ++I) if (S->Samples[I][0]==A) {
    *V=(UINT32)S->Samples[I][1]; ++Matches;
  }
  return Matches==1;
}
#define GET(A,V) do { if (!Value(S,(A),&(V))) return; } while (0)
VOID RaphaelCollectPixels (CONST VOID *F, CONST RAPHAEL_DISPLAY_SNAPSHOT *S,
  RAPHAEL_PIXEL_SNAPSHOT *O, RAPHAEL_DISPLAY_READ32 Read32,
  RAPHAEL_PIXEL_COUNTER Counter, UINT32 Frequency, VOID *Context) {
  INT32 Mdp, Smmu, Node, Len; CONST UINT8 *P;
  UINT32 MdpBase, Pipe, V, W, H, Stride, Address, Size, Handle, Sid, Mask;
  UINT32 SmmuBase, SmmuSize, Id0, Id1, Cr0, Page, Cbar, Sctlr, Active=0, Intf=0;
  for (UINTN I=0; I<sizeof(*O); ++I) ((UINT8 *)O)[I]=0;
  O->Version=1; O->Status=1;
  if (S->Version!=4 || S->Status!=RaphaelSmmuCollected || S->Count>RAPHAEL_DISPLAY_MAX_SAMPLES) return;
  O->Status=2;
  Mdp=FdtNodeOffsetByCompatible(F,-1,"qcom,sde-kms");
  P=FdtGetProp(F,Mdp,"reg",&Len); if (!P || Len<8) return; MdpBase=Be32(P);
  P=FdtGetProp(F,Mdp,"qcom,sde-sspp-off",&Len); if (!P || Len<4 || Len%4) return;
  Pipe=MdpBase+Be32(P);
  for (INT32 I=1; I<Len/4; ++I) {
    UINT32 At=MdpBase+Be32(P+I*4);
    GET(At,V); if (V) return; GET(At+0xc,V); if(V) return; GET(At+0x14,V); if(V) return;
  }
  GET(Pipe,W); H=W>>16; W&=65535;
  GET(Pipe+0xc,V); if (V!=((H<<16)|W)) return;
  GET(Pipe+8,V); if(V) return; GET(Pipe+0x10,V); if(V) return;
  GET(Pipe+0x14,Address); GET(Pipe+0x24,Stride);
  if (Stride>>16) return; // this linear interleaved format uses one plane
  GET(Pipe+0x28,V); if(V) return;
  for (UINT32 I=0; I<3; ++I) { GET(Pipe+0x18+I*4,V); if(V) return; }
  GET(Pipe+0x30,V); if(V!=0x237ff) return;
  GET(Pipe+0x34,V); if(V!=0x03020001) return;
  GET(Pipe+0x38,V); if(V!=0x80000000) return;
  GET(Pipe+0x70,V); if(V) return; GET(Pipe+0x170,V); if(V) return;
  if (W<64 || H<64 || W>4096 || H>4096 || Stride<W*4 || (Stride&3) || (Address&3)) return;
  UINT64 Extent=(UINT64)Stride*H;
  if (Extent>MAX_UINT32 || (UINT64)Address+Extent>0x100000000ULL) return;
  Node=FdtPathOffset(F,"/reserved-memory");
  if (Node<0 || FdtAddressCells(F,Node)!=2 || FdtSizeCells(F,Node)!=2) return;
  P=FdtGetProp(F,Node,"ranges",&Len); if (!P || Len) return;
  Node=FdtPathOffset(F,"/reserved-memory/cont_splash_region");
  P=FdtGetProp(F,Node,"reg",&Len); if (!P || Len!=16 || Be32(P) || Be32(P+8)) return;
  UINT32 Reserved=Be32(P+4); Size=Be32(P+12);
  if (!Size || Address<Reserved ||
      (UINT64)Address+Extent>(UINT64)Reserved+Size) return;
  // Read candidates only when every declared stream has the previously sampled
  // S1/S2 bypass configuration. This does not prove hidden fabric ownership.
  O->Status=3;
  P=FdtGetProp(F,Mdp,"iommus",&Len); if(!P || Len!=12) return;
  Handle=Be32(P); Sid=Be32(P+4); Mask=Be32(P+8);
  Smmu=FdtNodeOffsetByPhandle(F,Handle); P=FdtGetProp(F,Smmu,"reg",&Len);
  if(!P || Len<8) return;
  SmmuBase=Be32(P); SmmuSize=Be32(P+4);
  GET(SmmuBase+0x20,Id0); GET(SmmuBase+0x24,Id1); GET(SmmuBase,Cr0);
  if(Cr0&1 || !(Id0&(1U<<27)) || Id0&(1U<<8)) return;
  Page=1U<<((Id1>>31)?16:12);
  for (UINT32 Target=0; Target<0x8000; ++Target) if (!((Target^Sid)&~Mask)) {
    UINT32 Matches=0;
    for (UINT32 I=0; I<(Id0&255); ++I) {
      UINT32 Smr; GET(SmmuBase+0x800+I*4,Smr);
      if (!(Smr&(1U<<31)) || ((Target^Smr)&~((Smr>>16)&0x7fff)&0x7fff)) continue;
      ++Matches; GET(SmmuBase+0xc00+I*4,V); if((V>>16)&3) return;
      UINT32 Bank=V&255; if(Bank>=(Id1&255)) return;
      GET(SmmuBase+Page+Bank*4,Cbar);
      GET(SmmuBase+Page+0x800+Bank*4,V); if(!(V&1) || ((Cbar>>16)&3)!=1) return;
      GET(SmmuBase+SmmuSize/2+Bank*Page,Sctlr); if(Sctlr&1) return;
    }
    if(Matches!=1) return;
  }
  O->Status=2;
  P=FdtGetProp(F,Mdp,"qcom,sde-ctl-off",&Len); if(!P || Len<=0 || Len%4) return;
  for(INT32 I=0; I<Len/4; ++I) {
    UINT32 At=MdpBase+Be32(P+I*4); GET(At+0xf4,V);
    if(V) { if(Active) return; Active=V; GET(At+0x14,V); if(!(V&(1U<<17))) return; }
  }
  if(!Active || (Active&(Active-1))) return;
  while((Active>>Intf)!=1) ++Intf;
  P=FdtGetProp(F,Mdp,"qcom,sde-intf-off",&Len);
  if(!P || Intf>=(UINT32)Len/4 || !Prop(F,Mdp,"qcom,sde-intf-size",&V) || V<0x2b4) return;
  Intf=MdpBase+Be32(P+Intf*4);
  GET(Intf+0x284,V); if(V!=1) return;
  GET(Intf+0x2b4,V); if(!(V&(1U<<31)) || !(V&65535)) return;
  if(Frequency<1000 || Frequency>1000000000) return;
  O->Status=4; O->Width=W; O->Height=H; O->Stride=Stride; O->BaseLow=Address;
  O->Extent=(UINT32)Extent; O->InterfaceBase=Intf; O->CounterFrequency=Frequency; O->Grid=RAPHAEL_PIXEL_GRID;
  for(UINT32 Y=0; Y<RAPHAEL_PIXEL_GRID; ++Y) for(UINT32 X=0; X<RAPHAEL_PIXEL_GRID; ++X) {
    UINT32 At=Address+(Y*(H-1)/(RAPHAEL_PIXEL_GRID-1))*Stride+(X*(W-1)/(RAPHAEL_PIXEL_GRID-1))*4;
    O->Pixels[O->PixelCount++]=Read32(At,Context);
  }
  O->Status=5;
  for(UINT32 I=0; I<RAPHAEL_PIXEL_ROUNDS; ++I) {
    UINT64 Start=Counter(Context);
    O->Refresh[I][0]=(UINT32)Start; O->Refresh[I][1]=(UINT32)(Start>>32);
    O->Refresh[I][2]=Read32(Intf+0x26c,Context);
    O->Refresh[I][3]=Read32(Intf+0xac,Context);
    O->Refresh[I][4]=Read32(Intf+0x298,Context);
    O->Refresh[I][5]=Read32(Intf+0x2b0,Context);
    ++O->RefreshCount;
    if(I+1==RAPHAEL_PIXEL_ROUNDS) break;
    UINT32 Budget=10000000;
    while(Counter(Context)-Start<Frequency/500) if(!--Budget) return;
  }
  O->Status=6;
}
