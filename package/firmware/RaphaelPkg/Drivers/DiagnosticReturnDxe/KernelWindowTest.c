// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelDiagnostic.h>
#include <RaphaelKernelWindow.h>
#include <RaphaelAndroidReturn.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/HobLib.h>
#include <Library/UefiBootServicesTableLib.h>

// Use an existing fixed buffer: observing the map must not allocate in the run.
STATIC BOOLEAN HasType (UINT64 Base, UINT64 Bytes, UINT32 Type) {
  RAPHAEL_DIAGNOSTIC *D = RaphaelDiagnostic ();
  UINTN Size = sizeof (D->Map), Key, Stride;
  UINT32 Version;
  UINT64 End = Base + Bytes, At = Base;
  if (EFI_ERROR (gBS->GetMemoryMap (&Size, (VOID *)D->Map, &Key, &Stride, &Version)) ||
      Stride < sizeof (EFI_MEMORY_DESCRIPTOR) || Size % Stride) return FALSE;
  while (At < End) {
    UINT64 Next = At;
    for (UINTN I=0; I<Size; I+=Stride) {
      EFI_MEMORY_DESCRIPTOR *M = (VOID *)(D->Map + I);
      if (M->NumberOfPages > MAX_UINT64 / EFI_PAGE_SIZE ||
          M->PhysicalStart > MAX_UINT64 - EFI_PAGES_TO_SIZE (M->NumberOfPages)) return FALSE;
      UINT64 Limit = M->PhysicalStart + EFI_PAGES_TO_SIZE (M->NumberOfPages);
      if (M->PhysicalStart <= At && At < Limit) {
        if (M->Type != Type) return FALSE;
        Next = MIN (End, Limit); break;
      }
    }
    if (Next == At) return FALSE;
    At = Next;
  }
  return TRUE;
}

STATIC UINT64 Releasable(RAPHAEL_KERNEL_WINDOW *W) {
 if(!FixedPcdGetBool(PcdRaphaelAndroidReturn))return W->Bytes;
 VOID *Hob=GetFirstGuidHob(&gRaphaelAndroidReturnHobGuid);
 if(!Hob||GET_GUID_HOB_DATA_SIZE(Hob)!=sizeof(UINT64)||W->Bytes<RPH_RETURN_TAIL_BYTES)return 0;
 UINT64 High=W->Base+W->Bytes-RPH_RETURN_TAIL_BYTES,At=*(UINT64 *)GET_GUID_HOB_DATA(Hob);
 if(At!=High+RPH_RETURN_STUB_MAX||W->Candidate>High||W->WindowBytes>High-W->Candidate)return 0;
 struct rph_return_state *S=(VOID *)(UINTN)At;
 if(S->Magic!=RPH_RETURN_STATE_MAGIC||S->Version!=RPH_RETURN_STATE_VERSION||S->Armed!=1||S->HighBase!=High||S->HighEnd!=High+RPH_RETURN_TAIL_BYTES||
    !HasType(High,RPH_RETURN_TAIL_BYTES,EfiBootServicesData))return 0;
 return W->Bytes-RPH_RETURN_TAIL_BYTES;
}

EFI_STATUS RaphaelTestKernelWindow (VOID) {
  VOID *Hob = GetFirstGuidHob (&gRaphaelKernelWindowHobGuid);
  RAPHAEL_KERNEL_WINDOW *W;
  EFI_PHYSICAL_ADDRESS Address;
  EFI_STATUS Status;
  if (!Hob || GET_GUID_HOB_DATA_SIZE (Hob) != sizeof (*W)) return EFI_NOT_READY;
  W = GET_GUID_HOB_DATA (Hob);
  if (W->Version != 1 || W->Status != 2) return EFI_COMPROMISED_DATA;
  UINT64 Bytes=Releasable(W);if(!Bytes)return EFI_NOT_READY;
  W->ReservedMapOk = HasType (W->Base, W->Bytes, EfiBootServicesData);
  if (!W->ReservedMapOk) return EFI_COMPROMISED_DATA;
  Status = gBS->FreePages (W->Base, EFI_SIZE_TO_PAGES (Bytes));
  if (EFI_ERROR (Status)) { W->Error=Status; return Status; }
  W->Status = 3;
  W->ReleasedMapOk = HasType (W->Base, Bytes, EfiConventionalMemory);
  Address = W->Candidate;
  // Same AllocateAddress/type/count and low-21-bit constraint as pinned DarwinBoot.
  Status = W->ReleasedMapOk ? gBS->AllocatePages (AllocateAddress, EfiLoaderCode,
      EFI_SIZE_TO_PAGES (W->WindowBytes), &Address) : EFI_COMPROMISED_DATA;
  if (!EFI_ERROR (Status)) {
    W->AllocatedMapOk = Address == W->Candidate && HasType (Address, W->WindowBytes, EfiLoaderCode);
    Status = gBS->FreePages (Address, EFI_SIZE_TO_PAGES (W->WindowBytes));
  }
  W->Error = Status;
  Address = W->Base;
  EFI_STATUS Restore = gBS->AllocatePages (AllocateAddress, EfiBootServicesData,
      EFI_SIZE_TO_PAGES (Bytes), &Address);
  W->RestoredMapOk = !EFI_ERROR (Restore) && Address == W->Base && HasType (W->Base, W->Bytes, EfiBootServicesData);
  if (W->ReleasedMapOk && W->AllocatedMapOk && W->RestoredMapOk && !EFI_ERROR (Status)) W->Status=4;
  DEBUG ((DEBUG_INFO, "KERNEL_WINDOW lifecycle status=%lu reserved=%lu released=%lu allocated=%lu restored=%lu error=%lx\n",
    W->Status,W->ReservedMapOk,W->ReleasedMapOk,W->AllocatedMapOk,W->RestoredMapOk,W->Error));
  return W->Status == 4 ? EFI_SUCCESS : EFI_DEVICE_ERROR;
}

// Loader preparation: expose the quarantined run only immediately before the
// unmodified loader. On refusal, demand full restoration; fragmentation fails.
EFI_STATUS RaphaelReleaseKernelWindow(VOID) {
 VOID *Hob=GetFirstGuidHob(&gRaphaelKernelWindowHobGuid);
 if(!Hob||GET_GUID_HOB_DATA_SIZE(Hob)!=sizeof(RAPHAEL_KERNEL_WINDOW))return EFI_NOT_READY;
 RAPHAEL_KERNEL_WINDOW *W=GET_GUID_HOB_DATA(Hob);
 if(W->Status!=4||!HasType(W->Base,W->Bytes,EfiBootServicesData))return EFI_NOT_READY;
 UINT64 Bytes=Releasable(W);if(!Bytes)return EFI_NOT_READY;
 EFI_STATUS S=gBS->FreePages(W->Base,EFI_SIZE_TO_PAGES(Bytes));
 if(!EFI_ERROR(S)&&!HasType(W->Base,Bytes,EfiConventionalMemory))S=EFI_COMPROMISED_DATA;
 if(!EFI_ERROR(S))W->Status=5;
 return S;
}
EFI_STATUS RaphaelRestoreKernelWindow(VOID) {
 VOID *Hob=GetFirstGuidHob(&gRaphaelKernelWindowHobGuid);
 if(!Hob||GET_GUID_HOB_DATA_SIZE(Hob)!=sizeof(RAPHAEL_KERNEL_WINDOW))return EFI_NOT_READY;
 RAPHAEL_KERNEL_WINDOW *W=GET_GUID_HOB_DATA(Hob);
 UINT64 Bytes=Releasable(W);if(!Bytes)return EFI_NOT_READY;
 if(W->Status!=5||!HasType(W->Base,Bytes,EfiConventionalMemory))return EFI_COMPROMISED_DATA;
 EFI_PHYSICAL_ADDRESS At=W->Base;
 EFI_STATUS S=gBS->AllocatePages(AllocateAddress,EfiBootServicesData,EFI_SIZE_TO_PAGES(Bytes),&At);
 if(!EFI_ERROR(S)&&At==W->Base&&HasType(W->Base,W->Bytes,EfiBootServicesData))W->Status=4;
 return W->Status==4?EFI_SUCCESS:EFI_COMPROMISED_DATA;
}
