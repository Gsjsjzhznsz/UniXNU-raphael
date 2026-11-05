// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelDiagnostic.h>
#include <RaphaelKernelWindow.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/HobLib.h>
#include <Library/UefiBootServicesTableLib.h>

extern EFI_STATUS RaphaelTestPhysicalTimer(VOID);
extern EFI_STATUS RaphaelTestQemuTimer(RAPHAEL_DIAGNOSTIC *D);
extern EFI_STATUS RaphaelTestDarwin(EFI_HANDLE Image,RAPHAEL_DIAGNOSTIC *D);
extern EFI_STATUS RaphaelTestNativeStaging(VOID);
extern EFI_STATUS RaphaelTestPayload(EFI_HANDLE Image,RAPHAEL_DIAGNOSTIC *D);
extern EFI_STATUS RaphaelTestMenu(RAPHAEL_DIAGNOSTIC *D);
extern EFI_STATUS RaphaelTestGop(RAPHAEL_DIAGNOSTIC *D);
extern EFI_STATUS RaphaelPrepareNativeVideo(VOID);

STATIC BOOLEAN CheckTable (CONST EFI_TABLE_HEADER *Header) {
  UINT8 Buffer[sizeof (EFI_BOOT_SERVICES)];
  UINT32 Crc;
  if (Header->HeaderSize < sizeof (*Header) || Header->HeaderSize > sizeof (Buffer)) return FALSE;
  CopyMem (Buffer, Header, Header->HeaderSize);
  ((EFI_TABLE_HEADER *)Buffer)->CRC32 = 0;
  return !EFI_ERROR (gBS->CalculateCrc32 (Buffer, Header->HeaderSize, &Crc)) && Crc == Header->CRC32;
}

EFI_STATUS EFIAPI DiagnosticReturnEntry (EFI_HANDLE Handle, EFI_SYSTEM_TABLE *SystemTable) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic ();
  VOID *Hob = GetFirstGuidHob (&gRaphaelDiagnosticHobGuid);
  EFI_STATUS Status;
  UINTN Bytes = sizeof (D->Map), Key, Stride;
  UINT32 Version;
  EFI_PHYSICAL_ADDRESS Page = 0;
  UINT64 Arena = FixedPcdGet64 (PcdRaphaelArenaBase);
  UINT64 End = Arena + FixedPcdGet32 (PcdRaphaelArenaSize);
  (VOID)Handle;
  if (!Hob || GET_GUID_HOB_DATA_SIZE (Hob) != sizeof (D) ||
      *(RAPHAEL_DIAGNOSTIC **)GET_GUID_HOB_DATA (Hob) != D ||
      D->Magic != RAPHAEL_DIAG_MAGIC) return EFI_COMPROMISED_DATA;
  D->Stage = 5;
  D->SystemTableSignature = SystemTable->Hdr.Signature;
  D->BootServicesSignature = gBS->Hdr.Signature;
  D->SystemTableCrcOk = CheckTable (&SystemTable->Hdr);
  D->BootServicesCrcOk = CheckTable (&gBS->Hdr);
  // Exercise real DXE allocation, data access and release within the arena.
  Status = gBS->AllocatePages (AllocateAnyPages, EfiBootServicesData, 1, &Page);
  if (!EFI_ERROR (Status) && Page >= Arena && Page <= End - EFI_PAGE_SIZE) {
    SetMem ((VOID *)(UINTN)Page, EFI_PAGE_SIZE, 0x5a);
    D->AllocationProbeOk = *(volatile UINT64 *)(UINTN)Page == 0x5a5a5a5a5a5a5a5aULL;
    if (EFI_ERROR (gBS->FreePages (Page, 1))) D->AllocationProbeOk = 0;
  }
  if (FixedPcdGetBool(PcdRaphaelNativeVideo)) {
    Status = RaphaelPrepareNativeVideo();
    if (EFI_ERROR(Status)) ((RAPHAEL_FINISH)(UINTN)D->Finish)(0x23f);
  }
  if (FixedPcdGetBool(PcdRaphaelExperimentalGop) && !FixedPcdGetBool(PcdRaphaelNativeVideo) && !FixedPcdGetBool(PcdRaphaelVisibleManager) && D->Gop.Status!=1) {
    Status=RaphaelTestGop(D);
    if (EFI_ERROR(Status)) ((RAPHAEL_FINISH)(UINTN)D->Finish)(0x210);
  }
  if(FixedPcdGetBool(PcdRaphaelMenuTest) && D->Gop.Status!=1) {
    Status=RaphaelTestMenu(D);
    if(EFI_ERROR(Status))((RAPHAEL_FINISH)(UINTN)D->Finish)(0x211);
  }
  if(FixedPcdGetBool(PcdRaphaelPayloadTest)) {
    Status=RaphaelTestPayload(Handle,D);
    DEBUG((DEBUG_INFO,"RAPHAEL payload status=%lu block/ro/write/fs=%lu/%lu/%lu/%lu cfg=%lu/%lu run=%lu error=%r\n",D->Payload.Status,D->Payload.BlockIo,D->Payload.ReadOnly,D->Payload.WriteDenied,D->Payload.FileSystem,D->Payload.ConfigEntries,D->Payload.ConfigOk,D->Payload.RunCompleted,Status));
    if(EFI_ERROR(Status))((RAPHAEL_FINISH)(UINTN)D->Finish)(0x212);
  }
  if(FixedPcdGetBool(PcdRaphaelPhysicalTimerArch)) {
    Status=RaphaelTestPhysicalTimer();
    if(EFI_ERROR(Status))((RAPHAEL_FINISH)(UINTN)D->Finish)(0x225);
  }
  if(FixedPcdGetBool(PcdRaphaelQemuArchTest)) {
    Status=RaphaelTestQemuTimer(D);
    if(EFI_ERROR(Status))((RAPHAEL_FINISH)(UINTN)D->Finish)(0x214);
  }
  if(FixedPcdGetBool(PcdRaphaelDarwinTest) && !FixedPcdGetBool(PcdRaphaelNativeHandoff) && !FixedPcdGetBool(PcdRaphaelNativeLoadTest)) {
    Status=RaphaelTestDarwin(Handle,D);
    if(EFI_ERROR(Status))((RAPHAEL_FINISH)(UINTN)D->Finish)(0x213);
  }
  if (FixedPcdGetBool (PcdRaphaelKernelWindow)) {
    Status=RaphaelTestKernelWindow ();
    if (EFI_ERROR (Status)) ((RAPHAEL_FINISH)(UINTN)D->Finish)(0x232);
  }
  if(FixedPcdGetBool(PcdRaphaelNativeBoot)&&!FixedPcdGetBool(PcdRaphaelNativeHandoff)){
    Status=RaphaelTestNativeStaging();
    if(EFI_ERROR(Status))((RAPHAEL_FINISH)(UINTN)D->Finish)(0x239);
  }
  if(FixedPcdGetBool(PcdRaphaelNativeHandoff)||FixedPcdGetBool(PcdRaphaelNativeLoadTest)) {
    Status=RaphaelTestDarwin(Handle,D);
    if(EFI_ERROR(Status))((RAPHAEL_FINISH)(UINTN)D->Finish)(0x236);
  }
  Status = gBS->GetMemoryMap (&Bytes, (EFI_MEMORY_DESCRIPTOR *)D->Map, &Key, &Stride, &Version);
  if (EFI_ERROR (Status) || Stride < sizeof (EFI_MEMORY_DESCRIPTOR) || Bytes % Stride)
    ((RAPHAEL_FINISH)(UINTN)D->Finish)(0x201);
  D->MapKey = Key; D->MapBytes = Bytes; D->DescriptorSize = Stride; D->DescriptorVersion = Version;
  for (UINTN I = 0; I < Bytes; I += Stride) {
    EFI_MEMORY_DESCRIPTOR *M = (EFI_MEMORY_DESCRIPTOR *)(D->Map + I);
    if (FixedPcdGetBool (PcdRaphaelKernelWindow)) {
      VOID *WindowHob = GetFirstGuidHob (&gRaphaelKernelWindowHobGuid);
      if (!WindowHob || GET_GUID_HOB_DATA_SIZE (WindowHob) != sizeof (RAPHAEL_KERNEL_WINDOW))
        ((RAPHAEL_FINISH)(UINTN)D->Finish)(0x233);
      RAPHAEL_KERNEL_WINDOW *W = GET_GUID_HOB_DATA (WindowHob);
      if (W->Status == 4 && M->Type == EfiBootServicesData && M->PhysicalStart >= W->Base &&
          M->PhysicalStart < W->Base + W->Bytes &&
          M->NumberOfPages <= (W->Base + W->Bytes - M->PhysicalStart) / EFI_PAGE_SIZE) continue;
    }
    if (M->Type == EfiConventionalMemory || M->Type == EfiBootServicesCode ||
        M->Type == EfiBootServicesData || M->Type == EfiRuntimeServicesCode ||
        M->Type == EfiRuntimeServicesData) {
      if (M->NumberOfPages > MAX_UINT64 / EFI_PAGE_SIZE || M->PhysicalStart < Arena ||
          M->PhysicalStart > End || M->NumberOfPages * EFI_PAGE_SIZE > End - M->PhysicalStart)
        ++D->MapViolations;
    }
  }
  DEBUG ((DEBUG_INFO, "RAPHAEL DXE driver reached: ST/BS CRC=%lu/%lu map=%lu bytes violations=%lu alloc=%lu\n",
          D->SystemTableCrcOk, D->BootServicesCrcOk, D->MapBytes, D->MapViolations, D->AllocationProbeOk));
  D->Stage = 6;
  ((RAPHAEL_FINISH)(UINTN)D->Finish)(D->MapViolations || !D->SystemTableCrcOk ||
      !D->BootServicesCrcOk || !D->AllocationProbeOk ? 0x202 : 0);
  return EFI_ABORTED;
}
