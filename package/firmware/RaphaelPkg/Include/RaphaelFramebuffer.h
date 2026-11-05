// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_FRAMEBUFFER_H
#define RAPHAEL_FRAMEBUFFER_H
#include <RaphaelPixelProbe.h>
// UINT64, serialized big endian. Coordinates and budgets are diagnostic design
// choices; physical geometry is accepted only from this entry's gated snapshot.
typedef struct {
  UINT64 Version, Status, Base, Width, Height, Stride, Extent, MapBase, MapSize;
  UINT64 MappedReadVerified, ProtocolInstalled, QueryVerified, InvalidModeRejected;
  UINT64 BltChecks, PatchWritten, PatchVerified, PatchRestored, PatchMismatches;
  UINT64 Start, End, HoldTicks, Backup, Active, PatchWidth, PatchHeight, RestoreFallbackUsed;
} RAPHAEL_GOP_RESULT;
BOOLEAN RaphaelSplashRouteReady(CONST VOID *Fdt,CONST RAPHAEL_DISPLAY_SNAPSHOT *Display,
  CONST RAPHAEL_PIXEL_SNAPSHOT *Pixels);
BOOLEAN RaphaelFramebufferPlan (CONST RAPHAEL_PIXEL_SNAPSHOT *Pixels,
  UINT64 ProtectedBase, UINT64 ProtectedEnd, RAPHAEL_GOP_RESULT *Out);
typedef struct { UINT64 Base, Bytes; } RAPHAEL_FRAMEBUFFER_GUARD;
BOOLEAN RaphaelFramebufferPlanRanges(CONST RAPHAEL_PIXEL_SNAPSHOT *Pixels,
  CONST RAPHAEL_FRAMEBUFFER_GUARD *Guards, UINTN Count, RAPHAEL_GOP_RESULT *Out);
VOID RaphaelRestoreGopPatch (RAPHAEL_GOP_RESULT *Result, RAPHAEL_DISPLAY_READ32 Read,
  VOID (*Write)(UINT64, UINT32, VOID *), VOID *Context);
#endif
