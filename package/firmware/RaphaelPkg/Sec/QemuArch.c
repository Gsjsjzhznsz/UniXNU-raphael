// SPDX-License-Identifier: BSD-2-Clause-Patent
// Strictly emulator-only mapping gate. Values come from this QEMU-generated DTB.
#include <RaphaelDiagnostic.h>
#include <Library/ArmLib.h>
#include <Library/BaseLib.h>
extern INT32 fdt_node_check_compatible(CONST VOID *,INT32,CONST CHAR8 *);
#include <Library/BaseMemoryLib.h>
#include <Library/FdtLib.h>
#include <Library/PcdLib.h>

STATIC BOOLEAN Enabled(VOID *Fdt, INT32 Node) {
  INT32 Length; CONST CHAR8 *S=FdtGetProp(Fdt,Node,"status",&Length);
  return S==NULL || (Length==5 && CompareMem(S,"okay",5)==0) || (Length==3 && CompareMem(S,"ok",3)==0);
}
EFI_STATUS RaphaelPrepareQemuArch (VOID *Fdt, RAPHAEL_DIAGNOSTIC *D) {
  RAPHAEL_QEMU_ARCH_RESULT *R = &D->QemuArch;
  INT32 Node, Length;
  CONST UINT32 *Reg, *Ints;
  if (fdt_node_check_compatible (Fdt, 0, "linux,dummy-virt")) { return EFI_UNSUPPORTED; }
  if (FdtAddressCells (Fdt, 0) != 2 || FdtSizeCells (Fdt, 0) != 2) { return EFI_UNSUPPORTED; }
  Node = FdtNodeOffsetByCompatible (Fdt, -1, "arm,gic-v3");
  if (Node < 0 || FdtParentOffset (Fdt, Node) != 0 || FdtNodeOffsetByCompatible (Fdt, Node, "arm,gic-v3") >= 0) { return EFI_UNSUPPORTED; }
  if(!Enabled(Fdt,Node)||FdtGetProp(Fdt,Node,"interrupt-controller",&Length)==NULL||Length!=0)return EFI_UNSUPPORTED;
  const UINT32 *Cells=FdtGetProp(Fdt,Node,"#interrupt-cells",&Length);
  if(Cells==NULL||Length!=4||Fdt32ToCpu(*Cells)!=3)return EFI_COMPROMISED_DATA;
  UINT32 Handle=FdtGetPhandle(Fdt,Node);
  const UINT32 *Parent=FdtGetProp(Fdt,0,"interrupt-parent",&Length);
  if(Handle==0||Handle==MAX_UINT32||Parent==NULL||Length!=4||Fdt32ToCpu(*Parent)!=Handle)return EFI_UNSUPPORTED;
  if(FdtGetProp(Fdt,Node,"ranges",&Length)==NULL || Length!=0)return EFI_UNSUPPORTED;
  Cells=FdtGetProp(Fdt,Node,"#redistributor-regions",&Length);
  if(Cells==NULL||Length!=4||Fdt32ToCpu(*Cells)!=1)return EFI_UNSUPPORTED;
  Reg = FdtGetProp (Fdt, Node, "reg", &Length);
  if (Reg == NULL || Length != 32) { return EFI_COMPROMISED_DATA; }
  R->GicD = LShiftU64 (Fdt32ToCpu (Reg[0]), 32) | Fdt32ToCpu (Reg[1]);
  R->GicDBytes = LShiftU64 (Fdt32ToCpu (Reg[2]), 32) | Fdt32ToCpu (Reg[3]);
  R->GicR = LShiftU64 (Fdt32ToCpu (Reg[4]), 32) | Fdt32ToCpu (Reg[5]);
  R->GicRBytes = LShiftU64 (Fdt32ToCpu (Reg[6]), 32) | Fdt32ToCpu (Reg[7]);
  if (R->GicD != FixedPcdGet64 (PcdGicDistributorBase) || R->GicR != FixedPcdGet64 (PcdGicRedistributorsBase) ||
      R->GicDBytes != FixedPcdGet64 (PcdRaphaelQemuGicDBytes) || R->GicRBytes != FixedPcdGet64 (PcdRaphaelQemuGicRBytes)) { return EFI_COMPROMISED_DATA; }
  UINT64 Bases[2] = {R->GicD, R->GicR}, Sizes[2] = {R->GicDBytes, R->GicRBytes};
  for (UINTN I=0; I<2; ++I) {
    if (Bases[I]==0 || (Bases[I]&4095) || (Sizes[I]&4095) || Sizes[I] == 0 || Bases[I] > MAX_UINT64-Sizes[I] ||
        (Bases[I] < D->ExtentEnd && Bases[I]+Sizes[I] > D->ExtentBase)) { return EFI_COMPROMISED_DATA; }
  }
  if (Bases[0] < Bases[1]+Sizes[1] && Bases[1] < Bases[0]+Sizes[0]) { return EFI_COMPROMISED_DATA; }
  Node = FdtNodeOffsetByCompatible (Fdt, -1, "arm,armv8-timer");
  if (Node < 0) { return EFI_NOT_FOUND; }
  if(FdtParentOffset(Fdt,Node)!=0 || !Enabled(Fdt,Node) || FdtNodeOffsetByCompatible(Fdt,Node,"arm,armv8-timer")>=0 ||
     FdtGetProp(Fdt,Node,"interrupt-parent",&Length)!=NULL || FdtGetProp(Fdt,Node,"interrupts-extended",&Length)!=NULL)return EFI_UNSUPPORTED;
  Ints = FdtGetProp (Fdt, Node, "interrupts", &Length);
  if (Ints == NULL || Length != 48) { return EFI_COMPROMISED_DATA; }
  UINT64 *Ids[4] = {&R->SecureInt,&R->PhysicalInt,&R->VirtualInt,&R->HypInt};
  UINT32 Expected[4] = {FixedPcdGet32(PcdArmArchTimerSecIntrNum),FixedPcdGet32(PcdArmArchTimerIntrNum),
    FixedPcdGet32(PcdArmArchTimerVirtIntrNum),FixedPcdGet32(PcdArmArchTimerHypIntrNum)};
  for (UINTN I=0; I<4; ++I) {
    if (Fdt32ToCpu(Ints[I*3]) != 1 || Fdt32ToCpu(Ints[I*3+1]) >= 16 || Fdt32ToCpu(Ints[I*3+2]) != 4) { return EFI_UNSUPPORTED; }
    *Ids[I] = Fdt32ToCpu(Ints[I*3+1])+16;
    if (*Ids[I] != Expected[I]) { return EFI_COMPROMISED_DATA; }
    for(UINTN J=0; J<I; ++J)if(*Ids[I]==*Ids[J])return EFI_COMPROMISED_DATA;
  }
  R->Frequency = D->Cntfrq; if (R->Frequency == 0) { return EFI_COMPROMISED_DATA; }
  R->SavedCtl = ArmReadCntpCtl (); R->SavedCval = ArmReadCntpCval ();
  R->Version = 1; R->Status = 1;
  return EFI_SUCCESS;
}
