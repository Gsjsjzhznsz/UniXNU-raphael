// SPDX-License-Identifier: BSD-2-Clause-Patent
// Independent implementation from FDT and fixed primary interface semantics.
// This phase reads arbiter version, APID mapping and owner configuration only.
#include <RaphaelInputProbe.h>
#include <Library/FdtLib.h>
extern INT32 fdt_node_check_compatible(CONST VOID *, INT32, CONST CHAR8 *);
STATIC UINT32 Be32(CONST VOID *P) {
  CONST UINT8 *B=P; return ((UINT32)B[0]<<24)|((UINT32)B[1]<<16)|((UINT32)B[2]<<8)|B[3];
}
STATIC BOOLEAN U32(CONST VOID *F,INT32 N,CONST CHAR8 *K,UINT32 *V) {
  INT32 L; CONST VOID *P=FdtGetProp(F,N,K,&L); if(!P||L!=4)return FALSE; *V=Be32(P);return TRUE;
}
STATIC BOOLEAN Text(CONST VOID *F,INT32 N,CONST CHAR8 *K,CONST CHAR8 *S) {
  INT32 L;CONST CHAR8 *P=FdtGetProp(F,N,K,&L);if(!P)return FALSE;
  for(INT32 I=0;I<L;++I){if(P[I]!=S[I])return FALSE;if(!S[I])return TRUE;}return FALSE;
}
STATIC BOOLEAN Enabled(CONST VOID *F,INT32 N) {
  INT32 L;return !FdtGetProp(F,N,"status",&L)||Text(F,N,"status","okay")||Text(F,N,"status","ok");
}
STATIC BOOLEAN Equal(CONST CHAR8 *P,UINTN L,CONST CHAR8 *S) {
  for(UINTN I=0;I<L;++I){if(P[I]!=S[I])return FALSE;if(!S[I])return I+1==L;}return FALSE;
}
STATIC BOOLEAN Region(CONST VOID *F,INT32 N,CONST CHAR8 *Name,UINT32 *Base,UINT32 *Size,UINT64 Limit) {
  INT32 L,R;CONST CHAR8 *Names=FdtGetProp(F,N,"reg-names",&L);
  CONST UINT8 *Reg=FdtGetProp(F,N,"reg",&R);UINT32 Count=0,Found=0;
  if(!Names||!Reg||L<1||R<8||R%8)return FALSE;
  for(INT32 I=0;I<L;) {
    INT32 J=I;while(J<L&&Names[J])++J;if(J==L)return FALSE;
    if(Equal(Names+I,(UINTN)(J-I+1),Name)) {
      if(Count>=(UINT32)R/8)return FALSE;
      *Base=Be32(Reg+Count*8);*Size=Be32(Reg+Count*8+4);++Found;
    }
    ++Count;I=J+1;
  }
  return Found==1&&Count==(UINT32)R/8&&*Base&& !(*Base&3)&&*Size>=4&& !(*Size&3)&& (UINT64)*Base+*Size<=Limit;
}
STATIC BOOLEAN Peripheral(CONST VOID *F,INT32 N,INT32 Arb,UINT32 *Sid,UINT32 *Base,UINT32 *Size) {
  INT32 L,Parent=FdtParentOffset(F,N);CONST UINT8 *P;
  if(Parent<0||FdtParentOffset(F,Parent)!=Arb||!Enabled(F,N)||!Enabled(F,Parent)||
    fdt_node_check_compatible(F,Parent,"qcom,spmi-pmic"))return FALSE;
  P=FdtGetProp(F,Parent,"reg",&L);if(!P||L!=8||Be32(P)>15||Be32(P+4)!=0)return FALSE;
  *Sid=Be32(P);P=FdtGetProp(F,N,"reg",&L);if(!P||L!=8)return FALSE;
  *Base=Be32(P);*Size=Be32(P+4);
  return *Base&& !(*Base&255)&&*Size>=0x100&& !(*Size&255)&&*Base<=0xffff&&*Size<=0x10000-*Base;
}
STATIC BOOLEAN Targets(CONST VOID *F,INT32 Arb,RAPHAEL_INPUT_SNAPSHOT *O) {
  INT32 Keys=FdtNodeOffsetByCompatible(F,-1,"gpio-keys"),N,Up=-1,Gpio,Pon=-1,L;
  UINT32 Code,Type,Size,Base,Handle,Count=0;CONST UINT8 *P;
  if(Keys<0||!Enabled(F,Keys)||FdtNodeOffsetByCompatible(F,Keys,"gpio-keys")>=0)return FALSE;
  FdtForEachSubnode(N,F,Keys) {
    if(U32(F,N,"linux,code",&Code)&&Code==115){Up=N;++Count;}
  }
  if(Count!=1||!Enabled(F,Up)||!U32(F,Up,"debounce-interval",&O->DebounceMs)||O->DebounceMs>1000)return FALSE;
  P=FdtGetProp(F,Up,"gpios",&L);if(!P||L!=12)return FALSE;
  Handle=Be32(P);O->GpioNumber=Be32(P+4);O->GpioFlags=Be32(P+8);
  Gpio=FdtNodeOffsetByPhandle(F,Handle);
  if(Gpio<0||fdt_node_check_compatible(F,Gpio,"qcom,spmi-gpio")||
    !U32(F,Gpio,"#gpio-cells",&Count)||Count!=2||O->GpioFlags!=1||
    !Peripheral(F,Gpio,Arb,&O->VolumeSid,&Base,&Size)||
    O->GpioNumber<1||O->GpioNumber>Size/0x100)return FALSE;
  P=FdtGetProp(F,Gpio,"qcom,gpios-disallowed",&L);
  if(P) {if(L<0||L%4)return FALSE;for(INT32 I=0;I<L;I+=4)if(Be32(P+I)==O->GpioNumber)return FALSE;}
  // Physical GPIO numbering is one-based; disallowed pins do not compress its address.
  O->VolumeAddress=Base+(O->GpioNumber-1)*0x100+0x10;
  Count=0;
  N=-1;while((N=FdtNodeOffsetByCompatible(F,N,"qcom,qpnp-power-on"))>=0) {
    UINT32 HavePower=0,HaveDown=0;INT32 Child;
    FdtForEachSubnode(Child,F,N) {
      if(!U32(F,Child,"linux,code",&Code))continue;
      if(!U32(F,Child,"qcom,pon-type",&Type))return FALSE;
      if(Code==116&&Type==0)++HavePower;
      if(Code==114&&Type==1)++HaveDown;
    }
    if(HavePower==1&&HaveDown==1){Pon=N;++Count;}
  }
  if(Count!=1||!Peripheral(F,Pon,Arb,&O->PonSid,&Base,&Size)||Size<0x14)return FALSE;
  O->PonAddress=Base+0x10;return TRUE;
}
VOID RaphaelCollectInputMap(CONST VOID *F,RAPHAEL_INPUT_SNAPSHOT *O,RAPHAEL_INPUT_READ32 Read,VOID *Context) {
  INT32 Arb,Soc,L;CONST UINT8 *P;UINT64 Limit;
  for(UINTN I=0;I<sizeof(*O);++I)((UINT8 *)O)[I]=0;
  O->Version=1;O->Status=RaphaelInputNoHardware;
  Arb=FdtNodeOffsetByCompatible(F,-1,"qcom,spmi-pmic-arb");if(Arb<0)return;
  O->Status=RaphaelInputBadFdt;Soc=FdtPathOffset(F,"/soc");
  if(Soc<0||FdtParentOffset(F,Soc)!=0||FdtAddressCells(F,0)!=2||
    FdtAddressCells(F,Soc)!=1||FdtSizeCells(F,Soc)!=1||FdtParentOffset(F,Arb)!=Soc||
    !Enabled(F,Arb)||FdtNodeOffsetByCompatible(F,Arb,"qcom,spmi-pmic-arb")>=0)return;
  P=FdtGetProp(F,Soc,"ranges",&L);if(!P)return;
  if(L==0)Limit=0x100000000ULL;
  else if(L==16&&!Be32(P)&&!Be32(P+4)&&!Be32(P+8)&&Be32(P+12))Limit=Be32(P+12);
  else return;
  if(!U32(F,Arb,"qcom,ee",&O->Ee)||O->Ee>5||
    !U32(F,Arb,"qcom,channel",&O->Channel)||O->Channel>5||
    !Region(F,Arb,"core",&O->CoreBase,&O->CoreSize,Limit)||
    !Region(F,Arb,"cnfg",&O->CnfgBase,&O->CnfgSize,Limit)||
    !Region(F,Arb,"obsrvr",&O->ObserverBase,&O->ObserverSize,Limit)||
    O->CoreSize<=0x900||(O->CoreSize-0x900)/4>RAPHAEL_INPUT_MAX_APIDS||
    O->CnfgSize<0x700+(O->CoreSize-0x900)||
    O->ObserverSize<0x10000*O->Ee+0x80*((O->CoreSize-0x900)/4)||
    !Targets(F,Arb,O))return;
  UINT64 Bases[]={O->CoreBase,O->CnfgBase,O->ObserverBase};
  UINT64 Sizes[]={O->CoreSize,O->CnfgSize,O->ObserverSize};
  for(UINTN I=0;I<3;++I)for(UINTN J=0;J<I;++J)
    if(Bases[I]<Bases[J]+Sizes[J]&&Bases[J]<Bases[I]+Sizes[I])return;
  O->HardwareVersion=Read(O->CoreBase,Context);O->ReadCount=1;O->Status=RaphaelInputUnsupported;
  // Only the documented v5 register layout is accepted; do not infer later versions.
  if(O->HardwareVersion<0x50000000||O->HardwareVersion>=0x60000000)return;
  O->Count=(O->CoreSize-0x900)/4;O->PonApid=O->VolumeApid=0xffffffffU;
  O->PonOwner=O->VolumeOwner=0xffffffffU;
  for(UINT32 I=0;I<O->Count;++I) {
    O->Map[I]=Read((UINT64)O->CoreBase+0x900+4*I,Context);++O->ReadCount;
    if(!O->Map[I])continue;
    O->Owner[I]=Read((UINT64)O->CnfgBase+0x700+4*I,Context);++O->ReadCount;
    UINT32 Ppid=(O->Map[I]>>8)&0xfff,Owner=O->Owner[I]&7;
    if(Ppid==((O->PonSid<<8)|(O->PonAddress>>8))) {
      ++O->PonMatches;
      if(O->PonApid==0xffffffffU||Owner==O->Ee){O->PonApid=I;O->PonOwner=Owner;}
    }
    if(Ppid==((O->VolumeSid<<8)|(O->VolumeAddress>>8))) {
      ++O->VolumeMatches;
      if(O->VolumeApid==0xffffffffU||Owner==O->Ee){O->VolumeApid=I;O->VolumeOwner=Owner;}
    }
  }
  O->Status=O->PonMatches&&O->VolumeMatches?RaphaelInputMapCollected:RaphaelInputTargetsMissing;
}
