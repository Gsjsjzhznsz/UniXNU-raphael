// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_ICC_PROBE_H
#define RAPHAEL_ICC_PROBE_H
#include <RaphaelGicProbe.h>
#define RAPHAEL_ICC_REGISTER_COUNT 16
// Ordinals are a wire contract; no IAR/EOIR/DIR or write operation is present.
typedef enum {
 RaphaelSysCurrentEl, RaphaelSysDaif, RaphaelSysMpidr, RaphaelSysSre,
 RaphaelSysCtlr, RaphaelSysPmr, RaphaelSysBpr1, RaphaelSysIgrpen1,
 RaphaelSysRpr, RaphaelSysHppir1, RaphaelSysCntpCtl, RaphaelSysCntpCval,
 RaphaelSysCntvCtl, RaphaelSysCntvCval, RaphaelSysCntkctl, RaphaelSysCntfrq
} RAPHAEL_ICC_REGISTER;
typedef BOOLEAN (*RAPHAEL_ICC_READ)(UINT32 Register,UINT64 *Value,UINT64 *Esr,UINT64 *Elr,VOID *Context);
typedef struct {
 UINT64 Version,Status,Attempted,Completed,FailedSelector,TrapEsr,TrapElr;
 UINT64 Values[RAPHAEL_ICC_REGISTER_COUNT];
 UINT64 InjectedFaultRecovered,InjectedFaultEsr,InjectedFaultElr;
} RAPHAEL_ICC_SNAPSHOT;
// Status 1 prerequisites rejected, 2 EL/DAIF/MPIDR rejected, 3 SRE disabled,
// 4 read trapped, 5 complete. Partial snapshots never establish accessibility.
VOID RaphaelCollectIcc(CONST RAPHAEL_GIC_SNAPSHOT *Gic,RAPHAEL_ICC_SNAPSHOT *Output,
 RAPHAEL_ICC_READ Read,VOID *Context);
BOOLEAN RaphaelReadIccRegister(UINT32 Register,UINT64 *Value,UINT64 *Esr,UINT64 *Elr,VOID *Context);
BOOLEAN RaphaelReadInjectedUndefined(UINT64 *Value,UINT64 *Esr,UINT64 *Elr);
#endif
