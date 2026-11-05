// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelTimerSource.h>
#include <Library/PcdLib.h>
extern BOOLEAN RaphaelReadPhysicalCount(UINT64 *,UINT64 *,UINT64 *);
extern BOOLEAN RaphaelWritePhysicalCtl(UINT64,UINT64 *,UINT64 *);
extern BOOLEAN RaphaelWritePhysicalCval(UINT64,UINT64 *,UINT64 *);
BOOLEAN RaphaelTimerSourceRead(UINT32 R,UINT64 *V,UINT64 *Esr,UINT64 *Elr,VOID *C) {
 (VOID)C;if(!V||!Esr||!Elr)return FALSE;
 if(R==RAPHAEL_TIMER_COUNTER)return RaphaelReadPhysicalCount(V,Esr,Elr);
 if(R==RAPHAEL_TIMER_CTL)return RaphaelReadIccRegister(RaphaelSysCntpCtl,V,Esr,Elr,NULL);
 if(R==RAPHAEL_TIMER_CVAL)return RaphaelReadIccRegister(RaphaelSysCntpCval,V,Esr,Elr,NULL);
 return FALSE;
}
BOOLEAN RaphaelTimerSourceWrite(UINT32 R,UINT64 V,UINT64 *Esr,UINT64 *Elr,VOID *C) {
 if(!Esr||!Elr)return FALSE;
 // QEMU-only simulated write failure after CVAL was actually changed.
 // Restoring CTL=2 and the original CTL never enter this branch.
 if(FixedPcdGetBool(PcdRaphaelIccFaultTest)&&C&&R==RAPHAEL_TIMER_CTL&&V==3&&!*(BOOLEAN *)C) {
  UINT64 Unused=0;*(BOOLEAN *)C=TRUE;return RaphaelReadInjectedUndefined(&Unused,Esr,Elr);
 }
 if(R==RAPHAEL_TIMER_CTL&&(V&~3ULL)==0)return RaphaelWritePhysicalCtl(V,Esr,Elr);
 if(R==RAPHAEL_TIMER_CVAL)return RaphaelWritePhysicalCval(V,Esr,Elr);
 return FALSE;
}
