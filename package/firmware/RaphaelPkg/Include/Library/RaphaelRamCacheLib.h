// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_RAM_CACHE_LIB_H
#define RAPHAEL_RAM_CACHE_LIB_H
#include <RaphaelRamMapped.h>
#include <Library/RaphaelRamWriteLib.h>
// Separate metadata, followed by the unchanged page engine's 23-word wire.
// No allocator or RAM ownership grant. Sync must clean/invalidate to PoC.
typedef struct {
 UINT64 Version,Status,Reason,Base,Bytes,Pages,CurrentEl,Sctlr,Daif,Frequency;
 UINT64 ReadWriteTranslations,ParPreserved,PrePageSync,PostPageSync,MapRestored,RestoreDenials;
} RAPHAEL_RAM_CACHE_RESULT;
typedef BOOLEAN (*RAPHAEL_RAM_CACHE_SYNC)(UINT64 Address,UINT64 Bytes,VOID *Context);
typedef struct {
 RAPHAEL_RAM_CACHE_RESULT Result;
 RAPHAEL_RAM_WRITE_STATE *Engine;
 RAPHAEL_RAM_READ64 Read;
 RAPHAEL_RAM_WRITE64 Write;
 RAPHAEL_RAM_CACHE_SYNC Sync;
 RAPHAEL_RAM_COUNTER Counter;
 VOID *Context;
} RAPHAEL_RAM_CACHE_STATE;
// Shared by the generic model wrapper and native access callbacks. Keep the
// phase rules identical while avoiding a second indirect call for each word.
STATIC __attribute__((always_inline)) inline BOOLEAN
RaphaelRamCacheBeforeRead(RAPHAEL_RAM_CACHE_STATE *C,UINT64 Address){
 RAPHAEL_RAM_WRITE_RESULT *R=&C->Engine->Result;
 if(Address==R->ActivePage&&!R->Dirty&&!R->BackupWords){
  if(!C->Sync(R->ActivePage,RAPHAEL_RAM_PAGE_BYTES,C->Context))return FALSE;
  ++C->Result.PrePageSync;
 }
 return TRUE;
}
STATIC __attribute__((always_inline)) inline BOOLEAN
RaphaelRamCacheAfterWrite(RAPHAEL_RAM_CACHE_STATE *C,UINT64 Address){
 RAPHAEL_RAM_WRITE_RESULT *R=&C->Engine->Result;
 if(Address==R->ActivePage+RAPHAEL_RAM_PAGE_BYTES-8){
  if(!C->Sync(R->ActivePage,RAPHAEL_RAM_PAGE_BYTES,C->Context))return FALSE;
  ++C->Result.PostPageSync;
 }
 return TRUE;
}
BOOLEAN RaphaelWriteRamWithCache(RAPHAEL_RAM_CACHE_STATE *Cache,RAPHAEL_RAM_WRITE_STATE *Engine,
 CONST RAPHAEL_RAM_POLICY *Policy,UINTN PolicyBytes,CONST RAPHAEL_RAM_READ_RESULT *Before,
 CONST RAPHAEL_RAM_MAPPED_RESULT *Mapped,CONST RAPHAEL_RAM_ENTRY *Entry,UINT64 Pages,UINT64 *Backup,
 RAPHAEL_RAM_READ64 Read,RAPHAEL_RAM_WRITE64 Write,RAPHAEL_RAM_TRANSLATE Translate,
 RAPHAEL_RAM_CACHE_SYNC Sync,RAPHAEL_RAM_COUNTER Counter,VOID *Context);
// Native Read/Write receive Cache as their context and must invoke the shared
// BeforeRead/AfterWrite helpers around each successful physical access.
// Counter and Sync still receive the caller's original Context. This contract
// is used only by audited callbacks, never as an implicit fallback.
BOOLEAN RaphaelWriteRamWithCacheDirect(RAPHAEL_RAM_CACHE_STATE *Cache,RAPHAEL_RAM_WRITE_STATE *Engine,
 CONST RAPHAEL_RAM_POLICY *Policy,UINTN PolicyBytes,CONST RAPHAEL_RAM_READ_RESULT *Before,
 CONST RAPHAEL_RAM_MAPPED_RESULT *Mapped,CONST RAPHAEL_RAM_ENTRY *Entry,UINT64 Pages,UINT64 *Backup,
 RAPHAEL_RAM_READ64 Read,RAPHAEL_RAM_WRITE64 Write,RAPHAEL_RAM_TRANSLATE Translate,
 RAPHAEL_RAM_CACHE_SYNC Sync,RAPHAEL_RAM_COUNTER Counter,VOID *Context);
BOOLEAN RaphaelRunRamCacheWrite(CONST RAPHAEL_RAM_READ_RESULT *,CONST RAPHAEL_RAM_MAPPED_RESULT *,
 RAPHAEL_RAM_CACHE_STATE *,RAPHAEL_RAM_WRITE_STATE *,UINT64 *);
BOOLEAN RaphaelRestoreRamCacheMap(VOID);
#endif
