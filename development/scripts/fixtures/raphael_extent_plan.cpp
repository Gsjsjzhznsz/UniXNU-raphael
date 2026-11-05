// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelExtentPlan.h"
using namespace RaphaelStorage;
static unsigned cases=0;
static void check(bool b,const char *s){if(!b){fprintf(stderr,"FAIL %s\n",s);exit(1);}printf("PASS %s\n",s);++cases;}
static unsigned char pattern(uint64_t n){return (unsigned char)((n*29+(n>>11)*13+(n>>17))&255);}
struct Device {unsigned calls=0;unsigned fail=~0U;bool readPhysicalBlock(uint64_t lba,uint8_t *p){++calls;if(calls==fail)return false;for(unsigned i=0;i<4096;++i)p[i]=pattern(lba*4096+i);return true;}};
int main(){
 ExtentPlan p{};p.version=1;p.count=2;p.fileBytes=12288;p.lunBytes=262144;p.partitionBase=16384;p.partitionBytes=196608;p.requests=6;p.repeats=16;
 p.map[0]={0,32768,4096,0};p.map[1]={4096,65536,8192,1};
 p.request[0]={0,512};p.request[1]={512,512};p.request[2]={3584,1024};p.request[3]={11776,512};p.request[4]={7680,1024};p.request[5]={4096,512};
 unsigned at=0;for(unsigned i=0;i<p.requests;++i)for(unsigned j=0;j<p.request[i].bytes;++j){uint64_t pos=p.request[i].offset+j,phys=pos<4096?32768+pos:65536+pos-4096;p.expected[at++]=pattern(phys);}
 ReadOnlyExtents disk;Device device;uint8_t out[4096]{};uint64_t completed=0;
 check(validatePlan(p,disk),"validate full fragmented plan");
 check(executePlan(p,disk,device,out,completed)==Result::Ok&&completed==16&&device.calls==128&&!memcmp(out,p.expected,4096),"16 repeated exact reads including physical and extent boundaries");
 auto reject=[&](const char *name){device.calls=0;completed=99;check(executePlan(p,disk,device,out,completed)==Result::InvalidMap&&device.calls==0&&completed==0,name);};
 p.version=2;reject("reject unknown policy before DMA");p.version=1;
 p.count=129;reject("reject extent count overflow");p.count=2;
 p.requests=9;reject("reject request count overflow");p.requests=6;
 p.requests=0;reject("reject empty plan");p.requests=6;
 p.repeats=17;reject("reject repetition budget overflow");p.repeats=16;
 p.repeats=0;reject("reject zero iterations");p.repeats=16;
 p.request[0].offset=1;reject("reject unaligned logical address");p.request[0].offset=0;
 p.request[0].bytes=0;reject("reject zero request");p.request[0].bytes=512;
 p.request[0].bytes=4096;reject("reject output sum overflow");p.request[0].bytes=512;
 p.request[0].offset=12288;reject("reject EOF address");p.request[0].offset=0;
 p.request[0].offset=~uint64_t(511);reject("reject wrapped request address");p.request[0].offset=0;
 p.map[1].flags=0x801;reject("reject unwritten extents");p.map[1].flags=1;
 p.map[1].physical=32768;reject("reject overlapping allocation");p.map[1].physical=65536;
 p.expected[2048]^=1;device.calls=0;completed=0;check(executePlan(p,disk,device,out,completed)==Result::DeviceError&&completed==0,"byte mismatch prevents successful repetition");p.expected[2048]^=1;
 device.calls=0;device.fail=10;completed=0;check(executePlan(p,disk,device,out,completed)==Result::DeviceError&&completed==1,"second-pass transport error preserves only completed pass count");device.fail=~0U;
 device.calls=0;check(executePlan(p,disk,device,nullptr,completed)==Result::InvalidMap&&device.calls==0,"null output rejected before device access");
 printf("RAPHAEL_EXTENT_PLAN_OK cases=%u\n",cases);
}
