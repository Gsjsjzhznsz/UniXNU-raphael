// Exercise the production console queue without kernel or storage mocks.
#define RPH_LOG_HOST 1
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "RaphaelUfsLogBuffer.h"
static struct rph_log_ring ring;
int main(int argc,char **argv){
 assert(argc==2);unsigned char a[4032],b[4032];
 rph_log_capture(&ring,"first line\n",11);
 assert(rph_log_peek(&ring,a)==11);assert(rph_log_peek(&ring,b)==11);assert(!memcmp(a,b,11));
 rph_log_capture(&ring,"second line\n",12);assert(rph_log_peek(&ring,b)==23);assert(!memcmp(b,"first line\nsecond line\n",23));
 rph_log_commit(&ring,11);assert(rph_log_peek(&ring,a)==12);assert(!memcmp(a,"second line\n",12));rph_log_commit(&ring,12);
 assert(rph_log_peek(&ring,a)==0);
 ring.gate=1;rph_log_capture(&ring,"lost",4);ring.gate=0;assert(ring.dropped==4&&ring.head==23);
 for(unsigned i=0;i<RPH_LOG_RING_BYTES;++i){char c=(char)(i%251);rph_log_capture(&ring,&c,1);}
 rph_log_capture(&ring,"full",4);assert(ring.dropped==8);
 unsigned total=0;
 while((argc=(int)rph_log_peek(&ring,a))>0){for(int i=0;i<argc;++i)assert(a[i]==(unsigned char)((total+(unsigned)i)%251));total+=(unsigned)argc;rph_log_commit(&ring,(unsigned)argc);}
 assert(total==RPH_LOG_RING_BYTES);
 rph_log_capture(&ring,"persistent console test\n",24);
 unsigned n=rph_log_peek(&ring,a);assert(n==24);
 unsigned char block[4096]={0};uint64_t words[8]={0x3130474f4c485052ULL,0x1122,0x3344,0,123456,n,ring.dropped,0};
 memcpy(block,words,64);memcpy(block+64,a,n);words[7]=rph_log_crc32(block,4096);memcpy(block+56,&words[7],8);
 FILE *f=fopen(argv[1],"wb");assert(f);assert(fwrite(block,1,4096,f)==4096);assert(fclose(f)==0);
 puts("PASS: FIFO, pending retry, wrap, overflow, IRQ contention and record CRC");return 0;
}
