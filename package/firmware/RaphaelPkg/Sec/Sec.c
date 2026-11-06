// SPDX-License-Identifier: BSD-2-Clause-Patent
// Independent experimental SEC; native OS boot is an explicit opt-in profile.
#include <PiPei.h>
#include <RaphaelUfsHandoff.h>
#include <RaphaelUfsRead.h>
STATIC RAPHAEL_UFS_READ mUfsRead __attribute__((section(".data")))={{0},{0},{0}};
STATIC RAPHAEL_UFS_HANDOFF mUfsHandoff;
#include <RaphaelDiagnostic.h>
#include <RaphaelPpiProbe.h>
#include <RaphaelGicEnableMap.h>
#include <RaphaelTimerRoute.h>
#include <RaphaelTimerIrq.h>
#include <RaphaelPhysicalTimer.h>
#include <RaphaelRamRead.h>
#include <RaphaelKernelWindow.h>
#include "AndroidReturn.h"
#include <Guid/MemoryTypeInformation.h>
#include <RaphaelRamMapped.h>
STATIC_ASSERT(sizeof(RAPHAEL_RAM_MAPPED_RESULT)==27*8,"mapped RAM wire ABI");
STATIC RAPHAEL_RAM_MAPPED_RESULT mRamMapped __attribute__((section(".data")))={0};
#include <Library/RaphaelRamWriteLib.h>
#include <Library/RaphaelRamCacheLib.h>
STATIC_ASSERT(sizeof(RAPHAEL_RAM_CACHE_RESULT)==16*8,"cache RAM metadata ABI");
STATIC RAPHAEL_RAM_CACHE_STATE mRamCache __attribute__((section(".data")))={0};
STATIC RAPHAEL_RAM_WRITE_STATE mRamWrite __attribute__((section(".data"))) = {0};
STATIC UINT64 mRamBackup[RAPHAEL_RAM_PAGE_WORDS] __attribute__((section(".data"))) = {0};
#include <Library/RaphaelManagerUiLib.h>
STATIC_ASSERT(sizeof(RAPHAEL_RAM_WRITE_RESULT)==23*8,"RAM write wire ABI");
STATIC_ASSERT(sizeof(RAPHAEL_RAM_WRITE_STATE)==232,"RAM recovery storage ABI");
STATIC RAPHAEL_MANAGER_UI_STATE mManagerUi;
STATIC RAPHAEL_RAM_READ_RESULT mRamRead;
extern BOOLEAN RaphaelRunRamRead(CONST VOID *,RAPHAEL_DIAGNOSTIC *,RAPHAEL_RAM_READ_RESULT *,RAPHAEL_RAM_WRITE_STATE *,UINT64 *);
STATIC RAPHAEL_PHYSICAL_TIMER_STATE mPhysicalTimer;
// Linker-placed SEC data inside the existing FD budget; context/scratch unchanged.
STATIC RAPHAEL_PPI_RESULT mPpiProbe;
STATIC RAPHAEL_GIC_ENABLE_MAP mGicEnableMap;
STATIC RAPHAEL_TIMER_ROUTE_RESULT mTimerRoute;
STATIC RAPHAEL_TIMER_IRQ_RESULT mTimerIrq;
#include <Library/ArmLib.h>
#include <Library/ArmMmuLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/DebugLib.h>
#include <Library/FdtLib.h>
#include <Library/HobLib.h>
#include <Library/PrePiLib.h>
#include <Library/RaphaelMemoryContractLib.h>
#include <RaphaelFdtIdentity.h>

// These libfdt reserve/full-check entry points have no FdtLib wrapper in the
// pinned Basecore. They are linked from its unmodified BaseFdtLib instance.
extern INT32 fdt_check_full (CONST VOID *, UINTN);
extern INT32 fdt_add_mem_rsv (VOID *, UINT64, UINT64);
extern INT32 fdt_num_mem_rsv (CONST VOID *);
extern INT32 fdt_get_mem_rsv (CONST VOID *, INT32, UINT64 *, UINT64 *);
extern VOID EFIAPI RaphaelResume (RAPHAEL_DIAGNOSTIC *);
extern VOID EFIAPI ProcessLibraryConstructorList (VOID);

STATIC_ASSERT (OFFSET_OF (RAPHAEL_DIAGNOSTIC, Magic) == 232, "assembly ABI");
STATIC_ASSERT (OFFSET_OF (RAPHAEL_DIAGNOSTIC, Far) == 280, "exception ABI");
// Context and guided-section scratch separation is asserted in RaphaelDiagnostic.h.

VOID EFIAPI SecFinish(UINT64 Status);
STATIC UINT32 ReadDisplay32(UINT64 Address,VOID *Context);
STATIC UINT64 mUfsUncachedWords[5] __attribute__((section(".data")))={0};
STATIC UINT64 mUfsUncachedRanges[3][2] __attribute__((section(".data")))={{0}};
extern VOID EFIAPI RaphaelCallUfsUncached(CONST VOID *,VOID (EFIAPI *)(VOID));
STATIC VOID EFIAPI ExecuteUfsUncached(VOID){
  RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();CONST VOID *Fdt=(VOID *)(UINTN)D->FdtCopy;
  mUfsUncachedWords[2]=ArmReadSctlr();mUfsUncachedWords[4]++;
  if(mUfsUncachedWords[2]&0x1005)SecFinish(0x240);
  RaphaelCollectUfsHandoff(Fdt,D->ImageBase,D->ExtentEnd,&mUfsHandoff,ReadDisplay32,NULL);
  DEBUG((DEBUG_INFO,"UFS handoff status=%lu base=%lx bytes=%lx reads=%lu\n",mUfsHandoff.Status,mUfsHandoff.Base,mUfsHandoff.Bytes,mUfsHandoff.ReadCount));
  if(mUfsHandoff.Status!=1&&mUfsHandoff.Status!=3)SecFinish(0x23c);
  RaphaelUfsReadOnly(Fdt,&mUfsHandoff,FixedPcdGet64(PcdRaphaelNativeWatchdogBase),FixedPcdGet32(PcdRaphaelNativeWatchdogHz),D->Cntfrq,FixedPcdGet64(PcdRaphaelUfsReadLba),FixedPcdGetBool(PcdRaphaelUfsQueryOnly),FixedPcdGetBool(PcdRaphaelUfsResetOnError),FixedPcdGetBool(PcdRaphaelUfsPayload)?D->Payload.Base:0,FixedPcdGetBool(PcdRaphaelUfsPayload)?D->Payload.Bytes:0,&mUfsRead);

}

STATIC UINT64 CellValue (CONST UINT32 *Cells, INT32 Count) {
  UINT64 Value = SwapBytes32 (ReadUnaligned32 (Cells));
  if (Count == 2) Value = (Value << 32) | SwapBytes32 (ReadUnaligned32 (Cells + 1));
  return Value;
}

STATIC BOOLEAN AddRange (RAPHAEL_RANGE *Ranges, UINTN *Count, UINTN Max,
                        UINT64 Base, UINT64 Size) {
  if (!Size || Base > MAX_UINT64 - Size || *Count == Max) return FALSE;
  Ranges[(*Count)++] = (RAPHAEL_RANGE){Base, Size};
  return TRUE;
}

STATIC BOOLEAN ParseReg (CONST VOID *Fdt, INT32 Node, INT32 Parent, RAPHAEL_RANGE *Ranges,
                         UINTN *Count, UINTN Max) {
  INT32 Ac = FdtAddressCells (Fdt, Parent), Sc = FdtSizeCells (Fdt, Parent), Len;
  CONST UINT32 *Reg = FdtGetProp (Fdt, Node, "reg", &Len);
  if (Ac < 1 || Ac > 2 || Sc < 1 || Sc > 2 || !Reg || Len <= 0 ||
      Len % ((Ac + Sc) * 4)) return FALSE;
  for (INT32 I = 0; I < Len / 4; I += Ac + Sc) {
    if (!AddRange (Ranges, Count, Max, CellValue (Reg + I, Ac),
                   CellValue (Reg + I + Ac, Sc))) return FALSE;
  }
  return TRUE;
}

STATIC BOOLEAN CheckGeometry (CONST VOID *Fdt) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic ();
  RAPHAEL_RANGE Ram[32], Protected[128];
  UINTN Rc = 0, Pc = 0, Rejected;
  INT32 Node = -1, Depth = -1, Len, Parent, Parents[64];
  INT32 Reserved = FdtPathOffset (Fdt, "/reserved-memory");
  CONST CHAR8 *Type;
  CONST VOID *Value;
  UINT64 Base, Size, InitrdStart = 0, InitrdEnd = 0;
  RAPHAEL_ALLOCATION A[] = {
    {{D->ExtentBase, FixedPcdGet64 (PcdRaphaelFdBase) - D->ExtentBase}, 4096},
    {{FixedPcdGet64 (PcdRaphaelFdBase), FixedPcdGet32 (PcdRaphaelFdSize)}, 4096},
    {{FixedPcdGet64 (PcdRaphaelStackBase), FixedPcdGet32 (PcdRaphaelStackSize)}, 4096},
    {{FixedPcdGet64 (PcdRaphaelArenaBase), FixedPcdGet32 (PcdRaphaelArenaSize)}, 4096},
    {{FixedPcdGet64 (PcdRaphaelFdtBase), FixedPcdGet32 (PcdRaphaelFdtSize)}, 4096}
  };
  if (Reserved >= 0) {
    Value = FdtGetProp (Fdt, Reserved, "ranges", &Len);
    // Do not interpret untranslated bus addresses as physical RAM addresses.
    if (Value == NULL || Len != 0) return FALSE;
  }
  UINT64 DownloadEnd=FixedPcdGetBool(PcdRaphaelSparseArena)?FixedPcdGet64(PcdRaphaelDownloadedEnd):D->ExtentEnd;
  if (*(CONST UINT64 *)(UINTN)(D->ImageBase + 16) != DownloadEnd - D->ImageBase ||
      D->X1 || D->X2 || D->X3) return FALSE;
  while ((Node = FdtNextNode (Fdt, Node, &Depth)) >= 0) {
    if (Depth < 0) break;
    if ((UINTN)Depth >= ARRAY_SIZE (Parents)) return FALSE;
    Parent = Depth == 0 ? -1 : Parents[Depth - 1];
    Parents[Depth] = Node;
    // libfdt parent lookup rescans the tree from its root. Calling it for
    // every node makes a large handset FDT quadratic with caches disabled.
    // Keep the ancestor offsets from this single, bounded-depth traversal.
    Type = FdtGetProp (Fdt, Node, "device_type", &Len);
    if (Type && Len == 7 && CompareMem (Type, "memory", 7) == 0 &&
        !ParseReg (Fdt, Node, Parent, Ram, &Rc, ARRAY_SIZE (Ram))) return FALSE;
    if (Reserved >= 0 && Parent == Reserved) {
      // Dynamic pools are not an allocation grant. No allocation is made from
      // them; only checked explicit grants are used by this diagnostic experiment.
      Value = FdtGetProp (Fdt, Node, "reg", &Len);
      if (Value && !ParseReg (Fdt, Node, Parent, Protected, &Pc, ARRAY_SIZE (Protected))) return FALSE;
    }
  }
  for (INT32 I = 0; I < fdt_num_mem_rsv (Fdt); ++I) {
    if (fdt_get_mem_rsv (Fdt, I, &Base, &Size) ||
        !AddRange (Protected, &Pc, ARRAY_SIZE (Protected), Base, Size)) return FALSE;
  }
  Node = FdtPathOffset (Fdt, "/chosen");
  Value = FdtGetProp (Fdt, Node, "linux,initrd-start", &Len);
  if (Value) {
    if (Len != 4 && Len != 8) return FALSE;
    InitrdStart = CellValue (Value, Len / 4);
  }
  Value = FdtGetProp (Fdt, Node, "linux,initrd-end", &Len);
  if (Value) {
    if (Len != 4 && Len != 8) return FALSE;
    InitrdEnd = CellValue (Value, Len / 4);
  }
  if ((InitrdStart || InitrdEnd) && (InitrdEnd <= InitrdStart ||
      !AddRange (Protected, &Pc, ARRAY_SIZE (Protected), InitrdStart, InitrdEnd - InitrdStart))) return FALSE;
  if (!AddRange (Protected, &Pc, ARRAY_SIZE (Protected), D->ImageBase, D->ImageSize) ||
      !AddRange (Protected, &Pc, ARRAY_SIZE (Protected), D->X0, FdtTotalSize (Fdt))) return FALSE;
  if (D->Sp && !AddRange (Protected, &Pc, ARRAY_SIZE (Protected), D->Sp & ~4095ULL, 4096)) return FALSE;
  if (D->Lr && !AddRange (Protected, &Pc, ARRAY_SIZE (Protected), D->Lr & ~4095ULL, 4096)) return FALSE;
  if(FixedPcdGetBool(PcdRaphaelSparseArena)) {
    // Keep the actual Image grant distinct from the new experimental arena.
    // Every allocation is independently checked against the same live inputs.
    D->Status=RaphaelCheckMemoryPlan(D->ImageBase,
        (RAPHAEL_RANGE){D->ImageBase,DownloadEnd-D->ImageBase},A,3,
        Ram,Rc,Protected,Pc,&Rejected);
    if(D->Status==RaphaelPlanOk)D->Status=RaphaelCheckMemoryPlan(
        FixedPcdGet64(PcdRaphaelArenaBase),
        (RAPHAEL_RANGE){FixedPcdGet64(PcdRaphaelArenaBase),D->ExtentEnd-FixedPcdGet64(PcdRaphaelArenaBase)},
        &A[3],2,Ram,Rc,Protected,Pc,&Rejected);
  } else D->Status = RaphaelCheckMemoryPlan (FixedPcdGet64 (PcdRaphaelImageBase),
      (RAPHAEL_RANGE){D->ImageBase, D->ExtentEnd - D->ImageBase}, A, ARRAY_SIZE (A),
      Ram, Rc, Protected, Pc, &Rejected);
  if(D->Status!=RaphaelPlanOk)return FALSE;
  RAPHAEL_RANGE Extension={D->ImageBase,D->ExtentEnd-D->ImageBase};
  if(FixedPcdGetBool(PcdRaphaelSparseArena)){
    Extension.Length=DownloadEnd-D->ImageBase;
    if(!AddRange(Protected,&Pc,ARRAY_SIZE(Protected),FixedPcdGet64(PcdRaphaelArenaBase),
        D->ExtentEnd-FixedPcdGet64(PcdRaphaelArenaBase)))return FALSE;
  }
  return RaphaelPrepareKernelWindow(Ram,Rc,Protected,Pc,Extension)&&
      RaphaelPrepareAndroidReturn(D,Fdt,Ram,Rc,Protected,Pc);
}

STATIC UINT32 ReadDisplay32 (UINT64 Address, VOID *Context) {
  (VOID)Context;
  ArmDataMemoryBarrier ();
  UINT32 Value = *(volatile UINT32 *)(UINTN)Address;
  ArmDataMemoryBarrier ();
  return Value;
}

STATIC VOID WritePixel32 (UINT64 Address, UINT32 Value, VOID *Context) {
  (VOID)Context;
  *(volatile UINT32 *)(UINTN)Address=Value;
  ArmDataSynchronizationBarrier ();
}

STATIC UINT64 ReadPixelCounter (VOID *Context) {
  (VOID)Context;
  return ArmReadCntPct ();
}

extern EFI_STATUS RaphaelPrepareQemuArch(VOID *Fdt,RAPHAEL_DIAGNOSTIC *D);
extern EFI_STATUS RaphaelPreparePayload(RAPHAEL_DIAGNOSTIC *D);
extern EFI_STATUS RaphaelMaterializePayload(RAPHAEL_DIAGNOSTIC *D);

VOID EFIAPI SecFinish (UINT64 Status) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic ();
  VOID *Fdt = (VOID *)(UINTN)D->FdtCopy;
  UINT64 Record[48];
  INT32 Chosen;
  // An exception in the UFS DMA window cannot resume another storage owner.
  // Leave the owned FD pages intact for the already armed hardware reset.
  if(FixedPcdGetBool(PcdRaphaelUfsRead)&&mUfsRead.Word[27]){
    if(!FixedPcdGetBool(PcdRaphaelUfsResetOnError)||!RaphaelUfsEmergencyQuiesce(&mUfsHandoff,&mUfsRead))CpuDeadLoop();
  }
  if (D->Finishing) CpuDeadLoop ();
  D->Finishing = 1;
  if(FixedPcdGetBool(PcdRaphaelRamMappedProbe))RaphaelRestoreMappedPar();
  if((FixedPcdGet32(PcdRaphaelRamWritePages)|FixedPcdGet32(PcdRaphaelRamCacheWritePages))&&mRamWrite.Result.Dirty){
    mRamWrite.Result.EndCounter=ArmReadCntPct();
    // Never resume Android if original bytes could not be verified. A fault
    // during restoration re-enters with Finishing set and stops immediately.
    if(!RaphaelRestoreRamPage(&mRamWrite))CpuDeadLoop();
  }
  if(FixedPcdGet32(PcdRaphaelRamCacheWritePages)&&!RaphaelRestoreRamCacheMap())CpuDeadLoop();
  if(FixedPcdGetBool(PcdRaphaelQemuArchTest) && D->QemuArch.Version && D->Stage>=4) {
    // QEMU only. The GIC distributor/redistributor state is not restored;
    // therefore this mode is forbidden in handset image construction.
    ArmDisableInterrupts();ArmWriteCntpCtl((UINTN)D->QemuArch.SavedCtl&~1U);
    ArmWriteCntpCval(D->QemuArch.SavedCval);ArmWriteCntpCtl((UINTN)D->QemuArch.SavedCtl);
    D->QemuArch.CvalAfter=ArmReadCntpCval();D->QemuArch.CtlAfter=ArmReadCntpCtl();
    D->QemuArch.TimerRestored=D->QemuArch.CvalAfter==D->QemuArch.SavedCval&&((D->QemuArch.CtlAfter^D->QemuArch.SavedCtl)&3)==0;
  }
  if (FixedPcdGetBool(PcdRaphaelPhysicalTimerArch) && mPhysicalTimer.Dirty && mPhysicalTimer.Shutdown) {
    if (!mPhysicalTimer.Shutdown()) Status=0x224;
  }
  D->Status = Status;
  if(D->PixelWrite.Active) {
    RaphaelRestorePixelPatch(&D->PixelWrite,ReadDisplay32,WritePixel32,NULL);
    D->PixelWrite.Backup=0;
  }
  if(D->Menu.Restore.Active) {
    RaphaelRestoreGopPatch(&D->Menu.Restore,ReadDisplay32,WritePixel32,NULL);
    if(!D->Menu.Restore.Active)D->Menu.Restore.Backup=0;
  }
  if (FixedPcdGetBool(PcdRaphaelVisibleManager) && mManagerUi.Restore.Active) {
    RaphaelRestoreGopPatch(&mManagerUi.Restore,ReadDisplay32,WritePixel32,NULL);
    if(!mManagerUi.Restore.Active)mManagerUi.Restore.Backup=0;
    mManagerUi.Result.Active=mManagerUi.Restore.Active;
    mManagerUi.Result.Backup=mManagerUi.Restore.Backup;
    mManagerUi.Result.Fallback=mManagerUi.Restore.RestoreFallbackUsed;
  }
  if (D->Gop.Active) {
    RaphaelRestoreGopPatch(&D->Gop,ReadDisplay32,WritePixel32,NULL);
    if (!D->Gop.Active) D->Gop.Backup=0;
    else D->Status=0x240; // Retain the only backup if restoration failed.
  }
  if (Fdt != NULL) {
    Chosen = FdtPathOffset (Fdt, "/chosen");
    for (UINTN I = 0; I < ARRAY_SIZE (Record); ++I)
      Record[I] = SwapBytes64 (((UINT64 *)D)[I]);
    if (D->Display.Version) {
      UINT64 *Words = (UINT64 *)&D->Display;
      UINTN Count = 3 + 2 * D->Display.Count;
      if (Count > sizeof (D->Display) / 8) CpuDeadLoop ();
      for (UINTN I = 0; I < Count; ++I) Words[I] = SwapBytes64 (Words[I]);
      if (FdtSetProp (Fdt, Chosen, "raphael,display-snapshot", Words, (INT32)(Count * 8)))
        D->FdtCopy = 0;
    }
    if (D->PixelWrite.Version) {
      UINT64 *Words=(UINT64 *)&D->PixelWrite;
      for(UINTN I=0; I<sizeof(D->PixelWrite)/8; ++I) Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,display-write",Words,sizeof(D->PixelWrite))) D->FdtCopy=0;
    }
    if (D->Gop.Version) {
      UINT64 *Words=(UINT64 *)&D->Gop;
      for(UINTN I=0; I<sizeof(D->Gop)/8; ++I) Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,display-gop",Words,sizeof(D->Gop))) D->FdtCopy=0;
    }
    if (FixedPcdGetBool(PcdRaphaelVisibleManager) && mManagerUi.Result.Version) {
      UINT64 *Words=(UINT64 *)&mManagerUi.Result;
      for(UINTN I=0;I<sizeof(mManagerUi.Result)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,manager-ui",Words,sizeof(mManagerUi.Result)))D->FdtCopy=0;
    }
    if(FixedPcdGet32(PcdRaphaelRamWritePages)&&mRamWrite.Result.Version){
      UINT64 *Words=(UINT64 *)&mRamWrite.Result;
      for(UINTN I=0;I<sizeof(mRamWrite.Result)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ram-write",Words,sizeof(mRamWrite.Result)))D->FdtCopy=0;
    }
    if(FixedPcdGet32(PcdRaphaelRamCacheWritePages)&&mRamCache.Result.Version){
      UINT64 Wire[39];CopyMem(Wire,&mRamCache.Result,sizeof(mRamCache.Result));
      CopyMem(Wire+16,&mRamWrite.Result,sizeof(mRamWrite.Result));
      for(UINTN I=0;I<39;++I)Wire[I]=SwapBytes64(Wire[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ram-cache-write",Wire,sizeof(Wire)))D->FdtCopy=0;
    }
    if(FixedPcdGetBool(PcdRaphaelRamMappedProbe)&&mRamMapped.Version){
      UINT64 *Words=(UINT64 *)&mRamMapped;
      for(UINTN I=0;I<sizeof(mRamMapped)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ram-mapped",Words,sizeof(mRamMapped)))D->FdtCopy=0;
    }
    if (FixedPcdGetBool(PcdRaphaelRamReadProbe) && mRamRead.Version) {
      UINT64 *Words=(UINT64 *)&mRamRead;
      for(UINTN I=0;I<sizeof(mRamRead)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ram-read",Words,sizeof(mRamRead)))D->FdtCopy=0;
    }
    if (FixedPcdGetBool(PcdRaphaelPhysicalTimerArch) && mPhysicalTimer.Result.Version) {
      if (FixedPcdGetBool(PcdRaphaelPayloadTest) && mPhysicalTimer.Manager.Version) {
        UINT64 *Manager=(UINT64 *)&mPhysicalTimer.Manager;
        for (UINTN I=0;I<sizeof(mPhysicalTimer.Manager)/8;++I) Manager[I]=SwapBytes64(Manager[I]);
        if (FdtSetProp(Fdt,Chosen,"raphael,manager-run",Manager,sizeof(mPhysicalTimer.Manager))) D->FdtCopy=0;
      }
      UINT64 *Words=(UINT64 *)&mPhysicalTimer.Result;
      for (UINTN I=0;I<sizeof(mPhysicalTimer.Result)/8;++I) Words[I]=SwapBytes64(Words[I]);
      if (FdtSetProp(Fdt,Chosen,"raphael,physical-timer-arch",Words,sizeof(mPhysicalTimer.Result))) D->FdtCopy=0;
    }
    if(FixedPcdGetBool(PcdRaphaelTimerIrqTest)&&mTimerIrq.Version) {
      UINT64 *Words=(UINT64 *)&mTimerIrq;
      for(UINTN I=0;I<sizeof(mTimerIrq)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,timer-irq",Words,sizeof(mTimerIrq)))D->FdtCopy=0;
    }
    if(FixedPcdGetBool(PcdRaphaelTimerRouteTest)&&mTimerRoute.Version) {
      UINT64 *Words=(UINT64 *)&mTimerRoute;
      for(UINTN I=0;I<sizeof(mTimerRoute)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,timer-route",Words,sizeof(mTimerRoute)))D->FdtCopy=0;
    }
    if(FixedPcdGetBool(PcdRaphaelGicEnableMap)&&mGicEnableMap.Version) {
      UINT64 *Words=(UINT64 *)&mGicEnableMap;
      for(UINTN I=0;I<sizeof(mGicEnableMap)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,gic-enable-map",Words,sizeof(mGicEnableMap)))D->FdtCopy=0;
    }
    if(FixedPcdGetBool(PcdRaphaelPpiEnableProbe)&&mPpiProbe.Version) {
      UINT64 *Words=(UINT64 *)&mPpiProbe;
      for(UINTN I=0;I<sizeof(mPpiProbe)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ppi-enable-probe",Words,sizeof(mPpiProbe)))D->FdtCopy=0;
    }
    if(D->TimerSource.Version) {
      UINT64 *Words=(UINT64 *)&D->TimerSource;
      for(UINTN I=0;I<sizeof(D->TimerSource)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,timer-source",Words,sizeof(D->TimerSource)))D->FdtCopy=0;
    }
    if(D->Icc.Version) {
      UINT64 *Words=(UINT64 *)&D->Icc;
      for(UINTN I=0;I<sizeof(D->Icc)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,icc-readonly",Words,sizeof(D->Icc)))D->FdtCopy=0;
    }
    if(D->Gic.Version) {
      UINT64 *Words=(UINT64 *)&D->Gic;
      for(UINTN I=0;I<sizeof(D->Gic)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,gic-readonly",Words,sizeof(D->Gic)))D->FdtCopy=0;
    }
    if(D->QemuArch.Version) {
      UINT64 *Words=(UINT64 *)&D->QemuArch;
      for(UINTN I=0;I<sizeof(D->QemuArch)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,qemu-architecture",Words,sizeof(D->QemuArch)))D->FdtCopy=0;
    }
    if(D->NativeMmuResult) {
      UINT64 At=D->NativeMmuResult,Base=FixedPcdGet64(PcdRaphaelArenaBase),Bytes=FixedPcdGet32(PcdRaphaelArenaSize);
      if(At<Base||At-Base>Bytes||sizeof(RAPHAEL_NATIVE_MMU_STATE)>Bytes-(At-Base))D->FdtCopy=0;
      else {
        RAPHAEL_NATIVE_MMU_STATE *State=(VOID *)(UINTN)At;UINT64 Snapshot=State->Snapshot;
        if(FixedPcdGetBool(PcdRaphaelNativeEarlyTest)) {
          UINT64 E=State->Early;
          if(E<Base||E-Base>Bytes||sizeof(RAPHAEL_NATIVE_EARLY_STATE)>Bytes-(E-Base))D->FdtCopy=0;
          else {
            RAPHAEL_NATIVE_EARLY_STATE *Early=(VOID *)(UINTN)E;UINT64 Delta=Early->Delta,Length=Early->Result.DeltaBytes;
            if(Length>(Early->Result.Version>=9?0x100000:Early->Result.Version>=4?0x80000:0x40000)||Delta<Base||Delta-Base>Bytes||Length>Bytes-(Delta-Base))D->FdtCopy=0;
            else if(FdtSetProp(Fdt,Chosen,"raphael,native-early-delta",(VOID *)(UINTN)Delta,(UINT32)Length))D->FdtCopy=0;
            UINT64 EarlyWords[(sizeof(RAPHAEL_NATIVE_EARLY_RESULT)+sizeof(RAPHAEL_NATIVE_THREAD_RESULT)+sizeof(RAPHAEL_NATIVE_EXCEPTION_RESULT))/8];
            UINTN EarlyBytes=Early->Result.Version>=9?640:Early->Result.Version>=8?448:320;CopyMem(EarlyWords,&Early->Result,EarlyBytes);
            if(Early->Result.Version>=5){CopyMem((UINT8 *)EarlyWords+EarlyBytes,&Early->Thread,sizeof(Early->Thread));EarlyBytes+=sizeof(Early->Thread);}
            if(Early->Result.Version>=8){CopyMem((UINT8 *)EarlyWords+EarlyBytes,&Early->Exception,sizeof(Early->Exception));EarlyBytes+=sizeof(Early->Exception);}
            for(UINTN I=0;I<EarlyBytes/8;++I)EarlyWords[I]=SwapBytes64(EarlyWords[I]);
            if(FdtSetProp(Fdt,Chosen,"raphael,native-early-c",EarlyWords,(UINT32)EarlyBytes))D->FdtCopy=0;
          }
        }

        if(State->Platform.Version){
          UINT64 PlatformWords[sizeof(RAPHAEL_NATIVE_PLATFORM_RESULT)/8];CopyMem(PlatformWords,&State->Platform,sizeof(PlatformWords));
          for(UINTN I=0;I<ARRAY_SIZE(PlatformWords);++I)PlatformWords[I]=SwapBytes64(PlatformWords[I]);
          if(FdtSetProp(Fdt,Chosen,"raphael,native-platform",PlatformWords,sizeof(PlatformWords)))D->FdtCopy=0;
        }
        if(State->Gic.Version){
          UINT64 Words[sizeof(State->Gic)/8];CopyMem(Words,&State->Gic,sizeof(Words));
          for(UINTN I=0;I<ARRAY_SIZE(Words);++I)Words[I]=SwapBytes64(Words[I]);
          if(FdtSetProp(Fdt,Chosen,"raphael,native-gic",Words,sizeof(Words)))D->FdtCopy=0;
        }
        if(State->Watchdog.Version){
          UINT64 WatchdogWords[sizeof(State->Watchdog)/8];CopyMem(WatchdogWords,&State->Watchdog,sizeof(WatchdogWords));
          for(UINTN I=0;I<ARRAY_SIZE(WatchdogWords);++I)WatchdogWords[I]=SwapBytes64(WatchdogWords[I]);
          if(FdtSetProp(Fdt,Chosen,"raphael,native-watchdog",WatchdogWords,sizeof(WatchdogWords)))D->FdtCopy=0;
        }
        if(State->Pmap){
          UINT64 P=State->Pmap;
          if(P<Base||P-Base>Bytes||sizeof(RAPHAEL_NATIVE_PMAP_STATE)>Bytes-(P-Base))D->FdtCopy=0;
          else {
            RAPHAEL_NATIVE_PMAP_STATE *Pmap=(VOID *)(UINTN)P;UINT64 Sparse=Pmap->Sparse,Length=Pmap->Result.SparseBytes;
            if(!RaphaelNativePmapSparseRange(Sparse,Length,Base,Bytes))D->FdtCopy=0;
            else if(FdtSetProp(Fdt,Chosen,"raphael,native-pmap-tables",(VOID *)(UINTN)Sparse,(UINT32)Length))D->FdtCopy=0;
            UINT64 Transition=Pmap->Result.TransitionBase,TransitionBytes=Pmap->Result.TransitionBytes;
            if(TransitionBytes!=RaphaelNativeTransitionPages(Pmap->Result.CleanBytes)*4096||Transition<Base||Transition-Base>Bytes||TransitionBytes>Bytes-(Transition-Base))D->FdtCopy=0;
            else if(FdtSetProp(Fdt,Chosen,"raphael,native-pmap-transition",(VOID *)(UINTN)Transition,(UINT32)TransitionBytes))D->FdtCopy=0;
            UINT64 Adt=Pmap->AdtSnapshot,AdtBytes=Pmap->Result.AdtBytes;
            if(!AdtBytes||AdtBytes>65536||Adt<Base||Adt-Base>Bytes||AdtBytes>Bytes-(Adt-Base))D->FdtCopy=0;
            else if(FdtSetProp(Fdt,Chosen,"raphael,native-pmap-adt",(VOID *)(UINTN)Adt,(UINT32)AdtBytes))D->FdtCopy=0;
            UINT64 PmapWords[sizeof(RAPHAEL_NATIVE_PMAP_RESULT)/8];CopyMem(PmapWords,&Pmap->Result,sizeof(PmapWords));
            for(UINTN I=0;I<ARRAY_SIZE(PmapWords);++I)PmapWords[I]=SwapBytes64(PmapWords[I]);
            if(FdtSetProp(Fdt,Chosen,"raphael,native-pmap",PmapWords,sizeof(PmapWords)))D->FdtCopy=0;
          }
        }
        if(Snapshot<Base||Snapshot-Base>Bytes||65536>Bytes-(Snapshot-Base))D->FdtCopy=0;
        else if(FdtSetProp(Fdt,Chosen,"raphael,native-mmu-tables",(VOID *)(UINTN)Snapshot,65536))D->FdtCopy=0;
        UINT64 Words[sizeof(RAPHAEL_NATIVE_MMU_RESULT)/8];CopyMem(Words,(VOID *)(UINTN)At,sizeof(Words));
        for(UINTN I=0;I<ARRAY_SIZE(Words);++I)Words[I]=SwapBytes64(Words[I]);
        if(FdtSetProp(Fdt,Chosen,"raphael,native-mmu",Words,sizeof(Words)))D->FdtCopy=0;
      }
    }
    if(D->NativeEntryResult) {
      UINT64 At=D->NativeEntryResult,Base=FixedPcdGet64(PcdRaphaelArenaBase),Bytes=FixedPcdGet32(PcdRaphaelArenaSize);
      if(At<Base||At-Base>Bytes||sizeof(RAPHAEL_NATIVE_ENTRY_RESULT)>Bytes-(At-Base))D->FdtCopy=0;
      else {
        UINT64 Words[sizeof(RAPHAEL_NATIVE_ENTRY_RESULT)/8];CopyMem(Words,(VOID *)(UINTN)At,sizeof(Words));
        for(UINTN I=0;I<ARRAY_SIZE(Words);++I)Words[I]=SwapBytes64(Words[I]);
        if(FdtSetProp(Fdt,Chosen,"raphael,native-entry",Words,sizeof(Words)))D->FdtCopy=0;
      }
    }
    if(D->NativeLoadResult) {
      UINT64 At=D->NativeLoadResult,Base=FixedPcdGet64(PcdRaphaelArenaBase),Bytes=FixedPcdGet32(PcdRaphaelArenaSize);
      if(At<Base||At-Base>Bytes||sizeof(RAPHAEL_NATIVE_LOAD_RESULT)>Bytes-(At-Base))D->FdtCopy=0;
      else {
        UINT64 Words[sizeof(RAPHAEL_NATIVE_LOAD_RESULT)/8];CopyMem(Words,(VOID *)(UINTN)At,sizeof(Words));
        for(UINTN I=0;I<ARRAY_SIZE(Words);++I)Words[I]=SwapBytes64(Words[I]);
        if(FdtSetProp(Fdt,Chosen,"raphael,native-load",Words,sizeof(Words)))D->FdtCopy=0;
      }
    }
    if(D->Darwin.Version) {
      UINT64 *Words=(UINT64 *)&D->Darwin;
      for(UINTN I=0;I<sizeof(D->Darwin)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,darwin-diagnostic",Words,sizeof(D->Darwin)))D->FdtCopy=0;
    }
    if(D->Payload.Version) {
      UINT64 *Words=(UINT64 *)&D->Payload;
      for(UINTN I=0;I<sizeof(D->Payload)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,payload-diagnostic",Words,sizeof(D->Payload)))D->FdtCopy=0;
    }
    if(D->Menu.Version) {
      UINT64 *Words=(UINT64 *)&D->Menu;
      for(UINTN I=0;I<sizeof(D->Menu)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,display-menu",Words,sizeof(D->Menu)))D->FdtCopy=0;
    }
    if(D->InputDxe.Version) {
      UINT64 *Words=(UINT64 *)&D->InputDxe;
      for(UINTN I=0;I<sizeof(D->InputDxe)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,input-dxe",Words,sizeof(D->InputDxe)))D->FdtCopy=0;
    }
    if(D->Keys.Version) {
      UINT64 *Words=(UINT64 *)&D->Keys;
      for(UINTN I=0;I<sizeof(D->Keys)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,input-registers",Words,sizeof(D->Keys)))D->FdtCopy=0;
    }
    if (D->Input.Version) {
      UINT32 *Words=(UINT32 *)&D->Input;
      for(UINTN I=0;I<sizeof(D->Input)/4;++I)Words[I]=SwapBytes32(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,input-map",Words,sizeof(D->Input)))D->FdtCopy=0;
    }
    if (D->Pixels.Version) {
      UINT32 *Words = (UINT32 *)&D->Pixels;
      for (UINTN I=0; I<sizeof(D->Pixels)/4; ++I) Words[I]=SwapBytes32(Words[I]);
      if (FdtSetProp(Fdt,Chosen,"raphael,display-pixels",Words,sizeof(D->Pixels))) D->FdtCopy=0;
    }
    if(FixedPcdGetBool(PcdRaphaelAndroidReturn) && !RaphaelExportAndroidReturn(Fdt))D->FdtCopy=0;
    if(mUfsUncachedWords[0]){
      UINT64 Words[5];for(UINTN I=0;I<5;++I)Words[I]=SwapBytes64(mUfsUncachedWords[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ufs-uncached",Words,sizeof(Words)))D->FdtCopy=0;
    }
    if(mUfsRead.Word[0]){
      UINT64 *Words=mUfsRead.Word;
      for(UINTN I=0;I<RAPHAEL_UFS_READ_WORDS;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ufs-read",&mUfsRead,sizeof(mUfsRead)))D->FdtCopy=0;
    }
    if(mUfsHandoff.Version){
      UINT64 *Words=(UINT64 *)&mUfsHandoff;
      for(UINTN I=0;I<sizeof(mUfsHandoff)/8;++I)Words[I]=SwapBytes64(Words[I]);
      if(FdtSetProp(Fdt,Chosen,"raphael,ufs-handoff",Words,sizeof(mUfsHandoff)))D->FdtCopy=0;
    }
    if (Chosen < 0 || FdtSetProp (Fdt, Chosen, "raphael,sec-dxe", Record, sizeof (Record)) ||
        FdtSetProp (Fdt, Chosen, "raphael,sec-dxe-log", D->Log, (INT32)D->LogUsed) ||
        FdtSetProp (Fdt, Chosen, "raphael,sec-dxe-map", D->Map, (INT32)D->MapBytes) || FdtPack (Fdt))
      D->FdtCopy = 0;
  }
  // The assembly leaf cleans only our mapped extension and disables caches/MMU
  // without making further stack writes. Basecore's whole-cache APIs assert on
  // this architecture; no whole-cache stubs or firmware services are called.
  if(FixedPcdGetBool(PcdRaphaelAndroidReturn))RaphaelFinishAndroidReturn(D);
  if(FixedPcdGetBool(PcdRaphaelSparseArena)){
    // No high capsule was armed. Do not clean or touch unrelated sparse gaps.
    // The original Android boot partition is restored by a firmware reset.
    ArmDisableInterrupts();
    register UINT64 Function __asm__("x0")=0x84000009U;
    if(FixedPcdGetBool(PcdRaphaelAndroidReturnQemu))__asm__ volatile("hvc #0":"+r"(Function)::"x1","x2","x3","x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
    else __asm__ volatile("smc #0":"+r"(Function)::"x1","x2","x3","x4","x5","x6","x7","x8","x9","x10","x11","x12","x13","x14","x15","x16","x17","memory","cc");
    CpuDeadLoop();
  }
  RaphaelResume (D);
  CpuDeadLoop ();
}

VOID EFIAPI SecMain (VOID) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic ();
  VOID *Fdt = (VOID *)(UINTN)D->X0;
  VOID *Copy = (VOID *)(UINTN)FixedPcdGet64 (PcdRaphaelFdtBase);
  UINT64 Start = FixedPcdGet64 (PcdRaphaelExtentBase);
  UINT64 End = FixedPcdGet64 (PcdRaphaelExtentEnd);
  UINT64 Arena = FixedPcdGet64 (PcdRaphaelArenaBase);
  UINT64 ArenaSize = FixedPcdGet32 (PcdRaphaelArenaSize);
  EFI_HOB_HANDOFF_INFO_TABLE *Hob;
  EFI_STATUS Status;
  ARM_MEMORY_REGION_DESCRIPTOR Map[12];
  VOID *PageTable;
  UINTN PageTableBytes;
  ZeroMem ((UINT8 *)D + OFFSET_OF (RAPHAEL_DIAGNOSTIC, ImageBase),
           sizeof (*D) - OFFSET_OF (RAPHAEL_DIAGNOSTIC, ImageBase));
  D->Magic = RAPHAEL_DIAG_MAGIC;
  D->ImageBase = FixedPcdGet64 (PcdRaphaelImageBase);
  D->ImageSize = FixedPcdGet64 (PcdRaphaelImageSize);
  D->OriginalEntry = FixedPcdGet64 (PcdRaphaelOriginalEntry);
  D->OriginalInstruction = FixedPcdGet32 (PcdRaphaelOriginalInstruction);
  D->ExtentBase = Start;
  D->ExtentEnd = End;
  D->Finish = (UINTN)SecFinish;
  D->Stage = 1;
  DEBUG ((DEBUG_INFO, "RAPHAEL SEC entered EL1; hardware drivers disabled\n"));
  // Native recovery exports up to 512KiB delta, two 64KiB table snapshots,
  // a 64KiB ADT, transition tables, video records and bounded logs. Reserve
  // 1MiB before XNU executes; the generic 64KiB margin cannot hold that wire.
  UINT32 FdtHeadroom = FixedPcdGetBool(PcdRaphaelNativeEarlyTest) ? 0x100000 : 0x10000;
  if (FixedPcdGet32 (PcdRaphaelFdtSize) <= FdtHeadroom ||
      (D->X0 & 7) || FdtCheckHeader (Fdt) ||
      FdtTotalSize (Fdt) > FixedPcdGet32 (PcdRaphaelFdtSize) - FdtHeadroom ||
      fdt_check_full (Fdt, FdtTotalSize (Fdt))) SecFinish (0x101);
  if(FixedPcdGetBool(PcdRaphaelNativeLoadTest)&&(!FixedPcdGetBool(PcdRaphaelSparseArena)||
     !FixedPcdGetBool(PcdRaphaelDarwinTest)||FixedPcdGetBool(PcdRaphaelNativeHandoff)))SecFinish(0x23a);
  if(FixedPcdGetBool(PcdRaphaelSparseArena)){
    // Separate opt-in experimental arena; it is outside the actual Image.
    // This is an experimental boot grant, not a claim of downloaded bytes.
    if(!FixedPcdGetBool(PcdRaphaelAndroidReturn)||!FixedPcdGetBool(PcdRaphaelNativeBoot)||
       FixedPcdGetBool(PcdRaphaelNativeHandoff)||
       FixedPcdGet64(PcdRaphaelDownloadedEnd)!=FixedPcdGet64(PcdRaphaelStackBase)+FixedPcdGet32(PcdRaphaelStackSize)||
       FixedPcdGet64(PcdRaphaelDownloadedEnd)>Arena||Arena+ArenaSize>FixedPcdGet64(PcdRaphaelFdtBase))SecFinish(0x238);
  }
  if (!CheckGeometry (Fdt)) SecFinish (0x102);
  D->Stage = 2;
  if(FixedPcdGetBool(PcdRaphaelVisibleManager)) {
    if(!FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)||!FixedPcdGetBool(PcdRaphaelPayloadTest)||
       !FixedPcdGetBool(PcdRaphaelExperimentalGop)||!FixedPcdGetBool(PcdRaphaelInputProtocol)||FixedPcdGetBool(PcdRaphaelMenuTest))SecFinish(0x22a);
    mManagerUi.Result.Version=1;mManagerUi.Result.Status=1;
  }
  if(FixedPcdGetBool(PcdRaphaelPayloadTest)){D->Payload.Version=1;D->Payload.Status=1;}
  if(FixedPcdGetBool(PcdRaphaelDarwinTest)){D->Darwin.Version=1;D->Darwin.Status=1;}
  if (FdtOpenInto (Fdt, Copy, FixedPcdGet32 (PcdRaphaelFdtSize)) ||
      fdt_add_mem_rsv (Copy, Start, (FixedPcdGetBool(PcdRaphaelSparseArena)?FixedPcdGet64(PcdRaphaelDownloadedEnd):End) - Start) ||
      (FixedPcdGetBool(PcdRaphaelSparseArena)&&fdt_add_mem_rsv(Copy,Arena,End-Arena)) ||
      FdtSetPropString (Copy, FdtPathOffset (Copy, "/chosen"), "raphael,sec-dxe-id",
                        FixedPcdGetPtr (PcdRaphaelTestId))) SecFinish (0x103);
  D->FdtCopy = (UINTN)Copy;
  if(FixedPcdGetBool(PcdRaphaelUfsRead)&&!FixedPcdGetBool(PcdRaphaelUfsHandoff))SecFinish(0x23d);
  if(FixedPcdGetBool(PcdRaphaelUfsHandoff)&&!FixedPcdGetBool(PcdRaphaelUfsRead)){
    if(D->Sctlr&0x1005)SecFinish(0x23b);
    RaphaelCollectUfsHandoff(Fdt,D->ImageBase,D->ExtentEnd,&mUfsHandoff,ReadDisplay32,NULL);
    DEBUG((DEBUG_INFO,"UFS handoff status=%lu base=%lx bytes=%lx reads=%lu\n",mUfsHandoff.Status,mUfsHandoff.Base,mUfsHandoff.Bytes,mUfsHandoff.ReadCount));
    if(mUfsHandoff.Status!=1&&mUfsHandoff.Status!=3)SecFinish(0x23c);
  }

  if(FixedPcdGetBool(PcdRaphaelUfsRead)&&FixedPcdGetBool(PcdRaphaelAndroidReturnQemu)){
    INT32 Len; // Controlled non-SM8150 QEMU failure: test the pre-MMU return contract.
    if(FdtGetProp(Fdt,FdtPathOffset(Fdt,"/chosen"),"raphael,qemu-ufs-early-return",&Len)){
      if(!RaphaelArmAndroidReturnEarly(D))SecFinish(0x23f);
      SecFinish(0);
    }
  }
  if(FixedPcdGet32(PcdRaphaelRamWritePages)&&!FixedPcdGetBool(PcdRaphaelRamReadProbe))SecFinish(0x22b);
  if(FixedPcdGet32(PcdRaphaelRamCacheWritePages)&&(!FixedPcdGetBool(PcdRaphaelRamMappedProbe)||FixedPcdGet32(PcdRaphaelRamWritePages)))SecFinish(0x22f);
  if(FixedPcdGetBool(PcdRaphaelRamMappedProbe)&&(!FixedPcdGetBool(PcdRaphaelRamReadProbe)||
     FixedPcdGet32(PcdRaphaelRamWritePages)||FixedPcdGet32(PcdRaphaelStopAfterStage)>3))SecFinish(0x22c);
  if(FixedPcdGetBool(PcdRaphaelRamReadProbe)) {
    if(FixedPcdGet32(PcdRaphaelStopAfterStage)!=2&&!FixedPcdGetBool(PcdRaphaelRamMappedProbe))SecFinish(0x228);
    BOOLEAN Ok=RaphaelRunRamRead(Fdt,D,&mRamRead,&mRamWrite,mRamBackup);
    DEBUG((DEBUG_INFO,"RAM sparse read status=%lu reason=%lu completed=%lu/%lu PA=%lu\n",mRamRead.Status,mRamRead.Reason,mRamRead.Completed,mRamRead.Requested,mRamRead.PhysicalBits));
    if(FixedPcdGet32(PcdRaphaelRamWritePages))DEBUG((DEBUG_INFO,"RAM write status=%lu completed=%lu restored=%lu dirty=%lu\n",mRamWrite.Result.Status,mRamWrite.Result.CompletedPages,mRamWrite.Result.RestoredPages,mRamWrite.Result.Dirty));
    if(!Ok)SecFinish(0x229);
    if(FixedPcdGetBool(PcdRaphaelRamMappedProbe)){
      mRamMapped.Version=1;mRamMapped.Status=1;mRamMapped.Base=mRamRead.Base;
      mRamMapped.Bytes=mRamRead.Bytes;mRamMapped.Stride=mRamRead.Stride;
      mRamMapped.Requested=mRamRead.Requested;mRamMapped.BeforeDigest=mRamRead.Digest;
      if(FixedPcdGet32(PcdRaphaelRamCacheWritePages)){
        mRamCache.Result.Version=1;mRamCache.Result.Status=1;mRamCache.Result.Base=mRamRead.Base;
        mRamCache.Result.Bytes=mRamRead.Bytes;mRamCache.Result.Pages=FixedPcdGet32(PcdRaphaelRamCacheWritePages);
      }
    }
  }

  if(FixedPcdGetBool(PcdRaphaelGicProbe)) {
    if((FixedPcdGet32(PcdRaphaelStopAfterStage)!=2&&!FixedPcdGetBool(PcdRaphaelPhysicalTimerArch))||(D->Sctlr&0x1005))SecFinish(0x110);
    RaphaelCollectGic(Fdt,D->Mpidr,Start,End,&D->Gic,ReadDisplay32,NULL);
    DEBUG((DEBUG_INFO,"RAPHAEL read-only GIC status=%lu reason=%lu reads=%lu frames=%lu boot=%lu\n",
      D->Gic.Status,D->Gic.Reason,D->Gic.ReadCount,D->Gic.FrameCount,D->Gic.BootIndex));
    if(D->Gic.Status!=4)SecFinish(0x111);
  }
  if(FixedPcdGetBool(PcdRaphaelIccProbe)) {
    if(!FixedPcdGetBool(PcdRaphaelGicProbe)||(FixedPcdGet32(PcdRaphaelStopAfterStage)!=2&&!FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)))SecFinish(0x112);
    RaphaelCollectIcc(&D->Gic,&D->Icc,RaphaelReadIccRegister,NULL);
    DEBUG((DEBUG_INFO,"RAPHAEL read-only ICC status=%lu attempted=%lu completed=%lu failed=%lu\n",
      D->Icc.Status,D->Icc.Attempted,D->Icc.Completed,D->Icc.FailedSelector));
    if(D->Icc.Status!=5)SecFinish(0x113);
    if(FixedPcdGetBool(PcdRaphaelIccFaultTest)) {
      UINT64 Value=0xabcdef;
      BOOLEAN Read=RaphaelReadInjectedUndefined(&Value,&D->Icc.InjectedFaultEsr,&D->Icc.InjectedFaultElr);
      D->Icc.InjectedFaultRecovered=!Read&&Value==0xabcdef&&(D->Icc.InjectedFaultEsr>>26)==0&&D->Icc.InjectedFaultElr!=0;
      if(!D->Icc.InjectedFaultRecovered)SecFinish(0x114);
    }
  }
  if(FixedPcdGetBool(PcdRaphaelGicEnableMap)) {
    if(!FixedPcdGetBool(PcdRaphaelIccProbe)||FixedPcdGetBool(PcdRaphaelPpiEnableProbe)||
       FixedPcdGetBool(PcdRaphaelTimerSourceTest)||FixedPcdGetBool(PcdRaphaelIccFaultTest)||
       (FixedPcdGet32(PcdRaphaelStopAfterStage)!=2&&!FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)))SecFinish(0x11a);
    RaphaelCollectGicEnableMap(&D->Gic,&mGicEnableMap,ReadDisplay32,NULL);
    DEBUG((DEBUG_INFO,"GIC enable map status=%lu spi=%lu frames=%lu changed=%lu all-disabled=%lu\n",
      mGicEnableMap.Status,mGicEnableMap.SpiWords,mGicEnableMap.FrameCount,mGicEnableMap.ChangedWords,mGicEnableMap.AllObservedDisabled));
    if(mGicEnableMap.Status!=3&&mGicEnableMap.Status!=4)SecFinish(0x11b);
  }
  if(FixedPcdGetBool(PcdRaphaelTimerIrqTest)&&!FixedPcdGetBool(PcdRaphaelTimerRouteTest))SecFinish(0x120);
  if(FixedPcdGetBool(PcdRaphaelTimerRouteTest)) {
    if(!FixedPcdGetBool(PcdRaphaelGicEnableMap)||FixedPcdGetBool(PcdRaphaelPpiEnableProbe)||
       FixedPcdGetBool(PcdRaphaelTimerSourceTest)||FixedPcdGetBool(PcdRaphaelIccFaultTest)||
       (FixedPcdGet32(PcdRaphaelStopAfterStage)!=2&&!FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)))SecFinish(0x11c);
    if(FixedPcdGetBool(PcdRaphaelTimerIrqTest)) {
      if(FixedPcdGetBool(PcdRaphaelTimerRouteFaultTest)||(D->Icc.Values[RaphaelSysCtlr]&2))SecFinish(0x11f);
      RaphaelTestTimerRouteWithIrq(Fdt,&D->Gic,&D->Icc,&mGicEnableMap,&mTimerRoute,
        ReadDisplay32,WritePixel32,RaphaelTimerRouteRead,RaphaelTimerRouteWrite,NULL,RaphaelRunTimerIrqWindow,&mTimerIrq);
      DEBUG((DEBUG_INFO,"Timer IRQ status=%lu entries=%lu id=%lu EOI=%lu restore=%lu\n",
        mTimerIrq.Status,mTimerIrq.Entries,mTimerIrq.ObservedId,mTimerIrq.EoiCount,mTimerRoute.RestoreOk));
    } else RaphaelTestTimerRoute(Fdt,&D->Gic,&D->Icc,&mGicEnableMap,&mTimerRoute,
      ReadDisplay32,WritePixel32,RaphaelTimerRouteRead,RaphaelTimerRouteWrite,NULL);
    DEBUG((DEBUG_INFO,"Timer route status=%lu reason=%lu intid=%lu hppir=%lu polls=%lu restore=%lu\n",
      mTimerRoute.Status,mTimerRoute.Reason,mTimerRoute.Intid,mTimerRoute.HppirDuring,mTimerRoute.Polls,mTimerRoute.RestoreOk));
    if(FixedPcdGetBool(PcdRaphaelTimerRouteFaultTest)) {
      if(mTimerRoute.Status!=3||mTimerRoute.Reason!=2||!mTimerRoute.RestoreOk||mTimerRoute.TrapEsr>>26||!mTimerRoute.TrapElr)SecFinish(0x11e);
    } else if(mTimerRoute.Status!=6)SecFinish(0x11d);
  }
  if(FixedPcdGetBool(PcdRaphaelPpiEnableProbe)) {
    if(!FixedPcdGetBool(PcdRaphaelIccProbe)||FixedPcdGetBool(PcdRaphaelTimerSourceTest)||
       FixedPcdGetBool(PcdRaphaelIccFaultTest)||(FixedPcdGet32(PcdRaphaelStopAfterStage)!=2&&!FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)))SecFinish(0x118);
    RaphaelProbePhysicalPpi(Fdt,&D->Gic,&D->Icc,&mPpiProbe,ReadDisplay32,WritePixel32,ReadPixelCounter,NULL);
    DEBUG((DEBUG_INFO,"PPI probe status=%lu intid=%lu writes=%lu restored=%lu\n",mPpiProbe.Status,mPpiProbe.Intid,mPpiProbe.WriteCount,mPpiProbe.RestoreOk));
    if((mPpiProbe.Status!=6&&mPpiProbe.Status!=3)||!mPpiProbe.RestoreOk)SecFinish(0x119);
  }
  if(FixedPcdGetBool(PcdRaphaelTimerSourceTest)) {
    if(!FixedPcdGetBool(PcdRaphaelIccProbe)||(FixedPcdGet32(PcdRaphaelStopAfterStage)!=2&&!FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)))SecFinish(0x115);
    BOOLEAN Injected=FALSE;
    RaphaelTestTimerSource(&D->Icc,&D->TimerSource,RaphaelTimerSourceRead,RaphaelTimerSourceWrite,&Injected);
    DEBUG((DEBUG_INFO,"Timer source status=%lu reason=%lu polls=%lu writes=%lu\n",
      D->TimerSource.Status,D->TimerSource.Reason,D->TimerSource.Polls,D->TimerSource.WriteCalls));
    if(FixedPcdGetBool(PcdRaphaelIccFaultTest)) {
      if(!Injected||D->TimerSource.Status!=3||D->TimerSource.Reason!=3||D->TimerSource.WriteCalls!=5||
         (D->TimerSource.TrapEsr>>26)!=0||!D->TimerSource.TrapElr||
         ((D->TimerSource.RestoredCtl^D->TimerSource.OriginalCtl)&3)||
         D->TimerSource.RestoredCval!=D->TimerSource.OriginalCval)SecFinish(0x116);
    } else if(D->TimerSource.Status!=8)SecFinish(0x117);
  }
  if(FixedPcdGetBool(PcdRaphaelInputProbe)) {
    RaphaelCollectInputMap(Fdt,&D->Input,ReadDisplay32,NULL);
    DEBUG((DEBUG_INFO,"[raphael-sec] input status=%u version=0x%x reads=%u\n",D->Input.Status,D->Input.HardwareVersion,D->Input.ReadCount));
  }
  if(FixedPcdGetBool(PcdRaphaelInputRead)) {
    if(!FixedPcdGetBool(PcdRaphaelInputProbe))SecFinish(0x10a);
    RaphaelCollectKeyRegisters(&D->Input,(UINT32)D->Cntfrq,&D->Keys,ReadDisplay32,WritePixel32,ReadPixelCounter,NULL);
    DEBUG((DEBUG_INFO,"[raphael-sec] PMIC read status=%lu transactions=%lu completed=%lu\n",D->Keys.Status,D->Keys.Transactions,D->Keys.Completed));
  }
  if (FixedPcdGetBool (PcdRaphaelDisplayProbe)) {
    if ((!FixedPcdGetBool(PcdRaphaelExperimentalGop) &&
        FixedPcdGet32 (PcdRaphaelStopAfterStage) != 2) || (D->Sctlr & 0x1005)) SecFinish (0x106);
    RaphaelCollectDisplay (Fdt, &D->Display, ReadDisplay32, NULL);
    if (FixedPcdGetBool (PcdRaphaelSmmuProbe))
      RaphaelCollectSmmu (Fdt, &D->Display, ReadDisplay32, NULL);
    if (FixedPcdGetBool (PcdRaphaelPixelProbe)) {
      if (!FixedPcdGetBool (PcdRaphaelSmmuProbe)) SecFinish (0x107);
      RaphaelCollectPixels(Fdt,&D->Display,&D->Pixels,ReadDisplay32,ReadPixelCounter,(UINT32)D->Cntfrq,NULL);
      if (FixedPcdGetBool(PcdRaphaelPixelWrite)) {
        RaphaelTestPixelPatch(&D->Pixels,&D->PixelWrite,ReadDisplay32,WritePixel32,ReadPixelCounter,
          FixedPcdGet64(PcdRaphaelStackBase),FixedPcdGet32(PcdRaphaelStackSize),NULL);
        DEBUG((DEBUG_INFO,"RAPHAEL pixel patch status=%lu written=%lu verified=%lu restored=%lu\n",
          D->PixelWrite.Status,D->PixelWrite.Written,D->PixelWrite.Verified,D->PixelWrite.Restored));
      }
      DEBUG ((DEBUG_INFO,"RAPHAEL read-only pixels status=%u count=%u refresh=%u\n",
              D->Pixels.Status,D->Pixels.PixelCount,D->Pixels.RefreshCount));
    }
    DEBUG ((DEBUG_INFO, "RAPHAEL read-only display status=%lu samples=%lu\n", D->Display.Status, D->Display.Count));
  }
  if (FixedPcdGetBool(PcdRaphaelExperimentalGop)) {
    if (!FixedPcdGetBool(PcdRaphaelPixelProbe) || FixedPcdGetBool(PcdRaphaelPixelWrite)) SecFinish(0x108);
    D->Gop.Version=1; D->Gop.Status=1;
    if (RaphaelSplashRouteReady(Fdt,&D->Display,&D->Pixels)) {
      if (FixedPcdGetBool(PcdRaphaelSparseArena)) {
        ARM_MEMORY_REGION_DESCRIPTOR Output,Input;
        RAPHAEL_KERNEL_WINDOW *W=RaphaelKernelWindow();
        if (!RaphaelMapAndroidOutput(&Output)||!RaphaelMapAndroidReturn(&Input)||W->Status!=1) SecFinish(0x241);
        // The gap between the low Image and remote arena is not our memory.
        // Check every real occupied span, including the Android recovery data.
        RAPHAEL_FRAMEBUFFER_GUARD Guards[]={
          {Output.PhysicalBase,Output.Length},{Input.PhysicalBase,Input.Length},
          {Arena,End-Arena},{W->Base,W->Bytes},{D->X0,FdtTotalSize(Fdt)},
          {D->Sp&~4095ULL,4096},{D->Lr&~4095ULL,4096}
        };
        RaphaelFramebufferPlanRanges(&D->Pixels,Guards,ARRAY_SIZE(Guards),&D->Gop);
      } else RaphaelFramebufferPlan(&D->Pixels,Start,End,&D->Gop);
    }
  }
  if(FixedPcdGetBool(PcdRaphaelInputProtocol)) {
    RAPHAEL_KEY_TRANSPORT T;D->InputDxe.Version=1;D->InputDxe.Status=1;
    if(!FixedPcdGetBool(PcdRaphaelInputRead))SecFinish(0x10b);
    if(RaphaelKeyRegistersReady(&D->Keys)&&RaphaelKeyTransport(&D->Input,(UINT32)D->Cntfrq,&T)) {
      UINT64 A=T.PonObserver&~4095ULL,B=T.VolumeObserver&~4095ULL;
      if(B<A){UINT64 Swap=A;A=B;B=Swap;}
      D->InputDxe.MapBase0=A;D->InputDxe.MapBase1=B;D->InputDxe.MapCount=A==B?1:2;
      for(UINTN I=0;I<D->InputDxe.MapCount;++I) {
        UINT64 At=I?B:A;
        if((At<End&&At+4096>Start)||(D->Gop.Status==2&&At<D->Gop.MapBase+D->Gop.MapSize&&At+4096>D->Gop.MapBase))SecFinish(0x10c);
      }
      D->InputDxe.Status=2;
    }
  }
  if(FixedPcdGetBool(PcdRaphaelQemuArchTest)) {
    if(EFI_ERROR(RaphaelPrepareQemuArch(Fdt,D)))SecFinish(0x10f);
  }
  if (FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)) {
    if (!FixedPcdGetBool(PcdRaphaelTimerIrqTest) || FixedPcdGetBool(PcdRaphaelQemuArchTest) ||
        FixedPcdGetBool(PcdRaphaelTimerRouteFaultTest) || mTimerRoute.Status!=6 || !mTimerRoute.RestoreOk ||
        mTimerIrq.Status!=5 || mTimerIrq.Entries!=1 || mTimerIrq.EoiCount!=1 ||
        mGicEnableMap.Status!=3 || !mGicEnableMap.AllObservedDisabled) SecFinish(0x221);
    RAPHAEL_PHYSICAL_TIMER_RESULT *R=&mPhysicalTimer.Result;
    R->Version=1; R->Status=1;
    R->GicD=D->Gic.GicD; R->GicDBytes=D->Gic.GicDBytes; R->GicR=D->Gic.GicR; R->GicRBytes=D->Gic.GicRBytes;
    R->RdBase=D->Gic.Frames[D->Gic.BootIndex].Base; R->SgiBase=mTimerRoute.SgiBase;
    R->Intid=mTimerRoute.Intid; R->Flags=mTimerRoute.Flags; R->Frequency=mTimerRoute.Frequency;
    R->SavedDist=mTimerRoute.OriginalDist; R->SavedIgrpen=mTimerRoute.OriginalIgrpen;
    R->SavedCtl=mTimerRoute.OriginalCtl; R->SavedCval=mTimerRoute.OriginalCval;
    R->SavedDaif=mTimerRoute.DaifBefore; R->SavedEnable=mTimerRoute.EnabledBefore;
    R->SavedPending=mTimerRoute.PendingBefore; R->SavedActive=mTimerRoute.ActiveBefore;
    if (FixedPcdGetBool(PcdRaphaelPayloadTest)) {
      mPhysicalTimer.Manager.Version=1; mPhysicalTimer.Manager.Status=1;
      mPhysicalTimer.Manager.Frequency=D->Cntfrq; mPhysicalTimer.Manager.Timeout=FixedPcdGetBool(PcdRaphaelManagerKeys)?6:2;
    }
    R->SavedVctl=D->Icc.Values[RaphaelSysCntvCtl]; R->SavedVcval=D->Icc.Values[RaphaelSysCntvCval];
  }
  // Deliberate diagnostic stops distinguish SEC/FDT return, MMU return and
  // complete DXE dispatch on hardware. The phase is recorded before returning.
  if (FixedPcdGet32 (PcdRaphaelStopAfterStage) == 2) SecFinish (0);

  Hob = HobConstructor ((VOID *)(UINTN)Arena, ArenaSize,
                        (VOID *)(UINTN)Arena, (VOID *)(UINTN)(Arena + ArenaSize));
  SetHobList (Hob);
  ProcessLibraryConstructorList ();
  // Arena ownership is either the downloaded extension or the explicit
  // separate experimental boot grant. Every other byte stays reserved;
  // the active FDT/initrd holes never enter DXE heaps.
  UINT64 ResourceFlags=EFI_RESOURCE_ATTRIBUTE_PRESENT | EFI_RESOURCE_ATTRIBUTE_INITIALIZED |
      EFI_RESOURCE_ATTRIBUTE_TESTED | EFI_RESOURCE_ATTRIBUTE_WRITE_BACK_CACHEABLE;
  if(FixedPcdGetBool(PcdRaphaelNativeBoot)) {
    // Profile budgets only. Upper 20MiB is reserved SEC FAT backing.
    // Separate experimental staging uses 32MiB type bin plus 4MiB default headroom;
    // the original downloaded native profile retains its 24MiB type bin.
    UINT32 BinMiB=FixedPcdGetBool(PcdRaphaelSparseArena)?32U:24U;
    if (FixedPcdGetBool(PcdRaphaelSparseArena)) {
      if (ArenaSize!=56U*1024*1024 && ArenaSize!=72U*1024*1024 && ArenaSize!=320U*1024*1024) SecFinish(0x234);
    } else if (ArenaSize!=48U*1024*1024) SecFinish(0x234);
    BuildResourceDescriptorHob(EFI_RESOURCE_SYSTEM_MEMORY,ResourceFlags,Start,
        (FixedPcdGetBool(PcdRaphaelSparseArena)?FixedPcdGet64(PcdRaphaelDownloadedEnd):Arena)-Start);
    // PrePiHobLib lacks the WithOwner helper; emit the standard resource HOB.
    EFI_HOB_RESOURCE_DESCRIPTOR *Bin=CreateHob(EFI_HOB_TYPE_RESOURCE_DESCRIPTOR,sizeof(*Bin));
    if(!Bin)SecFinish(0x234);
    CopyGuid(&Bin->Owner,&gEfiMemoryTypeInformationGuid);Bin->ResourceType=EFI_RESOURCE_SYSTEM_MEMORY;
    Bin->ResourceAttribute=ResourceFlags;Bin->PhysicalStart=Arena;Bin->ResourceLength=ArenaSize-RAPHAEL_NATIVE_FAT_BYTES;
    BuildResourceDescriptorHob(EFI_RESOURCE_SYSTEM_MEMORY,ResourceFlags,
        Arena+ArenaSize-RAPHAEL_NATIVE_FAT_BYTES,End-(Arena+ArenaSize-RAPHAEL_NATIVE_FAT_BYTES));
    EFI_MEMORY_TYPE_INFORMATION Types[]={{EfiBootServicesData,EFI_SIZE_TO_PAGES(BinMiB*1024*1024)},{EfiMaxMemoryType,0}};
    BuildGuidDataHob(&gEfiMemoryTypeInformationGuid,Types,sizeof(Types));
  } else BuildResourceDescriptorHob(EFI_RESOURCE_SYSTEM_MEMORY,ResourceFlags,Start,End-Start);
  BuildMemoryAllocationHob (Start, (FixedPcdGetBool(PcdRaphaelSparseArena)?FixedPcdGet64(PcdRaphaelDownloadedEnd):Arena) - Start, EfiReservedMemoryType);
  BuildMemoryAllocationHob (Arena + ArenaSize, End - Arena - ArenaSize, EfiReservedMemoryType);
  if (FixedPcdGetBool (PcdRaphaelKernelWindow)) {
    RAPHAEL_KERNEL_WINDOW *W = RaphaelKernelWindow ();
    if (W->Status != 1) SecFinish (0x231);
    // Explicit experimental boot-policy admission. This core requires TESTED
    // to admit RAM; the bit is not evidence of an exhaustive DRAM test or the
    // absence of hidden firmware/DMA owners. Quarantine the complete run.
    BuildResourceDescriptorHob (EFI_RESOURCE_SYSTEM_MEMORY,
      EFI_RESOURCE_ATTRIBUTE_PRESENT | EFI_RESOURCE_ATTRIBUTE_INITIALIZED |
      EFI_RESOURCE_ATTRIBUTE_TESTED | EFI_RESOURCE_ATTRIBUTE_WRITE_BACK_CACHEABLE,
      W->Base, W->Bytes);
    BuildMemoryAllocationHob (W->Base, W->Bytes, EfiBootServicesData);
  }
  if (D->Gop.Status==2) {
    BuildResourceDescriptorHob(EFI_RESOURCE_MEMORY_RESERVED,
      EFI_RESOURCE_ATTRIBUTE_PRESENT | EFI_RESOURCE_ATTRIBUTE_INITIALIZED | EFI_RESOURCE_ATTRIBUTE_UNCACHEABLE,
      D->Gop.MapBase,D->Gop.MapSize);
    BuildMemoryAllocationHob(D->Gop.MapBase,D->Gop.MapSize,EfiReservedMemoryType);
  }
  if(D->InputDxe.Status==2)for(UINTN I=0;I<D->InputDxe.MapCount;++I) {
    UINT64 At=I?D->InputDxe.MapBase1:D->InputDxe.MapBase0;
    BuildResourceDescriptorHob(EFI_RESOURCE_MEMORY_MAPPED_IO,
      EFI_RESOURCE_ATTRIBUTE_PRESENT|EFI_RESOURCE_ATTRIBUTE_INITIALIZED|EFI_RESOURCE_ATTRIBUTE_UNCACHEABLE,At,4096);
    BuildMemoryAllocationHob(At,4096,EfiMemoryMappedIO);
  }
  if(FixedPcdGetBool(PcdRaphaelQemuArchTest)) {
    UINT64 Bases[2]={D->QemuArch.GicD,D->QemuArch.GicR};
    UINT64 Sizes[2]={D->QemuArch.GicDBytes,D->QemuArch.GicRBytes};
    for(UINTN I=0;I<2;++I) {
      BuildResourceDescriptorHob(EFI_RESOURCE_MEMORY_MAPPED_IO,EFI_RESOURCE_ATTRIBUTE_PRESENT|EFI_RESOURCE_ATTRIBUTE_INITIALIZED|EFI_RESOURCE_ATTRIBUTE_UNCACHEABLE,Bases[I],Sizes[I]);
      BuildMemoryAllocationHob(Bases[I],Sizes[I],EfiMemoryMappedIO);
    }
  }
  if (FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)) {
    RAPHAEL_PHYSICAL_TIMER_RESULT *R=&mPhysicalTimer.Result;
    UINT64 Bases[2]={R->GicD,R->GicR}, Sizes[2]={R->GicDBytes,R->GicRBytes};
    for (UINTN I=0;I<2;++I) {
      BuildResourceDescriptorHob(EFI_RESOURCE_MEMORY_MAPPED_IO,EFI_RESOURCE_ATTRIBUTE_PRESENT|EFI_RESOURCE_ATTRIBUTE_INITIALIZED|EFI_RESOURCE_ATTRIBUTE_UNCACHEABLE,Bases[I],Sizes[I]);
      BuildMemoryAllocationHob(Bases[I],Sizes[I],EfiMemoryMappedIO);
    }
    RAPHAEL_PHYSICAL_TIMER_STATE *State=&mPhysicalTimer;
    BuildGuidDataHob(&gRaphaelPhysicalTimerHobGuid,&State,sizeof(State));
  }
  if(FixedPcdGetBool(PcdRaphaelVisibleManager)) {
    RAPHAEL_MANAGER_UI_STATE *Ui=&mManagerUi;
    BuildGuidDataHob(&gRaphaelManagerUiHobGuid,&Ui,sizeof(Ui));
  }
  BuildCpuHob (ArmGetPhysicalAddressBits (), 0);
  BuildFvHob (FixedPcdGet64 (PcdRaphaelFdBase), FixedPcdGet32 (PcdRaphaelFdSize));
  BuildGuidDataHob (&gRaphaelDiagnosticHobGuid, &D, sizeof (D));
  if(FixedPcdGetBool(PcdRaphaelPayloadTest)&&EFI_ERROR(RaphaelPreparePayload(D)))SecFinish(0x10e);

  ZeroMem (Map, sizeof (Map));
  UINT64 MapStart=FixedPcdGetBool(PcdRaphaelAndroidReturn)?D->ImageBase:Start;
  Map[0].PhysicalBase = MapStart;
  Map[0].VirtualBase = MapStart;
  Map[0].Length = End - MapStart;
  Map[0].Attributes = ARM_MEMORY_REGION_ATTRIBUTE_WRITE_BACK;
  UINTN MapIndex=1;
  if(FixedPcdGetBool(PcdRaphaelSparseArena)){
    if(!RaphaelMapAndroidOutput(&Map[0])||!RaphaelMapAndroidReturn(&Map[1]))SecFinish(0x238);
    Map[2].PhysicalBase=Map[2].VirtualBase=Arena;
    Map[2].Length=End-Arena;Map[2].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_WRITE_BACK;
    // Leave every unrelated gap unmapped, including firmware reserved memory.
    for(UINTN I=0;I<3;++I)for(UINTN J=0;J<I;++J)
      if(Map[I].PhysicalBase<Map[J].PhysicalBase+Map[J].Length&&Map[J].PhysicalBase<Map[I].PhysicalBase+Map[I].Length)SecFinish(0x238);
    MapIndex=3;
  }
  if (FixedPcdGetBool (PcdRaphaelKernelWindow)) {
    RAPHAEL_KERNEL_WINDOW *W = RaphaelKernelWindow ();
    Map[MapIndex].PhysicalBase=Map[MapIndex].VirtualBase=W->Base;
    Map[MapIndex].Length=W->Bytes;
    Map[MapIndex++].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_WRITE_BACK;
  }
  if(FixedPcdGet64(PcdRaphaelNativeWatchdogBase)){
    UINT64 W=FixedPcdGet64(PcdRaphaelNativeWatchdogBase);INT32 Len=0;
    INT32 Node=FdtNodeOffsetByCompatible(Fdt,-1,"qcom,msm-watchdog");
    CONST UINT32 *Reg=Node<0?NULL:FdtGetProp(Fdt,Node,"reg",&Len);
    INT32 Parent=Node<0?-1:FdtParentOffset(Fdt,Node);
    // The stage-3 UFS-only profile also needs this mapping before preparing
    // its return capsule. It intentionally does not execute the XNU MMU test.
    BOOLEAN WatchdogProfile=FixedPcdGetBool(PcdRaphaelNativeMmuTest)||
      (FixedPcdGetBool(PcdRaphaelUfsRead)&&FixedPcdGetBool(PcdRaphaelAndroidReturn)&&
       (FixedPcdGet32(PcdRaphaelStopAfterStage)==3||FixedPcdGetBool(PcdRaphaelUfsPayload)));
    if(!WatchdogProfile||!Reg||Len!=8||Parent<0||
       FdtAddressCells(Fdt,Parent)!=1||FdtSizeCells(Fdt,Parent)!=1||SwapBytes32(Reg[0])!=W||SwapBytes32(Reg[1])!=4096||
       FdtNodeOffsetByCompatible(Fdt,Node,"qcom,msm-watchdog")!=-FDT_ERR_NOTFOUND)SecFinish(0x23e);
    // The current handset encodes identity translation as an explicit tuple.
    if(!RaphaelFdtRootIdentityRange(Fdt,Parent,W,4096)||
       (W&4095)||MapIndex>=ARRAY_SIZE(Map)-1)SecFinish(0x23e);
    DEBUG((DEBUG_INFO,"NATIVE watchdog resource accepted base=%lx bytes=4096\n",W));
    Map[MapIndex].PhysicalBase=Map[MapIndex].VirtualBase=W;Map[MapIndex].Length=4096;
    Map[MapIndex++].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_DEVICE;
    BuildResourceDescriptorHob(EFI_RESOURCE_MEMORY_MAPPED_IO,
      EFI_RESOURCE_ATTRIBUTE_PRESENT|EFI_RESOURCE_ATTRIBUTE_INITIALIZED|EFI_RESOURCE_ATTRIBUTE_UNCACHEABLE,W,4096);
    BuildMemoryAllocationHob(W,4096,EfiMemoryMappedIO);
  }
  if (D->Gop.Status==2) {
    Map[MapIndex].PhysicalBase=Map[MapIndex].VirtualBase=D->Gop.MapBase;
    Map[MapIndex].Length=D->Gop.MapSize;
    Map[MapIndex++].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_UNCACHED_UNBUFFERED;
  }
  if(D->InputDxe.Status==2)for(UINTN I=0;I<D->InputDxe.MapCount;++I) {
    Map[MapIndex].PhysicalBase=Map[MapIndex].VirtualBase=I?D->InputDxe.MapBase1:D->InputDxe.MapBase0;
    Map[MapIndex].Length=4096;Map[MapIndex++].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_DEVICE;
  }
  if(FixedPcdGetBool(PcdRaphaelQemuArchTest)) {
    if(MapIndex!=(FixedPcdGetBool(PcdRaphaelSparseArena)?3U:1U)+(FixedPcdGetBool(PcdRaphaelKernelWindow)?1U:0U)+(FixedPcdGet64(PcdRaphaelNativeWatchdogBase)?1U:0U))SecFinish(0x110);
    UINT64 Bases[2]={D->QemuArch.GicD,D->QemuArch.GicR};
    UINT64 Sizes[2]={D->QemuArch.GicDBytes,D->QemuArch.GicRBytes};
    for(UINTN I=0;I<2;++I) {
      if(MapIndex>=ARRAY_SIZE(Map)-1)SecFinish(0x110);
      for(UINTN J=0;J<MapIndex;++J)if(Bases[I]<Map[J].PhysicalBase+Map[J].Length&&Map[J].PhysicalBase<Bases[I]+Sizes[I])SecFinish(0x110);
      Map[MapIndex].PhysicalBase=Map[MapIndex].VirtualBase=Bases[I];Map[MapIndex].Length=Sizes[I];
      Map[MapIndex++].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_DEVICE;
    }
  }
  if (FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)) {
    RAPHAEL_PHYSICAL_TIMER_RESULT *R=&mPhysicalTimer.Result;
    UINT64 Bases[2]={R->GicD,R->GicR}, Sizes[2]={R->GicDBytes,R->GicRBytes};
    for (UINTN I=0;I<2;++I) {
      if (MapIndex>=ARRAY_SIZE(Map)-1 || !Sizes[I] || (Bases[I]&4095) || (Sizes[I]&4095)) SecFinish(0x222);
      for (UINTN J=0;J<MapIndex;++J) if (Bases[I]<Map[J].PhysicalBase+Map[J].Length && Map[J].PhysicalBase<Bases[I]+Sizes[I]) SecFinish(0x222);
      Map[MapIndex].PhysicalBase=Map[MapIndex].VirtualBase=Bases[I]; Map[MapIndex].Length=Sizes[I];
      Map[MapIndex++].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_DEVICE;
    }
  }
  if(FixedPcdGetBool(PcdRaphaelRamMappedProbe)){
    if(mRamMapped.Status!=1||MapIndex!=1||MapIndex>=ARRAY_SIZE(Map)-1)SecFinish(0x22d);
    Map[MapIndex].PhysicalBase=Map[MapIndex].VirtualBase=mRamRead.Base;
    Map[MapIndex].Length=mRamRead.Bytes;
    Map[MapIndex++].Attributes=ARM_MEMORY_REGION_ATTRIBUTE_WRITE_BACK_RO;
  }
  if(FixedPcdGetBool(PcdRaphaelAndroidReturn)&&!FixedPcdGetBool(PcdRaphaelSparseArena)){
    if(MapIndex>=ARRAY_SIZE(Map)-1||!RaphaelMapAndroidReturn(&Map[MapIndex]))SecFinish(0x236);
    for(UINTN I=0;I<MapIndex;++I)if(Map[MapIndex].PhysicalBase<Map[I].PhysicalBase+Map[I].Length&&Map[I].PhysicalBase<Map[MapIndex].PhysicalBase+Map[MapIndex].Length)SecFinish(0x236);
    ++MapIndex;
  }
  Status = ArmConfigureMmu (Map, &PageTable, &PageTableBytes);
  if (EFI_ERROR (Status)) SecFinish (0x104);
  D->PageTable = (UINTN)PageTable;
  D->PageTableBytes = PageTableBytes;
  D->MmuSctlr = ArmReadSctlr ();
  if(!RaphaelArmAndroidReturn(D))SecFinish(0x237);
  if(FixedPcdGetBool(PcdRaphaelUfsRead)){
    RAPHAEL_KERNEL_WINDOW *W=RaphaelKernelWindow();UINT64 Daif,Ctr;
    __asm__ volatile("mrs %0,daif":"=r"(Daif));
    __asm__ volatile("mrs %0,ctr_el0":"=r"(Ctr));
    // Ranges are page-aligned; every maintained cache line must fit a page.
    if((Daif&0xc0)!=0xc0||(4ULL<<((Ctr>>16)&15))>4096||W->Status!=1||W->Bytes<RPH_RETURN_TAIL_BYTES)SecFinish(0x240);
    mUfsUncachedRanges[0][0]=D->ExtentBase;mUfsUncachedRanges[0][1]=FixedPcdGet64(PcdRaphaelDownloadedEnd);
    mUfsUncachedRanges[1][0]=Arena;mUfsUncachedRanges[1][1]=End;
    mUfsUncachedRanges[2][0]=W->Base+W->Bytes-RPH_RETURN_TAIL_BYTES;mUfsUncachedRanges[2][1]=W->Base+W->Bytes;
    for(UINTN I=0;I<3;++I)if(mUfsUncachedRanges[I][1]<=mUfsUncachedRanges[I][0]||((mUfsUncachedRanges[I][0]|mUfsUncachedRanges[I][1])&4095))SecFinish(0x240);
    mUfsUncachedWords[0]=1;mUfsUncachedWords[1]=ArmReadSctlr();
    RaphaelCallUfsUncached(mUfsUncachedRanges,ExecuteUfsUncached);
    mUfsUncachedWords[3]=ArmReadSctlr();
    DEBUG((DEBUG_INFO,"UFS uncached before=%lx inside=%lx after=%lx callback=%lu stage=%lu\n",mUfsUncachedWords[1],mUfsUncachedWords[2],mUfsUncachedWords[3],mUfsUncachedWords[4],mUfsRead.Word[1]));
    if(mUfsUncachedWords[3]!=mUfsUncachedWords[1])SecFinish(0x240);
    if(FixedPcdGetBool(PcdRaphaelUfsPayload)){
      BOOLEAN Qemu=FixedPcdGetBool(PcdRaphaelAndroidReturnQemu);
      BOOLEAN Ready=Qemu||(mUfsRead.Word[0]==5&&mUfsRead.Word[1]==7&&mUfsRead.Word[18]==104&&mUfsRead.Word[20]==0&&!mUfsRead.Word[21]&&mUfsRead.Word[22]==1&&mUfsRead.Word[30]*4096==D->Payload.Bytes);
      D->Payload.CrcBefore=Ready&&RaphaelVerifyPayloadMemory(D->Payload.Base,D->Payload.Bytes);
      if(!Qemu&&Ready)mUfsRead.Word[18]=D->Payload.CrcBefore?0:105;
      DEBUG((DEBUG_INFO,Qemu?"UFS_PAYLOAD_MEMORY verified=%lu\n":"UFS_PAYLOAD_CACHED verified=%lu\n",D->Payload.CrcBefore));
    }
  }

  if(FixedPcdGetBool(PcdRaphaelPayloadTest)&&EFI_ERROR(RaphaelMaterializePayload(D)))SecFinish(0x235);
  if (FixedPcdGetBool (PcdRaphaelKernelWindow)) {
    RAPHAEL_KERNEL_WINDOW *W = RaphaelKernelWindow ();
    W->Status=2;
    BuildGuidDataHob (&gRaphaelKernelWindowHobGuid, W, sizeof (*W));
  }
  if (D->Gop.Status==2) {
    if (ReadDisplay32(D->Gop.Base,NULL)!=D->Pixels.Pixels[0] ||
        ReadDisplay32(D->Gop.Base+(D->Gop.Height-1)*D->Gop.Stride+(D->Gop.Width-1)*4,NULL)!=
          D->Pixels.Pixels[RAPHAEL_PIXEL_GRID*RAPHAEL_PIXEL_GRID-1]) SecFinish(0x109);
    D->Gop.MappedReadVerified=1; D->Gop.Status=3;
  }
  if(D->InputDxe.Status==2) {
    RAPHAEL_KEY_TRANSPORT T;
    if(!RaphaelKeyTransport(&D->Input,(UINT32)D->Cntfrq,&T)||
      (ReadDisplay32(T.PonObserver+8,NULL)&15)!=1||(ReadDisplay32(T.VolumeObserver+8,NULL)&15)!=1)SecFinish(0x10d);
    D->InputDxe.MappedReadVerified=1;D->InputDxe.Status=3;
  }
  if(FixedPcdGetBool(PcdRaphaelQemuArchTest))D->QemuArch.Status=2;
  if (FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)) {
    RAPHAEL_PHYSICAL_TIMER_RESULT *R=&mPhysicalTimer.Result;
    if (ReadDisplay32(R->GicD,NULL)!=R->SavedDist || ReadDisplay32(R->SgiBase+0x100,NULL)!=R->SavedEnable ||
        ReadDisplay32(R->SgiBase+0x300,NULL)!=R->SavedActive) SecFinish(0x223);
    R->MappedVerified=1; R->Status=2;
  }
  D->Stage = 3;
  DEBUG ((DEBUG_INFO, "RAPHAEL MMU enabled; HOB arena=0x%lx size=0x%lx\n", Arena, ArenaSize));
  if(FixedPcdGetBool(PcdRaphaelRamMappedProbe)){
    if(!RaphaelRunMappedRam(&mRamRead,&mRamMapped))SecFinish(0x22e);
    DEBUG((DEBUG_INFO,"RAM mapped reads=%lu translations=%lu denied=%lu digest=%lx\n",mRamMapped.Completed,mRamMapped.ReadTranslations,mRamMapped.WriteDenied,mRamMapped.Digest));
  }
  if(FixedPcdGet32(PcdRaphaelRamCacheWritePages)){
    if(!RaphaelRunRamCacheWrite(&mRamRead,&mRamMapped,&mRamCache,&mRamWrite,mRamBackup))SecFinish(0x230);
    DEBUG((DEBUG_INFO,"RAM cached write pages=%lu restored=%lu sync=%lu/%lu RO=%lu\n",mRamWrite.Result.CompletedPages,mRamWrite.Result.RestoredPages,mRamCache.Result.PrePageSync,mRamCache.Result.PostPageSync,mRamCache.Result.RestoreDenials));
  }
  if (FixedPcdGet32 (PcdRaphaelStopAfterStage) == 3) SecFinish (0);
  // Keep the externally reserved SEC stack. The experiment exits from the
  // diagnostic DXE before architectural protocols or a BDS boot manager exist.
  D->Stage = 4;
  Status = LoadDxeCoreFromFv (NULL, 0);
  DEBUG ((DEBUG_ERROR, "LoadDxeCoreFromFv returned: %r\n", Status));
  SecFinish (0x105);
}
