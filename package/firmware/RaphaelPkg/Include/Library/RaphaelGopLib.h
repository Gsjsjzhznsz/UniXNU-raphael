// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_GOP_LIB_H
#define RAPHAEL_GOP_LIB_H
#include <Uefi.h>
#include <RaphaelFramebuffer.h>
#include <Library/FrameBufferBltLib.h>
#define RAPHAEL_GOP_SIGNATURE SIGNATURE_32('R','G','O','P')
typedef struct {
  UINT32 Signature;
  EFI_GRAPHICS_OUTPUT_PROTOCOL Protocol;
  EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE Mode;
  EFI_GRAPHICS_OUTPUT_MODE_INFORMATION Info;
  FRAME_BUFFER_CONFIGURE *Configure;
} RAPHAEL_GOP;
RETURN_STATUS RaphaelGopConfigure (RAPHAEL_GOP *Gop, CONST RAPHAEL_GOP_RESULT *Plan,
  VOID *Configure, UINTN *ConfigureSize);
#endif
