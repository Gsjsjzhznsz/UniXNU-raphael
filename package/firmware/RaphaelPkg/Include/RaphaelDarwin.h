// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_DARWIN_H
#define RAPHAEL_DARWIN_H
#include <Uefi.h>
// Diagnostic wire record; not an XNU boot contract.
typedef struct {
  UINT64 Version, Status, ConsoleInstalled, DriverLoaded, DriverStarted;
  UINT64 ProtocolRevision, NullStatus, MissingStatus, InvalidStatus, UniXnuStatus;
  UINT64 Unloaded, ProtocolRemoved, ConsoleRestored, ExitBootServices;
  UINT64 LogCharacters, ServicesAlive, CrcBefore, CrcAfter;
} RAPHAEL_DARWIN_RESULT;
#endif
