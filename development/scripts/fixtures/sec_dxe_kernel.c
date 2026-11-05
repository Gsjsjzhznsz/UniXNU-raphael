/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Emulator-only receiver: UART comes from the emulator FDT, never a phone PA.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <libfdt.h>
#ifndef EXPECT_MANAGER_KEYS
#define EXPECT_MANAGER_KEYS 0
#endif
#ifndef EXPECT_VISIBLE_MANAGER
#define EXPECT_VISIBLE_MANAGER 0
#endif
#ifndef EXPECT_RAM_WRITE
#define EXPECT_RAM_WRITE 0
#endif
#ifndef EXPECT_RAM_CACHE_WRITE
#define EXPECT_RAM_CACHE_WRITE 0
#endif
#ifndef EXPECT_RAM_MAPPED
#define EXPECT_RAM_MAPPED 0
#endif
#ifndef EXPECT_RAM_READ
#define EXPECT_RAM_READ 0
#endif
#ifndef EXPECT_PHYSICAL_TIMER
#define EXPECT_PHYSICAL_TIMER 0
#endif
#ifndef EXPECT_TIMER_IRQ
#define EXPECT_TIMER_IRQ 0
#endif
#ifndef EXPECT_TIMER_ROUTE_FAULT
#define EXPECT_TIMER_ROUTE_FAULT 0
#endif
#ifndef EXPECT_TIMER_ROUTE
#define EXPECT_TIMER_ROUTE 0
#endif
#ifndef EXPECT_GIC_ENABLE_MAP
#define EXPECT_GIC_ENABLE_MAP 0
#endif
#ifndef EXPECT_PPI
#define EXPECT_PPI 0
#endif
#ifndef EXPECT_TIMER_SOURCE
#define EXPECT_TIMER_SOURCE 0
#endif
#ifndef EXPECT_ICC
#define EXPECT_ICC 0
#endif
#ifndef EXPECT_ICC_FAULT
#define EXPECT_ICC_FAULT 0
#endif
#ifndef EXPECT_GIC
#define EXPECT_GIC 0
#endif
#ifndef EXPECT_QEMU_ARCH
#define EXPECT_QEMU_ARCH 0
#endif
#ifndef EXPECT_DARWIN
#define EXPECT_DARWIN 0
#endif
#ifndef EXPECT_PAYLOAD
#define EXPECT_PAYLOAD 0
#endif
#ifndef EXPECT_INPUT_PROTOCOL
#define EXPECT_INPUT_PROTOCOL 0
#endif
#ifndef EXPECT_INPUT_READ
#define EXPECT_INPUT_READ 0
#endif
#ifndef EXPECT_INPUT_PROBE
#define EXPECT_INPUT_PROBE 0
#endif
#ifndef EXPECT_GOP
#define EXPECT_GOP 0
#endif
#ifndef EXPECT_FAULT
#define EXPECT_FAULT 0
#endif
#ifndef EXPECT_PIXEL_WRITE
#define EXPECT_PIXEL_WRITE 0
#endif
#ifndef EXPECT_PIXEL_PROBE
#define EXPECT_PIXEL_PROBE 0
#endif
#ifndef EXPECT_SMMU_PROBE
#define EXPECT_SMMU_PROBE 0
#endif
#ifndef EXPECT_DISPLAY_PROBE
#define EXPECT_DISPLAY_PROBE 0
#endif
#ifndef EXPECTED_STAGE
#define EXPECTED_STAGE 6
#endif
static volatile uint32_t *uart;
static int failures;
static void text(const char *s) { while (*s) *uart = (unsigned char)*s++; }
#if defined(REPLAY_CONTEXT_BASE) || EXPECT_GIC
static void hex_value(uint64_t value) {
  const char digits[] = "0123456789abcdef";
  text("0x");
  for (int i = 60; i >= 0; i -= 4) *uart = digits[(value >> i) & 15];
}
#endif
static void check(int good, const char *name) {
  text(good ? "PASS " : "FAIL "); text(name); text("\n");
  if (!good) ++failures;
}
static uint64_t reg_value(const fdt64_t *r, unsigned i) { return fdt64_to_cpu(r[i]); }

void fixture_main(const void *fdt, const unsigned char *image) {
  int len, node = fdt_node_offset_by_compatible(fdt, -1, "arm,pl011");
  const fdt32_t *reg = fdt_getprop(fdt, node, "reg", &len);
  if (!reg || len < 16) for (;;) __asm__ volatile("wfe");
  uart = (volatile uint32_t *)(uintptr_t)(((uint64_t)fdt32_to_cpu(reg[0]) << 32) | fdt32_to_cpu(reg[1]));
  node = fdt_path_offset(fdt, "/chosen");
  const fdt64_t *r = fdt_getprop(fdt, node, "raphael,sec-dxe", &len);
  const char *id = fdt_getprop(fdt, node, "raphael,sec-dxe-id", NULL);
  const char *args = fdt_getprop(fdt, node, "bootargs", NULL);
  check(r && len == 48 * 8, "SEC/DXE result record");
  int ui_len=0;
  const fdt64_t *ui=fdt_getprop(fdt,node,"raphael,manager-ui",&ui_len);
  if(EXPECT_VISIBLE_MANAGER){
    check(ui&&ui_len==128&&reg_value(ui,0)==1,"visible manager phase record");
    if(ui&&ui_len==128){
      const unsigned char *bytes=(const void *)ui;const char digits[]="0123456789abcdef";
      text("MANAGER_UI_WIRE ");for(unsigned i=0;i<128;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      check(reg_value(ui,1)==(EXPECTED_STAGE==6?5:1),"QEMU explicitly reports absent inherited display/input; no visible claim");
    }
  }else check(!ui,"visible manager transaction disabled by default");
  int ram_len=0;
  const fdt64_t *ram=fdt_getprop(fdt,node,"raphael,ram-read",&ram_len);
  if(EXPECT_RAM_READ) {
    check(ram&&ram_len==26*8&&reg_value(ram,0)==1,"sparse RAM read record");
    if(ram&&ram_len==26*8) {
      const unsigned char *bytes=(const void *)ram;const char digits[]="0123456789abcdef";
      text("RAM_READ_WIRE ");for(unsigned i=0;i<26*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      if(EXPECT_FAULT==3&&!EXPECT_RAM_MAPPED) {
        check(reg_value(ram,1)==2&&reg_value(ram,6)==256&&reg_value(ram,7)==1&&reg_value(ram,8)==0&&reg_value(ram,9)==reg_value(ram,3),"fatal load-site UDF preserves partial RAM result");
      } else {
      check(reg_value(ram,1)==3&&reg_value(ram,2)==0&&reg_value(ram,7)==256&&reg_value(ram,8)==256,"all 256 sparse reads completed");
      uint64_t digest=14695981039346656037ULL,nonzero=0;
      for(uint64_t off=0;off<reg_value(ram,4);off+=reg_value(ram,5))for(unsigned tail=0;tail<2;++tail){
        uint64_t a=reg_value(ram,3)+off+(tail?reg_value(ram,5)-8:0),v=*(volatile const uint64_t *)(uintptr_t)a;
        digest=(digest^a)*1099511628211ULL;digest=(digest^v)*1099511628211ULL;if(v)++nonzero;
      }
      check(digest==reg_value(ram,10)&&nonzero==reg_value(ram,11),"receiver independently recomputes RAM digest and nonzero count");
      check(reg_value(ram,23)==4&&(reg_value(ram,24)&0x1005)==0&&(reg_value(ram,25)&0x3c0)==0x3c0,"RAM read only with MMU/cache off and DAIF masked");
      }
    }
  }else check(!ram,"sparse RAM read disabled by default");
  int mapped_len=0;const fdt64_t *mapped=fdt_getprop(fdt,node,"raphael,ram-mapped",&mapped_len);
  if(EXPECT_RAM_MAPPED){
    check(mapped&&mapped_len==27*8&&reg_value(mapped,0)==1,"independent mapped RAM wire");
    if(mapped&&mapped_len==27*8){
      const unsigned char *bytes=(const void *)mapped;const char digits[]="0123456789abcdef";
      text("RAM_MAPPED_WIRE ");for(unsigned i=0;i<27*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      if(EXPECT_FAULT==3){
        check(reg_value(mapped,1)==2&&reg_value(mapped,7)==1&&reg_value(mapped,8)==0&&reg_value(mapped,19)==1&&reg_value(mapped,20)==1,"mapped load-site UDF preserves translated partial record");
      }else if(EXPECTED_STAGE==2){
        check(reg_value(mapped,1)==1&&reg_value(mapped,7)==0,"mapped RAM armed before MMU; no translated reads claimed");
      }else{
        check(reg_value(mapped,1)==3&&reg_value(mapped,7)==256&&reg_value(mapped,8)==256,"mapped 256 sparse reads complete");
        check(reg_value(mapped,10)==reg_value(mapped,11)&&reg_value(mapped,11)==reg_value(ram,10),"before and after MMU digests equal");
        check(reg_value(mapped,19)==256&&reg_value(mapped,20)==256&&reg_value(mapped,21)==256,"read translations write denial and PAR preservation complete");
        check((reg_value(mapped,17)&0x1005)==0x1005,"MMU and caches enabled during mapped probe");
      }
    }
  }else check(!mapped,"mapped RAM probe disabled by default");
  int cache_len=0;const fdt64_t *cache=fdt_getprop(fdt,node,"raphael,ram-cache-write",&cache_len);
  if(EXPECT_RAM_CACHE_WRITE){
    check(cache&&cache_len==39*8&&reg_value(cache,0)==1,"cached RAM independent metadata and engine wire");
    if(cache&&cache_len==39*8){
      const unsigned char *bytes=(const void *)cache;const char digits[]="0123456789abcdef";
      text("RAM_CACHE_WIRE ");for(unsigned i=0;i<39*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      if(EXPECT_FAULT==3)check(reg_value(cache,1)==1&&reg_value(cache,16)==0,"mapped-load failure precedes all cached stores");
      else if(EXPECTED_STAGE==2)check(reg_value(cache,1)==1&&reg_value(cache,16)==0,"cached write armed only; no stores before MMU");
      else{
        uint64_t tested=EXPECT_FAULT==4?1:EXPECT_RAM_CACHE_WRITE;int equal=1;
        for(uint64_t i=0;i<tested*512;++i){uint64_t address=reg_value(cache,3)+i*8;if(*(volatile const uint64_t *)(uintptr_t)address!=(address^0x0123456789abcdefULL))equal=0;}
        check(equal,"independent MMU-off receiver verifies every restored DRAM word");
        check(reg_value(cache,14)==1&&reg_value(cache,15)==256,"read-only map restored and queried");
        check(reg_value(cache,26)==0&&reg_value(cache,25)==0,"cached engine has no dirty page or retained backup");
        if(EXPECT_FAULT==4)check(reg_value(cache,17)==2&&reg_value(cache,23)==0&&reg_value(cache,27)==1,"partial cached write UDF restored one full original page");
        else check(reg_value(cache,17)==3&&reg_value(cache,23)==EXPECT_RAM_CACHE_WRITE,"all requested cached pages completed");
      }
    }
  }else check(!cache,"cached RAM write disabled by default");
  int rw_len=0;const fdt64_t *rw=fdt_getprop(fdt,node,"raphael,ram-write",&rw_len);
  if(EXPECT_RAM_WRITE){
    check(rw&&rw_len==23*8,"RAM write transaction record");
    if(rw&&rw_len==23*8){
      const unsigned char *bytes=(const void *)rw;const char digits[]="0123456789abcdef";
      text("RAM_WRITE_WIRE ");for(unsigned i=0;i<23*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      int identical=1;
      for(uint64_t i=0;i<EXPECT_RAM_WRITE*512;++i){uint64_t a=reg_value(rw,3)+i*8;if(*(volatile const uint64_t *)(uintptr_t)a!=(a^0x0123456789abcdefULL))identical=0;}
      check(identical,"independent receiver verifies every original RAM word after return");
      check(reg_value(rw,10)==0&&reg_value(rw,9)==0&&reg_value(rw,11)==(EXPECT_FAULT==4?1:EXPECT_RAM_WRITE),"no dirty or retained backup after verified page restoration");
      if(EXPECT_FAULT==4)check(reg_value(rw,1)==2&&reg_value(rw,7)==0,"fatal UDF returns only after dirty partial-page recovery");
      else check(reg_value(rw,1)==3&&reg_value(rw,7)==EXPECT_RAM_WRITE&&reg_value(rw,16)==EXPECT_RAM_WRITE*512,"requested pages complete with independent restore readback");
    }
  }else check(!rw,"RAM write disabled by default");
  int gic_len=0;
  const fdt64_t *gic=fdt_getprop(fdt,node,"raphael,gic-readonly",&gic_len);
#if EXPECT_GIC
  uint64_t mpidr;__asm__ volatile("mrs %0,mpidr_el1":"=r"(mpidr));
  text("GIC_MPIDR ");hex_value(mpidr);text("\n");
  check(gic&&gic_len==80*8&&reg_value(gic,0)==1&&reg_value(gic,1)==4,"read-only GIC complete snapshot");
  if(gic&&gic_len==80*8) {
    const unsigned char *bytes=(const void *)gic;const char digits[]="0123456789abcdef";
    text("GIC_WIRE ");for(unsigned i=0;i<80*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    check(reg_value(gic,9)==mpidr&&r&&reg_value(r,11)==mpidr,"read-only GIC matches independently read MPIDR");
    check(reg_value(gic,11)>0&&reg_value(gic,12)<reg_value(gic,11),"read-only GIC boot affinity found");
  }
#else
  check(!gic,"GIC read-only probe disabled by default");
#endif
  int em_len=0;const fdt64_t *em=fdt_getprop(fdt,node,"raphael,gic-enable-map",&em_len);
#if EXPECT_GIC_ENABLE_MAP
  check(em&&em_len==60*8&&reg_value(em,0)==1,"two-pass GIC enable map record");
  if(em&&em_len==60*8) {
    const unsigned char *bytes=(const void *)em;const char digits[]="0123456789abcdef";
    text("GIC_ENABLE_MAP_WIRE ");for(unsigned i=0;i<60*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    check(reg_value(em,1)==3||reg_value(em,1)==4,"GIC enable map complete evidence");
    check(gic&&gic_len==80*8&&reg_value(em,4)==(reg_value(gic,14)&31)&&reg_value(em,5)==reg_value(gic,11),"GIC map dimensions match collected TYPER and frames");
    check(reg_value(em,3)==3+2*(reg_value(em,4)+2*reg_value(em,5)),"GIC map bounded read count");
  }
#else
  check(!em,"GIC enable map disabled by default");
#endif
  int ppi_len=0;const fdt64_t *ppi=fdt_getprop(fdt,node,"raphael,ppi-enable-probe",&ppi_len);
#if EXPECT_PPI
  check(ppi&&ppi_len==20*8&&reg_value(ppi,0)==1,"single-PPI permission record");
  if(ppi&&ppi_len==20*8) {
    const unsigned char *bytes=(const void *)ppi;const char digits[]="0123456789abcdef";
    text("PPI_WIRE ");for(unsigned i=0;i<20*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    uint64_t intid=reg_value(ppi,3),mask=reg_value(ppi,6),base=reg_value(ppi,5);
    check(intid>=16&&intid<32&&mask==(1ULL<<intid),"PPI mask derived from FDT number");
    check((reg_value(ppi,1)==3||reg_value(ppi,1)==6)&&reg_value(ppi,17)==1&&reg_value(ppi,13)==2,"PPI attempt completes with exact restoration");
    check(reg_value(ppi,7)==reg_value(ppi,9)&&*(volatile uint32_t *)(uintptr_t)(base+0x100)==reg_value(ppi,7),"receiver independently reads restored PPI enable state");
    check(gic&&gic_len==80*8&&*(volatile uint32_t *)(uintptr_t)reg_value(gic,4)==reg_value(ppi,14)&&reg_value(ppi,14)==reg_value(ppi,15),"receiver independently verifies unchanged distributor control");
  }
#else
  check(!ppi,"PPI enable probe disabled by default");
#endif
  int ts_len=0;
  const fdt64_t *ts=fdt_getprop(fdt,node,"raphael,timer-source",&ts_len);
#if EXPECT_TIMER_SOURCE
  check(ts&&ts_len==17*8&&reg_value(ts,0)==1,"masked timer source record");
  if(ts&&ts_len==17*8) {
    const unsigned char *bytes=(const void *)ts;const char digits[]="0123456789abcdef";
    text("TIMER_SOURCE_WIRE ");for(unsigned i=0;i<17*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    check(!(reg_value(ts,4)&1)&&((reg_value(ts,4)^reg_value(ts,12))&3)==0&&reg_value(ts,5)==reg_value(ts,13),"CNTP originally disabled and restored");
    check(reg_value(ts,14)==5&&reg_value(ts,9)==reg_value(ts,7),"CNTP write count and CVAL readback");
    uint64_t post_ctl,post_cval,post_vctl,post_vcval;
    __asm__ volatile("mrs %0,cntp_ctl_el0\n mrs %1,cntp_cval_el0\n mrs %2,cntv_ctl_el0\n mrs %3,cntv_cval_el0":"=r"(post_ctl),"=r"(post_cval),"=r"(post_vctl),"=r"(post_vcval));
    check(((post_ctl^reg_value(ts,4))&3)==0&&post_cval==reg_value(ts,5),"receiver independently verifies physical timer restoration");
    int before_len=0;const fdt64_t *before_icc=fdt_getprop(fdt,node,"raphael,icc-readonly",&before_len);
    check(before_icc&&before_len==26*8&&((post_vctl^reg_value(before_icc,19))&3)==0&&post_vcval==reg_value(before_icc,20),"virtual timer writable state remains unchanged");

    if(EXPECT_ICC_FAULT)check(reg_value(ts,1)==3&&reg_value(ts,2)==3&&(reg_value(ts,15)>>26)==0&&reg_value(ts,16)>0&&reg_value(ts,11)==0,"CNTP simulated write failure restored after CVAL change");
    else {
      check(reg_value(ts,1)==8&&reg_value(ts,2)==0&&reg_value(ts,8)==7&&reg_value(ts,11)>0,"masked CNTP reaches ISTATUS");
      check(reg_value(ts,10)>=reg_value(ts,7)&&reg_value(ts,10)-reg_value(ts,6)>=reg_value(ts,3)/100,"CNTP elapsed counter independently constrained");
    }
  }
#else
  check(!ts,"masked timer source disabled by default");
#endif
  int irq_len=0;
  const fdt64_t *irq=fdt_getprop(fdt,node,"raphael,timer-irq",&irq_len);
#if EXPECT_TIMER_IRQ
  check(irq&&irq_len==24*8&&reg_value(irq,0)==1,"single physical timer IRQ record");
  if(irq&&irq_len==24*8) {
    const unsigned char *bytes=(const void *)irq;const char digits[]="0123456789abcdef";
    text("TIMER_IRQ_WIRE ");for(unsigned i=0;i<24*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    check(reg_value(irq,1)==5&&reg_value(irq,8)==1&&reg_value(irq,9)==reg_value(irq,2)&&reg_value(irq,16)==1,"exactly one target PPI acknowledged and EOId");
    check((reg_value(irq,12)&0x3c0)==0x340&&reg_value(irq,14)==0x340&&reg_value(irq,13)==0x3c0&&reg_value(irq,15)==0x3c0,"exception SPSR proves only IRQ unmasked and mask restored");
    check(reg_value(irq,17)==1&&reg_value(irq,18)==0&&reg_value(irq,19)==0&&reg_value(irq,23)==1,"source withdrawn, no spurious or unexpected ID, active pointer cleared");
    check(reg_value(irq,21)-80==reg_value(irq,22)&&reg_value(irq,20)==1,"IRQ preserves bounded SPx scratch frame");
  }
#else
  check(!irq,"one-shot timer IRQ disabled by default");
#endif
  int route_len=0;
  const fdt64_t *route=fdt_getprop(fdt,node,"raphael,timer-route",&route_len);
#if EXPECT_TIMER_ROUTE
  check(route&&route_len==44*8&&reg_value(route,0)==1,"physical timer route record");
  if(route&&route_len==44*8) {
    const unsigned char *bytes=(const void *)route;const char digits[]="0123456789abcdef";
    text("TIMER_ROUTE_WIRE ");for(unsigned i=0;i<44*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    check(reg_value(route,1)==(EXPECT_TIMER_ROUTE_FAULT?3:6)&&reg_value(route,2)==(EXPECT_TIMER_ROUTE_FAULT?2:0)&&reg_value(route,41)==1,"physical timer routed and restoration passed");
    if(EXPECT_TIMER_ROUTE_FAULT)check(reg_value(route,34)==0&&reg_value(route,42)>>26==0&&reg_value(route,43)>0,"route-local injected UDF recovered after GIC writes and cleanup ran");
    else check(reg_value(route,22)==reg_value(route,3)&&reg_value(route,20)==5&&reg_value(route,21)==1023&&reg_value(route,23)==1023,"HPPIR observes local timer then source withdrawal");
    check((reg_value(route,32)&0x3c0)==0x3c0&&(reg_value(route,33)&0x3c0)==0x3c0&&reg_value(route,27)==0&&reg_value(route,28)==0,"CPU IRQ stays masked and interrupt never active");
    uint64_t ctl,cval,group;__asm__ volatile("mrs %0,cntp_ctl_el0\n mrs %1,cntp_cval_el0\n mrs %2,icc_igrpen1_el1":"=r"(ctl),"=r"(cval),"=r"(group));
    check(((ctl^reg_value(route,13))&3)==0&&cval==reg_value(route,14)&&group==reg_value(route,10),"receiver independently reads restored CNTP and ICC group");
    const volatile uint32_t *local=(const volatile uint32_t *)(uintptr_t)reg_value(route,5);
    check(local[0x100/4]==0&&local[0x300/4]==0,"receiver independently reads disabled and inactive local enables");
  }
#else
  check(!route,"physical timer route disabled by default");
#endif
  int icc_len=0;
  const fdt64_t *icc=fdt_getprop(fdt,node,"raphael,icc-readonly",&icc_len);
#if EXPECT_ICC
  uint64_t freq;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(freq));
  text("ICC_FREQ ");hex_value(freq);text("\n");
  check(icc&&icc_len==26*8&&reg_value(icc,0)==1&&reg_value(icc,1)==5,"ICC system-register snapshot complete");
  if(icc&&icc_len==26*8) {
    const unsigned char *bytes=(const void *)icc;const char digits[]="0123456789abcdef";
    text("ICC_WIRE ");for(unsigned i=0;i<26*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    check(reg_value(icc,2)==16&&reg_value(icc,3)==16,"ICC reads bounded to audited selectors");
    check(reg_value(icc,9)==mpidr&&reg_value(icc,22)==freq,"ICC independent MPIDR/frequency match");
    check(reg_value(icc,10)&1,"ICC SRE already enabled without writes");
    check(reg_value(icc,5)==0&&reg_value(icc,6)==0,"actual ICC reads did not trap");
    if(EXPECT_ICC_FAULT)check(reg_value(icc,23)==1&&(reg_value(icc,24)>>26)==0&&reg_value(icc,25)>0,"mapped injected UDF recovered to leaf reader");
    else check(reg_value(icc,23)==0&&reg_value(icc,24)==0&&reg_value(icc,25)==0,"injected reader trap disabled");
  }
#else
  check(!icc,"ICC read-only probe disabled by default");
#endif
  int payload_len=0;
  const fdt64_t *payload=fdt_getprop(fdt,node,"raphael,payload-diagnostic",&payload_len);
  if(EXPECT_PAYLOAD) {
    unsigned status=EXPECTED_STAGE==2?1:((EXPECTED_STAGE==3||EXPECT_FAULT)?2:3);
    check(payload&&payload_len==16*8&&reg_value(payload,0)==1&&reg_value(payload,1)==status,"synthetic payload stage record");
    if(payload&&payload_len==16*8) {
      const unsigned char *bytes=(const void *)payload;const char digits[]="0123456789abcdef";
      text("PAYLOAD_WIRE ");for(unsigned i=0;i<16*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
    }
    if(payload&&payload_len==16*8&&status>=2) {
      check(reg_value(payload,3)==1048576&&reg_value(payload,5)==1,"payload FV bytes and FDT HOB");
      check(reg_value(payload,2)>=reg_value(r,24)&&reg_value(payload,2)+1048576<=reg_value(r,25),"payload stays within own extension");
      if(status==3) {
        check(reg_value(payload,6)&&reg_value(payload,7)&&reg_value(payload,8)&&reg_value(payload,9),"BlockIo write protection and FAT connected");
        check(reg_value(payload,10)==(EXPECT_MANAGER_KEYS?2:1)&&reg_value(payload,11)==1,"configuration loaded from RAM FAT");
        check(reg_value(payload,12)==0&&reg_value(payload,13)==1,EXPECT_QEMU_ARCH?"full UniXNURun exits after IRQ countdown":"full UniXNURun auto-exit without timer");
        check(reg_value(payload,14)==reg_value(payload,15),"payload CRC unchanged");
      }
    }
  } else check(!payload,"synthetic payload disabled by default");
  int manager_len=0;
  const fdt64_t *manager=fdt_getprop(fdt,node,"raphael,manager-run",&manager_len);
  if(EXPECT_PHYSICAL_TIMER&&EXPECT_PAYLOAD) {
    check(manager&&manager_len==48&&reg_value(manager,0)==1&&reg_value(manager,1)==(EXPECTED_STAGE==6?2:1),"physical TimerArch full manager phase record");
    if(manager&&manager_len==48) {
      const unsigned char *bytes=(const void *)manager;const char digits[]="0123456789abcdef";
      text("MANAGER_WIRE ");for(unsigned i=0;i<48;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      if(EXPECTED_STAGE==6) check(reg_value(manager,3)>reg_value(manager,2)&&reg_value(manager,3)-reg_value(manager,2)>=reg_value(manager,4)*18/10&&reg_value(manager,5)==(EXPECT_MANAGER_KEYS?6:2),"actual UniXNURun bounded physical IRQ countdown");
    }
  } else check(!manager,"physical manager test disabled by default");
  int pt_len=0;
  const fdt64_t *pt=fdt_getprop(fdt,node,"raphael,physical-timer-arch",&pt_len);
  if(EXPECT_PHYSICAL_TIMER) {
    check(pt&&pt_len==56*8&&reg_value(pt,0)==1&&reg_value(pt,1)==(EXPECTED_STAGE==2?1:EXPECTED_STAGE==3?2:4),"physical-only TimerArch stage record");
    if(pt&&pt_len==56*8) {
      const unsigned char *bytes=(const void *)pt;const char digits[]="0123456789abcdef";
      text("PHYSICAL_TIMER_WIRE ");for(unsigned i=0;i<56*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      if(EXPECTED_STAGE==6) {
        check(reg_value(pt,45)==1&&reg_value(pt,28)==reg_value(pt,29)&&reg_value(pt,28)>=20,"continuous timer IRQ/EOI and restoration");
        uint64_t ctl,cval,vc,vv,ig;
        __asm__ volatile("mrs %0,cntp_ctl_el0\n mrs %1,cntp_cval_el0\n mrs %2,cntv_ctl_el0\n mrs %3,cntv_cval_el0\n mrs %4,icc_igrpen1_el1":"=r"(ctl),"=r"(cval),"=r"(vc),"=r"(vv),"=r"(ig));
        check(((ctl^reg_value(pt,14))&3)==0&&cval==reg_value(pt,15)&&ig==reg_value(pt,13),"receiver independently verifies physical timer/interface restoration");
        check(((vc^reg_value(pt,20))&3)==0&&vv==reg_value(pt,21),"receiver verifies virtual timer unchanged");
        check(*(volatile uint32_t *)(uintptr_t)reg_value(pt,3)==reg_value(pt,12)&&*(volatile uint32_t *)(uintptr_t)(reg_value(pt,8)+0x100)==0&&*(volatile uint32_t *)(uintptr_t)(reg_value(pt,8)+0x300)==0,"receiver independently verifies GIC gates and active state");
      }
    }
  } else check(!pt,"physical-only TimerArch disabled by default");
  int arch_len=0;
  const fdt64_t *arch=fdt_getprop(fdt,node,"raphael,qemu-architecture",&arch_len);
  if(EXPECT_QEMU_ARCH) {
    unsigned status=EXPECTED_STAGE==2?1:(EXPECTED_STAGE==3?2:3);
    check(arch&&arch_len==29*8&&reg_value(arch,0)==1&&reg_value(arch,1)==status,"QEMU architecture stage record");
    if(arch&&arch_len==29*8) {
      const unsigned char *bytes=(const void *)arch;const char digits[]="0123456789abcdef";
      text("QEMU_ARCH_WIRE ");for(unsigned i=0;i<29*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
      check(reg_value(arch,3)>0&&reg_value(arch,5)>0&&reg_value(arch,12)>0,"QEMU DTB GIC windows and counter frequency recorded");
      if(status==3) {
        check(reg_value(arch,13)==1&&reg_value(arch,14)==1&&reg_value(arch,15)==1&&reg_value(arch,16)>0,"real CPU interrupt and timer protocols installed");
        check(reg_value(arch,17)==1&&reg_value(arch,18)>=reg_value(arch,12)*8/100&&reg_value(arch,18)<=reg_value(arch,12),"relative timer event waited 80ms to 1s");
        check(reg_value(arch,19)>=5&&reg_value(arch,20)>=reg_value(arch,12)*8/100&&reg_value(arch,20)<=reg_value(arch,12)&&reg_value(arch,21)==1,"periodic callbacks and cancellation stable");
        check(reg_value(arch,22)==1&&reg_value(arch,23)>=reg_value(arch,12)*18/10&&reg_value(arch,23)<=reg_value(arch,12)*5,"actual UniXNURun two-second countdown");
        check(reg_value(arch,24)==1&&reg_value(arch,25)==1,"timer sources disabled before return");
        check(reg_value(arch,26)==1&&reg_value(arch,27)==reg_value(arch,11)&&((reg_value(arch,28)^reg_value(arch,10))&3)==0,"CNTP control and compare restored");
      }
    }
  }else check(!arch,"QEMU architecture disabled by default");
  int darwin_len=0;
  const fdt64_t *darwin=fdt_getprop(fdt,node,"raphael,darwin-diagnostic",&darwin_len);
  if(EXPECT_DARWIN) {
    unsigned status=EXPECTED_STAGE==6&&!EXPECT_FAULT?3:1;
    check(darwin&&darwin_len==18*8&&reg_value(darwin,0)==1&&reg_value(darwin,1)==status,"Darwin diagnostic stage record");
    if(darwin&&darwin_len==18*8) {
      const unsigned char *bytes=(const void *)darwin;
      const char digits[]="0123456789abcdef";
      text("DARWIN_WIRE ");
      for(unsigned i=0;i<18*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}
      text("\n");
      if(status==3) {
        check(reg_value(darwin,2)==1&&reg_value(darwin,3)==1&&reg_value(darwin,4)==1&&reg_value(darwin,5)==0x20000,"actual FV DarwinBoot loaded and v2 protocol installed");
        check(reg_value(darwin,6)==0x8000000000000002ULL&&reg_value(darwin,7)==0x800000000000000eULL,"Darwin invalid request and missing file rejected");
        check(reg_value(darwin,8)==0x8000000000000001ULL&&reg_value(darwin,9)==0x8000000000000001ULL,"direct and UniXNU invalid Mach-O return");
        check(reg_value(darwin,10)==1&&reg_value(darwin,11)==1&&reg_value(darwin,12)==1,"driver unloaded protocol removed and text console restored");
        check(reg_value(darwin,13)==0&&reg_value(darwin,14)>0&&reg_value(darwin,15)==1,"memory text log and retained Boot Services");
        check(reg_value(darwin,16)==reg_value(darwin,17),"Darwin test leaves read-only FAT unchanged");
      }
    }
  } else check(!darwin,"Darwin diagnostic disabled by default");
  int input_dxe_len=0;
  const fdt64_t *input_dxe=fdt_getprop(fdt,node,"raphael,input-dxe",&input_dxe_len);
  if(EXPECT_INPUT_PROTOCOL)
    check(input_dxe && input_dxe_len==16*8 && reg_value(input_dxe,0)==1 && reg_value(input_dxe,1)==1 && reg_value(input_dxe,4)==0 && reg_value(input_dxe,6)==0,
      "unsupported hardware has no input MMIO mappings or protocol");
  else check(!input_dxe,"input protocol disabled by default");
  check(!fdt_getprop(fdt,node,"raphael,display-menu",NULL),"no menu on unsupported handset hardware");
  int key_len=0;
  const fdt64_t *keys=fdt_getprop(fdt,node,"raphael,input-registers",&key_len);
  if(EXPECT_INPUT_READ)
    check(keys && key_len==56*8 && reg_value(keys,0)==1 && reg_value(keys,1)==1 && reg_value(keys,2)==0,
      "unsupported PMIC transport issues no observer commands");
  else check(!keys,"PMIC read commands disabled by default");
  int input_len=0;
  const fdt32_t *input=fdt_getprop(fdt,node,"raphael,input-map",&input_len);
  if(EXPECT_INPUT_PROBE)
    check(input && input_len==(26+1024)*4 && fdt32_to_cpu(input[0])==1 && fdt32_to_cpu(input[1])==1 && fdt32_to_cpu(input[4])==0,
      "unsupported input hardware performs no MMIO reads or transactions");
  else check(!input,"input probe disabled by default");
  int gop_len=0;
  const fdt64_t *gop=fdt_getprop(fdt,node,"raphael,display-gop",&gop_len);
  if(EXPECT_GOP)
    check(gop && gop_len==26*8 && reg_value(gop,0)==1 && reg_value(gop,1)==1 && reg_value(gop,10)==0,
      "unsupported hardware installs no GOP or framebuffer mapping");
  else check(!gop,"GOP disabled by default");
  int display_len;
  int write_len=0;
  const fdt64_t *write_result=fdt_getprop(fdt,node,"raphael,display-write",&write_len);
  if(EXPECT_PIXEL_WRITE)
    check(write_result && write_len==19*8 && fdt64_to_cpu(write_result[0])==1 && fdt64_to_cpu(write_result[1])==1, "unsupported hardware performs no pixel writes");
  else
    check(!write_result,"pixel writes disabled");
  int pixel_len=0;
  const fdt32_t *pixels=fdt_getprop(fdt,node,"raphael,display-pixels",&pixel_len);
  if (EXPECT_PIXEL_PROBE)
    check(pixels && pixel_len==4301*4 && fdt32_to_cpu(pixels[0])==1 && fdt32_to_cpu(pixels[1])==1, "unsupported hardware performs no pixel reads");
  else
    check(!pixels, "pixel probe disabled");
  const fdt64_t *display = fdt_getprop(fdt, node, "raphael,display-snapshot", &display_len);
  if (EXPECT_DISPLAY_PROBE)
    check(display && display_len == 24 && reg_value(display,0)==(EXPECT_SMMU_PROBE ? 4 : 3) && reg_value(display,1)==1 && reg_value(display,2)==0, "unsupported hardware makes no display reads");
  else
    check(!display, "display probe disabled by default");
  check(id && !strcmp(id, "qemu-sec-dxe-v1"), "test identifier");
  check(args && !strcmp(args, "fixture_cookie=unchanged"), "original bootargs");
#ifdef REPLAY_CONTEXT_BASE
  if (!r) {
    const uint64_t *context = (const void *)(uintptr_t)REPLAY_CONTEXT_BASE;
    text("PRIVATE_REPLAY input_fdt/totalsize ");
    hex_value(context[0]); text(" ");
    hex_value(fdt_totalsize((const void *)(uintptr_t)context[0])); text("\n");
    text("PRIVATE_REPLAY stage/status/esr/elr/far ");
    for (unsigned i = 0; i < 5; ++i) {
      hex_value(context[i < 2 ? 27 + i : 31 + i]); text(" ");
    }
    text("\n");
  }
#endif
  if (r && len == 48 * 8) {
    uint64_t sctlr, daif, vbar, tpidr, tcr, ttbr0, ttbr1, mair, cpacr;
    __asm__ volatile("mrs %0,sctlr_el1" : "=r"(sctlr));
    __asm__ volatile("mrs %0,daif" : "=r"(daif));
    __asm__ volatile("mrs %0,vbar_el1" : "=r"(vbar));
    __asm__ volatile("mrs %0,tpidr_el0" : "=r"(tpidr));
    __asm__ volatile("mrs %0,tcr_el1" : "=r"(tcr));
    __asm__ volatile("mrs %0,ttbr0_el1" : "=r"(ttbr0));
    __asm__ volatile("mrs %0,ttbr1_el1" : "=r"(ttbr1));
    __asm__ volatile("mrs %0,mair_el1" : "=r"(mair));
    __asm__ volatile("mrs %0,cpacr_el1" : "=r"(cpacr));
    check(reg_value(r, 27) == (EXPECT_FAULT&&EXPECT_FAULT!=3&&EXPECT_FAULT!=4 ? 4 : EXPECTED_STAGE), "expected firmware stage reached");
    check(reg_value(r, 28) == (EXPECT_FAULT ? 0xe1 : 0), "diagnostic exit status");
    if (EXPECT_FAULT) {
      check((reg_value(r, 33) >> 26) == (EXPECT_FAULT>=2?0:0x3c), EXPECT_FAULT>=2?"unmapped UDF uses fatal diagnostic exit":"injected BRK captured in ESR");
      check(reg_value(r, 34) > reg_value(r, 24) && reg_value(r, 34) < reg_value(r, 25), "fault PC inside diagnostic extension");
    }
    check(reg_value(r, 19) == (uintptr_t)image, "original kernel address");
    check(reg_value(r, 23) == (uintptr_t)fdt && reg_value(r, 0) != (uintptr_t)fdt, "FDT clone");
    check((reg_value(r, 30) & 0x1005) == (EXPECTED_STAGE == 2 ? 0 : 0x1005), "expected MMU/cache phase");
    check(sctlr == reg_value(r, 7), "SCTLR restored");
    check(daif == reg_value(r, 8), "DAIF restored");
    check(vbar == reg_value(r, 12) && tpidr == reg_value(r, 13), "VBAR/TPIDR restored");
    check(tcr == reg_value(r, 14) && ttbr0 == reg_value(r, 15) && ttbr1 == reg_value(r, 16), "translation registers restored");
    check(mair == reg_value(r, 17) && cpacr == reg_value(r, 18), "MAIR/CPACR restored");
    check(*(const uint32_t *)image == reg_value(r, 22) && *(const uint64_t *)(image + 16) == reg_value(r, 20), "Image header restored");
    if (!EXPECT_FAULT && EXPECTED_STAGE == 6) {
    check(reg_value(r, 36) == 0x5453595320494249ULL && reg_value(r, 37) == 0x56524553544f4f42ULL, "UEFI ST/BS signatures");
    check(reg_value(r, 38) == 1 && reg_value(r, 39) == 1, "UEFI table CRCs");
    check(reg_value(r, 44) == 0, "DXE heap map confined to arena");
    check(reg_value(r, 45) == 1, "DXE allocate/write/free page");
    const void *map = fdt_getprop(fdt, node, "raphael,sec-dxe-map", &len);
    check(map && len > 0 && (uint64_t)len == reg_value(r, 41) && reg_value(r, 42) >= 40 && (uint64_t)len % reg_value(r, 42) == 0, "memory map serialized");
    }
    const char *log = fdt_getprop(fdt, node, "raphael,sec-dxe-log", &len);
    check(log && len > 0, "memory diagnostic log");
    check(reg_value(r,47)==0,"diagnostic log has no dropped bytes");
    if (log) { text("LOG_BEGIN\n"); for (int i=0;i<len;++i) *uart=(unsigned char)log[i]; text("\nLOG_END\n"); }
    int found = 0;
    for (int i = 0; i < fdt_num_mem_rsv(fdt); ++i) {
      uint64_t base, size;
      if (!fdt_get_mem_rsv(fdt, i, &base, &size) && base == reg_value(r, 24) && size == reg_value(r, 25) - base) found = 1;
    }
    check(found, "whole diagnostic extension reserved");
  }
  text(failures ? "SEC_DXE_FIXTURE_FAILED\n" : "SEC_DXE_FIXTURE_OK\n");
  uint64_t status[2] = {0x20026, (uint64_t)failures};
  register uint64_t function __asm__("x0") = 0x20;
  register void *argument __asm__("x1") = status;
  __asm__ volatile("hlt #0xf000" : "+r"(function), "+r"(argument) : : "memory");
  for (;;) __asm__ volatile("wfe");
}
