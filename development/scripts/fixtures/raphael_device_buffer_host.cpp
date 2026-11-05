// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cassert>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include "RaphaelDeviceBuffer.h"
int main(){
 alignas(8) uint8_t source[4160],destination[4160];
 for(unsigned i=0;i<sizeof(source);++i)source[i]=static_cast<uint8_t>(i*37+13);
 for(unsigned device=0;device<16;++device)for(unsigned normal=0;normal<16;++normal)
  for(unsigned bytes: {0U,1U,7U,8U,9U,15U,16U,17U,31U,32U,33U,511U,4096U}){
   memset(destination,0xa5,sizeof(destination));
   RaphaelDeviceBuffer::read(destination+normal,source+device,bytes);
   assert(memcmp(destination+normal,source+device,bytes)==0);
   for(unsigned i=0;i<normal;++i)assert(destination[i]==0xa5);
   for(unsigned i=normal+bytes;i<sizeof(destination);++i)assert(destination[i]==0xa5);
   memset(destination,0xa5,sizeof(destination));
   RaphaelDeviceBuffer::write(destination+device,source+normal,bytes);
   assert(memcmp(destination+device,source+normal,bytes)==0);
   for(unsigned i=0;i<device;++i)assert(destination[i]==0xa5);
   for(unsigned i=device+bytes;i<sizeof(destination);++i)assert(destination[i]==0xa5);
  }
}
