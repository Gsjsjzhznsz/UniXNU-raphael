// SPDX-License-Identifier: BSD-2-Clause-Patent
// Exercise actual command entry with M/C/I off and SCTLR.A alignment checking.
#include <RaphaelUfsTransport.h>
extern "C" void output(const char *s) {
 register unsigned long x0 asm("x0")=4;
 register const char *x1 asm("x1")=s;
 asm volatile("hlt #0xf000":"+r"(x0),"+r"(x1)::"memory");
}
extern "C" [[noreturn]] void finish(unsigned long code) {
 unsigned long reason[2]={0x20026,code};
 register unsigned long x0 asm("x0")=0x20;
 register void *x1 asm("x1")=reason;
 asm volatile("hlt #0xf000":"+r"(x0),"+r"(x1)::"memory");
 for(;;)asm volatile("wfe");
}
struct Io {
 unsigned read(unsigned){return 0;}
 void write(unsigned,unsigned){}
 bool dmaAllowed(uint64_t,uint64_t){return false;}
 bool toDevice(uint64_t,const void*,size_t){return false;}
 bool fromDevice(uint64_t,void*,size_t){return false;}
 uint64_t nowUs(){return 0;}
 void pause(){}
};
using T=RaphaelUfs::Transport<Io>;
// The assembly caller keeps the real object state opaque to the optimizer.
extern "C" __attribute__((noinline,used)) unsigned command_entry(T *t) {
 return unsigned(t->testUnitReady(0));
}
extern "C" [[noreturn]] void exception() {
 unsigned long esr;asm volatile("mrs %0,esr_el1":"=r"(esr));
 if(((esr>>26)&63)==0x25 && (esr&63)==0x21) {
  output("UFS_ALIGNMENT_FAULT\n");finish(33);
 }
 output("UFS_UNEXPECTED_EXCEPTION\n");finish(34);
}
extern "C" void invoke(T *);
extern "C" [[noreturn]] void main_entry() {
 unsigned long sctlr;asm volatile("mrs %0,sctlr_el1":"=r"(sctlr));
 if((sctlr&0x1005)||!(sctlr&2)){output("UFS_WRONG_MMU_STATE\n");finish(35);}
 Io io;T transport(io,{0,0,0,4096},RaphaelUfs::ReadCommand::Read10);
 invoke(&transport);
 if(transport.last.ocs!=15 || transport.last.residual || transport.last.response ||
    transport.last.status || transport.last.senseKey || transport.last.asc || transport.last.ascq)finish(36);
 output("UFS_ALIGNMENT_OK\n");finish(0);
}
