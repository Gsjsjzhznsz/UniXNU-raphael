// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_PPI_PROBE_H
#define RAPHAEL_PPI_PROBE_H
#include <RaphaelIccProbe.h>
typedef VOID (*RAPHAEL_PPI_WRITE32)(UINT64 Address,UINT32 Value,VOID *Context);
typedef UINT64 (*RAPHAEL_PPI_COUNTER)(VOID *Context);
typedef struct {
 UINT64 Version,Status,Reason,Intid,Flags,SgiBase,Mask;
 UINT64 EnabledBefore,EnabledDuring,EnabledAfter,ActiveBefore,PendingBefore;
 UINT64 RwpPolls,WriteCount,CtlrBefore,CtlrAfter,ReadCount,RestoreOk,PendingAfter,ActiveAfter;
} RAPHAEL_PPI_RESULT;
// Status 1 prerequisites, 2 invalid resources/changed state, 3 write ignored,
// 4 unexpected readback/timeout, 5 restore failed, 6 writable and restored.
BOOLEAN RaphaelResolvePhysicalPpi(CONST VOID *Fdt,UINT64 Frequency,UINT64 *Id,UINT64 *Flags);
VOID RaphaelProbePhysicalPpi(CONST VOID *Fdt,CONST RAPHAEL_GIC_SNAPSHOT *Gic,
 CONST RAPHAEL_ICC_SNAPSHOT *Icc,RAPHAEL_PPI_RESULT *Output,RAPHAEL_GIC_READ32 Read,
 RAPHAEL_PPI_WRITE32 Write,RAPHAEL_PPI_COUNTER Counter,VOID *Context);
#endif
