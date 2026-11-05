// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/mman.h>
#undef NULL
_Alignas(8) static unsigned char TestContext[61440];
#define _PCD_VALUE_PcdRaphaelContextBase ((UINT64)(UINTN)TestContext)
#include <RaphaelDiagnostic.h>
#include <Library/ArmLib.h>
#include <Library/DebugLib.h>
#include <Library/BaseMemoryLib.h>
#define Diag (*(RAPHAEL_DIAGNOSTIC *)TestContext)
#undef FixedPcdGet64
#undef FixedPcdGetBool
#define FixedPcdGet64(Token) ((UINT64)(UINTN)&Diag)
#define FixedPcdGetBool(Token) TRUE
#include "../../UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/PmicInputDxe/PmicInput.c"
STATIC UINT64 Now;
UINT64 ArmReadCntPct(VOID){return Now;}
VOID EFIAPI ArmDataMemoryBarrier(VOID){}
VOID EFIAPI ArmDataSynchronizationBarrier(VOID){}
VOID *EFIAPI ZeroMem(VOID *P,UINTN N){return memset(P,0,N);}
VOID EFIAPI DebugPrint(UINTN Level,CONST CHAR8 *Format,...){(VOID)Level;(VOID)Format;}
BOOLEAN EFIAPI DebugPrintEnabled(VOID){return TRUE;}
BOOLEAN EFIAPI DebugPrintLevelEnabled(CONST UINTN Level){(VOID)Level;return TRUE;}
EFI_BOOT_SERVICES *gBS;
EFI_GUID gEfiSimpleTextInProtocolGuid={0},gEfiDevicePathProtocolGuid={0};
STATIC EFI_BOOT_SERVICES Bs;
STATIC EFI_SYSTEM_TABLE St;
STATIC EFI_EVENT_NOTIFY Notify;
STATIC UINTN Signals,Installed,Closed,Checks;
STATIC VOID Check(BOOLEAN Value,CONST char *Name){if(!Value){fprintf(stderr,"FAIL %s\n",Name);exit(1);}printf("PASS %s\n",Name);++Checks;}
STATIC EFI_STATUS EFIAPI Create(UINT32 Type,EFI_TPL Tpl,EFI_EVENT_NOTIFY Fn,VOID *Context,EFI_EVENT *Event){
  (VOID)Context;Check(Type==EVT_NOTIFY_WAIT&&Tpl==TPL_CALLBACK,"real notify-wait event");Notify=Fn;*Event=(VOID *)0x1234;return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI Signal(EFI_EVENT E){Check(E==(VOID *)0x1234,"signals own event");++Signals;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI Close(EFI_EVENT E){(VOID)E;++Closed;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI Install(EFI_HANDLE *H,...){*H=(VOID *)0x9876;++Installed;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI Crc(VOID *Data,UINTN Size,UINT32 *Out){
  UINT8 *P=Data;UINT32 V=0xffffffff;for(UINTN I=0;I<Size;++I){V^=P[I];for(UINTN B=0;B<8;++B)V=(V>>1)^((V&1)?0xedb88320:0);}*Out=~V;return EFI_SUCCESS;
}
STATIC VOID Setup(VOID){
  memset(&Diag,0,sizeof(Diag));memset(&St,0,sizeof(St));memset(&mFilter,0,sizeof(mFilter));
  mBusy=mHavePending=mHavePolled=FALSE;mLastPoll=0;Now=0;
  Diag.Magic=RAPHAEL_DIAG_MAGIC;Diag.Cntfrq=1000000;RAPHAEL_INPUT_SNAPSHOT *I=&Diag.Input;
  I->Version=1;I->Status=4;I->HardwareVersion=0x50000000;I->Count=512;I->Ee=0;
  I->PonSid=0;I->PonAddress=0x810;I->VolumeSid=0;I->VolumeAddress=0xc510;
  I->PonApid=1;I->VolumeApid=2;I->PonMatches=I->VolumeMatches=1;
  I->ObserverBase=0x10000000;I->ObserverSize=0x100000;I->GpioFlags=1;I->DebounceMs=15;
  I->Map[1]=0x1000800;I->Map[2]=0x100c500;
  Diag.Keys.Version=1;Diag.Keys.Status=3;Diag.Keys.Transactions=Diag.Keys.Completed=6;
  for(UINTN N=0;N<6;++N)Diag.Keys.Registers[N].Completion=1;
  Diag.Keys.Registers[0].Value=0x10;Diag.Keys.Registers[1].Value=0x11;Diag.Keys.Registers[3].Value=0x80;
  Diag.InputDxe.Status=3;Diag.InputDxe.MappedReadVerified=1;
  *(UINT32 *)(UINTN)(0x10000080+8)=1;*(UINT32 *)(UINTN)(0x10000100+8)=1;
  *(UINT32 *)(UINTN)(0x10000080+0x18)=0;*(UINT32 *)(UINTN)(0x10000100+0x18)=1;
  St.Hdr.HeaderSize=sizeof(St);Bs.CreateEvent=Create;Bs.SignalEvent=Signal;Bs.CloseEvent=Close;Bs.InstallMultipleProtocolInterfaces=Install;Bs.CalculateCrc32=Crc;gBS=&Bs;
}
STATIC EFI_STATUS At(UINT64 Time,UINT32 Raw,EFI_INPUT_KEY *Key){
  Now=Time;*(UINT32 *)(UINTN)(0x10000100+0x18)=(Raw&1)?0:1;
  *(UINT32 *)(UINTN)(0x10000080+0x18)=((Raw&2)?2:0)|((Raw&4)?1:0);
  return mInput.ReadKeyStroke(&mInput,Key);
}
int main(void){
  VOID *Memory=mmap((VOID *)0x10000000,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
  Check(Memory==(VOID *)0x10000000,"map only synthetic observer memory in host process");
  Setup();Check(PmicInputEntry(NULL,&St)==EFI_SUCCESS,"actual driver installs protocol");
  Check(Installed==1&&St.ConIn==&mInput&&Diag.InputDxe.ProtocolInstalled==1,"published protocol and console");
  UINT32 Expected=St.Hdr.CRC32;St.Hdr.CRC32=0;UINT32 Computed;Crc(&St,sizeof(St),&Computed);St.Hdr.CRC32=Expected;Check(Computed==Expected,"system table CRC refreshed");
  EFI_INPUT_KEY Key;
  Check(At(0,0,&Key)==EFI_NOT_READY,"idle initializes filter");
  UINT64 Samples=Diag.InputDxe.Polls;Check(At(1000,1,&Key)==EFI_NOT_READY&&Diag.InputDxe.Polls==Samples,"five millisecond throttle");
  Check(At(5000,1,&Key)==EFI_NOT_READY&&At(15000,1,&Key)==EFI_NOT_READY,"debounce suppresses early key");
  Check(At(20000,1,&Key)==EFI_SUCCESS&&Key.ScanCode==SCAN_UP&&Key.UnicodeChar==0,"physical up maps to SCAN_UP");
  Check(At(2000000,1,&Key)==EFI_NOT_READY&&Diag.InputDxe.Events==1,"long hold does not repeat");
  Check(At(2010000,0,&Key)==EFI_NOT_READY&&At(2030000,0,&Key)==EFI_NOT_READY,"release debounced");
  Check(At(2040000,2,&Key)==EFI_NOT_READY&&At(2060000,2,&Key)==EFI_SUCCESS&&Key.ScanCode==SCAN_DOWN,"down maps to SCAN_DOWN");
  At(2070000,0,&Key);At(2090000,0,&Key);At(2100000,4,&Key);
  Now=2120000;Notify((VOID *)0x1234,NULL);Check(Signals==1,"WaitForKey polls and signals real pending input");
  Check(mInput.ReadKeyStroke(&mInput,&Key)==EFI_SUCCESS&&Key.ScanCode==0&&Key.UnicodeChar==13,"power maps to carriage return");
  Check(Diag.InputDxe.PressedMask==7&&(Diag.InputDxe.ReleasedMask&3)==3,"press and release telemetry");
  Check(mInput.ReadKeyStroke(&mInput,NULL)==EFI_INVALID_PARAMETER,"null key rejected");
  Check(mInput.Reset(&mInput,FALSE)==EFI_SUCCESS,"Reset clears pending filter");
  Check(At(3000000,1,&Key)==EFI_NOT_READY&&At(3050000,1,&Key)==EFI_NOT_READY,"held at reset suppressed");
  At(3060000,0,&Key);At(3080000,0,&Key);At(3090000,3,&Key);Check(At(3110000,3,&Key)==EFI_NOT_READY,"simultaneous chord suppressed");
  At(3120000,1,&Key);Check(At(3140000,1,&Key)==EFI_NOT_READY,"chord to single without release suppressed");
  At(3150000,0,&Key);At(3170000,0,&Key);At(3180000,1,&Key);Check(At(3200000,1,&Key)==EFI_SUCCESS,"full release rearms after chord");
  *(UINT32 *)(UINTN)(0x10000100+8)=3;Now=3210000;
  Check(mInput.ReadKeyStroke(&mInput,&Key)==EFI_DEVICE_ERROR&&Diag.InputDxe.Errors==1,"transaction failure becomes device error");
  Samples=Diag.InputDxe.Polls;Now=4000000;
  Check(mInput.ReadKeyStroke(&mInput,&Key)==EFI_DEVICE_ERROR&&Diag.InputDxe.Polls==Samples,"sticky error prevents more hardware commands");
  Setup();Diag.InputDxe.MappedReadVerified=0;Check(PmicInputEntry(NULL,&St)==EFI_UNSUPPORTED,"no mapping proof refuses installation");
  Setup();Diag.Keys.Registers[3].Value=0;Check(PmicInputEntry(NULL,&St)==EFI_UNSUPPORTED,"disabled input refuses installation");
  munmap(Memory,4096);printf("INPUT_DXE_HOST_OK %lu\n",(unsigned long)Checks);return 0;
}
