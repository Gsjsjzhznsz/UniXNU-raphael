// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cassert>
#include <vector>
#include <cstring>
#include "RaphaelFrameProbe.h"
int main(){
 rph_frame_probe p{};const unsigned w=180,h=390;const uint64_t stride=w*4+16;
 std::vector<unsigned char> src(stride*h),fb(stride*h),out(RPH_FRAME_BYTES);uint64_t meta[5];
 for(unsigned y=0;y<h;++y)for(unsigned x=0;x<w;++x){unsigned char *s=src.data()+y*stride+x*4;s[0]=x;s[1]=y;s[2]=0x80;s[3]=0xff;}
 fb=src;
 assert(!rph_frame_copy(&p,out.data(),out.size(),meta));
 assert(rph_frame_capture(&p,src.data(),src.size(),stride,fb.data(),fb.size(),stride,w,h,1,100,100));
 assert(rph_frame_copy(&p,out.data(),out.size(),meta));assert(meta[0]==1&&meta[2]==90*195&&meta[4]==0);
 assert(out[0]==128&&out[1]==0&&out[2]==0);unsigned i=(194*90+89)*3;assert(out[i]==128&&out[i+1]==(388&255)&&out[i+2]==178);
 assert(!rph_frame_capture(&p,src.data(),src.size(),stride,fb.data(),fb.size(),stride,w,h,2,12099,100));
 fb[0]^=1;assert(rph_frame_capture(&p,src.data(),src.size(),stride,fb.data(),fb.size(),stride,w,h,3,12100,100));assert(rph_frame_copy(&p,out.data(),out.size(),meta)&&meta[4]==1);
 p.gate=1;assert(!rph_frame_copy(&p,out.data(),out.size(),meta));assert(!rph_frame_capture(&p,src.data(),src.size(),stride,fb.data(),fb.size(),stride,w,h,4,24100,100));p.gate=0;
 assert(!rph_frame_capture(&p,src.data(),10,stride,fb.data(),fb.size(),stride,w,h,4,24100,100));
 memset(src.data(),0,src.size());memset(fb.data(),0,fb.size());assert(rph_frame_capture(&p,src.data(),src.size(),stride,fb.data(),fb.size(),stride,w,h,5,24100,100));assert(rph_frame_copy(&p,out.data(),out.size(),meta)&&meta[2]==0&&meta[3]==0&&meta[4]==0);
}
