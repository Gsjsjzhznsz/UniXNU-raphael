// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_RAM_ALIAS_LIB_H
#define RAPHAEL_RAM_ALIAS_LIB_H
#include <Library/RaphaelRamCacheLib.h>

// Independent simultaneous-sample diagnostic, not an allocation permission.
// Samples are the first and last UINT64 of each consecutive 4 KiB page.
// Status: 2 active, 3 complete, 4 input rejected, 5 I/O/pattern failure,
// 6 clock/deadline failure, 7 restoration incomplete. Phase is diagnostic only:
// 1 translation, 2 initial cache drain, 3 backup, 4 marker store, 5 marker
// verification, 6 restoration, 7 terminal. Existing RAM wires are unchanged.
typedef struct {
  UINT64 Version, Status, Reason, Phase, Base, Bytes, PageBytes, Pages, Samples;
  UINT64 BackupWords, ArmedWords, Dirty, RestoreActive, Rounds, PatternWords;
  UINT64 PatternMismatches, RestoredSamples, RestoreMismatches;
  UINT64 ReadAttempts, WriteAttempts, SyncAttempts, ReadWriteTranslations, ParPreserved;
  UINT64 PrepareSync, BackupSync, PatternSync, VerifySync;
  UINT64 RestorePreSync, RestoreWriteSync, RestoreReadSync, RestoreAttempts;
  UINT64 OriginalDigest, RestoreDigest, StartCounter, EndCounter, Frequency;
  UINT64 CurrentEl, Sctlr, Daif;
} RAPHAEL_RAM_ALIAS_RESULT;

typedef struct {
  RAPHAEL_RAM_ALIAS_RESULT Result;
  UINT64 *Backup;
  UINTN BackupBytes;
  RAPHAEL_RAM_READ64 Read;
  RAPHAEL_RAM_WRITE64 Write;
  RAPHAEL_RAM_CACHE_SYNC Sync;
  RAPHAEL_RAM_COUNTER Counter;
  VOID *Context;
  UINT64 BackupDigest, JournalSeal, ArmedMirror, Running;
} RAPHAEL_RAM_ALIAS_STATE;

// Initially zero State; all input objects and exact Pages*16-byte, aligned,
// caller-owned Backup must be mutually disjoint and outside the whole window.
// Callbacks/context and backing storage remain valid until successful recovery.
// Sync must perform real clean/invalidate to PoC with completion barriers.
// Before any marker, back up ALL samples and check both RW identity translations
// of EVERY sample, using this boot's source/FDT, mapped and live entry gates.
// Counter uses the existing eight-second forward-progress bound. Mandatory
// restoration has no timeout. A callback may return FALSE after doing its work.
// Returning FALSE with Dirty set requires fail-closed handling and retention of
// the entire state/backup; do not resume allocation or original Android entry.
BOOLEAN RaphaelProbeRamAliases (
  RAPHAEL_RAM_ALIAS_STATE *State,
  CONST RAPHAEL_RAM_POLICY *Policy, UINTN PolicyBytes,
  CONST RAPHAEL_RAM_READ_RESULT *Before,
  CONST RAPHAEL_RAM_MAPPED_RESULT *Mapped,
  CONST RAPHAEL_RAM_ENTRY *Entry,
  UINT64 Pages, UINT64 *Backup, UINTN BackupBytes,
  RAPHAEL_RAM_READ64 Read, RAPHAEL_RAM_WRITE64 Write,
  RAPHAEL_RAM_TRANSLATE Translate, RAPHAEL_RAM_CACHE_SYNC Sync,
  RAPHAEL_RAM_COUNTER Counter, VOID *Context);

// Explicit retry is allowed after a normally returning recovery failure.
// Reentry while recovery is active is rejected without modifying its journal.
// Real synchronous exceptions require a separately qualified SEC recovery path;
// this standalone engine alone does not prove that path or phone RAM ownership.
BOOLEAN RaphaelRestoreRamAliases (RAPHAEL_RAM_ALIAS_STATE *State);
#endif
