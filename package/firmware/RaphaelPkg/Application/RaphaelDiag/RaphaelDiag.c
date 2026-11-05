// SPDX-License-Identifier: BSD-2-Clause-Patent
// Protocol-only diagnostics. No board MMIO addresses or partition writes.
#include <Uefi.h>
#include <Protocol/GraphicsOutput.h>
#include <Protocol/SerialIo.h>

static EFI_SYSTEM_TABLE *mSystemTable;
static EFI_SERIAL_IO_PROTOCOL *mSerial;
static EFI_GUID mGopGuid = EFI_GRAPHICS_OUTPUT_PROTOCOL_GUID;
static EFI_GUID mSerialGuid = EFI_SERIAL_IO_PROTOCOL_GUID;
// Keep an address-bearing build tag so PE relocation handling is exercised.
static CONST CHAR16 * volatile mBuildTag = L"RAPHAEL:DIAG:entered version=1\r\n";

static VOID
Log(CONST CHAR16 *Message)
{
  CHAR8 Bytes[192];
  UINTN Index;
  UINTN Count;

  if (mSystemTable->ConOut != NULL) {
    mSystemTable->ConOut->OutputString(mSystemTable->ConOut, (CHAR16 *)Message);
  }
  if (mSerial != NULL) {
    Index = 0;
    while ((Message[Index] != 0) && (Index < sizeof(Bytes))) {
      Bytes[Index] = (Message[Index] < 0x80) ? (CHAR8)Message[Index] : '?';
      Index++;
    }
    Count = Index;
    mSerial->Write(mSerial, &Count, Bytes);
  }
}

static VOID
Hex(CONST CHAR16 *Label, UINT64 Value)
{
  CHAR16 Text[19];
  CONST CHAR16 *Digits = L"0123456789abcdef";
  UINTN Index;

  Text[0] = '0';
  Text[1] = 'x';
  for (Index = 0; Index < 16; Index++) {
    Text[Index + 2] = Digits[(Value >> ((15 - Index) * 4)) & 15];
  }
  Text[18] = 0;
  Log(Label);
  Log(Text);
  Log(L"\r\n");
}

static VOID
ReportGop(VOID)
{
  EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop;
  EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *Info;
  EFI_STATUS Status;

  Gop = NULL;
  Status = mSystemTable->BootServices->LocateProtocol(&mGopGuid, NULL, (VOID **)&Gop);
  Hex(L"RAPHAEL:GOP:locate=", Status);
  if (EFI_ERROR(Status) || (Gop == NULL) || (Gop->Mode == NULL) ||
      (Gop->Mode->Info == NULL)) {
    Log(L"RAPHAEL:GOP:unavailable\r\n");
    return;
  }
  Info = Gop->Mode->Info;
  Hex(L"RAPHAEL:GOP:width=", Info->HorizontalResolution);
  Hex(L"RAPHAEL:GOP:height=", Info->VerticalResolution);
  Hex(L"RAPHAEL:GOP:pixels-per-scanline=", Info->PixelsPerScanLine);
  Hex(L"RAPHAEL:GOP:format=", Info->PixelFormat);
  Hex(L"RAPHAEL:GOP:framebuffer-base=", Gop->Mode->FrameBufferBase);
  Hex(L"RAPHAEL:GOP:framebuffer-bytes=", Gop->Mode->FrameBufferSize);
  Log(L"RAPHAEL:GOP:observation-only; no SetMode or framebuffer store\r\n");
}

static VOID
ReportMemory(VOID)
{
  EFI_BOOT_SERVICES *Bs;
  EFI_MEMORY_DESCRIPTOR *Map;
  EFI_MEMORY_DESCRIPTOR *Entry;
  EFI_STATUS Status;
  UINTN Capacity;
  UINTN Bytes;
  UINTN Key;
  UINTN Stride;
  UINT32 Version;
  UINTN Offset;
  UINTN Attempt;

  Bs = mSystemTable->BootServices;
  Bytes = 0;
  Stride = 0;
  Status = Bs->GetMemoryMap(&Bytes, NULL, &Key, &Stride, &Version);
  if ((Status != EFI_BUFFER_TOO_SMALL) || (Stride < sizeof(EFI_MEMORY_DESCRIPTOR)) ||
      (Stride > 4096) || (Bytes > 16 * 1024 * 1024)) {
    Hex(L"RAPHAEL:MEMORY:query-failed=", Status);
    return;
  }
  for (Attempt = 0; Attempt < 3; Attempt++) {
    Capacity = Bytes + 8 * Stride;
    Map = NULL;
    Status = Bs->AllocatePool(EfiLoaderData, Capacity, (VOID **)&Map);
    if (EFI_ERROR(Status)) {
      Hex(L"RAPHAEL:MEMORY:allocate-failed=", Status);
      return;
    }
    Bytes = Capacity;
    Status = Bs->GetMemoryMap(&Bytes, Map, &Key, &Stride, &Version);
    if (!EFI_ERROR(Status)) {
      if ((Stride < sizeof(EFI_MEMORY_DESCRIPTOR)) || (Bytes > Capacity) ||
          ((Bytes % Stride) != 0)) {
        Log(L"RAPHAEL:MEMORY:malformed-map\r\n");
        Bs->FreePool(Map);
        return;
      }
      Hex(L"RAPHAEL:MEMORY:descriptor-version=", Version);
      Hex(L"RAPHAEL:MEMORY:count=", Bytes / Stride);
      for (Offset = 0; Offset < Bytes; Offset += Stride) {
        Entry = (EFI_MEMORY_DESCRIPTOR *)((UINT8 *)Map + Offset);
        Hex(L"RAPHAEL:MEMORY:type=", Entry->Type);
        Hex(L"  base=", Entry->PhysicalStart);
        Hex(L"  pages=", Entry->NumberOfPages);
        Hex(L"  attributes=", Entry->Attribute);
      }
      Bs->FreePool(Map);
      return;
    }
    Bs->FreePool(Map);
    if ((Status != EFI_BUFFER_TOO_SMALL) || (Bytes > 16 * 1024 * 1024)) {
      break;
    }
  }
  Hex(L"RAPHAEL:MEMORY:failed=", Status);
}

EFI_STATUS EFIAPI
RaphaelDiagEntry(IN EFI_HANDLE ImageHandle, IN EFI_SYSTEM_TABLE *SystemTable)
{
  EFI_EVENT Events[2];
  EFI_EVENT Timer;
  EFI_INPUT_KEY Key;
  EFI_STATUS Status;
  UINTN Index;
  UINT64 Register;

  (VOID)ImageHandle;
  if ((SystemTable == NULL) || (SystemTable->Hdr.Signature != EFI_SYSTEM_TABLE_SIGNATURE) ||
      (SystemTable->BootServices == NULL)) {
    return EFI_INVALID_PARAMETER;
  }
  mSystemTable = SystemTable;
  mSerial = NULL;
  SystemTable->BootServices->LocateProtocol(&mSerialGuid, NULL, (VOID **)&mSerial);
  Log(mBuildTag);
  Hex(L"RAPHAEL:UEFI:revision=", SystemTable->Hdr.Revision);
  __asm__ volatile ("mrs %0, CurrentEL" : "=r"(Register));
  Hex(L"RAPHAEL:CPU:CurrentEL=", Register >> 2);
  __asm__ volatile ("mrs %0, cntfrq_el0" : "=r"(Register));
  Hex(L"RAPHAEL:CPU:counter-frequency=", Register);
  ReportGop();
  ReportMemory();
  if ((SystemTable->ConIn == NULL) || (SystemTable->ConIn->WaitForKey == NULL)) {
    Log(L"RAPHAEL:INPUT:unavailable\r\n");
    return EFI_SUCCESS;
  }
  Log(L"RAPHAEL:MENU: G=GOP M=memory Q=return; log scan/unicode for keys\r\n");
  Timer = NULL;
  Status = SystemTable->BootServices->CreateEvent(EVT_TIMER, TPL_APPLICATION, NULL, NULL, &Timer);
  if (EFI_ERROR(Status)) {
    return Status;
  }
  // Fifteen seconds after entering the menu; return even if input is absent.
  Status = SystemTable->BootServices->SetTimer(Timer, TimerRelative, 150000000);
  if (!EFI_ERROR(Status)) {
    Events[0] = SystemTable->ConIn->WaitForKey;
    Events[1] = Timer;
    while (TRUE) {
      Status = SystemTable->BootServices->WaitForEvent(2, Events, &Index);
      if (EFI_ERROR(Status) || (Index == 1)) {
        Log(L"RAPHAEL:MENU:timeout-or-wait-error\r\n");
        break;
      }
      Status = SystemTable->ConIn->ReadKeyStroke(SystemTable->ConIn, &Key);
      if (EFI_ERROR(Status)) {
        continue;
      }
      Hex(L"RAPHAEL:INPUT:scan=", Key.ScanCode);
      Hex(L"RAPHAEL:INPUT:unicode=", Key.UnicodeChar);
      if ((Key.UnicodeChar == 'q') || (Key.UnicodeChar == 'Q')) {
        break;
      } else if ((Key.UnicodeChar == 'g') || (Key.UnicodeChar == 'G')) {
        ReportGop();
      } else if ((Key.UnicodeChar == 'm') || (Key.UnicodeChar == 'M')) {
        ReportMemory();
      }
    }
  }
  SystemTable->BootServices->CloseEvent(Timer);
  Log(L"RAPHAEL:DIAG:return-to-firmware\r\n");
  return Status;
}
