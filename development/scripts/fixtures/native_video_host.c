// SPDX-License-Identifier: BSD-2-Clause-Patent
// Exercise real native-video code, including full pitched-frame restoration.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef NULL
#include <RaphaelNativeVideo.h>
#include <Library/BaseLib.h>
static unsigned pass, fail_alloc, fail_read, bad_query;
enum { W=64,H=32,PITCH=80 };
static UINT32 pixels[PITCH*H], original[PITCH*H];
VOID *EFIAPI AllocatePool(UINTN n) { return fail_alloc ? NULL : malloc(n); }
VOID EFIAPI FreePool(VOID *p) { free(p); }
VOID *EFIAPI ZeroMem(VOID *p,UINTN n) { return memset(p,0,n); }
INTN EFIAPI CompareMem(CONST VOID *a,CONST VOID *b,UINTN n) { return memcmp(a,b,n); }
UINT64 EFIAPI ReadUnaligned64(CONST VOID *p) { UINT64 v;memcpy(&v,p,8);return v; }
static EFI_GRAPHICS_OUTPUT_MODE_INFORMATION info={0,W,H,PixelBlueGreenRedReserved8BitPerColor,{0,0,0,0},PITCH};
static EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE mode={1,0,&info,sizeof(info),0,sizeof(pixels)};
static EFI_STATUS EFIAPI query(EFI_GRAPHICS_OUTPUT_PROTOCOL *g,UINT32 m,UINTN *n,EFI_GRAPHICS_OUTPUT_MODE_INFORMATION **out) {
 (void)g;(void)m;*out=malloc(sizeof(info));memcpy(*out,&info,sizeof(info));(*out)->HorizontalResolution+=bad_query;*n=sizeof(info);return EFI_SUCCESS;
}
static EFI_STATUS EFIAPI blt(EFI_GRAPHICS_OUTPUT_PROTOCOL *g,EFI_GRAPHICS_OUTPUT_BLT_PIXEL *b,EFI_GRAPHICS_OUTPUT_BLT_OPERATION op,UINTN sx,UINTN sy,UINTN dx,UINTN dy,UINTN w,UINTN h,UINTN delta) {
 (void)g;(void)sx;(void)sy;(void)dx;(void)dy;(void)delta;
 if(fail_read)return EFI_DEVICE_ERROR;
 if(op!=EfiBltVideoToBltBuffer||w!=W||h!=H)abort();
 for(UINTN y=0;y<h;++y)memcpy((UINT32 *)b+y*w,pixels+y*PITCH,w*4);
 return EFI_SUCCESS;
}
static EFI_GRAPHICS_OUTPUT_PROTOCOL gop={query,NULL,blt,&mode};
static UINT32 read32(UINT64 a,VOID *c) {(void)c;return *(UINT32 *)(UINTN)a;}
static VOID write32(UINT64 a,UINT32 v,VOID *c) {(void)c;*(UINT32 *)(UINTN)a=v;}
static VOID dropwrite(UINT64 a,UINT32 v,VOID *c) {(void)a;(void)v;(void)c;}
static void ok(int v,const char *s){if(!v){fprintf(stderr,"FAIL %s\n",s);exit(1);}printf("PASS %s\n",s);++pass;}
int main(void) {
 RAPHAEL_PIXEL_SNAPSHOT sample={0};sample.Version=1;sample.Status=6;sample.BaseLow=0x180000;sample.Width=64;sample.Height=64;sample.Stride=256;sample.Extent=64*256;sample.PixelCount=4096;sample.RefreshCount=32;
 RAPHAEL_FRAMEBUFFER_GUARD spans[]={{0x100000,0x10000},{0x200000,0x10000}};RAPHAEL_GOP_RESULT planned;
 ok(RaphaelFramebufferPlanRanges(&sample,spans,2,&planned)&&planned.Status==2,"disjoint allocations allow a real framebuffer in the gap");
 spans[1].Base=0x180001;ok(!RaphaelFramebufferPlanRanges(&sample,spans,2,&planned),"page-rounded framebuffer overlap with any real span refused");
 spans[1].Base=MAX_UINT64-1;ok(!RaphaelFramebufferPlanRanges(&sample,spans,2,&planned),"overflowing occupied range refused");
 ok(!RaphaelFramebufferPlanRanges(&sample,spans,0,&planned),"missing occupied spans refused");
 RAPHAEL_GOP_RESULT s={0};UINT64 video[6]={0};UINT8 args[0x60]={0};mode.FrameBufferBase=(UINTN)pixels;
 s.Status=4;s.MappedReadVerified=s.ProtocolInstalled=1;s.Base=mode.FrameBufferBase;s.Width=W;s.Height=H;s.Stride=PITCH*4;s.Extent=sizeof(pixels);
 for(unsigned i=0;i<PITCH*H;++i)original[i]=pixels[i]=i*0x010101+0x12;
 ok(RaphaelNativeVideoBegin(NULL,&gop,video)==EFI_INVALID_PARAMETER,"missing live state rejected");
 s.MappedReadVerified=0;ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_UNSUPPORTED&&!s.Active,"missing same-entry mapping proof refused");s.MappedReadVerified=1;
 info.PixelFormat=PixelBltOnly;ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_COMPROMISED_DATA,"Blt-only cannot invent a physical framebuffer");info.PixelFormat=PixelBlueGreenRedReserved8BitPerColor;
 s.Extent--;ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_UNSUPPORTED,"short mapped extent rejected");s.Extent++;
 bad_query=1;ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_COMPROMISED_DATA&&!s.Active,"inconsistent queried mode refused");bad_query=0;
 fail_alloc=1;ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_OUT_OF_RESOURCES&&!s.Active&&!s.Backup,"allocation failure leaves no transaction");fail_alloc=0;
 fail_read=1;ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_DEVICE_ERROR&&!s.Active&&!s.Backup,"backup read failure leaves no transaction");fail_read=0;
 ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_SUCCESS&&s.Active&&s.Backup,"full inherited frame backed up before any loader writes");
 ok(video[0]==mode.FrameBufferBase&&video[1]==1&&video[2]==PITCH*4&&video[3]==W&&video[4]==H&&video[5]==32,"six Boot_Video fields use actual supplied GOP");
 UINT64 saved=s.Backup;ok(RaphaelNativeVideoBegin(&s,&gop,video)==EFI_ALREADY_STARTED&&s.Backup==saved,"active backup cannot be overwritten");
 memcpy(args+0x28,video,sizeof(video));ok(RaphaelNativeVideoMatches(args,video),"independent Darwin boot argument ABI matches");
 for(unsigned i=0;i<6;++i){args[0x28+i*8]^=1;ok(!RaphaelNativeVideoMatches(args,video),"each changed boot video field is rejected");args[0x28+i*8]^=1;}
 for(unsigned y=0;y<H;++y)for(unsigned x=0;x<W;++x)pixels[y*PITCH+x]^=0x00ffffff;
 RaphaelRestoreGopPatch(&s,read32,dropwrite,NULL);ok(s.Active&&s.Backup==saved&&s.PatchMismatches==W*H,"failed restore retains original full frame");
 RaphaelRestoreGopPatch(&s,read32,write32,NULL);ok(!s.Active&&s.PatchMismatches==0&&s.PatchRestored==W*H&&!memcmp(pixels,original,sizeof(pixels)),"SEC restores all pixels and preserves pitch padding");free((VOID *)(UINTN)s.Backup);
 memset(video,0,sizeof(video));memset(args,0,sizeof(args));ok(RaphaelNativeVideoMatches(args,video),"default headless contract remains all zero");
 printf("NATIVE_VIDEO_HOST_OK %u\n",pass);return 0;
}
