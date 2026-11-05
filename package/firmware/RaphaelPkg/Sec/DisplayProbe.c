// SPDX-License-Identifier: BSD-2-Clause-Patent
// Register semantics: fixed MiCode raphael-p-oss; see DISPLAY-PROBE.zh-CN.md.
// Physical bases and pipe offsets come only from the validated current FDT.
#include <RaphaelDisplayProbe.h>
#include <Library/FdtLib.h>
extern INT32 fdt_node_check_compatible (CONST VOID *, INT32, CONST CHAR8 *);

STATIC UINT32 Be32 (CONST VOID *Ptr) {
  CONST UINT8 *P = Ptr;
  return ((UINT32)P[0] << 24) | ((UINT32)P[1] << 16) | ((UINT32)P[2] << 8) | P[3];
}
STATIC BOOLEAN FirstString (CONST VOID *Fdt, INT32 Node, CONST CHAR8 *Key, CONST CHAR8 *Text) {
  INT32 Len;
  CONST CHAR8 *P = FdtGetProp (Fdt, Node, Key, &Len);
  if (!P) return FALSE;
  for (INT32 I = 0; I < Len; ++I) {
    if (P[I] != Text[I]) return FALSE;
    if (Text[I] == 0) return TRUE;
  }
  return FALSE;
}
STATIC BOOLEAN U32Prop (CONST VOID *Fdt, INT32 Node, CONST CHAR8 *Key, UINT32 *Value) {
  INT32 Len;
  CONST VOID *P = FdtGetProp (Fdt, Node, Key, &Len);
  if (!P || Len != 4) return FALSE;
  *Value = Be32 (P);
  return TRUE;
}
STATIC BOOLEAN DirectReg (CONST VOID *Fdt, INT32 Node, INT32 Soc, UINT64 Limit, UINT64 *Base, UINT32 *Size) {
  INT32 Len;
  CONST UINT8 *P;
  if (Node < 0 || FdtParentOffset (Fdt, Node) != Soc) return FALSE;
  P = FdtGetProp (Fdt, Node, "status", &Len);
  if (P && !FirstString (Fdt, Node, "status", "ok") &&
           !FirstString (Fdt, Node, "status", "okay")) return FALSE;
  P = FdtGetProp (Fdt, Node, "reg", &Len);
  if (!P || Len < 8 || Len % 8) return FALSE;
  *Base = Be32 (P); *Size = Be32 (P + 4);
  return *Base != 0 && (*Base & 3) == 0 && *Size >= 4 && *Base + *Size <= Limit;
}
STATIC UINT32 Sample (RAPHAEL_DISPLAY_SNAPSHOT *Out, RAPHAEL_DISPLAY_READ32 Read32,
                     VOID *Context, UINT64 Address) {
  // Geometry and worst-case count are checked before the first hardware read.
  UINT32 Value = Read32 (Address, Context);
  Out->Samples[Out->Count][0] = Address;
  Out->Samples[Out->Count++][1] = Value;
  return Value;
}
STATIC BOOLEAN ClockRunning (UINT32 Value) {
  // Conservative: both software enable and no CLK_OFF are required.
  return (Value & 0x80000001U) == 1;
}
// Each list is an independent FDT-declared register window. Validate every
// window and pairwise overlap before any read; no route-derived arbitrary MMIO.
typedef struct {
  CONST UINT32 *Offsets;
  UINT32 Count, Size;
} DISPLAY_BLOCKS;
STATIC BOOLEAN Blocks (CONST VOID *Fdt, INT32 Mdp, CONST CHAR8 *Key,
                       CONST CHAR8 *SizeKey, UINT32 Max, UINT32 Minimum,
                       UINT32 MdpSize, DISPLAY_BLOCKS *Out) {
  INT32 Len;
  Out->Offsets = FdtGetProp (Fdt, Mdp, Key, &Len);
  if (!Out->Offsets || Len <= 0 || Len % 4 || (UINT32)Len / 4 > Max ||
      !U32Prop (Fdt, Mdp, SizeKey, &Out->Size) || Out->Size < Minimum) return FALSE;
  Out->Count = (UINT32)Len / 4;
  for (UINT32 I = 0; I < Out->Count; ++I) {
    UINT32 At = Be32 (Out->Offsets + I);
    if (At < 4 || (At & 3) || At > MdpSize || Out->Size > MdpSize - At) return FALSE;
  }
  return TRUE;
}
STATIC BOOLEAN Separate (DISPLAY_BLOCKS *All, UINTN Count) {
  for (UINTN A = 0; A < Count; ++A)
    for (UINT32 I = 0; I < All[A].Count; ++I)
      for (UINTN B = 0; B <= A; ++B)
        for (UINT32 J = 0; J < (B == A ? I : All[B].Count); ++J) {
          UINT64 X = Be32 (All[A].Offsets + I), Y = Be32 (All[B].Offsets + J);
          if (X < Y + All[B].Size && Y < X + All[A].Size) return FALSE;
        }
  return TRUE;
}
VOID RaphaelCollectDisplay (CONST VOID *Fdt, RAPHAEL_DISPLAY_SNAPSHOT *Out,
                            RAPHAEL_DISPLAY_READ32 Read32, VOID *Context) {
  INT32 Soc, Mdp, Gcc, Cc, Gdsc, Len;
  UINT64 MdpBase, GccBase, CcBase, GdscBase, Limit;
  CONST UINT8 *Ranges;
  UINT32 MdpSize, GccSize, CcSize, GdscSize, Handle, BlendCount;
  CONST UINT32 *Blend;
  DISPLAY_BLOCKS B[5]; // SSPP, CTL, LM, INTF, PP; every base comes from FDT.
  STATIC CONST UINT32 IntfOffsets[] = {
    0x00, 0x04, 0x60, 0x84, 0x90, 0xac, 0x25c, 0x284, 0x288, 0x2b4
  };
  // SM8150 (major 5) uses interface TE, not the legacy PP TE registers.
  STATIC CONST UINT32 PpOffsets[] = {0xa0, 0xac, 0xc8};
  // Only non-destructive configuration registers. No interrupt/status clear,
  // command FIFO, SMMU table, framebuffer or peripheral reset is accessed.
  STATIC CONST UINT32 Offsets[] = {
    0x00, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c, 0x20,
    0x24, 0x28, 0x30, 0x34, 0x38, 0x70, 0x170, 0x174, 0x178, 0x17c
  };
  for (UINTN I = 0; I < sizeof (*Out); ++I) ((UINT8 *)Out)[I] = 0;
  Out->Version = 3;
  Out->Status = RaphaelDisplayNoHardware;
  Mdp = FdtNodeOffsetByCompatible (Fdt, -1, "qcom,sde-kms");
  Gcc = FdtNodeOffsetByCompatible (Fdt, -1, "qcom,gcc-sm8150-v2");
  Cc = FdtNodeOffsetByCompatible (Fdt, -1, "qcom,dispcc-sm8150-v2");
  if (Mdp < 0 || Gcc < 0 || Cc < 0) return;
  Out->Status = RaphaelDisplayBadFdt;
  // Never interpret an untranslated bus address as a physical MMIO address.
  Soc = FdtPathOffset (Fdt, "/soc");
  if (Soc < 0 || FdtAddressCells (Fdt, 0) != 2) return;
  Ranges = FdtGetProp (Fdt, Soc, "ranges", &Len);
  if (!Ranges) return;
  // Support only an explicit identity window or an empty identity mapping.
  // The handset describes child=0,parent=0,length=0xffffffff, not empty ranges.
  if (Len == 0) Limit = 0x100000000ULL;
  else if (Len == 16 && Be32 (Ranges) == 0 && Be32 (Ranges + 4) == 0 &&
           Be32 (Ranges + 8) == 0 && Be32 (Ranges + 12) != 0)
    Limit = Be32 (Ranges + 12);
  else return;
  if (FdtParentOffset (Fdt, Soc) != 0 ||
      FdtAddressCells (Fdt, Soc) != 1 || FdtSizeCells (Fdt, Soc) != 1 ||
      !FirstString (Fdt, Mdp, "reg-names", "mdp_phys") ||
      !FirstString (Fdt, Gcc, "reg-names", "cc_base") ||
      !FirstString (Fdt, Cc, "reg-names", "cc_base") ||
      !DirectReg (Fdt, Mdp, Soc, Limit, &MdpBase, &MdpSize) ||
      !DirectReg (Fdt, Gcc, Soc, Limit, &GccBase, &GccSize) ||
      !DirectReg (Fdt, Cc, Soc, Limit, &CcBase, &CcSize) ||
      !U32Prop (Fdt, Mdp, "sde-vdd-supply", &Handle)) return;
  Gdsc = FdtNodeOffsetByPhandle (Fdt, Handle);
  if (Gdsc < 0 || fdt_node_check_compatible (Fdt, Gdsc, "qcom,gdsc") ||
      !FirstString (Fdt, Gdsc, "regulator-name", "mdss_core_gdsc") ||
      !DirectReg (Fdt, Gdsc, Soc, Limit, &GdscBase, &GdscSize) ||
      GccSize < 0xb010 || CcSize < 0x2084) return;
  // The supplied GDSCR must be inside the same display clock region.
  if (GdscSize != 4 || GdscBase < CcBase || GdscBase + 4 > CcBase + CcSize) return;
  if (!Blocks (Fdt, Mdp, "qcom,sde-sspp-off", "qcom,sde-sspp-src-size", 8, 0x180, MdpSize, &B[0]) ||
      !Blocks (Fdt, Mdp, "qcom,sde-ctl-off", "qcom,sde-ctl-size", 6, 0xf8, MdpSize, &B[1]) ||
      !Blocks (Fdt, Mdp, "qcom,sde-mixer-off", "qcom,sde-mixer-size", 6, 8, MdpSize, &B[2]) ||
      !Blocks (Fdt, Mdp, "qcom,sde-intf-off", "qcom,sde-intf-size", 4, 0x2b8, MdpSize, &B[3]) ||
      !Blocks (Fdt, Mdp, "qcom,sde-pp-off", "qcom,sde-pp-size", 6, 0xcc, MdpSize, &B[4]) ||
      !Separate (B, ARRAY_SIZE (B))) return;
  Blend = FdtGetProp (Fdt, Mdp, "qcom,sde-mixer-blend-op-off", &Len);
  if (!Blend || Len <= 0 || Len % 4 || Len > 11 * 4 ||
      !U32Prop (Fdt, Mdp, "qcom,sde-mixer-blendstages", &BlendCount) ||
      BlendCount != (UINT32)Len / 4) return;
  for (UINT32 I = 0; I < BlendCount; ++I) {
    UINT32 At = Be32 (Blend + I);
    if (At < 8 || (At & 3) || At > B[2].Size || B[2].Size - At < 8) return;
    for (UINT32 J = 0; J < I; ++J) {
      UINT64 Other = Be32 (Blend + J);
      if (At < Other + 8 && Other < (UINT64)At + 8) return;
    }
  }
  // The last LM layer extension must also fit inside every CTL window.
  if (0xa0 + B[2].Count * 4 > B[1].Size ||
      5 + B[0].Count * ARRAY_SIZE (Offsets) + B[1].Count * (2 + 4 * B[2].Count) +
      B[2].Count * (2 + 2 * BlendCount) + B[3].Count * ARRAY_SIZE (IntfOffsets) +
      B[4].Count * ARRAY_SIZE (PpOffsets) > RAPHAEL_DISPLAY_MAX_SAMPLES) return;
  Out->Status = RaphaelDisplayGccOff;
  UINT32 GccValue = Sample (Out, Read32, Context, GccBase + 0xb00c);
  // gcc_disp_ahb_clk has hwcg_bit=1. The primary driver's branch wait skips
  // CLK_OFF in HWCG mode, where an idle clock can be stopped automatically.
  // Require software enable; accept the known HWCG mode only on this gate.
  if (!(GccValue & 1) || ((GccValue & 0x80000000U) && !(GccValue & 2))) return;
  Out->Status = RaphaelDisplayPowerOff;
  if (!(Sample (Out, Read32, Context, GdscBase) & 0x80000000U)) return;
  Out->Status = RaphaelDisplayAhbOff;
  if (!ClockRunning (Sample (Out, Read32, Context, CcBase + 0x2080))) return;
  Out->Status = RaphaelDisplayMdpOff;
  if (!ClockRunning (Sample (Out, Read32, Context, CcBase + 0x200c))) return;
  UINT32 Revision = Sample (Out, Read32, Context, MdpBase);
  if ((Revision >> 28) != 5) {
    Out->Status = RaphaelDisplayUnsupportedRevision;
    return;
  }
  for (UINT32 I = 0; I < B[0].Count; ++I)
    for (UINTN J = 0; J < ARRAY_SIZE (Offsets); ++J)
      Sample (Out, Read32, Context, MdpBase + Be32 (B[0].Offsets + I) + Offsets[J]);
  for (UINT32 I = 0; I < B[1].Count; ++I) {
    UINT64 At = MdpBase + Be32 (B[1].Offsets + I);
    Sample (Out, Read32, Context, At + 0x14); // CTL_TOP
    Sample (Out, Read32, Context, At + 0xf4); // CTL_INTF_ACTIVE
    for (UINT32 J = 0; J < B[2].Count; ++J) {
      Sample (Out, Read32, Context, At + (J == 5 ? 0x24 : J * 4));
      Sample (Out, Read32, Context, At + 0x40 + J * 4);
      Sample (Out, Read32, Context, At + 0x70 + J * 4);
      Sample (Out, Read32, Context, At + 0xa0 + J * 4);
    }
  }
  for (UINT32 I = 0; I < B[2].Count; ++I) {
    UINT64 At = MdpBase + Be32 (B[2].Offsets + I);
    Sample (Out, Read32, Context, At); // LM_OP_MODE
    Sample (Out, Read32, Context, At + 4); // LM_OUT_SIZE
    for (UINT32 J = 0; J < BlendCount; ++J) {
      Sample (Out, Read32, Context, At + Be32 (Blend + J)); // blend op
      Sample (Out, Read32, Context, At + Be32 (Blend + J) + 4); // combined alpha
    }
  }
  for (UINT32 I = 0; I < B[3].Count; ++I)
    for (UINTN J = 0; J < ARRAY_SIZE (IntfOffsets); ++J)
      Sample (Out, Read32, Context, MdpBase + Be32 (B[3].Offsets + I) + IntfOffsets[J]);
  for (UINT32 I = 0; I < B[4].Count; ++I)
    for (UINTN J = 0; J < ARRAY_SIZE (PpOffsets); ++J)
      Sample (Out, Read32, Context, MdpBase + Be32 (B[4].Offsets + I) + PpOffsets[J]);
  Out->Status = RaphaelDisplayCollected;
}
