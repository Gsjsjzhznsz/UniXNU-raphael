// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_PMAP_H
#define RAPHAEL_NATIVE_PMAP_H
#include <Uefi.h>
// The return bridge may straddle an architectural 2 MiB block boundary.
// Test the complete checked extent, never only the first instruction.
STATIC inline BOOLEAN RaphaelNativeRelayBlock(UINT64 Block,UINT64 Relay,UINT64 RelayBytes) {
 return RelayBytes&&Relay<=MAX_UINT64-RelayBytes&&Block<=MAX_UINT64-0x200000ULL&&
   Relay<Block+0x200000ULL&&Block<Relay+RelayBytes;
}
#define RAPHAEL_NATIVE_PMAP_SPARSE_BYTES 524288U
// Shared by the producer and SEC serializer: one capacity and owned range.
STATIC inline BOOLEAN RaphaelNativePmapSparseRange(UINT64 At,UINT64 Length,UINT64 Base,UINT64 Bytes) {
 return Length<=RAPHAEL_NATIVE_PMAP_SPARSE_BYTES&&At>=Base&&At-Base<=Bytes&&Length<=Bytes-(At-Base);
}
typedef struct {
 UINT64 Version,Status,Error,TransitionBase,TransitionBytes,TransitionCrcBefore,TransitionCrcAfter,TransitionOk,OriginalTtbr0,OriginalTtbr1,ObservedTransitionTtbr0,CleanBase,CleanBytes,TablePages,NonzeroDescriptors,SparseBytes,SparseCapacity,Root0Empty,RelayUnmapped,HighDataPages,HighProbes,CaptureOk,TableCrcXor,Reserved,AdtPhysical,AdtBytes,AdtCrcBefore,AdtCrcAfter,AdtCrcRestored,AdtRestored,AdtChangedBytes,AdtBackupOk;
} RAPHAEL_NATIVE_PMAP_RESULT;
typedef struct { RAPHAEL_NATIVE_PMAP_RESULT Result;UINT64 Sparse,AdtSnapshot; } RAPHAEL_NATIVE_PMAP_STATE;
EFI_STATUS RaphaelPrepareNativePmap(VOID);
EFI_STATUS RaphaelArmNativePmap(UINT64 Base,UINT64 Bytes,UINT64 Relay,UINT64 RelayBytes,UINT64 Tcr,UINT64 Args);
BOOLEAN RaphaelNativePmapRead(UINT64 Va,UINTN Bytes,VOID *Out,UINT64 *Pa);
UINT64 RaphaelNativePmapRoot(VOID);
UINT64 RaphaelNativePmapState(VOID);
BOOLEAN RaphaelCaptureNativePmap(UINT64 Root0,UINT64 Root1,UINT64 Checkpoint,UINT64 *Physical);
#endif
