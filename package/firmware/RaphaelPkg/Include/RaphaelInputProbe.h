// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_INPUT_PROBE_H
#define RAPHAEL_INPUT_PROBE_H
#include <Base.h>
#define RAPHAEL_INPUT_MAX_APIDS 512
#define RAPHAEL_INPUT_HEADER_WORDS 26
// Every field and array element is a big-endian UINT32 on the FDT wire.
enum { RaphaelInputDisabled, RaphaelInputNoHardware, RaphaelInputBadFdt,
       RaphaelInputUnsupported, RaphaelInputMapCollected, RaphaelInputTargetsMissing };
typedef struct {
  UINT32 Version, Status, HardwareVersion, Count, ReadCount, Ee, Channel;
  UINT32 CoreBase, CoreSize, CnfgBase, CnfgSize, ObserverBase, ObserverSize;
  UINT32 PonSid, PonAddress, VolumeSid, VolumeAddress, GpioNumber, GpioFlags, DebounceMs;
  UINT32 PonApid, VolumeApid, PonMatches, VolumeMatches, PonOwner, VolumeOwner;
  UINT32 Map[RAPHAEL_INPUT_MAX_APIDS], Owner[RAPHAEL_INPUT_MAX_APIDS];
} RAPHAEL_INPUT_SNAPSHOT;
STATIC_ASSERT(sizeof(RAPHAEL_INPUT_SNAPSHOT)==(RAPHAEL_INPUT_HEADER_WORDS+2*RAPHAEL_INPUT_MAX_APIDS)*4,"Input wire size");
typedef UINT32 (*RAPHAEL_INPUT_READ32)(UINT64 Address, VOID *Context);
// Only a read callback is exposed. No PMIC transaction is issued here.
VOID RaphaelCollectInputMap(CONST VOID *Fdt, RAPHAEL_INPUT_SNAPSHOT *Out,
                            RAPHAEL_INPUT_READ32 Read32, VOID *Context);
#endif
