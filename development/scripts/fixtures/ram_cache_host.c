// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef NULL
#include <Library/RaphaelRamCacheLib.h>
// These offsets explain the exact native AArch64 opcode audit. Keep the
// context, phase counters and unchanged emergency engine layout explicit.
_Static_assert(sizeof(RAPHAEL_RAM_CACHE_STATE)==176,"cache state ABI");
_Static_assert(sizeof(RAPHAEL_RAM_WRITE_STATE)==232,"engine state ABI");
_Static_assert(sizeof(RAPHAEL_RAM_WRITE_RESULT)==184,"engine wire ABI");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_CACHE_STATE,Engine)==0x80,"native engine");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_CACHE_STATE,Sync)==0x98,"native sync");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_CACHE_STATE,Context)==0xa8,"caller context");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_CACHE_STATE,Result.PrePageSync)==0x60,"pre counter");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_CACHE_STATE,Result.PostPageSync)==0x68,"post counter");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_WRITE_RESULT,ActivePage)==0x40,"active page");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_WRITE_RESULT,BackupWords)==0x48,"backup count");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_WRITE_RESULT,Dirty)==0x50,"dirty guard");
_Static_assert(__builtin_offsetof(RAPHAEL_RAM_WRITE_RESULT,WriteAttempts)==0x68,"checkpoint count");
#define BASE 0x100000000ULL
#define WORDS 4096
STATIC struct {
 UINT64 Before,Dram[WORDS],Cache[WORDS],Original[WORDS],After;
 UINT8 Valid[WORDS],Dirty[WORDS];
 UINT64 Reads,Writes,Syncs,Queries,FailRead,FailWrite,FailSync,FailQuery,ClockCalls,ClockStep;
 BOOLEAN SyncPermanent,BadPa,BadAttribute,ReadOnly;
} A;
STATIC struct {UINT64 Before;RAPHAEL_RAM_CACHE_STATE State;UINT64 After;} C;
STATIC struct {UINT64 Before;RAPHAEL_RAM_WRITE_STATE State;UINT64 After;} S;
STATIC struct {UINT64 Before,Words[512],After;} Backup;
STATIC RAPHAEL_RAM_POLICY P;
STATIC RAPHAEL_RAM_READ_RESULT G;
STATIC RAPHAEL_RAM_MAPPED_RESULT M;
STATIC RAPHAEL_RAM_ENTRY E;
STATIC UINTN Checks;
STATIC BOOLEAN Direct;
STATIC VOID Check(BOOLEAN Good,CONST char *Name){
 if(!Good){fprintf(stderr,"FAIL %s cache=%llu/%llu engine=%llu/%llu dirty=%llu sync=%llu\n",Name,
  (unsigned long long)C.State.Result.Status,(unsigned long long)C.State.Result.Reason,
  (unsigned long long)S.State.Result.Status,(unsigned long long)S.State.Result.Reason,
  (unsigned long long)S.State.Result.Dirty,(unsigned long long)A.Syncs);exit(1);}
 ++Checks;printf("PASS %s %s\n",Direct?"direct":"generic",Name);
}
STATIC VOID Reset(VOID){
 memset(&A,0,sizeof(A));memset(&C,0,sizeof(C));memset(&S,0,sizeof(S));memset(&Backup,0,sizeof(Backup));
 memset(&P,0,sizeof(P));memset(&G,0,sizeof(G));memset(&M,0,sizeof(M));memset(&E,0,sizeof(E));
 A.Before=A.After=C.Before=C.After=S.Before=S.After=Backup.Before=Backup.After=0x1234feed9876cafeULL;
 for(UINTN I=0;I<WORDS;++I){A.Dram[I]=A.Original[I]=(BASE+I*8)^0x0123456789abcdefULL;A.Cache[I]=A.Dram[I]^0x7777;A.Valid[I]=1;}
 A.ClockStep=100;
 P.Version=1;P.HeaderBytes=64;P.TotalBytes=80;P.Base=BASE;P.Bytes=RAPHAEL_RAM_WINDOW_BYTES;P.Stride=RAPHAEL_RAM_STRIDE;P.MaxReads=256;P.GuardCount=1;P.Guards[0]=(RAPHAEL_RANGE){0x80000000,4096};
 G.Version=1;G.Status=3;G.Base=BASE;G.Bytes=P.Bytes;G.Stride=P.Stride;G.Requested=G.Attempted=G.Completed=256;G.ActiveAddress=BASE+P.Bytes-8;
 G.Digest=0x1234;G.NonZero=1;G.StartCounter=10;G.EndCounter=20;G.Frequency=19200000;G.Mmfr0=2;G.PhysicalBits=40;
 G.RamRanges=G.PolicyGuards=1;G.EntryGuards=4;G.CurrentEl=4;G.Daif=0x3c0;
 M.Version=1;M.Status=3;M.Base=BASE;M.Bytes=P.Bytes;M.Stride=P.Stride;M.Requested=M.Attempted=M.Completed=256;M.ActiveAddress=G.ActiveAddress;
 M.BeforeDigest=M.Digest=G.Digest;M.NonZero=1;M.StartCounter=30;M.EndCounter=40;M.Frequency=G.Frequency;M.CurrentEl=4;M.Sctlr=0x1005;M.Daif=0x3c0;
 M.ReadTranslations=M.WriteDenied=M.ParPreserved=256;
 E.CurrentEl=4;E.Sctlr=0x1005;E.Daif=0x3c0;E.Mmfr0=2;E.PhysicalBits=40;E.Frequency=G.Frequency;
}
STATIC BOOLEAN Read(UINT64 Address,UINT64 *Value,VOID *Context){
 assert(Context==&A);assert(Address>=BASE&&(Address-BASE)/8<WORDS&&!(Address&7));++A.Reads;
 if(A.Reads==A.FailRead)return FALSE;
 UINTN I=(Address-BASE)/8;
 if(!A.Valid[I]){A.Cache[I]=A.Dram[I];A.Valid[I]=1;}
 *Value=A.Cache[I];return TRUE;
}
STATIC BOOLEAN Write(UINT64 Address,UINT64 Value,VOID *Context){
 assert(Context==&A);assert(Address>=BASE&&(Address-BASE)/8<WORDS&&!(Address&7));++A.Writes;
 if(A.Writes==A.FailWrite)return FALSE;
 UINTN I=(Address-BASE)/8;
 A.Cache[I]=Value;A.Valid[I]=A.Dirty[I]=1;return TRUE;
}
STATIC BOOLEAN Sync(UINT64 Address,UINT64 Bytes,VOID *Context){
 assert(Context==&A);assert(Address>=BASE&&!(Address&4095)&&Bytes==4096&&Address+Bytes<=BASE+WORDS*8);++A.Syncs;
 if(A.Syncs==A.FailSync||(A.SyncPermanent&&A.Syncs>=A.FailSync))return FALSE;
 for(UINTN I=(Address-BASE)/8;I<(Address-BASE+Bytes)/8;++I){if(A.Dirty[I])A.Dram[I]=A.Cache[I];A.Dirty[I]=A.Valid[I]=0;}
 return TRUE;
}
STATIC BOOLEAN Translate(UINT64 Address,UINT64 *RP,UINT64 *WP,UINT64 *Original,UINT64 *Restored,VOID *Context){
 assert(Context==&A);++A.Queries;*RP=*WP=(0xffULL<<56)|(Address&~4095ULL);*Original=*Restored=0;
 if(A.BadPa)*RP^=4096;
 if(A.BadAttribute)*WP^=1ULL<<56;
 if(A.ReadOnly)*WP=0x1f;
 return A.Queries!=A.FailQuery;
}
STATIC UINT64 Clock(VOID *Context){assert(Context==&A);return 1000+A.ClockStep*A.ClockCalls++;}
STATIC BOOLEAN ReadDirect(UINT64 Address,UINT64 *Value,VOID *Context){
 RAPHAEL_RAM_CACHE_STATE *Cache=Context;assert(Cache==&C.State&&Cache->Context==&A&&Cache->Engine==&S.State);
 if(!RaphaelRamCacheBeforeRead(Cache,Address))return FALSE;
 return Read(Address,Value,Cache->Context);
}
STATIC BOOLEAN WriteDirect(UINT64 Address,UINT64 Value,VOID *Context){
 RAPHAEL_RAM_CACHE_STATE *Cache=Context;assert(Cache==&C.State&&Cache->Context==&A&&Cache->Engine==&S.State);
 if(!Write(Address,Value,Cache->Context))return FALSE;
 return RaphaelRamCacheAfterWrite(Cache,Address);
}
STATIC BOOLEAN Run(UINT64 Pages){
 if(Direct)return RaphaelWriteRamWithCacheDirect(&C.State,&S.State,&P,80,&G,&M,&E,Pages,Backup.Words,ReadDirect,WriteDirect,Translate,Sync,Clock,&A);
 return RaphaelWriteRamWithCache(&C.State,&S.State,&P,80,&G,&M,&E,Pages,Backup.Words,Read,Write,Translate,Sync,Clock,&A);
}

STATIC BOOLEAN Restored(VOID){
 return !memcmp(A.Dram,A.Original,sizeof(A.Dram))&&S.State.Result.Dirty==0&&S.State.Result.BackupWords==0&&
 A.Before==A.After&&C.Before==C.After&&S.Before==S.After&&Backup.Before==Backup.After&&C.Before==0x1234feed9876cafeULL;
}
int main(int argc,char **argv){
 assert(argc==2);for(UINTN Mode=0;Mode<2;++Mode){Direct=(BOOLEAN)Mode;Reset();Check(Run(1)&&Restored()&&A.Syncs==4&&C.State.Result.PrePageSync==1&&C.State.Result.PostPageSync==3,"one page uses real clean/invalidate model and restores stale-cache DRAM");
 Check(S.State.Context==&C.State&&C.State.Context==&A&&(!Direct||(S.State.Read==ReadDirect&&S.State.Write==WriteDirect)),"direct dispatch and emergency context preserve caller identity");
 FILE *f=fopen(argv[1],"wb");assert(f);assert(fwrite(&C.State.Result,128,1,f)==1);assert(fwrite(&S.State.Result,184,1,f)==1);fclose(f);
 Reset();Check(Run(8)&&Restored()&&A.Syncs==32&&S.State.Result.CompletedPages==8,"eight pages are separately synchronized and restored");
 UINT64 Positions[]={1,512,513,1024,1536,2048};
 for(UINTN I=0;I<sizeof(Positions)/sizeof(Positions[0]);++I){Reset();A.FailRead=Positions[I];BOOLEAN Ok=Run(1);if(S.State.Result.Dirty)Check(RaphaelRestoreRamPage(&S.State),"failed read retains usable emergency restore context");Check(!Ok&&Restored(),"read failure restores physical model bytes");}
 UINT64 Writes[]={1,257,512,513,1024,1025,1536};
 for(UINTN I=0;I<sizeof(Writes)/sizeof(Writes[0]);++I){Reset();A.FailWrite=Writes[I];BOOLEAN Ok=Run(1);if(S.State.Result.Dirty)Check(RaphaelRestoreRamPage(&S.State),"failed write emergency recovery");Check(!Ok&&Restored(),"write failure restores physical model bytes");}
 for(UINTN I=1;I<=4;++I){Reset();A.FailSync=I;BOOLEAN Ok=Run(1);if(S.State.Result.Dirty)Check(RaphaelRestoreRamPage(&S.State),"failed PoC synchronization emergency recovery");Check(!Ok&&Restored(),"sync failure never reports completion and original DRAM is recovered");}
 Reset();A.FailSync=3;A.SyncPermanent=TRUE;Check(!Run(1)&&S.State.Result.Dirty==1&&S.State.Result.BackupWords==512,"persistent PoC failure retains dirty state and complete original backup");
 Check(!RaphaelRestoreRamPage(&S.State)&&S.State.Result.Dirty==1&&!memcmp(Backup.Words,A.Original,4096),"persistent restore failure cannot clear dirty evidence");
 for(UINTN I=1;I<=256;I+=127){Reset();A.FailQuery=I;Check(!Run(1)&&!A.Writes&&!A.Reads,"translation failure issues no candidate memory access");}
 Reset();A.BadPa=TRUE;Check(!Run(1)&&!A.Writes,"wrong PA rejected before write");Reset();A.BadAttribute=TRUE;Check(!Run(1)&&!A.Writes,"wrong WB attribute rejected");Reset();A.ReadOnly=TRUE;Check(!Run(1)&&!A.Writes,"read-only permission rejected before write");
 Reset();E.Sctlr=0;Check(!Run(1)&&!A.Writes,"MMU-off live entry rejected");Reset();E.Daif=0;Check(!Run(1)&&!A.Writes,"unmasked entry rejected");Reset();E.CurrentEl=8;Check(!Run(1)&&!A.Writes,"wrong EL rejected");
 Reset();E.PhysicalBits=52;Check(!Run(1)&&!A.Writes,"unsupported PA width rejected");Reset();E.Frequency=1;Check(!Run(1)&&!A.Writes,"frequency mismatch rejected");
 Reset();M.Digest^=1;Check(!Run(1)&&!A.Writes,"changed mapped digest rejected");Reset();M.WriteDenied=0;Check(!Run(1)&&!A.Writes,"missing prior RO proof rejected");Reset();M.Sctlr=0;Check(!Run(1)&&!A.Writes,"missing mapped MCI proof rejected");Reset();M.Status=1;Check(!Run(1)&&!A.Writes,"stage2 pending gate rejected");
 Reset();P.Guards[0].Base=BASE;Check(!Run(1)&&!A.Writes,"overlapping sourced policy rejected by unchanged engine");
 Reset();Check(!Run(0)&&!A.Writes,"zero pages rejected");Reset();Check(!Run(65537)&&!A.Writes,"oversize request rejected");
 Reset();A.ClockStep=G.Frequency*9;Check(!Run(1)&&!A.Writes&&Restored(),"eight second budget rejects before mutation");
 }
 printf("RAM_CACHE_HOST_OK %lu\n",(unsigned long)Checks);return 0;
}
