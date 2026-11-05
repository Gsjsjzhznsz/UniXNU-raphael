// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelDiagnostic.h>
#include <Protocol/GraphicsOutput.h>
#include <Library/ArmLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/UefiBootServicesTableLib.h>
STATIC UINT32 Read (UINT64 A,VOID *C) { (VOID)C; return *(volatile UINT32 *)(UINTN)A; }
STATIC VOID Write (UINT64 A,UINT32 V,VOID *C) {
  (VOID)C; *(volatile UINT32 *)(UINTN)A=V; ArmDataSynchronizationBarrier();
}
EFI_STATUS RaphaelTestGop (RAPHAEL_DIAGNOSTIC *D) {
  EFI_GRAPHICS_OUTPUT_PROTOCOL *G=NULL;
  RAPHAEL_GOP_RESULT *R=&D->Gop;
  EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *Info=NULL;
  UINTN Size=0, Count=256*128, Bytes=256*128*4;
  EFI_STATUS S=gBS->LocateProtocol(&gEfiGraphicsOutputProtocolGuid,NULL,(VOID **)&G);
  UINT32 *Backup=NULL,*Pattern=NULL,*Check=NULL;
  if (EFI_ERROR(S) || !G || R->Status!=4 || !R->MappedReadVerified) return EFI_NOT_READY;
  S=G->QueryMode(G,0,&Size,&Info);
  if (EFI_ERROR(S)) goto Exit;
  if (!Info || Size!=sizeof(*Info)) { S=EFI_COMPROMISED_DATA;goto Exit; }
  if (Info->HorizontalResolution!=R->Width || Info->VerticalResolution!=R->Height ||
      Info->PixelsPerScanLine!=R->Stride/4 || Info->PixelFormat!=PixelBlueGreenRedReserved8BitPerColor ||
      G->Mode->FrameBufferBase!=R->Base || G->Mode->FrameBufferSize!=R->Extent || G->Mode->MaxMode!=1) {
    S=EFI_COMPROMISED_DATA; goto Exit;
  }
  R->QueryVerified=1; FreePool(Info); Info=NULL;
  if (G->QueryMode(G,1,&Size,&Info)!=EFI_UNSUPPORTED || G->SetMode(G,1)!=EFI_UNSUPPORTED) {
    S=EFI_COMPROMISED_DATA; goto Exit;
  }
  R->InvalidModeRejected=1;
  if (R->Width<256 || R->Height<128) { S=EFI_UNSUPPORTED; goto Exit; }
  Backup=AllocatePool(Bytes); Pattern=AllocatePool(Bytes); Check=AllocatePool(Bytes);
  if (!Backup || !Pattern || !Check) { S=EFI_OUT_OF_RESOURCES; goto Exit; }
  S=G->Blt(G,(VOID *)Backup,EfiBltVideoToBltBuffer,0,0,0,0,256,128,0);
  if (EFI_ERROR(S)) goto Exit;
  R->Backup=(UINTN)Backup; R->PatchWidth=256; R->PatchHeight=128; R->Active=1;
  EFI_GRAPHICS_OUTPUT_BLT_PIXEL White={255,255,255,255};
  S=G->Blt(G,&White,EfiBltVideoFill,0,0,0,0,256,128,0); if(EFI_ERROR(S)) goto Exit;
  S=G->Blt(G,(VOID *)Check,EfiBltVideoToBltBuffer,0,0,0,0,256,128,0); if(EFI_ERROR(S)) goto Exit;
  for(UINTN I=0;I<Count;++I) if((Check[I]&0xffffffU)!=0xffffffU) { S=EFI_COMPROMISED_DATA;goto Exit; }
  R->BltChecks|=1;
  for(UINTN Y=0;Y<128;++Y) for(UINTN X=0;X<256;++X) {
    UINT32 V=X<86?0xffff0000U:X<171?0xff00ff00U:0xff0000ffU;
    if(!X || X==255 || !Y || Y==127) V=0xffffffffU;
    Pattern[Y*256+X]=V;
  }
  S=G->Blt(G,(VOID *)Pattern,EfiBltBufferToVideo,0,0,0,0,256,128,0); if(EFI_ERROR(S)) goto Exit;
  R->BltChecks|=2; R->PatchWritten=Count;
  // Exercise an actual overlapping descending video copy inside the patch.
  S=G->Blt(G,NULL,EfiBltVideoToVideo,0,0,0,1,256,126,0); if(EFI_ERROR(S)) goto Exit;
  CopyMem(Pattern+256,Pattern,256*126*4);
  R->BltChecks|=8;
  S=G->Blt(G,(VOID *)Check,EfiBltVideoToBltBuffer,0,0,0,0,256,128,0); if(EFI_ERROR(S)) goto Exit;
  for(UINTN I=0;I<Count;++I) if(Check[I]==Pattern[I]) ++R->PatchVerified;
  if(R->PatchVerified!=Count) { S=EFI_COMPROMISED_DATA;goto Exit; }
  R->BltChecks|=4; R->Status=5;
  R->Start=ArmReadCntPct(); R->HoldTicks=D->Cntfrq*10;
  UINTN Budget=1000000000;
  do {
    R->End=ArmReadCntPct();
    if(!--Budget) { S=EFI_TIMEOUT;goto Exit; }
  } while(R->End-R->Start<R->HoldTicks);
  S=G->Blt(G,(VOID *)Backup,EfiBltBufferToVideo,0,0,0,0,256,128,0); if(EFI_ERROR(S)) goto Exit;
  S=G->Blt(G,(VOID *)Check,EfiBltVideoToBltBuffer,0,0,0,0,256,128,0); if(EFI_ERROR(S)) goto Exit;
  for(UINTN I=0;I<Count;++I) {
    if(Check[I]==Backup[I]) ++R->PatchRestored; else ++R->PatchMismatches;
  }
  if(R->PatchMismatches) { S=EFI_COMPROMISED_DATA;goto Exit; }
  R->Active=0; R->Status=6; S=EFI_SUCCESS;
Exit:
  if(R->Active) RaphaelRestoreGopPatch(R,Read,Write,NULL);
  if(Info) FreePool(Info);
  if(Pattern) FreePool(Pattern);
  if(Check) FreePool(Check);
  if(Backup && !R->Active) { FreePool(Backup);R->Backup=0; }
  DEBUG((DEBUG_INFO,"RAPHAEL GOP diagnostic status=%lu blt=0x%lx verify=%lu restore=%lu error=%r\n",
    R->Status,R->BltChecks,R->PatchVerified,R->PatchRestored,S));
  return S;
}
