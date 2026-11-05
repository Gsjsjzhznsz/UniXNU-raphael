// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_TIMER_IRQ_H
#define RAPHAEL_TIMER_IRQ_H
#include <Uefi.h>
// Assembly wire offsets below are audited against offsetof at host build time.
typedef struct {
 UINT64 Version,Status,ExpectedId,Frequency,StartCounter,Deadline,EndCounter,Polls;
 UINT64 Entries,ObservedId,IrqCounter,IrqElr,IrqSpsr,DaifBefore,DaifUnmasked,DaifAfter;
 UINT64 EoiCount,SourceMasked,SpuriousCount,UnexpectedId,SpSel,StackPointer,HandlerSp,ActiveCleared;
} RAPHAEL_TIMER_IRQ_RESULT;
// Bounded EL1/SPx one-shot window. Status2 rejected, 3 timed out, 4 bad IRQ, 5 complete.
BOOLEAN RaphaelRunTimerIrqWindow(VOID *Result,UINT64 Intid,UINT64 Frequency);
VOID RaphaelTimerIrqHandler(VOID);
#endif
