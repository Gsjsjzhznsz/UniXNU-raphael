// SPDX-License-Identifier: BSD-2-Clause-Patent
// Read-only synthetic FAT integration. No Android initrd or handset storage access.
#include <RaphaelDiagnostic.h>
#include <RaphaelPhysicalTimer.h>
#include <RaphaelKernelWindow.h>
#include <Library/RaphaelManagerUiLib.h>
#include <Library/RaphaelManagerInputLib.h>
#include <Library/FdtLib.h>
#include <Library/HobLib.h>
#include <Protocol/BlockIo.h>
#include <Protocol/SimpleFileSystem.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/ArmLib.h>
#include <Library/DevicePathLib.h>
#include <Library/MemoryAllocationLib.h>
#include <../Library/UniXNULib/Internal.h>
STATIC EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *mStagingFs;
// Only the explicit staging profile exercises a whole-file pool allocation.
STATIC EFI_STATUS CheckStagedKernel(EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *Fs) {
 if(!FixedPcdGetBool(PcdRaphaelNativeBoot)||FixedPcdGetBool(PcdRaphaelNativeHandoff))return EFI_SUCCESS;
 UINTN Bytes=FixedPcdGet32(PcdRaphaelStagingKernelBytes);UINT32 Crc=0;EFI_FILE_PROTOCOL *Root=NULL,*File=NULL;VOID *Buffer=NULL;
 EFI_STATUS S=Fs->OpenVolume(Fs,&Root);if(EFI_ERROR(S))return S;
 S=Root->Open(Root,&File,L"\\EFI\\UniXNU\\kernel.macho",EFI_FILE_MODE_READ,0);if(EFI_ERROR(S))goto Done;
 RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();UINTN MapBytes=sizeof(D->Map),Key,Stride;UINT32 Version;
 if(!EFI_ERROR(gBS->GetMemoryMap(&MapBytes,(VOID *)D->Map,&Key,&Stride,&Version))&&Stride>=sizeof(EFI_MEMORY_DESCRIPTOR)){
  for(UINTN I=0;I<MapBytes;I+=Stride){EFI_MEMORY_DESCRIPTOR *M=(VOID *)(D->Map+I);
   if(M->Type==EfiConventionalMemory)DEBUG((DEBUG_INFO,"NATIVE_STAGING free base=%lx bytes=%lx\n",M->PhysicalStart,EFI_PAGES_TO_SIZE(M->NumberOfPages)));
  }
 }
 Buffer=AllocatePool(Bytes);DEBUG((DEBUG_INFO,"NATIVE_STAGING pool=%lx bytes=%lu\n",(UINT64)(UINTN)Buffer,(UINT64)Bytes));if(!Bytes||!Buffer){S=EFI_OUT_OF_RESOURCES;goto Done;}
 UINT64 At=(UINTN)Buffer,Base=FixedPcdGet64(PcdRaphaelArenaBase),End=Base+FixedPcdGet32(PcdRaphaelArenaSize)-RAPHAEL_NATIVE_FAT_BYTES;
 if(At<Base||At>End||Bytes>End-At){S=EFI_COMPROMISED_DATA;goto Done;}
 UINTN Read=Bytes;S=File->Read(File,&Read,Buffer);if(EFI_ERROR(S)||Read!=Bytes){S=EFI_LOAD_ERROR;goto Done;}
 UINT8 Extra;Read=1;S=File->Read(File,&Read,&Extra);if(EFI_ERROR(S)||Read){S=EFI_COMPROMISED_DATA;goto Done;}
 S=gBS->CalculateCrc32(Buffer,Bytes,&Crc);if(!EFI_ERROR(S)&&Crc!=FixedPcdGet32(PcdRaphaelStagingKernelCrc))S=EFI_CRC_ERROR;
 DEBUG((DEBUG_INFO,"NATIVE_STAGING kernel bytes=%lu buffer=%lx crc=%08x expected=%08x status=%r\n",(UINT64)Bytes,At,Crc,FixedPcdGet32(PcdRaphaelStagingKernelCrc),S));
Done:
 if(Buffer)FreePool(Buffer);if(File)File->Close(File);if(Root)Root->Close(Root);return S;
}
STATIC UINT64 ManagerCounter(VOID){return ArmReadCntPct();}
EFI_STATUS RaphaelTestPayload(EFI_HANDLE Image,RAPHAEL_DIAGNOSTIC *D) {
 RAPHAEL_PAYLOAD_RESULT *P=&D->Payload;EFI_STATUS S;UINT32 Crc;EFI_HANDLE *Handles=NULL,Ram=NULL;
 UINTN Count=0;EFI_BLOCK_IO_PROTOCOL *Io=NULL;EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *Fs=NULL;UINT8 Sector[512];
 EFI_GUID RamGuid={0xA9C6827C,0x1BD8,0x410C,{0x88,0x5A,0xC4,0x65,0x00,0xF7,0xD8,0x36}};
 UINT64 Base=FixedPcdGetBool(PcdRaphaelNativeBoot)?FixedPcdGet64(PcdRaphaelArenaBase):FixedPcdGet64(PcdRaphaelFdBase);
 UINT64 End=Base+(FixedPcdGetBool(PcdRaphaelNativeBoot)?FixedPcdGet32(PcdRaphaelArenaSize):FixedPcdGet32(PcdRaphaelFdSize));
 UINT64 ExpectedBytes=FixedPcdGetBool(PcdRaphaelNativeBoot)?RAPHAEL_NATIVE_FAT_BYTES:RAPHAEL_DIAGNOSTIC_FAT_BYTES;
 if(P->Status!=2||P->Base<Base||P->Base>End||P->Bytes!=ExpectedBytes||P->Bytes>End-P->Base)return EFI_NOT_READY;
 // Explicit visible mode has an independent full-frame transaction below.
 EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop=NULL;
 if(!EFI_ERROR(gBS->LocateProtocol(&gEfiGraphicsOutputProtocolGuid,NULL,(VOID **)&Gop))&&
    !FixedPcdGetBool(PcdRaphaelVisibleManager)&&!FixedPcdGetBool(PcdRaphaelNativeVideo))return EFI_UNSUPPORTED;
 if(FixedPcdGetBool(PcdRaphaelNativeVideo)&&(!Gop||!D->Gop.Active||!D->Gop.Backup))return EFI_NOT_READY;
 S=gBS->CalculateCrc32((VOID *)(UINTN)P->Base,P->Bytes,&Crc);if(EFI_ERROR(S))return S;P->CrcBefore=Crc;
 S=gBS->LocateHandleBuffer(ByProtocol,&gEfiBlockIoProtocolGuid,NULL,&Count,&Handles);if(EFI_ERROR(S))return S;
 for(UINTN I=0;I<Count;++I) {
  EFI_DEVICE_PATH_PROTOCOL *Path=NULL;
  if(EFI_ERROR(gBS->HandleProtocol(Handles[I],&gEfiDevicePathProtocolGuid,(VOID **)&Path)))continue;
  if(DevicePathType(Path)!=HARDWARE_DEVICE_PATH||DevicePathSubType(Path)!=HW_VENDOR_DP||DevicePathNodeLength(Path)!=sizeof(VENDOR_DEVICE_PATH)||!CompareGuid(&((VENDOR_DEVICE_PATH *)Path)->Guid,&RamGuid))continue;
  if(!EFI_ERROR(gBS->HandleProtocol(Handles[I],&gEfiBlockIoProtocolGuid,(VOID **)&Io))){Ram=Handles[I];break;}
 }
 FreePool(Handles);if(!Ram||!Io||!Io->Media||!Io->Media->MediaPresent||Io->Media->BlockSize!=512||Io->Media->LastBlock!=ExpectedBytes/512-1)return EFI_NOT_FOUND;
 P->BlockIo=1;P->ReadOnly=Io->Media->ReadOnly;if(!P->ReadOnly)return EFI_WRITE_PROTECTED;
 S=Io->ReadBlocks(Io,Io->Media->MediaId,0,512,Sector);if(EFI_ERROR(S)||CompareMem(Sector,(VOID *)(UINTN)P->Base,512))return EFI_COMPROMISED_DATA;
 P->WriteDenied=Io->WriteBlocks(Io,Io->Media->MediaId,0,512,Sector)==EFI_WRITE_PROTECTED;if(!P->WriteDenied)return EFI_COMPROMISED_DATA;
 // Installing the RAM device may already connect the registered disk/FAT
 // bindings. Check the resulting protocol before requesting a new binding.
 S=gBS->HandleProtocol(Ram,&gEfiSimpleFileSystemProtocolGuid,(VOID **)&Fs);
 if(EFI_ERROR(S)) {
  gBS->ConnectController(Ram,NULL,NULL,TRUE);
  S=gBS->HandleProtocol(Ram,&gEfiSimpleFileSystemProtocolGuid,(VOID **)&Fs);
 }
 if(EFI_ERROR(S)||!Fs)return EFI_NOT_FOUND;
 mStagingFs=Fs;
 P->FileSystem=1;UNIXNU_CONFIG Config;UniXNUConfigLoad(Image,&Config);P->ConfigEntries=Config.EntryCount;
 // External native payloads use an immediate diagnostic exit; timer protocol
 // relative/periodic/cancellation checks remain independent of this menu.
 BOOLEAN ImmediateNative=FixedPcdGetBool(PcdRaphaelNativeBoot)&&FixedPcdGetBool(PcdRaphaelUfsPayload);
 P->ConfigOk=Config.Volume==Ram&&Config.Error[0]==0&&Config.EntryCount==(FixedPcdGetBool(PcdRaphaelManagerKeys)?2:1)&&Config.Timeout==(FixedPcdGetBool(PcdRaphaelManagerKeys)?6:ImmediateNative?0:(FixedPcdGetBool(PcdRaphaelQemuArchTest)||FixedPcdGetBool(PcdRaphaelPhysicalTimerArch))?2:0)&&Config.DefaultIndex==0&&Config.Entries[0].Type==UniXNUEntryAction&&Config.Entries[0].Action==UniXNUActionExit;
 if(!P->ConfigOk||(FixedPcdGetBool(PcdRaphaelVisibleManager)&&Config.Console!=UniXNUConsoleGraphics))return EFI_COMPROMISED_DATA;
 RAPHAEL_MANAGER_RESULT *Manager=NULL;
 if(FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)) {
  VOID *Hob=GetFirstGuidHob(&gRaphaelPhysicalTimerHobGuid);
  if(!Hob||GET_GUID_HOB_DATA_SIZE(Hob)!=sizeof(RAPHAEL_PHYSICAL_TIMER_STATE *))return EFI_NOT_READY;
  RAPHAEL_PHYSICAL_TIMER_STATE *State=*(RAPHAEL_PHYSICAL_TIMER_STATE **)GET_GUID_HOB_DATA(Hob);
  if(State->Result.Status!=3||!State->Dirty||State->Result.Reason||!State->Result.TimerProtocol)return EFI_NOT_READY;
  Manager=&State->Manager; Manager->Timeout=Config.Timeout;
 }
 RAPHAEL_MANAGER_UI_STATE *Ui=NULL;
 if(FixedPcdGetBool(PcdRaphaelVisibleManager)) {
  VOID *Hob=GetFirstGuidHob(&gRaphaelManagerUiHobGuid);
  if(!Hob||GET_GUID_HOB_DATA_SIZE(Hob)!=sizeof(Ui))return EFI_NOT_READY;
  Ui=*(RAPHAEL_MANAGER_UI_STATE **)GET_GUID_HOB_DATA(Hob);
  if(!Ui||Ui->Result.Version!=1||Ui->Result.Status!=1)return EFI_NOT_READY;
  if(D->Gop.Status==1) {
    // Explicit simulator-only missing-hardware model. Never accepted by the handset decoder.
    INT32 Len=0;CONST CHAR8 *Compat=FdtGetProp((VOID *)(UINTN)D->FdtCopy,0,"compatible",&Len);
    if(!Compat||Len!=17||CompareMem(Compat,"linux,dummy-virt",17))return EFI_UNSUPPORTED;
    Ui->Result.Status=5;
    DEBUG((DEBUG_INFO,"RAPHAEL manager UI QEMU model: no inherited display/input; visible path skipped\n"));
  } else {
    if(D->Gop.Status!=4||D->Gop.Base==0||D->InputDxe.Status!=4||!D->InputDxe.ProtocolInstalled||D->InputDxe.Errors||!gST->ConIn||!Gop)return EFI_NOT_READY;
    S=RaphaelManagerUiBegin(Ui,&D->Gop,TRUE,Gop);if(EFI_ERROR(S))return S;
  }
 }
 RAPHAEL_MANAGER_INPUT *Keys=NULL;
 EFI_SIMPLE_TEXT_INPUT_PROTOCOL *SavedInput=gST->ConIn;
 EFI_HANDLE SavedInputHandle=gST->ConsoleInHandle,KeysHandle=NULL;
 UINT32 SavedTableCrc=gST->Hdr.CRC32;
 if(FixedPcdGetBool(PcdRaphaelManagerKeys)&&Ui&&Ui->Restore.Active) {
  if(Config.Entries[1].Type!=UniXNUEntryAction||Config.Entries[1].Action!=UniXNUActionExit)return EFI_COMPROMISED_DATA;
  Keys=AllocateZeroPool(sizeof(*Keys));if(!Keys)return EFI_OUT_OF_RESOURCES;
  S=RaphaelManagerInputBegin(Keys,SavedInput,ManagerCounter,D->Cntfrq,6);if(EFI_ERROR(S)){FreePool(Keys);return S;}
  S=gBS->InstallProtocolInterface(&KeysHandle,&gEfiSimpleTextInProtocolGuid,EFI_NATIVE_INTERFACE,&Keys->Protocol);
  if(EFI_ERROR(S)){if(!EFI_ERROR(RaphaelManagerInputEnd(Keys)))FreePool(Keys);return S;}
  gST->ConIn=&Keys->Protocol;gST->ConsoleInHandle=KeysHandle;gST->Hdr.CRC32=0;
  S=gBS->CalculateCrc32(gST,gST->Hdr.HeaderSize,&gST->Hdr.CRC32);
  if(EFI_ERROR(S)){
   gST->ConIn=SavedInput;gST->ConsoleInHandle=SavedInputHandle;gST->Hdr.CRC32=SavedTableCrc;
   EFI_STATUS U=gBS->UninstallProtocolInterface(KeysHandle,&gEfiSimpleTextInProtocolGuid,&Keys->Protocol);
   EFI_STATUS C=RaphaelManagerInputEnd(Keys);if(!EFI_ERROR(U)&&!EFI_ERROR(C))FreePool(Keys);return S;
  }
 }
 UINT64 Start=ArmReadCntPct(); if(Manager)Manager->StartCounter=Start;
 S=UniXNURun(Image,UniXNUHostApplication);P->RunStatus=S;P->RunCompleted=1;
 if(KeysHandle){
  gST->ConIn=SavedInput;gST->ConsoleInHandle=SavedInputHandle;gST->Hdr.CRC32=SavedTableCrc;
  EFI_STATUS U=gBS->UninstallProtocolInterface(KeysHandle,&gEfiSimpleTextInProtocolGuid,&Keys->Protocol);
  EFI_STATUS C=RaphaelManagerInputEnd(Keys);
  DEBUG((DEBUG_INFO,"RAPHAEL manager keys up/down/enter/automatic/errors/delivered=%lu/%lu/%lu/%lu/%lu/%lu\n",Keys->Up,Keys->Down,Keys->Enter,Keys->Automatic,Keys->Errors,Keys->Delivered));
  UINT32 VerifiedCrc=0;gST->Hdr.CRC32=0;EFI_STATUS V=gBS->CalculateCrc32(gST,gST->Hdr.HeaderSize,&VerifiedCrc);gST->Hdr.CRC32=SavedTableCrc;
  BOOLEAN Restored=!EFI_ERROR(V)&&VerifiedCrc==SavedTableCrc&&gST->ConIn==SavedInput&&gST->ConsoleInHandle==SavedInputHandle;
  DEBUG((DEBUG_INFO,"RAPHAEL manager input cleanup console=%u uninstall=%u close=%u\n",(UINT32)Restored,(UINT32)!EFI_ERROR(U),(UINT32)!EFI_ERROR(C)));
  if(EFI_ERROR(U)||EFI_ERROR(C)||Keys->Errors||!Restored)S=EFI_DEVICE_ERROR;
  // Preserve a failed detach/close allocation until SEC returns; no dangling callback context.
  if(!EFI_ERROR(U)&&!EFI_ERROR(C))FreePool(Keys);
 }
 if(FixedPcdGetBool(PcdRaphaelQemuArchTest)){D->QemuArch.ManagerTicks=ArmReadCntPct()-Start;D->QemuArch.ManagerCompleted=!EFI_ERROR(S);}
 if(Manager) {
  Manager->EndCounter=ArmReadCntPct();
  if(EFI_ERROR(S)||Manager->EndCounter<Start||Manager->EndCounter-Start<(FixedPcdGetBool(PcdRaphaelManagerKeys)||ImmediateNative?1:Manager->Frequency*18/10)||Manager->EndCounter-Start>Manager->Frequency*(FixedPcdGetBool(PcdRaphaelManagerKeys)?8:5))return EFI_TIMEOUT;
  Manager->Status=2;
 }
 EFI_STATUS RunStatus=S;
 if(Ui&&Ui->Restore.Active) {
  EFI_STATUS RestoreStatus=RaphaelManagerUiFinish(Ui);
  DEBUG((DEBUG_INFO,"RAPHAEL full manager UI status=%lu changed/restored/mismatch=%lu/%lu/%lu error=%r\n",Ui->Result.Status,Ui->Result.PixelsChanged,Ui->Result.PixelsRestored,Ui->Result.Mismatches,RestoreStatus));
  if(EFI_ERROR(RestoreStatus))return RestoreStatus;
 }
 if(EFI_ERROR(RunStatus))return RunStatus;
 S=gBS->CalculateCrc32((VOID *)(UINTN)P->Base,P->Bytes,&Crc);if(EFI_ERROR(S))return S;P->CrcAfter=Crc;
 if(P->CrcAfter!=P->CrcBefore)return EFI_COMPROMISED_DATA;
 P->Status=3;return EFI_SUCCESS;
}

// Match the original loader's allocation phase: release the quarantined run
// immediately before the file-buffer allocation, then fully restore it.
EFI_STATUS RaphaelTestNativeStaging(VOID) {
 if(!mStagingFs||!FixedPcdGetBool(PcdRaphaelNativeBoot)||FixedPcdGetBool(PcdRaphaelNativeHandoff))return EFI_NOT_READY;
 EFI_STATUS S=RaphaelReleaseKernelWindow();if(EFI_ERROR(S))return S;
 S=CheckStagedKernel(mStagingFs);EFI_STATUS Restore=RaphaelRestoreKernelWindow();
 DEBUG((DEBUG_INFO,"NATIVE_STAGING window_restore=%r\n",Restore));
 return EFI_ERROR(Restore)?Restore:S;
}
