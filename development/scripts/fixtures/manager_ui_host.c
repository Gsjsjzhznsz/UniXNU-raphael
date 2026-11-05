// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef NULL
#include <Library/RaphaelManagerUiLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/MemoryAllocationLib.h>
static unsigned pass,allocs,fail_alloc,fail_blt,calls,bad_restore;
static UINT32 pixels[64*32],original[64*32];
VOID *EFIAPI AllocatePool(UINTN n){++allocs;if(fail_alloc&&allocs==fail_alloc)return NULL;return malloc(n);}
VOID EFIAPI FreePool(VOID *p){free(p);}
VOID *EFIAPI ZeroMem(VOID *p,UINTN n){return memset(p,0,n);}
INTN EFIAPI CompareMem(CONST VOID *a,CONST VOID *b,UINTN n){return memcmp(a,b,n);}
static EFI_GRAPHICS_OUTPUT_MODE_INFORMATION info={0,64,32,PixelBlueGreenRedReserved8BitPerColor,{0,0,0,0},64};
static EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE mode={1,0,&info,sizeof(info),0x12340000,sizeof(pixels)};
static EFI_STATUS EFIAPI query(EFI_GRAPHICS_OUTPUT_PROTOCOL *g,UINT32 m,UINTN *bytes,EFI_GRAPHICS_OUTPUT_MODE_INFORMATION **out){(void)g;if(m)return EFI_UNSUPPORTED;*out=malloc(sizeof(info));memcpy(*out,&info,sizeof(info));*bytes=sizeof(info);return EFI_SUCCESS;}
static EFI_STATUS EFIAPI blt(EFI_GRAPHICS_OUTPUT_PROTOCOL *g,EFI_GRAPHICS_OUTPUT_BLT_PIXEL *b,EFI_GRAPHICS_OUTPUT_BLT_OPERATION op,UINTN sx,UINTN sy,UINTN dx,UINTN dy,UINTN w,UINTN h,UINTN delta){
 (void)g;(void)delta;++calls;if(fail_blt==calls)return EFI_DEVICE_ERROR;assert(sx==0&&dx==0&&w==64);
 if(op==EfiBltVideoToBltBuffer){assert(dy==0&&sy+h<=32);memcpy(b,pixels+sy*64,w*h*4);}
 else{assert(op==EfiBltBufferToVideo&&sx==0&&sy==0&&dy==0&&h==32);memcpy(pixels,b,sizeof(pixels));if(bad_restore)pixels[0]^=1;}
 return EFI_SUCCESS;
}
static EFI_GRAPHICS_OUTPUT_PROTOCOL gop={query,NULL,blt,&mode};
static void ok(int v,const char *s){if(!v){fprintf(stderr,"FAIL %s\n",s);abort();}printf("PASS %s\n",s);++pass;}
_Static_assert(sizeof(RAPHAEL_MANAGER_UI_RESULT)==128,"wire prefix");
_Static_assert(sizeof(RAPHAEL_MANAGER_UI_STATE)==352,"materialized SEC state");
int main(void){
 RAPHAEL_MANAGER_UI_STATE s={0};RAPHAEL_GOP_RESULT e={0};e.Width=64;e.Height=32;e.Stride=256;e.Base=mode.FrameBufferBase;e.Extent=sizeof(pixels);
 for(unsigned i=0;i<64*32;++i)original[i]=pixels[i]=i*0x010101+0x12;
 ok(RaphaelManagerUiBegin(NULL,&e,1,&gop)==EFI_INVALID_PARAMETER,"null state");
 ok(RaphaelManagerUiBegin(&s,&e,0,&gop)==EFI_INVALID_PARAMETER,"missing input");
 for(unsigned n=1;n<=2;++n){fail_alloc=n;allocs=0;ok(RaphaelManagerUiBegin(&s,&e,1,&gop)==EFI_OUT_OF_RESOURCES&&!s.Restore.Active&&!s.Restore.Backup&&!s.Line,"partial allocation cleanup");}fail_alloc=0;
 fail_blt=calls+1;ok(RaphaelManagerUiBegin(&s,&e,1,&gop)==EFI_DEVICE_ERROR&&!s.Restore.Active&&!s.Restore.Backup&&!s.Line,"backup read failure cleanup");fail_blt=0;
 ok(!EFI_ERROR(RaphaelManagerUiBegin(&s,&e,1,&gop))&&s.Restore.Active&&s.Result.Status==2,"original framebuffer backed up");
 UINT64 saved=s.Restore.Backup;ok(RaphaelManagerUiBegin(&s,&e,1,&gop)==EFI_ALREADY_STARTED&&saved==s.Restore.Backup,"active backup cannot be discarded");
 pixels[7]^=0xff;pixels[129]^=0xff;
 ok(!EFI_ERROR(RaphaelManagerUiFinish(&s))&&s.Result.Status==4&&s.Result.PixelsChanged==2&&s.Result.PixelsRestored==2048&&!s.Result.Active&&!s.Result.Backup,"changed manager frame restored exactly");
 ok(memcmp(pixels,original,sizeof(pixels))==0,"all original pixels preserved");
 ok(RaphaelManagerUiFinish(&s)==EFI_NOT_READY,"finished transaction cannot run twice");
 ok(!EFI_ERROR(RaphaelManagerUiBegin(&s,&e,1,&gop)),"restart supported");
 ok(RaphaelManagerUiFinish(&s)==EFI_COMPROMISED_DATA&&!s.Restore.Active&&!s.Line&&memcmp(pixels,original,sizeof(pixels))==0,"unchanged manager output is rejected after restore");
 ok(!EFI_ERROR(RaphaelManagerUiBegin(&s,&e,1,&gop)),"write failure setup");pixels[0]^=1;
 fail_blt=calls+33;ok(RaphaelManagerUiFinish(&s)==EFI_DEVICE_ERROR&&s.Restore.Active&&s.Restore.Backup&&s.Line,"restore write failure retains original");
 fail_blt=0;ok(!EFI_ERROR(RaphaelManagerUiFinish(&s))&&!s.Restore.Active&&memcmp(pixels,original,sizeof(pixels))==0,"retained original can be retried");
 ok(!EFI_ERROR(RaphaelManagerUiBegin(&s,&e,1,&gop)),"restore mismatch setup");pixels[0]^=1;bad_restore=1;
 ok(RaphaelManagerUiFinish(&s)==EFI_COMPROMISED_DATA&&s.Restore.Active&&s.Restore.Backup&&s.Result.Mismatches==1,"mismatch retains original for fatal fallback");bad_restore=0;
 ok(!EFI_ERROR(RaphaelManagerUiFinish(&s))&&memcmp(pixels,original,sizeof(pixels))==0,"mismatch retry restores original");
 for(unsigned failure=1;failure<=2;++failure){
  ok(!EFI_ERROR(RaphaelManagerUiBegin(&s,&e,1,&gop)),"row failure setup");pixels[3]^=0x10;
  fail_blt=calls+(failure==1?1:34);
  EFI_STATUS status=RaphaelManagerUiFinish(&s);
  ok(status==EFI_DEVICE_ERROR,"row access error propagated");
  if(failure==1)ok(!s.Restore.Active&&!s.Restore.Backup&&!s.Line&&memcmp(pixels,original,sizeof(pixels))==0,"failed pre-scan still restores and releases original");
  else{
   ok(s.Restore.Active&&s.Restore.Backup&&s.Line,"failed restoration readback retains backing memory");fail_blt=0;
   ok(!EFI_ERROR(RaphaelManagerUiFinish(&s))&&!s.Restore.Active&&memcmp(pixels,original,sizeof(pixels))==0,"restoration readback retry preserves first changed-frame evidence");
  }
  fail_blt=0;
 }
 info.PixelFormat=PixelBltOnly;mode.FrameBufferBase=0;mode.FrameBufferSize=0;e.Base=0;e.Extent=0;
 ok(!EFI_ERROR(RaphaelManagerUiBegin(&s,&e,1,&gop))&&s.Result.PixelFormat==PixelBltOnly,"AAVMF Blt-only interface records no invented framebuffer");pixels[1]^=1;
 ok(!EFI_ERROR(RaphaelManagerUiFinish(&s))&&memcmp(pixels,original,sizeof(pixels))==0,"Blt-only transaction uses protocol for restore");
 e.Base=0x12340000;e.Extent=sizeof(pixels);
 ok(RaphaelManagerUiBegin(&s,&e,1,&gop)==EFI_UNSUPPORTED,"physical phone expectation cannot match Blt-only interface");
 info.PixelFormat=PixelBlueGreenRedReserved8BitPerColor;mode.FrameBufferBase=e.Base;mode.FrameBufferSize=e.Extent;
 e.Width=4097;ok(RaphaelManagerUiBegin(&s,&e,1,&gop)==EFI_UNSUPPORTED,"unbounded width refused");e.Width=64;e.Stride=1;ok(RaphaelManagerUiBegin(&s,&e,1,&gop)==EFI_UNSUPPORTED,"invalid stride refused");e.Stride=256;e.Base=~0ULL-1;ok(RaphaelManagerUiBegin(&s,&e,1,&gop)==EFI_UNSUPPORTED,"overflow framebuffer refused");
 printf("MANAGER_UI_HOST_OK %u\n",pass);return 0;
}
