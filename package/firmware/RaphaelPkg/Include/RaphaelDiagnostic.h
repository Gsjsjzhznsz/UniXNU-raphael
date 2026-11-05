// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_DIAGNOSTIC_H
#define RAPHAEL_DIAGNOSTIC_H
#include <Uefi.h>
#include <Library/PcdLib.h>
#include <RaphaelDisplayProbe.h>
#include <RaphaelPixelProbe.h>
#include <RaphaelPixelWrite.h>
#include <RaphaelFramebuffer.h>
#include <RaphaelInputProbe.h>
#include <Library/RaphaelKeysLib.h>
#include <RaphaelInputDxe.h>
#include <RaphaelMenu.h>
#include <RaphaelPayload.h>
#include <RaphaelDarwin.h>
#include <RaphaelNativeLoad.h>
#include <RaphaelNativeEntry.h>
#include <RaphaelNativeMmu.h>
#include <RaphaelNativeWatchdog.h>
#include <RaphaelQemuArch.h>
#include <RaphaelGicProbe.h>
#include <RaphaelIccProbe.h>
#include <RaphaelTimerSource.h>

#define RAPHAEL_DIAG_MAGIC SIGNATURE_64 ('R','A','P','H','D','I','A','G')
#define RAPHAEL_DIAG_LOG_SIZE 16384
#define RAPHAEL_DIAG_MAP_SIZE 4096

// Assembly writes these first 30 UINT64s. Keep offsets in SecEntry.S in sync.
typedef struct {
  UINT64 X0, X1, X2, X3, Lr, Sp, El, Sctlr;
  UINT64 Daif, Cntfrq, Counter, Mpidr;
  UINT64 Vbar, Tpidr, Tcr, Ttbr0, Ttbr1, Mair, Cpacr;
  UINT64 ImageBase, ImageSize, OriginalEntry, OriginalInstruction;
  UINT64 FdtCopy, ExtentBase, ExtentEnd;
  UINT64 Finish, Stage, Status, Magic;
  UINT64 MmuSctlr, PageTable, PageTableBytes;
  UINT64 Esr, Elr, Far;
  UINT64 SystemTableSignature, BootServicesSignature;
  UINT64 SystemTableCrcOk, BootServicesCrcOk;
  UINT64 MapKey, MapBytes, DescriptorSize, DescriptorVersion;
  UINT64 MapViolations, AllocationProbeOk, LogUsed, LogDropped;
  UINT8 Map[RAPHAEL_DIAG_MAP_SIZE];
  CHAR8 Log[RAPHAEL_DIAG_LOG_SIZE];
  UINT64 Finishing;
  RAPHAEL_DISPLAY_SNAPSHOT Display;
  RAPHAEL_PIXEL_SNAPSHOT Pixels;
  RAPHAEL_PIXEL_WRITE_RESULT PixelWrite;
  RAPHAEL_GOP_RESULT Gop;
  RAPHAEL_INPUT_SNAPSHOT Input;
  RAPHAEL_KEY_RESULT Keys;
  RAPHAEL_INPUT_DXE_RESULT InputDxe;
  RAPHAEL_MENU_RESULT Menu;
  RAPHAEL_PAYLOAD_RESULT Payload;
  RAPHAEL_DARWIN_RESULT Darwin;
  UINT64 NativeLoadResult;
  UINT64 NativeEntryResult;
  UINT64 NativeMmuResult;
  RAPHAEL_QEMU_ARCH_RESULT QemuArch;
  RAPHAEL_GIC_SNAPSHOT Gic;
  RAPHAEL_ICC_SNAPSHOT Icc;
  RAPHAEL_TIMER_SOURCE_RESULT TimerSource;
} RAPHAEL_DIAGNOSTIC;
STATIC_ASSERT (sizeof (RAPHAEL_DIAGNOSTIC) <= 0xf000, "Diagnostic context overlaps final-page guided-section scratch");

typedef VOID (EFIAPI *RAPHAEL_FINISH)(UINT64 Status);

STATIC inline RAPHAEL_DIAGNOSTIC *RaphaelDiagnostic (VOID) {
  return (RAPHAEL_DIAGNOSTIC *)(UINTN)FixedPcdGet64 (PcdRaphaelContextBase);
}
#endif
