// SPDX-License-Identifier: BSD-2-Clause-Patent
// Emulator-only. AAVMF supplies services; original DarwinBoot performs handoff.
#include <Uefi.h>
#include <Guid/EventGroup.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/DevicePathLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/PrintLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiRuntimeServicesTableLib.h>
#include <../Library/UniXNULib/Internal.h>
#include <Protocol/LoadedImage.h>
#include <Protocol/UniXNULoader.h>
#include <Protocol/SimpleFileSystem.h>
#include <HandoffState.h>

STATIC HANDOFF_STATE *mState;
STATIC VOID EFIAPI ExitNotice(EFI_EVENT Event,VOID *Context) {
 (VOID)Event;(VOID)Context;
 ++mState->ExitCount;
 WriteBackDataCacheRange(mState,sizeof(*mState));
}
STATIC VOID Fail(CONST CHAR8 *Where,EFI_STATUS Status) {
 UniXNULog("HANDOFF_FIXTURE_FAIL %a %r",Where,Status);
 gRT->ResetSystem(EfiResetShutdown,Status,0,NULL);
 CpuDeadLoop();
}
EFI_STATUS EFIAPI HandoffFixtureEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *Table) {
 EFI_STATUS S;EFI_LOADED_IMAGE_PROTOCOL *Loaded;EFI_DEVICE_PATH_PROTOCOL *Path;
 EFI_HANDLE Driver=NULL;UNIXNU_LOADER_PROTOCOL *Loader;EFI_EVENT Event;
 UNIXNU_CONFIG Config;
 EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *Fs;EFI_FILE_PROTOCOL *Root,*Tree;
 UINT8 Buffer[32768];UINTN Bytes=4096,ExpectedBytes=sizeof(Buffer);UINT32 Crc,ExpectedCrc=0;CHAR16 Args[64];
 UINT64 El;__asm__ volatile("mrs %0,CurrentEL":"=r"(El));(VOID)Table;
 UniXNULogInit();
 if(El!=4)Fail("need EL1",EFI_UNSUPPORTED);
 S=gBS->HandleProtocol(Image,&gEfiLoadedImageProtocolGuid,(VOID **)&Loaded);if(EFI_ERROR(S))Fail("parent",S);
 Path=FileDevicePath(Loaded->DeviceHandle,L"\\DarwinBoot.efi");if(!Path)Fail("driver path",EFI_OUT_OF_RESOURCES);
 S=gBS->LoadImage(FALSE,Image,Path,NULL,0,&Driver);FreePool(Path);if(EFI_ERROR(S))Fail("driver load",S);
 S=gBS->StartImage(Driver,NULL,NULL);if(EFI_ERROR(S))Fail("driver start",S);
 S=gBS->HandleProtocol(Driver,&gUniXNULoaderProtocolGuid,(VOID **)&Loader);
 if(EFI_ERROR(S)||Loader->Revision!=0x20000)Fail("v2 protocol",S);
 S=gBS->HandleProtocol(Loaded->DeviceHandle,&gEfiSimpleFileSystemProtocolGuid,(VOID **)&Fs);if(EFI_ERROR(S))Fail("filesystem",S);
 S=Fs->OpenVolume(Fs,&Root);if(EFI_ERROR(S))Fail("root",S);
 S=Root->Open(Root,&Tree,L"\\EFI\\UniXNU\\probe.macho.adt",EFI_FILE_MODE_READ,0);if(EFI_ERROR(S))Fail("ADT open",S);
 S=Tree->Read(Tree,&Bytes,Buffer);Tree->Close(Tree);if(EFI_ERROR(S)||Bytes==0||Bytes>=4096)Fail("ADT read",S);
 S=gBS->CalculateCrc32(Buffer,Bytes,&Crc);if(EFI_ERROR(S))Fail("ADT CRC",S);
 S=Root->Open(Root,&Tree,L"\\EFI\\UniXNU\\expected.bin",EFI_FILE_MODE_READ,0);
 if(S==EFI_NOT_FOUND)ExpectedBytes=0;
 else {
  if(EFI_ERROR(S))Fail("expected data open",S);
  S=Tree->Read(Tree,&ExpectedBytes,Buffer);Tree->Close(Tree);
  if(EFI_ERROR(S)||ExpectedBytes==0||ExpectedBytes==sizeof(Buffer))Fail("expected data read",S);
  S=gBS->CalculateCrc32(Buffer,ExpectedBytes,&ExpectedCrc);if(EFI_ERROR(S))Fail("expected data CRC",S);
 }
 Root->Close(Root);
 // Four-KiB allocation isolates the notice cache lines from unrelated state.
 mState=AllocatePages(1);if(!mState)Fail("notice page",EFI_OUT_OF_RESOURCES);
 ZeroMem(mState,4096);mState->Magic=HANDOFF_MAGIC;mState->Version=1;mState->Bytes=sizeof(*mState);
 mState->TreeBytes=Bytes;mState->TreeCrc=Crc;mState->RamdiskBytes=ExpectedBytes;mState->RamdiskCrc=ExpectedCrc;
 S=gBS->CreateEventEx(EVT_NOTIFY_SIGNAL,TPL_NOTIFY,ExitNotice,NULL,&gEfiEventExitBootServicesGuid,&Event);if(EFI_ERROR(S))Fail("exit notice",S);
 UnicodeSPrint(Args,sizeof(Args),L"probe=%016lx",(UINT64)(UINTN)mState);
 UniXNUConfigLoad(Image,&Config);
 if(Config.EntryCount!=1 || Config.Error[0] || Config.Entries[0].Type!=UniXNUEntryXnu)Fail("config",EFI_COMPROMISED_DATA);
 Config.Entries[0].Args=Args;
 UniXNULog("HANDOFF_FIXTURE_READY loader-v2 via UniXNUBootEntry, synthetic kernel, ExitBootServices expected");
 S=UniXNUBootEntry(Image,&Config,&Config.Entries[0]);
 Fail("handoff returned",S);return EFI_ABORTED;
}
