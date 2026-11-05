// SPDX-License-Identifier: BSD-2-Clause-Patent
// Diagnostic adapter to the pinned, unchanged generic UniXNU renderer.
// Its normal menu loop needs timer architectural services, still a later step.
#include <RaphaelDiagnostic.h>
#include <../Library/UniXNULib/Internal.h>
#include <Library/ArmLib.h>
STATIC UINT32 Read(UINT64 A,VOID *C){(VOID)C;ArmDataMemoryBarrier();UINT32 V=*(volatile UINT32 *)(UINTN)A;ArmDataMemoryBarrier();return V;}
STATIC VOID Write(UINT64 A,UINT32 V,VOID *C){(VOID)C;*(volatile UINT32 *)(UINTN)A=V;ArmDataSynchronizationBarrier();}
EFI_STATUS RaphaelTestMenu(RAPHAEL_DIAGNOSTIC *D) {
  EFI_GRAPHICS_OUTPUT_PROTOCOL *G=NULL;EFI_STATUS S;
  RAPHAEL_MENU_RESULT *M=&D->Menu;RAPHAEL_GOP_RESULT *R=&M->Restore;
  UNIXNU_UI Ui;UNIXNU_CONFIG Config;UNIXNU_ENTRY Entries[3];
  UINT32 *Backup=NULL,*Line=NULL;UINTN Count=D->Gop.Width*D->Gop.Height,Width=D->Gop.Width,Height=D->Gop.Height;
  if(!D->InputDxe.ProtocolInstalled||D->InputDxe.Errors||!gST->ConIn)return EFI_NOT_READY;
  S=gBS->LocateProtocol(&gEfiGraphicsOutputProtocolGuid,NULL,(VOID **)&G);if(EFI_ERROR(S)||!G)return EFI_NOT_READY;
  M->Version=1;M->Status=1;R->Base=D->Gop.Base;R->Width=Width;R->Height=Height;R->Stride=D->Gop.Stride;
  if(!Width||!Height||Width>4096||Height>4096||Count>MAX_UINTN/4)return EFI_UNSUPPORTED;
  Backup=AllocatePool(Count*4);Line=AllocatePool(Width*4);
  if(!Backup||!Line){S=EFI_OUT_OF_RESOURCES;goto Exit;}
  S=G->Blt(G,(VOID *)Backup,EfiBltVideoToBltBuffer,0,0,0,0,Width,Height,0);if(EFI_ERROR(S))goto Exit;
  R->Backup=(UINTN)Backup;R->PatchWidth=Width;R->PatchHeight=Height;R->Active=1;
  ZeroMem(&Config,sizeof(Config));ZeroMem(Entries,sizeof(Entries));
  Config.Console=UniXNUConsoleGraphics;Config.Title=L"UniXNU";Config.ShowLogo=TRUE;
  Config.Layout=UniXNULayoutAuto;Config.PortraitBelow=UNIXNU_PORTRAIT_BELOW_DEFAULT;
  Config.SourceLabel=L"Redmi K20 Pro";Config.Entries=Entries;Config.EntryCount=3;
  Entries[0].Title=L"Return to Android";Entries[1].Title=L"Key test";Entries[2].Title=L"Boot information";
  for(UINTN I=0;I<3;++I)Entries[I].Type=UniXNUEntryAction;
  UniXNUUiInit(&Config,&Ui);if(Ui.Mode!=UniXNUUiGraphics){S=EFI_NOT_READY;goto Exit;}
  UniXNUUiDrawFrame(&Ui,&Config);if(Ui.VisibleRows<3){S=EFI_UNSUPPORTED;goto Exit;}
  for(UINTN I=0;I<3;++I)UniXNUUiDrawEntry(&Ui,&Config,I,I==0);
  UniXNUUiDrawStatus(&Ui,1,L"Vol+/Vol-: select    Power: choose");
  UniXNUUiDrawStatus(&Ui,2,L"Automatic return to Android in 40 seconds");
  // Count actual changed pixels without a second full-frame allocation.
  for(UINTN Y=0;Y<Height;++Y) {
    S=G->Blt(G,(VOID *)Line,EfiBltVideoToBltBuffer,0,Y,0,0,Width,1,0);if(EFI_ERROR(S))goto Exit;
    for(UINTN X=0;X<Width;++X)if(Line[X]!=Backup[Y*Width+X])++M->PixelsChanged;
  }
  if(!M->PixelsChanged){S=EFI_COMPROMISED_DATA;goto Exit;}
  M->Status=2;M->Start=ArmReadCntPct();M->HoldTicks=D->Cntfrq*40;UINT64 LastSecond=MAX_UINT64;
  UINTN Budget=2000000000;
  for(;;) {
    M->End=ArmReadCntPct();UINT64 Elapsed=M->End-M->Start;
    if(Elapsed>=M->HoldTicks){M->ExitReason=1;break;}
    if(!--Budget){S=EFI_TIMEOUT;goto Exit;}
    UINT64 Second=Elapsed/D->Cntfrq;
    if(Second!=LastSecond) {
      CHAR16 Text[96];UnicodeSPrint(Text,sizeof(Text),L"Return to Android in %u s",(UINT32)(40-Second));
      UniXNUUiDrawStatus(&Ui,0,Text);LastSecond=Second;
    }
    S=gBS->CheckEvent(gST->ConIn->WaitForKey);
    if(S==EFI_NOT_READY)continue;
    if(EFI_ERROR(S))goto Exit;
    ++M->WaitSignals;EFI_INPUT_KEY Key;
    S=gST->ConIn->ReadKeyStroke(gST->ConIn,&Key);if(S==EFI_NOT_READY)continue;if(EFI_ERROR(S))goto Exit;
    UINTN Previous=M->Selected;
    if(Key.ScanCode==SCAN_UP){M->Selected=(M->Selected+2)%3;++M->Up;}
    if(Key.ScanCode==SCAN_DOWN){M->Selected=(M->Selected+1)%3;++M->Down;}
    if(Key.UnicodeChar==CHAR_CARRIAGE_RETURN) {
      ++M->Enter;
      if(M->Selected==0){M->ExitReason=2;break;}
      CHAR16 Info[96];UnicodeSPrint(Info,sizeof(Info),L"Inherited display %ux%u; ARM64 EL1",(UINT32)Width,(UINT32)Height);
      UniXNUUiDrawStatus(&Ui,2,M->Selected==1?L"Key test: Vol+, Vol-, Power":Info);
    }
    if(M->Selected!=Previous) {
      UniXNUUiDrawEntry(&Ui,&Config,Previous,FALSE);UniXNUUiDrawEntry(&Ui,&Config,M->Selected,TRUE);
    }
  }
  M->End=ArmReadCntPct();
  S=G->Blt(G,(VOID *)Backup,EfiBltBufferToVideo,0,0,0,0,Width,Height,0);if(EFI_ERROR(S))goto Exit;
  for(UINTN Y=0;Y<Height;++Y) {
    S=G->Blt(G,(VOID *)Line,EfiBltVideoToBltBuffer,0,Y,0,0,Width,1,0);if(EFI_ERROR(S))goto Exit;
    for(UINTN X=0;X<Width;++X)if(Line[X]==Backup[Y*Width+X])++R->PatchRestored;else ++R->PatchMismatches;
  }
  if(R->PatchMismatches){S=EFI_COMPROMISED_DATA;goto Exit;}
  R->Active=0;M->Status=3;S=EFI_SUCCESS;
Exit:
  if(R->Active)RaphaelRestoreGopPatch(R,Read,Write,NULL);
  if(Line)FreePool(Line);if(Backup&&!R->Active){FreePool(Backup);R->Backup=0;}
  DEBUG((DEBUG_INFO,"RAPHAEL menu status=%lu up/down/enter=%lu/%lu/%lu restored=%lu mismatch=%lu error=%r\n",
    M->Status,M->Up,M->Down,M->Enter,R->PatchRestored,R->PatchMismatches,S));return S;
}
