// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelReadOnlyExtents.h"
using namespace RaphaelStorage;
static unsigned cases=0;
static void check(bool v,const char *name){if(!v){fprintf(stderr,"FAIL %s\n",name);exit(1);}++cases;printf("PASS %s\n",name);}
struct Disk {
 unsigned calls=0;uint64_t fail=UINT64_MAX;
 bool readPhysicalBlocks(uint64_t lba,uint32_t blocks,uint8_t *out){++calls;if(lba<=fail&&fail-lba<blocks)return false;for(uint32_t i=0;i<blocks*4096;++i)out[i]=uint8_t((lba*4096+i)*29+7);return true;}
 bool readPhysicalBlock(uint64_t lba,uint8_t *out){++calls;if(lba==fail)return false;for(unsigned i=0;i<4096;++i)out[i]=uint8_t((lba*4096+i)*29+7);return true;}
};
int main(){
 Bounds b{12288,262144,16384,196608,4096,512};
 Extent ext[]={{0,32768,4096,0},{4096,65536,8192,1}};ReadOnlyExtents m;Disk d;uint8_t out[12288];
 check(m.read(d,0,512,out)==Result::NotReady&&d.calls==0,"uninitialized map refuses IO");
 check(m.overlapsPhysical(0,4096),"uninitialized root map denies writes");
 check(m.initialize(ext,2,b)==Result::Ok&&m.size()==12288,"validate fragmented plaintext map");
 check(m.overlapsPhysical(32768,4096),"diagnostic writes reject first root extent");
 check(m.overlapsPhysical(65536,4096),"diagnostic writes reject fragmented second root extent");
 check(!m.overlapsPhysical(73728,4096),"root extent end is exclusive");
 check(m.overlapsPhysical(28672,8192),"crossing root extent start is rejected");
 check(!m.overlapsPhysical(0,4096),"diagnostic allocation outside root extents can be checked");
 check(m.overlapsPhysical(UINT64_MAX-1,4096),"diagnostic allocation overflow rejected");
 check(m.overlapsPhysical(0,0),"empty diagnostic allocation rejected");
 check(m.read(d,3584,5120,out)==Result::Ok&&d.calls==3,"512 sectors cross physical block and extent");
 bool match=true;for(unsigned i=0;i<5120;++i){uint64_t logical=3584+i,physical=logical<4096?32768+logical:65536+logical-4096;match=match&&out[i]==uint8_t(physical*29+7);}check(match,"exact bytes from correct fragmented physical offsets");
 unsigned batchStart=d.calls;check(m.readAligned(d,0,12288,out)==Result::Ok&&d.calls==batchStart+2,"batched read splits only at physical extent boundary");
 match=true;for(unsigned i=0;i<12288;++i){uint64_t physical=i<4096?32768+i:65536+i-4096;match=match&&out[i]==uint8_t(physical*29+7);}check(match,"batched fragmented bytes exactly match sector reader");
 check(m.readAligned(d,512,4096,out)==Result::InvalidRead,"batch requires physical block aligned start");
 d.fail=17;memset(out,0xa5,sizeof(out));check(m.readAligned(d,4096,8192,out)==Result::DeviceError&&out[0]==0xa5,"failed multi-block command exposes no stale payload");d.fail=UINT64_MAX;
 unsigned before=d.calls;check(m.read(d,12288,512,out)==Result::InvalidRead&&d.calls==before,"reject EOF without device IO");
 check(m.read(d,1,512,out)==Result::InvalidRead&&m.read(d,0,513,out)==Result::InvalidRead,"reject virtual unaligned reads");
 check(m.read(d,UINT64_MAX-511,1024,out)==Result::InvalidRead,"reject wrapped read range");
 d.fail=16;memset(out,0xa5,sizeof(out));check(m.read(d,4096,512,out)==Result::DeviceError&&out[0]==0xa5,"failed physical block exposes no stale bytes");d.fail=UINT64_MAX;
 b.fileBytes=8704;check(m.initialize(ext,2,b)==Result::Ok&&m.read(d,8192,512,out)==Result::Ok,"rounded final physical block permits exact partial EOF");
 check(m.readAligned(d,8192,512,out)==Result::Ok&&out[0]==uint8_t(69632*29+7),"batch partial final file block preserves exact tail bytes");
 check(m.read(d,8704,512,out)==Result::InvalidRead,"tail allocation outside virtual file remains inaccessible");
 auto reject=[&](const char *name){check(m.initialize(ext,2,b)==Result::InvalidMap&&m.size()==0,name);};
 ext[1].logical=8192;reject("reject sparse hole");ext[1].logical=4096;
 ext[1].physical=32768;reject("reject physical alias");ext[1].physical=65536;
 ext[1].flags=0x801;reject("reject unwritten extent");ext[1].flags=0x9;reject("reject encoded extent");ext[1].flags=3;reject("reject unknown extent");ext[1].flags=1;
 ext[0].flags=1;reject("reject premature LAST flag");ext[0].flags=0;
 ext[1].physical=UINT64_MAX-4095;reject("reject physical overflow");ext[1].physical=65536;
 ext[0].physical=0;reject("reject outside approved userdata partition");ext[0].physical=32768;
 ext[1].bytes=12288;reject("reject excess mapping beyond rounded file");ext[1].bytes=8192;
 b.partitionBase=UINT64_MAX-4095;reject("reject partition overflow");b.partitionBase=16384;
 b.physicalBlockBytes=512;reject("require explicit verified physical geometry");b.physicalBlockBytes=4096;
 b.virtualBlockBytes=4096;reject("require declared virtual 512 geometry");b.virtualBlockBytes=512;
 b.fileBytes=UINT64_MAX-511;reject("reject file rounding overflow");
 check(m.initialize(ext,129,b)==Result::InvalidMap,"bounded extent count");
 printf("RAPHAEL_READONLY_EXTENTS_OK cases=%u\n",cases);return 0;
}
