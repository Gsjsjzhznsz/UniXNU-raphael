// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelFramebuffer.h>
BOOLEAN RaphaelFramebufferPlan (CONST RAPHAEL_PIXEL_SNAPSHOT *P, UINT64 Start,
  UINT64 End, RAPHAEL_GOP_RESULT *O) {
  if (!O) return FALSE;
  for (UINTN I=0; I<sizeof(*O); ++I) ((UINT8 *)O)[I]=0;
  O->Version=1; O->Status=1;
  if (!P || P->Version!=1 || P->Status!=6 || P->BaseHigh || !P->BaseLow ||
      P->Width<64 || P->Width>4096 || P->Height<64 || P->Height>4096 ||
      (P->BaseLow&3) || (P->Stride&3) || P->Stride<P->Width*4 || P->Stride>65536 ||
      P->Extent!=(UINT64)P->Stride*P->Height ||
      P->PixelCount!=RAPHAEL_PIXEL_GRID*RAPHAEL_PIXEL_GRID ||
      P->RefreshCount!=RAPHAEL_PIXEL_ROUNDS || Start>=End) return FALSE;
  UINT64 Limit=(UINT64)P->BaseLow+P->Extent;
  if (Limit>0x100000000ULL) return FALSE;
  O->MapBase=P->BaseLow&~4095ULL;
  O->MapSize=((Limit+4095)&~4095ULL)-O->MapBase;
  if (O->MapBase<End && O->MapBase+O->MapSize>Start) {
    O->MapBase=O->MapSize=0; return FALSE;
  }
  O->Base=P->BaseLow; O->Width=P->Width; O->Height=P->Height;
  O->Stride=P->Stride; O->Extent=P->Extent; O->Status=2;
  return TRUE;
}
BOOLEAN RaphaelFramebufferPlanRanges(CONST RAPHAEL_PIXEL_SNAPSHOT *P,
  CONST RAPHAEL_FRAMEBUFFER_GUARD *Guards, UINTN Count, RAPHAEL_GOP_RESULT *O) {
  if (!O) return FALSE;
  for (UINTN I=0; I<sizeof(*O); ++I) ((UINT8 *)O)[I]=0;
  O->Version=1; O->Status=1;
  if (!Guards || !Count || Count>16) return FALSE;
  for (UINTN I=0; I<Count; ++I) {
    if (!Guards[I].Bytes || Guards[I].Base>MAX_UINT64-Guards[I].Bytes) return FALSE;
  }
  for (UINTN I=0; I<Count; ++I)
    if (!RaphaelFramebufferPlan(P,Guards[I].Base,Guards[I].Base+Guards[I].Bytes,O)) return FALSE;
  return TRUE;
}
VOID RaphaelRestoreGopPatch (RAPHAEL_GOP_RESULT *R, RAPHAEL_DISPLAY_READ32 Read,
  VOID (*Write)(UINT64,UINT32,VOID *), VOID *Context) {
  if (!R || !R->Active || !R->Backup || !Read || !Write) return;
  CONST UINT32 *Saved=(CONST UINT32 *)(UINTN)R->Backup;
  R->PatchRestored=0; R->PatchMismatches=0;
  // Patch geometry is fixed before Active; only this helper and the DXE test
  // own these fields. Backup remains live until Active is cleared.
  if (!R->PatchWidth || R->PatchWidth>R->Width || !R->PatchHeight || R->PatchHeight>R->Height)
    return;
  for (UINTN Y=0; Y<R->PatchHeight; ++Y) for (UINTN X=0; X<R->PatchWidth; ++X)
    Write(R->Base+Y*R->Stride+X*4,Saved[Y*R->PatchWidth+X],Context);
  for (UINTN Y=0; Y<R->PatchHeight; ++Y) for (UINTN X=0; X<R->PatchWidth; ++X) {
    if (Read(R->Base+Y*R->Stride+X*4,Context)==Saved[Y*R->PatchWidth+X]) ++R->PatchRestored;
    else ++R->PatchMismatches;
  }
  R->RestoreFallbackUsed=1; if(!R->PatchMismatches) R->Active=0;
}
