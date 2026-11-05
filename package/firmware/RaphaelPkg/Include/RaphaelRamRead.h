// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_RAM_READ_H
#define RAPHAEL_RAM_READ_H
#include <Uefi.h>
#include <Library/RaphaelMemoryContractLib.h>
#define RAPHAEL_RAM_POLICY_GUID {0xd2cd8ed5,0xa64e,0x45d3,{0x8b,0x4e,0x3d,0x02,0xd1,0xf1,0xb0,0xfb}}
#define RAPHAEL_RAM_MAX_GUARDS 128
#define RAPHAEL_RAM_WINDOW_BYTES 0x10000000ULL
#define RAPHAEL_RAM_STRIDE 0x200000ULL
// Native little-endian immutable FV asset. Size is exactly 64+16*GuardCount.
typedef struct {
  UINT64 Version, HeaderBytes, TotalBytes, Base, Bytes, Stride, MaxReads, GuardCount;
  RAPHAEL_RANGE Guards[RAPHAEL_RAM_MAX_GUARDS];
} RAPHAEL_RAM_POLICY;
typedef struct {
  UINT64 CurrentEl, Sctlr, Daif, Mmfr0, PhysicalBits, Frequency, GuardCount;
  RAPHAEL_RANGE Guards[8];
} RAPHAEL_RAM_ENTRY;
// Only this materialized SEC data grows; the near-full entry context is unchanged.
// Status: 1 initialized, 2 validated/reading, 3 complete, 4 entry/policy reject,
// 5 FDT/guard reject, 6 clock/timeout reject, 7 callback failure.
typedef struct {
  UINT64 Version, Status, Reason, Base, Bytes, Stride, Requested, Attempted, Completed, ActiveAddress;
  UINT64 Digest, NonZero, StartCounter, EndCounter, Frequency, Mmfr0, PhysicalBits;
  UINT64 RamRanges, FixedReservations, HeaderReservations, DynamicPools, PolicyGuards, EntryGuards;
  UINT64 CurrentEl, Sctlr, Daif;
} RAPHAEL_RAM_READ_RESULT;
typedef BOOLEAN (*RAPHAEL_RAM_READ64)(UINT64 Address, UINT64 *Value, VOID *Context);
typedef UINT64 (*RAPHAEL_RAM_COUNTER)(VOID *Context);
VOID RaphaelReadRamWindow(CONST VOID *Fdt, CONST RAPHAEL_RAM_POLICY *Policy, UINTN PolicyBytes,
  CONST RAPHAEL_RAM_ENTRY *Entry, RAPHAEL_RAM_READ_RESULT *Result,
  RAPHAEL_RAM_READ64 Read, RAPHAEL_RAM_COUNTER Counter, VOID *Context);
BOOLEAN RaphaelLoadRamPolicy(RAPHAEL_RAM_POLICY *Policy,UINTN *PolicyBytes);
#endif
