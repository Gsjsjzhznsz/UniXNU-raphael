// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelRamMapped.h>
#include <Library/ArmLib.h>
#include <Library/BaseMemoryLib.h>
STATIC volatile UINT64 mSavedPar __attribute__((section(".data")))=0;
STATIC volatile UINT64 mParActive __attribute__((section(".data")))=0;
__attribute__((noinline)) VOID RaphaelRestoreMappedPar(VOID){
 if(mParActive){__asm__ volatile("msr par_el1,%0\n isb"::"r"(mSavedPar):"memory");mParActive=0;}
}
__attribute__((noinline)) BOOLEAN TranslateMappedRam(UINT64 Address,UINT64 *ReadPar,UINT64 *WritePar,
 UINT64 *Original,UINT64 *Restored,VOID *Context){
 (VOID)Context;UINT64 P;
 __asm__ volatile("mrs %0,par_el1":"=r"(P));mSavedPar=P;mParActive=1;*Original=P;
 __asm__ volatile("at s1e1r,%1\n isb\n mrs %0,par_el1":"=r"(P):"r"(Address):"memory");*ReadPar=P;
 __asm__ volatile("at s1e1w,%1\n isb\n mrs %0,par_el1":"=r"(P):"r"(Address):"memory");*WritePar=P;
 RaphaelRestoreMappedPar();__asm__ volatile("mrs %0,par_el1":"=r"(P));*Restored=P;return TRUE;
}
__attribute__((noinline)) STATIC BOOLEAN ReadMappedRam64(UINT64 Address,UINT64 *Value,VOID *Context){
 // Synchronize the newly enabled translation regime; also keep this diagnostic
 // load site distinct from the pre-MMU callback under linker ICF.
 (VOID)Context;ArmDataSynchronizationBarrier();__asm__ volatile("isb":::"memory");
 *Value=*(volatile CONST UINT64 *)(UINTN)Address;
 ArmDataMemoryBarrier();return TRUE;
}
STATIC UINT64 Counter(VOID *Context){(VOID)Context;return ArmReadCntPct();}
BOOLEAN RaphaelRunMappedRam(CONST RAPHAEL_RAM_READ_RESULT *Before,RAPHAEL_RAM_MAPPED_RESULT *R){
 RAPHAEL_RAM_ENTRY E;ZeroMem(&E,sizeof(E));
 __asm__ volatile("mrs %0,currentel":"=r"(E.CurrentEl));
 __asm__ volatile("mrs %0,sctlr_el1":"=r"(E.Sctlr));
 __asm__ volatile("mrs %0,daif":"=r"(E.Daif));
 __asm__ volatile("mrs %0,id_aa64mmfr0_el1":"=r"(E.Mmfr0));
 __asm__ volatile("mrs %0,cntfrq_el0":"=r"(E.Frequency));E.PhysicalBits=ArmGetPhysicalAddressBits();
 RaphaelReadMappedRam(Before,&E,R,TranslateMappedRam,ReadMappedRam64,Counter,NULL);
 return R->Status==3;
}
