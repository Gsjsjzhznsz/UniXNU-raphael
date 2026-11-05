// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_GIC_PROBE_H
#define RAPHAEL_GIC_PROBE_H
#include <Uefi.h>
#define RAPHAEL_GIC_MAX_FRAMES 8
#define RAPHAEL_GIC_SGI_WORDS 15
// Read-only architecture register snapshot. No system-register/IAR access.
typedef UINT32 (*RAPHAEL_GIC_READ32)(UINT64 Address,VOID *Context);
typedef struct {UINT64 Base,Typer,Ctlr,Iidr,Waker,Pidr2;} RAPHAEL_GIC_FRAME;
typedef struct {
 UINT64 Version,Status,Reason,ReadCount;
 UINT64 GicD,GicDBytes,GicR,GicRBytes,Stride;
 UINT64 Mpidr,Affinity,FrameCount,BootIndex;
 UINT64 Ctlr,Typer,Iidr,Pidr2;
 RAPHAEL_GIC_FRAME Frames[RAPHAEL_GIC_MAX_FRAMES];
 UINT64 Sgi[RAPHAEL_GIC_SGI_WORDS];
} RAPHAEL_GIC_SNAPSHOT;
// Status: 1 unsupported root (no MMIO), 2 invalid FDT (no MMIO),
// 3 unsupported/inconsistent hardware (partial read-only), 4 complete.
VOID RaphaelCollectGic(CONST VOID *Fdt,UINT64 Mpidr,UINT64 ProtectedBase,UINT64 ProtectedEnd,
 RAPHAEL_GIC_SNAPSHOT *Output,RAPHAEL_GIC_READ32 Read,VOID *Context);
#endif
