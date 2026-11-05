// SPDX-License-Identifier: BSD-2-Clause-Patent
// One temporary rectangle in the already sampled splash buffer. No MMIO writes.
#include <RaphaelPixelWrite.h>
STATIC UINT64 Digest (UINT64 H, UINT32 V) { return (H^V)*1099511628211ULL; }
STATIC UINT64 Address (CONST RAPHAEL_PIXEL_WRITE_RESULT *R, UINT32 I) {
  return R->Base+(I/RAPHAEL_PATCH_WIDTH)*R->Stride+(I%RAPHAEL_PATCH_WIDTH)*4;
}
STATIC UINT32 Pattern (UINT32 I) {
  UINT32 X=I%RAPHAEL_PATCH_WIDTH,Y=I/RAPHAEL_PATCH_WIDTH;
  if(X<4 || Y<4 || X>=RAPHAEL_PATCH_WIDTH-4 || Y>=RAPHAEL_PATCH_HEIGHT-4) return 0xffffffff;
  return X<RAPHAEL_PATCH_WIDTH/3 ? 0xffff0000 : X<2*RAPHAEL_PATCH_WIDTH/3 ? 0xff00ff00 : 0xff0000ff;
}
VOID RaphaelRestorePixelPatch (RAPHAEL_PIXEL_WRITE_RESULT *R,
  RAPHAEL_DISPLAY_READ32 Read, RAPHAEL_PIXEL_WRITE32 Write, VOID *Context) {
  if(!R->Active) return;
  CONST UINT32 *Backup=(CONST UINT32 *)(UINTN)R->Backup;
  R->Active=0; // Never recurse if a restoration access itself faults.
  R->RestoredDigest=14695981039346656037ULL;
  for(UINT32 I=0; I<R->Written; ++I) Write(Address(R,I),Backup[I],Context);
  for(UINT32 I=0; I<R->Written; ++I) {
    UINT32 V=Read(Address(R,I),Context);
    R->RestoredDigest=Digest(R->RestoredDigest,V);
    if(V==Backup[I]) ++R->Restored; else ++R->Mismatches;
  }
}
VOID RaphaelTestPixelPatch (CONST RAPHAEL_PIXEL_SNAPSHOT *P, RAPHAEL_PIXEL_WRITE_RESULT *R,
  RAPHAEL_DISPLAY_READ32 Read, RAPHAEL_PIXEL_WRITE32 Write,
  RAPHAEL_PIXEL_COUNTER Counter, UINT64 StackBase, UINT64 StackSize, VOID *Context) {
  UINT32 Backup[RAPHAEL_PATCH_PIXELS];
  for(UINTN I=0; I<sizeof(*R); ++I) ((UINT8 *)R)[I]=0;
  R->Version=1; R->Status=1;
  if(P->Version!=1 || P->Status!=6 || P->PixelCount!=RAPHAEL_PIXEL_GRID*RAPHAEL_PIXEL_GRID ||
     P->RefreshCount!=RAPHAEL_PIXEL_ROUNDS || P->CounterFrequency<1000 ||
     P->CounterFrequency>1000000000 || P->BaseHigh || !P->BaseLow ||
     (P->BaseLow&3) || P->Width<RAPHAEL_PATCH_WIDTH || P->Height<RAPHAEL_PATCH_HEIGHT ||
     P->Width>4096 || P->Height>4096 ||
     P->Stride<P->Width*4 || (P->Stride&3) || (UINT64)P->Stride*P->Height!=P->Extent ||
     (UINT64)P->BaseLow+P->Extent>0x100000000ULL) return;
  R->Status=2;
  UINT64 B=(UINTN)Backup;
  if(StackBase>MAX_UINT64-StackSize || B<StackBase ||
     B>MAX_UINT64-sizeof(Backup) || B+sizeof(Backup)>StackBase+StackSize) return;
  R->Backup=B; R->Base=P->BaseLow; R->Width=RAPHAEL_PATCH_WIDTH; R->Height=RAPHAEL_PATCH_HEIGHT;
  R->Stride=P->Stride; R->Count=RAPHAEL_PATCH_PIXELS;
  R->OriginalDigest=14695981039346656037ULL; R->PatternDigest=14695981039346656037ULL;
  // All originals are read and saved before the first write.
  for(UINT32 I=0; I<RAPHAEL_PATCH_PIXELS; ++I) {
    Backup[I]=Read(Address(R,I),Context); R->OriginalDigest=Digest(R->OriginalDigest,Backup[I]);
  }
  R->Status=3; R->Active=1;
  for(UINT32 I=0; I<RAPHAEL_PATCH_PIXELS; ++I) {
    R->Written=I+1; Write(Address(R,I),Pattern(I),Context);
  }
  for(UINT32 I=0; I<RAPHAEL_PATCH_PIXELS; ++I) {
    UINT32 V=Read(Address(R,I),Context); R->PatternDigest=Digest(R->PatternDigest,V);
    if(V!=Pattern(I)) { R->Status=4; goto Restore; }
    ++R->Verified;
  }
  R->Status=5; R->Start=Counter(Context); R->HoldTicks=(UINT64)P->CounterFrequency*10;
  UINT32 Budget=1000000000;
  do {
    R->End=Counter(Context);
    if(!--Budget) { R->Status=6; goto Restore; }
  } while(R->End-R->Start<R->HoldTicks);
  R->Status=7;
Restore:
  RaphaelRestorePixelPatch(R,Read,Write,Context);
  R->Backup=0;
  if(R->Restored!=R->Written || R->Mismatches || R->RestoredDigest!=R->OriginalDigest) R->Status=8;
}
