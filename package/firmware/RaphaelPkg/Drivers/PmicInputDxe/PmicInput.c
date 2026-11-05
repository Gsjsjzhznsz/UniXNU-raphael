// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelDiagnostic.h>
#include <Protocol/SimpleTextIn.h>
#include <Protocol/DevicePath.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/ArmLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
STATIC RAPHAEL_KEY_TRANSPORT mTransport;
STATIC RAPHAEL_KEY_FILTER mFilter;
STATIC RAPHAEL_INPUT_DXE_RESULT *mResult;
STATIC EFI_INPUT_KEY mPending;
STATIC BOOLEAN mHavePending,mBusy,mHavePolled;
STATIC UINT64 mLastPoll;
STATIC EFI_SIMPLE_TEXT_INPUT_PROTOCOL mInput;
STATIC UINT32 Read(UINT64 A,VOID *C) {
  (VOID)C;ArmDataMemoryBarrier();UINT32 V=*(volatile UINT32 *)(UINTN)A;ArmDataMemoryBarrier();return V;
}
STATIC VOID Write(UINT64 A,UINT32 V,VOID *C) {
  (VOID)C;*(volatile UINT32 *)(UINTN)A=V;ArmDataSynchronizationBarrier();
}
STATIC UINT64 Counter(VOID *C){(VOID)C;return ArmReadCntPct();}
STATIC VOID Poll(VOID) {
  if(mBusy||mHavePending||!mResult||mResult->Errors)return;
  UINT64 Now=ArmReadCntPct();
  if(mHavePolled&&Now-mLastPoll<((UINT64)mTransport.Frequency*5+999)/1000)return;
  mBusy=TRUE;mHavePolled=TRUE;mLastPoll=Now;UINT32 Raw=0;
  ++mResult->Polls;
  if(!RaphaelReadKeyState(&mTransport,&Raw,Read,Write,Counter,NULL)) {
    ++mResult->Errors;mBusy=FALSE;return;
  }
  mResult->LastRaw=Raw;
  UINT32 Press=RaphaelFilterKeys(&mFilter,Raw,Now);
  mResult->PressedMask=mFilter.PressedMask;mResult->ReleasedMask=mFilter.ReleasedMask;
  if(Press) {
    mPending.ScanCode=Press==RAPHAEL_KEY_UP?SCAN_UP:Press==RAPHAEL_KEY_DOWN?SCAN_DOWN:SCAN_NULL;
    mPending.UnicodeChar=Press==RAPHAEL_KEY_POWER?CHAR_CARRIAGE_RETURN:0;
    mHavePending=TRUE;++mResult->Events;mResult->LastScan=mPending.ScanCode;
  }
  mBusy=FALSE;
}
STATIC EFI_STATUS EFIAPI Reset(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This,BOOLEAN Extended) {
  (VOID)Extended;if(This!=&mInput)return EFI_INVALID_PARAMETER;
  UINT64 Debounce=mFilter.DebounceTicks;ZeroMem(&mFilter,sizeof(mFilter));mFilter.DebounceTicks=Debounce;
  mHavePending=FALSE;mHavePolled=FALSE;++mResult->ResetCalls;return mResult->Errors?EFI_DEVICE_ERROR:EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI ReadKey(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This,EFI_INPUT_KEY *Key) {
  if(This!=&mInput||!Key)return EFI_INVALID_PARAMETER;++mResult->ReadCalls;Poll();
  if(mResult->Errors)return EFI_DEVICE_ERROR;if(!mHavePending)return EFI_NOT_READY;
  *Key=mPending;mHavePending=FALSE;return EFI_SUCCESS;
}
STATIC VOID EFIAPI Wait(EFI_EVENT Event,VOID *Context) {
  (VOID)Context;Poll();if(mHavePending)gBS->SignalEvent(Event);
}
STATIC struct {VENDOR_DEVICE_PATH Vendor;EFI_DEVICE_PATH_PROTOCOL End;} mPath={
  {{HARDWARE_DEVICE_PATH,HW_VENDOR_DP,{sizeof(VENDOR_DEVICE_PATH),0}},
   {0x708721be,0x5b5c,0x40bf,{0xbd,0x69,0x09,0xa1,0x72,0xb1,0x74,0x0d}}},
  {END_DEVICE_PATH_TYPE,END_ENTIRE_DEVICE_PATH_SUBTYPE,{sizeof(EFI_DEVICE_PATH_PROTOCOL),0}}};
EFI_STATUS EFIAPI PmicInputEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *Table) {
  (VOID)Image;(VOID)Table;RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();
  if(!FixedPcdGetBool(PcdRaphaelInputProtocol)||D->Magic!=RAPHAEL_DIAG_MAGIC||D->InputDxe.Status!=3||!D->InputDxe.MappedReadVerified||
    !RaphaelKeyRegistersReady(&D->Keys)||!RaphaelKeyTransport(&D->Input,(UINT32)D->Cntfrq,&mTransport))return EFI_UNSUPPORTED;
  mResult=&D->InputDxe;mFilter.DebounceTicks=((UINT64)mTransport.Frequency*D->Input.DebounceMs+999)/1000;
  mInput.Reset=Reset;mInput.ReadKeyStroke=ReadKey;
  EFI_STATUS S=gBS->CreateEvent(EVT_NOTIFY_WAIT,TPL_CALLBACK,Wait,NULL,&mInput.WaitForKey);if(EFI_ERROR(S))return S;
  EFI_HANDLE Handle=NULL;
  S=gBS->InstallMultipleProtocolInterfaces(&Handle,&gEfiSimpleTextInProtocolGuid,&mInput,&gEfiDevicePathProtocolGuid,&mPath,NULL);
  if(EFI_ERROR(S)){gBS->CloseEvent(mInput.WaitForKey);return S;}
  mResult->ProtocolInstalled=1;mResult->Status=4;
  // Assign the console and refresh CRC for callers using gST->ConIn.
  EFI_HANDLE PreviousHandle=Table->ConsoleInHandle;EFI_SIMPLE_TEXT_INPUT_PROTOCOL *PreviousInput=Table->ConIn;
  UINT32 PreviousCrc=Table->Hdr.CRC32;
  Table->ConsoleInHandle=Handle;Table->ConIn=&mInput;Table->Hdr.CRC32=0;
  S=gBS->CalculateCrc32(Table,Table->Hdr.HeaderSize,&Table->Hdr.CRC32);
  if(EFI_ERROR(S)) {
    Table->ConsoleInHandle=PreviousHandle;Table->ConIn=PreviousInput;Table->Hdr.CRC32=PreviousCrc;
    gBS->UninstallMultipleProtocolInterfaces(Handle,&gEfiSimpleTextInProtocolGuid,&mInput,&gEfiDevicePathProtocolGuid,&mPath,NULL);
    gBS->CloseEvent(mInput.WaitForKey);mResult->ProtocolInstalled=0;mResult->Status=3;return S;
  }
  DEBUG((DEBUG_INFO,"RAPHAEL PM8150 SimpleTextIn installed with bounded polling\n"));return EFI_SUCCESS;
}
