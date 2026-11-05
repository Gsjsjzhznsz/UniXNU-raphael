// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_MEMORY_CONTRACT_LIB_H
#define RAPHAEL_MEMORY_CONTRACT_LIB_H
#include <Base.h>

typedef struct {
  UINT64 Base;
  UINT64 Length;
} RAPHAEL_RANGE;

typedef struct {
  RAPHAEL_RANGE Range;
  UINT64 Alignment;
} RAPHAEL_ALLOCATION;

enum {
  RaphaelPlanOk = 0,
  RaphaelPlanBadArgument,
  RaphaelPlanWrongEntry,
  RaphaelPlanOverflow,
  RaphaelPlanAlignment,
  RaphaelPlanOutsideImage,
  RaphaelPlanOutsideRam,
  RaphaelPlanProtectedOverlap,
  RaphaelPlanAllocationOverlap
};

// Geometry check only: a passing result cannot establish memory ownership.
// The caller must supply the real loaded Image extent, RAM and every protected
// range, including the FDT, initrd and any still-owned firmware/runtime memory.
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
  );
#endif
