// SPDX-License-Identifier: BSD-2-Clause-Patent
// An explicit experimental boot grant, distinct from a RAM-test result.
#include <PiPei.h>
#include <RaphaelKernelWindow.h>
#include <Library/ArmLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/PrePiLib.h>
STATIC RAPHAEL_KERNEL_WINDOW mWindow;
RAPHAEL_KERNEL_WINDOW *RaphaelKernelWindow (VOID) { return &mWindow; }

BOOLEAN RaphaelPrepareKernelWindow (CONST RAPHAEL_RANGE *Ram, UINTN RamCount,
  CONST RAPHAEL_RANGE *Protected, UINTN ProtectedCount, RAPHAEL_RANGE Extension)
{
  EFI_GUID Guid = RAPHAEL_KERNEL_WINDOW_POLICY_GUID;
  EFI_PEI_FILE_HANDLE File;
  VOID *Data = NULL;
  UINT64 Fd = FixedPcdGet64 (PcdRaphaelFdBase), FdSize = FixedPcdGet32 (PcdRaphaelFdSize);
  UINT64 Address;
  RAPHAEL_KERNEL_WINDOW_POLICY Policy;
  RAPHAEL_RANGE Guards[257];
  RAPHAEL_ALLOCATION Allocation;
  EFI_COMMON_SECTION_HEADER *Header;
  UINTN Bytes, Rejected;
  if (!FixedPcdGetBool (PcdRaphaelKernelWindow)) return TRUE;
  if (EFI_ERROR (FfsFindFileByName (&Guid, (VOID *)(UINTN)Fd, &File)) ||
      EFI_ERROR (FfsFindSectionData (EFI_SECTION_RAW, File, &Data))) return FALSE;
  Address = (UINTN)Data;
  if (Address < Fd + 4 || Address > Fd + FdSize || 64 > Fd + FdSize - Address) return FALSE;
  Header = (VOID *)((UINT8 *)Data - sizeof (*Header));
  Bytes = Header->Size[0] | (Header->Size[1] << 8) | (Header->Size[2] << 16);
  if (Header->Type != EFI_SECTION_RAW || Bytes < 68 || Bytes - 4 > sizeof (Policy) ||
      Bytes - 4 > Fd + FdSize - Address) return FALSE;
  Bytes -= 4;
  ZeroMem (&Policy, sizeof (Policy));
  CopyMem (&Policy, Data, Bytes);
  if (Policy.Magic != RAPHAEL_KERNEL_WINDOW_MAGIC || Policy.Version != 1 ||
      Policy.TotalBytes != Bytes || !Policy.GuardCount || Policy.GuardCount > 128 ||
      Bytes != 64 + 16 * Policy.GuardCount || ProtectedCount > 128 ||
      (Policy.WindowBytes != SIZE_256MB && Policy.WindowBytes != SIZE_512MB && Policy.WindowBytes != 704ULL*SIZE_1MB) || Policy.Bytes != Policy.WindowBytes + SIZE_2MB ||
      (Policy.Base & (SIZE_2MB - 1)) || (Policy.VirtualBase & EFI_PAGE_MASK) ||
      Policy.Base > MAX_UINT64 - Policy.Bytes || ArmGetPhysicalAddressBits () >= 64 ||
      Policy.Base + Policy.Bytes > LShiftU64 (1, ArmGetPhysicalAddressBits ())) return FALSE;
  CopyMem (Guards, Protected, ProtectedCount * sizeof (*Guards));
  CopyMem (Guards + ProtectedCount, Policy.Guards, Policy.GuardCount * sizeof (*Guards));
  Guards[ProtectedCount + Policy.GuardCount] = Extension;
  Allocation.Range = (RAPHAEL_RANGE){Policy.Base, Policy.Bytes};
  Allocation.Alignment = SIZE_2MB;
  if (RaphaelCheckMemoryPlan (Policy.Base, Allocation.Range, &Allocation, 1, Ram, RamCount,
        Guards, ProtectedCount + Policy.GuardCount + 1, &Rejected) != RaphaelPlanOk) return FALSE;
  mWindow = (RAPHAEL_KERNEL_WINDOW){.Version=1, .Status=1, .Base=Policy.Base,
    .Bytes=Policy.Bytes, .VirtualBase=Policy.VirtualBase, .WindowBytes=Policy.WindowBytes,
    .Candidate=Policy.Base + (Policy.VirtualBase & (SIZE_2MB - 1))};
  DEBUG ((DEBUG_INFO, "KERNEL_WINDOW admitted base=%lx bytes=%lx candidate=%lx owned=%lx\n",
          mWindow.Base, mWindow.Bytes, mWindow.Candidate, mWindow.WindowBytes));
  return TRUE;
}
