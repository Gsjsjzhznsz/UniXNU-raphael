// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_UFS_LOG_BUFFER_H
#define RAPHAEL_UFS_LOG_BUFFER_H
#ifdef RPH_LOG_HOST
#include <stdint.h>
#endif
#define RPH_LOG_RING_BYTES (256u*1024u)
#define RPH_LOG_PAYLOAD_BYTES 4032u
struct rph_log_ring {
 uint32_t gate;
 uint64_t head,tail,dropped;
 unsigned char data[RPH_LOG_RING_BYTES];
};
// Nonblocking capture: console/IRQ paths never wait for a flush or device I/O.
static inline void rph_log_capture(struct rph_log_ring *r,const char *s,unsigned n){
 if(!s||!n)return;
 if(__atomic_exchange_n(&r->gate,1,__ATOMIC_ACQUIRE)){
  __atomic_fetch_add(&r->dropped,n,__ATOMIC_RELAXED);return;
 }
 uint64_t head=__atomic_load_n(&r->head,__ATOMIC_RELAXED);
 uint64_t tail=__atomic_load_n(&r->tail,__ATOMIC_ACQUIRE);
 unsigned take=n;if(take>RPH_LOG_RING_BYTES-(head-tail))take=(unsigned)(RPH_LOG_RING_BYTES-(head-tail));
 for(unsigned i=0;i<take;++i)r->data[(head+i)%RPH_LOG_RING_BYTES]=(unsigned char)s[i];
 __atomic_store_n(&r->head,head+take,__ATOMIC_RELEASE);
 if(take<n)__atomic_fetch_add(&r->dropped,n-take,__ATOMIC_RELAXED);
 __atomic_store_n(&r->gate,0,__ATOMIC_RELEASE);
}
static inline unsigned rph_log_peek(struct rph_log_ring *r,unsigned char *out){
 if(__atomic_exchange_n(&r->gate,1,__ATOMIC_ACQUIRE))return 0;
 uint64_t tail=__atomic_load_n(&r->tail,__ATOMIC_RELAXED);
 uint64_t head=__atomic_load_n(&r->head,__ATOMIC_ACQUIRE);
 unsigned n=(unsigned)(head-tail);if(n>RPH_LOG_PAYLOAD_BYTES)n=RPH_LOG_PAYLOAD_BYTES;
 for(unsigned i=0;i<n;++i)out[i]=r->data[(tail+i)%RPH_LOG_RING_BYTES];
 __atomic_store_n(&r->gate,0,__ATOMIC_RELEASE);return n;
}
static inline void rph_log_commit(struct rph_log_ring *r,unsigned n){
 __atomic_fetch_add(&r->tail,n,__ATOMIC_RELEASE);
}
static inline uint32_t rph_log_crc32(const unsigned char *p,unsigned n){
 uint32_t c=~0u;
 for(unsigned i=0;i<n;++i){c^=p[i];for(unsigned b=0;b<8;++b)c=(c>>1)^(0xedb88320u&(0u-(c&1u)));}
 return ~c;
}
#endif
