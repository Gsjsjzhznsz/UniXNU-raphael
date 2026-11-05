// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelDiagnostic.h>
#include <Library/RaphaelGopLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/BaseLib.h>
#include <Library/DebugLib.h>
#include <Protocol/DevicePath.h>
STATIC RAPHAEL_GOP mGop;
STATIC struct {
  VENDOR_DEVICE_PATH Vendor;
  EFI_DEVICE_PATH_PROTOCOL End;
} mPath={
  {{HARDWARE_DEVICE_PATH,HW_VENDOR_DP,{sizeof(VENDOR_DEVICE_PATH),0}},
    {0xcfa29b17,0x2eed,0x4164,{0xbb,0xd0,0x42,0xb4,0x8b,0xcc,0xf1,0x05}}},
  {END_DEVICE_PATH_TYPE,END_ENTIRE_DEVICE_PATH_SUBTYPE,{sizeof(EFI_DEVICE_PATH_PROTOCOL),0}}
};
EFI_STATUS EFIAPI SplashGopEntry (EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable) {
  RAPHAEL_DIAGNOSTIC *D=RaphaelDiagnostic();
  (VOID)ImageHandle; (VOID)SystemTable;
  if (!FixedPcdGetBool(PcdRaphaelExperimentalGop) || D->Magic!=RAPHAEL_DIAG_MAGIC ||
      D->Gop.Status!=3 || !D->Gop.MappedReadVerified) return EFI_UNSUPPORTED;
  UINTN Size=0; EFI_STATUS Status=RaphaelGopConfigure(&mGop,&D->Gop,NULL,&Size);
  if (Status!=EFI_BUFFER_TOO_SMALL) return Status;
  VOID *Configure=AllocatePool(Size);
  if (!Configure) return EFI_OUT_OF_RESOURCES;
  Status=RaphaelGopConfigure(&mGop,&D->Gop,Configure,&Size);
  if (EFI_ERROR(Status)) { FreePool(Configure); return Status; }
  EFI_HANDLE Handle=NULL;
  Status=gBS->InstallMultipleProtocolInterfaces(&Handle,&gEfiGraphicsOutputProtocolGuid,
    &mGop.Protocol,&gEfiDevicePathProtocolGuid,&mPath,NULL);
  if (EFI_ERROR(Status)) { FreePool(Configure); return Status; }
  D->Gop.ProtocolInstalled=1; D->Gop.Status=4;
  DEBUG((DEBUG_INFO,"RAPHAEL inherited GOP %lux%lu stride=%lu NC base=0x%lx\n",
    D->Gop.Width,D->Gop.Height,D->Gop.Stride,D->Gop.Base));
  return EFI_SUCCESS;
}
