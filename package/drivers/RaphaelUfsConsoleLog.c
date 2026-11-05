// SPDX-License-Identifier: BSD-2-Clause-Patent
// Explicit private allocation only. Console capture never invokes storage.
#include <kern/thread.h>
#include <kern/misc_protos.h>
#include <IOKit/IOReturn.h>
#include <IOKit/IOLocks.h>
#include "RaphaelUfsLogBuffer.h"
#include "RaphaelUfsLogAllocation.h"
extern IOReturn raphael_ufs_diagnostic_append(const void *,uint32_t,uint64_t,uint64_t,uint64_t,uint64_t *);
extern volatile uint32_t raphael_ufs_online;
static struct rph_log_ring ring;
struct log_write_policy {
 uint64_t magic,version,lun,partition_first,partition_blocks,lba,blocks,block_bytes;
 unsigned char original[4096],replacement[4096];
};
_Static_assert(sizeof(struct log_write_policy)==8256,"Existing UFS single-block ABI");
static struct log_write_policy policy;
volatile uint64_t raphael_ufs_console_log_record[16];
static unsigned pending;
static IOLock *flushGate;
void raphael_ufs_log_init(void){
 flushGate=IOLockAlloc();
 if(!flushGate)panic("Raphael UFS log: no flush lock");
}
void raphael_ufs_log_capture(const char *s,int size){
 if(size>0)rph_log_capture(&ring,s,(unsigned)size);
}
// Both callers flush only in normal, sleepable context.
static void flushLocked(void){
 volatile uint64_t *r=raphael_ufs_console_log_record;
 if(r[1]>=3 || !__atomic_load_n(&raphael_ufs_online,__ATOMIC_ACQUIRE))return; // allocation exhausted or terminal device error
 r[0]=0x31474f4c485052ULL;
 if(!policy.magic){
  const uint64_t *a=raphael_ufs_log_allocation;
  policy.magic=0x3157525346485052ULL;policy.version=1;
  policy.lun=a[1];policy.partition_first=a[2];policy.partition_blocks=a[3];
  policy.blocks=1;policy.block_bytes=4096;r[1]=1;
 }
 for(unsigned batch=0;batch<4;++batch){
  if(r[3]>=raphael_ufs_log_allocation[6]){r[1]=3;return;}
  if(!pending){
   memset(policy.replacement,0,sizeof(policy.replacement));
   pending=rph_log_peek(&ring,policy.replacement+64);if(!pending)return;
   uint64_t words[8]={0x3130474f4c485052ULL,raphael_ufs_log_allocation[4],raphael_ufs_log_allocation[5],r[3],0,pending,0,0};
   __asm__ volatile("mrs %0,cntpct_el0":"=r"(words[4]));
   words[6]=__atomic_load_n(&ring.dropped,__ATOMIC_RELAXED);
   memcpy(policy.replacement,words,sizeof(words));
   words[7]=rph_log_crc32(policy.replacement,sizeof(policy.replacement));
   memcpy(policy.replacement+56,&words[7],8);
  }
  policy.lba=raphael_ufs_log_allocation[8+r[3]];
  uint64_t stages=0;r[2]=r[2]+1;
  IOReturn status=raphael_ufs_diagnostic_append(&policy,sizeof(policy),raphael_ufs_log_allocation[8],raphael_ufs_log_allocation[6],r[3],&stages);
  r[6]=(uint32_t)status;r[7]=stages;r[8]=policy.lba;
  if(status==kIOReturnNotReady)return; // keep the same pending bytes until UFS exists
  if(status!=kIOReturnSuccess){r[1]=4;return;}
  rph_log_commit(&ring,pending);r[3]=r[3]+1;r[4]=r[4]+pending;pending=0;r[1]=2;
  r[5]=__atomic_load_n(&ring.dropped,__ATOMIC_RELAXED);
  __asm__ volatile("mrs %0,cntpct_el0":"=r"(r[9]));
  r[10]=__atomic_load_n(&ring.head,__ATOMIC_ACQUIRE);r[11]=__atomic_load_n(&ring.tail,__ATOMIC_ACQUIRE);
 }
}

void raphael_ufs_log_flush(void){
 if(!flushGate)return;
 IOLockLock(flushGate);flushLocked();IOLockUnlock(flushGate);
}
// The validated selector2 path releases clientGate before calling this function.
// Serialize with observer flushing and persist the reason before entering panic.
void raphael_ufs_log_watchdog_panic(const char *text,unsigned limit){
 if(!flushGate)return;
 IOLockLock(flushGate);
 static const char begin[]="\nRPH WATCHDOG PANIC REASON BEGIN\n";
 static const char end[]="\nRPH WATCHDOG PANIC REASON END\n";
 unsigned n=0;while(n<limit && text[n])++n;
 raphael_ufs_log_capture(begin,sizeof(begin)-1);
 raphael_ufs_log_capture(text,(int)n);
 raphael_ufs_log_capture(end,sizeof(end)-1);
 uint64_t target=__atomic_load_n(&ring.head,__ATOMIC_ACQUIRE);
 for(unsigned batch=0;batch<17 && ring.tail<target;++batch){
  uint64_t previous=ring.tail;flushLocked();if(ring.tail==previous)break;
 }
 IOLockUnlock(flushGate);
}

// Called only after the existing observer has captured its bounded records.
// Each complete row enters the same ring atomically; no console rendering or
// storage operation is added to printing, exception, or IRQ paths.
void raphael_ufs_log_snapshot(const char *name,const volatile uint64_t *words,unsigned count)
{
 char row[256];
 int n=snprintf(row,sizeof(row),"\nRPH SNAP BEGIN %s %u\n",name,count);
 raphael_ufs_log_capture(row,n);
 for(unsigned offset=0;offset<count;offset+=8){
  n=snprintf(row,sizeof(row),"\nRPH SNAP WORDS %s %u",name,offset);
  for(unsigned j=offset;j<count && j<offset+8;++j)
   n+=snprintf(row+n,sizeof(row)-(unsigned)n," %016llx",(unsigned long long)words[j]);
  row[n++]='\n';raphael_ufs_log_capture(row,n);
  if((offset%256)==248)raphael_ufs_log_flush();
 }
 n=snprintf(row,sizeof(row),"\nRPH SNAP END %s\n",name);
 raphael_ufs_log_capture(row,n);raphael_ufs_log_flush();
}
