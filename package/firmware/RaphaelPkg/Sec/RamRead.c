// SPDX-License-Identifier: BSD-2-Clause-Patent
// Sparse READ-ONLY access to a policy-selected candidate. No allocator or writes.
#include <RaphaelRamRead.h>
#include <Library/FdtLib.h>
extern INT32 fdt_check_full(CONST VOID *, UINTN);
extern INT32 fdt_num_mem_rsv(CONST VOID *);
extern INT32 fdt_get_mem_rsv(CONST VOID *, INT32, UINT64 *, UINT64 *);
STATIC BOOLEAN Valid(UINT64 Base,UINT64 Bytes){return Bytes&&Base<=MAX_UINT64-Bytes;}
STATIC BOOLEAN Overlap(UINT64 A,UINT64 N,UINT64 B,UINT64 M){return A<B+M&&B<A+N;}
STATIC UINT64 Cell(CONST UINT32 *P,INT32 Count){
  CONST UINT8 *B=(CONST VOID *)P;UINT64 V=0;
  for(INT32 I=0;I<Count*4;++I)V=(V<<8)|B[I];
  return V;
}
STATIC BOOLEAN Different(CONST VOID *A,CONST VOID *B,UINTN N){
  CONST UINT8 *X=A,*Y=B;for(UINTN I=0;I<N;++I)if(X[I]!=Y[I])return TRUE;return FALSE;
}
STATIC BOOLEAN AllowedRoot(CONST VOID *Fdt){
  INT32 Len;CONST CHAR8 *P=FdtGetProp(Fdt,0,"compatible",&Len);BOOLEAN Found=FALSE;
  if(!P||Len<=0||Len>256)return FALSE;
  for(INT32 I=0;I<Len;){
    INT32 End=I;while(End<Len&&P[End])++End;
    if(End==Len||End==I)return FALSE;
    if((End-I==11&&!Different(P+I,"qcom,sm8150",11))||
       (End-I==16&&!Different(P+I,"linux,dummy-virt",16)))Found=TRUE;
    I=End+1;
  }
  return Found;
}
STATIC BOOLEAN Reg(CONST VOID *Fdt,INT32 Node,INT32 Parent,CONST RAPHAEL_RAM_POLICY *P,
                   RAPHAEL_RAM_READ_RESULT *R,BOOLEAN IsRam,BOOLEAN *Contained){
  INT32 Ac=FdtAddressCells(Fdt,Parent),Sc=FdtSizeCells(Fdt,Parent),Len;
  CONST UINT32 *Cells=FdtGetProp(Fdt,Node,"reg",&Len);
  if(Ac<1||Ac>2||Sc<1||Sc>2||!Cells||Len<=0||Len%((Ac+Sc)*4))return FALSE;
  for(INT32 I=0;I<Len/4;I+=Ac+Sc){
    UINT64 Base=Cell(Cells+I,Ac),Bytes=Cell(Cells+I+Ac,Sc);
    if(!Valid(Base,Bytes))return FALSE;
    if(IsRam){
      if(++R->RamRanges>32)return FALSE;
      if(P->Base>=Base&&P->Base+P->Bytes<=Base+Bytes)*Contained=TRUE;
    }else{
      if(++R->FixedReservations>128||Overlap(P->Base,P->Bytes,Base,Bytes))return FALSE;
    }
  }
  return TRUE;
}
VOID RaphaelReadRamWindow(CONST VOID *Fdt,CONST RAPHAEL_RAM_POLICY *P,UINTN PolicyBytes,
  CONST RAPHAEL_RAM_ENTRY *E,RAPHAEL_RAM_READ_RESULT *R,
  RAPHAEL_RAM_READ64 Read,RAPHAEL_RAM_COUNTER Counter,VOID *Context){
  STATIC CONST UINT8 PaBits[16]={32,36,40,42,44,48,52,0,0,0,0,0,0,0,0,0};
  BOOLEAN Contained=FALSE;INT32 Node=-1,Depth=-1,Parents[64],Reserved,Len,Visited=0;
  UINT64 InitrdStart=0,InitrdEnd=0;
  if(!R)return;
  for(UINTN I=0;I<sizeof(*R);++I)((UINT8 *)R)[I]=0;
  R->Version=1;R->Status=4;R->Reason=1;
  if(!P||!E||!Read||!Counter||PolicyBytes<64||P->Version!=1||P->HeaderBytes!=64||
     P->GuardCount>RAPHAEL_RAM_MAX_GUARDS||PolicyBytes!=64+16*P->GuardCount||P->TotalBytes!=PolicyBytes||
     !Valid(P->Base,P->Bytes)||P->Bytes!=RAPHAEL_RAM_WINDOW_BYTES||P->Stride!=RAPHAEL_RAM_STRIDE||
     (P->Base&(P->Stride-1))||P->MaxReads!=2*(P->Bytes/P->Stride)||!P->GuardCount||
     E->CurrentEl!=4||(E->Sctlr&0x1005)||(E->Daif&0x3c0)!=0x3c0||
     E->Frequency<1000||E->Frequency>1000000000||!E->GuardCount||E->GuardCount>8)return;
  R->Base=P->Base;R->Bytes=P->Bytes;R->Stride=P->Stride;R->Requested=P->MaxReads;
  R->Frequency=E->Frequency;R->Mmfr0=E->Mmfr0;R->PhysicalBits=E->PhysicalBits;
  R->CurrentEl=E->CurrentEl;R->Sctlr=E->Sctlr;R->Daif=E->Daif;
  R->Reason=2;
  if(!PaBits[E->Mmfr0&15]||E->PhysicalBits!=PaBits[E->Mmfr0&15]||P->Base+P->Bytes>(1ULL<<E->PhysicalBits))return;
  R->Status=5;R->Reason=3;
  if(!Fdt||FdtCheckHeader(Fdt)||FdtTotalSize(Fdt)>0x100000||fdt_check_full(Fdt,FdtTotalSize(Fdt))||!AllowedRoot(Fdt))return;
  R->Reason=5;
  for(UINTN I=0;I<P->GuardCount;++I){
    RAPHAEL_RANGE G=P->Guards[I];++R->PolicyGuards;
    if(!Valid(G.Base,G.Length)||Overlap(P->Base,P->Bytes,G.Base,G.Length))return;
  }
  for(UINTN I=0;I<E->GuardCount;++I){
    RAPHAEL_RANGE G=E->Guards[I];++R->EntryGuards;
    if(!Valid(G.Base,G.Length)||Overlap(P->Base,P->Bytes,G.Base,G.Length))return;
  }
  Reserved=FdtPathOffset(Fdt,"/reserved-memory");
  if(Reserved>=0&&(!FdtGetProp(Fdt,Reserved,"ranges",&Len)||Len))return;
  while((Node=FdtNextNode(Fdt,Node,&Depth))>=0){
    if(Depth<0)break;
    if(Depth>=64||++Visited>65536)return;
    INT32 Parent=Depth?Parents[Depth-1]:-1;Parents[Depth]=Node;
    CONST CHAR8 *Type=FdtGetProp(Fdt,Node,"device_type",&Len);
    if(Type&&Len==7&&!Different(Type,"memory",7)){
      // A root-level RAM declaration has no untranslated parent bus.
      if(Parent!=0||!Reg(Fdt,Node,Parent,P,R,TRUE,&Contained))return;
    }
    if(Reserved>=0&&Parent==Reserved){
      CONST VOID *Value=FdtGetProp(Fdt,Node,"reg",&Len);
      if(Value){if(!Reg(Fdt,Node,Parent,P,R,FALSE,&Contained))return;}
      else if(FdtGetProp(Fdt,Node,"size",&Len)){
        INT32 Sc=FdtSizeCells(Fdt,Reserved);
        if(Sc<1||Sc>2||Len!=Sc*4)return;
        ++R->DynamicPools; // Records a declaration; no allocation/ownership grant.
      }
    }
  }
  if(Node!=-1&&Depth>=0)return;
  R->Reason=4;if(!Contained)return;
  R->Reason=5;
  INT32 Count=fdt_num_mem_rsv(Fdt);if(Count<0||Count>128)return;
  for(INT32 I=0;I<Count;++I){
    UINT64 Base,Bytes;++R->HeaderReservations;
    if(fdt_get_mem_rsv(Fdt,I,&Base,&Bytes)||!Valid(Base,Bytes)||Overlap(P->Base,P->Bytes,Base,Bytes))return;
  }
  Node=FdtPathOffset(Fdt,"/chosen");if(Node<0)return;
  CONST UINT32 *Value=FdtGetProp(Fdt,Node,"linux,initrd-start",&Len);
  if(Value){if(Len!=4&&Len!=8)return;InitrdStart=Cell(Value,Len/4);}
  Value=FdtGetProp(Fdt,Node,"linux,initrd-end",&Len);
  if(Value){if(Len!=4&&Len!=8)return;InitrdEnd=Cell(Value,Len/4);}
  if((InitrdStart||InitrdEnd)&&(InitrdEnd<=InitrdStart||
     !Valid(InitrdStart,InitrdEnd-InitrdStart)||Overlap(P->Base,P->Bytes,InitrdStart,InitrdEnd-InitrdStart)))return;
  R->Status=2;R->Reason=6;R->Digest=14695981039346656037ULL;
  R->StartCounter=Counter(Context);R->EndCounter=R->StartCounter;
  for(UINT64 Offset=0;Offset<P->Bytes;Offset+=P->Stride)for(UINTN Tail=0;Tail<2;++Tail){
    UINT64 V;R->ActiveAddress=P->Base+Offset+(Tail?P->Stride-8:0);++R->Attempted;
    if(!Read(R->ActiveAddress,&V,Context)){R->Status=7;R->Reason=7;return;}
    ++R->Completed;if(V)++R->NonZero;
    R->Digest=(R->Digest^R->ActiveAddress)*1099511628211ULL;
    R->Digest=(R->Digest^V)*1099511628211ULL;
    UINT64 Previous=R->EndCounter;R->EndCounter=Counter(Context);
    if(R->EndCounter<Previous||R->EndCounter-R->StartCounter>E->Frequency/10){R->Status=6;return;}
  }
  R->Status=3;R->Reason=0;
}
