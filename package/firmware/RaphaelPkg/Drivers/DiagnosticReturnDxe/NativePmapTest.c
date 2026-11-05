// SPDX-License-Identifier: BSD-2-Clause-Patent
// Independent, exact-grant TTBR0 transition and bounded sparse pmap evidence.
#include <RaphaelDiagnostic.h>
#include <RaphaelNativePmap.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/CacheMaintenanceLib.h>
#define TABLE_MASK 0x0000fffffffff000ULL
#define TABLE_BYTES (4*EFI_PAGE_SIZE)
#define PAGE_LIMIT 256
STATIC RAPHAEL_NATIVE_PMAP_STATE mState;
STATIC UINT64 *mTransition;
// The longer PID1 observer exhausted the historical 128 KiB buffer after
// 109 pages. Keep the full graph mandatory within a checked 512 KiB bound.
STATIC UINT8 mSparse[RAPHAEL_NATIVE_PMAP_SPARSE_BYTES],mAdtBefore[65536],mAdtAfter[65536];
STATIC UINT64 mBase,mBytes,mRelay;
STATIC struct {UINT64 Physical;UINTN Level;} mPages[PAGE_LIMIT];
STATIC_ASSERT(sizeof(RAPHAEL_NATIVE_PMAP_RESULT)==256,"pmap wire ABI");
STATIC_ASSERT(OFFSET_OF(RAPHAEL_NATIVE_PMAP_RESULT,ObservedTransitionTtbr0)==80,"relay pmap ABI");
STATIC BOOLEAN Owned(UINT64 P,UINT64 N){return N&&P>=mBase&&P-mBase<=mBytes&&N<=mBytes-(P-mBase);}
EFI_STATUS RaphaelPrepareNativePmap(VOID){
 mTransition=AllocatePages(4);if(!mTransition)return EFI_OUT_OF_RESOURCES;
 UINT64 Arena=FixedPcdGet64(PcdRaphaelArenaBase),Heap=FixedPcdGet32(PcdRaphaelArenaSize)-RAPHAEL_NATIVE_FAT_BYTES,At=(UINTN)mTransition;
 if(At<Arena||At-Arena>Heap||TABLE_BYTES>Heap-(At-Arena)||(At&4095))return EFI_COMPROMISED_DATA;
 return EFI_SUCCESS;
}
EFI_STATUS RaphaelArmNativePmap(UINT64 Base,UINT64 Bytes,UINT64 Relay,UINT64 RelayBytes,UINT64 Tcr,UINT64 Args){
 // No mapping outside the actual loader allocation; at most one L1 entry.
 if(!mTransition||(Base&4095)||(Bytes&4095)||(Bytes!=SIZE_256MB&&Bytes!=SIZE_512MB&&Bytes!=704ULL*SIZE_1MB)||Base+Bytes<Base||((Base>>30)!=((Base+Bytes-1)>>30))||
  Relay<Base||Relay>=Base+Bytes||!RelayBytes||RelayBytes>2048||RelayBytes>Base+Bytes-Relay||(Tcr&63)!=26||((Tcr>>16)&63)!=26||((Tcr>>14)&3)||((Tcr>>30)&3)!=2)return EFI_COMPROMISED_DATA;
 mBase=Base;mBytes=Bytes;mRelay=Relay;ZeroMem(&mState,sizeof(mState));ZeroMem(mTransition,TABLE_BYTES);
 UINT64 Root=(UINTN)mTransition,L2=Root+4096;UINTN Partial=2;
 mTransition[(Base>>30)&255]=L2|3;
 UINT64 First=Base&~0x1fffffULL,End=Base+Bytes;
 for(UINT64 Block=First;Block<End;Block+=SIZE_2MB){
  UINT64 Flags=0x0040000000000601ULL;if(!RaphaelNativeRelayBlock(Block,Relay,RelayBytes))Flags|=1ULL<<53;
  if(Block>=Base&&End-Block>=SIZE_2MB)mTransition[512+((Block>>21)&511)]=Block|Flags;
  else {
   if(Partial>=4)return EFI_COMPROMISED_DATA;UINT64 L3=Root+Partial*4096;mTransition[512+((Block>>21)&511)]=L3|3;
   for(UINTN J=0;J<512;++J){UINT64 P=Block+J*4096;if(Owned(P,4096))mTransition[Partial*512+J]=P|(Flags|2);}
   ++Partial;
  }
 }
 RAPHAEL_NATIVE_PMAP_RESULT *R=&mState.Result;R->Version=1;R->Status=1;R->TransitionBase=Root;R->TransitionBytes=TABLE_BYTES;R->TransitionCrcBefore=CalculateCrc32(mTransition,TABLE_BYTES);
 R->CleanBase=Base;R->CleanBytes=Bytes;R->SparseCapacity=sizeof(mSparse);mState.Sparse=(UINTN)mSparse;
 if(!Owned(Args,4096))return EFI_COMPROMISED_DATA;R->AdtPhysical=Args+4096;R->AdtBytes=ReadUnaligned32((VOID *)(UINTN)(Args+0x68));
 if(!R->AdtBytes||R->AdtBytes>sizeof(mAdtBefore)||!Owned(R->AdtPhysical,R->AdtBytes)||
  ReadUnaligned64((VOID *)(UINTN)(Args+0x60))!=ReadUnaligned64((VOID *)(UINTN)(Args+8))+R->AdtPhysical-Base)return EFI_COMPROMISED_DATA;
 CopyMem(mAdtBefore,(VOID *)(UINTN)R->AdtPhysical,(UINTN)R->AdtBytes);R->AdtCrcBefore=CalculateCrc32(mAdtBefore,(UINTN)R->AdtBytes);mState.AdtSnapshot=(UINTN)mAdtAfter;
 WriteBackDataCacheRange(mAdtBefore,(UINTN)R->AdtBytes);WriteBackDataCacheRange(mTransition,TABLE_BYTES);return EFI_SUCCESS;
}
UINT64 RaphaelNativePmapRoot(VOID){return (UINTN)mTransition;}
UINT64 RaphaelNativePmapState(VOID){return (UINTN)&mState;}
STATIC BOOLEAN Visit(UINT64 P,UINTN Level){
 RAPHAEL_NATIVE_PMAP_RESULT *R=&mState.Result;
 if(P&4095||!Owned(P,4096)||Level<1||Level>3)return FALSE;
 for(UINTN I=0;I<R->TablePages;++I)if(mPages[I].Physical==P)return mPages[I].Level==Level;
 if(R->TablePages>=PAGE_LIMIT||R->SparseBytes+16>sizeof(mSparse))return FALSE;
 mPages[R->TablePages].Physical=P;mPages[R->TablePages].Level=Level;++R->TablePages;
 CONST UINT64 *Page=(VOID *)(UINTN)P;UINTN Count=0;for(UINTN I=0;I<512;++I)if(Page[I])++Count;
 if(Count*10>sizeof(mSparse)-R->SparseBytes-16)return FALSE;
 UINT32 Crc=CalculateCrc32((VOID *)Page,4096);R->TableCrcXor^=Crc;UINT8 *At=mSparse+R->SparseBytes;
 WriteUnaligned64((VOID *)At,P);WriteUnaligned16((VOID *)(At+8),(UINT16)Level);WriteUnaligned16((VOID *)(At+10),(UINT16)Count);WriteUnaligned32((VOID *)(At+12),Crc);At+=16;
 for(UINTN I=0;I<512;++I)if(Page[I]){WriteUnaligned16((VOID *)At,(UINT16)I);WriteUnaligned64((VOID *)(At+2),Page[I]);At+=10;++R->NonzeroDescriptors;}
 R->SparseBytes+=16+Count*10;
 for(UINTN I=0;I<512;++I){UINT64 V=Page[I];if(!V)continue;if(!(V&1))return FALSE;
  if(Level<3&&(V&3)==3){if(!Visit(V&TABLE_MASK,Level+1))return FALSE;}
  else if((V&3)!=(Level==3?3:1))return FALSE;
 }
 return TRUE;
}
STATIC BOOLEAN Walk(UINT64 Root,UINT64 Va,UINT64 *Pa){
 Va&=(1ULL<<38)-1;UINT64 P=Root&TABLE_MASK;
 for(UINTN Level=1;Level<=3;++Level){
  BOOLEAN Seen=FALSE;for(UINTN I=0;I<mState.Result.TablePages;++I)if(mPages[I].Physical==P&&mPages[I].Level==Level)Seen=TRUE;
  if(!Seen)return FALSE;UINTN Shift=12+9*(3-Level);UINT64 V=((CONST UINT64 *)(UINTN)P)[(Va>>Shift)&511];if(!(V&1))return FALSE;
  if(Level<3&&(V&3)==3){P=V&TABLE_MASK;continue;}
  if((V&3)!=(Level==3?3:1))return FALSE;UINT64 Mask=(1ULL<<Shift)-1;*Pa=(V&TABLE_MASK&~Mask)|(Va&Mask);return TRUE;
 }
 return FALSE;
}
BOOLEAN RaphaelCaptureNativePmap(UINT64 Root0,UINT64 Root1,UINT64 Checkpoint,UINT64 *Physical){
 RAPHAEL_NATIVE_PMAP_RESULT *R=&mState.Result;R->OriginalTtbr0=Root0;R->OriginalTtbr1=Root1;
 R->TransitionCrcAfter=CalculateCrc32(mTransition,TABLE_BYTES);R->TransitionOk=R->TransitionCrcAfter==R->TransitionCrcBefore&&R->ObservedTransitionTtbr0==R->TransitionBase;
 BOOLEAN Valid=!(Root0&4095)&&!(Root1&4095)&&Root0!=Root1&&Visit(Root0,1)&&Visit(Root1,1);R->CaptureOk=Valid;
 UINT64 Pa=0;if(Valid){
  R->Root0Empty=TRUE;for(UINTN I=0;I<512;++I)if(((CONST UINT64 *)(UINTN)Root0)[I])R->Root0Empty=FALSE;
  R->RelayUnmapped=!Walk(Root0,mRelay,&Pa);
  RAPHAEL_NATIVE_EARLY_STATE *E=(VOID *)(UINTN)RaphaelNativeEarlyState();
  for(UINTN I=0;I<E->Result.SavedRanges;++I)for(UINTN J=0;J<E->Result.Ranges[I].Bytes;J+=4096){UINT64 Va=E->Result.Ranges[I].Virtual+J;if(Walk(Root1,Va,&Pa)&&Pa==RaphaelNativePhysical(Va))++R->HighDataPages;else Valid=FALSE;}
  UINT64 Probes[]={Checkpoint,0,0};
  // Original vector locations are passed via the MMU state rather than guessed.
  extern UINT64 RaphaelNativeLowVectorVa(VOID);extern UINT64 RaphaelNativeHighVectorVa(VOID);
  Probes[1]=RaphaelNativeLowVectorVa();Probes[2]=RaphaelNativeHighVectorVa();
  for(UINTN I=0;I<ARRAY_SIZE(Probes);++I)if(Walk(Root1,Probes[I],&Pa)&&Pa==RaphaelNativePhysical(Probes[I]))++R->HighProbes;else Valid=FALSE;
  if(!Walk(Root1,Checkpoint,Physical))Valid=FALSE;
 }
 CopyMem(mAdtAfter,(VOID *)(UINTN)R->AdtPhysical,(UINTN)R->AdtBytes);R->AdtCrcAfter=CalculateCrc32(mAdtAfter,(UINTN)R->AdtBytes);
 for(UINTN I=0;I<R->AdtBytes;++I)if(mAdtBefore[I]!=mAdtAfter[I])++R->AdtChangedBytes;
 R->AdtBackupOk=CalculateCrc32(mAdtBefore,(UINTN)R->AdtBytes)==R->AdtCrcBefore;
 if(R->AdtBackupOk){CopyMem((VOID *)(UINTN)R->AdtPhysical,mAdtBefore,(UINTN)R->AdtBytes);WriteBackDataCacheRange((VOID *)(UINTN)R->AdtPhysical,(UINTN)R->AdtBytes);R->AdtCrcRestored=CalculateCrc32((VOID *)(UINTN)R->AdtPhysical,(UINTN)R->AdtBytes);R->AdtRestored=R->AdtCrcRestored==R->AdtCrcBefore;}
 Valid=Valid&&R->AdtRestored&&R->TransitionOk&&R->Root0Empty&&R->RelayUnmapped&&R->HighProbes==3;R->Status=Valid?3:2;R->Error=Valid?0:1;return Valid;
}

// Only after capturing and validating the active table graph. Never use the
// old linear kernel alias for a dynamically allocated thread or stack.
BOOLEAN RaphaelNativePmapRead(UINT64 Va,UINTN Bytes,VOID *Out,UINT64 *Pa){
 if(mState.Result.Status!=3||!Bytes||Bytes>4096||(Va>>38)!=0x3ffffffULL||
  Bytes>4096-(Va&4095)||!Walk(mState.Result.OriginalTtbr1,Va,Pa)||!Owned(*Pa,Bytes))return FALSE;
 if(Out)CopyMem(Out,(VOID *)(UINTN)*Pa,Bytes);return TRUE;
}
