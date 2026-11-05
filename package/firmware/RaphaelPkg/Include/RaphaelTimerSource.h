// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_TIMER_SOURCE_H
#define RAPHAEL_TIMER_SOURCE_H
#include <RaphaelIccProbe.h>
// These selectors only expose the physical counter and CNTP source; no CNTV/GIC.
#define RAPHAEL_TIMER_COUNTER 0
#define RAPHAEL_TIMER_CTL 1
#define RAPHAEL_TIMER_CVAL 2
#define RAPHAEL_TIMER_MAX_POLLS 1000000
// Status 1 prerequisite rejection, 2 state changed/unsupported, 3 write trap,
// 4 read trap, 5 readback mismatch, 6 timeout, 7 restoration failure, 8 complete.
typedef struct {
 UINT64 Version,Status,Reason,Frequency,OriginalCtl,OriginalCval;
 UINT64 StartCounter,Deadline,ObservedCtl,ObservedCval,EndCounter,Polls;
 UINT64 RestoredCtl,RestoredCval,WriteCalls,TrapEsr,TrapElr;
} RAPHAEL_TIMER_SOURCE_RESULT;
typedef BOOLEAN (*RAPHAEL_TIMER_WRITE)(UINT32 Register,UINT64 Value,UINT64 *Esr,UINT64 *Elr,VOID *Context);
VOID RaphaelTestTimerSource(CONST RAPHAEL_ICC_SNAPSHOT *Icc,RAPHAEL_TIMER_SOURCE_RESULT *Output,
 RAPHAEL_ICC_READ Read,RAPHAEL_TIMER_WRITE Write,VOID *Context);
BOOLEAN RaphaelTimerSourceRead(UINT32 Register,UINT64 *Value,UINT64 *Esr,UINT64 *Elr,VOID *Context);
BOOLEAN RaphaelTimerSourceWrite(UINT32 Register,UINT64 Value,UINT64 *Esr,UINT64 *Elr,VOID *Context);
#endif
