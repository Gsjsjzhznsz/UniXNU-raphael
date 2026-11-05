// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_ENTRY_H
#define RAPHAEL_NATIVE_ENTRY_H
#include <Uefi.h>
// Fixed 40Q wire; assembly offsets are checked below by C static assertions.
typedef struct {
  UINT64 Version, Status, ArmedCount, TrapCount, Entry, Checkpoint;
  UINT64 OriginalInstruction, ProbeInstruction, Esr, Elr, Far, Spsr;
  UINT64 X0, X1, X20, X21, Sp, Sctlr, CurrentEl, Daif, Counter, Vbar;
  UINT64 Tcr, Ttbr0, Ttbr1, Mair;
  UINT64 SavedSctlr, SavedVbar, SavedTcr, SavedTtbr0, SavedTtbr1, SavedMair;
  UINT64 Frequency, Affinity, PatchRestored, MmuRestored, ExitCompleted;
  UINT64 Error, PrefixInstructions, VectorSlot;
} RAPHAEL_NATIVE_ENTRY_RESULT;
BOOLEAN RaphaelNativeEntryRange(UINT64 Address, UINT64 Bytes);
EFI_STATUS RaphaelArmNativeEntry(UINT64 Entry, UINT64 Args);
VOID RaphaelNativeEntryFinish(BOOLEAN Valid);
#endif
