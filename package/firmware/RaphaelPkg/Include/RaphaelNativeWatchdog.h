// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_WATCHDOG_H
#define RAPHAEL_NATIVE_WATCHDOG_H
#include <Uefi.h>
typedef struct {
 UINT64 Version,Status,Base,Frequency,Seconds,SavedEnable,SavedBark,SavedBite;
 UINT64 Armed,ReadbackEnable,ReadbackBark,ReadbackBite;
 UINT64 RestoredEnable,RestoredBark,RestoredBite,RestoreOk;
} RAPHAEL_NATIVE_WATCHDOG_RESULT;
EFI_STATUS RaphaelNativeWatchdogArm(VOID);
BOOLEAN RaphaelNativeWatchdogStop(VOID);
#endif
