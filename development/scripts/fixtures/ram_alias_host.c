// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelRamAliasLib.h>
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(RAPHAEL_RAM_ALIAS_RESULT) == 312, "alias result ABI");
_Static_assert(sizeof(RAPHAEL_RAM_ALIAS_STATE) == 400, "64-bit alias state ABI");
_Static_assert(sizeof(RAPHAEL_RAM_WRITE_RESULT) == 184, "old page result unchanged");
_Static_assert(sizeof(RAPHAEL_RAM_CACHE_RESULT) == 128, "old cache result unchanged");

// Synthetic addresses only. Candidate RAM is never host-dereferenced. DRAM
// decodes each sample through Map; the physically tagged cache is separate.
typedef struct {
  UINT64 Cookie;
  RAPHAEL_RAM_ALIAS_STATE S;
  RAPHAEL_RAM_POLICY P;
  RAPHAEL_RAM_READ_RESULT B;
  RAPHAEL_RAM_MAPPED_RESULT M;
  RAPHAEL_RAM_ENTRY E;
  UINT64 Pages, *Dram, *Original, *Cache, *Map, *Backup;
  unsigned char *Valid, *Dirty;
  UINT64 Reads, Writes, Syncs, Translates, Clocks, Time;
  char Fault;
  UINT64 At;
  int After, HoldRecovery, Reenter, Reentered, SlowRestore;
} MODEL;
static int Cases;
static void pass(const char *name) { ++Cases; printf("PASS %s\n", name); }
static UINT64 mix(UINT64 x) { x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL; x ^= x >> 27; return x * 0x94d049bb133111ebULL ^ (x >> 31); }
static UINT64 index_of(MODEL *m, UINT64 a) {
  assert(m->Cookie == 0x414c494153ULL && a >= m->P.Base);
  UINT64 o = a - m->P.Base, tail = o & 4095;
  assert(o < m->Pages * 4096 && (tail == 0 || tail == 4088));
  return o / 4096 * 2 + (tail != 0);
}
static int fault(MODEL *m, char kind, UINT64 n) { return m->Fault == kind && n == m->At; }
static BOOLEAN load(UINT64 a, UINT64 *v, VOID *ctx) {
  MODEL *m = ctx; UINT64 i = index_of(m,a); ++m->Reads;
  if ((m->HoldRecovery && m->S.Result.Phase == 6) || fault(m,'r',m->Reads)) return FALSE;
  if (!m->Valid[i]) { m->Cache[i] = m->Dram[m->Map[i]]; m->Valid[i] = 1; }
  *v = m->Cache[i]; return TRUE;
}
static BOOLEAN store(UINT64 a, UINT64 v, VOID *ctx) {
  MODEL *m = ctx; UINT64 i = index_of(m,a); ++m->Writes;
  if (m->S.Result.Phase != 6) {
    assert(m->S.Result.BackupWords == m->Pages * 2);
    assert(m->S.Result.ReadWriteTranslations == m->Pages * 2);
    assert(m->S.Result.ParPreserved == m->Pages * 2);
    assert(m->S.Result.Dirty == 1 && m->S.Result.ArmedWords >= i+1);
    assert(m->S.ArmedMirror == ~m->S.Result.ArmedWords);
    if (i == 0) for (UINT64 j=0; j<m->Pages*2; ++j) assert(m->Backup[j] == m->Original[m->Map[j]]);
    if (m->S.Result.Rounds) assert(m->S.Result.ArmedWords == m->Pages * 2);
  }
  int fail = fault(m,'w',m->Writes) || (m->HoldRecovery && m->S.Result.Phase == 6);
  if (fail && !m->After) return FALSE;
  m->Cache[i] = v; m->Valid[i] = m->Dirty[i] = 1;
  return !fail;
}
static BOOLEAN sync_page(UINT64 a, UINT64 bytes, VOID *ctx) {
  MODEL *m = ctx; assert(bytes == 4096 && !(a & 4095));
  UINT64 i = index_of(m,a); ++m->Syncs;
  if (m->SlowRestore && m->S.Result.Phase == 6) { m->Time += 9*m->B.Frequency; m->SlowRestore=0; }
  if (m->Reenter && m->S.Result.Phase == 6 && !m->Reentered) {
    m->Reentered = 1;
    UINT64 armed = m->S.Result.ArmedWords, saved = m->S.JournalSeal;
    assert(!RaphaelRestoreRamAliases(&m->S));
    assert(m->S.Result.RestoreActive == 1 && m->S.Result.ArmedWords == armed && m->S.JournalSeal == saved);
  }
  int fail = fault(m,'s',m->Syncs) || (m->HoldRecovery && m->S.Result.Phase == 6);
  if (fail && !m->After) return FALSE;
  for (UINT64 j=i; j<i+2; ++j) {
    if (m->Dirty[j]) m->Dram[m->Map[j]] = m->Cache[j];
    m->Valid[j] = m->Dirty[j] = 0;
  }
  return !fail;
}
static BOOLEAN translate(UINT64 a, UINT64 *r, UINT64 *w, UINT64 *o, UINT64 *p, VOID *ctx) {
  MODEL *m = ctx; index_of(m,a); ++m->Translates;
  *r = *w = 0xff00000000000000ULL | (a & ~4095ULL); *o = *p = 0x55aa;
  if (fault(m,'t',m->Translates)) return FALSE;
  if (fault(m,'i',m->Translates)) *w ^= 4096;
  if (fault(m,'p',m->Translates)) *p ^= 1;
  if (fault(m,'a',m->Translates)) *r &= 0x00ffffffffffffffULL;
  return TRUE;
}
static UINT64 counter(VOID *ctx) {
  MODEL *m = ctx; assert(!m->S.Result.RestoreActive); ++m->Clocks; ++m->Time;
  if (fault(m,'c',m->Clocks)) return m->Time - 2;
  if (fault(m,'d',m->Clocks)) return m->S.Result.StartCounter + 8*m->B.Frequency + 1;
  return m->Time;
}
static void init(MODEL *m, UINT64 pages) {
  memset(m,0,sizeof(*m)); m->Cookie=0x414c494153ULL; m->Pages=pages; m->Time=1000;
  m->Dram=calloc(pages*2,8); m->Original=calloc(pages*2,8); m->Cache=calloc(pages*2,8);
  m->Map=calloc(pages*2,8); m->Backup=calloc(pages*2,8); m->Valid=calloc(pages*2,1); m->Dirty=calloc(pages*2,1);
  assert(m->Dram&&m->Original&&m->Cache&&m->Map&&m->Backup&&m->Valid&&m->Dirty);
  for(UINT64 i=0;i<pages*2;++i) { m->Dram[i]=m->Original[i]=mix(i+0x3d072d3); m->Map[i]=i; }
  RAPHAEL_RAM_POLICY *p=&m->P;
  p->Version=1; p->HeaderBytes=64; p->TotalBytes=80; p->Base=0x100000000ULL;
  p->Bytes=RAPHAEL_RAM_WINDOW_BYTES; p->Stride=RAPHAEL_RAM_STRIDE; p->MaxReads=256; p->GuardCount=1;
  p->Guards[0]=(RAPHAEL_RANGE){0x80000000,0x1000000};
  RAPHAEL_RAM_READ_RESULT *b=&m->B;
  b->Version=1; b->Status=3; b->Base=p->Base; b->Bytes=p->Bytes; b->Stride=p->Stride;
  b->Requested=b->Attempted=b->Completed=256; b->ActiveAddress=p->Base+p->Bytes-8;
  b->Digest=0x55; b->StartCounter=10; b->EndCounter=20; b->Frequency=19200000; b->Mmfr0=2; b->PhysicalBits=40;
  b->RamRanges=2; b->PolicyGuards=1; b->EntryGuards=4; b->CurrentEl=4; b->Daif=0x3c0;
  RAPHAEL_RAM_MAPPED_RESULT *g=&m->M;
  g->Version=1; g->Status=3; g->Base=p->Base; g->Bytes=p->Bytes; g->Stride=p->Stride;
  g->Requested=g->Attempted=g->Completed=256; g->ActiveAddress=b->ActiveAddress;
  g->BeforeDigest=g->Digest=b->Digest; g->StartCounter=30; g->EndCounter=40; g->Frequency=b->Frequency;
  g->CurrentEl=4; g->Sctlr=0x1005; g->Daif=0x3c0; g->ReadTranslations=g->WriteDenied=g->ParPreserved=256;
  RAPHAEL_RAM_ENTRY *e=&m->E;
  e->CurrentEl=4; e->Sctlr=g->Sctlr; e->Daif=g->Daif; e->Mmfr0=b->Mmfr0; e->PhysicalBits=40;
  e->Frequency=b->Frequency; e->GuardCount=4;
  for(int i=0;i<4;++i) e->Guards[i]=(RAPHAEL_RANGE){0x80000000ULL+(UINT64)i*0x1000000,0x1000000};
}
static void destroy(MODEL *m) {
  free(m->Dram); free(m->Original); free(m->Cache); free(m->Map); free(m->Backup); free(m->Valid); free(m->Dirty);
}
static BOOLEAN run(MODEL *m) {
  return RaphaelProbeRamAliases(&m->S,&m->P,80,&m->B,&m->M,&m->E,m->Pages,m->Backup,m->Pages*16,
    load,store,translate,sync_page,counter,m);
}
static void original(MODEL *m) {
  assert(!memcmp(m->Dram,m->Original,m->Pages*16));
  assert(!m->S.Result.Dirty && !m->S.Result.ArmedWords && !m->S.Result.BackupWords && !m->S.Result.RestoreActive);
  for(UINT64 i=0;i<m->Pages*2;++i) { assert(!m->Backup[i]); assert(!m->Dirty[i]); }
}
static void no_io(MODEL *m) { assert(!m->Reads&&!m->Writes&&!m->Syncs&&!m->Translates&&!m->Clocks); }
static void recover(MODEL *m) {
  if(m->S.Result.Dirty) {
    assert(m->S.Result.BackupWords==m->Pages*2);
    assert(RaphaelRestoreRamAliases(&m->S));
  }
  original(m);
}
static void normal(UINT64 pages) {
  MODEL m; init(&m,pages); assert(run(&m)); RAPHAEL_RAM_ALIAS_RESULT *v=&m.S.Result;
  assert(v->Status==3 && !v->Reason && v->Rounds==2 && v->Samples==pages*2);
  assert(v->PatternWords==pages*4 && v->RestoredSamples==pages*2);
  assert(v->ReadWriteTranslations==pages*2 && v->ParPreserved==pages*2);
  assert(v->PrepareSync==pages && v->BackupSync==pages && v->PatternSync==pages*2 && v->VerifySync==pages*2);
  assert(v->RestorePreSync==pages && v->RestoreWriteSync==pages && v->RestoreReadSync==pages);
  assert(v->SyncAttempts==pages*9 && v->ReadAttempts==pages*8 && v->WriteAttempts==pages*6);
  assert(v->OriginalDigest==v->RestoreDigest && !v->PatternMismatches && !v->RestoreMismatches);
  original(&m); char name[100]; snprintf(name,sizeof(name),"all-samples-retained-and-restored-%llu-pages",(unsigned long long)pages); pass(name);
  destroy(&m);
}
static void alias(UINT64 pages, UINT64 from, UINT64 to, const char *name) {
  MODEL m; init(&m,pages); m.Map[from]=to;
  assert(!run(&m)); assert(m.S.Result.Status==5 && m.S.Result.Reason==5 && m.S.Result.PatternMismatches);
  original(&m); pass(name); destroy(&m);
}
static void callback_faults(void) {
  MODEL baseline; init(&baseline,3); assert(run(&baseline));
  UINT64 counts[]={baseline.Reads,baseline.Writes,baseline.Syncs,baseline.Translates,baseline.Translates,baseline.Translates,baseline.Translates,baseline.Clocks,baseline.Clocks};
  char kinds[]={'r','w','s','t','i','p','a','c','d'}; destroy(&baseline);
  for(unsigned k=0;k<sizeof(kinds);++k) for(int after=0;after<=((kinds[k]=='w'||kinds[k]=='s')?1:0);++after)
    for(UINT64 n=(kinds[k]=='c'||kinds[k]=='d')?2:1;n<=counts[k];++n) {
      MODEL m; init(&m,3); m.Fault=kinds[k]; m.At=n; m.After=after;
      assert(!run(&m)); assert(m.S.Result.Status!=3); recover(&m);
      char name[100]; snprintf(name,sizeof(name),"callback-%c-%s-position-%llu",kinds[k],after?"after-effect":"before-effect",(unsigned long long)n);
      pass(name); destroy(&m);
    }
}
static void dirty(MODEL *m) {
  init(m,4); m->Fault='w'; m->At=5; m->After=1; m->HoldRecovery=1;
  assert(!run(m)); assert(m->S.Result.Status==7 && m->S.Result.Dirty && m->S.Result.ArmedWords==5);
  assert(m->S.Result.BackupWords==8); m->HoldRecovery=0; m->Fault=0;
}
static void retained_recovery(void) {
  MODEL m; dirty(&m); UINT64 writes=m.Writes, reads=m.Reads, syncs=m.Syncs;
  m.Backup[7]^=1; assert(!RaphaelRestoreRamAliases(&m.S));
  assert(m.S.Result.Reason==9 && m.Writes==writes && m.Reads==reads && m.Syncs==syncs && m.S.Result.Dirty);
  m.Backup[7]^=1; assert(RaphaelRestoreRamAliases(&m.S)); original(&m); pass("complete-backup-integrity-checked-before-any-recovery-store"); destroy(&m);
  dirty(&m); RAPHAEL_RAM_ALIAS_STATE saved=m.S;
  struct {size_t offset;UINT64 bad;} bad[]={
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Version),2},{offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Dirty),2},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Dirty),0},{offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Base),MAX_UINT64},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Bytes),4096},{offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.PageBytes),8},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Pages),0},{offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Pages),65537},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.Samples),6},{offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.BackupWords),7},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.ArmedWords),0},{offsetof(RAPHAEL_RAM_ALIAS_STATE,Result.ArmedWords),9},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Backup),0},{offsetof(RAPHAEL_RAM_ALIAS_STATE,BackupBytes),8},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Read),0},{offsetof(RAPHAEL_RAM_ALIAS_STATE,Write),0},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,Sync),0},{offsetof(RAPHAEL_RAM_ALIAS_STATE,BackupDigest),0},
    {offsetof(RAPHAEL_RAM_ALIAS_STATE,JournalSeal),0},{offsetof(RAPHAEL_RAM_ALIAS_STATE,ArmedMirror),0}};
  for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);++i) {
    m.S=saved; memcpy((char*)&m.S+bad[i].offset,&bad[i].bad,8); writes=m.Writes; reads=m.Reads; syncs=m.Syncs;
    assert(!RaphaelRestoreRamAliases(&m.S)); assert(m.Writes==writes && m.Reads==reads && m.Syncs==syncs);
    char name[100]; snprintf(name,sizeof(name),"corrupt-recovery-journal-field-%u-fails-without-I-O",i); pass(name);
  }
  m.S=saved; assert(!run(&m)); assert(m.S.Result.Dirty && m.S.Result.ArmedWords==5);
  m.Reenter=1; assert(RaphaelRestoreRamAliases(&m.S)); assert(m.Reentered); original(&m);
  pass("dirty-state-retained-for-retry-and-recovery-reentry-rejected"); destroy(&m);
}
static void inputs(void) {
  MODEL m;
  struct {char object;size_t offset;UINT64 bad;} cases[]={
    {'p',offsetof(RAPHAEL_RAM_POLICY,Version),2},{'p',offsetof(RAPHAEL_RAM_POLICY,TotalBytes),64},
    {'p',offsetof(RAPHAEL_RAM_POLICY,Base),MAX_UINT64},{'p',offsetof(RAPHAEL_RAM_POLICY,Bytes),4096},
    {'p',offsetof(RAPHAEL_RAM_POLICY,GuardCount),129},{'p',offsetof(RAPHAEL_RAM_POLICY,Guards),0x100000000ULL},
    {'b',offsetof(RAPHAEL_RAM_READ_RESULT,Status),2},{'b',offsetof(RAPHAEL_RAM_READ_RESULT,Completed),255},
    {'b',offsetof(RAPHAEL_RAM_READ_RESULT,PhysicalBits),48},{'b',offsetof(RAPHAEL_RAM_READ_RESULT,Frequency),0},
    {'b',offsetof(RAPHAEL_RAM_READ_RESULT,EndCounter),MAX_UINT64},{'b',offsetof(RAPHAEL_RAM_READ_RESULT,Sctlr),0x1005},
    {'b',offsetof(RAPHAEL_RAM_READ_RESULT,EntryGuards),0},{'b',offsetof(RAPHAEL_RAM_READ_RESULT,RamRanges),33},
    {'m',offsetof(RAPHAEL_RAM_MAPPED_RESULT,WriteDenied),255},{'m',offsetof(RAPHAEL_RAM_MAPPED_RESULT,RestoredPar),1},
    {'m',offsetof(RAPHAEL_RAM_MAPPED_RESULT,Digest),0},{'m',offsetof(RAPHAEL_RAM_MAPPED_RESULT,StartCounter),0},
    {'e',offsetof(RAPHAEL_RAM_ENTRY,Sctlr),0},{'e',offsetof(RAPHAEL_RAM_ENTRY,Daif),0},
    {'e',offsetof(RAPHAEL_RAM_ENTRY,GuardCount),9},{'e',offsetof(RAPHAEL_RAM_ENTRY,Guards),0x100000000ULL},
    {'e',offsetof(RAPHAEL_RAM_ENTRY,Mmfr0),0},{'e',offsetof(RAPHAEL_RAM_ENTRY,CurrentEl),8}};
  for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
    init(&m,3); void *obj=cases[i].object=='p'?(void*)&m.P:cases[i].object=='b'?(void*)&m.B:cases[i].object=='m'?(void*)&m.M:(void*)&m.E;
    memcpy((char*)obj+cases[i].offset,&cases[i].bad,8); assert(!run(&m)); no_io(&m); destroy(&m);
    char name[80]; snprintf(name,sizeof(name),"gate-input-%u-rejected-before-I-O",i); pass(name);
  }
  init(&m,3); m.S.Running=1; assert(!run(&m)); no_io(&m); assert(m.S.Running==1); destroy(&m); pass("active-engine-cannot-be-reentered");
  init(&m,3); m.S.Result.Dirty=1; assert(!run(&m)); no_io(&m); assert(m.S.Result.Dirty==1); destroy(&m); pass("dirty-engine-cannot-be-reinitialized");
  init(&m,3); assert(!RaphaelProbeRamAliases(&m.S,&m.P,80,&m.B,&m.M,&m.E,0,m.Backup,48,load,store,translate,sync_page,counter,&m)); no_io(&m); destroy(&m); pass("zero-page-request-rejected");
  init(&m,3); assert(!RaphaelProbeRamAliases(&m.S,&m.P,80,&m.B,&m.M,&m.E,65537,m.Backup,48,load,store,translate,sync_page,counter,&m)); no_io(&m); destroy(&m); pass("over-window-page-request-rejected");
  init(&m,3); assert(!RaphaelProbeRamAliases(&m.S,&m.P,80,&m.B,&m.M,&m.E,3,m.Backup,40,load,store,translate,sync_page,counter,&m)); no_io(&m); destroy(&m); pass("backup-must-cover-all-samples");
  init(&m,3); RAPHAEL_RAM_POLICY saved=m.P;
  assert(!RaphaelProbeRamAliases(&m.S,&m.P,80,&m.B,&m.M,&m.E,3,(UINT64*)&m.P,48,load,store,translate,sync_page,counter,&m)); no_io(&m); assert(!memcmp(&saved,&m.P,sizeof(saved))); destroy(&m); pass("backup-input-alias-rejected-before-clearing");
  init(&m,3); RAPHAEL_RAM_ALIAS_STATE state=m.S;
  assert(!RaphaelProbeRamAliases(&m.S,&m.P,80,&m.B,&m.M,&m.E,3,(UINT64*)&m.S,48,load,store,translate,sync_page,counter,&m)); no_io(&m); assert(!memcmp(&state,&m.S,sizeof(state))); destroy(&m); pass("backup-state-alias-rejected-before-clearing");
  init(&m,3); assert(!RaphaelProbeRamAliases(&m.S,&m.P,80,&m.B,&m.M,&m.E,3,(UINT64*)(UINTN)m.P.Base,48,load,store,translate,sync_page,counter,&m)); no_io(&m); destroy(&m); pass("backup-inside-candidate-window-rejected");
  init(&m,3); assert(!RaphaelProbeRamAliases(&m.S,&m.P,80,&m.B,&m.M,&m.E,3,m.Backup,48,NULL,store,translate,sync_page,counter,&m)); no_io(&m); destroy(&m); pass("missing-physical-read-callback-rejected");
}
int main(void) {
  normal(1); normal(3); normal(256);
  alias(4,2,0,"same-offset-cross-page-DRAM-alias-detected-and-restored");
  alias(4,7,0,"cross-offset-DRAM-alias-detected-and-restored");
  alias(4,1,0,"head-tail-DRAM-alias-detected-and-restored");
  alias(1024,2047,0,"distant-page-DRAM-alias-detected-and-restored");
  callback_faults(); retained_recovery(); inputs();
  MODEL m; init(&m,3); m.Cache[0]=mix(999); m.Valid[0]=m.Dirty[0]=1; m.Original[0]=m.Cache[0];
  assert(run(&m)); original(&m); pass("preexisting-dirty-cache-drained-before-backup"); destroy(&m);
  init(&m,4); m.Map[2]=0;
  m.Cache[0]=mix(777); m.Valid[0]=m.Dirty[0]=1;
  m.Cache[2]=mix(888); m.Valid[2]=m.Dirty[2]=1; m.Original[0]=m.Cache[2];
  assert(!run(&m)); assert(m.S.Result.Status==5 && m.S.Result.Reason==5); original(&m);
  pass("all-dirty-alias-lines-drained-before-first-backup"); destroy(&m);
  init(&m,3); m.SlowRestore=1; assert(!run(&m));
  assert(m.S.Result.Status==6 && m.S.Result.Reason==6 && m.S.Result.RestoredSamples==6);
  original(&m); pass("mandatory-restore-completes-before-total-deadline-rejection"); destroy(&m);
  normal(65536);
  alias(65536,131071,0,"full-window-distant-DRAM-alias-detected-and-restored");
  printf("RAM_ALIAS_HOST_OK %d\n",Cases); return 0;
}
