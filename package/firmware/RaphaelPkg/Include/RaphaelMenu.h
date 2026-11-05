// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_MENU_H
#define RAPHAEL_MENU_H
#include <RaphaelFramebuffer.h>
typedef struct {
  UINT64 Version,Status,Start,End,HoldTicks,Selected,Up,Down,Enter,WaitSignals,PixelsChanged,ExitReason;
  RAPHAEL_GOP_RESULT Restore;
} RAPHAEL_MENU_RESULT;
#endif
