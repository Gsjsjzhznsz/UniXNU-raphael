// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelRamAliasLib.h>
STATIC_ASSERT (sizeof (RAPHAEL_RAM_ALIAS_RESULT) == 312, "alias result layout");
STATIC_ASSERT (sizeof (RAPHAEL_RAM_ALIAS_STATE) == 400, "64-bit alias state layout");

STATIC BOOLEAN Valid (UINT64 Base, UINT64 Bytes) {
  return Bytes != 0 && Base <= MAX_UINT64 - Bytes;
}
STATIC BOOLEAN Overlap (UINT64 A, UINT64 N, UINT64 B, UINT64 M) {
  return A < B + M && B < A + N;
}
STATIC VOID Fence (VOID) { __asm__ __volatile__ ("" ::: "memory"); }
STATIC UINT64 Digest (UINT64 D, UINT64 A, UINT64 V) {
  return ((D ^ A) * 1099511628211ULL ^ V) * 1099511628211ULL;
}
STATIC UINT64 Address (CONST RAPHAEL_RAM_ALIAS_RESULT *R, UINT64 I) {
  return R->Base + (I / 2) * RAPHAEL_RAM_PAGE_BYTES + ((I & 1) ? RAPHAEL_RAM_PAGE_BYTES - 8 : 0);
}
STATIC UINT64 Seal (CONST RAPHAEL_RAM_ALIAS_STATE *S) {
  CONST RAPHAEL_RAM_ALIAS_RESULT *R = &S->Result;
  UINT64 D = Digest (14695981039346656037ULL, R->Base, R->Bytes);
  D = Digest (D, R->Pages, R->Samples);
  return Digest (D, (UINTN)S->Backup, S->BackupBytes);
}
STATIC UINT64 BackupHash (CONST RAPHAEL_RAM_ALIAS_STATE *S) {
  UINT64 D = 14695981039346656037ULL;
  for (UINT64 I = 0; I < S->Result.Samples; ++I) D = Digest (D, Address (&S->Result, I), S->Backup[I]);
  return D;
}
STATIC VOID ClearBackup (RAPHAEL_RAM_ALIAS_STATE *S) {
  for (UINTN I = 0; I < S->BackupBytes / sizeof (UINT64); ++I) S->Backup[I] = 0;
  S->Result.BackupWords = 0;
  S->BackupDigest = 0;
}
STATIC BOOLEAN Clock (RAPHAEL_RAM_ALIAS_STATE *S) {
  RAPHAEL_RAM_ALIAS_RESULT *R = &S->Result;
  UINT64 Previous = R->EndCounter, Now = S->Counter (S->Context);
  R->EndCounter = Now;
  if (Now < Previous || Now < R->StartCounter || Now - R->StartCounter > R->Frequency * 8) {
    R->Status = 6; R->Reason = 6; return FALSE;
  }
  return TRUE;
}
STATIC BOOLEAN SyncPage (RAPHAEL_RAM_ALIAS_STATE *S, UINT64 Page, UINT64 *Completed) {
  ++S->Result.SyncAttempts;
  if (!S->Sync (S->Result.Base + Page * RAPHAEL_RAM_PAGE_BYTES, RAPHAEL_RAM_PAGE_BYTES, S->Context)) return FALSE;
  ++*Completed;
  return TRUE;
}
STATIC BOOLEAN RejectRecovery (RAPHAEL_RAM_ALIAS_STATE *S, UINT64 Reason) {
  S->Result.Status = 7; S->Result.Reason = Reason; return FALSE;
}
BOOLEAN RaphaelRestoreRamAliases (RAPHAEL_RAM_ALIAS_STATE *S) {
  if (S == NULL) return FALSE;
  RAPHAEL_RAM_ALIAS_RESULT *R = &S->Result;
  if (R->RestoreActive) return FALSE;
  if (!R->Dirty) return R->ArmedWords == 0 ? TRUE : RejectRecovery (S, 8);
  // Validate bounds before hashing or issuing ANY recovery store. The seal and
  // complemented high-water mark detect accidental metadata damage; neither is
  // a cryptographic or DMA protection mechanism.
  if (R->Version != 1 || R->Dirty != 1 || R->PageBytes != RAPHAEL_RAM_PAGE_BYTES ||
      R->Bytes != RAPHAEL_RAM_WINDOW_BYTES || !Valid (R->Base, R->Bytes) ||
      (R->Base & (RAPHAEL_RAM_STRIDE - 1)) || R->Pages == 0 || R->Pages > 65536 ||
      R->Samples != R->Pages * 2 || R->BackupWords != R->Samples ||
      R->ArmedWords == 0 || R->ArmedWords > R->Samples || S->ArmedMirror != ~R->ArmedWords ||
      S->Backup == NULL || ((UINTN)S->Backup & 7) || S->BackupBytes != R->Samples * 8 ||
      !Valid ((UINTN)S, sizeof (*S)) || !Valid ((UINTN)S->Backup, S->BackupBytes) ||
      Overlap ((UINTN)S, sizeof (*S), R->Base, R->Bytes) ||
      Overlap ((UINTN)S->Backup, S->BackupBytes, R->Base, R->Bytes) ||
      Overlap ((UINTN)S->Backup, S->BackupBytes, (UINTN)S, sizeof (*S)) ||
      S->Read == NULL || S->Write == NULL || S->Sync == NULL || S->JournalSeal != Seal (S))
    return RejectRecovery (S, 8);
  if (BackupHash (S) != S->BackupDigest || S->BackupDigest != R->OriginalDigest)
    return RejectRecovery (S, 9);

  R->RestoreActive = 1; R->Phase = 6; ++R->RestoreAttempts;
  Fence ();
  BOOLEAN Ok = TRUE;
  UINT64 ArmedPages = (R->ArmedWords + 1) / 2;
  // Drain every possibly dirty marker line BEFORE the first original store.
  // Otherwise an aliased page's late cache writeback could overwrite recovery.
  for (UINT64 Page = 0; Page < ArmedPages; ++Page)
    if (!SyncPage (S, Page, &R->RestorePreSync)) Ok = FALSE;
  for (UINT64 Page = 0; Page < ArmedPages; ++Page) {
    for (UINT64 I = Page * 2; I < MIN (Page * 2 + 2, R->ArmedWords); ++I) {
      ++R->WriteAttempts;
      if (!S->Write (Address (R, I), S->Backup[I], S->Context)) Ok = FALSE;
    }
    if (!SyncPage (S, Page, &R->RestoreWriteSync)) Ok = FALSE;
  }
  UINT64 D = 14695981039346656037ULL;
  // Verify ALL backed-up samples, including addresses changed only by aliases.
  for (UINT64 Page = 0; Page < R->Pages; ++Page) {
    if (!SyncPage (S, Page, &R->RestoreReadSync)) Ok = FALSE;
    for (UINT64 I = Page * 2; I < Page * 2 + 2; ++I) {
      UINT64 Value = 0;
      ++R->ReadAttempts;
      if (!S->Read (Address (R, I), &Value, S->Context) || Value != S->Backup[I]) {
        ++R->RestoreMismatches; Ok = FALSE;
      }
      D = Digest (D, Address (R, I), Value);
    }
  }
  R->RestoreDigest = D;
  if (D != R->OriginalDigest) Ok = FALSE;
  R->RestoreActive = 0;
  if (!Ok) return RejectRecovery (S, 7);
  R->RestoredSamples = R->Samples;
  Fence ();
  ClearBackup (S);
  R->ArmedWords = 0; S->ArmedMirror = MAX_UINT64;
  Fence ();
  R->Dirty = 0;
  return TRUE;
}

STATIC BOOLEAN Gates (
  CONST RAPHAEL_RAM_POLICY *P, UINTN PolicyBytes,
  CONST RAPHAEL_RAM_READ_RESULT *B, CONST RAPHAEL_RAM_MAPPED_RESULT *M,
  CONST RAPHAEL_RAM_ENTRY *E) {
  STATIC CONST UINT8 PaBits[16] = {32,36,40,42,44,48,52,0,0,0,0,0,0,0,0,0};
  if (P->Version != 1 || P->HeaderBytes != 64 || P->GuardCount == 0 || P->GuardCount > RAPHAEL_RAM_MAX_GUARDS ||
      PolicyBytes != 64 + 16 * P->GuardCount || P->TotalBytes != PolicyBytes ||
      P->Bytes != RAPHAEL_RAM_WINDOW_BYTES || !Valid (P->Base, P->Bytes) || (P->Base & (RAPHAEL_RAM_STRIDE - 1)) ||
      P->Stride != RAPHAEL_RAM_STRIDE || P->MaxReads != 256 ||
      B->Version != 1 || B->Status != 3 || B->Reason || B->Base != P->Base || B->Bytes != P->Bytes || B->Stride != P->Stride ||
      B->Requested != 256 || B->Attempted != 256 || B->Completed != 256 || B->PolicyGuards != P->GuardCount ||
      B->EntryGuards == 0 || B->EntryGuards > 8 || B->RamRanges == 0 || B->RamRanges > 32 ||
      B->FixedReservations > 128 || B->HeaderReservations > 128 || B->DynamicPools > 128 || B->NonZero > 256 ||
      !PaBits[B->Mmfr0 & 15] || B->PhysicalBits != PaBits[B->Mmfr0 & 15] || B->PhysicalBits > 48 ||
      B->ActiveAddress != P->Base + P->Bytes - 8 || B->EndCounter < B->StartCounter ||
      B->CurrentEl != 4 || (B->Sctlr & 0x1005) || (B->Daif & 0x3c0) != 0x3c0 ||
      B->Frequency < 1000 || B->Frequency > 1000000000 || B->EndCounter - B->StartCounter > B->Frequency / 10 ||
      M->Version != 1 || M->Status != 3 || M->Reason || M->Base != B->Base || M->Bytes != B->Bytes || M->Stride != B->Stride ||
      M->Requested != 256 || M->Attempted != 256 || M->Completed != 256 || M->ActiveAddress != B->ActiveAddress ||
      M->BeforeDigest != B->Digest || M->Digest != B->Digest || M->NonZero != B->NonZero ||
      M->ReadTranslations != 256 || M->WriteDenied != 256 || M->ParPreserved != 256 ||
      M->OriginalPar != M->RestoredPar || M->Frequency != B->Frequency || M->StartCounter < B->EndCounter ||
      M->EndCounter < M->StartCounter || M->EndCounter - M->StartCounter > B->Frequency / 10 ||
      E->CurrentEl != 4 || (E->Sctlr & 0x1005) != 0x1005 || (E->Daif & 0x3c0) != 0x3c0 ||
      E->CurrentEl != M->CurrentEl || E->Sctlr != M->Sctlr || E->Daif != M->Daif ||
      E->Frequency != B->Frequency || E->Mmfr0 != B->Mmfr0 || E->PhysicalBits != B->PhysicalBits ||
      E->GuardCount != B->EntryGuards || E->GuardCount == 0 || E->GuardCount > 8 ||
      P->Base + P->Bytes > (1ULL << E->PhysicalBits)) return FALSE;
  for (UINTN I = 0; I < P->GuardCount; ++I)
    if (!Valid (P->Guards[I].Base, P->Guards[I].Length) ||
        Overlap (P->Guards[I].Base, P->Guards[I].Length, P->Base, P->Bytes)) return FALSE;
  for (UINTN I = 0; I < E->GuardCount; ++I)
    if (!Valid (E->Guards[I].Base, E->Guards[I].Length) ||
        Overlap (E->Guards[I].Base, E->Guards[I].Length, P->Base, P->Bytes)) return FALSE;
  return TRUE;
}

BOOLEAN RaphaelProbeRamAliases (
  RAPHAEL_RAM_ALIAS_STATE *S, CONST RAPHAEL_RAM_POLICY *P, UINTN PolicyBytes,
  CONST RAPHAEL_RAM_READ_RESULT *B, CONST RAPHAEL_RAM_MAPPED_RESULT *M, CONST RAPHAEL_RAM_ENTRY *E,
  UINT64 Pages, UINT64 *Backup, UINTN BackupBytes,
  RAPHAEL_RAM_READ64 Read, RAPHAEL_RAM_WRITE64 Write, RAPHAEL_RAM_TRANSLATE Translate,
  RAPHAEL_RAM_CACHE_SYNC Sync, RAPHAEL_RAM_COUNTER Counter, VOID *Context) {
  if (S == NULL || S->Result.Dirty || S->Running || S->Result.RestoreActive ||
      P == NULL || B == NULL || M == NULL || E == NULL || Backup == NULL) return FALSE;
  // Reject aliases before clearing any state or input. Input objects themselves
  // remain caller-owned and immutable; Context extent is a caller obligation.
  RAPHAEL_RANGE Objects[] = {{(UINTN)S,sizeof (*S)}, {(UINTN)P,PolicyBytes},
    {(UINTN)B,sizeof (*B)}, {(UINTN)M,sizeof (*M)}, {(UINTN)E,sizeof (*E)}, {(UINTN)Backup,BackupBytes}};
  if (PolicyBytes < 64) return FALSE;
  for (UINTN I = 0; I < ARRAY_SIZE (Objects); ++I) {
    if (!Valid (Objects[I].Base, Objects[I].Length)) return FALSE;
    for (UINTN J = 0; J < I; ++J)
      if (Overlap (Objects[I].Base, Objects[I].Length, Objects[J].Base, Objects[J].Length)) return FALSE;
  }
  for (UINTN I = 0; I < sizeof (*S); ++I) ((UINT8 *)S)[I] = 0;
  RAPHAEL_RAM_ALIAS_RESULT *R = &S->Result;
  R->Version = 1; R->Status = 4; R->Reason = 1;
  if (Pages == 0 || Pages > 65536 || BackupBytes != Pages * 16 || ((UINTN)Backup & 7) ||
      Read == NULL || Write == NULL || Translate == NULL || Sync == NULL || Counter == NULL ||
      !Gates (P, PolicyBytes, B, M, E)) return FALSE;
  for (UINTN I = 0; I < ARRAY_SIZE (Objects); ++I)
    if (Overlap (Objects[I].Base, Objects[I].Length, P->Base, P->Bytes)) return FALSE;
  if (Context != NULL && (Overlap ((UINTN)Context, 1, P->Base, P->Bytes) ||
      Overlap ((UINTN)Context, 1, (UINTN)S, sizeof (*S)) ||
      Overlap ((UINTN)Context, 1, (UINTN)Backup, BackupBytes))) return FALSE;
  S->Backup = Backup; S->BackupBytes = BackupBytes;
  S->Read = Read; S->Write = Write; S->Sync = Sync; S->Counter = Counter; S->Context = Context;
  S->Running = 1; S->ArmedMirror = MAX_UINT64;
  R->Status = 2; R->Reason = 0; R->Base = P->Base; R->Bytes = P->Bytes;
  R->PageBytes = RAPHAEL_RAM_PAGE_BYTES; R->Pages = Pages; R->Samples = Pages * 2;
  R->CurrentEl = E->CurrentEl; R->Sctlr = E->Sctlr; R->Daif = E->Daif; R->Frequency = E->Frequency;
  R->OriginalDigest = 14695981039346656037ULL;
  R->StartCounter = R->EndCounter = Counter (Context);
  if (R->StartCounter < M->EndCounter) { R->Status = 6; R->Reason = 6; goto Done; }
  R->Phase = 1;
  for (UINT64 I = 0; I < R->Samples; ++I) {
    if (!(I & 1) && !Clock (S)) goto Done;
    UINT64 A = Address (R, I), RP = 0, WP = 0, OP = 0, Restored = 0;
    if (!Translate (A, &RP, &WP, &OP, &Restored, Context) || OP != Restored ||
        (RP & 1) || (WP & 1) || (RP >> 56) != 0xff || (WP >> 56) != 0xff ||
        (RP & 0x0000fffffffff000ULL) != (A & ~4095ULL) ||
        (WP & 0x0000fffffffff000ULL) != (A & ~4095ULL)) {
      R->Status = 5; R->Reason = 11; goto Done;
    }
    ++R->ReadWriteTranslations; ++R->ParPreserved;
  }
  // Drain the entire sample set before acquiring the first backup. This keeps
  // late writebacks through a DRAM alias from changing an earlier backup.
  R->Phase = 2;
  for (UINT64 Page = 0; Page < Pages; ++Page) {
    if (!Clock (S)) goto Done;
    if (!SyncPage (S, Page, &R->PrepareSync)) { R->Status = 5; R->Reason = 10; goto Done; }
  }
  R->Phase = 3;
  for (UINT64 Page = 0; Page < Pages; ++Page) {
    if (!Clock (S)) goto Done;
    if (!SyncPage (S, Page, &R->BackupSync)) { R->Status = 5; R->Reason = 10; goto Done; }
    for (UINT64 I = Page * 2; I < Page * 2 + 2; ++I) {
      ++R->ReadAttempts;
      if (!Read (Address (R, I), &Backup[I], Context)) { R->Status = 5; R->Reason = 2; goto Done; }
      ++R->BackupWords;
      R->OriginalDigest = Digest (R->OriginalDigest, Address (R, I), Backup[I]);
    }
  }
  S->BackupDigest = BackupHash (S); S->JournalSeal = Seal (S);
  if (S->BackupDigest != R->OriginalDigest) { R->Status = 5; R->Reason = 9; goto Done; }
  for (UINT64 Round = 0; Round < 2; ++Round) {
    R->Phase = 4;
    for (UINT64 Page = 0; Page < Pages; ++Page) {
      if (!Clock (S)) goto Done;
      for (UINT64 I = Page * 2; I < Page * 2 + 2; ++I) {
        // Monotonic high-water mark is NEVER reset for the second round.
        if (I + 1 > R->ArmedWords) R->ArmedWords = I + 1;
        S->ArmedMirror = ~R->ArmedWords; R->Dirty = 1;
        Fence ();
        UINT64 Value = (Address (R, I) ^ 0xa5a55a5a3c3cc3c3ULL) ^ (Round ? MAX_UINT64 : 0);
        ++R->WriteAttempts;
        if (!Write (Address (R, I), Value, Context)) { R->Status = 5; R->Reason = 3; goto Done; }
      }
      if (!SyncPage (S, Page, &R->PatternSync)) { R->Status = 5; R->Reason = 10; goto Done; }
    }
    R->Phase = 5;
    for (UINT64 Page = 0; Page < Pages; ++Page) {
      if (!Clock (S)) goto Done;
      if (!SyncPage (S, Page, &R->VerifySync)) { R->Status = 5; R->Reason = 10; goto Done; }
      for (UINT64 I = Page * 2; I < Page * 2 + 2; ++I) {
        UINT64 Value = 0, Expected = (Address (R, I) ^ 0xa5a55a5a3c3cc3c3ULL) ^ (Round ? MAX_UINT64 : 0);
        ++R->ReadAttempts;
        if (!Read (Address (R, I), &Value, Context)) { R->Status = 5; R->Reason = 4; goto Done; }
        if (Value != Expected) { ++R->PatternMismatches; R->Status = 5; R->Reason = 5; goto Done; }
        ++R->PatternWords;
      }
    }
    ++R->Rounds;
  }
Done:
  if (R->Dirty || R->ArmedWords) {
    if (!RaphaelRestoreRamAliases (S)) { S->Running = 0; return FALSE; }
  } else ClearBackup (S);
  S->Running = 0;
  if (R->Status != 2) return FALSE;
  if (!Clock (S)) return FALSE;
  if (R->Rounds != 2 || R->RestoredSamples != R->Samples || R->OriginalDigest != R->RestoreDigest)
    return RejectRecovery (S, 8);
  R->Status = 3; R->Reason = 0; R->Phase = 7;
  return TRUE;
}
