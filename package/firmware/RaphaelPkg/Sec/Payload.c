// SPDX-License-Identifier: BSD-2-Clause-Patent
// Read-only payload in our FV; native FAT is split to avoid extended FFS sizes.
#include <RaphaelDiagnostic.h>
#include <Library/PrePiLib.h>
#include <Library/FdtLib.h>
#include <Library/HobLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/BaseMemoryLib.h>
#include <Pi/PiFirmwareFile.h>
STATIC VOID *mPart[2];
STATIC EFI_STATUS FindRaw(EFI_GUID *Guid, UINTN Expected, VOID **Data) {
 EFI_PEI_FILE_HANDLE File;EFI_STATUS S;
 UINT64 Base=FixedPcdGet64(PcdRaphaelFdBase),Size=FixedPcdGet32(PcdRaphaelFdSize);
 S=FfsFindFileByName(Guid,(VOID *)(UINTN)Base,&File);if(EFI_ERROR(S))return S;
 S=FfsFindSectionData(EFI_SECTION_RAW,File,Data);if(EFI_ERROR(S))return S;
 UINT64 Address=(UINTN)*Data;
 if(Address<Base+4||Address>Base+Size||Expected>Base+Size-Address)return EFI_COMPROMISED_DATA;
 EFI_COMMON_SECTION_HEADER *Header=(VOID *)((UINT8 *)*Data-sizeof(*Header));
 UINT32 Length=Header->Size[0]|(Header->Size[1]<<8)|(Header->Size[2]<<16);
 return Header->Type==EFI_SECTION_RAW&&Length==sizeof(*Header)+Expected?EFI_SUCCESS:EFI_COMPROMISED_DATA;
}
EFI_STATUS RaphaelPreparePayload(RAPHAEL_DIAGNOSTIC *D) {
 EFI_GUID Guid=RAPHAEL_PAYLOAD_GUID,Second=RAPHAEL_PAYLOAD_PART1_GUID;
 EFI_GUID Entry={0xDAEE82E6,0x8090,0x4E72,{0xBF,0xB9,0x78,0xC1,0x3C,0xD4,0xE3,0x59}};
 VOID *Data=NULL,*Fdt;EFI_STATUS S;UINTN Bytes=RAPHAEL_DIAGNOSTIC_FAT_BYTES;
 if(FixedPcdGetBool(PcdRaphaelNativeBoot)) {
  Bytes=RAPHAEL_NATIVE_FAT_BYTES;
  if(FixedPcdGetBool(PcdRaphaelUfsPayload)) {
   if(!FixedPcdGetBool(PcdRaphaelUfsRead)||!FixedPcdGetBool(PcdRaphaelUfsExtents)||Bytes<20*1024*1024||Bytes>160*1024*1024||(Bytes&4095))return EFI_UNSUPPORTED;
  } else {
   if(Bytes!=20*1024*1024)return EFI_UNSUPPORTED;
   S=FindRaw(&Guid,RAPHAEL_NATIVE_PART_BYTES,&mPart[0]);if(EFI_ERROR(S))return S;
   S=FindRaw(&Second,RAPHAEL_NATIVE_PART_BYTES,&mPart[1]);if(EFI_ERROR(S))return S;
  }
  // First page allocation in SEC. Keep the FAT above the separate DXE bin
  // resource, so neither it nor the loader's file buffer fragments kernel RAM.
  Data=AllocatePages(EFI_SIZE_TO_PAGES(Bytes));if(!Data)return EFI_OUT_OF_RESOURCES;
  UINT64 End=FixedPcdGet64(PcdRaphaelArenaBase)+FixedPcdGet32(PcdRaphaelArenaSize);
  if((UINTN)Data!=End-Bytes)return EFI_COMPROMISED_DATA;
 } else {S=FindRaw(&Guid,Bytes,&Data);if(EFI_ERROR(S))return S;}
 Fdt=AllocateZeroPool(4096);if(!Fdt)return EFI_OUT_OF_RESOURCES;
 if(FdtCreateEmptyTree(Fdt,4096))return EFI_COMPROMISED_DATA;
 INT32 Chosen=FdtAddSubnode(Fdt,0,"chosen");if(Chosen<0)return EFI_COMPROMISED_DATA;
 UINT64 Address=(UINTN)Data;
 if(FdtSetPropU64(Fdt,Chosen,"linux,initrd-start",Address)||FdtSetPropU64(Fdt,Chosen,"linux,initrd-end",Address+Bytes))return EFI_COMPROMISED_DATA;
 UINT64 Ptr=(UINTN)Fdt;if(!BuildGuidDataHob(&Entry,&Ptr,sizeof(Ptr)))return EFI_OUT_OF_RESOURCES;
 D->Payload.Base=Address;D->Payload.Bytes=Bytes;D->Payload.Fdt=Ptr;
 D->Payload.HobPresent=1;D->Payload.Status=2;return EFI_SUCCESS;
}
EFI_STATUS RaphaelMaterializePayload(RAPHAEL_DIAGNOSTIC *D) {
 if(!FixedPcdGetBool(PcdRaphaelNativeBoot))return EFI_SUCCESS;
 if(FixedPcdGetBool(PcdRaphaelUfsPayload))return D->Payload.Status==2&&D->Payload.CrcBefore==1?EFI_SUCCESS:EFI_NOT_READY;
 if(!mPart[0]||!mPart[1]||D->Payload.Status!=2||D->Payload.Bytes!=RAPHAEL_NATIVE_FAT_BYTES)return EFI_NOT_READY;
 for(UINTN I=0;I<2;++I)CopyMem((VOID *)(UINTN)(D->Payload.Base+I*RAPHAEL_NATIVE_PART_BYTES),mPart[I],RAPHAEL_NATIVE_PART_BYTES);
 return EFI_SUCCESS;
}
