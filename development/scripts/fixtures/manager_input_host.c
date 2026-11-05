// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef NULL
#include <Library/RaphaelManagerInputLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
STATIC UINT64 Now=100;
STATIC UINTN Checks,Signals,ReadCalls,Closed;
STATIC EFI_EVENT_NOTIFY Notify;
STATIC VOID *NotifyContext;
STATIC EFI_STATUS CreateStatus,CloseStatus,RealStatus=EFI_NOT_READY;
STATIC EFI_INPUT_KEY NextKey;
STATIC EFI_BOOT_SERVICES Bs;
EFI_BOOT_SERVICES *gBS=&Bs;
UINT64 Counter(VOID){return Now;}
VOID *EFIAPI ZeroMem(VOID *P,UINTN N){return memset(P,0,N);}
VOID EFIAPI DebugPrint(UINTN L,CONST CHAR8 *F,...){(VOID)L;(VOID)F;}
BOOLEAN EFIAPI DebugPrintEnabled(VOID){return TRUE;}
BOOLEAN EFIAPI DebugPrintLevelEnabled(CONST UINTN L){(VOID)L;return TRUE;}
STATIC EFI_STATUS EFIAPI Create(UINT32 T,EFI_TPL P,EFI_EVENT_NOTIFY F,VOID *C,EFI_EVENT *E){assert(T==EVT_NOTIFY_WAIT&&P==TPL_CALLBACK);if(EFI_ERROR(CreateStatus))return CreateStatus;Notify=F;NotifyContext=C;*E=(VOID *)0x1234;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI Signal(EFI_EVENT E){assert(E==(VOID *)0x1234);++Signals;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI Close(EFI_EVENT E){assert(E==(VOID *)0x1234);++Closed;return CloseStatus;}
STATIC EFI_STATUS EFIAPI CheckEvent(EFI_EVENT E){assert(E==(VOID *)0x4321);return RealStatus;}
STATIC EFI_STATUS EFIAPI RealRead(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *P,EFI_INPUT_KEY *K){(VOID)P;++ReadCalls;if(EFI_ERROR(RealStatus))return RealStatus;*K=NextKey;RealStatus=EFI_NOT_READY;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI RealReset(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *P,BOOLEAN B){(VOID)P;(VOID)B;RealStatus=EFI_NOT_READY;return EFI_SUCCESS;}
STATIC VOID Check(BOOLEAN V,CONST char *N){if(!V){fprintf(stderr,"FAIL %s\n",N);exit(1);}printf("PASS %s\n",N);++Checks;}
int main(void){
 Bs.CreateEvent=Create;Bs.SignalEvent=Signal;Bs.CloseEvent=Close;Bs.CheckEvent=CheckEvent;
 RAPHAEL_MANAGER_INPUT S={0};EFI_SIMPLE_TEXT_INPUT_PROTOCOL Real={RealReset,RealRead,(VOID *)0x4321};EFI_INPUT_KEY K;
 Check(RaphaelManagerInputBegin(NULL,&Real,Counter,1000,6)==EFI_INVALID_PARAMETER,"null state refused");
 Check(RaphaelManagerInputBegin(&S,&Real,Counter,0,6)==EFI_INVALID_PARAMETER,"zero frequency refused");
 Check(RaphaelManagerInputBegin(&S,&Real,Counter,1000,7)==EFI_INVALID_PARAMETER,"unbounded duration refused");
 Check(RaphaelManagerInputBegin(&S,&Real,Counter,MAX_UINT64,6)==EFI_INVALID_PARAMETER,"duration multiplication overflow refused");
 Now=MAX_UINT64-1;Check(RaphaelManagerInputBegin(&S,&Real,Counter,1000,6)==EFI_UNSUPPORTED,"counter deadline overflow refused");Now=100;
 CreateStatus=EFI_OUT_OF_RESOURCES;Check(RaphaelManagerInputBegin(&S,&Real,Counter,1000,6)==EFI_OUT_OF_RESOURCES&&!S.Protocol.WaitForKey,"event failure leaves no active handle");CreateStatus=0;
 Check(!EFI_ERROR(RaphaelManagerInputBegin(&S,&Real,Counter,1000,6))&&S.Deadline==6100,"six-second absolute deadline");
 Check(RaphaelManagerInputBegin(&S,&Real,Counter,1000,6)==EFI_ALREADY_STARTED,"active event cannot be discarded");
 Check(S.Protocol.ReadKeyStroke(NULL,&K)==EFI_INVALID_PARAMETER&&S.Protocol.ReadKeyStroke(&S.Protocol,NULL)==EFI_INVALID_PARAMETER,"null read parameters refused");
 Notify(S.Protocol.WaitForKey,NotifyContext);Check(Signals==0&&ReadCalls==0,"no signal or read while real event is not ready");
 for(UINTN I=0;I<3;++I){
  NextKey.ScanCode=I==0?SCAN_UP:I==1?SCAN_DOWN:SCAN_NULL;NextKey.UnicodeChar=I==2?CHAR_CARRIAGE_RETURN:0;RealStatus=EFI_SUCCESS;Now+=100;
  Notify(S.Protocol.WaitForKey,NotifyContext);Notify(S.Protocol.WaitForKey,NotifyContext);
  Check(Signals==(I+1)*2&&ReadCalls==I+1,"pending event survives repeated wait without consuming another key");
  Check(!EFI_ERROR(S.Protocol.ReadKeyStroke(&S.Protocol,&K))&&K.ScanCode==NextKey.ScanCode&&K.UnicodeChar==NextKey.UnicodeChar,"real key delivered unchanged");
 }
 Check(S.Up==1&&S.Down==1&&S.Enter==1&&S.Automatic==0&&S.Delivered==3,"physical Up Down Enter have independent counts");
 UINT64 Deadline=S.Deadline;Check(!EFI_ERROR(S.Protocol.Reset(&S.Protocol,FALSE))&&S.Deadline==Deadline&&S.Delivered==3,"reset cannot extend deadline or erase physical evidence");
 RealStatus=EFI_DEVICE_ERROR;Notify(S.Protocol.WaitForKey,NotifyContext);Check(S.Errors==1,"real event error recorded");
 Now=S.Deadline;Notify(S.Protocol.WaitForKey,NotifyContext);Check(!EFI_ERROR(S.Protocol.ReadKeyStroke(&S.Protocol,&K))&&K.ScanCode==0&&K.UnicodeChar==13,"absolute deadline delivers Enter even after physical activity or error");
 Check(S.Automatic==1&&S.Enter==1&&S.Up==1&&S.Down==1,"synthetic fallback cannot become physical Enter evidence");
 CloseStatus=EFI_DEVICE_ERROR;Check(RaphaelManagerInputEnd(&S)==EFI_DEVICE_ERROR&&S.Protocol.WaitForKey,"close failure retains event for retry");CloseStatus=0;
 Check(!EFI_ERROR(RaphaelManagerInputEnd(&S))&&!S.Protocol.WaitForKey,"event closed after console restoration");
 Check(RaphaelManagerInputEnd(&S)==EFI_NOT_READY,"ended wrapper cannot close twice");
 printf("MANAGER_INPUT_HOST_OK %lu\n",(unsigned long)Checks);return 0;
}
