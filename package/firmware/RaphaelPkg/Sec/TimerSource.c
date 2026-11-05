// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelTimerSource.h>
VOID RaphaelTestTimerSource(CONST RAPHAEL_ICC_SNAPSHOT *I,RAPHAEL_TIMER_SOURCE_RESULT *O,
 RAPHAEL_ICC_READ Read,RAPHAEL_TIMER_WRITE Write,VOID *C) {
 UINT64 FreshCtl=0,FreshCval=0;BOOLEAN RestoreOk=TRUE;
 if(!O)return;
 for(UINTN N=0;N<sizeof(*O);++N)((UINT8 *)O)[N]=0;
 O->Version=1;O->Status=1;
 if(!I||!Read||!Write||I->Version!=1||I->Status!=5||I->Attempted!=16||I->Completed!=16||
   I->FailedSelector!=MAX_UINT64||I->TrapEsr||I->TrapElr||I->Values[RaphaelSysCurrentEl]!=4||
   (I->Values[RaphaelSysDaif]&0x3c0)!=0x3c0||!(I->Values[RaphaelSysSre]&1)||
   I->Values[RaphaelSysCntpCtl]>7||(I->Values[RaphaelSysCntpCtl]&1)||
   I->Values[RaphaelSysCntfrq]<1000||I->Values[RaphaelSysCntfrq]>1000000000)return;
 O->Frequency=I->Values[RaphaelSysCntfrq];O->OriginalCtl=I->Values[RaphaelSysCntpCtl];O->OriginalCval=I->Values[RaphaelSysCntpCval];
 // Re-read before the first write. The source must still be disabled and match.
 O->Reason=1;
 if(!Read(RAPHAEL_TIMER_CTL,&FreshCtl,&O->TrapEsr,&O->TrapElr,C)||
    !Read(RAPHAEL_TIMER_CVAL,&FreshCval,&O->TrapEsr,&O->TrapElr,C)||
    !Read(RAPHAEL_TIMER_COUNTER,&O->StartCounter,&O->TrapEsr,&O->TrapElr,C)){O->Status=4;return;}
 if(FreshCtl>7||((FreshCtl^O->OriginalCtl)&3)||FreshCval!=O->OriginalCval||
   O->StartCounter>MAX_UINT64-O->Frequency/10){O->Status=2;return;}
 O->Deadline=O->StartCounter+O->Frequency/100;
 // IMASK remains set for the entire period in which this timer is enabled.
 O->Reason=2;++O->WriteCalls;
 if(!Write(RAPHAEL_TIMER_CVAL,O->Deadline,&O->TrapEsr,&O->TrapElr,C)){O->Status=3;goto Restore;}
 if(!Read(RAPHAEL_TIMER_CVAL,&O->ObservedCval,&O->TrapEsr,&O->TrapElr,C)){O->Status=4;goto Restore;}
 if(O->ObservedCval!=O->Deadline){O->Status=5;goto Restore;}
 O->Reason=3;++O->WriteCalls;
 if(!Write(RAPHAEL_TIMER_CTL,3,&O->TrapEsr,&O->TrapElr,C)){O->Status=3;goto Restore;}
 O->Reason=4;O->Status=6;
 for(UINTN N=0;N<RAPHAEL_TIMER_MAX_POLLS;++N) {
  ++O->Polls;
  if(!Read(RAPHAEL_TIMER_CTL,&O->ObservedCtl,&O->TrapEsr,&O->TrapElr,C)||
     !Read(RAPHAEL_TIMER_COUNTER,&O->EndCounter,&O->TrapEsr,&O->TrapElr,C)){O->Status=4;break;}
  if(O->ObservedCtl>7||(O->ObservedCtl&3)!=3||O->EndCounter<O->StartCounter){O->Status=5;break;}
  if(O->ObservedCtl&4) {O->Status=O->EndCounter>=O->Deadline?8:5;break;}
  if(O->EndCounter-O->StartCounter>=O->Frequency/10)break;
 }
Restore:
 // Always attempt all three writes, including after a partially effective trap.
 // First disable with IMASK set, then restore CVAL, then the original CTL bits.
 ++O->WriteCalls;if(!Write(RAPHAEL_TIMER_CTL,2,&O->TrapEsr,&O->TrapElr,C))RestoreOk=FALSE;
 ++O->WriteCalls;if(!Write(RAPHAEL_TIMER_CVAL,O->OriginalCval,&O->TrapEsr,&O->TrapElr,C))RestoreOk=FALSE;
 ++O->WriteCalls;if(!Write(RAPHAEL_TIMER_CTL,O->OriginalCtl&3,&O->TrapEsr,&O->TrapElr,C))RestoreOk=FALSE;
 if(!Read(RAPHAEL_TIMER_CTL,&O->RestoredCtl,&O->TrapEsr,&O->TrapElr,C))RestoreOk=FALSE;
 if(!Read(RAPHAEL_TIMER_CVAL,&O->RestoredCval,&O->TrapEsr,&O->TrapElr,C))RestoreOk=FALSE;
 if(!RestoreOk||O->RestoredCtl>7||((O->RestoredCtl^O->OriginalCtl)&3)||O->RestoredCval!=O->OriginalCval)O->Status=7;
 if(O->Status==8)O->Reason=0;
}
