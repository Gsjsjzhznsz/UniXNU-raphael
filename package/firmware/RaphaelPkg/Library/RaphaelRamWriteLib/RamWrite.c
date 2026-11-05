// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelRamWriteLib.h>
STATIC BOOLEAN Valid(UINT64 B,UINT64 N){return N&&B<=MAX_UINT64-N;}
STATIC BOOLEAN Overlap(UINT64 A,UINT64 N,UINT64 B,UINT64 M){return A<B+M&&B<A+N;}
STATIC UINT64 Digest(UINT64 D,UINT64 A,UINT64 V){return ((D^A)*1099511628211ULL^V)*1099511628211ULL;}
STATIC UINT64 BackupDigest(RAPHAEL_RAM_WRITE_STATE *S){
 UINT64 D=14695981039346656037ULL;
 for(UINTN I=0;I<RAPHAEL_RAM_PAGE_WORDS;++I)D=Digest(D,S->Result.ActivePage+I*8,S->Backup[I]);
 return D;
}
STATIC VOID Clear(UINT64 *P){for(UINTN I=0;I<RAPHAEL_RAM_PAGE_WORDS;++I)P[I]=0;}
STATIC BOOLEAN Clock(RAPHAEL_RAM_WRITE_STATE *S){
 UINT64 Now=S->Counter(S->Context),Previous=S->Result.EndCounter;S->Result.EndCounter=Now;
 return Now>=Previous&&Now-S->Result.StartCounter<=S->Result.Frequency*8;
}
BOOLEAN RaphaelRestoreRamPage(RAPHAEL_RAM_WRITE_STATE *S){
 if(!S)return FALSE;
 RAPHAEL_RAM_WRITE_RESULT *R=&S->Result;
 if(!R->Dirty)return TRUE;
 // Check every address calculation before issuing a recovery store. Do not
 // discard an invalid dirty state: the caller must stop and retain evidence.
 if(R->Version!=1||R->Dirty!=1||!S->Backup||((UINTN)S->Backup&7)||!S->Read||!S->Write||
    R->BackupWords!=RAPHAEL_RAM_PAGE_WORDS||R->PageBytes!=RAPHAEL_RAM_PAGE_BYTES||
    R->Bytes!=RAPHAEL_RAM_WINDOW_BYTES||!Valid(R->Base,R->Bytes)||(R->Base&(RAPHAEL_RAM_STRIDE-1))||
    !R->RequestedPages||R->RequestedPages>R->Bytes/RAPHAEL_RAM_PAGE_BYTES||
    R->CompletedPages>=R->RequestedPages||R->RestoredPages!=R->CompletedPages||
    R->ActivePage!=R->Base+R->CompletedPages*RAPHAEL_RAM_PAGE_BYTES||
    !Valid((UINTN)S->Backup,RAPHAEL_RAM_PAGE_BYTES)||
    Overlap((UINTN)S->Backup,RAPHAEL_RAM_PAGE_BYTES,R->Base,R->Bytes)||
    Overlap((UINTN)S->Backup,RAPHAEL_RAM_PAGE_BYTES,(UINTN)S,sizeof(*S))){
  R->Status=7;R->Reason=10;return FALSE;
 }
 if(BackupDigest(S)!=S->BackupDigest){R->Status=7;R->Reason=9;return FALSE;}
 BOOLEAN Ok=TRUE;
 // Mandatory restoration has no diagnostic timeout. Complete all words even
 // after an individual callback failure, then independently read back all.
 for(UINTN I=0;I<RAPHAEL_RAM_PAGE_WORDS;++I){++R->WriteAttempts;if(!S->Write(R->ActivePage+I*8,S->Backup[I],S->Context))Ok=FALSE;}
 UINT64 D=R->RestoreDigest;
 for(UINTN I=0;I<RAPHAEL_RAM_PAGE_WORDS;++I){
  UINT64 V=0;++R->ReadAttempts;
  if(!S->Read(R->ActivePage+I*8,&V,S->Context)||V!=S->Backup[I]){++R->RestoreMismatches;Ok=FALSE;}
  D=Digest(D,R->ActivePage+I*8,V);
 }
 if(!Ok){R->Status=7;R->Reason=7;return FALSE;}
 R->RestoreDigest=D;R->RestoreWords+=RAPHAEL_RAM_PAGE_WORDS;++R->RestoredPages;
 R->Dirty=0;R->BackupWords=0;Clear(S->Backup);S->BackupDigest=0;return TRUE;
}
BOOLEAN RaphaelWriteRamPages(RAPHAEL_RAM_WRITE_STATE *S,CONST RAPHAEL_RAM_POLICY *P,UINTN PolicyBytes,
 CONST RAPHAEL_RAM_READ_RESULT *G,UINT64 Pages,UINT64 *Backup,UINTN BackupBytes,
 RAPHAEL_RAM_READ64 Read,RAPHAEL_RAM_WRITE64 Write,RAPHAEL_RAM_COUNTER Counter,VOID *Context){
 STATIC CONST UINT8 PaBits[16]={32,36,40,42,44,48,52,0,0,0,0,0,0,0,0,0};
 if(!S||S->Result.Dirty)return FALSE;
 // Reject aliases before clearing state, including aliases to input objects.
 UINT64 B=(UINTN)Backup,T=(UINTN)S,A=(UINTN)P,H=(UINTN)G;
 if(!P||!G||!Backup||!Valid(T,sizeof(*S))||!Valid(B,BackupBytes)||
    !Valid(A,PolicyBytes)||PolicyBytes<64||!Valid(H,sizeof(*G))||
    Overlap(T,sizeof(*S),B,BackupBytes)||Overlap(T,sizeof(*S),A,PolicyBytes)||
    Overlap(T,sizeof(*S),H,sizeof(*G))||Overlap(B,BackupBytes,A,PolicyBytes)||
    Overlap(B,BackupBytes,H,sizeof(*G)))return FALSE;
 for(UINTN I=0;I<sizeof(*S);++I)((UINT8 *)S)[I]=0;
 RAPHAEL_RAM_WRITE_RESULT *R=&S->Result;R->Version=1;R->Status=4;R->Reason=1;
 if((B&7)||BackupBytes!=RAPHAEL_RAM_PAGE_BYTES||!Read||!Write||!Counter||
    P->Version!=1||P->HeaderBytes!=64||P->GuardCount<1||P->GuardCount>RAPHAEL_RAM_MAX_GUARDS||
    PolicyBytes!=64+16*P->GuardCount||P->TotalBytes!=PolicyBytes||
    P->Bytes!=RAPHAEL_RAM_WINDOW_BYTES||!Valid(P->Base,P->Bytes)||(P->Base&(RAPHAEL_RAM_STRIDE-1))||
    P->Stride!=RAPHAEL_RAM_STRIDE||P->MaxReads!=256||!Pages||Pages>P->Bytes/RAPHAEL_RAM_PAGE_BYTES||
    G->Version!=1||G->Status!=3||G->Reason||G->Base!=P->Base||G->Bytes!=P->Bytes||G->Stride!=P->Stride||
    G->Requested!=256||G->Attempted!=256||G->Completed!=256||G->PolicyGuards!=P->GuardCount||
    !G->EntryGuards||G->EntryGuards>8||!G->RamRanges||G->RamRanges>32||
    G->FixedReservations>128||G->HeaderReservations>128||G->NonZero>256||
    !PaBits[G->Mmfr0&15]||G->PhysicalBits!=PaBits[G->Mmfr0&15]||
    P->Base+P->Bytes>(1ULL<<G->PhysicalBits)||
    G->ActiveAddress!=P->Base+P->Bytes-8||G->EndCounter<G->StartCounter||
    G->CurrentEl!=4||(G->Sctlr&0x1005)||(G->Daif&0x3c0)!=0x3c0||
    G->Frequency<1000||G->Frequency>1000000000||G->EndCounter-G->StartCounter>G->Frequency/10||
    Overlap(B,BackupBytes,P->Base,P->Bytes)||Overlap(T,sizeof(*S),P->Base,P->Bytes)||
    Overlap(A,PolicyBytes,P->Base,P->Bytes)||Overlap(H,sizeof(*G),P->Base,P->Bytes))return FALSE;
 for(UINTN I=0;I<P->GuardCount;++I){RAPHAEL_RANGE Q=P->Guards[I];if(!Valid(Q.Base,Q.Length)||Overlap(Q.Base,Q.Length,P->Base,P->Bytes))return FALSE;}
 S->Backup=Backup;S->Read=Read;S->Write=Write;S->Counter=Counter;S->Context=Context;
 R->Status=2;R->Reason=0;R->Base=P->Base;R->Bytes=P->Bytes;R->PageBytes=RAPHAEL_RAM_PAGE_BYTES;R->RequestedPages=Pages;R->Frequency=G->Frequency;
 R->OriginalDigest=R->RestoreDigest=14695981039346656037ULL;
 R->StartCounter=R->EndCounter=Counter(Context);
 for(UINT64 Page=0;Page<Pages;++Page){
  R->ActivePage=P->Base+Page*RAPHAEL_RAM_PAGE_BYTES;
  if(!Clock(S)){R->Status=6;R->Reason=6;return FALSE;}
  for(UINTN I=0;I<RAPHAEL_RAM_PAGE_WORDS;++I){
   ++R->ReadAttempts;
   if(!Read(R->ActivePage+I*8,&Backup[I],Context)){R->Status=5;R->Reason=2;Clear(Backup);R->BackupWords=0;return FALSE;}
   ++R->BackupWords;R->OriginalDigest=Digest(R->OriginalDigest,R->ActivePage+I*8,Backup[I]);
  }
  if(!Clock(S)){R->Status=6;R->Reason=6;Clear(Backup);R->BackupWords=0;return FALSE;}
  S->BackupDigest=BackupDigest(S);R->Dirty=1;
  BOOLEAN Ok=TRUE,TimedOut=FALSE;
  for(UINTN Phase=0;Phase<2&&Ok;++Phase){
   for(UINTN I=0;I<RAPHAEL_RAM_PAGE_WORDS;++I){
    UINT64 Address=R->ActivePage+I*8,V=(Address^0xa5a55a5a3c3cc3c3ULL)^(Phase?MAX_UINT64:0);++R->WriteAttempts;
    if(!Write(Address,V,Context)){Ok=FALSE;R->Reason=3;break;}
   }
   for(UINTN I=0;I<RAPHAEL_RAM_PAGE_WORDS&&Ok;++I){
    UINT64 Address=R->ActivePage+I*8,V,Expected=(Address^0xa5a55a5a3c3cc3c3ULL)^(Phase?MAX_UINT64:0);++R->ReadAttempts;
    if(!Read(Address,&V,Context)){Ok=FALSE;R->Reason=4;break;}
    if(V!=Expected){++R->PatternMismatches;Ok=FALSE;R->Reason=5;break;}++R->PatternWords;
   }
   if(!Clock(S)){TimedOut=TRUE;Ok=FALSE;R->Reason=6;}
  }
  if(!RaphaelRestoreRamPage(S))return FALSE;
  if(!Ok){R->Status=TimedOut?6:5;return FALSE;}
  ++R->CompletedPages;
 }
 if(!Clock(S)){R->Status=6;R->Reason=6;return FALSE;}
 if(R->OriginalDigest!=R->RestoreDigest){R->Status=7;R->Reason=8;return FALSE;}
 R->Status=3;R->Reason=0;return TRUE;
}
