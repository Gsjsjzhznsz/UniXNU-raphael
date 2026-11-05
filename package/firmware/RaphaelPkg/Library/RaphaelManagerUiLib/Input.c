// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelManagerInputLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/DebugLib.h>

STATIC VOID Poll(RAPHAEL_MANAGER_INPUT *S) {
  if (S->HavePending) return;
  if (S->Counter() >= S->Deadline) {
    S->Pending.ScanCode = SCAN_NULL;
    S->Pending.UnicodeChar = CHAR_CARRIAGE_RETURN;
    S->HavePending = S->Synthetic = TRUE;
    return;
  }
  EFI_STATUS Status = gBS->CheckEvent(S->Real->WaitForKey);
  if (Status == EFI_NOT_READY) return;
  if (EFI_ERROR(Status)) { ++S->Errors; return; }
  Status = S->Real->ReadKeyStroke(S->Real, &S->Pending);
  if (!EFI_ERROR(Status)) {
    S->HavePending = TRUE;
    S->Synthetic = FALSE;
  } else if (Status != EFI_NOT_READY) {
    ++S->Errors;
  }
}
STATIC EFI_STATUS EFIAPI Reset(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, BOOLEAN Extended) {
  if (!This) return EFI_INVALID_PARAMETER;
  RAPHAEL_MANAGER_INPUT *S = BASE_CR(This, RAPHAEL_MANAGER_INPUT, Protocol);
  S->HavePending = FALSE;
  // A reset cannot extend the deadline or erase the physical-key evidence.
  return S->Real->Reset(S->Real, Extended);
}
STATIC EFI_STATUS EFIAPI Read(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, EFI_INPUT_KEY *Key) {
  if (!This || !Key) return EFI_INVALID_PARAMETER;
  RAPHAEL_MANAGER_INPUT *S = BASE_CR(This, RAPHAEL_MANAGER_INPUT, Protocol);
  Poll(S);
  if (!S->HavePending) return EFI_NOT_READY;
  *Key = S->Pending;
  S->HavePending = FALSE;
  ++S->Delivered;
  if (S->Synthetic) ++S->Automatic;
  else if (Key->ScanCode == SCAN_UP && !Key->UnicodeChar) ++S->Up;
  else if (Key->ScanCode == SCAN_DOWN && !Key->UnicodeChar) ++S->Down;
  else if (Key->ScanCode == SCAN_NULL && Key->UnicodeChar == CHAR_CARRIAGE_RETURN) ++S->Enter;
  DEBUG((DEBUG_INFO, "RAPHAEL manager key scan=%u unicode=%u automatic=%u ticks=%lu\n",
    (UINT32)Key->ScanCode, (UINT32)Key->UnicodeChar, (UINT32)S->Synthetic, S->Counter()-S->Start));
  return EFI_SUCCESS;
}
STATIC VOID EFIAPI Wait(EFI_EVENT Event, VOID *Context) {
  RAPHAEL_MANAGER_INPUT *S = Context;
  Poll(S);
  if (S->HavePending) gBS->SignalEvent(Event);
}
EFI_STATUS RaphaelManagerInputBegin(RAPHAEL_MANAGER_INPUT *S,
  EFI_SIMPLE_TEXT_INPUT_PROTOCOL *Real, RAPHAEL_INPUT_COUNTER Counter,
  UINT64 Frequency, UINTN Seconds) {
  if (!S || !Real || !Real->Reset || !Real->ReadKeyStroke || !Real->WaitForKey || !Counter ||
      !Frequency || Seconds != 6 || Frequency > MAX_UINT64/Seconds)
    return EFI_INVALID_PARAMETER;
  if (S->Protocol.WaitForKey) return EFI_ALREADY_STARTED;
  UINT64 Start = Counter(), Ticks = Frequency*Seconds;
  if (!Start || Start > MAX_UINT64-Ticks) return EFI_UNSUPPORTED;
  ZeroMem(S, sizeof(*S));
  S->Real=Real; S->Counter=Counter; S->Frequency=Frequency;
  S->Start=Start; S->Deadline=Start+Ticks;
  S->Protocol.Reset=Reset; S->Protocol.ReadKeyStroke=Read;
  EFI_STATUS Status = gBS->CreateEvent(EVT_NOTIFY_WAIT, TPL_CALLBACK, Wait, S, &S->Protocol.WaitForKey);
  if (!EFI_ERROR(Status)) DEBUG((DEBUG_INFO, "RAPHAEL manager input start=%lu deadline=%lu frequency=%lu\n", Start, S->Deadline, Frequency));
  return Status;
}
EFI_STATUS RaphaelManagerInputEnd(RAPHAEL_MANAGER_INPUT *S) {
  if (!S || !S->Protocol.WaitForKey) return EFI_NOT_READY;
  EFI_STATUS Status = gBS->CloseEvent(S->Protocol.WaitForKey);
  if (!EFI_ERROR(Status)) S->Protocol.WaitForKey=NULL;
  return Status;
}
