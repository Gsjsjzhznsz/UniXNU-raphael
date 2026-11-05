// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelNativeVideo.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/MemoryAllocationLib.h>

EFI_STATUS RaphaelNativeVideoBegin(RAPHAEL_GOP_RESULT *R,
  EFI_GRAPHICS_OUTPUT_PROTOCOL *G, UINT64 Video[6]) {
  if (!R || !G || !Video || !G->Mode || !G->Mode->Info || !G->QueryMode || !G->Blt)
    return EFI_INVALID_PARAMETER;
  if (R->Active || R->Backup) return EFI_ALREADY_STARTED;
  // All these fields originate in this entry's display/SMMU/pixel gates.
  if (R->Status != 4 || !R->MappedReadVerified || !R->ProtocolInstalled ||
      !R->Width || !R->Height || R->Width > 4096 || R->Height > 4096 ||
      R->Stride < R->Width * 4 || (R->Stride & 3) ||
      R->Stride > MAX_UINT64 / R->Height || R->Extent != R->Stride * R->Height ||
      !R->Base || (R->Base & 3) || R->Base > MAX_UINT64 - R->Extent)
    return EFI_UNSUPPORTED;
  EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *I = G->Mode->Info, *Q = NULL;
  if (G->Mode->SizeOfInfo < sizeof(*I) || G->Mode->MaxMode != 1 || G->Mode->Mode != 0 ||
      I->PixelFormat != PixelBlueGreenRedReserved8BitPerColor ||
      I->HorizontalResolution != R->Width || I->VerticalResolution != R->Height ||
      I->PixelsPerScanLine * 4ULL != R->Stride ||
      G->Mode->FrameBufferBase != R->Base || G->Mode->FrameBufferSize != R->Extent)
    return EFI_COMPROMISED_DATA;
  UINTN Size = 0;
  EFI_STATUS S = G->QueryMode(G, 0, &Size, &Q);
  if (EFI_ERROR(S)) return S;
  BOOLEAN Match = Q && Size >= sizeof(*Q) && !CompareMem(Q, I, sizeof(*I));
  if (Q) FreePool(Q);
  if (!Match) return EFI_COMPROMISED_DATA;
  UINTN Bytes = R->Width * R->Height * sizeof(UINT32);
  VOID *Backup = AllocatePool(Bytes);
  if (!Backup) return EFI_OUT_OF_RESOURCES;
  S = G->Blt(G, Backup, EfiBltVideoToBltBuffer, 0, 0, 0, 0, R->Width, R->Height, 0);
  if (EFI_ERROR(S)) { FreePool(Backup); return S; }
  // Compact rows match the existing SEC restoration helper. Keep the copy
  // active across ExitBootServices; that helper needs no boot services.
  R->Backup = (UINTN)Backup; R->PatchWidth = R->Width; R->PatchHeight = R->Height;
  R->QueryVerified = 1; R->Active = 1;
  Video[0] = R->Base; Video[1] = 1; Video[2] = R->Stride;
  Video[3] = R->Width; Video[4] = R->Height; Video[5] = 32;
  return EFI_SUCCESS;
}
BOOLEAN RaphaelNativeVideoMatches(CONST VOID *Args, CONST UINT64 Video[6]) {
  if (!Args || !Video) return FALSE;
  CONST UINT8 *A = Args;
  for (UINTN I = 0; I < 6; ++I)
    if (ReadUnaligned64((CONST VOID *)(A + 0x28 + I * 8)) != Video[I]) return FALSE;
  return TRUE;
}
