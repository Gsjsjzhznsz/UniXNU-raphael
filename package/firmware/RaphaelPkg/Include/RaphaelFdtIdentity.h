// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_FDT_IDENTITY_H
#define RAPHAEL_FDT_IDENTITY_H

// Validate a resource on the observed /soc bus against its root-bus ranges.
// Empty ranges and an explicit containing identity tuple are both valid DT.
// The parent must be the root; no untranslated ancestor may be ignored.
STATIC BOOLEAN RaphaelFdtRootIdentityRange(
  CONST VOID *Fdt, INT32 Bus, UINT64 Address, UINT64 Bytes
) {
  INT32 Length = 0;
  if (Bus < 0 || FdtParentOffset(Fdt, Bus) != 0 ||
      FdtAddressCells(Fdt, Bus) != 1 || FdtSizeCells(Fdt, Bus) != 1 ||
      FdtAddressCells(Fdt, 0) != 2 || !Bytes || Address > MAX_UINT64 - Bytes)
    return FALSE;
  CONST UINT32 *Ranges = (CONST UINT32 *)FdtGetProp(Fdt, Bus, "ranges", &Length);
  if (Ranges == NULL || Length < 0 || (Length % 16) != 0) return FALSE;
  if (Length == 0) return TRUE;
  UINTN Matches = 0;
  for (INT32 I = 0; I < Length / 4; I += 4) {
    UINT64 Child = SwapBytes32(ReadUnaligned32(Ranges + I));
    UINT64 Parent = ((UINT64)SwapBytes32(ReadUnaligned32(Ranges + I + 1)) << 32) |
      SwapBytes32(ReadUnaligned32(Ranges + I + 2));
    UINT64 Span = SwapBytes32(ReadUnaligned32(Ranges + I + 3));
    if (Address < Child || Address - Child > Span || Bytes > Span - (Address - Child))
      continue;
    if (Parent > MAX_UINT64 - (Address - Child) || Parent + (Address - Child) != Address)
      return FALSE;
    ++Matches;
  }
  return Matches == 1;
}
#endif
