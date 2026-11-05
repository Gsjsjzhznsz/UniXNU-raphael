// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_PAYLOAD_H
#define RAPHAEL_PAYLOAD_H
#include <Uefi.h>
#include <Library/PcdLib.h>
#define RAPHAEL_PAYLOAD_GUID {0x8a9e0a07,0xb2fc,0x47f1,{0xa5,0x8b,0x10,0xaa,0xc5,0x65,0x02,0x94}}
#define RAPHAEL_DIAGNOSTIC_FAT_BYTES 1048576
// Explicit native profile budgets, not discovered hardware capacities.
#define RAPHAEL_NATIVE_FAT_BYTES FixedPcdGet32(PcdRaphaelNativeFatBytes)
#define RAPHAEL_NATIVE_PART_BYTES (RAPHAEL_NATIVE_FAT_BYTES / 2)
#define RAPHAEL_PAYLOAD_PART1_GUID {0x49c128b8,0x093b,0x4186,{0xae,0x24,0x36,0x6f,0x6c,0x4d,0x4d,0x6f}}
typedef struct {
 UINT64 Version,Status,Base,Bytes,Fdt,HobPresent,BlockIo,ReadOnly,WriteDenied,FileSystem,ConfigEntries,ConfigOk,RunStatus,RunCompleted,CrcBefore,CrcAfter;
} RAPHAEL_PAYLOAD_RESULT;
#endif
