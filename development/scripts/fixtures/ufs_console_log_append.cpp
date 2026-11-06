#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <vector>
#include "RaphaelUfsLogPolicy.h"
using RaphaelUfs::Result;
struct Fake {
 unsigned enables=0,writes=0,flushes=0,reads=0,revokes=0;bool active=false;unsigned total;std::vector<uint8_t> media;
 Fake(unsigned n=3):total(n),media(n*4096){}
 Result read(uint8_t,uint64_t lba,uint32_t,void *out,uint32_t){++reads;assert(lba>=10&&lba<10+total);memcpy(out,media.data()+(lba-10)*4096,4096);return Result::Ok;}
 Result enableDiagnosticWrites(const RaphaelUfs::DiagnosticWriteWindow &w){assert(w.first==10&&w.blocks==total);assert(!enables);++enables;active=true;return Result::Ok;}
 Result writeDiagnostic(uint8_t,uint64_t lba,uint32_t,const void *data,uint32_t){assert(active);++writes;memcpy(media.data()+(lba-10)*4096,data,4096);return Result::Ok;}
 Result flushDiagnostic(){assert(active);++flushes;return Result::Ok;}
 void revokeDiagnosticWrites(){++revokes;active=false;}
};
int main(){
 RaphaelStorage::UfsAppendSession session;Fake f;uint8_t scratch[4096];uint64_t flags;
 RaphaelStorage::UfsWritePolicy p{};p.magic=0x3157525346485052ULL;p.version=1;p.lunBlocks=100;p.partitionFirst=5;p.partitionBlocks=80;p.blocks=1;p.blockBytes=4096;
 for(unsigned i=0;i<3;++i){p.first=10+i;memset(p.replacement,int(i+1),4096);assert(RaphaelStorage::executeLogAppend(p,10,3,i,session,f,scratch,flags)==0&&flags==63);assert(f.enables==1&&session.next==i+1);}
 assert(f.writes==3&&f.flushes==3&&f.revokes==1&&session.finished&&!f.active);
 unsigned reads=f.reads;assert(RaphaelStorage::executeLogAppend(p,10,3,2,session,f,scratch,flags)==203&&f.reads==reads);
 RaphaelStorage::UfsAppendSession fresh;Fake occupied;occupied.media[1]=7;p.first=10;assert(RaphaelStorage::executeLogAppend(p,10,3,0,fresh,occupied,scratch,flags)==201&&occupied.writes==0&&occupied.enables==0);
 assert(!RaphaelStorage::validateLogAppend(p,10,3,1,fresh));assert(!RaphaelStorage::validateLogAppend(p,10,8193,0,fresh));
 RaphaelStorage::UfsAppendSession wide;Fake large(8192);p.lunBlocks=20000;p.partitionFirst=5;p.partitionBlocks=19000;
 for(unsigned i=0;i<8192;++i){p.first=10+i;memset(p.replacement,int(i%251+1),4096);assert(RaphaelStorage::executeLogAppend(p,10,8192,i,wide,large,scratch,flags)==0&&flags==63);assert(large.enables==1&&wide.next==i+1);}
 assert(large.writes==8192&&large.revokes==1&&wide.finished&&!large.active);
 p.first=10;assert(!RaphaelStorage::validateLogAppend(p,10,8193,0,fresh));
 puts("PASS: three and8192 durable appends share one grant; terminal/reordered/occupied/out-of-range writes rejected");
}
