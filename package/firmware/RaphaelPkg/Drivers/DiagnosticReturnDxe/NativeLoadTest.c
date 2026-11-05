// SPDX-License-Identifier: BSD-2-Clause-Patent
// Default load test stops inside BeforeExitBootServices. The separate exit
// profile observes the real core return; neither profile branches into XNU.
#include <RaphaelDiagnostic.h>
#include <RaphaelKernelWindow.h>
#include <Library/BaseLib.h>
#include <Library/PrintLib.h>
#include <Library/DebugLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DxeServicesLib.h>
#include <Library/ArmLib.h>
#include <Library/HobLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <RaphaelNativeVideo.h>

STATIC UINT64 mVideo[6];
EFI_STATUS RaphaelPrepareNativeVideo(VOID) {
  if (!FixedPcdGetBool(PcdRaphaelNativeLoadTest) || !FixedPcdGetBool(PcdRaphaelExperimentalGop) ||
      FixedPcdGetBool(PcdRaphaelNativeHandoff) || FixedPcdGetBool(PcdRaphaelVisibleManager)) return EFI_UNSUPPORTED;
  EFI_GRAPHICS_OUTPUT_PROTOCOL *G = NULL;
  EFI_STATUS S = gBS->LocateProtocol(&gEfiGraphicsOutputProtocolGuid, NULL, (VOID **)&G);
  if (EFI_ERROR(S)) return S;
  S = RaphaelNativeVideoBegin(&RaphaelDiagnostic()->Gop, G, mVideo);
  if (!EFI_ERROR(S)) DEBUG((DEBUG_INFO,"NATIVE_VIDEO inherited base=%lx %lux%lu stride=%lu depth=%lu backed_up=1\n",
    mVideo[0],mVideo[3],mVideo[4],mVideo[2],mVideo[5]));
  return S;
}
STATIC RAPHAEL_NATIVE_LOAD_POLICY *mPolicy;
STATIC RAPHAEL_NATIVE_LOAD_RESULT mResult;
STATIC RAPHAEL_NATIVE_LOAD_SEGMENT *mSegments;
STATIC RAPHAEL_NATIVE_LOAD_TRUST *mTrust;
STATIC RAPHAEL_NATIVE_LOAD_TRUST *mRamdisk;
BOOLEAN RaphaelNativeHasData(VOID) {return mRamdisk != NULL;}
STATIC BOOLEAN Within(UINT64 At, UINT64 Bytes, UINT64 Base, UINT64 Length) {
  return At >= Base && At - Base <= Length && Bytes <= Length - (At - Base);
}
EFI_STATUS RaphaelPrepareNativeLoad(VOID) {
  EFI_GUID Guid = {0xd8588174,0xc45b,0x4308,{0x91,0x0f,0xad,0xd8,0xb5,0x10,0x70,0xb2}};
  VOID *Raw = NULL; UINTN Bytes = 0;
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic();
  VOID *Hob = GetFirstGuidHob(&gRaphaelKernelWindowHobGuid);
  if (!Hob || GET_GUID_HOB_DATA_SIZE(Hob) != sizeof(RAPHAEL_KERNEL_WINDOW)) return EFI_NOT_READY;
  RAPHAEL_KERNEL_WINDOW *W = GET_GUID_HOB_DATA(Hob);
  RAPHAEL_NATIVE_LOAD_RESULT *R = &mResult;
  R->Version = FixedPcdGetBool(PcdRaphaelNativeExitComplete) ? 2 : 1; R->Status = 1;
  if (FixedPcdGetBool(PcdRaphaelNativeEntryTest) && !FixedPcdGetBool(PcdRaphaelNativeExitComplete)) return EFI_UNSUPPORTED;
  if (FixedPcdGetBool(PcdRaphaelNativeExitComplete) &&
      !FixedPcdGetBool(PcdRaphaelPhysicalTimerArch) && !FixedPcdGetBool(PcdRaphaelQemuArchTest)) return EFI_UNSUPPORTED;
  if (!FixedPcdGetBool(PcdRaphaelNativeLoadTest) ||
      !FixedPcdGetBool(PcdRaphaelAndroidReturn) ||
      FixedPcdGetBool(PcdRaphaelNativeHandoff) || !W || W->Status != 4) return EFI_UNSUPPORTED;
  EFI_STATUS S = GetSectionFromAnyFv(&Guid, EFI_SECTION_RAW, 0, &Raw, &Bytes);
  if (EFI_ERROR(S)) return S;
  // Keep the policy in the separately granted arena throughout the callback.
  UINT64 Arena = FixedPcdGet64(PcdRaphaelArenaBase);
  UINT64 Heap = FixedPcdGet32(PcdRaphaelArenaSize) - RAPHAEL_NATIVE_FAT_BYTES;
  if (!Within((UINTN)Raw, Bytes, Arena, Heap) || Bytes < sizeof(*mPolicy)) return EFI_COMPROMISED_DATA;
  RAPHAEL_NATIVE_LOAD_POLICY *P = Raw;
  if (P->Magic != RAPHAEL_NATIVE_LOAD_MAGIC || (P->Version != 1 && P->Version != 2 && P->Version != 3) || !P->Count ||
      P->Count > RAPHAEL_NATIVE_LOAD_MAX_SEGMENTS ||
      Bytes != sizeof(*P) + P->Count * sizeof(*mSegments) + (P->Version == 3 ? 2*sizeof(*mTrust) : P->Version == 2 ? sizeof(*mTrust) : 0) ||
      P->PhysicalBase != W->Candidate || P->WindowBytes != W->WindowBytes ||
      P->VirtualBase != W->VirtualBase || P->VirtualEnd <= P->VirtualBase ||
      P->VirtualEnd - P->VirtualBase > P->WindowBytes - SIZE_2MB ||
      P->ArgsOffset != ALIGN_VALUE(P->VirtualEnd - P->VirtualBase, SIZE_16KB) ||
      !Within(P->ArgsOffset, EFI_PAGE_SIZE + P->TreeBytes, 0, P->WindowBytes - SIZE_2MB) ||
      !P->TreeBytes || P->TreeCrc > MAX_UINT32 || P->Frequency != D->Cntfrq ||
      P->Affinity != (D->Mpidr & 0xff00ffffffULL) ||
      P->Entry < P->VirtualBase || P->Entry >= P->VirtualEnd) return EFI_COMPROMISED_DATA;
  RAPHAEL_NATIVE_LOAD_SEGMENT *Segments = (VOID *)(P + 1);
  BOOLEAN Executable = FALSE;
  for (UINTN I = 0; I < P->Count; ++I) {
    RAPHAEL_NATIVE_LOAD_SEGMENT *T = &Segments[I];
    if (!T->Bytes || T->FileBytes > T->Bytes || T->Crc > MAX_UINT32 ||
        !Within(T->Offset, T->Bytes, 0, P->VirtualEnd - P->VirtualBase)) return EFI_COMPROMISED_DATA;
    for (UINTN J = 0; J < I; ++J)
      if (T->Offset < Segments[J].Offset + Segments[J].Bytes &&
          Segments[J].Offset < T->Offset + T->Bytes) return EFI_COMPROMISED_DATA;
    if ((T->Protection & 4) && P->Entry - P->VirtualBase >= T->Offset &&
        P->Entry - P->VirtualBase - T->Offset < T->FileBytes) Executable = TRUE;
  }
  if (!Executable) return EFI_COMPROMISED_DATA;
  RAPHAEL_NATIVE_LOAD_TRUST *Trust = P->Version >= 2 ? (VOID *)(Segments + P->Count) : NULL;
  RAPHAEL_NATIVE_LOAD_TRUST *Ramdisk = P->Version == 3 ? Trust + 1 : NULL;
  UINT64 SidecarStart = ALIGN_VALUE(P->ArgsOffset + EFI_PAGE_SIZE + P->TreeBytes, EFI_PAGE_SIZE);
  if (Ramdisk && (!Ramdisk->Bytes || Ramdisk->Bytes > SIZE_8MB || Ramdisk->Crc > MAX_UINT32 ||
      Ramdisk->Offset != SidecarStart || !Within(Ramdisk->Offset, Ramdisk->Bytes, 0, P->WindowBytes - SIZE_2MB) ||
      !Within(Ramdisk->AdtOffset, 16, 0, P->TreeBytes) || !(Ramdisk->AdtOffset + 16 <= Trust->AdtOffset || Trust->AdtOffset + 16 <= Ramdisk->AdtOffset))) return EFI_COMPROMISED_DATA;
  if (Trust && (!Trust->Bytes || Trust->Bytes > SIZE_16MB || Trust->Crc > MAX_UINT32 ||
      Trust->Offset != SidecarStart + (Ramdisk ? ALIGN_VALUE(Ramdisk->Bytes, EFI_PAGE_SIZE) : 0) ||
      !Within(Trust->Offset, Trust->Bytes, 0, P->WindowBytes - SIZE_2MB) ||
      !Within(Trust->AdtOffset, 16, 0, P->TreeBytes))) return EFI_COMPROMISED_DATA;
  mPolicy = P; mSegments = Segments; mTrust = Trust; mRamdisk = Ramdisk;
  if(FixedPcdGetBool(PcdRaphaelNativeMmuTest))return RaphaelPrepareNativeMmu();
  return EFI_SUCCESS;
}
BOOLEAN RaphaelNativeEntryRange(UINT64 Address,UINT64 Bytes) {
  if(!mPolicy||!mSegments||Address<mPolicy->PhysicalBase)return FALSE;
  UINT64 Offset=Address-mPolicy->PhysicalBase;
  for(UINTN I=0;I<mPolicy->Count;++I)
    if((mSegments[I].Protection&4)&&Within(Offset,Bytes,mSegments[I].Offset,mSegments[I].FileBytes))return TRUE;
  return FALSE;
}
UINT64 RaphaelNativePhysical(UINT64 Virtual) {
  if(!mPolicy||Virtual<mPolicy->VirtualBase||Virtual>=mPolicy->VirtualEnd)return 0;
  return mPolicy->PhysicalBase+Virtual-mPolicy->VirtualBase;
}
BOOLEAN RaphaelNativeMemoryRange(UINT64 Address,UINT64 Bytes) {
  if(!mPolicy||Address<mPolicy->PhysicalBase)return FALSE;
  UINT64 Offset=Address-mPolicy->PhysicalBase;
  for(UINTN I=0;I<mPolicy->Count;++I)if(Within(Offset,Bytes,mSegments[I].Offset,mSegments[I].Bytes))return TRUE;
  return FALSE;
}
BOOLEAN RaphaelNativeBackupRange(UINT64 Address,UINT64 Bytes,UINT64 FileBytes,BOOLEAN Reclaimed) {
 if(!mPolicy||!mSegments||Address<mPolicy->PhysicalBase)return FALSE;
 for(UINTN I=0;I<mPolicy->Count;++I)if(Address-mPolicy->PhysicalBase==mSegments[I].Offset&&Bytes==mSegments[I].Bytes&&FileBytes==mSegments[I].FileBytes&&(!(mSegments[I].Protection&4)||(Reclaimed&&Bytes==SIZE_16KB)))return TRUE;
 return FALSE;
}
STATIC BOOLEAN ValidateLoaded(RAPHAEL_DIAGNOSTIC *D) {
  RAPHAEL_NATIVE_LOAD_POLICY *P = mPolicy;
  RAPHAEL_NATIVE_LOAD_RESULT *R = &mResult;
  if (!P || !mSegments) return FALSE;
  R->FileSegmentsOk=0; R->ZeroSegmentsOk=0;
  UINT64 Base = P->PhysicalBase, ArgsAt = Base + P->ArgsOffset;
  CONST UINT8 *A = (VOID *)(UINTN)ArgsAt;
  UINT64 TreeAt = ArgsAt + EFI_PAGE_SIZE;
  R->PhysicalBase = Base; R->Args = ArgsAt; R->Tree = TreeAt;
  R->Entry = Base + P->Entry - P->VirtualBase; R->WindowBytes = P->WindowBytes;
  R->SegmentCount = P->Count; R->Frequency = ArmReadCntFrq();
  R->Affinity = D->Mpidr & 0xff00ffffffULL;
  // Darwin23 boot_args ABI, pinned BootArgs.h and Apple boot.h are audited
  // separately. Unaligned reads avoid casting a packed ABI to a native struct.
  CHAR8 ExpectedArgs[96];
  if(FixedPcdGet32(PcdRaphaelNativeKallocZones))AsciiSPrint(ExpectedArgs,sizeof(ExpectedArgs),"-v keepsyms=1 cpus=1 kt_fixed_zones=%u",FixedPcdGet32(PcdRaphaelNativeKallocZones));
  else AsciiStrCpyS(ExpectedArgs,sizeof(ExpectedArgs),"-v keepsyms=1 cpus=1");
  R->ArgsOk = ReadUnaligned16((VOID *)A) == 2 && ReadUnaligned16((VOID *)(A+2)) == 2 &&
    ReadUnaligned64((VOID *)(A+8)) == P->VirtualBase &&
    ReadUnaligned64((VOID *)(A+16)) == Base &&
    ReadUnaligned64((VOID *)(A+24)) == P->WindowBytes &&
    ReadUnaligned64((VOID *)(A+0x478)) == P->WindowBytes &&
    ReadUnaligned64((VOID *)(A+0x60)) == P->VirtualBase + TreeAt - Base &&
    ReadUnaligned32((VOID *)(A+0x68)) == P->TreeBytes &&
    ReadUnaligned64((VOID *)(A+32)) >= TreeAt + P->TreeBytes &&
    ReadUnaligned64((VOID *)(A+32)) <= Base + P->WindowBytes - SIZE_2MB &&
    CompareMem(A+0x6c,ExpectedArgs,AsciiStrSize(ExpectedArgs)) == 0;
  // Default profile remains headless (mVideo is zero). Native-video must
  // match the independently captured, same-entry GOP contract exactly.
  if (FixedPcdGetBool(PcdRaphaelNativeVideo) && (!mVideo[0] || !D->Gop.Active || !D->Gop.Backup)) R->ArgsOk = 0;
  if (!RaphaelNativeVideoMatches(A,mVideo)) R->ArgsOk = 0;
  DEBUG((DEBUG_INFO,"NATIVE_VIDEO args_match=%lu base=%lx %lux%lu stride=%lu depth=%lu\n",
    (UINT64)R->ArgsOk,ReadUnaligned64((VOID *)(A+0x28)),ReadUnaligned64((VOID *)(A+0x40)),
    ReadUnaligned64((VOID *)(A+0x48)),ReadUnaligned64((VOID *)(A+0x38)),ReadUnaligned64((VOID *)(A+0x50))));
  for (UINTN I = 0; I < P->Count; ++I) {
    RAPHAEL_NATIVE_LOAD_SEGMENT *T = &mSegments[I];
    CONST UINT8 *Data = (VOID *)(UINTN)(Base + T->Offset);
    if (CalculateCrc32((VOID *)Data, T->FileBytes) == T->Crc) ++R->FileSegmentsOk;
    BOOLEAN Zero = TRUE;
    for (UINTN J = T->FileBytes; J < T->Bytes; ++J) if (Data[J]) { Zero = FALSE; break; }
    if (Zero) ++R->ZeroSegmentsOk;
  }
  R->TreeCrc = CalculateCrc32((VOID *)(UINTN)TreeAt, P->TreeBytes);
  BOOLEAN TrustOk = TRUE;
  if (mTrust) {
    UINT64 TrustAt = Base + mTrust->Offset;
    TrustOk = CalculateCrc32((VOID *)(UINTN)TrustAt, mTrust->Bytes) == mTrust->Crc &&
      ReadUnaligned64((VOID *)(UINTN)(TreeAt + mTrust->AdtOffset)) == TrustAt &&
      ReadUnaligned64((VOID *)(UINTN)(TreeAt + mTrust->AdtOffset + 8)) == mTrust->Bytes;
  }
  BOOLEAN RamdiskOk = TRUE;
  if (mRamdisk) {
    UINT64 At = Base + mRamdisk->Offset;
    RamdiskOk = CalculateCrc32((VOID *)(UINTN)At, mRamdisk->Bytes) == mRamdisk->Crc &&
      ReadUnaligned64((VOID *)(UINTN)(TreeAt + mRamdisk->AdtOffset)) == At &&
      ReadUnaligned64((VOID *)(UINTN)(TreeAt + mRamdisk->AdtOffset + 8)) == mRamdisk->Bytes;
  }
  return RamdiskOk && TrustOk && R->ArgsOk && R->FileSegmentsOk == P->Count && R->ZeroSegmentsOk == P->Count &&
    R->TreeCrc == P->TreeCrc && R->Frequency == P->Frequency && R->Affinity == P->Affinity;
}
VOID RaphaelNativeLoadNotice(VOID) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic();
  RAPHAEL_NATIVE_LOAD_RESULT *R = &mResult;
  if (FixedPcdGetBool(PcdRaphaelNativeExitComplete)) { ++R->ExitNoticeCount; return; }
  ArmDisableInterrupts();
  D->NativeLoadResult = (UINTN)R;
  ++R->ExitNoticeCount; R->Status = 2;
  BOOLEAN Valid = R->ExitNoticeCount == 1 && ValidateLoaded(D);
  R->Status = Valid ? 3 : 2; R->Error = Valid ? 0 : 1;
  D->Stage = 7;
  // SEC serializes into our FDT and enters the pre-armed high Android capsule.
  // No BootServices calls occur here. The core has not shut down its timer
  // or terminated the memory map; this callback never returns to the core.
  ((RAPHAEL_FINISH)(UINTN)D->Finish)(Valid ? 0 : 0x23a);
  CpuDeadLoop();
}

BOOLEAN RaphaelNativeExitReturned(EFI_STATUS Status, EFI_SYSTEM_TABLE *SystemTable, EFI_BOOT_SERVICES *OldServices) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic();
  RAPHAEL_NATIVE_LOAD_RESULT *R = &mResult;
  ArmDisableInterrupts();
  D->NativeLoadResult = (UINTN)R;
  BOOLEAN Valid = R->Version == 2 && R->ExitNoticeCount == 1 && Status == EFI_SUCCESS &&
    SystemTable->BootServices == NULL && SystemTable->ConOut == NULL && SystemTable->ConIn == NULL;
  // The fixed Mu core zeroes the original table before returning success.
  CONST UINT8 *Bytes = (VOID *)OldServices;
  for (UINTN I = 0; I < sizeof(*OldServices); ++I) if (Bytes[I]) Valid = FALSE;
  Valid = ValidateLoaded(D) && Valid;
  R->Status = Valid ? 4 : 2; R->Error = Valid ? 0 : (Status ? Status : 1);
  D->Stage = 8;
  if(Valid&&FixedPcdGetBool(PcdRaphaelNativeEntryTest)) {
    EFI_STATUS Armed=RaphaelNativeWatchdogArm();
    if(!EFI_ERROR(Armed))Armed=RaphaelArmNativeEntry(R->Entry,R->Args);
    if(!EFI_ERROR(Armed))return TRUE;
    RaphaelNativeWatchdogStop();
    Valid=FALSE;R->Status=2;R->Error=Armed;
  }
  ((RAPHAEL_FINISH)(UINTN)D->Finish)(Valid ? 0 : 0x23b);
  CpuDeadLoop();
  return FALSE;
}

VOID RaphaelNativeEntryFinish(BOOLEAN Valid) {
  RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();
  Valid=RaphaelNativeWatchdogStop()&&Valid;
  Valid=ValidateLoaded(D)&&Valid;
  RAPHAEL_NATIVE_ENTRY_RESULT *R=(VOID *)(UINTN)D->NativeEntryResult;
  R->Status=Valid?3:2;R->Error=Valid?0:2;
  D->Stage=9;
  ((RAPHAEL_FINISH)(UINTN)D->Finish)(Valid?0:0x23c);
  CpuDeadLoop();
}

VOID RaphaelNativeMmuFinish(BOOLEAN Valid) {
  RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();Valid=ValidateLoaded(D)&&Valid;
  RAPHAEL_NATIVE_MMU_RESULT *R=(VOID *)(UINTN)D->NativeMmuResult;
  R->SegmentsOk=mResult.FileSegmentsOk;R->ZeroOk=mResult.ZeroSegmentsOk;
  R->Status=Valid?3:2;R->Error=Valid?0:2;D->Stage=FixedPcdGetBool(PcdRaphaelNativePlatformTest)?13:FixedPcdGetBool(PcdRaphaelNativePmapTest)?12:FixedPcdGetBool(PcdRaphaelNativeEarlyTest)?11:10;
  ((RAPHAEL_FINISH)(UINTN)D->Finish)(Valid?0:0x23d);CpuDeadLoop();
}
