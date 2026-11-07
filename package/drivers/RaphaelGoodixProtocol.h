// SPDX-License-Identifier: BSD-2-Clause-Patent
// Independent GT9889/Normandy wire decoder. Register offsets are supplied from
// this handset's selected Goodix configuration, never inferred from chip name.
// Protocol reference: Xiaomi raphael-p-oss 663db50, goodix_ts_i2c.c.
#pragma once
#include <stdint.h>
#include <stddef.h>
#define RPH_GOODIX_CONTACTS 10
struct rph_goodix_contact { uint8_t id,width; uint16_t x,y; };
struct rph_goodix_frame { uint8_t count; struct rph_goodix_contact contacts[RPH_GOODIX_CONTACTS]; };
// Zero means the complete transfer succeeded; short transfers must be errors.
// A write error does not establish whether the controller accepted the ACK.
struct rph_goodix_bus {
 void *context;
 int (*read)(void *,uint16_t,uint8_t *,size_t);
 int (*write)(void *,uint16_t,const uint8_t *,size_t);
};
enum { RPH_GOODIX_NONE=0,RPH_GOODIX_FRAME=1,RPH_GOODIX_REQUEST=2,
 RPH_GOODIX_IO=-1,RPH_GOODIX_CHECKSUM=-2,RPH_GOODIX_INVALID=-3 };
static inline int rph_goodix_decode(const uint8_t *data,size_t length,struct rph_goodix_frame *out) {
 if(!data || !out || length<4)return RPH_GOODIX_INVALID;
 if(!(data[0]&0x80))return (data[0]&0x40)?RPH_GOODIX_REQUEST:RPH_GOODIX_NONE;
 unsigned count=data[1]&15;
 if(count>RPH_GOODIX_CONTACTS || length<4+8*count)return RPH_GOODIX_INVALID;
 uint8_t sum=0;for(unsigned i=0;i<4+8*count;++i)sum=(uint8_t)(sum+data[i]);
 if(sum)return RPH_GOODIX_CHECKSUM;
 struct rph_goodix_frame next={0,{ {0,0,0,0} }};next.count=(uint8_t)count;
 unsigned ids=0;
 for(unsigned i=0;i<count;++i) {
  const uint8_t *p=data+2+8*i;unsigned id=p[0]&15;
  unsigned x=p[1]|((unsigned)p[2]<<8),y=p[3]|((unsigned)p[4]<<8);
  if((p[0]&0x80) || id>=RPH_GOODIX_CONTACTS || (ids&(1u<<id)) || x>1079 || y>2339)return RPH_GOODIX_INVALID;
  ids|=1u<<id;next.contacts[i].id=(uint8_t)id;next.contacts[i].width=p[5];
  next.contacts[i].x=(uint16_t)x;next.contacts[i].y=(uint16_t)y;
 }
 *out=next;return RPH_GOODIX_FRAME;
}
static inline int rph_goodix_poll(struct rph_goodix_bus *bus,uint16_t coordinates,struct rph_goodix_frame *out,uint8_t *status) {
 uint8_t data[84]={0};
 if(!bus || !bus->read || !bus->write || !out || !coordinates || coordinates>UINT16_MAX-83u)return RPH_GOODIX_INVALID;
 if(bus->read(bus->context,coordinates,data,12))return RPH_GOODIX_IO;
 if(status)*status=data[0];
 if(!(data[0]&0x80))return (data[0]&0x40)?RPH_GOODIX_REQUEST:RPH_GOODIX_NONE;
 unsigned count=data[1]&15;
 int result=RPH_GOODIX_INVALID;
 struct rph_goodix_frame next;
 if(count<=RPH_GOODIX_CONTACTS) {
  if(count>1 && bus->read(bus->context,(uint16_t)(coordinates+12),data+12,8*(count-1)))result=RPH_GOODIX_IO;
  else result=rph_goodix_decode(data,sizeof(data),&next);
 }
 // The hardware latches the packet until this ACK, including rejected packets.
 // An ACK failure cannot be reported as a successful frame (would replay it).
 uint8_t clear=0;
 if(bus->write(bus->context,coordinates,&clear,1))return RPH_GOODIX_IO;
 if(result==RPH_GOODIX_FRAME)*out=next;
 return result;
}
