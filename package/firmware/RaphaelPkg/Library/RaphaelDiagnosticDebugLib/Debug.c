// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelDiagnostic.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/PrintLib.h>
#include <Library/SemihostLib.h>

STATIC VOID Append (CONST CHAR8 *Text) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic ();
  if (D->Magic != RAPHAEL_DIAG_MAGIC) return;
  if(FixedPcdGetBool(PcdRaphaelNativeQemuGate))SemihostWriteString((CHAR8 *)Text);
  while (*Text) {
    if (D->LogUsed < sizeof (D->Log)) D->Log[D->LogUsed++] = *Text;
    else ++D->LogDropped;
    ++Text;
  }
}
VOID EFIAPI DebugVPrint (UINTN Level, CONST CHAR8 *Format, VA_LIST Args) {
  CHAR8 Buffer[512];
  // Include INFO/LOAD/ERROR; omit verbose dispatcher and allocation traffic.
  if (!(Level & (DEBUG_ERROR | DEBUG_WARN | DEBUG_INFO | DEBUG_LOAD))) return;
  AsciiVSPrint (Buffer, sizeof (Buffer), Format, Args);
  Append (Buffer);
}
VOID EFIAPI DebugBPrint (UINTN Level, CONST CHAR8 *Format, BASE_LIST Args) {
  CHAR8 Buffer[512];
  if (!(Level & (DEBUG_ERROR | DEBUG_WARN | DEBUG_INFO | DEBUG_LOAD))) return;
  AsciiBSPrint (Buffer, sizeof (Buffer), Format, Args);
  Append (Buffer);
}
VOID EFIAPI DebugPrint (UINTN Level, CONST CHAR8 *Format, ...) {
  VA_LIST Args;
  VA_START (Args, Format);
  DebugVPrint (Level, Format, Args);
  VA_END (Args);
}
VOID EFIAPI DebugAssert (CONST CHAR8 *File, UINTN Line, CONST CHAR8 *Description) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic ();
  DebugPrint (DEBUG_ERROR, "ASSERT %a:%u %a\n", File, Line, Description);
  if (D->Magic == RAPHAEL_DIAG_MAGIC && D->Finish)
    ((RAPHAEL_FINISH)(UINTN)D->Finish)(0xa55e);
  CpuDeadLoop ();
}
VOID *EFIAPI DebugClearMemory (VOID *Buffer, UINTN Length) { return SetMem (Buffer, Length, 0xaf); }
BOOLEAN EFIAPI DebugAssertEnabled (VOID) { return TRUE; }
BOOLEAN EFIAPI DebugPrintEnabled (VOID) { return TRUE; }
BOOLEAN EFIAPI DebugCodeEnabled (VOID) { return (FixedPcdGet8(PcdDebugPropertyMask) & DEBUG_PROPERTY_DEBUG_CODE_ENABLED) != 0; }
BOOLEAN EFIAPI DebugClearMemoryEnabled (VOID) { return FALSE; }
BOOLEAN EFIAPI DebugPrintLevelEnabled (UINTN Level) {
  return (Level & (DEBUG_ERROR | DEBUG_WARN | DEBUG_INFO | DEBUG_LOAD)) != 0;
}
