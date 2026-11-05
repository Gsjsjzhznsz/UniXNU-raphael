// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <PayloadFixture.h>
#include <Protocol/LoadedImage.h>
#include <Library/BaseLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <../Library/UniXNULib/Internal.h>
EFI_STATUS EFIAPI PayloadProbeEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *Table) {
  EFI_GUID Guid=FIXTURE_GUID;FIXTURE_RESULT *R=NULL;EFI_LOADED_IMAGE_PROTOCOL *L=NULL;
  EFI_STATUS S=gBS->LocateProtocol(&Guid,NULL,(VOID **)&R);
  if(EFI_ERROR(S)||!R||R->Magic!=FIXTURE_MAGIC)return EFI_UNSUPPORTED;
  S=gBS->HandleProtocol(Image,&gEfiLoadedImageProtocolGuid,(VOID **)&L);
  if(EFI_ERROR(S)||!L)return EFI_COMPROMISED_DATA;
  ++R->Calls;R->OptionsOk=L->LoadOptions&&L->LoadOptionsSize==StrSize(L"raphael-fixture-only")&&StrCmp(L->LoadOptions,L"raphael-fixture-only")==0;
  R->ParentOk=L->ParentHandle==R->Parent&&Table==gST&&gBS->Hdr.Signature==EFI_BOOT_SERVICES_SIGNATURE;
  UniXNULogInit();UniXNULog("PAYLOAD_PROBE_ENTER calls=%lu options=%lu parent=%lu",R->Calls,R->OptionsOk,R->ParentOk);
  return R->OptionsOk&&R->ParentOk?EFI_SUCCESS:EFI_COMPROMISED_DATA;
}
