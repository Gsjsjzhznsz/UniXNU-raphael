// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_PHYSICAL_TIMER_H
#define RAPHAEL_PHYSICAL_TIMER_H
#include <Uefi.h>
// All addresses and interrupt numbers are resolved from this boot's FDT/GIC.
// Status: 1 SEC prerequisites, 2 device mapping, 3 driver live, 4 event tests pass.
// RestoreOk is independent of Status. No full interrupt-controller ownership.
typedef struct {
  UINT64 Version, Status, Reason, GicD, GicDBytes, GicR, GicRBytes, RdBase, SgiBase, Intid, Flags, Frequency;
  UINT64 SavedDist, SavedIgrpen, SavedCtl, SavedCval, SavedDaif, SavedEnable, SavedPending, SavedActive, SavedVctl, SavedVcval;
  UINT64 MappedVerified, CpuProtocol, IrqRegistered, HwProtocol, TimerProtocol;
  UINT64 Period, IrqCount, EoiCount, Spurious, Unexpected, SourceMasked, NotifyCount, FirstCounter, LastCounter, StartCounter, EndCounter;
  UINT64 RelativeFired, RelativeTicks, PeriodicCount, PeriodicTicks, CancelStable, CancelTicks;
  UINT64 TimerStopped, RestoreOk, DistAfter, IgrpenAfter, CtlAfter, CvalAfter, EnableAfter, PendingAfter, ActiveAfter, DaifAfter, VctlAfter, VcvalAfter;
} RAPHAEL_PHYSICAL_TIMER_RESULT;
typedef BOOLEAN (EFIAPI *RAPHAEL_TIMER_SHUTDOWN)(VOID);
typedef struct {
  UINT64 Version, Status, StartCounter, EndCounter, Frequency, Timeout;
} RAPHAEL_MANAGER_RESULT;
typedef struct {
  RAPHAEL_PHYSICAL_TIMER_RESULT Result;
  RAPHAEL_TIMER_SHUTDOWN Shutdown;
  UINT64 Dirty;
  RAPHAEL_MANAGER_RESULT Manager;
} RAPHAEL_PHYSICAL_TIMER_STATE;
extern EFI_GUID gRaphaelPhysicalTimerHobGuid;
#endif
