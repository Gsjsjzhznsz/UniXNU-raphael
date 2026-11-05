// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_TIMER_ROUTE_H
#define RAPHAEL_TIMER_ROUTE_H
#include <RaphaelGicEnableMap.h>
#include <RaphaelPpiProbe.h>
#include <RaphaelTimerSource.h>
// Physical source selectors retain the TimerSource contract. No IAR/EOIR access.
#define RAPHAEL_ROUTE_IGRPEN1 3
#define RAPHAEL_ROUTE_HPPIR1 4
#define RAPHAEL_ROUTE_DAIF 5
// Status1 prerequisite reject; 2 fresh-state reject; 3 access/readback error;
// 4 timeout; 5 restoration failure; 6 routed, withdrawn and restored.
typedef struct {
 UINT64 Version,Status,Reason,Intid,Flags,SgiBase,Frequency;
 UINT64 OriginalDist,DistDuring,RestoredDist,OriginalIgrpen,IgrpenDuring,RestoredIgrpen;
 UINT64 OriginalCtl,OriginalCval,RestoredCtl,RestoredCval,Deadline,StartCounter,EndCounter,CtlDuring;
 UINT64 HppirBefore,HppirDuring,HppirAfter,PendingBefore,PendingDuring,PendingAfter;
 UINT64 ActiveBefore,ActiveAfter,EnabledBefore,EnabledDuring,EnabledAfter;
 UINT64 DaifBefore,DaifAfter,Polls,ClearPolls,RwpPolls,MmioReads,MmioWrites,SysReads,SysWrites,RestoreOk,TrapEsr,TrapElr;
} RAPHAEL_TIMER_ROUTE_RESULT;
typedef BOOLEAN (*RAPHAEL_TIMER_IRQ_WINDOW)(VOID *Result,UINT64 Intid,UINT64 Frequency);
VOID RaphaelTestTimerRouteWithIrq(CONST VOID *,CONST RAPHAEL_GIC_SNAPSHOT *,CONST RAPHAEL_ICC_SNAPSHOT *,
 CONST RAPHAEL_GIC_ENABLE_MAP *,RAPHAEL_TIMER_ROUTE_RESULT *,RAPHAEL_GIC_READ32,RAPHAEL_PPI_WRITE32,
 RAPHAEL_ICC_READ,RAPHAEL_TIMER_WRITE,VOID *,RAPHAEL_TIMER_IRQ_WINDOW,VOID *);
VOID RaphaelTestTimerRoute(CONST VOID *Fdt,CONST RAPHAEL_GIC_SNAPSHOT *Gic,
 CONST RAPHAEL_ICC_SNAPSHOT *Icc,CONST RAPHAEL_GIC_ENABLE_MAP *Map,RAPHAEL_TIMER_ROUTE_RESULT *Output,
 RAPHAEL_GIC_READ32 MmioRead,RAPHAEL_PPI_WRITE32 MmioWrite,
 RAPHAEL_ICC_READ Read,RAPHAEL_TIMER_WRITE Write,VOID *Context);
BOOLEAN RaphaelTimerRouteRead(UINT32,UINT64 *,UINT64 *,UINT64 *,VOID *);
BOOLEAN RaphaelTimerRouteWrite(UINT32,UINT64,UINT64 *,UINT64 *,VOID *);
#endif
