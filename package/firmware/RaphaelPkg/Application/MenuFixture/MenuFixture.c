// SPDX-License-Identifier: BSD-2-Clause-Patent
// AAVMF-only positive renderer fixture. Input is explicitly synthetic.
#include <RaphaelDiagnostic.h>
#include <Protocol/GraphicsOutput.h>
#include <Protocol/SimpleTextIn.h>
#include <Library/ArmLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiLib.h>
extern EFI_STATUS RaphaelTestMenu(RAPHAEL_DIAGNOSTIC *D);
STATIC UINT64 Start,Frequency;STATIC UINTN Step;STATIC EFI_SIMPLE_TEXT_INPUT_PROTOCOL Input;
STATIC EFI_STATUS EFIAPI Reset(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This,BOOLEAN Extended){(VOID)This;(VOID)Extended;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI Read(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This,EFI_INPUT_KEY *K){
  if(This!=&Input||!K)return EFI_INVALID_PARAMETER;
  if(Step>=3||ArmReadCntPct()-Start<(Step+1)*Frequency)return EFI_NOT_READY;
  K->ScanCode=Step==0?SCAN_UP:Step==1?SCAN_DOWN:0;K->UnicodeChar=Step==2?13:0;++Step;return EFI_SUCCESS;
}
STATIC VOID EFIAPI Wait(EFI_EVENT E,VOID *C){(VOID)C;if(Step<3&&ArmReadCntPct()-Start>=(Step+1)*Frequency)gBS->SignalEvent(E);}
EFI_STATUS EFIAPI MenuFixtureEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *St){
  (VOID)Image;EFI_GRAPHICS_OUTPUT_PROTOCOL *G=NULL;EFI_STATUS S=gBS->LocateProtocol(&gEfiGraphicsOutputProtocolGuid,NULL,(VOID **)&G);
  if(EFI_ERROR(S)||!G){Print(L"MENU_FIXTURE_FAIL GOP\r\n");return EFI_NOT_READY;}
  RAPHAEL_DIAGNOSTIC *D=AllocateZeroPool(sizeof(*D));if(!D)return EFI_OUT_OF_RESOURCES;
  D->Cntfrq=ArmReadCntFrq();D->InputDxe.ProtocolInstalled=1;D->Gop.Base=G->Mode->FrameBufferBase;
  D->Gop.Width=G->Mode->Info->HorizontalResolution;D->Gop.Height=G->Mode->Info->VerticalResolution;
  D->Gop.Stride=G->Mode->Info->PixelsPerScanLine*4;
  EFI_SIMPLE_TEXT_INPUT_PROTOCOL *Previous=St->ConIn;Input.Reset=Reset;Input.ReadKeyStroke=Read;
  S=gBS->CreateEvent(EVT_NOTIFY_WAIT,TPL_CALLBACK,Wait,NULL,&Input.WaitForKey);if(EFI_ERROR(S))return S;
  St->ConIn=&Input;Start=ArmReadCntPct();Frequency=D->Cntfrq;
  Print(L"MENU_FIXTURE_START synthetic keys; %ux%u\r\n",(UINT32)D->Gop.Width,(UINT32)D->Gop.Height);
  S=RaphaelTestMenu(D);St->ConIn=Previous;gBS->CloseEvent(Input.WaitForKey);
  BOOLEAN Good=!EFI_ERROR(S)&&D->Menu.Status==3&&D->Menu.Up==1&&D->Menu.Down==1&&D->Menu.Enter==1&&
    D->Menu.ExitReason==2&&D->Menu.Restore.PatchRestored==D->Gop.Width*D->Gop.Height&&
    !D->Menu.Restore.PatchMismatches&&!D->Menu.Restore.Active&&!D->Menu.Restore.Backup;
  Print(L"MENU_FIXTURE_RESULT status=%lu up=%lu down=%lu enter=%lu restore=%lu mismatch=%lu changed=%lu\r\n",D->Menu.Status,D->Menu.Up,D->Menu.Down,D->Menu.Enter,D->Menu.Restore.PatchRestored,D->Menu.Restore.PatchMismatches,D->Menu.PixelsChanged);
  Print(Good?L"MENU_FIXTURE_OK\r\n":L"MENU_FIXTURE_FAIL\r\n");
  FreePool(D);return Good?EFI_SUCCESS:EFI_COMPROMISED_DATA;
}
