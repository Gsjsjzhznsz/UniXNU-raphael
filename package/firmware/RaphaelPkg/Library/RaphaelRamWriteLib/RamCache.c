// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelRamCacheLib.h>
STATIC BOOLEAN Valid(UINT64 B,UINT64 N){return N&&B<=MAX_UINT64-N;}
STATIC BOOLEAN Overlap(UINT64 A,UINT64 N,UINT64 B,UINT64 M){return A<B+M&&B<A+N;}
STATIC BOOLEAN ReadCached(UINT64 Address,UINT64 *Value,VOID *Context){
 RAPHAEL_RAM_CACHE_STATE *C=Context;
 if(!RaphaelRamCacheBeforeRead(C,Address))return FALSE;
 return C->Read(Address,Value,C->Context);
}
STATIC BOOLEAN WriteCached(UINT64 Address,UINT64 Value,VOID *Context){
 RAPHAEL_RAM_CACHE_STATE *C=Context;
 if(!C->Write(Address,Value,C->Context))return FALSE;
 return RaphaelRamCacheAfterWrite(C,Address);
}
STATIC UINT64 CounterCached(VOID *Context){RAPHAEL_RAM_CACHE_STATE *C=Context;return C->Counter(C->Context);}
STATIC BOOLEAN WriteRamWithCache(BOOLEAN Direct,RAPHAEL_RAM_CACHE_STATE *C,RAPHAEL_RAM_WRITE_STATE *S,
 CONST RAPHAEL_RAM_POLICY *P,UINTN PolicyBytes,CONST RAPHAEL_RAM_READ_RESULT *B,
 CONST RAPHAEL_RAM_MAPPED_RESULT *M,CONST RAPHAEL_RAM_ENTRY *E,UINT64 Pages,UINT64 *Backup,
 RAPHAEL_RAM_READ64 Read,RAPHAEL_RAM_WRITE64 Write,RAPHAEL_RAM_TRANSLATE Translate,
 RAPHAEL_RAM_CACHE_SYNC Sync,RAPHAEL_RAM_COUNTER Counter,VOID *Context){
 if(!C||!S||!P||!B||!M||!E||!Backup||S->Result.Dirty)return FALSE;
 RAPHAEL_RANGE Inputs[]={{(UINTN)S,sizeof(*S)},{(UINTN)P,PolicyBytes},{(UINTN)B,sizeof(*B)},
  {(UINTN)M,sizeof(*M)},{(UINTN)E,sizeof(*E)},{(UINTN)Backup,RAPHAEL_RAM_PAGE_BYTES}};
 if(!Valid((UINTN)C,sizeof(*C)))return FALSE;
 for(UINTN I=0;I<sizeof(Inputs)/sizeof(Inputs[0]);++I)
  if(!Valid(Inputs[I].Base,Inputs[I].Length)||Overlap((UINTN)C,sizeof(*C),Inputs[I].Base,Inputs[I].Length))return FALSE;
 for(UINTN I=0;I<sizeof(*C);++I)((UINT8 *)C)[I]=0;
 RAPHAEL_RAM_CACHE_RESULT *R=&C->Result;R->Version=1;R->Status=4;R->Reason=1;
 if(!Read||!Write||!Translate||!Sync||!Counter||!Pages||Pages>65536||
  B->Version!=1||B->Status!=3||B->Reason||B->Bytes!=RAPHAEL_RAM_WINDOW_BYTES||B->Stride!=RAPHAEL_RAM_STRIDE||
  B->Base>MAX_UINT64-B->Bytes||(B->Base&(B->Stride-1))||B->Requested!=256||B->Attempted!=256||B->Completed!=256||
  M->Version!=1||M->Status!=3||M->Reason||M->Base!=B->Base||M->Bytes!=B->Bytes||M->Stride!=B->Stride||
  M->Requested!=256||M->Attempted!=256||M->Completed!=256||M->ReadTranslations!=256||M->WriteDenied!=256||M->ParPreserved!=256||
  M->CurrentEl!=4||(M->Sctlr&0x1005)!=0x1005||(M->Daif&0x3c0)!=0x3c0||
  M->Frequency!=B->Frequency||M->OriginalPar!=M->RestoredPar||M->ActiveAddress!=B->Base+B->Bytes-8||
  M->EndCounter<M->StartCounter||M->EndCounter-M->StartCounter>M->Frequency/10||
  M->BeforeDigest!=B->Digest||M->Digest!=B->Digest||M->NonZero!=B->NonZero||
  E->CurrentEl!=4||(E->Sctlr&0x1005)!=0x1005||(E->Daif&0x3c0)!=0x3c0||
  E->Frequency!=B->Frequency||E->Mmfr0!=B->Mmfr0||E->PhysicalBits!=B->PhysicalBits||
  E->Frequency<1000||E->Frequency>1000000000||E->PhysicalBits<32||E->PhysicalBits>48||
  B->Base+B->Bytes>(1ULL<<E->PhysicalBits)||
  Overlap((UINTN)C,sizeof(*C),B->Base,B->Bytes))return FALSE;
 R->Base=B->Base;R->Bytes=B->Bytes;R->Pages=Pages;R->CurrentEl=E->CurrentEl;R->Sctlr=E->Sctlr;R->Daif=E->Daif;R->Frequency=E->Frequency;
 R->Status=5;R->Reason=2;
 for(UINT64 Offset=0;Offset<B->Bytes;Offset+=B->Stride)for(UINTN Tail=0;Tail<2;++Tail){
  UINT64 Address=B->Base+Offset+(Tail?B->Stride-8:0),RP=0,WP=0,Original=0,Restored=0;
  if(!Translate(Address,&RP,&WP,&Original,&Restored,Context)||Original!=Restored||
   (RP&1)||(WP&1)||(RP>>56)!=0xff||(WP>>56)!=0xff||
   (RP&0x0000fffffffff000ULL)!=(Address&~4095ULL)||(WP&0x0000fffffffff000ULL)!=(Address&~4095ULL))return FALSE;
  ++R->ReadWriteTranslations;++R->ParPreserved;
 }
 C->Engine=S;C->Read=Read;C->Write=Write;C->Sync=Sync;C->Counter=Counter;C->Context=Context;
 R->Status=2;R->Reason=3;
 BOOLEAN Ok=RaphaelWriteRamPages(S,P,PolicyBytes,B,Pages,Backup,RAPHAEL_RAM_PAGE_BYTES,
  Direct?Read:ReadCached,Direct?Write:WriteCached,CounterCached,C);
 if(!Ok){R->Status=6;return FALSE;}
 if(R->PrePageSync!=Pages||R->PostPageSync!=3*Pages){R->Status=6;R->Reason=4;return FALSE;}
 R->Status=3;R->Reason=0;return TRUE;
}
BOOLEAN RaphaelWriteRamWithCache(RAPHAEL_RAM_CACHE_STATE *C,RAPHAEL_RAM_WRITE_STATE *S,
 CONST RAPHAEL_RAM_POLICY *P,UINTN PolicyBytes,CONST RAPHAEL_RAM_READ_RESULT *B,
 CONST RAPHAEL_RAM_MAPPED_RESULT *M,CONST RAPHAEL_RAM_ENTRY *E,UINT64 Pages,UINT64 *Backup,
 RAPHAEL_RAM_READ64 Read,RAPHAEL_RAM_WRITE64 Write,RAPHAEL_RAM_TRANSLATE Translate,
 RAPHAEL_RAM_CACHE_SYNC Sync,RAPHAEL_RAM_COUNTER Counter,VOID *Context){
 return WriteRamWithCache(FALSE,C,S,P,PolicyBytes,B,M,E,Pages,Backup,Read,Write,Translate,Sync,Counter,Context);
}
BOOLEAN RaphaelWriteRamWithCacheDirect(RAPHAEL_RAM_CACHE_STATE *C,RAPHAEL_RAM_WRITE_STATE *S,
 CONST RAPHAEL_RAM_POLICY *P,UINTN PolicyBytes,CONST RAPHAEL_RAM_READ_RESULT *B,
 CONST RAPHAEL_RAM_MAPPED_RESULT *M,CONST RAPHAEL_RAM_ENTRY *E,UINT64 Pages,UINT64 *Backup,
 RAPHAEL_RAM_READ64 Read,RAPHAEL_RAM_WRITE64 Write,RAPHAEL_RAM_TRANSLATE Translate,
 RAPHAEL_RAM_CACHE_SYNC Sync,RAPHAEL_RAM_COUNTER Counter,VOID *Context){
 return WriteRamWithCache(TRUE,C,S,P,PolicyBytes,B,M,E,Pages,Backup,Read,Write,Translate,Sync,Counter,Context);
}
