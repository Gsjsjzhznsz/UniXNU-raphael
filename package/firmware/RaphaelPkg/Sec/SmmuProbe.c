// SPDX-License-Identifier: BSD-2-Clause-Patent
// Read-only SMMUv2 observations. Physical windows are exclusively FDT-derived.
// Interface semantics: pinned MiCode arm-smmu.c and arm-smmu-regs.h.
#include <RaphaelDisplayProbe.h>
#include <Library/FdtLib.h>
extern INT32 fdt_node_check_compatible (CONST VOID *, INT32, CONST CHAR8 *);

STATIC UINT32 Be32 (CONST VOID *P) {
  CONST UINT8 *B = P;
  return ((UINT32)B[0] << 24) | ((UINT32)B[1] << 16) | ((UINT32)B[2] << 8) | B[3];
}
STATIC BOOLEAN U32 (CONST VOID *F, INT32 N, CONST CHAR8 *K, UINT32 *V) {
  INT32 L; CONST VOID *P = FdtGetProp (F, N, K, &L);
  if (!P || L != 4) return FALSE;
  *V = Be32 (P); return TRUE;
}
STATIC BOOLEAN Text (CONST VOID *F, INT32 N, CONST CHAR8 *K, CONST CHAR8 *S) {
  INT32 L; CONST CHAR8 *P = FdtGetProp (F, N, K, &L);
  if (!P) return FALSE;
  for (INT32 I = 0; I < L; ++I) {
    if (P[I] != S[I]) return FALSE;
    if (!S[I]) return TRUE;
  }
  return FALSE;
}
STATIC BOOLEAN Enabled (CONST VOID *F, INT32 N) {
  INT32 L;
  return !FdtGetProp (F, N, "status", &L) || Text (F,N,"status","ok") || Text (F,N,"status","okay");
}
STATIC BOOLEAN Region (CONST VOID *F, INT32 N, UINT64 *Base, UINT32 *Size) {
  INT32 L; CONST UINT8 *P = FdtGetProp (F,N,"reg",&L);
  if (!P || L < 8 || L % 8 || !Enabled (F,N)) return FALSE;
  *Base = Be32 (P); *Size = Be32 (P+4);
  return *Base && !(*Base & 3) && *Size >= 4 && *Base + *Size <= 0xffffffffULL;
}
STATIC UINT32 Read (RAPHAEL_DISPLAY_SNAPSHOT *O, RAPHAEL_DISPLAY_READ32 Fn, VOID *C, UINT64 A) {
  UINT32 V = Fn (A,C);
  O->Samples[O->Count][0] = A;
  O->Samples[O->Count++][1] = V;
  return V;
}
VOID RaphaelCollectSmmu (CONST VOID *F, RAPHAEL_DISPLAY_SNAPSHOT *O,
                         RAPHAEL_DISPLAY_READ32 Fn, VOID *C) {
  INT32 Mdp, Smmu, Gcc, Soc, N, Gdsc, L;
  UINT32 Handle, Cells, Sid, Mask, Count = 1, Sids[16], Coverage[16] = {0};
  UINT32 PowerCount = 0, SmmuSize, GccSize, PowerSize;
  UINT64 Base, GccBase, Power[16], Temp, Limit;
  CONST UINT8 *P;
  UINT32 Matches[16] = {0}, Banks[16], BankCount = 0;
  STATIC CONST UINT32 CbOffsets[] = {0,4,0x10,0x20,0x24,0x28,0x2c,0x30,0x34,0x38,0x3c};
  if (O->Version != 3) return;
  O->Version = 4;
  if (O->Status != RaphaelDisplayCollected) return;
  O->Status = RaphaelSmmuBadFdt;
  // The preceding collector validated root/soc cell widths and identity ranges.
  // Limit the prefix so the worst-case append below cannot overrun its context.
  if (O->Count > 507) return;
  Soc = FdtPathOffset (F,"/soc");
  Mdp = FdtNodeOffsetByCompatible (F,-1,"qcom,sde-kms");
  Gcc = FdtNodeOffsetByCompatible (F,-1,"qcom,gcc-sm8150-v2");
  if (Mdp < 0 || Gcc < 0 || FdtParentOffset (F,Gcc) != Soc ||
      !Region (F,Gcc,&GccBase,&GccSize)) return;
  P = FdtGetProp (F,Soc,"ranges",&L);
  if (!P) return;
  if (L == 0) Limit = 0x100000000ULL;
  else if (L == 16 && !Be32 (P) && !Be32 (P+4) && !Be32 (P+8) && Be32 (P+12))
    Limit = Be32 (P+12);
  else return;
  P = FdtGetProp (F,Mdp,"iommus",&L);
  if (!P || L != 12) return;
  Handle = Be32 (P); Sid = Be32 (P+4); Mask = Be32 (P+8);
  Smmu = FdtNodeOffsetByPhandle (F,Handle);
  if (Smmu < 0 || FdtParentOffset (F,Smmu) != Soc ||
      fdt_node_check_compatible (F,Smmu,"qcom,qsmmu-v500") ||
      !U32 (F,Smmu,"#iommu-cells",&Cells) || Cells != 2 ||
      !Text (F,Smmu,"reg-names","base") || !Region (F,Smmu,&Base,&SmmuSize) ||
      Base + SmmuSize > Limit || SmmuSize < 0x2000 || (SmmuSize & 1) || Sid > 0x7fff || Mask > 0x7fff ||
      FdtGetProp (F,Smmu,"calxeda,smmu-secure-config-access",&L) ||
      FdtGetProp (F,Smmu,"qcom,enable-static-cb",&L) ||
      FdtGetProp (F,Smmu,"clock-names",&L) ||
      FdtGetProp (F,Smmu,"clocks",&L) ||
      FdtGetProp (F,Smmu,"qcom,regulator-names",&L)) return;
  Sids[0] = Sid & ~Mask;
  for (UINT32 Bit = 0; Bit < 15; ++Bit) if (Mask & (1U << Bit)) {
    if (Count == ARRAY_SIZE (Sids)) return;
    for (UINT32 I = 0; I < Count; ++I) Sids[Count+I] = Sids[I] | (1U << Bit);
    Count *= 2;
  }
  for (N = FdtFirstSubnode (F,Smmu); N >= 0; N = FdtNextSubnode (F,N)) {
    if (fdt_node_check_compatible (F,N,"qcom,qsmmuv500-tbu")) continue;
    P = FdtGetProp (F,N,"qcom,stream-id-range",&L);
    if (!P || L != 8) return;
    UINT32 Start = Be32 (P), Length = Be32 (P+4), Hits = 0;
    if (!Length || Start > 0x7fff || Length > 0x8000 - Start) return;
    for (UINT32 I = 0; I < Count; ++I) if (Sids[I] >= Start && Sids[I] - Start < Length) {
      if (++Coverage[I] != 1) return;
      ++Hits;
    }
    if (!Hits) continue;
    if (!Enabled (F,N) || PowerCount == ARRAY_SIZE (Power) ||
        !U32 (F,N,"vdd-supply",&Handle) ||
        FdtGetProp (F,N,"clock-names",&L) || FdtGetProp (F,N,"clocks",&L)) return;
    P = FdtGetProp (F,N,"qcom,regulator-names",&L);
    if (!P || L != 4 || !Text (F,N,"qcom,regulator-names","vdd")) return;
    Gdsc = FdtNodeOffsetByPhandle (F,Handle);
    if (Gdsc < 0 || FdtParentOffset (F,Gdsc) != Soc ||
        fdt_node_check_compatible (F,Gdsc,"qcom,gdsc") ||
        !Region (F,Gdsc,&Temp,&PowerSize) || PowerSize != 4 ||
        Temp < GccBase || Temp + 4 > GccBase + GccSize) return;
    for (UINT32 I = 0; I < PowerCount; ++I) if (Power[I] == Temp) return;
    Power[PowerCount++] = Temp;
  }
  for (UINT32 I = 0; I < Count; ++I) if (Coverage[I] != 1) return;
  // Worst case: 255 SMRs, one S2CR and 13 context registers per target SID.
  if (!PowerCount || O->Count + PowerCount + 4 + 255 + Count * 14 > RAPHAEL_DISPLAY_MAX_SAMPLES) return;
  O->Status = RaphaelSmmuPowerOff;
  for (UINT32 I = 0; I < PowerCount; ++I)
    if (!(Read (O,Fn,C,Power[I]) & 0x80000000U)) return;
  O->Status = RaphaelSmmuUnsupported;
  UINT32 Id0 = Read (O,Fn,C,Base+0x20), Id1 = Read (O,Fn,C,Base+0x24);
  Read (O,Fn,C,Base+0x28);
  Read (O,Fn,C,Base); // nonsecure CR0; no secure alias is requested.
  UINT32 Groups = Id0 & 255, PgShift = (Id1 >> 31) ? 16 : 12;
  UINT32 NumCb = Id1 & 255, NumS2 = (Id1 >> 16) & 255;
  UINT64 Half = SmmuSize / 2, Page = 1ULL << PgShift;
  // No probing writes to discover writable masks. Extended IDs are unsupported.
  if (!(Id0 & (1U << 27)) || !(Id0 & (3U << 29)) || (Id0 & (1U << 8)) ||
      !Groups || !NumCb || NumCb > 128 || NumS2 > NumCb ||
      (1ULL << (((Id1 >> 28) & 7) + 1 + PgShift)) != Half ||
      NumCb * Page > Half || Page + 0xa00 > Half) return;
  O->Status = RaphaelSmmuAmbiguous;
  for (UINT32 I = 0; I < Groups; ++I) {
    UINT32 Smr = Read (O,Fn,C,Base+0x800+I*4);
    if (!(Smr & 0x80000000U)) continue;
    UINT32 SmrMask = (Smr >> 16) & 0x7fff, SmrId = Smr & 0x7fff, Hits = 0;
    for (UINT32 J = 0; J < Count; ++J) if (!((Sids[J] ^ SmrId) & ~SmrMask)) {
      if (++Matches[J] != 1) return;
      ++Hits;
    }
    if (!Hits) continue;
    UINT32 S2cr = Read (O,Fn,C,Base+0xc00+I*4), Type = (S2cr >> 16) & 3;
    if (Type == 3) return;
    if (Type == 0) {
      UINT32 Bank = S2cr & 255;
      if (Bank >= NumCb) return;
      BOOLEAN Seen = FALSE;
      for (UINT32 J = 0; J < BankCount; ++J) if (Banks[J] == Bank) Seen = TRUE;
      if (!Seen) {
        if (BankCount == ARRAY_SIZE (Banks)) return;
        Banks[BankCount++] = Bank;
      }
    }
  }
  O->Status = RaphaelSmmuNoStream;
  for (UINT32 I = 0; I < Count; ++I) if (Matches[I] != 1) return;
  for (UINT32 I = 0; I < BankCount; ++I) {
    UINT32 Bank = Banks[I];
    Read (O,Fn,C,Base+Page+Bank*4); // CBAR
    Read (O,Fn,C,Base+Page+0x800+Bank*4); // CBA2R
    for (UINTN J = 0; J < ARRAY_SIZE (CbOffsets); ++J)
      Read (O,Fn,C,Base+Half+Bank*Page+CbOffsets[J]);
  }
  O->Status = RaphaelSmmuCollected;
}
