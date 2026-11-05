// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_QEMU_ARCH_H
#define RAPHAEL_QEMU_ARCH_H
#include <Uefi.h>
// Emulator-only state. No handset ownership or interrupt restoration contract.
typedef struct {
  UINT64 Version, Status, GicD, GicDBytes, GicR, GicRBytes;
  UINT64 SecureInt, PhysicalInt, VirtualInt, HypInt, SavedCtl, SavedCval, Frequency;
  UINT64 CpuProtocol, InterruptProtocol, TimerProtocol, Period;
  UINT64 RelativeFired, RelativeTicks, PeriodicCount, PeriodicTicks, CancelStable;
  UINT64 ManagerCompleted, ManagerTicks, SourcesDisabled, TimerDisabled;
  UINT64 TimerRestored, CvalAfter, CtlAfter;
} RAPHAEL_QEMU_ARCH_RESULT;
#endif
