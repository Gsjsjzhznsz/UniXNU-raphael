// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_PIXEL_PROBE_H
#define RAPHAEL_PIXEL_PROBE_H
#include <RaphaelDisplayProbe.h>
#define RAPHAEL_PIXEL_GRID 64
#define RAPHAEL_PIXEL_ROUNDS 32
// Big-endian UINT32 wire record. Pixels stay private; public evidence is hashed.
typedef struct {
  UINT32 Version, Status, Width, Height, Stride, BaseLow, BaseHigh, Extent;
  UINT32 InterfaceBase, CounterFrequency, Grid, PixelCount, RefreshCount;
  UINT32 Pixels[RAPHAEL_PIXEL_GRID * RAPHAEL_PIXEL_GRID];
  // counter low/high, INTF_STATUS, FRAME_COUNT, TE_INT_COUNT, TE_LINE_COUNT
  UINT32 Refresh[RAPHAEL_PIXEL_ROUNDS][6];
} RAPHAEL_PIXEL_SNAPSHOT;
typedef UINT64 (*RAPHAEL_PIXEL_COUNTER)(VOID *Context);
VOID RaphaelCollectPixels (CONST VOID *Fdt, CONST RAPHAEL_DISPLAY_SNAPSHOT *Display,
  RAPHAEL_PIXEL_SNAPSHOT *Out, RAPHAEL_DISPLAY_READ32 Read32,
  RAPHAEL_PIXEL_COUNTER Counter, UINT32 Frequency, VOID *Context);
#endif
