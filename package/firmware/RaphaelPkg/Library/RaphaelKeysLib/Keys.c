// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelKeysLib.h>
BOOLEAN RaphaelKeyTransport(CONST RAPHAEL_INPUT_SNAPSHOT *I,UINT32 Frequency,RAPHAEL_KEY_TRANSPORT *T) {
  UINT64 End,At[2];UINT32 Apid[2],Sid[2],Address[2];
  if(!I||!T||I->Version!=1||I->Status!=RaphaelInputMapCollected||I->HardwareVersion<0x50000000||
    I->HardwareVersion>=0x60000000||!Frequency||Frequency>1000000000||I->Ee>5||
    !I->Count||I->Count>RAPHAEL_INPUT_MAX_APIDS||I->PonOwner!=I->Ee||I->VolumeOwner!=I->Ee||
    !I->PonMatches||!I->VolumeMatches||I->GpioFlags!=1||I->PonSid>15||I->VolumeSid>15||
    I->PonAddress>0xffff||I->VolumeAddress>0xffff||(I->PonAddress&255)!=0x10||(I->VolumeAddress&255)!=0x10||
    !I->ObserverBase||(I->ObserverBase&4095)||!I->ObserverSize)return FALSE;
  Apid[0]=I->PonApid;Apid[1]=I->VolumeApid;Sid[0]=I->PonSid;Sid[1]=I->VolumeSid;
  Address[0]=I->PonAddress;Address[1]=I->VolumeAddress;
  End=(UINT64)I->ObserverBase+I->ObserverSize;if(End>0x100000000ULL)return FALSE;
  for(UINTN N=0;N<2;++N) {
    if(Apid[N]>=I->Count||!I->Map[Apid[N]]||((I->Map[Apid[N]]>>8)&0xfff)!=((Sid[N]<<8)|(Address[N]>>8))||
      (I->Owner[Apid[N]]&7)!=I->Ee)return FALSE;
    At[N]=(UINT64)I->ObserverBase+0x10000*I->Ee+0x80*Apid[N];
    if(At[N]+0x1c>End)return FALSE;
  }
  if(At[0]==At[1])return FALSE;
  T->PonObserver=At[0];T->VolumeObserver=At[1];T->PonSid=I->PonSid;T->PonAddress=I->PonAddress;
  T->VolumeSid=I->VolumeSid;T->VolumeAddress=I->VolumeAddress;T->Frequency=Frequency;return TRUE;
}
STATIC BOOLEAN ReadByte(CONST RAPHAEL_KEY_TRANSPORT *T,BOOLEAN Volume,UINT32 Offset,RAPHAEL_KEY_REGISTER *R,
  RAPHAEL_INPUT_READ32 Read,RAPHAEL_KEY_WRITE32 Write,RAPHAEL_KEY_COUNTER Counter,VOID *Context) {
  UINT64 Start=Counter(Context),Limit=((UINT64)T->Frequency+999)/1000;
  R->Sid=Volume?T->VolumeSid:T->PonSid;
  R->Address=((Volume?T->VolumeAddress:T->PonAddress)&~255U)+Offset;
  R->Observer=Volume?T->VolumeObserver:T->PonObserver;
  R->Command=(1U<<27)|((Offset&255)<<4); // EXT_READL, one byte; no write opcode is implemented.
  Write(R->Observer,(UINT32)R->Command,Context);
  for(UINTN N=0;N<100000;++N) {
    ++R->Polls;R->Completion=Read(R->Observer+8,Context);
    if(R->Completion&1) {
      if(R->Completion&14){R->Error=2;return FALSE;}
      R->Value=Read(R->Observer+0x18,Context)&255;return TRUE;
    }
    if(Counter(Context)-Start>=Limit){R->Error=1;return FALSE;}
  }
  R->Error=1;return FALSE;
}
VOID RaphaelCollectKeyRegisters(CONST RAPHAEL_INPUT_SNAPSHOT *I,UINT32 Frequency,RAPHAEL_KEY_RESULT *O,
  RAPHAEL_INPUT_READ32 Read,RAPHAEL_KEY_WRITE32 Write,RAPHAEL_KEY_COUNTER Counter,VOID *Context) {
  RAPHAEL_KEY_TRANSPORT T;
  for(UINTN N=0;N<sizeof(*O);++N)((UINT8 *)O)[N]=0;
  O->Version=1;O->Status=1;
  if(!Read||!Write||!Counter||!RaphaelKeyTransport(I,Frequency,&T))return;
  O->Status=2;O->Start=Counter(Context);O->TimeoutTicks=((UINT64)Frequency+999)/1000;
  // GPIO type, subtype, mode, enable, real-time status, then PON real-time status.
  CONST UINT32 Offsets[]={4,5,0x40,0x46,0x10,0x10};
  for(UINTN N=0;N<RAPHAEL_KEY_REGISTER_COUNT;++N) {
    ++O->Transactions;
    if(!ReadByte(&T,N<5,Offsets[N],&O->Registers[N],Read,Write,Counter,Context)) {
      O->Error=O->Registers[N].Error;O->Status=4;O->End=Counter(Context);return;
    }
    ++O->Completed;
  }
  O->End=Counter(Context);O->Status=3;
}
BOOLEAN RaphaelReadKeyState(CONST RAPHAEL_KEY_TRANSPORT *T,UINT32 *Keys,
  RAPHAEL_INPUT_READ32 Read,RAPHAEL_KEY_WRITE32 Write,RAPHAEL_KEY_COUNTER Counter,VOID *Context) {
  RAPHAEL_KEY_REGISTER V={0},P={0};
  if(!T||!Keys||!Read||!Write||!Counter)return FALSE;
  if(!ReadByte(T,TRUE,0x10,&V,Read,Write,Counter,Context)||!ReadByte(T,FALSE,0x10,&P,Read,Write,Counter,Context))return FALSE;
  *Keys=(!(V.Value&1)?RAPHAEL_KEY_UP:0)|((P.Value&2)?RAPHAEL_KEY_DOWN:0)|((P.Value&1)?RAPHAEL_KEY_POWER:0);
  return TRUE;
}

BOOLEAN RaphaelKeyRegistersReady(CONST RAPHAEL_KEY_RESULT *R) {
  if(!R||R->Version!=1||R->Status!=3||R->Completed!=6||R->Transactions!=6||R->Error)return FALSE;
  for(UINTN I=0;I<6;++I)if(R->Registers[I].Error||(R->Registers[I].Completion&15)!=1)return FALSE;
  UINT64 Subtype=R->Registers[1].Value;
  return R->Registers[0].Value==0x10&&(Subtype==0x10||Subtype==0x11)&&
    (R->Registers[2].Value&3)==0&&(R->Registers[3].Value&0x80)!=0;
}
UINT32 RaphaelFilterKeys(RAPHAEL_KEY_FILTER *F,UINT32 Raw,UINT64 Now) {
  if(!F||Raw>7)return 0;
  if(!F->Initialized) {
    F->Initialized=1;F->Candidate=F->Stable=Raw;F->Since=Now;F->Armed=Raw==0;return 0;
  }
  if(Raw!=F->Candidate){F->Candidate=Raw;F->Since=Now;return 0;}
  if(F->Stable==Raw||Now-F->Since<F->DebounceTicks)return 0;
  UINT32 Previous=F->Stable;F->Stable=Raw;F->ReleasedMask|=Previous&~Raw;
  if(!Raw){F->Armed=1;return 0;}
  BOOLEAN Armed=F->Armed!=0;F->Armed=0;
  if(!Armed||(Raw&(Raw-1)))return 0;
  F->PressedMask|=Raw;return Raw;
}
