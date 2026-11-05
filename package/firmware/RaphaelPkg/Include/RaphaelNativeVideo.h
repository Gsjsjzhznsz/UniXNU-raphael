// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_VIDEO_H
#define RAPHAEL_NATIVE_VIDEO_H
#include <Uefi.h>
#include <RaphaelFramebuffer.h>
#include <Protocol/GraphicsOutput.h>
// Inherited mode only. No address, geometry, or timing defaults.
EFI_STATUS RaphaelNativeVideoBegin(RAPHAEL_GOP_RESULT *State,
  EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop, UINT64 Video[6]);
BOOLEAN RaphaelNativeVideoMatches(CONST VOID *Args, CONST UINT64 Video[6]);
#endif
