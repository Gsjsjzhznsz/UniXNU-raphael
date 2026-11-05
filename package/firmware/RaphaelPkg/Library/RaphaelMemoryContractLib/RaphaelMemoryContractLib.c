// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <Library/RaphaelMemoryContractLib.h>

STATIC BOOLEAN
ValidRange (RAPHAEL_RANGE Range)
{
  return Range.Length != 0 && Range.Base <= MAX_UINT64 - Range.Length;
}

STATIC BOOLEAN
Contains (RAPHAEL_RANGE Outer, RAPHAEL_RANGE Inner)
{
  return Inner.Base >= Outer.Base &&
         Inner.Base + Inner.Length <= Outer.Base + Outer.Length;
}

STATIC BOOLEAN
Overlaps (RAPHAEL_RANGE A, RAPHAEL_RANGE B)
{
  return A.Base < B.Base + B.Length && B.Base < A.Base + A.Length;
}

UINT32
RaphaelCheckMemoryPlan (
  UINT64 ExpectedEntry,
  RAPHAEL_RANGE LoadedImage,
  CONST RAPHAEL_ALLOCATION *Allocations,
  UINTN AllocationCount,
  CONST RAPHAEL_RANGE *Ram,
  UINTN RamCount,
  CONST RAPHAEL_RANGE *Protected,
  UINTN ProtectedCount,
  UINTN *RejectedIndex
  )
{
  UINTN I, J;
  BOOLEAN InRam;
  RAPHAEL_RANGE Candidate;
  UINT64 Alignment;
  if (RejectedIndex != NULL) *RejectedIndex = MAX_UINTN;
  if (Allocations == NULL || AllocationCount == 0 || Ram == NULL || RamCount == 0 ||
      (ProtectedCount != 0 && Protected == NULL)) return RaphaelPlanBadArgument;
  if (LoadedImage.Base != ExpectedEntry) return RaphaelPlanWrongEntry;
  if (!ValidRange (LoadedImage)) return RaphaelPlanOverflow;
  for (I = 0; I < RamCount; ++I) {
    if (!ValidRange (Ram[I])) return RaphaelPlanOverflow;
  }
  for (I = 0; I < ProtectedCount; ++I) {
    if (!ValidRange (Protected[I])) return RaphaelPlanOverflow;
  }
  for (I = 0; I < AllocationCount; ++I) {
    if (RejectedIndex != NULL) *RejectedIndex = I;
    Candidate = Allocations[I].Range;
    Alignment = Allocations[I].Alignment;
    if (!ValidRange (Candidate)) return RaphaelPlanOverflow;
    if (Alignment == 0 || (Alignment & (Alignment - 1)) != 0 ||
        Candidate.Base % Alignment != 0 || Candidate.Length % 4096 != 0)
      return RaphaelPlanAlignment;
    if (!Contains (LoadedImage, Candidate)) return RaphaelPlanOutsideImage;
    InRam = FALSE;
    for (J = 0; J < RamCount; ++J) {
      if (Contains (Ram[J], Candidate)) InRam = TRUE;
    }
    if (!InRam) return RaphaelPlanOutsideRam;
    for (J = 0; J < ProtectedCount; ++J) {
      if (Overlaps (Candidate, Protected[J])) return RaphaelPlanProtectedOverlap;
    }
    for (J = 0; J < I; ++J) {
      // Earlier allocations have already passed range/overflow checks.
      if (Overlaps (Candidate, Allocations[J].Range)) return RaphaelPlanAllocationOverlap;
    }
  }
  if (RejectedIndex != NULL) *RejectedIndex = MAX_UINTN;
  return RaphaelPlanOk;
}
