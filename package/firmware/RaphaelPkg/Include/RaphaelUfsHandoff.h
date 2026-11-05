// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_UFS_HANDOFF_H
#define RAPHAEL_UFS_HANDOFF_H
#include <Uefi.h>
#define RAPHAEL_UFS_HANDOFF_REGS 18
typedef UINT32 (*RAPHAEL_UFS_READ32)(UINT64,VOID *);
// Status: 1 unsupported root, 2 invalid resource contract, 3 completed read-only.
// Register offsets are JESD223 HCI; all physical resources come from live FDT.
typedef struct {UINT64 Version,Status,ReadCount,Base,Bytes;
 UINT64 Offsets[RAPHAEL_UFS_HANDOFF_REGS];
 UINT64 First[RAPHAEL_UFS_HANDOFF_REGS],Second[RAPHAEL_UFS_HANDOFF_REGS];
} RAPHAEL_UFS_HANDOFF;
VOID RaphaelCollectUfsHandoff(CONST VOID *,UINT64,UINT64,RAPHAEL_UFS_HANDOFF *,RAPHAEL_UFS_READ32,VOID *);
#endif
