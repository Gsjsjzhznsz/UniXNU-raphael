// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_HANDOFF_STATE_H
#define RAPHAEL_HANDOFF_STATE_H
#include <Base.h>
// Synthetic QEMU design constants, never handset or XNU hardware parameters.
#define HANDOFF_MAGIC 0x48414e444f464631ULL
#define HANDOFF_VIRTUAL_BASE 0xffff000000200000ULL
#define HANDOFF_WINDOW_BYTES 0x10000000ULL
#define HANDOFF_SEGMENT_BYTES 0x20000ULL
#define HANDOFF_TEXT_MARKER 0x7261706868616e64ULL
// AAVMF owns this allocation. Exit notice cleans it before MMU shutdown.
typedef struct {
  UINT64 Magic, Version, Bytes, ExitCount, TreeBytes, TreeCrc, RamdiskBytes, RamdiskCrc;
} HANDOFF_STATE;
#endif
