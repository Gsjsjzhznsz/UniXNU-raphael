// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_RAM_MAPPED_H
#define RAPHAEL_RAM_MAPPED_H
#include <RaphaelRamRead.h>
// Independent wire. Existing MMU-off ram-read ABI remains unchanged.
// Status: 1 pre-map gate passed, 2 querying/reading, 3 complete, 4 input reject,
// 5 translation/attribute/permission/PAR failure, 6 time bound, 7 read failure,
// 8 changed sparse contents. This grants no allocator or DMA ownership.
typedef struct {
 UINT64 Version,Status,Reason,Base,Bytes,Stride,Requested,Attempted,Completed,ActiveAddress;
 UINT64 BeforeDigest,Digest,NonZero,StartCounter,EndCounter,Frequency,CurrentEl,Sctlr,Daif;
 UINT64 ReadTranslations,WriteDenied,ParPreserved,FirstReadPar,LastReadPar,LastWritePar,OriginalPar,RestoredPar;
} RAPHAEL_RAM_MAPPED_RESULT;
typedef BOOLEAN (*RAPHAEL_RAM_TRANSLATE)(UINT64 Address,UINT64 *ReadPar,UINT64 *WritePar,
 UINT64 *OriginalPar,UINT64 *RestoredPar,VOID *Context);
VOID RaphaelReadMappedRam(CONST RAPHAEL_RAM_READ_RESULT *Before,CONST RAPHAEL_RAM_ENTRY *Entry,
 RAPHAEL_RAM_MAPPED_RESULT *Result,RAPHAEL_RAM_TRANSLATE Translate,RAPHAEL_RAM_READ64 Read,
 RAPHAEL_RAM_COUNTER Counter,VOID *Context);
BOOLEAN RaphaelRunMappedRam(CONST RAPHAEL_RAM_READ_RESULT *Before,RAPHAEL_RAM_MAPPED_RESULT *Result);
VOID RaphaelRestoreMappedPar(VOID);
BOOLEAN TranslateMappedRam(UINT64,UINT64 *,UINT64 *,UINT64 *,UINT64 *,VOID *);
#endif
