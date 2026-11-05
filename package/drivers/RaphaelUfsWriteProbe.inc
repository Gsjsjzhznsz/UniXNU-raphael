// SPDX-License-Identifier: BSD-2-Clause-Patent
// Included only by an explicit private diagnostic build. One observer thread
// calls this after IOSleep, before storage handback. Never use in panic/IRQ.
extern "C" {
volatile uint64_t raphael_ufs_write_request_record[6]={};
int raphael_ufs_diagnostic_write_once(void){
 auto *r=raphael_ufs_write_request_record;
 if(r[4])return 1;
 r[0]=1;r[1]=r[1]+1;
 uint64_t stages=0;
 IOReturn status=raphael_ufs_diagnostic_write(raphael_ufs_write_probe_policy,sizeof(raphael_ufs_write_probe_policy),&stages);
 r[2]=static_cast<uint32_t>(status);r[3]=stages;
 if(status==kIOReturnNotReady)return 0; // No controller yet; no write was authorized.
 uint64_t counter;__asm__ volatile("mrs %0,cntpct_el0":"=r"(counter));r[5]=counter;
 __atomic_store_n(&r[4],1,__ATOMIC_RELEASE);
 return 1; // Success or terminal refusal/error: never attempt another write.
}
}
