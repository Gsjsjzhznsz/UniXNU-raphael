// SPDX-License-Identifier: BSD-2-Clause-Patent
// Ephemeral, unprotected development Data only. No key or passcode operations.
#include <IOKit/IOService.h>
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOLib.h>
#include <pexpert/device_tree.h>
#include <pexpert/pexpert.h>
#include <libkern/libkern.h>
extern "C" {
volatile uint64_t raphael_offline_aks_stage=0,raphael_offline_aks_opens=0;
volatile uint64_t raphael_offline_aks_refused=0,raphael_offline_aks_calls=0;
volatile uint64_t raphael_offline_aks_selector=0,raphael_offline_aks_result=0;
volatile uint64_t raphael_offline_aks_selectors=0;
bool native_aks_state_enabled(void) {
 unsigned enable=0;
#if RAPHAEL_HANDSET_DISPLAY
 // This archive is linked only by the explicit diagnostic scratch-Data option.
 // Reuse the owned display opt-in; no handset boot-argument fallback.
 DTEntry chosen=nullptr;const void *value=nullptr;unsigned length=0;
 if(SecureDTLookupEntry(nullptr,"/chosen",&chosen)!=kSuccess ||
    SecureDTGetProperty(chosen,"unixnu,diagnostic-display",&value,&length)!=kSuccess ||
    !value || length!=sizeof(enable))return false;
 memcpy(&enable,value,sizeof(enable));
#else
 PE_parse_boot_argn("raphael-offline-keystore",&enable,sizeof(enable));
#endif
 return enable==1;
}
// The explicitly enabled scratch Data volume has no passcode. In the pinned
// 21H461 SBFMobileKeyBag ABI, sls == 3 means no passcode; sls == 0 means
// unlocked and still makes hasPasscodeSet true. This service has no key or
// passcode operations and must never describe a protected user volume.
uint32_t native_aks_lock_state(void) { return 3; }
void native_keyevents_open_refused(void) {raphael_offline_aks_refused=raphael_offline_aks_refused+1;}
void native_aks_opened(void) {raphael_offline_aks_opens=raphael_offline_aks_opens+1;}
void native_aks_call(uint32_t selector,int32_t result) {
 if(raphael_offline_aks_calls==0 || selector!=raphael_offline_aks_selector)
  IOLog("RPH AKS selector=%u result=%x\n",selector,(uint32_t)result);
 raphael_offline_aks_calls=raphael_offline_aks_calls+1;raphael_offline_aks_selector=selector;
 raphael_offline_aks_result=(uint32_t)result;
 if(selector<64)raphael_offline_aks_selectors=raphael_offline_aks_selectors|(1ULL<<selector);
}
IOService *native_keyevents_allocate(void);
}
extern "C" void raphael_offline_keystore_probe(void) {
 if(!native_aks_state_enabled())return;
 if(raphael_offline_aks_stage)panic("raphael offline AKS: duplicate publication");
 raphael_offline_aks_stage=1;
 IOService *service=native_keyevents_allocate();
 if(!service || !service->init() || !service->attach(IOService::getPlatform()))
  panic("raphael offline AKS: service construction");
 if(!service->setProperty("RaphaelEphemeralOnly",true) ||
    !service->setProperty("HardwareKeyProtectionAvailable",false) ||
    !service->start(IOService::getPlatform()))panic("raphael offline AKS: service publication");
 raphael_offline_aks_stage=2;
 IOLog("RPH AKS ephemeral unprotected state service published\n");
}
