// SPDX-License-Identifier: BSD-2-Clause-Patent
// QEMU/AAVMF only: unchanged native XNU, debugger-gated ExitBootServices.
#include <Uefi.h>
#include <Guid/EventGroup.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/DevicePathLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiRuntimeServicesTableLib.h>
#include <Library/UefiLib.h>
#include <../Library/UniXNULib/Internal.h>
#include <Protocol/LoadedImage.h>
#include <Protocol/UniXNULoader.h>

typedef struct { UINT64 Magic; volatile UINT64 Release; volatile UINT64 ExitCount; } NATIVE_GATE;
STATIC NATIVE_GATE *mGate;
STATIC VOID EFIAPI ExitNotice(EFI_EVENT Event,VOID *Context) {
 (VOID)Event;(VOID)Context;
 ++mGate->ExitCount;
 // The debugger changes only this firmware allocation, never kernel bytes.
 WriteBackInvalidateDataCacheRange(mGate,EFI_PAGE_SIZE);
 while(!mGate->Release) {
  InvalidateDataCacheRange(mGate,EFI_PAGE_SIZE);
  CpuPause();
 }
 WriteBackDataCacheRange(mGate,EFI_PAGE_SIZE);
}
STATIC VOID Fail(CONST CHAR8 *Where,EFI_STATUS Status) {
 UniXNULog("NATIVE_XNU_FIXTURE_FAIL %a %r",Where,Status);
 gRT->ResetSystem(EfiResetShutdown,Status,0,NULL);
 CpuDeadLoop();
}
EFI_STATUS EFIAPI NativeXnuFixtureEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *Table) {
 EFI_STATUS S;EFI_LOADED_IMAGE_PROTOCOL *Loaded;EFI_DEVICE_PATH_PROTOCOL *Path;
 EFI_HANDLE Driver=NULL;UNIXNU_LOADER_PROTOCOL *Loader;EFI_EVENT Event;UNIXNU_CONFIG Config;
 UINT64 Frequency,Affinity;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(Frequency));__asm__ volatile("mrs %0,mpidr_el1":"=r"(Affinity));
 Print(L"NATIVE_XNU_CPU frequency=%lu affinity=%lx\r\n",Frequency,Affinity);
 UINT64 El;__asm__ volatile("mrs %0,CurrentEL":"=r"(El));(VOID)Table;
 UniXNULogInit();if(El!=4)Fail("need EL1",EFI_UNSUPPORTED);
 S=gBS->HandleProtocol(Image,&gEfiLoadedImageProtocolGuid,(VOID **)&Loaded);if(EFI_ERROR(S))Fail("parent",S);
 Path=FileDevicePath(Loaded->DeviceHandle,L"\\DarwinBoot.efi");if(!Path)Fail("driver path",EFI_OUT_OF_RESOURCES);
 S=gBS->LoadImage(FALSE,Image,Path,NULL,0,&Driver);FreePool(Path);if(EFI_ERROR(S))Fail("driver load",S);
 S=gBS->StartImage(Driver,NULL,NULL);if(EFI_ERROR(S))Fail("driver start",S);
 S=gBS->HandleProtocol(Driver,&gUniXNULoaderProtocolGuid,(VOID **)&Loader);
 if(EFI_ERROR(S)||Loader->Revision!=0x20000)Fail("v2 protocol",S);
 mGate=AllocatePages(1);if(!mGate)Fail("gate page",EFI_OUT_OF_RESOURCES);
 ZeroMem(mGate,EFI_PAGE_SIZE);mGate->Magic=0x4e41544956454731ULL;
 S=gBS->CreateEventEx(EVT_NOTIFY_SIGNAL,TPL_NOTIFY,ExitNotice,NULL,&gEfiEventExitBootServicesGuid,&Event);if(EFI_ERROR(S))Fail("exit notice",S);
 UniXNUConfigLoad(Image,&Config);
 if(Config.EntryCount!=1||Config.Error[0]||Config.Entries[0].Type!=UniXNUEntryXnu)Fail("config",EFI_COMPROMISED_DATA);
 Print(L"NATIVE_XNU_GATE %016lx\r\n",(UINT64)(UINTN)mGate);
 UniXNULog("NATIVE_XNU_READY unchanged host kernel via UniXNUBootEntry; QEMU only");
 S=UniXNUBootEntry(Image,&Config,&Config.Entries[0]);Fail("handoff returned",S);return EFI_ABORTED;
}
