// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_GIC_ENABLE_MAP_H
#define RAPHAEL_GIC_ENABLE_MAP_H
#include <RaphaelGicProbe.h>
#define RAPHAEL_GIC_SPI_ENABLE_WORDS 31
typedef struct {
 UINT64 Version,Status,Reason,ReadCount,SpiWords,FrameCount;
 UINT64 EnabledSpiOr,EnabledLocalOr,LpiEnabledOr,ChangedWords;
 UINT64 DistributorBefore,DistributorAfter,AllObservedDisabled;
 UINT64 Spi[RAPHAEL_GIC_SPI_ENABLE_WORDS];
 UINT64 Local[RAPHAEL_GIC_MAX_FRAMES],LocalCtlr[RAPHAEL_GIC_MAX_FRAMES];
} RAPHAEL_GIC_ENABLE_MAP;
// Status1 rejected snapshot/architecture/ranges; 2 header changed;
// 3 complete and unchanged; 4 complete but changed. Read-only, not atomic.
VOID RaphaelCollectGicEnableMap(CONST RAPHAEL_GIC_SNAPSHOT *Gic,
 RAPHAEL_GIC_ENABLE_MAP *Output,RAPHAEL_GIC_READ32 Read,VOID *Context);
#endif
