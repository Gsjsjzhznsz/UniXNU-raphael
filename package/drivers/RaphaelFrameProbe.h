// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_FRAME_PROBE_H
#define RAPHAEL_FRAME_PROBE_H
#include <stdint.h>
#include <stddef.h>
#define RPH_FRAME_W 90u
#define RPH_FRAME_H 195u
#define RPH_FRAME_BYTES (RPH_FRAME_W*RPH_FRAME_H*3u)
struct rph_frame_probe {
 uint32_t gate,ready;
 uint64_t frame,counter,last_counter,nonblack,framebuffer_nonblack,mismatches;
 unsigned char rgb[RPH_FRAME_BYTES];
};
// The swap path and diagnostic worker never wait for one another. The worker
// copies a stable thumbnail before logging; no surface or mapping is retained.
static inline int rph_frame_take(struct rph_frame_probe *p){
 uint32_t expected=0;
 return __atomic_compare_exchange_n(&p->gate,&expected,1,0,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);
}
static inline void rph_frame_release(struct rph_frame_probe *p){__atomic_store_n(&p->gate,0,__ATOMIC_RELEASE);}
static inline int rph_frame_capture(struct rph_frame_probe *p,const void *source,uint64_t source_bytes,uint64_t source_stride,
 const volatile void *framebuffer,uint64_t framebuffer_bytes,uint64_t framebuffer_stride,uint32_t width,uint32_t height,
 uint64_t frame,uint64_t counter,uint64_t frequency){
 if(!source||!framebuffer||!width||!height||!frequency||frequency>UINT64_MAX/120||
    source_stride<(uint64_t)width*4||framebuffer_stride<(uint64_t)width*4||
    source_stride>UINT64_MAX/height||framebuffer_stride>UINT64_MAX/height||
    source_bytes<source_stride*height||framebuffer_bytes<framebuffer_stride*height||
    ((uintptr_t)framebuffer&3)||(framebuffer_stride&3)||!rph_frame_take(p))return 0;
 if(p->ready && counter-p->last_counter<frequency*120){rph_frame_release(p);return 0;}
 uint64_t nonblack=0,fb_nonblack=0,mismatches=0;
 for(unsigned y=0;y<RPH_FRAME_H;++y){
  uint64_t sy=(uint64_t)y*height/RPH_FRAME_H;
  for(unsigned x=0;x<RPH_FRAME_W;++x){
   uint64_t sx=(uint64_t)x*width/RPH_FRAME_W;
   const unsigned char *s=(const unsigned char *)source+sy*source_stride+sx*4;
   uint32_t pixel=s[0]|((uint32_t)s[1]<<8)|((uint32_t)s[2]<<16);
   const volatile uint32_t *f=(const volatile uint32_t *)((const volatile unsigned char *)framebuffer+sy*framebuffer_stride+sx*4);
   uint32_t actual=*f&0xffffff;
   unsigned at=(y*RPH_FRAME_W+x)*3;
   p->rgb[at]=s[2];p->rgb[at+1]=s[1];p->rgb[at+2]=s[0];
   nonblack+=pixel!=0;fb_nonblack+=actual!=0;mismatches+=pixel!=actual;
  }
 }
 p->frame=frame;p->counter=counter;p->last_counter=counter;p->nonblack=nonblack;
 p->framebuffer_nonblack=fb_nonblack;p->mismatches=mismatches;p->ready=1;
 rph_frame_release(p);return 1;
}
static inline int rph_frame_copy(struct rph_frame_probe *p,unsigned char *out,unsigned size,uint64_t meta[5]){
 if(!out||size!=RPH_FRAME_BYTES||!meta||!rph_frame_take(p))return 0;
 if(!p->ready){rph_frame_release(p);return 0;}
 for(unsigned i=0;i<RPH_FRAME_BYTES;++i)out[i]=p->rgb[i];
 meta[0]=p->frame;meta[1]=p->counter;meta[2]=p->nonblack;meta[3]=p->framebuffer_nonblack;meta[4]=p->mismatches;
 rph_frame_release(p);return 1;
}
#endif
