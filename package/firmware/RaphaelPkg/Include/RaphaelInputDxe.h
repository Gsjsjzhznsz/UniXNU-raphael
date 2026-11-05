// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_INPUT_DXE_H
#define RAPHAEL_INPUT_DXE_H
#include <Uefi.h>
typedef struct {
  UINT64 Version,Status,MapBase0,MapBase1,MapCount,MappedReadVerified,ProtocolInstalled;
  UINT64 Polls,Errors,Events,ReadCalls,ResetCalls,PressedMask,ReleasedMask,LastRaw,LastScan;
} RAPHAEL_INPUT_DXE_RESULT;
#endif
