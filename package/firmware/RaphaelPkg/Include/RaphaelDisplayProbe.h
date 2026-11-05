// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_DISPLAY_PROBE_H
#define RAPHAEL_DISPLAY_PROBE_H
#include <Base.h>
#define RAPHAEL_DISPLAY_MAX_SAMPLES 1024
// Wire form: big-endian UINT64 version/status/count, then address/value pairs.
enum {
  RaphaelDisplayDisabled = 0,
  RaphaelDisplayNoHardware = 1,
  RaphaelDisplayBadFdt = 2,
  RaphaelDisplayGccOff = 3,
  RaphaelDisplayPowerOff = 4,
  RaphaelDisplayAhbOff = 5,
  RaphaelDisplayMdpOff = 6,
  RaphaelDisplayCollected = 7,
  RaphaelDisplayUnsupportedRevision = 8,
  RaphaelSmmuBadFdt = 9,
  RaphaelSmmuPowerOff = 10,
  RaphaelSmmuUnsupported = 11,
  RaphaelSmmuAmbiguous = 12,
  RaphaelSmmuCollected = 13,
  RaphaelSmmuNoStream = 14
};
typedef struct {
  UINT64 Version, Status, Count;
  UINT64 Samples[RAPHAEL_DISPLAY_MAX_SAMPLES][2];
} RAPHAEL_DISPLAY_SNAPSHOT;
typedef UINT32 (*RAPHAEL_DISPLAY_READ32)(UINT64 Address, VOID *Context);
// The caller validates the entire FDT and runs with MMU/cache disabled.
// Read32 is the only hardware operation; there is deliberately no write API.
VOID RaphaelCollectDisplay (CONST VOID *Fdt, RAPHAEL_DISPLAY_SNAPSHOT *Out,
                            RAPHAEL_DISPLAY_READ32 Read32, VOID *Context);
// May append only after a successful display snapshot. Wire v4 retains the
// display prefix followed by bounded SMMU power, ID, stream and context reads.
VOID RaphaelCollectSmmu (CONST VOID *Fdt, RAPHAEL_DISPLAY_SNAPSHOT *Out,
                         RAPHAEL_DISPLAY_READ32 Read32, VOID *Context);
#endif
