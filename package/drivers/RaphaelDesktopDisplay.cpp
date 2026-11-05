#if RAPHAEL_OFFLINE_KEYSTORE
extern "C" void raphael_offline_keystore_probe(void);
#endif
// SPDX-License-Identifier: BSD-2-Clause-Patent
// Original-family development adapter over the audited inherited framebuffer.
#include "OriginalLegacyFramebufferABI.h"
#include "NativeLegacyRequest.h"
#include <IOKit/IOMemoryDescriptor.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IODeviceMemory.h>
#include <libkern/c++/OSArray.h>
#include <pexpert/pexpert.h>
#if RAPHAEL_HANDSET_DISPLAY
#include <pexpert/device_tree.h>
#endif
extern "C" kern_return_t OSKextLoadKextWithIdentifier(const char *);
// Each accessor is bound to the unchanged original IOSurface getter after the
// build script checks its actual instructions in this exact OS candidate.
extern "C" IOMemoryDescriptor *raphael_surface_descriptor(OSObject *);
extern "C" uint64_t raphael_surface_width(OSObject *),raphael_surface_height(OSObject *);
extern "C" uint64_t raphael_surface_stride(OSObject *),raphael_surface_allocation(OSObject *);
extern "C" uint32_t raphael_surface_format(OSObject *),raphael_surface_planes(OSObject *);
extern "C" void raphael_legacy_mark_swap(void *,const void *,uint32_t);
extern "C" {
volatile unsigned raphael_display_stage, raphael_display_guard, raphael_display_clients;
volatile unsigned raphael_display_hardware_stage,raphael_display_video_status;
volatile uint64_t raphael_display_row_bytes,raphael_display_depth,raphael_display_rotate,raphael_display_map_length;
volatile int raphael_display_surface_status=-1, raphael_display_family_status=-1;
volatile int raphael_display_meta_status=-1;
// All counters describe memory presentation only, never GPU or panel fences.
volatile uint64_t raphael_display_validations,raphael_display_rejected,raphael_display_kicks;
volatile uint64_t raphael_display_frames,raphael_display_blank_frames,raphael_display_retired;
volatile uint64_t raphael_display_bytes,raphael_display_nonblack,raphael_display_reject_reason;
volatile uint64_t raphael_display_transfer_status,raphael_display_client_status,raphael_display_power_status;
__attribute__((noinline)) void raphael_display_frame_checkpoint(void) { __asm__ volatile("" ::: "memory"); }
volatile uint64_t raphael_display_base, raphael_display_width, raphael_display_height;
__attribute__((noinline)) void raphael_display_checkpoint(void) { __asm__ volatile("" ::: "memory"); }
}
class RaphaelDesktopDisplay : public IOMobileFramebufferLegacy {
 OSDeclareDefaultStructors(RaphaelDesktopDisplay)
 IOMemoryMap *mapping=nullptr;
 const void *validated[8]={};
 bool kicking=false;
 static uint32_t word(const void *p,unsigned offset) {uint32_t v;memcpy(&v,(const char *)p+offset,4);return v;}
 static void *pointer(const void *p,unsigned offset) {void *v;memcpy(&v,(const char *)p+offset,8);return v;}
 static void putPointer(void *p,unsigned offset,const void *v) {memcpy((char *)p+offset,&v,8);}
 bool accepted(const void *request) const {for(auto p:validated)if(p==request)return request;return false;}
 void forget(const void *request) {for(auto &p:validated)if(p==request)p=nullptr;}
 bool remember(const void *request) {
  if(accepted(request))return true;
  for(auto &p:validated)if(!p){p=request;return true;}return false;
 }
 bool onlyPending(const void *request) const {
  return request && !pointer(this,0x1560) && pointer(this,0x1568)==request &&
   !pointer(request,0xb90) && pointer(request,0xb98)==(const char *)this+0x1568 &&
   pointer(this,0x1570)==(const char *)request+0xb90;
 }
 bool activateOnlyPending(const void *request) {
  if(!onlyPending(request))return false;
  // Exact original TAILQ removal for a single head, preserving the family's
  // reference and generation ownership. The original completion releases it.
  putPointer(this,0x1560,request);
  putPointer(this,0x1568,nullptr);
  putPointer(this,0x1570,(char *)this+0x1568);
  raphael_legacy_mark_swap(this,request,3);
  return true;
 }
 bool checkedSurface(OSObject *surface) const {
  if(!surface || !surface->metaCast("IOSurface"))return false;
  IOMemoryDescriptor *memory=raphael_surface_descriptor(surface);
  return raphael_surface_width(surface)>=raphael_display_width &&
   raphael_surface_height(surface)>=raphael_display_height &&
   raphael_surface_format(surface)==0x42475241 && raphael_surface_planes(surface)==0 &&
   memory && memory->metaCast("IOMemoryDescriptor") &&
   native_legacy_surface_bounds((uint32_t)raphael_display_width,(uint32_t)raphael_display_height,
    raphael_surface_stride(surface),raphael_surface_allocation(surface),memory->getLength());
 }
public:
 void free() override { OSSafeReleaseNULL(mapping);IOMobileFramebufferLegacy::free(); }
 bool start(IOService *provider) override {
  raphael_display_stage=5;
  bool result=IOMobileFramebufferLegacy::start(provider);
  raphael_display_stage=result?6:7;
  if(result && mapping) {
   // This backend keeps the firmware scanout logically active. The original
   // setter owns both requested (+0x16cc) and powered (+0x16d0) state words.
   // Announcing only power leaves requested zero: the original selector 5
   // then returns success while deliberately skipping validation and queuing.
   // This is a logical always-on policy, not a physical panel power control.
   struct State {uint32_t skipRequested,requested,skipPowered,powered;uint8_t changed,pad[11];};
   State state={0,1,0,1,1,{}};
   raphael_display_power_status=(uint32_t)IOMobileFramebufferLegacy::setDisplayState(&state,false);
  }
  raphael_display_checkpoint();return result;
 }
 bool startHardware() override {
  raphael_display_hardware_stage=1;
  PE_Video video={};IOService *provider=getProvider();
  raphael_display_video_status=PE_current_console(&video);
  raphael_display_base=video.v_baseAddr;raphael_display_width=video.v_width;raphael_display_height=video.v_height;
  raphael_display_row_bytes=video.v_rowBytes;raphael_display_depth=video.v_depth;raphael_display_rotate=video.v_rotate;
  if(!provider || raphael_display_video_status || !video.v_baseAddr || !video.v_width ||
   !video.v_height || video.v_depth!=32 || video.v_rotate || video.v_width>16384 ||
   video.v_height>16384 || video.v_rowBytes<video.v_width*4 ||
   video.v_rowBytes>UINT64_MAX/video.v_height)return false;
  raphael_display_hardware_stage=2;
  mapping=provider->mapDeviceMemoryWithIndex(0,kIOMapInhibitCache);
  raphael_display_map_length=mapping?mapping->getLength():0;
  if(!mapping || !mapping->getVirtualAddress() || mapping->getPhysicalAddress()!=video.v_baseAddr ||
    mapping->getLength()!=video.v_rowBytes*video.v_height)return false;
  raphael_display_hardware_stage=3;
  installBootDimensions((uint32_t)video.v_width,(uint32_t)video.v_height);
  raphael_display_base=video.v_baseAddr;raphael_display_width=video.v_width;raphael_display_height=video.v_height;
  raphael_display_stage=4;return true;
 }
 bool isMainDisplay() override {return mapping!=nullptr;}
 bool validateSwap(const void *request) override {
  raphael_display_validations=raphael_display_validations+1;
  unsigned reason=1;bool valid=false;
  if(request && mapping) {
   reason=2;OSObject *surfaces[4]={};memcpy(surfaces,(const char *)request+2624,sizeof(surfaces));
   if(!surfaces[1] && !surfaces[2] && !surfaces[3]) {
    if(!surfaces[0])valid=native_legacy_blank_state(word(request,792),word(request,796),word(request,800));
    else if(native_legacy_single_layer_state(word(request,792),word(request,796),word(request,800))) {
     reason=3;bool geometry=word(request,816)==raphael_display_width && word(request,820)==raphael_display_height;
     const unsigned rectOffsets[]={17,81};
     for(unsigned offset:rectOffsets) {
      uint32_t rect[4];memcpy(rect,(const char *)request+offset,sizeof(rect));
      geometry=geometry && !rect[0] && !rect[1] && rect[2]==raphael_display_width && rect[3]==raphael_display_height;
     }
     for(unsigned offset=804;offset<=812;offset+=4)geometry=geometry && !word(request,offset);
     reason=4;valid=geometry && checkedSurface(surfaces[0]);
    }
   }
   if(valid && !remember(request)){reason=5;valid=false;}
  }
  if(!valid){forget(request);raphael_display_rejected=raphael_display_rejected+1;}
  raphael_display_reject_reason=valid?0:reason;
  return valid;
 }
 void kickSwapQueue() override {
  raphael_display_kicks=raphael_display_kicks+1;
  if(kicking || !mapping)return;
  kicking=true;
  const void *request=pointer(this,0x1568);
  if(!accepted(request) || !onlyPending(request)){kicking=false;return;}
  auto surface=(OSObject *)pointer(request,2624);
  bool copied=false;
  uint64_t length=raphael_display_width*raphael_display_height*4;
  uint32_t width=(uint32_t)raphael_display_width,height=(uint32_t)raphael_display_height;
  if(!surface) {
   copied=native_legacy_fill_pixels((volatile void *)mapping->getVirtualAddress(),mapping->getLength(),
    raphael_display_row_bytes,width,height,0xff000000);
   if(copied){raphael_display_blank_frames=raphael_display_blank_frames+1;raphael_display_nonblack=0;}
  } else if(checkedSurface(surface)) {
   IOMemoryDescriptor *memory=raphael_surface_descriptor(surface);
   IOReturn prepared=memory->prepare(kIODirectionOut);
   raphael_display_transfer_status=(uint32_t)prepared;
   if(prepared==kIOReturnSuccess) {
    IOMemoryMap *source=memory->map();
    if(source && source->getVirtualAddress() && source->getLength()>=raphael_surface_allocation(surface)) {
     uint64_t stride=raphael_surface_stride(surface);
     copied=native_legacy_copy_pixels((volatile void *)mapping->getVirtualAddress(),mapping->getLength(),
      raphael_display_row_bytes,(const void *)source->getVirtualAddress(),source->getLength(),stride,width,height);
     if(copied && raphael_display_frames<8) {
      uint64_t scan[5];
      if(native_legacy_frame_scan((const void *)source->getVirtualAddress(),source->getLength(),stride,width,height,scan))
       raphael_display_nonblack=scan[0];
     }
    }
    OSSafeReleaseNULL(source);
    IOReturn completed=memory->complete(kIODirectionOut);
    if(completed!=kIOReturnSuccess){copied=false;raphael_display_transfer_status=(uint32_t)completed;}
   }
  }
  if(copied) {
   __asm__ volatile("dsb sy" ::: "memory");
   raphael_display_frames=raphael_display_frames+1;raphael_display_bytes=raphael_display_bytes+length;
   if(activateOnlyPending(request)) {
    forget(request);
    IOMobileFramebufferLegacy::completeCurrentSwap();
    raphael_display_retired=raphael_display_retired+1;
    raphael_display_transfer_status=0;
   } else raphael_display_transfer_status=(uint32_t)kIOReturnBusy;
   raphael_display_frame_checkpoint();
  } else if(!raphael_display_transfer_status)raphael_display_transfer_status=(uint32_t)kIOReturnUnsupported;
  kicking=false;
 }
 IOReturn collectCompletionReports(uint32_t,void *,uint32_t *count,uint32_t) override {
  if(count)*count=0;return kIOReturnUnsupported;
 }
 void registerService(IOOptionBits options=0) override {
  IOService::registerService(options);raphael_display_stage=8;raphael_display_checkpoint();
 }
 IOReturn getDotPitch(uint32_t *pitch) override {
  if(!pitch)return kIOReturnBadArgument;*pitch=0;return kIOReturnNotFound;
 }
 IOReturn supportedFrameInfo(uint32_t,uint32_t *count,char *key,uint32_t *mask) override {
  if(!count || !key || !mask)return kIOReturnBadArgument;
  *count=0;*mask=0;bzero(key,64);return kIOReturnUnsupported;
 }
 IOReturn newUserClient(task_t task,void *security,UInt32 type,IOUserClient **client) override {
  // Mark the call pending before counting its entry. The single-CPU diagnostic
  // observer must not read the initial success value while the parent sleeps.
  raphael_display_client_status=(uint32_t)kIOReturnNotReady;
  raphael_display_clients=raphael_display_clients+1;
  IOReturn status=IOMobileFramebufferLegacy::newUserClient(task,security,type,client);
  raphael_display_client_status=(uint32_t)status;return status;
 }
 #define GUARD(n) __attribute__((noreturn,noinline)) void opaque##n() override {raphael_display_guard=n;panic("raphael display: unsupported ABI slot %u",n);}
 GUARD(211) GUARD(245) GUARD(246) GUARD(306) GUARD(307) GUARD(338) GUARD(345)
 #undef GUARD
};
OSDefineMetaClassAndStructors(RaphaelDesktopDisplay,IOMobileFramebufferLegacy)
// This initializer is removed from __mod_init_func and invoked after the original
// family is genuinely loaded. The original super metaclass must exist first.
struct RaphaelMetaPlacement {};
inline void *operator new(size_t,void *where,RaphaelMetaPlacement) {return where;}
static void raphael_display_class_init(void) {
 ::new ((void *)&RaphaelDesktopDisplay::gMetaClass,RaphaelMetaPlacement{}) RaphaelDesktopDisplay::MetaClass;
}
extern "C" void native_legacy_display_probe(void) { }
extern "C" void native_legacy_display_late_probe(void) {
 unsigned enable=0;PE_parse_boot_argn("raphael-desktop-display",&enable,sizeof(enable));
#if RAPHAEL_HANDSET_DISPLAY
 // Only the explicit handset profile consumes this owned handoff opt-in.
 // Firmware independently backs up and validates the full current Boot_Video.
 DTEntry chosen=nullptr;void const *value=nullptr;unsigned length=0;
 if(SecureDTLookupEntry(nullptr,"/chosen",&chosen)!=kSuccess ||
    SecureDTGetProperty(chosen,"unixnu,diagnostic-display",&value,&length)!=kSuccess ||
    !value || length!=sizeof(enable))return;
 memcpy(&enable,value,sizeof(enable));
#endif
 if(enable!=1)return;
#if RAPHAEL_OFFLINE_KEYSTORE
 raphael_offline_keystore_probe();
#endif
 raphael_display_stage=1;
 raphael_display_family_status=OSKextLoadKextWithIdentifier("com.apple.iokit.IOMobileGraphicsFamily");
 raphael_display_surface_status=OSKextLoadKextWithIdentifier("com.apple.iokit.IOSurface");
 if(raphael_display_family_status || raphael_display_surface_status){raphael_display_checkpoint();return;}
 void *handle=OSMetaClass::preModLoad("__kernel__");
 if(!handle)panic("raphael display: no metaclass load handle");
 raphael_display_class_init();
 raphael_display_meta_status=OSMetaClass::postModLoad(handle);
 if(raphael_display_meta_status)panic("raphael display: metaclass registration %d",raphael_display_meta_status);
 raphael_display_stage=2;
 PE_Video video={};if(PE_current_console(&video) || !video.v_baseAddr || !video.v_rowBytes ||
  !video.v_height || video.v_rowBytes>UINT64_MAX/video.v_height)return;
 IOService *provider=new IOService;
 if(!provider || !provider->init() || !provider->attach(IOService::getPlatform()))panic("raphael display: provider");
 provider->setName("RaphaelGOP");
 IODeviceMemory *memory=IODeviceMemory::withRange(video.v_baseAddr,video.v_rowBytes*video.v_height);
 OSArray *memories=memory?OSArray::withObjects((const OSObject **)&memory,1):nullptr;
 if(!memories)panic("raphael display: framebuffer resource");
 provider->setDeviceMemory(memories);memories->release();memory->release();
 RaphaelDesktopDisplay *display=new RaphaelDesktopDisplay;
 if(!display || !display->init() || !display->attach(provider))panic("raphael display: instance");
 raphael_display_stage=3;
 if(!display->start(provider))panic("raphael display: original start failed");
 raphael_display_checkpoint();
}
