// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <AsmMacroLib.h>
// No-op in every built image. QEMU patches this exact NOP after the 257th
// pattern store to test dirty-page restoration through the fatal SEC path.
// The recovered path has a larger WriteAttempts count and cannot re-enter it.
ASM_FUNC(RaphaelRamWriteCheckpoint)
 nop
 ret
