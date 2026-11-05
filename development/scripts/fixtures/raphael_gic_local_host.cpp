// SPDX-License-Identifier: BSD-2-Clause-Patent
// Exercise the production routine against architectural NS RAZ/WI behavior.
#include <cstdint>
#include <cassert>
#include <cstdio>
#include <map>
#include <vector>
#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelGicLocal.h"
struct Model {
 bool ds, sgiAvailable = true, ready = true;
 unsigned secureWrites = 0, wakeWrites = 0, barriers = 0;
 std::map<unsigned,uint32_t> regs;
 std::vector<uint32_t> disables;
 explicit Model(bool single) : ds(single) { regs[0x400]=0x12345678; regs[0x410]=0x98765432; regs[0xc04]=0xffffffff; }
 uint32_t readRd(unsigned) { return 0; }
 void writeRd(unsigned o,uint32_t) { assert(o==0x14);++wakeWrites; if(!ds)++secureWrites; }
 bool waitRd(unsigned,unsigned) { return ready; }
 uint32_t readSgi(unsigned o) {
  if(!ds && (o==0x80 || o==0xd00))return 0;
  return regs[o];
 }
 void writeSgi(unsigned o,uint32_t v) {
  constexpr uint32_t owned=1U|(1U<<18);
  if(o==0x80 || o==0xd00) {if(!ds){++secureWrites;return;}assert(o!=0xd00);regs[o]=v;return;}
  if(o==0x180){assert((v&~owned)==0);disables.push_back(v);regs[0x100]&=~v;return;}
  if(o==0x100){regs[o]|=v&(sgiAvailable?0xffffffff:~1U);return;}
  if(o==0x280){regs[0x200]&=~v;return;}
  regs[o]=v;
 }
 void barrier(){++barriers;}
};
int main(){
 constexpr uint32_t owned=1U|(1U<<18);
 {Model m(false);assert(raphaelConfigureGicLocal(m,18,0x10));assert(m.secureWrites==0&&m.wakeWrites==0);assert(m.regs[0x100]==owned);assert(m.regs[0x400]==0x12345680&&m.regs[0x410]==0x98805432);assert(m.disables==std::vector<uint32_t>{owned});}
 {Model m(true);assert(raphaelConfigureGicLocal(m,18,0x50));assert(m.regs[0x80]==owned&&m.wakeWrites==1&&m.secureWrites==0);}
 {Model m(false);m.sgiAvailable=false;assert(!raphaelConfigureGicLocal(m,18,0x10));assert(m.regs[0x100]==(1U<<18));}
 {Model m(false);m.regs[0x100]=1U<<19;assert(!raphaelConfigureGicLocal(m,18,0x10));assert(m.disables.empty()&&m.regs[0x100]==(1U<<19));}
 {Model m(false);m.regs[0x300]=1U<<18;assert(!raphaelConfigureGicLocal(m,18,0x10));assert(m.disables.empty());}
 {Model m(false);assert(!raphaelConfigureGicLocal(m,18,0));assert(m.disables.empty());}
 {Model m(false);m.ready=false;assert(!raphaelConfigureGicLocal(m,18,0x10));}
 {Model m(false);assert(!raphaelConfigureGicLocal(m,32,0x10));assert(!raphaelConfigureGicLocal(m,15,0x10));assert(m.disables.empty());}
 puts("8 production GIC local behavior cases passed (DS=0, DS=1, secure SGI, foreign IRQ, active IRQ, ARE, timeout, bounds)");
}
