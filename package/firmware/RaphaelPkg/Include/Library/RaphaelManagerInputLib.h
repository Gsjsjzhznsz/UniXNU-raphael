// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_MANAGER_INPUT_LIB_H
#define RAPHAEL_MANAGER_INPUT_LIB_H
#include <Uefi.h>
#include <Protocol/SimpleTextIn.h>
typedef UINT64 (*RAPHAEL_INPUT_COUNTER)(VOID);
// Diagnostic wrapper: delivers real keys, then a separately marked Enter at
// the fixed deadline even if upstream cancelled its countdown after a key.
typedef struct {
  EFI_SIMPLE_TEXT_INPUT_PROTOCOL Protocol;
  EFI_SIMPLE_TEXT_INPUT_PROTOCOL *Real;
  RAPHAEL_INPUT_COUNTER Counter;
  EFI_INPUT_KEY Pending;
  BOOLEAN HavePending, Synthetic;
  UINT64 Frequency, Start, Deadline;
  UINT64 Up, Down, Enter, Automatic, Errors, Delivered;
} RAPHAEL_MANAGER_INPUT;
EFI_STATUS RaphaelManagerInputBegin(RAPHAEL_MANAGER_INPUT *State,
  EFI_SIMPLE_TEXT_INPUT_PROTOCOL *Real, RAPHAEL_INPUT_COUNTER Counter,
  UINT64 Frequency, UINTN Seconds);
EFI_STATUS RaphaelManagerInputEnd(RAPHAEL_MANAGER_INPUT *State);
#endif
