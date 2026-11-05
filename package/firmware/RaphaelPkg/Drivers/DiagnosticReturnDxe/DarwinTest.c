// SPDX-License-Identifier: BSD-2-Clause-Patent
// Original FV loader with a temporary text log console. Default profile verifies
// invalid-input refusal; explicit native profile loads the frozen real kernel.
#include <RaphaelDiagnostic.h>
#include <RaphaelKernelWindow.h>
#include <Library/ArmLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/SemihostLib.h>
#include <Library/UefiLib.h>
#include <Guid/EventGroup.h>
#include <Library/BaseMemoryLib.h>
#include <Library/BaseLib.h>
#include <Library/PrintLib.h>
#include <Library/DebugLib.h>
#include <Library/DxeServicesLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Protocol/SimpleTextOut.h>
#include <Protocol/UniXNULoader.h>
#include <../Library/UniXNULib/Internal.h>

STATIC RAPHAEL_DIAGNOSTIC *mDiagnostic;
STATIC EFI_SIMPLE_TEXT_OUTPUT_MODE mMode = {1, 0, EFI_TEXT_ATTR (EFI_LIGHTGRAY, EFI_BLACK), 0, 0, FALSE};

STATIC EFI_STATUS EFIAPI TextReset (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, BOOLEAN Extended) {
  (VOID)This; (VOID)Extended;
  mMode.CursorColumn = 0; mMode.CursorRow = 0;
  return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI TextOutput (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, CHAR16 *Text) {
  EFI_STATUS Status = EFI_SUCCESS;
  (VOID)This;
  if (Text == NULL || mDiagnostic == NULL) { return EFI_INVALID_PARAMETER; }
  // UefiLib print has a fixed bound. Also bound this diagnostic provider for
  // malformed strings. This is a virtual log surface, never a pixel console.
  for (UINTN I = 0; I < 4096; ++I) {
    CHAR16 Wide = Text[I];
    if (Wide == 0) { return Status; }
    CHAR8 Byte = Wide < 128 ? (CHAR8)Wide : '?';
    if(FixedPcdGetBool(PcdRaphaelNativeQemuGate))SemihostWriteCharacter(Byte);
    if (Wide >= 128) { Status = EFI_WARN_UNKNOWN_GLYPH; }
    if (mDiagnostic->LogUsed < sizeof (mDiagnostic->Log)) {
      mDiagnostic->Log[mDiagnostic->LogUsed++] = Byte;
    } else { ++mDiagnostic->LogDropped; }
    ++mDiagnostic->Darwin.LogCharacters;
    if (Byte == '\n') { mMode.CursorRow = (mMode.CursorRow + 1) % 25; mMode.CursorColumn = 0; }
    else if (Byte == '\r') { mMode.CursorColumn = 0; }
    else { mMode.CursorColumn = (mMode.CursorColumn + 1) % 80; }
  }
  return EFI_BAD_BUFFER_SIZE;
}
STATIC EFI_STATUS EFIAPI TextTest (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, CHAR16 *Text) {
  (VOID)This;
  if (Text == NULL) { return EFI_INVALID_PARAMETER; }
  for (UINTN I = 0; I < 4096; ++I) {
    if (Text[I] == 0) { return EFI_SUCCESS; }
    if (Text[I] >= 128) { return EFI_UNSUPPORTED; }
  }
  return EFI_BAD_BUFFER_SIZE;
}
STATIC EFI_STATUS EFIAPI TextQuery (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, UINTN Mode, UINTN *Cols, UINTN *Rows) {
  (VOID)This;
  if (Cols == NULL || Rows == NULL) { return EFI_INVALID_PARAMETER; }
  if (Mode != 0) { return EFI_UNSUPPORTED; }
  // Virtual log geometry is a diagnostic design choice, not phone hardware.
  *Cols = 80; *Rows = 25; return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI TextMode (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, UINTN Mode) {
  if (Mode != 0) { return EFI_UNSUPPORTED; }
  return TextReset (This, FALSE);
}
STATIC EFI_STATUS EFIAPI TextAttribute (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, UINTN Attribute) {
  (VOID)This;
  if (Attribute > 0x7f) { return EFI_UNSUPPORTED; }
  mMode.Attribute = (INT32)Attribute; return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI TextClear (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This) { return TextReset (This, FALSE); }
STATIC EFI_STATUS EFIAPI TextCursor (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, UINTN Column, UINTN Row) {
  (VOID)This;
  if (Column >= 80 || Row >= 25) { return EFI_UNSUPPORTED; }
  mMode.CursorColumn = (INT32)Column; mMode.CursorRow = (INT32)Row; return EFI_SUCCESS;
}
STATIC EFI_STATUS EFIAPI TextVisible (EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, BOOLEAN Visible) {
  (VOID)This; mMode.CursorVisible = Visible; return EFI_SUCCESS;
}
STATIC EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL mText = {
  TextReset, TextOutput, TextTest, TextQuery, TextMode, TextAttribute,
  TextClear, TextCursor, TextVisible, &mMode
};
typedef struct {UINT64 Magic;volatile UINT64 Release;volatile UINT64 ExitCount;} NATIVE_GATE;
STATIC NATIVE_GATE *mGate;
STATIC EFI_EXIT_BOOT_SERVICES mOriginalExit;
STATIC EFI_BOOT_SERVICES *mOriginalServices;
STATIC VOID RestoreExitFunction(VOID) {
  if (!mOriginalExit) return;
  mOriginalServices->ExitBootServices = mOriginalExit;
  mOriginalServices->Hdr.CRC32 = 0;
  mOriginalServices->Hdr.CRC32 = CalculateCrc32(mOriginalServices, mOriginalServices->Hdr.HeaderSize);
}
STATIC EFI_STATUS EFIAPI ObserveExitReturn(EFI_HANDLE Image, UINTN Key) {
  // Restore the exact table before invoking the real core implementation.
  // No allocations or GetMemoryMap calls, so the loader's key is unchanged.
  RestoreExitFunction();
  EFI_STATUS Status = mOriginalExit(Image, Key);
  mOriginalExit = NULL;
  // The entry-test profile returns success to the unmodified DarwinEnter.
  // Otherwise record the real exit and enter the Android recovery capsule.
  if(RaphaelNativeExitReturned(Status, gST, mOriginalServices))return Status;
  return EFI_ABORTED;
}
STATIC __attribute__((noinline)) VOID NativeGateWait(VOID) {
 while(!mGate->Release){InvalidateDataCacheRange(mGate,EFI_PAGE_SIZE);CpuPause();}
 WriteBackDataCacheRange(mGate,EFI_PAGE_SIZE);
}
STATIC VOID EFIAPI ExitNotice (EFI_EVENT Event, VOID *Context) {
  (VOID)Event;
  if(FixedPcdGetBool(PcdRaphaelNativeLoadTest))RaphaelNativeLoadNotice();
  ((RAPHAEL_DARWIN_RESULT *)Context)->ExitBootServices = 1;
  if(FixedPcdGetBool(PcdRaphaelNativeQemuGate)&&mGate) {
    ++mGate->ExitCount;mGate->Release=0;
    WriteBackInvalidateDataCacheRange(mGate,EFI_PAGE_SIZE);
    NativeGateWait();
  }
}
STATIC EFI_STATUS TableCrc (VOID) {
  gST->Hdr.CRC32 = 0;
  return gBS->CalculateCrc32 (gST, gST->Hdr.HeaderSize, &gST->Hdr.CRC32);
}

EFI_STATUS RaphaelTestDarwin (EFI_HANDLE Image, RAPHAEL_DIAGNOSTIC *D) {
  RAPHAEL_DARWIN_RESULT *R = &D->Darwin;
  EFI_GUID DriverGuid = {0x1b64af87,0x8415,0x4b57,{0x9b,0x16,0x68,0x0d,0x70,0x91,0x3b,0x9f}};
  EFI_HANDLE Console = NULL, Driver = NULL;
  EFI_EVENT Event = NULL;
  EFI_STATUS Status;
  EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *SavedOut = gST->ConOut, *SavedErr = gST->StdErr;
  EFI_HANDLE SavedOutHandle = gST->ConsoleOutHandle, SavedErrHandle = gST->StandardErrorHandle;
  UNIXNU_LOADER_PROTOCOL *Loader = NULL;
  VOID *Pe = NULL;
  UINTN PeBytes = 0;
  UINT32 Crc = 0;
  UNIXNU_CONFIG Config;
  UNIXNU_LOADER_BOOT_REQUEST Request;
  UNIXNU_ENTRY Entry;
  R->Version = 1; R->Status = 2;
  if (D->Payload.Status != 3) { return EFI_NOT_READY; }
  Status = gBS->CalculateCrc32 ((VOID *)(UINTN)D->Payload.Base, D->Payload.Bytes, &Crc);
  if (EFI_ERROR (Status)) { return Status; }
  R->CrcBefore = Crc;
  Status = gBS->LocateProtocol (&gUniXNULoaderProtocolGuid, NULL, (VOID **)&Loader);
  if (Status != EFI_NOT_FOUND) { return EFI_ALREADY_STARTED; }
  mDiagnostic = D;
  Status = gBS->InstallMultipleProtocolInterfaces (&Console, &gEfiSimpleTextOutProtocolGuid, &mText, NULL);
  if (EFI_ERROR (Status)) { goto Done; }
  R->ConsoleInstalled = 1;
  gST->ConOut = &mText; gST->StdErr = &mText;
  gST->ConsoleOutHandle = Console; gST->StandardErrorHandle = Console;
  Status = TableCrc ();
  if (EFI_ERROR (Status)) { goto Done; }
  Status = gBS->CreateEventEx (EVT_NOTIFY_SIGNAL, TPL_NOTIFY, ExitNotice, R,
                              (FixedPcdGetBool(PcdRaphaelNativeLoadTest)&&!FixedPcdGetBool(PcdRaphaelNativeExitComplete))?&gEfiEventBeforeExitBootServicesGuid:&gEfiEventExitBootServicesGuid, &Event);
  if (EFI_ERROR (Status)) { goto Done; }
  // Stored as FREEFORM/PE32: DXE dispatcher must not start it before the
  // temporary console exists. LoadImage performs the actual relocation.
  Status = GetSectionFromAnyFv (&DriverGuid, EFI_SECTION_PE32, 0, &Pe, &PeBytes);
  if (EFI_ERROR (Status)) { goto Done; }
  Status = gBS->LoadImage (FALSE, Image, NULL, Pe, PeBytes, &Driver);
  FreePool (Pe); Pe = NULL;
  if (EFI_ERROR (Status)) { Driver = NULL; goto Done; }
  R->DriverLoaded = 1;
  Status = gBS->StartImage (Driver, NULL, NULL);
  if (EFI_ERROR (Status)) { Driver = NULL; goto Done; }
  R->DriverStarted = 1;
  Status = gBS->HandleProtocol (Driver, &gUniXNULoaderProtocolGuid, (VOID **)&Loader);
  if (EFI_ERROR (Status) || Loader == NULL || Loader->Boot == NULL) { Status = EFI_NOT_FOUND; goto Done; }
  R->ProtocolRevision = Loader->Revision;
  if (Loader->Revision != UNIXNU_LOADER_REVISION) { Status = EFI_UNSUPPORTED; goto Done; }
  if(FixedPcdGetBool(PcdRaphaelNativeHandoff)||FixedPcdGetBool(PcdRaphaelNativeLoadTest)) {
    UniXNUConfigLoad(Image,&Config);
    if(Config.Volume==NULL||Config.Error[0]||Config.EntryCount!=1){Status=EFI_COMPROMISED_DATA;goto Done;}
    if(FixedPcdGetBool(PcdRaphaelNativeQemuGate)) {
      mGate=AllocatePages(1);if(!mGate){Status=EFI_OUT_OF_RESOURCES;goto Done;}
      ZeroMem(mGate,EFI_PAGE_SIZE);mGate->Magic=0x4e41544956454731ULL;
      Print(L"NATIVE_XNU_CPU frequency=%lu affinity=%lx\r\n",D->Cntfrq,D->Mpidr);
      Print(L"NATIVE_XNU_GATE %016lx\r\n",(UINT64)(UINTN)mGate);
      Print(L"NATIVE_XNU_ALLOCATOR alloc=%lx free=%lx wait=%lx\r\n",(UINT64)(UINTN)gBS->AllocatePool,(UINT64)(UINTN)gBS->FreePool,(UINT64)(UINTN)NativeGateWait);
      Print(L"NATIVE_XNU_PRELOAD_GATE\r\n");
      WriteBackInvalidateDataCacheRange(mGate,EFI_PAGE_SIZE);NativeGateWait();
    }
    ZeroMem(&Entry,sizeof(Entry));Entry.Id="native-mainline";Entry.Title=L"Native XNU";
    Entry.Type=UniXNUEntryXnu;Entry.Volume=Config.Volume;
    Entry.Path=L"\\EFI\\UniXNU\\kernel.macho";Entry.Args=FixedPcdGetBool(PcdRaphaelNativeQemuGate)?L"-v keepsyms=1 cpus=1 kt_fixed_zones=200":L"-v keepsyms=1 cpus=1";
    CHAR16 NativeArgs[96];
    if(FixedPcdGet32(PcdRaphaelNativeKallocZones)){
      UnicodeSPrint(NativeArgs,sizeof(NativeArgs),L"-v keepsyms=1 cpus=1 kt_fixed_zones=%u",FixedPcdGet32(PcdRaphaelNativeKallocZones));Entry.Args=NativeArgs;
    }
    if(FixedPcdGetBool(PcdRaphaelNativeLoadTest)) {
      Status=RaphaelPrepareNativeLoad();if(EFI_ERROR(Status))goto Done;
    }
    if(FixedPcdGetBool(PcdRaphaelNativeLoadTest) && RaphaelNativeHasData())Entry.Initrd=L"\\EFI\\UniXNU\\data.packed";
    Status=RaphaelReleaseKernelWindow();if(EFI_ERROR(Status))goto Done;
    Print(L"NATIVE_XNU_READY own SEC/DXE; original DarwinBoot\r\n");
    if(FixedPcdGetBool(PcdRaphaelNativeExitComplete)) {
      mOriginalServices=gBS; mOriginalExit=gBS->ExitBootServices;
      gBS->ExitBootServices=ObserveExitReturn;
      gBS->Hdr.CRC32=0;gBS->Hdr.CRC32=CalculateCrc32(gBS,gBS->Hdr.HeaderSize);
    }
    R->UniXnuStatus=UniXNUBootEntry(Image,&Config,&Entry);
    if(mOriginalExit){RestoreExitFunction();mOriginalExit=NULL;}
    EFI_STATUS Restore=RaphaelRestoreKernelWindow();
    Status=EFI_ERROR(Restore)?Restore:R->UniXnuStatus;
    // A valid kernel handoff never returns. Returning success is a failure.
    if(!EFI_ERROR(Status))Status=EFI_ABORTED;
    goto Done;
  }
  R->NullStatus = Loader->Boot (Loader, NULL);
  UniXNUConfigLoad (Image, &Config);
  if (Config.Volume == NULL || Config.Error[0] != 0 || Config.EntryCount != 1) { Status = EFI_COMPROMISED_DATA; goto Done; }
  ZeroMem (&Request, sizeof (Request));
  Request.Volume = Config.Volume; Request.KernelPath = L"\\missing.macho";
  R->MissingStatus = Loader->Boot (Loader, &Request);
  Request.KernelPath = L"\\EFI\\UniXNU\\invalid.macho";
  R->InvalidStatus = Loader->Boot (Loader, &Request);
  ZeroMem (&Entry, sizeof (Entry));
  Entry.Id = "darwin-negative"; Entry.Title = L"Reject invalid kernel";
  Entry.Type = UniXNUEntryXnu; Entry.Volume = Config.Volume;
  Entry.Path = (CHAR16 *)Request.KernelPath; Entry.Args = L"diagnostic-invalid-only";
  R->UniXnuStatus = UniXNUBootEntry (Image, &Config, &Entry);
  VOID *Buffer = AllocateZeroPool (73);
  if (Buffer != NULL) {
    Status = gBS->CalculateCrc32 (Buffer, 73, &Crc); FreePool (Buffer);
    R->ServicesAlive = !EFI_ERROR (Status);
  }
  Status = gBS->CalculateCrc32 ((VOID *)(UINTN)D->Payload.Base, D->Payload.Bytes, &Crc);
  if (EFI_ERROR (Status)) { goto Done; }
  R->CrcAfter = Crc;
  Status = R->NullStatus == EFI_INVALID_PARAMETER && R->MissingStatus == EFI_NOT_FOUND &&
           R->InvalidStatus == EFI_LOAD_ERROR && R->UniXnuStatus == EFI_LOAD_ERROR &&
           R->ServicesAlive && !R->ExitBootServices && R->CrcBefore == R->CrcAfter ? EFI_SUCCESS : EFI_COMPROMISED_DATA;
Done:
  if (Pe != NULL) { FreePool (Pe); }
  if (Driver != NULL) {
    EFI_STATUS Unload = gBS->UnloadImage (Driver);
    R->Unloaded = !EFI_ERROR (Unload);
    if (EFI_ERROR (Unload)) { Status = Unload; }
  }
  Loader = NULL;
  R->ProtocolRemoved = gBS->LocateProtocol (&gUniXNULoaderProtocolGuid, NULL, (VOID **)&Loader) == EFI_NOT_FOUND;
  if (Event != NULL) { gBS->CloseEvent (Event); }
  if (R->ConsoleInstalled) {
    gST->ConOut = SavedOut; gST->StdErr = SavedErr;
    gST->ConsoleOutHandle = SavedOutHandle; gST->StandardErrorHandle = SavedErrHandle;
    EFI_STATUS Restore = TableCrc ();
    EFI_STATUS Remove = gBS->UninstallMultipleProtocolInterfaces (Console, &gEfiSimpleTextOutProtocolGuid, &mText, NULL);
    R->ConsoleRestored = !EFI_ERROR (Restore) && !EFI_ERROR (Remove) && gST->ConOut == SavedOut && gST->StdErr == SavedErr;
    if (!R->ConsoleRestored) { Status = EFI_COMPROMISED_DATA; }
  }
  mDiagnostic = NULL;
  if (!EFI_ERROR (Status) && R->Unloaded && R->ProtocolRemoved && R->ConsoleRestored && R->LogCharacters != 0) { R->Status = 3; }
  else if (!EFI_ERROR (Status)) { Status = EFI_COMPROMISED_DATA; }
  DEBUG ((DEBUG_INFO, "RAPHAEL Darwin status=%lu loaded/started=%lu/%lu revision=%lx exitbs=%lu restored=%lu error=%r\n",
    R->Status, R->DriverLoaded, R->DriverStarted, R->ProtocolRevision, R->ExitBootServices, R->ConsoleRestored, Status));
  return Status;
}
