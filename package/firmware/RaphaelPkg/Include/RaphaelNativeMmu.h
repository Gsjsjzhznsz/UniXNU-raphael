// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_MMU_H
#define RAPHAEL_NATIVE_MMU_H
#include <Uefi.h>
#include <RaphaelNativeEarly.h>
#include <RaphaelNativePmap.h>
#include <RaphaelNativeWatchdog.h>
typedef struct {
  UINT64 Magic, Version, ArmInit, LowVectors, HighVectors, Tables, TablesBytes, Tcr, Mair, Sctlr, ExceptionSp, InterruptSp, ArmOpcode, Start, StartBytes, StartCrc, Ttb, TtbBytes, TtbCrc, Flags, BootstrapSkip;
} RAPHAEL_NATIVE_MMU_POLICY;
typedef struct {
  UINT64 Version, Status, Armed, TrapCount, Entry, CheckpointVa, OriginalInstruction, ProbeInstruction, Esr, Elr, Far, Spsr, X0, X1, X20, X21, X22, X23, X24, X25, Sp, Lr, Sctlr, Vbar, Tcr, Ttbr0, Ttbr1, Mair, SavedSctlr, SavedVbar, SavedTcr, SavedTtbr0, SavedTtbr1, SavedMair, SavedCpacr, SavedTpidrEl0, SavedTpidrro, SavedTpidrEl1, SavedSpEl0, Frequency, Affinity, VectorSlot, CacheOffSctlr, RelayPa, Tables, TablesBytes, TablesCrcBefore, TablesCrcAfter, PhysicalTranslation, VirtualTranslation, PatchRestored, TablesRestored, MmuRestored, ArgsOk, SegmentsOk, ZeroOk, Error, ExpectedTcr, ExpectedMair, ExpectedSctlr, ExpectedPhysBase, ExpectedVirtBase, ExpectedMemBytes, TablesChangedCount, InterruptedSp, CurrentEl, Daif, Cpacr, TpidrEl0, Tpidrro, TpidrEl1, Counter;
} RAPHAEL_NATIVE_MMU_RESULT;
typedef struct {
 UINT64 Version,Status;
 UINT64 SavedPhysicalControl,SavedPhysicalCompare,SavedVirtualControl,SavedVirtualCompare,SavedKernelControl;
 UINT64 ObservedPhysicalControl,ObservedPhysicalCompare,ObservedVirtualControl,ObservedVirtualCompare,ObservedKernelControl;
 UINT64 RestoredPhysicalControl,RestoredPhysicalCompare,RestoredVirtualControl,RestoredVirtualCompare,RestoredKernelControl;
 UINT64 RestoreOk;
} RAPHAEL_NATIVE_PLATFORM_RESULT;
// Only the bounded boot-CPU GICv3 configuration touched by RaphaelBootCpu.
// Snapshot/early/pmap offsets used by the relay precede this appended record.
#define RAPHAEL_NATIVE_GIC_WORDS 16
typedef struct {
 UINT64 Version,Status,Dist,Rdist,TimerId,RestoreOk,ChangedWords,Reserved;
 UINT64 Saved[RAPHAEL_NATIVE_GIC_WORDS],Observed[RAPHAEL_NATIVE_GIC_WORDS],Restored[RAPHAEL_NATIVE_GIC_WORDS];
} RAPHAEL_NATIVE_GIC_RESULT;
EFI_STATUS RaphaelSaveNativeGic(RAPHAEL_NATIVE_GIC_RESULT *State);
BOOLEAN RaphaelRestoreNativeGic(RAPHAEL_NATIVE_GIC_RESULT *State);
typedef struct { RAPHAEL_NATIVE_MMU_RESULT Result; UINT64 Snapshot,Early,Pmap; RAPHAEL_NATIVE_PLATFORM_RESULT Platform; RAPHAEL_NATIVE_WATCHDOG_RESULT Watchdog; RAPHAEL_NATIVE_GIC_RESULT Gic; } RAPHAEL_NATIVE_MMU_STATE;
EFI_STATUS RaphaelPrepareNativeMmu(VOID);
EFI_STATUS RaphaelArmNativeMmu(UINT64 Entry,UINT64 Args);
BOOLEAN RaphaelNativeMemoryRange(UINT64 Address,UINT64 Bytes);
BOOLEAN RaphaelNativeBackupRange(UINT64 Address,UINT64 Bytes,UINT64 FileBytes,BOOLEAN Reclaimed);
UINT64 RaphaelNativePhysical(UINT64 Virtual);
RAPHAEL_NATIVE_WATCHDOG_RESULT *RaphaelNativeWatchdogResult(VOID);
VOID RaphaelNativeMmuFinish(BOOLEAN Valid);
#endif
