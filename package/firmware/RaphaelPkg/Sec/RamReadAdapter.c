// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelDiagnostic.h>
#include <RaphaelRamRead.h>
#include <Library/RaphaelRamWriteLib.h>
#include <Library/ArmLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/PrePiLib.h>
#include <Library/FdtLib.h>
#include <Pi/PiFirmwareFile.h>
// Candidate loads remain isolated and independently machine-code audited.
__attribute__((noinline)) STATIC BOOLEAN ReadRam64(UINT64 Address,UINT64 *Value,VOID *Context){
  (VOID)Context;ArmDataSynchronizationBarrier();
  *Value=*(volatile CONST UINT64 *)(UINTN)Address;
  ArmDataMemoryBarrier();return TRUE;
}
extern VOID RaphaelRamWriteCheckpoint(VOID);
__attribute__((noinline)) STATIC BOOLEAN WriteRam64(UINT64 Address,UINT64 Value,VOID *Context){
 RAPHAEL_RAM_WRITE_STATE *S=Context;
 ArmDataSynchronizationBarrier();
 *(volatile UINT64 *)(UINTN)Address=Value;
 ArmDataSynchronizationBarrier();
 if(S->Result.WriteAttempts==257)RaphaelRamWriteCheckpoint();
 return TRUE;
}
STATIC UINT64 Counter(VOID *Context){(VOID)Context;return ArmReadCntPct();}
BOOLEAN RaphaelLoadRamPolicy(RAPHAEL_RAM_POLICY *Policy,UINTN *PolicyBytes){
 EFI_GUID Guid=RAPHAEL_RAM_POLICY_GUID;EFI_PEI_FILE_HANDLE File;VOID *Data=NULL;
 UINT64 Base=FixedPcdGet64(PcdRaphaelFdBase),Size=FixedPcdGet32(PcdRaphaelFdSize),Address;
 if(!Policy||!PolicyBytes)return FALSE;
 if(EFI_ERROR(FfsFindFileByName(&Guid,(VOID *)(UINTN)Base,&File))||
    EFI_ERROR(FfsFindSectionData(EFI_SECTION_RAW,File,&Data)))return FALSE;
 Address=(UINTN)Data;
 if(Address<Base+4||Address>Base+Size||64>Base+Size-Address)return FALSE;
 EFI_COMMON_SECTION_HEADER *Header=(VOID *)((UINT8 *)Data-sizeof(*Header));
 UINT32 Length=Header->Size[0]|(Header->Size[1]<<8)|(Header->Size[2]<<16);
 if(Header->Type!=EFI_SECTION_RAW||Length<sizeof(*Header)+64||
    Length-sizeof(*Header)>sizeof(*Policy)||Length-sizeof(*Header)>Base+Size-Address)return FALSE;
 ZeroMem(Policy,sizeof(*Policy));*PolicyBytes=Length-sizeof(*Header);CopyMem(Policy,Data,*PolicyBytes);return TRUE;
}
BOOLEAN RaphaelRunRamRead(CONST VOID *Fdt,RAPHAEL_DIAGNOSTIC *D,RAPHAEL_RAM_READ_RESULT *R,RAPHAEL_RAM_WRITE_STATE *S,UINT64 *Backup){
 RAPHAEL_RAM_POLICY Policy;UINTN PolicyBytes;RAPHAEL_RAM_ENTRY E;
 R->Version=1;R->Status=4;R->Reason=1;
 if(!RaphaelLoadRamPolicy(&Policy,&PolicyBytes))return FALSE;
 ZeroMem(&E,sizeof(E));
  __asm__ volatile("mrs %0,currentel":"=r"(E.CurrentEl));
  __asm__ volatile("mrs %0,sctlr_el1":"=r"(E.Sctlr));
  __asm__ volatile("mrs %0,daif":"=r"(E.Daif));
  __asm__ volatile("mrs %0,id_aa64mmfr0_el1":"=r"(E.Mmfr0));
  __asm__ volatile("mrs %0,cntfrq_el0":"=r"(E.Frequency));
  E.PhysicalBits=ArmGetPhysicalAddressBits();
  E.Guards[E.GuardCount++]=(RAPHAEL_RANGE){D->ImageBase,D->ExtentEnd-D->ImageBase};
  E.Guards[E.GuardCount++]=(RAPHAEL_RANGE){D->X0,FdtTotalSize(Fdt)};
  E.Guards[E.GuardCount++]=(RAPHAEL_RANGE){D->Sp&~4095ULL,4096};
  E.Guards[E.GuardCount++]=(RAPHAEL_RANGE){D->Lr&~4095ULL,4096};
  RaphaelReadRamWindow(Fdt,&Policy,PolicyBytes,&E,R,ReadRam64,Counter,NULL);
  if(R->Status!=3)return FALSE;
  if(FixedPcdGet32(PcdRaphaelRamWritePages)){
    // This policy and read gate were produced immediately above from the same
    // boot. No prior-boot result or host assertion is substituted here.
    return RaphaelWriteRamPages(S,&Policy,PolicyBytes,R,
      FixedPcdGet32(PcdRaphaelRamWritePages),Backup,RAPHAEL_RAM_PAGE_BYTES,
      ReadRam64,WriteRam64,Counter,S);
  }
  return TRUE;
}
