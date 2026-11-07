// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "RaphaelGoodixProtocol.h"
struct fake { unsigned reads,acks; int fail_read,fail_ack,clear_on_ack; uint8_t packet[84]; };
static void checksum(uint8_t *p) {unsigned n=4+8*(p[1]&15);p[n-1]=0;unsigned s=0;for(unsigned i=0;i<n-1;++i)s+=p[i];p[n-1]=(uint8_t)-s;}
static int read_packet(void *c,uint16_t reg,uint8_t *out,size_t n) {struct fake *f=c;++f->reads;if(f->fail_read && f->reads==2)return -1;assert(reg>=0x9000 && reg+n<=0x9054);memcpy(out,f->packet+reg-0x9000,n);return 0;}
static int ack(void *c,uint16_t reg,const uint8_t *p,size_t n) {struct fake *f=c;assert(reg==0x9000 && n==1 && *p==0);++f->acks;if(!f->fail_ack && f->clear_on_ack)f->packet[0]=0;return f->fail_ack;}
static void contact(uint8_t *p,unsigned i,unsigned id,unsigned x,unsigned y) {p+=2+8*i;p[0]=(uint8_t)id;p[1]=(uint8_t)x;p[2]=(uint8_t)(x>>8);p[3]=(uint8_t)y;p[4]=(uint8_t)(y>>8);p[5]=12;}
int main(void) {
 struct fake f={0};struct rph_goodix_bus bus={&f,read_packet,ack};struct rph_goodix_frame frame={0};uint8_t status;
 assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==0 && !f.acks);
 f.packet[0]=0x80;f.packet[1]=1;contact(f.packet,0,3,540,2339);checksum(f.packet);
 assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==1 && frame.count==1 && frame.contacts[0].id==3 && frame.contacts[0].y==2339 && f.acks==1);
 contact(f.packet,0,3,540,1700);checksum(f.packet);
 assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==1 && frame.contacts[0].id==3 && frame.contacts[0].y==1700);
 f.packet[1]=2;contact(f.packet,0,7,1079,0);contact(f.packet,1,3,0,2339);checksum(f.packet);
 assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==1 && frame.count==2 && frame.contacts[1].id==3);
 f.packet[1]=0;checksum(f.packet);assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==1 && frame.count==0);
 f.packet[1]=10;for(unsigned i=0;i<10;++i)contact(f.packet,i,i,i*100,i*200);checksum(f.packet);
 assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==1 && frame.count==10);
 unsigned a=f.acks;f.packet[9]^=1;assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==-2 && frame.count==10 && f.acks==a+1);f.packet[9]^=1;
 a=f.acks;contact(f.packet,1,0,100,200);checksum(f.packet);assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==-3 && f.acks==a+1);
 a=f.acks;contact(f.packet,1,1,1080,200);checksum(f.packet);assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==-3 && f.acks==a+1);
 a=f.acks;f.packet[1]=15;assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==-3 && f.acks==a+1);
 f.packet[1]=2;contact(f.packet,1,1,100,200);checksum(f.packet);f.reads=0;f.fail_read=1;
 a=f.acks;struct rph_goodix_frame saved=frame;
 assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==-1 && f.acks==a+1 && memcmp(&frame,&saved,sizeof(frame))==0);f.fail_read=0;f.fail_ack=1;
 a=f.acks;assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==-1 && f.acks==a+1 && memcmp(&frame,&saved,sizeof(frame))==0);f.fail_ack=0;
 assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==1 && frame.count==2);
 f.clear_on_ack=1;f.reads=0;f.fail_read=1;f.packet[0]=0x80;
 a=f.acks;assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==RPH_GOODIX_IO && f.acks==a+1);
 f.fail_read=0;assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==RPH_GOODIX_NONE);
 f.clear_on_ack=0;f.packet[0]=0x40;a=f.acks;assert(rph_goodix_poll(&bus,0x9000,&frame,&status)==2 && f.acks==a);
 unsigned reads=f.reads;assert(rph_goodix_poll(&bus,0xffad,&frame,&status)==RPH_GOODIX_INVALID && f.reads==reads);
 assert(rph_goodix_poll(&bus,0x9000,NULL,&status)==RPH_GOODIX_INVALID && f.reads==reads);
 puts("PASS Goodix: press/move/release, reordered IDs, ten contacts, checksum, bounds, I/O failure and ACK");
}
