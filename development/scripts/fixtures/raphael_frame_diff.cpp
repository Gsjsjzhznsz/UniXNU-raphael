// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cassert>
#include <cstring>
#include <vector>
#include "NativeLegacyRequest.h"
int main(){
 const unsigned w=34,h=3;const uint64_t ss=w*4+8,ds=w*4+24;
 std::vector<uint64_t> src((ss*h+7)/8),dst((ds*h+7)/8,~0ull),shadow((w*h*4+7)/8);
 for(unsigned y=0;y<h;++y)for(unsigned x=0;x<w;++x){uint32_t v=0xff000000|(y*100+x);memcpy((char *)src.data()+y*ss+x*4,&v,4);}
 auto copy=[&](int valid){return native_legacy_copy_diff(dst.data(),ds*h,ds,src.data(),ss*h,ss,w,h,shadow.data(),valid);};
 assert(copy(0)==w*h*4);for(unsigned y=0;y<h;++y)assert(!memcmp((char *)dst.data()+y*ds,(char *)src.data()+y*ss,w*4));
 assert(copy(1)==0);
 ((char *)src.data())[4]^=7;assert(copy(1)==64);assert(copy(1)==0);
 ((char *)src.data())[ss+32*4]^=1;assert(copy(1)==8);
 assert(native_legacy_copy_diff(dst.data(),ds*h,ds,src.data(),ss*h,ss,w-1,h,shadow.data(),1)==UINT64_MAX);
 assert(native_legacy_fill_pixels(dst.data(),ds*h,ds,w,h,0xff000000));assert(copy(0)==w*h*4);
 for(unsigned y=0;y<h;++y){assert(!memcmp((char *)dst.data()+y*ds,(char *)src.data()+y*ss,w*4));for(unsigned k=w*4;k<ds;++k)assert(((unsigned char *)dst.data())[y*ds+k]==255);}
}
