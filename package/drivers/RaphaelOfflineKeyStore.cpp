// SPDX-License-Identifier: BSD-2-Clause-Patent
// Ephemeral, unprotected development Data; optional software wrapping, no passcode protection.
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
// unlocked and still makes hasPasscodeSet true. Optional software wrapping
// does not turn this scratch volume into a protected user volume.
uint32_t native_aks_lock_state(void) { return 3; }
// The same private port-assigned UUID already consumed by IOPlatformUUID.
// No board identifier or fallback is invented when the ADT input is absent.
size_t native_aks_device_id(uint8_t *out,size_t capacity) {
 DTEntry chosen=nullptr;const void *value=nullptr;unsigned length=0;
 if(!out || capacity<16 || SecureDTLookupEntry(nullptr,"/chosen",&chosen)!=kSuccess ||
    SecureDTGetProperty(chosen,"unixnu-platform-uuid",&value,&length)!=kSuccess ||
    !value || length!=16)return 0;
 memcpy(out,value,16);return 16;
}
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
