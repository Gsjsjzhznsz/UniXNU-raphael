// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef NULL
#include <Library/RaphaelRamWriteLib.h>
#define TEST_BASE 0x100000000ULL
#define WORDS (8*512)
typedef struct {
 UINT64 Before,Memory[WORDS],After,Original[WORDS];
 UINT64 Reads,Writes,FailRead,FailWrite,WrongRead,ClockCalls,ClockAt,ClockStep;
 BOOLEAN AfterWrite,Backwards;
} MODEL;
STATIC MODEL M;
STATIC RAPHAEL_RAM_POLICY P;
STATIC RAPHAEL_RAM_READ_RESULT G;
STATIC RAPHAEL_RAM_WRITE_STATE S;
STATIC struct {UINT64 Before,Words[512],After;} B;
STATIC UINTN Checks;
STATIC UINT64 Random=0x2718281828459045ULL;
STATIC UINT64 Next(VOID){Random^=Random<<13;Random^=Random>>7;Random^=Random<<17;return Random;}
STATIC VOID Check(BOOLEAN V,CONST char *Name){if(!V){fprintf(stderr,"FAIL %s status=%llu reason=%llu read=%llu write=%llu dirty=%llu\n",Name,(unsigned long long)S.Result.Status,(unsigned long long)S.Result.Reason,(unsigned long long)M.Reads,(unsigned long long)M.Writes,(unsigned long long)S.Result.Dirty);exit(1);}++Checks;printf("PASS %s\n",Name);}
STATIC VOID Reset(VOID){
 memset(&M,0,sizeof(M));memset(&S,0,sizeof(S));memset(&P,0,sizeof(P));memset(&G,0,sizeof(G));
 M.Before=M.After=B.Before=B.After=0x1234feedcafe9876ULL;
 for(UINTN I=0;I<WORDS;++I)M.Memory[I]=M.Original[I]=Next();
 for(UINTN I=0;I<512;++I)B.Words[I]=0xdeadbeef;
 P.Version=1;P.HeaderBytes=64;P.TotalBytes=80;P.Base=TEST_BASE;P.Bytes=RAPHAEL_RAM_WINDOW_BYTES;P.Stride=RAPHAEL_RAM_STRIDE;P.MaxReads=256;P.GuardCount=1;P.Guards[0]=(RAPHAEL_RANGE){0x80000000,0x10000000};
 G.Version=1;G.Status=3;G.Base=P.Base;G.Bytes=P.Bytes;G.Stride=P.Stride;G.Requested=G.Attempted=G.Completed=256;G.PolicyGuards=1;G.EntryGuards=4;G.RamRanges=3;G.ActiveAddress=P.Base+P.Bytes-8;G.CurrentEl=4;G.Daif=0x3c0;G.Mmfr0=2;G.PhysicalBits=40;G.Frequency=1000;G.StartCounter=100;G.EndCounter=110;
}
STATIC UINTN Index(UINT64 A){assert(A>=TEST_BASE&&A<TEST_BASE+sizeof(M.Memory)&&!(A&7));return (UINTN)((A-TEST_BASE)/8);}
STATIC BOOLEAN Read(UINT64 A,UINT64 *V,VOID *C){assert(C==&M);++M.Reads;if(M.Reads==M.FailRead)return FALSE;*V=M.Memory[Index(A)];if(M.Reads==M.WrongRead)*V^=1;return TRUE;}
STATIC BOOLEAN Write(UINT64 A,UINT64 V,VOID *C){assert(C==&M);++M.Writes;BOOLEAN Fail=M.Writes==M.FailWrite;if(!Fail||M.AfterWrite)M.Memory[Index(A)]=V;return !Fail;}
STATIC UINT64 Counter(VOID *C){assert(C==&M);++M.ClockCalls;if(M.ClockAt&&M.ClockCalls>=M.ClockAt)return M.Backwards?0:100000;return 100+M.ClockCalls*M.ClockStep;}
STATIC BOOLEAN Run(UINT64 N){return RaphaelWriteRamPages(&S,&P,80,&G,N,B.Words,sizeof(B.Words),Read,Write,Counter,&M);}
STATIC BOOLEAN Same(VOID){return !memcmp(M.Memory,M.Original,sizeof(M.Memory))&&M.Before==M.After&&M.Before==B.Before&&B.Before==B.After;}
STATIC BOOLEAN ZeroBackup(VOID){for(UINTN I=0;I<512;++I)if(B.Words[I])return FALSE;return TRUE;}
STATIC VOID Rejected(CONST char *Name){Check(!Run(1)&&!M.Reads&&!M.Writes&&!S.Result.Dirty&&Same(),Name);}
int main(int argc,char **argv){
 assert(argc==2);
 Reset();Check(Run(1)&&Same()&&ZeroBackup()&&S.Result.Status==3&&S.Result.CompletedPages==1&&S.Result.RestoredPages==1&&S.Result.PatternWords==1024&&S.Result.RestoreWords==512&&M.Reads==2048&&M.Writes==1536&&S.Result.OriginalDigest==S.Result.RestoreDigest,"nonzero randomized original page restored with independent full-memory comparison");
 FILE *Wire=fopen(argv[1],"wb");assert(Wire&&fwrite(&S.Result,1,sizeof(S.Result),Wire)==sizeof(S.Result)&&!fclose(Wire));
 Reset();Check(Run(8)&&Same()&&ZeroBackup()&&S.Result.CompletedPages==8&&S.Result.RestoredPages==8&&M.Reads==8*2048&&M.Writes==8*1536,"eight distinct pages and surrounding canaries restored");
 for(UINT64 N=1;N<=512;++N){Reset();M.FailRead=N;assert(!Run(1)&&Same()&&!M.Writes&&!S.Result.Dirty&&ZeroBackup());}
 Check(TRUE,"all 512 backup-read failure positions issue no store");
 for(UINTN After=0;After<2;++After){for(UINT64 N=1;N<=1024;++N){Reset();M.FailWrite=N;M.AfterWrite=(BOOLEAN)After;assert(!Run(1)&&Same()&&!S.Result.Dirty&&ZeroBackup()&&S.Result.Status==5);}}
 Check(TRUE,"all 1024 pattern-write positions recover failures both before and after the store");
 for(UINT64 N=513;N<=1536;++N){Reset();M.FailRead=N;assert(!Run(1)&&Same()&&!S.Result.Dirty&&ZeroBackup()&&S.Result.Status==5);}
 Check(TRUE,"all 1024 pattern-read failures restore originals");
 for(UINT64 N=513;N<=1536;++N){Reset();M.WrongRead=N;assert(!Run(1)&&Same()&&!S.Result.Dirty&&ZeroBackup()&&S.Result.PatternMismatches==1);}
 Check(TRUE,"all 1024 false pattern values are rejected and recovered");
 for(UINT64 N=1025;N<=1536;++N){Reset();M.FailWrite=N;assert(!Run(1)&&S.Result.Dirty&&S.Result.BackupWords==512&&S.Result.Status==7);UINT64 Saved[512];memcpy(Saved,B.Words,sizeof(Saved));assert(!Run(1)&&!memcmp(Saved,B.Words,sizeof(Saved)));assert(RaphaelRestoreRamPage(&S)&&Same()&&!S.Result.Dirty&&ZeroBackup());}
 Check(TRUE,"all 512 restore-write failures retain the backup block a new run and recover on retry");
 for(UINT64 N=1537;N<=2048;++N){Reset();M.FailRead=N;assert(!Run(1)&&S.Result.Dirty&&S.Result.Status==7&&Same());assert(RaphaelRestoreRamPage(&S)&&Same()&&!S.Result.Dirty&&ZeroBackup());}
 Check(TRUE,"all 512 restore-read failures retain originals until a verified retry");
 for(UINT64 N=1537;N<=2048;++N){Reset();M.WrongRead=N;assert(!Run(1)&&S.Result.Dirty&&S.Result.Status==7);assert(RaphaelRestoreRamPage(&S)&&Same()&&!S.Result.Dirty);}
 Check(TRUE,"all 512 false restore values prevent success and permit retry");
 for(UINTN Back=0;Back<2;++Back)for(UINT64 N=2;N<=6;++N){Reset();M.ClockAt=N;M.Backwards=(BOOLEAN)Back;assert(!Run(1)&&Same()&&!S.Result.Dirty&&S.Result.Status==6);}
 Check(TRUE,"every clock boundary rejects expiry or backwards time without abandoning restoration");
 Reset();M.ClockStep=1;Check(Run(1)&&Same(),"monotonic nonzero counter advances accepted");
 Reset();G.PhysicalBits=36;Rejected("read gate physical width must agree with MMFR0");
 Reset();G.Mmfr0=7;Rejected("reserved PA encoding rejected");
 Reset();P.Base=1ULL<<40;G.Base=P.Base;G.ActiveAddress=P.Base+P.Bytes-8;Rejected("candidate past supported physical address rejected");
 Reset();P.Guards[0].Base=P.Base;Rejected("source guard overlap rejected");
 Reset();P.Guards[0]=(RAPHAEL_RANGE){MAX_UINT64,1};Rejected("source guard overflow rejected");
 Reset();P.TotalBytes=79;Rejected("policy length mismatch rejected");
 Reset();Check(!RaphaelWriteRamPages(&S,&P,63,&G,1,B.Words,sizeof(B.Words),Read,Write,Counter,&M)&&!M.Reads&&!M.Writes,"truncated policy header rejected");
 Reset();G.Status=2;Rejected("incomplete same-boot read gate rejected");
 Reset();G.Completed=255;Rejected("partial sparse reads rejected");
 Reset();G.ActiveAddress-=8;Rejected("last sparse address mismatch rejected");
 Reset();G.EntryGuards=0;Rejected("missing live entry protection rejected");
 Reset();G.RamRanges=0;Rejected("missing RAM containment evidence rejected");
 Reset();G.EndCounter=99;Rejected("backwards sparse-read gate rejected");
 Reset();G.EndCounter=201;Rejected("expired sparse-read gate rejected");
 Reset();G.Sctlr=1;Rejected("MMU-on entry rejected");
 Reset();G.Sctlr=4;Rejected("data cache-on entry rejected");
 Reset();G.Sctlr=4096;Rejected("instruction cache-on entry rejected");
 Reset();G.Daif=0x340;Rejected("unmasked IRQ rejected");
 Reset();G.CurrentEl=8;Rejected("wrong exception level rejected");
 Reset();G.Frequency=MAX_UINT64;Rejected("counter budget multiplication bounded");
 Reset();Check(!Run(0)&&!M.Writes&&!M.Reads,"zero pages rejected");
 Reset();Check(!Run(65537)&&!M.Writes&&!M.Reads,"page count beyond candidate rejected");
 Reset();Check(!RaphaelWriteRamPages(&S,&P,80,&G,1,(UINT64 *)&S,4096,Read,Write,Counter,&M)&&!M.Writes&&!M.Reads,"backup aliasing state rejected before clearing");
 Reset();Check(!RaphaelWriteRamPages(&S,&P,80,&G,1,(UINT64 *)&P,4096,Read,Write,Counter,&M)&&!M.Writes&&!M.Reads,"backup aliasing immutable policy rejected");
 Reset();Check(!RaphaelWriteRamPages(&S,&P,80,&G,1,(UINT64 *)(UINTN)TEST_BASE,4096,Read,Write,Counter,&M)&&!M.Writes&&!M.Reads,"backup inside candidate rejected without dereference");
 Reset();Check(!RaphaelWriteRamPages(&S,&P,80,&G,1,(UINT64 *)(UINTN)(MAX_UINT64-7),4096,Read,Write,Counter,&M)&&!M.Writes&&!M.Reads,"backup pointer overflow rejected without dereference");
 Reset();Check(!RaphaelWriteRamPages(&S,&P,80,&G,1,B.Words,4095,Read,Write,Counter,&M)&&!M.Writes&&!M.Reads,"backup size mismatch rejected");
 Reset();M.FailWrite=1025;assert(!Run(1)&&S.Result.Dirty);UINT64 Saved[512];memcpy(Saved,B.Words,sizeof(Saved));B.Words[17]^=1;UINT64 W=M.Writes;Check(!RaphaelRestoreRamPage(&S)&&S.Result.Dirty&&M.Writes==W&&S.Result.Reason==9,"corrupted original backup cannot be written into candidate");memcpy(B.Words,Saved,sizeof(Saved));Check(RaphaelRestoreRamPage(&S)&&Same(),"backup integrity repair allows recovery retry");
 Reset();M.FailWrite=1025;assert(!Run(1));RAPHAEL_RAM_WRITE_STATE Good=S;
 for(UINTN K=0;K<7;++K){S=Good;switch(K){case 0:S.Result.Bytes=0;break;case 1:S.Result.Base=MAX_UINT64-4095;break;case 2:S.Result.ActivePage=MAX_UINT64-7;break;case 3:S.Result.PageBytes=0;break;case 4:S.Result.CompletedPages=65536;break;case 5:S.Result.RequestedPages=0;break;default:S.Result.BackupWords=511;break;}UINT64 Before=M.Writes;assert(!RaphaelRestoreRamPage(&S)&&S.Result.Dirty&&M.Writes==Before);}
 Check(TRUE,"damaged recovery bounds never issue a store");S=Good;Check(RaphaelRestoreRamPage(&S)&&Same(),"valid retained state restores after rejected corrupt copies");
 Check(!RaphaelRestoreRamPage(NULL),"null recovery state rejected");
 printf("RAM_WRITE_HOST_OK %lu\n",(unsigned long)Checks);return 0;
}
