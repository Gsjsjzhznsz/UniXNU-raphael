// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelRamMapped.h>
VOID RaphaelReadMappedRam(CONST RAPHAEL_RAM_READ_RESULT *B,CONST RAPHAEL_RAM_ENTRY *E,
 RAPHAEL_RAM_MAPPED_RESULT *R,RAPHAEL_RAM_TRANSLATE Translate,RAPHAEL_RAM_READ64 Read,
 RAPHAEL_RAM_COUNTER Counter,VOID *Context){
 STATIC CONST UINT8 PaBits[6]={32,36,40,42,44,48};
 if(!R)return;
 for(UINTN I=0;I<sizeof(*R);++I)((UINT8 *)R)[I]=0;
 R->Version=1;R->Status=4;R->Reason=1;
 if(!B||!E||!Translate||!Read||!Counter||B->Version!=1||B->Status!=3||B->Reason||
  B->Bytes!=RAPHAEL_RAM_WINDOW_BYTES||B->Stride!=RAPHAEL_RAM_STRIDE||
  B->Base>MAX_UINT64-B->Bytes||(B->Base&(B->Stride-1))||
  B->Requested!=256||B->Attempted!=256||B->Completed!=256||
  B->ActiveAddress!=B->Base+B->Bytes-8||B->NonZero>256||
  B->CurrentEl!=4||(B->Sctlr&0x1005)||(B->Daif&0x3c0)!=0x3c0||
  !B->RamRanges||B->RamRanges>32||!B->PolicyGuards||B->PolicyGuards>128||
  !B->EntryGuards||B->EntryGuards>8||B->FixedReservations>128||B->HeaderReservations>128||
  (B->Mmfr0&15)>=6||B->PhysicalBits!=PaBits[B->Mmfr0&15]||
  B->EndCounter<B->StartCounter||B->EndCounter-B->StartCounter>B->Frequency/10||
  B->Base+B->Bytes>(1ULL<<B->PhysicalBits)||E->CurrentEl!=4||
  (E->Sctlr&0x1005)!=0x1005||(E->Daif&0x3c0)!=0x3c0||
  E->Frequency!=B->Frequency||E->Mmfr0!=B->Mmfr0||E->PhysicalBits!=B->PhysicalBits||
  E->Frequency<1000||E->Frequency>1000000000)return;
 R->Base=B->Base;R->Bytes=B->Bytes;R->Stride=B->Stride;R->Requested=B->Requested;
 R->BeforeDigest=B->Digest;R->Frequency=E->Frequency;R->CurrentEl=E->CurrentEl;R->Sctlr=E->Sctlr;R->Daif=E->Daif;
 R->Status=2;R->Reason=2;R->Digest=14695981039346656037ULL;
 R->StartCounter=Counter(Context);R->EndCounter=R->StartCounter;
 for(UINT64 Offset=0;Offset<R->Bytes;Offset+=R->Stride)for(UINTN Tail=0;Tail<2;++Tail){
  UINT64 Address=R->Base+Offset+(Tail?R->Stride-8:0),V,ReadPar=0,WritePar=0,Original=0,Restored=0;
  R->ActiveAddress=Address;++R->Attempted;
  BOOLEAN Ok=Translate(Address,&ReadPar,&WritePar,&Original,&Restored,Context);
  if(R->Attempted==1){R->FirstReadPar=ReadPar;R->OriginalPar=Original;}
  R->LastReadPar=ReadPar;R->LastWritePar=WritePar;R->RestoredPar=Restored;
  R->Status=5;
  // 4KiB, <=48-bit identity mapping; PAR attributes must be normal WB (0xff).
  // S1E1W queries permission only: no candidate store is ever issued.
  if(!Ok||(ReadPar&1)||((ReadPar&0x0000fffffffff000ULL)!=(Address&~4095ULL))||
   (ReadPar>>56)!=0xff||!(WritePar&1)||Original!=Restored||Original!=R->OriginalPar)return;
  ++R->ReadTranslations;++R->WriteDenied;++R->ParPreserved;
  R->Status=2;R->Reason=3;
  if(!Read(Address,&V,Context)){R->Status=7;return;}
  ++R->Completed;if(V)++R->NonZero;
  R->Digest=(R->Digest^Address)*1099511628211ULL;R->Digest=(R->Digest^V)*1099511628211ULL;
  UINT64 Previous=R->EndCounter;R->EndCounter=Counter(Context);
  if(R->EndCounter<Previous||R->EndCounter-R->StartCounter>R->Frequency/10){R->Status=6;return;}
 }
 R->Reason=4;if(R->Digest!=R->BeforeDigest||R->NonZero!=B->NonZero){R->Status=8;return;}
 R->Status=3;R->Reason=0;
}
