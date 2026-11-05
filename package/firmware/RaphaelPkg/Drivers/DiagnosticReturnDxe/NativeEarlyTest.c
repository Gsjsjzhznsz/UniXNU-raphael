// SPDX-License-Identifier: BSD-2-Clause-Patent
// Preserve complete early-mutable segments, with no service calls after exit.
#include <RaphaelDiagnostic.h>
#include <RaphaelNativeEarly.h>
#include <Library/BaseMemoryLib.h>
#include <Library/BaseLib.h>
#include <Library/DxeServicesLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/CacheMaintenanceLib.h>
STATIC RAPHAEL_NATIVE_EARLY_POLICY mE;
STATIC RAPHAEL_NATIVE_THREAD_POLICY mThread;
STATIC RAPHAEL_NATIVE_COMPILED_POLICY mCompiled;
STATIC RAPHAEL_NATIVE_EARLY_STATE mState;
STATIC UINT8 *mAllocation,*mBackup;
STATIC UINT8 mDelta[0x100000];
STATIC UINT64 mPanicPa[2];STATIC UINT32 mPanicOpcode[2];
STATIC_ASSERT(sizeof(mE)==384,"early policy ABI");
STATIC_ASSERT(sizeof(RAPHAEL_NATIVE_EARLY_RESULT)==640,"early result ABI");
#define GUARD 0x3152444145475052ULL
STATIC BOOLEAN Guards(VOID) {
 return mAllocation&&ReadUnaligned64((VOID *)mAllocation)==GUARD&&ReadUnaligned64((VOID *)(mAllocation+8))==mE.BackupBytes&&
 ReadUnaligned64((VOID *)(mBackup+mE.BackupBytes))==GUARD&&ReadUnaligned64((VOID *)(mBackup+mE.BackupBytes+8))==mE.BackupBytes;
}
EFI_STATUS RaphaelPrepareNativeEarly(VOID) {
 EFI_GUID Guid={0x3d7c6c2f,0x3c93,0x41f6,{0x8a,0x43,0xe6,0x3f,0xe3,0xea,0x80,0x78}};
 VOID *Raw;UINTN Bytes;EFI_STATUS S=GetSectionFromAnyFv(&Guid,EFI_SECTION_RAW,0,&Raw,&Bytes);if(EFI_ERROR(S))return S;
 if(Bytes<128)return EFI_COMPROMISED_DATA;CopyMem(&mE,Raw,128);
 if(mE.Count!=(mE.Version>=9?8:mE.Version>=8?5:3))return EFI_COMPROMISED_DATA;
 UINTN PolicyBytes=128+(UINTN)mE.Count*sizeof(mE.Ranges[0]);
 if(Bytes<PolicyBytes)return EFI_COMPROMISED_DATA;CopyMem(mE.Ranges,(UINT8 *)Raw+128,PolicyBytes-128);
 if(Bytes!=PolicyBytes+(mE.Version>=5?sizeof(mThread):0)+(mE.Version>=7?sizeof(mCompiled):0))return EFI_COMPROMISED_DATA;
 if(mE.Version>=5){
  CopyMem(&mThread,(UINT8 *)Raw+PolicyBytes,sizeof(mThread));
  if(mThread.BaseOffset>=4096||mThread.TopOffset>=4096||(mThread.BaseOffset&7)||(mThread.TopOffset&7)||
   mThread.ContextBytes!=208||!RaphaelNativeMemoryRange(RaphaelNativePhysical(mThread.SizeVa),8))return EFI_COMPROMISED_DATA;
 }
 if(mE.Version>=7){
  CopyMem(&mCompiled,(UINT8 *)Raw+PolicyBytes+sizeof(mThread),sizeof(mCompiled));
  if(!mCompiled.Bytes||mCompiled.Bytes>2048||(mCompiled.Config&7)||
    !RaphaelNativeMemoryRange(RaphaelNativePhysical(mCompiled.Config),128)||
    !RaphaelNativeEntryRange(RaphaelNativePhysical(mCompiled.Relay),mCompiled.Bytes)||
    mCompiled.Body<mCompiled.Relay||mCompiled.Body>=mCompiled.Relay+mCompiled.Bytes)return EFI_COMPROMISED_DATA;
 }
 if(mE.Magic!=SIGNATURE_64('R','P','H','E','A','R','0','1')||mE.Version!=(FixedPcdGetBool(PcdRaphaelNativePlatformTest)?(mE.Reserved[2]>=17?(mE.Count==8?9:8):mE.Reserved[2]>=15?7:mE.Reserved[2]==14?6:mE.Reserved[2]>=11?5:(mE.Reserved[2]>=7&&mE.Reserved[2]<=10)?4:3):FixedPcdGetBool(PcdRaphaelNativePmapTest)?2:1)||mE.Count!=(mE.Version>=9?8:mE.Version>=8?5:3)||mE.BackupBytes>(mE.Version>=9?12:3)*SIZE_1MB||!mE.BackupBytes||mE.DeltaCapacity!=(mE.Version>=9?sizeof(mDelta):mE.Version>=4?0x80000:0x40000)||mE.Flags!=mE.Version||
 (!FixedPcdGetBool(PcdRaphaelNativePlatformTest)&&(mE.Reserved[0]||mE.Reserved[1]||mE.Reserved[2]))||mE.ArgsBytes!=0x480||mE.FrameBytes!=(mE.Version>=5?(mE.Reserved[2]==11?0:mE.Reserved[2]==19?368:mE.Reserved[2]==20?mE.FrameBytes:80):mE.Version==4?304:208)||mE.Opcode>MAX_UINT32||
 !RaphaelNativeEntryRange(RaphaelNativePhysical(mE.Checkpoint),4)||!RaphaelNativeEntryRange(RaphaelNativePhysical(mE.ReturnVa),4)||
 !RaphaelNativeMemoryRange(RaphaelNativePhysical(mE.ConstArgs),mE.ArgsBytes)||!RaphaelNativeMemoryRange(RaphaelNativePhysical(mE.BootArgs),8))return EFI_COMPROMISED_DATA;
 if(FixedPcdGetBool(PcdRaphaelNativePlatformTest)){
  if(mE.Reserved[2]>20)return EFI_COMPROMISED_DATA;
  if(mE.Reserved[2]==20&&(mE.FrameBytes<16||mE.FrameBytes>256||(mE.FrameBytes&15)))return EFI_COMPROMISED_DATA;
  if(mE.Version>=8){
   if(!RaphaelNativeMemoryRange(RaphaelNativePhysical(mE.Reserved[0]),8)||!mE.Reserved[1]||mE.Reserved[1]>65536||(mE.Reserved[1]&4095))return EFI_COMPROMISED_DATA;
  }else for(UINTN I=0;I<2;++I){mPanicPa[I]=RaphaelNativePhysical(mE.Reserved[I]);if(!RaphaelNativeEntryRange(mPanicPa[I],4))return EFI_COMPROMISED_DATA;}
 }
 UINT64 Total=0;
 for(UINTN I=0;I<mE.Count;++I){RAPHAEL_NATIVE_EARLY_RANGE *T=&mE.Ranges[I];
  if(!T->Bytes||(T->Bytes&4095)||(T->Virtual&4095)||T->Crc>MAX_UINT32||
    !RaphaelNativeBackupRange(RaphaelNativePhysical(T->Virtual),T->Bytes,T->FileBytes,mE.Version>=8&&I>=3)||T->Bytes>mE.BackupBytes-Total)return EFI_COMPROMISED_DATA;
  for(UINTN J=0;J<I;++J)if(T->Virtual<mE.Ranges[J].Virtual+mE.Ranges[J].Bytes&&mE.Ranges[J].Virtual<T->Virtual+T->Bytes)return EFI_COMPROMISED_DATA;
  Total+=T->Bytes;
 }
 if(Total!=mE.BackupBytes)return EFI_COMPROMISED_DATA;
 mAllocation=AllocatePool((UINTN)mE.BackupBytes+32);if(!mAllocation)return EFI_OUT_OF_RESOURCES;mBackup=mAllocation+16;
 UINT64 Arena=FixedPcdGet64(PcdRaphaelArenaBase),Heap=FixedPcdGet32(PcdRaphaelArenaSize)-RAPHAEL_NATIVE_FAT_BYTES,At=(UINTN)mAllocation;
 if(At<Arena||At-Arena>Heap||mE.BackupBytes+32>Heap-(At-Arena))return EFI_COMPROMISED_DATA;
 WriteUnaligned64((VOID *)mAllocation,GUARD);WriteUnaligned64((VOID *)(mAllocation+8),mE.BackupBytes);
 WriteUnaligned64((VOID *)(mBackup+mE.BackupBytes),GUARD);WriteUnaligned64((VOID *)(mBackup+mE.BackupBytes+8),mE.BackupBytes);
 return EFI_SUCCESS;
}
EFI_STATUS RaphaelSaveNativeEarly(UINT64 Args) {
 if(!Guards())return EFI_COMPROMISED_DATA;RAPHAEL_NATIVE_EARLY_RESULT *R=&mState.Result;ZeroMem(R,sizeof(*R));
 R->Version=mE.Version;R->Status=1;R->CheckpointVa=mE.Checkpoint;R->ReturnVa=mE.ReturnVa;R->ConstArgsVa=mE.ConstArgs;R->OriginalArgsPa=Args;R->ArgsBytes=mE.ArgsBytes;
 R->BackupBase=(UINTN)mBackup;R->BackupBytes=mE.BackupBytes;mState.Delta=(UINTN)mDelta;
 UINTN Offset=0;
 for(UINTN I=0;I<mE.Count;++I){RAPHAEL_NATIVE_EARLY_RANGE *T=&mE.Ranges[I];RAPHAEL_NATIVE_EARLY_RANGE_RESULT *D=&R->Ranges[I];
  D->Virtual=T->Virtual;D->Physical=RaphaelNativePhysical(T->Virtual);D->Bytes=T->Bytes;
  CopyMem(mBackup+Offset,(VOID *)(UINTN)D->Physical,(UINTN)T->Bytes);D->CrcBefore=CalculateCrc32(mBackup+Offset,(UINTN)T->Bytes);
  if(D->CrcBefore!=T->Crc)return EFI_COMPROMISED_DATA;Offset+=(UINTN)T->Bytes;++R->SavedRanges;
 }
 WriteBackDataCacheRange(mBackup,(UINTN)mE.BackupBytes);return Guards()?EFI_SUCCESS:EFI_COMPROMISED_DATA;
}
BOOLEAN RaphaelNativeEarlyArgs(UINT64 X0,UINT64 X1,UINT64 Args) {
 RAPHAEL_NATIVE_EARLY_RESULT *R=&mState.Result;
 R->ArgsCopyOk=(FixedPcdGetBool(PcdRaphaelNativePlatformTest)?(mE.Reserved[2]!=0||X0==mE.ConstArgs):(FixedPcdGetBool(PcdRaphaelNativePmapTest)||(X0==0&&X1==mE.ConstArgs)))&&ReadUnaligned64((VOID *)(UINTN)RaphaelNativePhysical(mE.BootArgs))==mE.ConstArgs&&
 CompareMem((VOID *)(UINTN)RaphaelNativePhysical(mE.ConstArgs),(VOID *)(UINTN)Args,(UINTN)mE.ArgsBytes)==0;
 return R->ArgsCopyOk;
}
BOOLEAN RaphaelRestoreNativeEarly(VOID) {
 RAPHAEL_NATIVE_EARLY_RESULT *R=&mState.Result;BOOLEAN Valid=Guards()&&R->SavedRanges==mE.Count;UINTN Offset=0;
 for(UINTN I=0;I<mE.Count;++I){RAPHAEL_NATIVE_EARLY_RANGE *T=&mE.Ranges[I];RAPHAEL_NATIVE_EARLY_RANGE_RESULT *D=&R->Ranges[I];
  CONST UINT8 *Data=(VOID *)(UINTN)D->Physical;D->CrcAfter=CalculateCrc32((VOID *)Data,(UINTN)D->Bytes);
  for(UINTN J=0;J<D->Bytes;J+=8)if(ReadUnaligned64((VOID *)(mBackup+Offset+J))!=ReadUnaligned64((VOID *)(Data+J))){
   ++D->ChangedWords;
   if(R->DeltaBytes+12>mE.DeltaCapacity){R->DeltaOverflow=1;Valid=FALSE;continue;}
   WriteUnaligned32((VOID *)(mDelta+R->DeltaBytes),(UINT32)(Offset+J));WriteUnaligned64((VOID *)(mDelta+R->DeltaBytes+4),ReadUnaligned64((VOID *)(Data+J)));R->DeltaBytes+=12;++R->DeltaWords;
  }
  D->BackupOk=Guards()&&CalculateCrc32(mBackup+Offset,(UINTN)D->Bytes)==T->Crc;
  if(D->BackupOk){CopyMem((VOID *)(UINTN)D->Physical,mBackup+Offset,(UINTN)D->Bytes);WriteBackDataCacheRange((VOID *)(UINTN)D->Physical,(UINTN)D->Bytes);D->CrcRestored=CalculateCrc32((VOID *)(UINTN)D->Physical,(UINTN)D->Bytes);if(D->CrcRestored==T->Crc)++R->RestoredRanges;else Valid=FALSE;}else Valid=FALSE;
  Offset+=(UINTN)D->Bytes;
 }
 if(FixedPcdGetBool(PcdRaphaelNativePlatformTest)&&mE.Version<7)for(UINTN I=0;I<2;++I){
  WriteUnaligned32((VOID *)(UINTN)mPanicPa[I],mPanicOpcode[I]);WriteBackDataCacheRange((VOID *)(UINTN)mPanicPa[I],4);InvalidateInstructionCacheRange((VOID *)(UINTN)mPanicPa[I],4);
 }
 Valid=Valid&&R->RestoredRanges==mE.Count&&R->ArgsCopyOk;R->Status=Valid?3:2;R->Error=Valid?0:1;return Valid;
}
UINT64 RaphaelNativeEarlyCheckpoint(VOID){return mE.Checkpoint;}
UINT64 RaphaelNativeEarlyOpcode(VOID){return mE.Opcode;}
UINT64 RaphaelNativeEarlyReturn(VOID){return mE.ReturnVa;}
UINT64 RaphaelNativeEarlyFrame(VOID){return mE.FrameBytes;}
UINT64 RaphaelNativeEarlyState(VOID){return (UINTN)&mState;}

UINT64 RaphaelNativePlatformStop(VOID){return mE.Reserved[2];}
VOID RaphaelArmNativePanics(VOID){
 if(!FixedPcdGetBool(PcdRaphaelNativePlatformTest)||mE.Version>=7)return;
 for(UINTN I=0;I<2;++I){mPanicOpcode[I]=ReadUnaligned32((VOID *)(UINTN)mPanicPa[I]);WriteUnaligned32((VOID *)(UINTN)mPanicPa[I],0xd42a6a60U);WriteBackDataCacheRange((VOID *)(UINTN)mPanicPa[I],4);InvalidateInstructionCacheRange((VOID *)(UINTN)mPanicPa[I],4);}
}

BOOLEAN RaphaelNativeEarlyStack(UINT64 Thread,UINT64 Sp,UINT64 Continuation){
 if(mE.Version<5)return FALSE;
 RAPHAEL_NATIVE_THREAD_RESULT *T=&mState.Thread;ZeroMem(T,sizeof(*T));T->Version=1;T->Status=2;T->ThreadVa=Thread;
 if((mE.Reserved[2]==11&&Continuation!=mE.Checkpoint)||(Thread&7)||Thread+4096<Thread)return FALSE;
 if(!RaphaelNativePmapRead(Thread,1,NULL,&T->ThreadPa)||
  !RaphaelNativePmapRead(Thread+mThread.BaseOffset,8,&T->StackBase,&T->BaseFieldPa)||
  !RaphaelNativePmapRead(Thread+mThread.TopOffset,8,&T->StackTop,&T->TopFieldPa))return FALSE;
 T->StackBytes=ReadUnaligned64((VOID *)(UINTN)RaphaelNativePhysical(mThread.SizeVa));
 if(T->StackBytes<4096||T->StackBytes>65536||(T->StackBytes&4095)||(T->StackBase&4095)||
  T->StackBase+T->StackBytes<T->StackBase||Sp+mE.FrameBytes<Sp||Sp+mE.FrameBytes!=T->StackTop||
  T->StackTop!=T->StackBase+T->StackBytes-mThread.ContextBytes)return FALSE;
 UINT64 Pages[16];
 for(UINTN I=0;I<T->StackBytes/4096;++I){
  if(!RaphaelNativePmapRead(T->StackBase+I*4096,4096,NULL,&Pages[I]))return FALSE;
  for(UINTN J=0;J<I;++J)if(Pages[J]==Pages[I])return FALSE;
  ++T->StackPages;
 }
 T->FirstPa=Pages[0];T->LastPa=Pages[T->StackPages-1];T->Status=3;return TRUE;
}

CONST RAPHAEL_NATIVE_COMPILED_POLICY *RaphaelNativeCompiledPolicy(VOID){return mE.Version>=7?&mCompiled:NULL;}

BOOLEAN RaphaelNativeEarlyExceptionStack(UINT64 Sp){
 if(mE.Version<8)return FALSE;
 RAPHAEL_NATIVE_EXCEPTION_RESULT *T=&mState.Exception;ZeroMem(T,sizeof(*T));
 T->Version=1;T->Status=2;T->FieldVa=mE.Reserved[0];T->Bytes=mE.Reserved[1];
 if(!RaphaelNativePmapRead(T->FieldVa,8,&T->Top,&T->FieldPa)||T->Top!=Sp||
   T->Top<T->Bytes||(T->Top&4095))return FALSE;
 UINT64 Pages[16];
 for(UINTN I=0;I<T->Bytes/4096;++I){
  if(!RaphaelNativePmapRead(T->Top-T->Bytes+I*4096,4096,NULL,&Pages[I]))return FALSE;
  for(UINTN J=0;J<I;++J)if(Pages[J]==Pages[I])return FALSE;
 }
 T->FirstPa=Pages[0];T->LastPa=Pages[T->Bytes/4096-1];T->Status=3;return TRUE;
}
