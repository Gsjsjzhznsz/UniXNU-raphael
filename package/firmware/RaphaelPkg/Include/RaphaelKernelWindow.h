// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_KERNEL_WINDOW_H
#define RAPHAEL_KERNEL_WINDOW_H
#include <Uefi.h>
#include <Library/RaphaelMemoryContractLib.h>
#define RAPHAEL_KERNEL_WINDOW_POLICY_GUID \
  {0x7f1a45cb,0x8376,0x40cd,{0xaa,0x87,0x19,0x8e,0xb6,0x54,0xa1,0x52}}
#define RAPHAEL_KERNEL_WINDOW_MAGIC SIGNATURE_64('R','A','P','H','W','I','N','1')
#define RAPHAEL_KERNEL_WINDOW_MAX_GUARDS 128
typedef struct {
  UINT64 Magic, Version, TotalBytes, Base, Bytes, VirtualBase, WindowBytes, GuardCount;
  RAPHAEL_RANGE Guards[RAPHAEL_KERNEL_WINDOW_MAX_GUARDS];
} RAPHAEL_KERNEL_WINDOW_POLICY;
typedef struct {
  UINT64 Version, Status, Base, Bytes, VirtualBase, WindowBytes;
  UINT64 Candidate, ReservedMapOk, ReleasedMapOk, AllocatedMapOk, RestoredMapOk;
  UINT64 Error;
} RAPHAEL_KERNEL_WINDOW;
extern EFI_GUID gRaphaelKernelWindowHobGuid;
BOOLEAN RaphaelPrepareKernelWindow (CONST RAPHAEL_RANGE *Ram, UINTN RamCount,
  CONST RAPHAEL_RANGE *Protected, UINTN ProtectedCount, RAPHAEL_RANGE Extension);
RAPHAEL_KERNEL_WINDOW *RaphaelKernelWindow (VOID);
EFI_STATUS RaphaelTestKernelWindow (VOID);
EFI_STATUS RaphaelReleaseKernelWindow (VOID);
EFI_STATUS RaphaelRestoreKernelWindow (VOID);
#endif
