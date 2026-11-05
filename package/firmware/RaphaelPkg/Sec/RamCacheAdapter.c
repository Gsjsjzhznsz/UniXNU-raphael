// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelRamCacheLib.h>
#include <Library/ArmLib.h>
#include <Library/ArmMmuLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
STATIC volatile UINT64 mCacheMapActive __attribute__((section(".data")))=0;
STATIC UINT64 mCacheMapBase __attribute__((section(".data")))=0;
STATIC UINT64 mCacheMapBytes __attribute__((section(".data")))=0;
STATIC RAPHAEL_RAM_CACHE_STATE *mCacheState __attribute__((section(".data")))=NULL;
BOOLEAN RaphaelRestoreRamCacheMap(VOID){
 if(!mCacheMapActive)return TRUE;
 if(EFI_ERROR(ArmSetMemoryAttributes(mCacheMapBase,mCacheMapBytes,EFI_MEMORY_RO,EFI_MEMORY_RO)))return FALSE;
 if(!mCacheState)return FALSE;
 mCacheState->Result.RestoreDenials=0;
 for(UINT64 Off=0;Off<mCacheMapBytes;Off+=RAPHAEL_RAM_STRIDE)for(UINTN Tail=0;Tail<2;++Tail){
  UINT64 Address=mCacheMapBase+Off+(Tail?RAPHAEL_RAM_STRIDE-8:0),RP,WP,Original,Restored;
  if(!TranslateMappedRam(Address,&RP,&WP,&Original,&Restored,NULL)||Original!=Restored||
    (RP&1)||!(WP&1)||(RP>>56)!=0xff||(RP&0x0000fffffffff000ULL)!=(Address&~4095ULL))return FALSE;
  ++mCacheState->Result.RestoreDenials;
 }
 mCacheState->Result.MapRestored=1;mCacheMapActive=0;return TRUE;
}
STATIC UINT64 Counter(VOID *Context){(VOID)Context;return ArmReadCntPct();}
__attribute__((noinline)) STATIC BOOLEAN ReadCacheRam64(UINT64 Address,UINT64 *Value,VOID *Context){
 // Ordinary WB RAM on the same PE; phase completion is in SyncCachePage.
 // Compiler fences also keep backup/Dirty metadata across this access.
 RAPHAEL_RAM_CACHE_STATE *C=Context;
 if(!RaphaelRamCacheBeforeRead(C,Address))return FALSE;
 __asm__ volatile("" ::: "memory");
 *Value=*(volatile CONST UINT64 *)(UINTN)Address;
 __asm__ volatile("" ::: "memory");return TRUE;
}
extern VOID RaphaelRamWriteCheckpoint(VOID);
__attribute__((noinline)) STATIC BOOLEAN WriteCacheRam64(UINT64 Address,UINT64 Value,VOID *Context){
 RAPHAEL_RAM_CACHE_STATE *C=Context;RAPHAEL_RAM_WRITE_STATE *S=C->Engine;
 __asm__ volatile("" ::: "memory");
 *(volatile UINT64 *)(UINTN)Address=Value;
 __asm__ volatile("" ::: "memory");
 if(S->Result.WriteAttempts==257)RaphaelRamWriteCheckpoint();
 return RaphaelRamCacheAfterWrite(C,Address);
}
__attribute__((noinline)) STATIC BOOLEAN SyncCachePage(UINT64 Address,UINT64 Bytes,VOID *Context){
 (VOID)Context;
 if(!mCacheMapActive||(Address&4095)||Bytes!=RAPHAEL_RAM_PAGE_BYTES||Address<mCacheMapBase||
    Address>mCacheMapBase+mCacheMapBytes-Bytes)return FALSE;
 // Drain prior page accesses before maintenance, including partial stores
 // on the exception recovery path. The line walker and this caller both
 // complete with DSB SY before pattern/restore verification may refill.
 ArmDataSynchronizationBarrier();
 WriteBackInvalidateDataCacheRange((VOID *)(UINTN)Address,(UINTN)Bytes);ArmDataSynchronizationBarrier();return TRUE;
}
BOOLEAN RaphaelRunRamCacheWrite(CONST RAPHAEL_RAM_READ_RESULT *B,CONST RAPHAEL_RAM_MAPPED_RESULT *M,
 RAPHAEL_RAM_CACHE_STATE *C,RAPHAEL_RAM_WRITE_STATE *S,UINT64 *Backup){
 RAPHAEL_RAM_POLICY Policy;UINTN PolicyBytes;RAPHAEL_RAM_ENTRY E;
 if(M->Status!=3||!RaphaelLoadRamPolicy(&Policy,&PolicyBytes)||Policy.Base!=B->Base||Policy.Bytes!=B->Bytes)return FALSE;
 mCacheMapBase=B->Base;mCacheMapBytes=B->Bytes;mCacheState=C;mCacheMapActive=1;
 // Change permissions only; preserve WB attributes. Set active before calling
 // the updater so exception recovery also repairs a partially updated table.
 if(EFI_ERROR(ArmSetMemoryAttributes(B->Base,B->Bytes,0,EFI_MEMORY_RO)))return FALSE;
 ZeroMem(&E,sizeof(E));
 __asm__ volatile("mrs %0,currentel":"=r"(E.CurrentEl));__asm__ volatile("mrs %0,sctlr_el1":"=r"(E.Sctlr));
 __asm__ volatile("mrs %0,daif":"=r"(E.Daif));__asm__ volatile("mrs %0,id_aa64mmfr0_el1":"=r"(E.Mmfr0));
 __asm__ volatile("mrs %0,cntfrq_el0":"=r"(E.Frequency));E.PhysicalBits=ArmGetPhysicalAddressBits();
 BOOLEAN Ok=RaphaelWriteRamWithCacheDirect(C,S,&Policy,PolicyBytes,B,M,&E,
  FixedPcdGet32(PcdRaphaelRamCacheWritePages),Backup,ReadCacheRam64,WriteCacheRam64,TranslateMappedRam,SyncCachePage,Counter,S);
 if(S->Result.Dirty&&!RaphaelRestoreRamPage(S))return FALSE;
 if(!RaphaelRestoreRamCacheMap())return FALSE;
 return Ok;
}
