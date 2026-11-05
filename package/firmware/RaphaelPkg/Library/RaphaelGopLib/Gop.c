// SPDX-License-Identifier: BSD-2-Clause-Patent
// One inherited BGR mode; generic fills/copies use pinned Basecore Blt library.
#include <Library/RaphaelGopLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/ArmLib.h>

STATIC RAPHAEL_GOP *Owner (EFI_GRAPHICS_OUTPUT_PROTOCOL *This) {
  if (!This) return NULL;
  RAPHAEL_GOP *G=BASE_CR(This,RAPHAEL_GOP,Protocol);
  return G->Signature==RAPHAEL_GOP_SIGNATURE ? G : NULL;
}
STATIC EFI_STATUS EFIAPI Query (EFI_GRAPHICS_OUTPUT_PROTOCOL *This, UINT32 Number,
  UINTN *Size, EFI_GRAPHICS_OUTPUT_MODE_INFORMATION **Info) {
  RAPHAEL_GOP *G=Owner(This);
  if (!G || !Size || !Info) return EFI_INVALID_PARAMETER;
  if (Number) return EFI_UNSUPPORTED;
  *Info=AllocateCopyPool(sizeof(G->Info),&G->Info);
  if (!*Info) return EFI_OUT_OF_RESOURCES;
  *Size=sizeof(G->Info); return EFI_SUCCESS;
}
STATIC BOOLEAN Rectangle (UINTN X,UINTN Y,UINTN W,UINTN H, RAPHAEL_GOP *G) {
  return X<G->Info.HorizontalResolution && Y<G->Info.VerticalResolution &&
    W<=G->Info.HorizontalResolution-X && H<=G->Info.VerticalResolution-Y;
}
STATIC BOOLEAN BufferRange (EFI_GRAPHICS_OUTPUT_BLT_PIXEL *B, UINTN X, UINTN Y,
  UINTN W,UINTN H,UINTN Delta) {
  if (!B || X>MAX_UINTN/4-W || Y>MAX_UINTN-H) return FALSE;
  UINTN Row=(X+W)*4;
  if (!Delta) Delta=W*4;
  if (Delta<Row || (Delta&3) || Y+H-1>(MAX_UINTN-Row)/Delta) return FALSE;
  UINTN Bytes=(Y+H-1)*Delta+Row;
  return (UINTN)B<=MAX_UINTN-Bytes;
}
STATIC EFI_STATUS EFIAPI Blt (EFI_GRAPHICS_OUTPUT_PROTOCOL *This,
  EFI_GRAPHICS_OUTPUT_BLT_PIXEL *Buffer, EFI_GRAPHICS_OUTPUT_BLT_OPERATION Op,
  UINTN Sx,UINTN Sy,UINTN Dx,UINTN Dy,UINTN W,UINTN H,UINTN Delta) {
  RAPHAEL_GOP *G=Owner(This);
  if (!G || !G->Configure || !W || !H || W>4096 || H>4096 ||
      (UINT32)Op>=EfiGraphicsOutputBltOperationMax) return EFI_INVALID_PARAMETER;
  if ((Op==EfiBltVideoToBltBuffer || Op==EfiBltVideoToVideo) && !Rectangle(Sx,Sy,W,H,G))
    return EFI_INVALID_PARAMETER;
  if (Op!=EfiBltVideoToBltBuffer && !Rectangle(Dx,Dy,W,H,G)) return EFI_INVALID_PARAMETER;
  if ((Op==EfiBltVideoFill && !Buffer) ||
      (Op==EfiBltBufferToVideo && !BufferRange(Buffer,Sx,Sy,W,H,Delta)) ||
      (Op==EfiBltVideoToBltBuffer && !BufferRange(Buffer,Dx,Dy,W,H,Delta)))
    return EFI_INVALID_PARAMETER;
  EFI_STATUS Status;
  if (Op==EfiBltVideoToVideo) {
    // The pinned generic implementation starts descending copies one row past
    // the rectangle. Use overlap-safe CopyMem with the correct last row here.
    UINTN Stride=(UINTN)G->Info.PixelsPerScanLine*4;
    UINT8 *Base=(UINT8 *)(UINTN)G->Mode.FrameBufferBase;
    for (UINTN I=0; I<H; ++I) {
      UINTN Row=Dy>Sy ? H-1-I : I;
      CopyMem(Base+(Dy+Row)*Stride+Dx*4,Base+(Sy+Row)*Stride+Sx*4,W*4);
    }
    Status=EFI_SUCCESS;
  } else Status=FrameBufferBlt(G->Configure,Buffer,Op,Sx,Sy,Dx,Dy,W,H,Delta);
  ArmDataSynchronizationBarrier();
  return Status;
}
STATIC EFI_STATUS EFIAPI SetMode (EFI_GRAPHICS_OUTPUT_PROTOCOL *This, UINT32 Number) {
  RAPHAEL_GOP *G=Owner(This);
  EFI_GRAPHICS_OUTPUT_BLT_PIXEL Black={0,0,0,0};
  if (!G) return EFI_INVALID_PARAMETER;
  if (Number) return EFI_UNSUPPORTED;
  // Only the inherited active timing exists. GOP requires clearing a selected
  // mode; no clocks, panel commands or display registers are reprogrammed.
  return Blt(This,&Black,EfiBltVideoFill,0,0,0,0,
    G->Info.HorizontalResolution,G->Info.VerticalResolution,0);
}
RETURN_STATUS RaphaelGopConfigure (RAPHAEL_GOP *G, CONST RAPHAEL_GOP_RESULT *P,
  VOID *Configure, UINTN *Size) {
  if (!G || !P || !Size || P->Status<3 || !P->MappedReadVerified ||
      !P->Base || P->Width<64 || P->Width>4096 || P->Height<64 || P->Height>4096 ||
      (P->Base&3) || (P->Stride&3) || P->Stride<P->Width*4 || P->Stride>65536 ||
      P->Extent!=P->Stride*P->Height || P->Base>MAX_UINTN-P->Extent) return RETURN_UNSUPPORTED;
  ZeroMem(G,sizeof(*G));
  G->Info.HorizontalResolution=(UINT32)P->Width;
  G->Info.VerticalResolution=(UINT32)P->Height;
  G->Info.PixelFormat=PixelBlueGreenRedReserved8BitPerColor;
  G->Info.PixelsPerScanLine=(UINT32)(P->Stride/4);
  RETURN_STATUS Status=FrameBufferBltConfigure((VOID *)(UINTN)P->Base,&G->Info,Configure,Size);
  if (RETURN_ERROR(Status)) return Status;
  G->Signature=RAPHAEL_GOP_SIGNATURE; G->Configure=Configure;
  G->Mode.MaxMode=1; G->Mode.Info=&G->Info; G->Mode.SizeOfInfo=sizeof(G->Info);
  G->Mode.FrameBufferBase=P->Base; G->Mode.FrameBufferSize=(UINTN)P->Extent;
  G->Protocol.QueryMode=Query; G->Protocol.SetMode=SetMode; G->Protocol.Blt=Blt;
  G->Protocol.Mode=&G->Mode;
  return RETURN_SUCCESS;
}
