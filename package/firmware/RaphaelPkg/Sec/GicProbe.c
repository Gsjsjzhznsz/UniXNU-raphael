// SPDX-License-Identifier: BSD-2-Clause-Patent
// Offsets/affinity/stride semantics audited against the pinned primary source.
#include <RaphaelGicProbe.h>
#include <Library/FdtLib.h>
STATIC UINT32 Be32(CONST VOID *P) {CONST UINT8 *B=P;return ((UINT32)B[0]<<24)|((UINT32)B[1]<<16)|((UINT32)B[2]<<8)|B[3];}
STATIC UINT64 Cells(CONST UINT8 *P,INT32 N) {UINT64 V=Be32(P);if(N==2)V=(V<<32)|Be32(P+4);return V;}
STATIC BOOLEAN Equal(CONST CHAR8 *P,INT32 N,CONST CHAR8 *S) {
 INT32 I=0;while(I<N&&S[I]&&P[I]==S[I])++I;return I==N&&S[I]==0;
}
// Ignore malformed unrelated legacy compatible strings, but never malformed
// matching candidates. Scanning every node prevents an unrelated bad string
// from hiding a duplicate GIC later in the tree.
STATIC INT32 Compatible(CONST VOID *F,INT32 N,CONST CHAR8 *S) {
 INT32 L;CONST CHAR8 *P=FdtGetProp(F,N,"compatible",&L);BOOLEAN Found=FALSE,Bad=FALSE;
 if(!P)return 0;
 for(INT32 I=0;I<L;) {INT32 J=I;while(J<L&&P[J])++J;
  if(Equal(P+I,J-I,S))Found=TRUE;
  if(J==L)Bad=TRUE;
  I=J+1;
 }
 return Found?(Bad?-1:1):0;
}
STATIC BOOLEAN Enabled(CONST VOID *F,INT32 N) {
 INT32 L;CONST CHAR8 *P=FdtGetProp(F,N,"status",&L);
 return !P||(L==5&&Equal(P,4,"okay")&&P[4]==0)||(L==3&&Equal(P,2,"ok")&&P[2]==0);
}
STATIC BOOLEAN Overlap(UINT64 A,UINT64 N,UINT64 B,UINT64 M) {return A<B+M&&B<A+N;}
STATIC UINT32 ReadWord(RAPHAEL_GIC_SNAPSHOT *O,RAPHAEL_GIC_READ32 Read,VOID *C,UINT64 A) {++O->ReadCount;return Read(A,C);}
VOID RaphaelCollectGic(CONST VOID *F,UINT64 Mpidr,UINT64 ProtectedBase,UINT64 ProtectedEnd,
 RAPHAEL_GIC_SNAPSHOT *O,RAPHAEL_GIC_READ32 Read,VOID *C) {
 INT32 N=-1,Depth=-1,Gic=-1,Parent,L,Ac,Sc;CONST UINT8 *P;UINT64 Limit=MAX_UINT64,At;
 if(!O)return;
 for(UINTN I=0;I<sizeof(*O);++I)((UINT8 *)O)[I]=0;
 O->Version=1;O->Status=2;O->Reason=1;
 if(!F||FdtCheckHeader(F))return;
 O->Status=1;O->Reason=0;
 INT32 Phone=Compatible(F,0,"qcom,sm8150"),Qemu=Compatible(F,0,"linux,dummy-virt");
 if(!Phone&&!Qemu)return;
 O->Status=2;O->Reason=1;
 if(Phone<0||Qemu<0||!Read||ProtectedBase>=ProtectedEnd||FdtAddressCells(F,0)!=2||FdtSizeCells(F,0)!=2)return;
 while((N=FdtNextNode(F,N,&Depth))>=0&&Depth>=0) {
  INT32 Match=Compatible(F,N,"arm,gic-v3");
  if(Match<0||(Match&&Gic>=0))return;
  if(Match)Gic=N;
 }
 if(N<-1||Gic<0||!Enabled(F,Gic))return;
 Parent=FdtParentOffset(F,Gic);if(Parent<0||!Enabled(F,Parent))return;
 if(Parent!=0) {
  if(!Phone||FdtParentOffset(F,Parent)!=0||Parent!=FdtPathOffset(F,"/soc")||FdtAddressCells(F,Parent)!=1||FdtSizeCells(F,Parent)!=1)return;
  P=FdtGetProp(F,Parent,"ranges",&L);if(!P)return;
  if(L!=0){if(L!=16||Be32(P)||Be32(P+4)||Be32(P+8)||!Be32(P+12))return;Limit=Be32(P+12);}
 }else if(!Qemu)return;
 P=FdtGetProp(F,Gic,"interrupt-controller",&L);if(!P||L!=0)return;
 P=FdtGetProp(F,Gic,"#interrupt-cells",&L);if(!P||L!=4||Be32(P)!=3)return;
 P=FdtGetProp(F,Gic,"#redistributor-regions",&L);if(!P||L!=4||Be32(P)!=1)return;
 Ac=FdtAddressCells(F,Parent);Sc=FdtSizeCells(F,Parent);
 if(Ac<1||Ac>2||Sc<1||Sc>2)return;
 P=FdtGetProp(F,Gic,"reg",&L);if(!P||L!=2*(Ac+Sc)*4)return;
 O->GicD=Cells(P,Ac);O->GicDBytes=Cells(P+Ac*4,Sc);
 P+=(Ac+Sc)*4;O->GicR=Cells(P,Ac);O->GicRBytes=Cells(P+Ac*4,Sc);
 UINT64 Bases[2]={O->GicD,O->GicR},Sizes[2]={O->GicDBytes,O->GicRBytes};
 for(UINTN I=0;I<2;++I)if(!Bases[I]||!Sizes[I]||((Bases[I]|Sizes[I])&0xffff)||Bases[I]>MAX_UINT64-Sizes[I]||
    Bases[I]+Sizes[I]>Limit||Overlap(Bases[I],Sizes[I],ProtectedBase,ProtectedEnd-ProtectedBase))return;
 if(O->GicDBytes<0x10000||O->GicRBytes<0x20000||Overlap(Bases[0],Sizes[0],Bases[1],Sizes[1]))return;
 P=FdtGetProp(F,Gic,"redistributor-stride",&L);
 if(P){if(L!=8)return;O->Stride=Cells(P,2);if(O->Stride<0x20000||(O->Stride&0xffff)||O->Stride>O->GicRBytes||O->GicRBytes%O->Stride)return;}
 if(Phone&&!O->Stride)return; // this board binding provides explicit stride
 // Reject MMIO aliases into any FDT RAM bank before the first hardware read.
 N=-1;Depth=-1;
 while((N=FdtNextNode(F,N,&Depth))>=0&&Depth>=0) {
  P=FdtGetProp(F,N,"device_type",&L);
  if(!P||L!=7||!Equal((CONST CHAR8 *)P,6,"memory")||P[6])continue;
  if(FdtParentOffset(F,N)!=0)return;
  P=FdtGetProp(F,N,"reg",&L);if(!P||L<=0||L%16)return;
  for(INT32 I=0;I<L;I+=16) {
   UINT64 B=Cells(P+I,2),S=Cells(P+I+8,2);if(!S||B>MAX_UINT64-S)return;
   for(UINTN J=0;J<2;++J)if(Overlap(B,S,Bases[J],Sizes[J]))return;
  }
 }
 if(N<-1)return;
 O->Mpidr=Mpidr;O->Affinity=((Mpidr>>32)&255)<<24|(Mpidr&0xffffff);O->BootIndex=MAX_UINT64;
 O->Status=3;O->Reason=2;
 O->Pidr2=ReadWord(O,Read,C,O->GicD+0xffe8);
 if(((O->Pidr2>>4)&15)!=3&&((O->Pidr2>>4)&15)!=4)return;
 O->Ctlr=ReadWord(O,Read,C,O->GicD);O->Typer=ReadWord(O,Read,C,O->GicD+4);O->Iidr=ReadWord(O,Read,C,O->GicD+8);
 At=O->GicR;
 for(UINTN I=0;I<RAPHAEL_GIC_MAX_FRAMES;++I) {
  O->Reason=3;if(At<O->GicR||At-O->GicR>O->GicRBytes-0x20000)return;
  RAPHAEL_GIC_FRAME *R=&O->Frames[I];R->Base=At;
  R->Pidr2=ReadWord(O,Read,C,At+0xffe8);if(((R->Pidr2>>4)&15)!=3&&((R->Pidr2>>4)&15)!=4)return;
  UINT64 Low=ReadWord(O,Read,C,At+8),High=ReadWord(O,Read,C,At+12);R->Typer=Low|(High<<32);
  R->Ctlr=ReadWord(O,Read,C,At);R->Iidr=ReadWord(O,Read,C,At+4);R->Waker=ReadWord(O,Read,C,At+0x14);
  O->FrameCount=I+1;O->Reason=4;
  for(UINTN J=0;J<I;++J)if((O->Frames[J].Typer>>32)==High)return;
  if(High==O->Affinity)O->BootIndex=I;
  UINT64 Step=O->Stride?O->Stride:((R->Typer&2)?0x40000:0x20000);
  if(Step<((R->Typer&2)?0x40000:0x20000)||At>MAX_UINT64-Step||Step>O->GicRBytes-(At-O->GicR))return;
  if(R->Typer&16)break;
  At+=Step;
 }
 O->Reason=5;
 if(!O->FrameCount||!(O->Frames[O->FrameCount-1].Typer&16)||O->BootIndex==MAX_UINT64)return;
 At=O->Frames[O->BootIndex].Base+0x10000;
 CONST UINT32 Offsets[RAPHAEL_GIC_SGI_WORDS]={0x80,0x100,0x200,0x300,0xd00,0xc00,0xc04,0x400,0x404,0x408,0x40c,0x410,0x414,0x418,0x41c};
 for(UINTN I=0;I<RAPHAEL_GIC_SGI_WORDS;++I)O->Sgi[I]=ReadWord(O,Read,C,At+Offsets[I]);
 O->Status=4;O->Reason=0;
}
