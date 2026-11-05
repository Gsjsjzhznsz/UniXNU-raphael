#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
#include "RaphaelUfsLogPolicy.h"
using RaphaelUfs::Result;
struct Fake {
 unsigned enables=0,writes=0,flushes=0,reads=0,revokes=0;bool active=false;unsigned char media[3][4096]{};
 Result read(uint8_t,uint64_t lba,uint32_t,void *out,uint32_t){++reads;assert(lba>=10&&lba<13);memcpy(out,media[lba-10],4096);return Result::Ok;}
 Result enableDiagnosticWrites(const RaphaelUfs::DiagnosticWriteWindow &w){assert(w.first==10&&w.blocks==3);assert(!enables);++enables;active=true;return Result::Ok;}
 Result writeDiagnostic(uint8_t,uint64_t lba,uint32_t,const void *data,uint32_t){assert(active);++writes;memcpy(media[lba-10],data,4096);return Result::Ok;}
 Result flushDiagnostic(){assert(active);++flushes;return Result::Ok;}
 void revokeDiagnosticWrites(){++revokes;active=false;}
};
int main(){
 RaphaelStorage::UfsAppendSession session;Fake f;uint8_t scratch[4096];uint64_t flags;
 RaphaelStorage::UfsWritePolicy p{};p.magic=0x3157525346485052ULL;p.version=1;p.lunBlocks=100;p.partitionFirst=5;p.partitionBlocks=80;p.blocks=1;p.blockBytes=4096;
 for(unsigned i=0;i<3;++i){p.first=10+i;memset(p.replacement,int(i+1),4096);assert(RaphaelStorage::executeLogAppend(p,10,3,i,session,f,scratch,flags)==0&&flags==63);assert(f.enables==1&&session.next==i+1);}
 assert(f.writes==3&&f.flushes==3&&f.revokes==1&&session.finished&&!f.active);
 unsigned reads=f.reads;assert(RaphaelStorage::executeLogAppend(p,10,3,2,session,f,scratch,flags)==203&&f.reads==reads);
 RaphaelStorage::UfsAppendSession fresh;Fake occupied;occupied.media[0][1]=7;p.first=10;assert(RaphaelStorage::executeLogAppend(p,10,3,0,fresh,occupied,scratch,flags)==201&&occupied.writes==0&&occupied.enables==0);
 assert(!RaphaelStorage::validateLogAppend(p,10,3,1,fresh));assert(!RaphaelStorage::validateLogAppend(p,10,4097,0,fresh));
 puts("PASS: three durable appends share one grant; terminal/reordered/occupied/out-of-range writes rejected");
}
