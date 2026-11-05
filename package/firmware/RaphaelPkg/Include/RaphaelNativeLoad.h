// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_LOAD_H
#define RAPHAEL_NATIVE_LOAD_H
#include <Uefi.h>
#define RAPHAEL_NATIVE_LOAD_MAGIC SIGNATURE_64('R','P','H','L','O','A','D','1')
#define RAPHAEL_NATIVE_LOAD_MAX_SEGMENTS 64
typedef struct {
  UINT64 Magic, Version, Count, VirtualBase, VirtualEnd, Entry, ArgsOffset;
  UINT64 TreeBytes, TreeCrc, PhysicalBase, WindowBytes, Frequency, Affinity;
} RAPHAEL_NATIVE_LOAD_POLICY;
typedef struct { UINT64 Offset, Bytes, FileBytes, Crc, Protection; } RAPHAEL_NATIVE_LOAD_SEGMENT;
// Version 2 appends one TrustCache; version 3 appends TrustCache then packed Data.
BOOLEAN RaphaelNativeHasData(VOID);
typedef struct { UINT64 Offset, Bytes, Crc, AdtOffset; } RAPHAEL_NATIVE_LOAD_TRUST;
typedef struct {
  UINT64 Version, Status, PhysicalBase, Args, Tree, Entry, WindowBytes;
  UINT64 SegmentCount, FileSegmentsOk, ZeroSegmentsOk, TreeCrc, ArgsOk;
  UINT64 ExitNoticeCount, Frequency, Affinity, Error;
} RAPHAEL_NATIVE_LOAD_RESULT;
EFI_STATUS RaphaelPrepareNativeLoad(VOID);
VOID RaphaelNativeLoadNotice(VOID);
BOOLEAN RaphaelNativeExitReturned(EFI_STATUS Status, EFI_SYSTEM_TABLE *SystemTable, EFI_BOOT_SERVICES *OldServices);
#endif
