// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_PIXEL_WRITE_H
#define RAPHAEL_PIXEL_WRITE_H
#include <RaphaelPixelProbe.h>
#define RAPHAEL_PATCH_WIDTH 256
#define RAPHAEL_PATCH_HEIGHT 128
#define RAPHAEL_PATCH_PIXELS (RAPHAEL_PATCH_WIDTH*RAPHAEL_PATCH_HEIGHT)
typedef VOID (*RAPHAEL_PIXEL_WRITE32)(UINT64 Address, UINT32 Value, VOID *Context);
typedef struct {
  UINT64 Version, Status, Base, Width, Height, Stride, Count;
  UINT64 Written, Verified, Restored, Mismatches, OriginalDigest, PatternDigest, RestoredDigest;
  UINT64 Start, End, HoldTicks, Backup, Active;
} RAPHAEL_PIXEL_WRITE_RESULT;
VOID RaphaelRestorePixelPatch (RAPHAEL_PIXEL_WRITE_RESULT *R,
  RAPHAEL_DISPLAY_READ32 Read, RAPHAEL_PIXEL_WRITE32 Write, VOID *Context);
VOID RaphaelTestPixelPatch (CONST RAPHAEL_PIXEL_SNAPSHOT *P, RAPHAEL_PIXEL_WRITE_RESULT *R,
  RAPHAEL_DISPLAY_READ32 Read, RAPHAEL_PIXEL_WRITE32 Write,
  RAPHAEL_PIXEL_COUNTER Counter, UINT64 StackBase, UINT64 StackSize, VOID *Context);
#endif
