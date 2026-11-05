// SPDX-License-Identifier: BSD-2-Clause-Patent
// Emulator-only negative interface checks against the unchanged DarwinBoot driver.
// The runner supplies only empty, truncated or invalid Mach-O input, never a kernel.
#include <Uefi.h>
#include <Guid/EventGroup.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DevicePathLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiRuntimeServicesTableLib.h>
#include <../Library/UniXNULib/Internal.h>
#include <Protocol/LoadedImage.h>
#include <Protocol/UniXNULoader.h>

STATIC UINTN mPass;
STATIC UINTN mFail;
STATIC BOOLEAN mExited;

STATIC VOID
Check (CONST CHAR8 *Name, BOOLEAN Good)
{
  UniXNULog ("DARWIN_FIXTURE_%a %a", Good ? "PASS" : "FAIL", Name);
  if (Good) { ++mPass; } else { ++mFail; }
}

STATIC VOID EFIAPI
ExitNotice (EFI_EVENT Event, VOID *Context)
{
  (VOID)Event;
  (VOID)Context;
  mExited = TRUE;
}

STATIC BOOLEAN
BootServicesAlive (VOID)
{
  VOID *Buffer;
  EFI_STATUS Status;
  UINT32 Crc;
  if (mExited || (gBS->Hdr.Signature != EFI_BOOT_SERVICES_SIGNATURE)) { return FALSE; }
  Buffer = AllocateZeroPool (73);
  if (Buffer == NULL) { return FALSE; }
  Status = gBS->CalculateCrc32 (Buffer, 73, &Crc);
  FreePool (Buffer);
  return !EFI_ERROR (Status);
}

STATIC VOID
ExpectBoot (UNIXNU_LOADER_PROTOCOL *Loader, CONST CHAR8 *Name,
            CONST UNIXNU_LOADER_BOOT_REQUEST *Request, EFI_STATUS Expected)
{
  EFI_STATUS Status = Loader->Boot (Loader, Request);
  UniXNULog ("DARWIN_FIXTURE_STATUS %a actual=%r expected=%r", Name, Status, Expected);
  Check (Name, (Status == Expected) && BootServicesAlive ());
}

STATIC EFI_STATUS
StartDriver (EFI_HANDLE Parent, EFI_HANDLE Volume, EFI_HANDLE *Driver)
{
  EFI_DEVICE_PATH_PROTOCOL *Path;
  EFI_STATUS Status;
  *Driver = NULL;
  Path = FileDevicePath (Volume, L"\\DarwinBoot.efi");
  if (Path == NULL) { return EFI_OUT_OF_RESOURCES; }
  Status = gBS->LoadImage (FALSE, Parent, Path, NULL, 0, Driver);
  FreePool (Path);
  if (!EFI_ERROR (Status)) { Status = gBS->StartImage (*Driver, NULL, NULL); }
  return Status;
}

EFI_STATUS EFIAPI
DarwinFixtureEntry (EFI_HANDLE Image, EFI_SYSTEM_TABLE *Table)
{
  EFI_STATUS Status;
  EFI_LOADED_IMAGE_PROTOCOL *Loaded;
  EFI_LOADED_IMAGE_PROTOCOL *DriverLoaded;
  EFI_HANDLE Driver = NULL;
  EFI_HANDLE Duplicate = NULL;
  UNIXNU_LOADER_PROTOCOL *Loader = NULL;
  UNIXNU_LOADER_PROTOCOL *Again = NULL;
  UNIXNU_LOADER_BOOT_REQUEST Request;
  UNIXNU_CONFIG Config;
  EFI_EVENT ExitEvent = NULL;
  UINT8 Byte = 0;
  UINT8 BadPacked[32] = {0};
  CHAR16 LongArgs[1025];
  CHAR16 NonAscii[] = {0x100, 0};
  UINT64 CurrentEl;
  (VOID)Table;

  UniXNULogInit ();
  UniXNULog ("DARWIN_FIXTURE_START unchanged driver; invalid inputs only; no OS profile");
  __asm__ volatile ("mrs %0, CurrentEL" : "=r" (CurrentEl));
  Check ("AAVMF execution is EL1", CurrentEl == 4);
  if (CurrentEl != 4) { goto Failed; }
  Status = gBS->CreateEventEx (EVT_NOTIFY_SIGNAL, TPL_NOTIFY, ExitNotice, NULL,
                              &gEfiEventExitBootServicesGuid, &ExitEvent);
  Check ("ExitBootServices notification armed", !EFI_ERROR (Status));
  if (EFI_ERROR (Status)) { goto Failed; }
  Status = gBS->HandleProtocol (Image, &gEfiLoadedImageProtocolGuid, (VOID **)&Loaded);
  if (EFI_ERROR (Status)) { goto Failed; }
  Status = StartDriver (Image, Loaded->DeviceHandle, &Driver);
  Check ("LoadImage and StartImage driver", !EFI_ERROR (Status));
  if (EFI_ERROR (Status)) { goto Failed; }
  Status = gBS->HandleProtocol (Driver, &gUniXNULoaderProtocolGuid, (VOID **)&Loader);
  Check ("loader v2 on actual image handle", !EFI_ERROR (Status) && Loader != NULL &&
         Loader->Revision == UNIXNU_LOADER_REVISION && Loader->Boot != NULL);
  if (EFI_ERROR (Status) || Loader == NULL || Loader->Boot == NULL) { goto Failed; }
  Status = gBS->HandleProtocol (Driver, &gEfiLoadedImageProtocolGuid, (VOID **)&DriverLoaded);
  Check ("driver has unload callback and correct parent", !EFI_ERROR (Status) &&
         DriverLoaded->Unload != NULL && DriverLoaded->ParentHandle == Image);
  Status = StartDriver (Image, Loaded->DeviceHandle, &Duplicate);
  Check ("duplicate driver start rejected", Status == EFI_ALREADY_STARTED);
  Status = gBS->LocateProtocol (&gUniXNULoaderProtocolGuid, NULL, (VOID **)&Again);
  Check ("duplicate leaves original protocol", !EFI_ERROR (Status) && Again == Loader);

  ZeroMem (&Request, sizeof (Request));
  ExpectBoot (Loader, "NULL request rejected", NULL, EFI_INVALID_PARAMETER);
  Request.KernelPath = L"\\missing.macho";
  ExpectBoot (Loader, "missing volume rejected", &Request, EFI_INVALID_PARAMETER);
  Request.Volume = Loaded->DeviceHandle;
  Request.KernelPath = NULL;
  ExpectBoot (Loader, "missing path rejected", &Request, EFI_INVALID_PARAMETER);
  Request.KernelPath = L"\\missing.macho";
  Request.KextCount = 1;
  ExpectBoot (Loader, "staged kexts refused", &Request, EFI_UNSUPPORTED);
  Request.KextCount = 0;
  Request.DeviceTree = &Byte;
  ExpectBoot (Loader, "request FDT pointer refused", &Request, EFI_UNSUPPORTED);
  Request.DeviceTree = NULL;
  Request.DeviceTreeSize = 1;
  ExpectBoot (Loader, "request FDT size refused", &Request, EFI_UNSUPPORTED);
  Request.DeviceTreeSize = 0;
  Request.RamdiskSize = 1;
  ExpectBoot (Loader, "NULL ramdisk with length refused", &Request, EFI_BAD_BUFFER_SIZE);
  Request.RamdiskSize = 0;
  Request.Ramdisk = &Byte;
  ExpectBoot (Loader, "ramdisk without length refused", &Request, EFI_BAD_BUFFER_SIZE);
  CopyMem (BadPacked, "DBRDISK1", 8);
  Request.Ramdisk = BadPacked;
  Request.RamdiskSize = sizeof (BadPacked);
  ExpectBoot (Loader, "invalid packed ramdisk refused", &Request, EFI_BAD_BUFFER_SIZE);
  Request.Ramdisk = NULL;
  Request.RamdiskSize = 0;
  Request.BootArgs = NonAscii;
  ExpectBoot (Loader, "non ASCII arguments refused", &Request, EFI_BAD_BUFFER_SIZE);
  for (UINTN I = 0; I < 1024; ++I) { LongArgs[I] = L'a'; }
  LongArgs[1024] = 0;
  Request.BootArgs = LongArgs;
  ExpectBoot (Loader, "1024 character arguments refused", &Request, EFI_BAD_BUFFER_SIZE);
  LongArgs[1023] = 0;
  ExpectBoot (Loader, "1023 character arguments reach file lookup", &Request, EFI_NOT_FOUND);
  Request.BootArgs = NULL;
  Request.Volume = Image;
  ExpectBoot (Loader, "volume without filesystem refused", &Request, EFI_UNSUPPORTED);
  Request.Volume = Loaded->DeviceHandle;
  ExpectBoot (Loader, "missing kernel returns to firmware", &Request, EFI_NOT_FOUND);

  struct { CONST CHAR8 *Name; CONST CHAR16 *Path; EFI_STATUS Expected; } Cases[] = {
    { "empty file refused", L"\\EFI\\UniXNU\\Cases\\empty.macho", EFI_BAD_BUFFER_SIZE },
    { "truncated header refused", L"\\EFI\\UniXNU\\Cases\\tiny.macho", EFI_UNSUPPORTED },
    { "non Mach-O header refused", L"\\EFI\\UniXNU\\Cases\\zero.macho", EFI_UNSUPPORTED },
    { "wrong CPU refused", L"\\EFI\\UniXNU\\Cases\\wrong-cpu.macho", EFI_UNSUPPORTED },
    { "command bytes outside file refused", L"\\EFI\\UniXNU\\Cases\\overflow.macho", EFI_LOAD_ERROR },
    { "missing command bytes refused", L"\\EFI\\UniXNU\\Cases\\truncated-command.macho", EFI_LOAD_ERROR },
    { "command size outside table refused", L"\\EFI\\UniXNU\\Cases\\bad-command.macho", EFI_LOAD_ERROR },
    { "kernel without segments or entry refused", L"\\EFI\\UniXNU\\Cases\\no-entry.macho", EFI_LOAD_ERROR },
    { "directory refused as kernel", L"\\EFI\\UniXNU\\Cases", EFI_BAD_BUFFER_SIZE }
  };
  for (UINTN I = 0; I < ARRAY_SIZE (Cases); ++I) {
    Request.KernelPath = Cases[I].Path;
    ExpectBoot (Loader, Cases[I].Name, &Request, Cases[I].Expected);
  }

  UniXNUConfigLoad (Image, &Config);
  Check ("xnu entry parsed from fixture config", Config.Error[0] == 0 &&
         Config.EntryCount == 1 && Config.Entries[0].Type == UniXNUEntryXnu &&
         Config.Entries[0].Volume == Loaded->DeviceHandle);
  if (Config.EntryCount != 1 || Config.Entries[0].Type != UniXNUEntryXnu) { goto Failed; }
  Status = UniXNUBootEntry (Image, &Config, &Config.Entries[0]);
  Check ("actual UniXNU to DarwinBoot returns parse error", Status == EFI_LOAD_ERROR && BootServicesAlive ());
  Check ("no ExitBootServices during all requests", !mExited && BootServicesAlive ());
  Status = gBS->UnloadImage (Driver);
  Check ("UnloadImage succeeds", !EFI_ERROR (Status));
  if (!EFI_ERROR (Status)) { Driver = NULL; }
  Status = gBS->LocateProtocol (&gUniXNULoaderProtocolGuid, NULL, (VOID **)&Again);
  Check ("unload removes loader protocol", Status == EFI_NOT_FOUND);
  Status = UniXNUBootEntry (Image, &Config, &Config.Entries[0]);
  Check ("UniXNU refuses boot with loader absent", Status == EFI_UNSUPPORTED && BootServicesAlive ());
  Status = StartDriver (Image, Loaded->DeviceHandle, &Driver);
  Check ("driver reload after unload succeeds", !EFI_ERROR (Status));
  if (!EFI_ERROR (Status)) {
    Status = gBS->UnloadImage (Driver);
    Check ("reloaded driver unload succeeds", !EFI_ERROR (Status));
    if (!EFI_ERROR (Status)) { Driver = NULL; }
  }
  if (ExitEvent != NULL) { gBS->CloseEvent (ExitEvent); }
  UniXNULog ("DARWIN_FIXTURE_RESULT passed=%u failed=%u ebs=%u", (UINT32)mPass, (UINT32)mFail, mExited);
  UniXNULog ("DARWIN_FIXTURE_%a", mFail ? "FAILED" : "OK");
  gRT->ResetSystem (EfiResetShutdown, mFail ? EFI_ABORTED : EFI_SUCCESS, 0, NULL);
  return mFail ? EFI_ABORTED : EFI_SUCCESS;
Failed:
  UniXNULog ("DARWIN_FIXTURE_FAILED early passed=%u failed=%u", (UINT32)mPass, (UINT32)mFail);
  gRT->ResetSystem (EfiResetShutdown, EFI_ABORTED, 0, NULL);
  return EFI_ABORTED;
}
