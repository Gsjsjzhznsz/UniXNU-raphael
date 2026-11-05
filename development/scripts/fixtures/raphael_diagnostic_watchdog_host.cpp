// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cassert>
#include <cstdint>
#include "RaphaelDiagnosticWatchdog.h"
struct Io {
 uint64_t t=100;unsigned writes=0;uint32_t enabled=1,bark=655300,bite=688065;
 uint32_t read(unsigned n){assert(n==8||n==16||n==20);return n==8?enabled:n==16?bark:bite;}
 void write(unsigned n,uint32_t v){assert(n==4&&v==1);++writes;}
 uint64_t now(){return t;}
};
using Watchdog=RaphaelDiagnostic::Watchdog<Io>;using R=RaphaelDiagnostic::PetResult;
int main(){
 {Io io;Watchdog w(io);assert(w.begin(32765,20,1000,60000));assert(io.writes==1);io.t=599;assert(w.pet()==R::Waiting);io.t=600;assert(w.pet()==R::Petted);io.t=60099;assert(w.pet()==R::Petted);io.t=60100;assert(w.pet()==R::Expired);assert(io.writes==3);io.t=70000;assert(w.pet()==R::Expired&&io.writes==3);assert(!w.begin(32765,20,1000,60000));}
 {Io io;Watchdog w(io);assert(w.begin(32765,20,1000,60000));io.t+=500;io.bark=1;assert(w.pet()==R::Changed&&io.writes==1);}
 {Io io;Watchdog w(io);assert(w.begin(32765,20,1000,60000));w.stop();io.t+=500;assert(w.pet()==R::Expired&&io.writes==1);assert(!w.begin(32765,20,1000,60000));}
 {Io io;Watchdog w(io);assert(w.begin(32765,20,1000,180000,120000));io.t=120099;assert(!w.observerExpired());io.t=120100;assert(w.observerExpired());assert(w.pet()==R::Petted);io.t=180100;assert(w.pet()==R::Expired&&io.writes==2);}
 {Io io;Watchdog w(io);assert(!w.begin(32765,20,1000,180000,40000));assert(!w.begin(32765,20,1000,180001,120000));assert(io.writes==0);}
 {Io io;io.enabled=0;Watchdog w(io);assert(!w.begin(32765,20,1000,60000)&&io.writes==0);}
 {Io io;io.bite--;Watchdog w(io);assert(!w.begin(32765,20,1000,60000)&&io.writes==0);}
 {Io io;Watchdog w(io);assert(!w.begin(0,20,1000,60000));assert(!w.begin(UINT32_MAX,20,1000,60000));assert(!w.begin(32765,60,1000,60000));assert(!w.begin(32765,20,0,60000));assert(!w.begin(32765,20,1000000001ULL,60000));assert(!w.begin(32765,20,1000,60001));assert(io.writes==0);}
 {Io io;Watchdog w(io);assert(!w.observerExpired());assert(w.begin(32765,20,1000,60000));io.t=40099;assert(!w.observerExpired());io.t=40100;assert(w.observerExpired());assert(w.pet()==R::Petted);assert(io.writes==2);}
 {Io io;io.t=UINT64_MAX-5;Watchdog w(io);assert(w.begin(32765,20,1000,60000));io.t=1000;assert(w.pet()==R::Petted);io.t=39994;assert(w.observerExpired());io.t=59994;assert(w.pet()==R::Expired&&io.writes==2);}
 {Io io;Watchdog w(io);assert(w.begin(32765,20,1000,300000,240000));io.t=240099;assert(!w.observerExpired());io.t=240100;assert(w.observerExpired());assert(w.pet()==R::Petted);io.t=300100;assert(w.pet()==R::Expired&&io.writes==2);}
 {Io io;Watchdog w(io);assert(!w.begin(32765,20,1000,300000,120000));assert(!w.begin(32765,20,1000,180000,240000));assert(!w.begin(32765,20,1000,300001,240000));assert(io.writes==0);}

 {Io io;Watchdog w(io);assert(w.begin(32765,20,1000,420000,360000));io.t=360099;assert(!w.observerExpired());io.t=360100;assert(w.observerExpired());assert(w.pet()==R::Petted);io.t=420100;assert(w.pet()==R::Expired&&io.writes==2);io.t=500000;assert(w.pet()==R::Expired&&io.writes==2);}
 {Io io;Watchdog w(io);assert(!w.begin(32765,20,1000,420000,240000));assert(!w.begin(32765,20,1000,300000,360000));assert(!w.begin(32765,20,1000,420001,360000));assert(io.writes==0);}

 {Io io;Watchdog w(io);assert(w.begin(32765,20,19200000,780000,720000));io.t=100+19200000ULL*720-1;assert(!w.observerExpired());io.t++;assert(w.observerExpired());assert(w.pet()==R::Petted);io.t=100+19200000ULL*780;assert(w.pet()==R::Expired&&io.writes==2);}
 {Io io;Watchdog w(io);assert(!w.begin(32765,20,1000,780000,360000));assert(!w.begin(32765,20,1000,420000,720000));assert(io.writes==0);}
 {Io io;Watchdog w(io);assert(w.begin(32765,20,19200000,1860000,1800000));io.t=100+19200000ULL*1800-1;assert(!w.observerExpired());io.t++;assert(w.observerExpired());assert(w.pet()==R::Petted);io.t=100+19200000ULL*1860;assert(w.pet()==R::Expired&&io.writes==2);}
 {Io io;Watchdog w(io);assert(!w.begin(32765,20,1000,1860000,720000));assert(!w.begin(32765,20,1000,780000,1800000));assert(io.writes==0);}

}
