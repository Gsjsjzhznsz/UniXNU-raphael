// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_RAM_WRITE_LIB_H
#define RAPHAEL_RAM_WRITE_LIB_H
#include <RaphaelRamRead.h>
#define RAPHAEL_RAM_PAGE_BYTES 4096ULL
#define RAPHAEL_RAM_PAGE_WORDS (RAPHAEL_RAM_PAGE_BYTES/8)
typedef BOOLEAN (*RAPHAEL_RAM_WRITE64)(UINT64 Address, UINT64 Value, VOID *Context);
// New standalone diagnostic; not wired into SEC or the allocator.
// Status: 1 initialized, 2 active, 3 complete, 4 rejected, 5 I/O/pattern failure,
// 6 clock/deadline failure, 7 incomplete restoration. Dirty is cleared only
// after all original words were written and independently read back.
typedef struct {
 UINT64 Version,Status,Reason,Base,Bytes,PageBytes,RequestedPages,CompletedPages;
 UINT64 ActivePage,BackupWords,Dirty,RestoredPages,ReadAttempts,WriteAttempts;
 UINT64 PatternWords,PatternMismatches,RestoreWords,RestoreMismatches;
 UINT64 OriginalDigest,RestoreDigest,StartCounter,EndCounter,Frequency;
} RAPHAEL_RAM_WRITE_RESULT;
typedef struct {
 RAPHAEL_RAM_WRITE_RESULT Result;
 UINT64 *Backup;
 RAPHAEL_RAM_READ64 Read;
 RAPHAEL_RAM_WRITE64 Write;
 RAPHAEL_RAM_COUNTER Counter;
 VOID *Context;
 UINT64 BackupDigest;
} RAPHAEL_RAM_WRITE_STATE;
// State must initially be zeroed. The backup must be disjoint from state and
// immutable input structures. Callback failure must return normally. A real
// synchronous exception requires a separately validated recovery path.
// Caller must supply this boot's successful source/FDT/CPU read gate, an owned
// page backup, and bounded physical callbacks. No memory ownership is granted.
BOOLEAN RaphaelWriteRamPages(RAPHAEL_RAM_WRITE_STATE *State,
 CONST RAPHAEL_RAM_POLICY *Policy, UINTN PolicyBytes, CONST RAPHAEL_RAM_READ_RESULT *ReadGate,
 UINT64 Pages, UINT64 *Backup, UINTN BackupBytes,
 RAPHAEL_RAM_READ64 Read, RAPHAEL_RAM_WRITE64 Write,
 RAPHAEL_RAM_COUNTER Counter, VOID *Context);
// May be called from the caller's exception path. A restore failure retains
// Dirty and all original backup words; the caller must not resume allocation.
BOOLEAN RaphaelRestoreRamPage(RAPHAEL_RAM_WRITE_STATE *State);
#endif
