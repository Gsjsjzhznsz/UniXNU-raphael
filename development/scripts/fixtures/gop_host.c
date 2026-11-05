// SPDX-License-Identifier: BSD-2-Clause-Patent
// Runs actual port GOP and pinned generic Blt code against guarded host RAM.
#include <Library/RaphaelGopLib.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/ArmLib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
static unsigned checks;
static void check(int ok,const char *name) {
  if(!ok) { fprintf(stderr,"FAIL %s\n",name);exit(1); }
  ++checks;printf("PASS %s\n",name);
}
VOID *EFIAPI CopyMem(VOID *D,CONST VOID *S,UINTN N) {return memmove(D,S,N);}
VOID *EFIAPI ZeroMem(VOID *D,UINTN N) {return memset(D,0,N);}
VOID *EFIAPI SetMem(VOID *D,UINTN N,UINT8 V) {return memset(D,V,N);}
VOID *EFIAPI SetMem32(VOID *D,UINTN N,UINT32 V) {for(UINTN I=0;I<N/4;++I)((UINT32 *)D)[I]=V;return D;}
VOID *EFIAPI SetMem64(VOID *D,UINTN N,UINT64 V) {for(UINTN I=0;I<N/8;++I)((UINT64 *)D)[I]=V;return D;}
INTN EFIAPI HighBitSet32(UINT32 V) {return V?31-__builtin_clz(V):-1;}
VOID *EFIAPI AllocateCopyPool(UINTN N,CONST VOID *P) {VOID *D=malloc(N);if(D)memcpy(D,P,N);return D;}
VOID EFIAPI ArmDataSynchronizationBarrier(VOID) {}
VOID EFIAPI DebugPrint(UINTN L,CONST CHAR8 *F,...) {(void)L;(void)F;}
VOID EFIAPI DebugAssert(CONST CHAR8 *F,UINTN L,CONST CHAR8 *D) {fprintf(stderr,"ASSERT %s:%llu %s\n",F,(unsigned long long)L,D);abort();}
BOOLEAN EFIAPI DebugPrintEnabled(VOID) {return TRUE;}
BOOLEAN EFIAPI DebugAssertEnabled(VOID) {return TRUE;}
BOOLEAN EFIAPI DebugPrintLevelEnabled(CONST UINTN L) {(void)L;return FALSE;}
static UINT32 read32(UINT64 A,VOID *C) {(void)C;return *(UINT32 *)(UINTN)A;}
static void write32(UINT64 A,UINT32 V,VOID *C) {(void)C;*(UINT32 *)(UINTN)A=V;}
static RAPHAEL_PIXEL_SNAPSHOT pixels;
static VOID dropwrite(UINT64 A,UINT32 V,VOID *C){(VOID)A;(VOID)V;(VOID)C;}
int main(void) {
  RAPHAEL_GOP_RESULT plan;
  pixels.Version=1;pixels.Status=6;pixels.BaseLow=0x100004;
  pixels.Width=64;pixels.Height=64;pixels.Stride=256;pixels.Extent=64*256;
  pixels.PixelCount=4096;pixels.RefreshCount=32;
  check(RaphaelFramebufferPlan(&pixels,0x200000,0x300000,&plan) &&
    plan.MapBase==0x100000 && plan.MapSize==20480 && plan.Status==2,"page-rounded mapping from supplied geometry");
  check(!RaphaelFramebufferPlan(&pixels,0x104000,0x105000,&plan),"rounded mapping cannot overlap diagnostic extension");
  check(!RaphaelFramebufferPlan(NULL,1,2,&plan),"missing live snapshot rejected");
  pixels.Status=5;check(!RaphaelFramebufferPlan(&pixels,1,2,&plan),"incomplete read proof rejected");pixels.Status=6;
  pixels.BaseHigh=1;check(!RaphaelFramebufferPlan(&pixels,1,2,&plan),"unproven high address rejected");pixels.BaseHigh=0;
  pixels.Extent=1;check(!RaphaelFramebufferPlan(&pixels,1,2,&plan),"extent mismatch rejected");pixels.Extent=64*256;
  pixels.BaseLow=0xfffff000;check(!RaphaelFramebufferPlan(&pixels,1,2,&plan),"physical end overflow rejected");
  pixels.BaseLow=0x100004;pixels.Stride=252;check(!RaphaelFramebufferPlan(&pixels,1,2,&plan),"stride narrower than visible pixels rejected");
  enum {W=80,H=64,PITCH=96,N=PITCH*H};
  UINT32 *guard=malloc((N+32)*4),*v=guard+16,*expected=malloc(N*4),*buffer=malloc(N*4);
  if(!guard||!expected||!buffer)abort();
  for(UINTN I=0;I<N+32;++I)guard[I]=0xa5a5a5a5;
  for(UINTN I=0;I<N;++I)v[I]=expected[I]=(UINT32)(0x34000000+I);
  memset(&plan,0,sizeof(plan));plan.Status=3;plan.MappedReadVerified=1;
  plan.Base=(UINTN)v;plan.Width=W;plan.Height=H;plan.Stride=PITCH*4;plan.Extent=N*4;
  RAPHAEL_GOP g;UINTN size=0;
  check(RaphaelGopConfigure(&g,&plan,NULL,&size)==RETURN_BUFFER_TOO_SMALL && size>0,"GOP configuration size query");
  VOID *config=malloc(size);
  check(RaphaelGopConfigure(&g,&plan,config,&size)==RETURN_SUCCESS,"actual port GOP configured over guarded RAM");
  EFI_GRAPHICS_OUTPUT_PROTOCOL *p=&g.Protocol;
  EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *info=NULL;UINTN isize=0;
  check(p->QueryMode(p,0,&isize,&info)==EFI_SUCCESS && info!=&g.Info &&
    isize==sizeof(*info) && info->HorizontalResolution==W && info->VerticalResolution==H &&
    info->PixelsPerScanLine==PITCH && info->PixelFormat==PixelBlueGreenRedReserved8BitPerColor,"QueryMode returns allocated inherited BGR geometry");free(info);
  check(p->QueryMode(p,1,&isize,&info)==EFI_UNSUPPORTED && p->SetMode(p,1)==EFI_UNSUPPORTED,"invalid mode rejected without writes");
  check(p->QueryMode(p,0,NULL,&info)==EFI_INVALID_PARAMETER,"null query output rejected");
  EFI_GRAPHICS_OUTPUT_BLT_PIXEL color={3,2,1,255};
  check(p->Blt(p,&color,EfiBltVideoFill,0,0,5,6,10,9,0)==EFI_SUCCESS,"generic video fill");
  for(UINTN Y=6;Y<15;++Y)for(UINTN X=5;X<15;++X)expected[Y*PITCH+X]=0x00010203;
  check(!memcmp(v,expected,N*4),"fill touches exact rectangle, preserves row padding");
  for(UINTN I=0;I<N;++I)buffer[I]=(UINT32)(0x56000000+I);
  check(p->Blt(p,(VOID *)buffer,EfiBltBufferToVideo,7,8,20,21,12,13,PITCH*4)==EFI_SUCCESS,"buffer to video with source offset and Delta");
  for(UINTN Y=0;Y<13;++Y)memcpy(expected+(21+Y)*PITCH+20,buffer+(8+Y)*PITCH+7,12*4);
  check(!memcmp(v,expected,N*4),"buffer to video exact pixel values");
  memset(buffer,0xa6,N*4);
  check(p->Blt(p,(VOID *)buffer,EfiBltVideoToBltBuffer,20,21,4,5,12,13,PITCH*4)==EFI_SUCCESS,"video to buffer with destination offset and Delta");
  int good=1;
  for(UINTN Y=0;Y<H;++Y)for(UINTN X=0;X<PITCH;++X) {
    UINT32 want=(Y>=5&&Y<18&&X>=4&&X<16)?expected[(Y-5+21)*PITCH+X-4+20]:0xa6a6a6a6;
    if(buffer[Y*PITCH+X]!=want)good=0;
  }
  check(good,"video readback preserves destination padding and surrounding data");
  check(p->Blt(p,NULL,EfiBltVideoToVideo,0,0,0,1,W,H-1,0)==EFI_SUCCESS,"descending overlapping video copy to final visible row");
  for(UINTN Y=H-1;Y>0;--Y)memmove(expected+Y*PITCH,expected+(Y-1)*PITCH,W*4);
  check(!memcmp(v,expected,N*4),"descending overlap uses correct final source row");
  check(p->Blt(p,NULL,EfiBltVideoToVideo,0,1,0,0,W,H-1,0)==EFI_SUCCESS,"ascending overlapping video copy");
  for(UINTN Y=0;Y<H-1;++Y)memmove(expected+Y*PITCH,expected+(Y+1)*PITCH,W*4);
  check(!memcmp(v,expected,N*4),"ascending overlap exact values");
  check(p->Blt(p,NULL,EfiBltVideoToVideo,0,0,1,0,W-1,1,0)==EFI_SUCCESS,"horizontal overlap right");memmove(expected+1,expected,(W-1)*4);
  check(!memcmp(v,expected,N*4),"horizontal overlap exact values");
  check(p->Blt(p,&color,EfiBltVideoFill,0,0,MAX_UINTN,0,1,1,0)==EFI_INVALID_PARAMETER,"wrapped destination rejected");
  check(p->Blt(p,NULL,EfiBltVideoToVideo,MAX_UINTN,0,0,0,1,1,0)==EFI_INVALID_PARAMETER,"wrapped source rejected");
  check(p->Blt(p,NULL,EfiBltVideoFill,0,0,0,0,1,1,0)==EFI_INVALID_PARAMETER,"null fill buffer rejected");
  check(p->Blt(p,(VOID *)buffer,EfiBltBufferToVideo,0,0,0,0,10,2,4)==EFI_INVALID_PARAMETER,"short Delta rejected");
  check(p->Blt(p,(VOID *)buffer,EfiBltVideoToBltBuffer,0,0,0,MAX_UINTN,1,2,4)==EFI_INVALID_PARAMETER,"buffer row overflow rejected");
  check(p->Blt(p,(VOID *)(UINTN)(MAX_UINTN-1),EfiBltBufferToVideo,0,0,0,0,1,1,4)==EFI_INVALID_PARAMETER,"buffer pointer overflow rejected");
  check(p->Blt(p,&color,(EFI_GRAPHICS_OUTPUT_BLT_OPERATION)-1,0,0,0,0,1,1,0)==EFI_INVALID_PARAMETER,"invalid operation rejected");
  check(p->Blt(p,&color,EfiBltVideoFill,0,0,0,0,0,1,0)==EFI_INVALID_PARAMETER,"empty rectangle rejected");
  check(!memcmp(v,expected,N*4),"all invalid requests leave framebuffer unchanged");
  check(p->SetMode(p,0)==EFI_SUCCESS,"SetMode active mode clears display without timing changes");
  for(UINTN Y=0;Y<H;++Y)for(UINTN X=0;X<W;++X)expected[Y*PITCH+X]=0;
  check(!memcmp(v,expected,N*4),"SetMode clears visible pixels and preserves pitch padding");
  for(UINTN I=0;I<N;++I)v[I]=expected[I]=(UINT32)(I^0xabcd1234);
  UINT32 saved[32];for(UINTN Y=0;Y<4;++Y)for(UINTN X=0;X<8;++X) {
    saved[Y*8+X]=v[Y*PITCH+X];v[Y*PITCH+X]=0;
  }
  plan.Backup=(UINTN)saved;plan.Active=1;plan.PatchWidth=8;plan.PatchHeight=4;
  RaphaelRestoreGopPatch(&plan,read32,write32,NULL);
  check(!memcmp(v,expected,N*4) && plan.Active==0 && plan.PatchRestored==32 &&
    plan.PatchMismatches==0 && plan.RestoreFallbackUsed==1,"SEC fallback restores saved patch exactly");
  plan.Active=1; v[0]^=1;
  RaphaelRestoreGopPatch(&plan,read32,dropwrite,NULL);
  check(plan.Active==1 && plan.PatchMismatches==1,"failed restoration retains active backup");
  RaphaelRestoreGopPatch(&plan,read32,write32,NULL);
  check(plan.Active==0 && !memcmp(v,expected,N*4),"retained backup permits restoration retry");
  good=1;for(UINTN I=0;I<16;++I)if(guard[I]!=0xa5a5a5a5||guard[N+16+I]!=0xa5a5a5a5)good=0;
  check(good,"framebuffer guards intact after all operations");
  free(config);free(guard);free(expected);free(buffer);
  printf("GOP_HOST_OK %u\n",checks);return 0;
}
