// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelUfsHandoff.h>
#include <Library/FdtLib.h>
STATIC UINT32 Be32(CONST UINT8 *P){return ((UINT32)P[0]<<24)|((UINT32)P[1]<<16)|((UINT32)P[2]<<8)|P[3];}
STATIC BOOLEAN Eq(CONST CHAR8 *P,INT32 L,CONST CHAR8 *S){INT32 I=0;while(I<L&&S[I]&&P[I]==S[I])++I;return I==L&&!S[I];}
STATIC INT32 Compat(CONST VOID *F,INT32 N,CONST CHAR8 *S){
 INT32 L;CONST CHAR8 *P=FdtGetProp(F,N,"compatible",&L);BOOLEAN Found=FALSE,Bad=FALSE;
 if(!P)return 0;
 for(INT32 I=0;I<L;){INT32 J=I;while(J<L&&P[J])++J;if(Eq(P+I,J-I,S))Found=TRUE;if(J==L)Bad=TRUE;I=J+1;}
 return Found?(Bad?-1:1):0;
}
STATIC BOOLEAN Enabled(CONST VOID *F,INT32 N){INT32 L;CONST CHAR8 *P=FdtGetProp(F,N,"status",&L);return !P||(L==5&&Eq(P,4,"okay")&&!P[4])||(L==3&&Eq(P,2,"ok")&&!P[2]);}
STATIC BOOLEAN Overlap(UINT64 A,UINT64 N,UINT64 B,UINT64 M){return A<B+M&&B<A+N;}
VOID RaphaelCollectUfsHandoff(CONST VOID *F,UINT64 Start,UINT64 End,RAPHAEL_UFS_HANDOFF *O,RAPHAEL_UFS_READ32 Read,VOID *C){
 if(!O)return;
 for(UINTN I=0;I<sizeof(*O);++I)((UINT8 *)O)[I]=0;
 O->Version=1;O->Status=2;
 if(!F||FdtCheckHeader(F))return;
 INT32 Root=Compat(F,0,"qcom,sm8150");if(!Root){O->Status=1;return;}
 if(Root<0||!Read||Start>=End||FdtAddressCells(F,0)!=2||FdtSizeCells(F,0)!=2)return;
 INT32 Soc=FdtPathOffset(F,"/soc"),N=-1,D=-1,Host=-1,L;CONST UINT8 *P;
 if(Soc<0||FdtParentOffset(F,Soc)!=0||!Enabled(F,Soc)||FdtAddressCells(F,Soc)!=1||FdtSizeCells(F,Soc)!=1)return;
 P=FdtGetProp(F,Soc,"ranges",&L);if(!P)return;
 UINT64 Limit=MAX_UINT64;
 if(L){if(L!=16||Be32(P)||Be32(P+4)||Be32(P+8)||!Be32(P+12))return;Limit=Be32(P+12);}
 while((N=FdtNextNode(F,N,&D))>=0&&D>=0){INT32 M=Compat(F,N,"qcom,ufshc");if(M<0||(M&&Host>=0))return;if(M)Host=N;}
 if(N<-1||Host<0||FdtParentOffset(F,Host)!=Soc||!Enabled(F,Host))return;
 P=FdtGetProp(F,Host,"reg-names",&L);if(!P||L<8||!Eq((CONST CHAR8 *)P,7,"ufs_mem")||P[7])return;
 P=FdtGetProp(F,Host,"reg",&L);if(!P||L<8||L%8)return;
 O->Base=Be32(P);O->Bytes=Be32(P+4);
 if(!O->Base||(O->Base&4095)||O->Bytes<0xa0||O->Bytes>0x10000||O->Base+O->Bytes>Limit||Overlap(O->Base,O->Bytes,Start,End-Start))return;
 N=-1;D=-1;
 while((N=FdtNextNode(F,N,&D))>=0&&D>=0){
  P=FdtGetProp(F,N,"device_type",&L);if(!P||L!=7||!Eq((CONST CHAR8 *)P,6,"memory")||P[6])continue;
  if(FdtParentOffset(F,N)!=0)return;
  P=FdtGetProp(F,N,"reg",&L);if(!P||L<=0||L%16)return;
  for(INT32 I=0;I<L;I+=16){UINT64 B=((UINT64)Be32(P+I)<<32)|Be32(P+I+4),S=((UINT64)Be32(P+I+8)<<32)|Be32(P+I+12);if(!S||B>MAX_UINT64-S||Overlap(O->Base,O->Bytes,B,S))return;}
 }
 if(N<-1)return;
 // Standard read-only CAP/VER/AHIT/IS/IE/HCS/HCE/UIC errors and UTRL/UTMRL.
 // No response buffers, ICE key slots, vendor registers, acknowledge or writes.
 CONST UINT32 Offsets[RAPHAEL_UFS_HANDOFF_REGS]={0,8,0x18,0x20,0x24,0x30,0x34,0x38,0x3c,0x40,0x44,0x48,0x50,0x54,0x58,0x60,0x78,0x80};
 for(UINTN I=0;I<RAPHAEL_UFS_HANDOFF_REGS;++I){O->Offsets[I]=Offsets[I];O->First[I]=Read(O->Base+Offsets[I],C);++O->ReadCount;}
 for(UINTN I=0;I<RAPHAEL_UFS_HANDOFF_REGS;++I){O->Second[I]=Read(O->Base+Offsets[I],C);++O->ReadCount;}
 O->Status=3;
}
