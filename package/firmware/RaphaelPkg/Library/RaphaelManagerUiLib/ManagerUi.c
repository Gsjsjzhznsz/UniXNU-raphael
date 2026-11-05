// SPDX-License-Identifier: BSD-2-Clause-Patent
// Own bounded framebuffer transaction around unchanged complete UniXNURun.
#include <Library/RaphaelManagerUiLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/MemoryAllocationLib.h>
STATIC VOID Sync(RAPHAEL_MANAGER_UI_STATE *S){S->Result.Active=S->Restore.Active;S->Result.Backup=S->Restore.Backup;S->Result.Fallback=S->Restore.RestoreFallbackUsed;}
EFI_STATUS RaphaelManagerUiBegin(RAPHAEL_MANAGER_UI_STATE *S,CONST RAPHAEL_GOP_RESULT *E,
                                BOOLEAN Input,EFI_GRAPHICS_OUTPUT_PROTOCOL *G) {
 if(!S||!E||!G||!G->Blt||!G->QueryMode||!Input||!G->Mode||!G->Mode->Info)return EFI_INVALID_PARAMETER;
 // An active or retained transaction must never lose its only original copy.
 if(S->Restore.Active||S->Restore.Backup||S->Line)return EFI_ALREADY_STARTED;
 ZeroMem(S,sizeof(*S));RAPHAEL_MANAGER_UI_RESULT *R=&S->Result;RAPHAEL_GOP_RESULT *B=&S->Restore;
 R->Version=1;
 UINTN W=E->Width,H=E->Height;
 BOOLEAN BltOnly=G->Mode->Info->PixelFormat==PixelBltOnly;
 if(!W||!H||W>4096||H>4096||E->Stride<W*4||E->Stride>MAX_UINT64/H||(!BltOnly&&E->Extent<H*E->Stride)||E->Base>MAX_UINT64-E->Extent||
    G->Mode->Info->HorizontalResolution!=W||G->Mode->Info->VerticalResolution!=H||
    G->Mode->Info->PixelsPerScanLine*4ULL!=E->Stride||(!BltOnly&&G->Mode->Info->PixelFormat!=PixelBlueGreenRedReserved8BitPerColor)||
    (BltOnly&&(E->Base||E->Extent))||
    G->Mode->FrameBufferBase!=E->Base||G->Mode->FrameBufferSize!=E->Extent)return EFI_UNSUPPORTED;
 EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *Info=NULL;UINTN Bytes=0;
 EFI_STATUS Status=G->QueryMode(G,G->Mode->Mode,&Bytes,&Info);
 if(EFI_ERROR(Status))return Status;
 BOOLEAN Match=Info&&Bytes>=sizeof(*Info)&&!CompareMem(Info,G->Mode->Info,sizeof(*Info));
 if(Info)FreePool(Info);
 if(!Match)return EFI_COMPROMISED_DATA;
 R->Status=1;R->Base=E->Base;R->Width=W;R->Height=H;R->Stride=E->Stride;R->FramePixels=W*H;R->InputReady=1;R->QueryVerified=1;R->PixelFormat=G->Mode->Info->PixelFormat;
 S->Gop=G;UINT32 *Backup=AllocatePool(W*H*4);S->Line=AllocatePool(W*4);
 if(!Backup||!S->Line){if(Backup)FreePool(Backup);if(S->Line)FreePool(S->Line);S->Line=NULL;return EFI_OUT_OF_RESOURCES;}
 Status=G->Blt(G,(VOID *)Backup,EfiBltVideoToBltBuffer,0,0,0,0,W,H,0);
 if(EFI_ERROR(Status)){FreePool(Backup);FreePool(S->Line);S->Line=NULL;return Status;}
 B->Base=E->Base;B->Width=W;B->Height=H;B->Stride=E->Stride;B->PatchWidth=W;B->PatchHeight=H;B->Backup=(UINTN)Backup;B->Active=1;
 R->Status=2;Sync(S);return EFI_SUCCESS;
}
EFI_STATUS RaphaelManagerUiFinish(RAPHAEL_MANAGER_UI_STATE *S) {
 if(!S||!S->Gop||!S->Line||!S->Restore.Active||!S->Restore.Backup)return EFI_NOT_READY;
 RAPHAEL_MANAGER_UI_RESULT *R=&S->Result;RAPHAEL_GOP_RESULT *B=&S->Restore;EFI_GRAPHICS_OUTPUT_PROTOCOL *G=S->Gop;
 UINTN W=R->Width,H=R->Height;UINT32 *Backup=(VOID *)(UINTN)B->Backup;EFI_STATUS Outcome=EFI_SUCCESS,Status;
 UINT64 Changed=0;
 R->PixelsRestored=R->Mismatches=0;B->PatchRestored=B->PatchMismatches=0;
 for(UINTN Y=0;Y<H;++Y){
  Status=G->Blt(G,(VOID *)S->Line,EfiBltVideoToBltBuffer,0,Y,0,0,W,1,0);
  if(EFI_ERROR(Status)){Outcome=Status;break;}
  for(UINTN X=0;X<W;++X)if(S->Line[X]!=Backup[Y*W+X])++Changed;
 }
 if(Changed>R->PixelsChanged)R->PixelsChanged=Changed;
 if(!EFI_ERROR(Outcome)&&!R->PixelsChanged)Outcome=EFI_COMPROMISED_DATA;
 if(R->PixelsChanged)R->Status=3;
 Status=G->Blt(G,(VOID *)Backup,EfiBltBufferToVideo,0,0,0,0,W,H,0);
 if(EFI_ERROR(Status)){Sync(S);return Status;}
 for(UINTN Y=0;Y<H;++Y){
  Status=G->Blt(G,(VOID *)S->Line,EfiBltVideoToBltBuffer,0,Y,0,0,W,1,0);
  if(EFI_ERROR(Status)){Sync(S);return Status;}
  for(UINTN X=0;X<W;++X)if(S->Line[X]==Backup[Y*W+X])++R->PixelsRestored;else ++R->Mismatches;
 }
 B->PatchRestored=R->PixelsRestored;B->PatchMismatches=R->Mismatches;
 if(R->Mismatches){Sync(S);return EFI_COMPROMISED_DATA;}
 B->Active=0;B->Backup=0;FreePool(Backup);FreePool(S->Line);S->Line=NULL;Sync(S);
 if(!EFI_ERROR(Outcome))R->Status=4;
 return Outcome;
}
