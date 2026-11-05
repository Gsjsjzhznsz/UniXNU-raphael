// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_MANAGER_UI_LIB_H
#define RAPHAEL_MANAGER_UI_LIB_H
#include <Uefi.h>
#include <RaphaelFramebuffer.h>
#include <Protocol/GraphicsOutput.h>
// Wire prefix only; raw framebuffer contents never leave private RAM.
// Status: 1 validated resources, 2 backed up, 3 changed, 4 fully restored.
typedef struct {
 UINT64 Version,Status,Base,Width,Height,Stride,FramePixels,PixelsChanged,PixelsRestored,Mismatches;
 UINT64 InputReady,QueryVerified,Active,Backup,Fallback,PixelFormat;
} RAPHAEL_MANAGER_UI_RESULT;
typedef struct {
 RAPHAEL_MANAGER_UI_RESULT Result;
 RAPHAEL_GOP_RESULT Restore;
 UINT32 *Line;
 EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop;
} RAPHAEL_MANAGER_UI_STATE;
extern EFI_GUID gRaphaelManagerUiHobGuid;
EFI_STATUS RaphaelManagerUiBegin(RAPHAEL_MANAGER_UI_STATE *State,CONST RAPHAEL_GOP_RESULT *Expected,
                                BOOLEAN InputReady,EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop);
// Always tries restoration, including after a failed or unchanged manager run.
// Keeps original backing memory alive if restoration/readback fails.
EFI_STATUS RaphaelManagerUiFinish(RAPHAEL_MANAGER_UI_STATE *State);
#endif
