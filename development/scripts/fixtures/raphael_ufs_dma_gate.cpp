// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <map>
#include <cstdio>
#include <stdexcept>
#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelUfsDmaGate.h"
int main(){try{
 const uint64_t b=0x1000000,size=0x100000;std::map<uint64_t,uint32_t> good;
 good[b+0x20]=(1U<<27)|(1U<<30)|3;good[b+0x24]=(6U<<28)|56;good[b]=0;
 for(unsigned i=0;i<3;++i)good[b+0x800+i*4]=1U<<31;
 good[b+0xc00]=1U<<16;good[b+0xc04]=2U<<16;good[b+0xc08]=2;
 good[b+0x1000+8]=1U<<16;good[b+0x80000+2*4096]=0;
 unsigned cases=0;
 auto run=[&](const char *name,std::map<uint64_t,uint32_t> m,bool expected,uint64_t bytes=0x100000){
  uint64_t valid=0,reason=0;auto read=[&](uint64_t a){auto it=m.find(a);if(it==m.end())throw std::runtime_error("unexpected read");return it->second;};
  bool ok=RaphaelUfs::noActiveTranslation(read,b,bytes,valid,reason);if(ok!=expected)throw std::runtime_error(name);
  printf("PASS %s result=%d reason=%llu\n",name,ok,(unsigned long long)reason);++cases;
 };
 run("bypass, fault and disabled translated streams safe",good,true);
 auto m=good;m[b+0x800]=0;m.erase(b+0xc00);run("invalid SMR never dereferences S2CR",m,true);
 m=good;m[b+0x80000+2*4096]=1;run("active stage1 rejected",m,false);
 m=good;m[b+0x1000+8]=3U<<16;run("stage2 translation rejected",m,false);
 m=good;m[b+0x1000+8]=0;run("stage2-only context rejected",m,false);
 m=good;m[b+0xc08]=3U<<16;run("reserved stream type rejected",m,false);
 m=good;m[b+0xc08]=56;run("out of range bank rejected before bank access",m,false);
 m=good;m[b]=1;run("powered down controller rejected",m,false);
 m=good;m[b+0x20]|=1U<<8;run("extended stream IDs unsupported",m,false);
 m=good;m[b+0x20]&=~255U;run("zero stream groups rejected",m,false);
 m=good;m[b+0x24]&=~255U;run("zero banks rejected",m,false);
 m=good;m[b+0x24]=0x600000ff;run("oversized bank count rejected",m,false);
 run("incorrect resource geometry rejected",good,false,size/2);
 run("tiny resource rejected before reads",{},false,4096);
 printf("RAPHAEL_UFS_DMA_GATE_OK %u\n",cases);return 0;
 }catch(const std::exception &e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
