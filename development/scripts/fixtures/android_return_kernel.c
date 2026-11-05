/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Independent QEMU receiver for the real high return stub.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <libfdt.h>
#ifndef RETURN_RAMDISK_BYTES
#define RETURN_RAMDISK_BYTES 12345
#endif
#ifndef RETURN_NATIVE_STAGING
#define RETURN_NATIVE_STAGING 0
#endif
static volatile uint32_t *uart;static unsigned failures,checks;
static void text(const char *s){while(*s)*uart=(unsigned char)*s++;}
static void check(int pass,const char *name){text(pass?"PASS ":"FAIL ");text(name);text("\n");++checks;if(!pass)++failures;}
static uint64_t word(const fdt64_t *p,unsigned n){return fdt64_to_cpu(p[n]);}
void fixture_main(const void *fdt,const unsigned char *image){
 int len,node=fdt_node_offset_by_compatible(fdt,-1,"arm,pl011");const fdt32_t *reg=fdt_getprop(fdt,node,"reg",&len);
 if(!reg||len<16)for(;;)__asm__ volatile("wfe");uart=(void *)(uintptr_t)(((uint64_t)fdt32_to_cpu(reg[0])<<32)|fdt32_to_cpu(reg[1]));
 node=fdt_path_offset(fdt,"/chosen");const fdt64_t *q=fdt_getprop(fdt,node,"raphael,android-return",&len);
 check(q&&len==80,"return wire");if(q&&len==80){
 check(word(q,0)==1&&word(q,1)==3,"real high stub decode completed");check(word(q,2)==word(q,7)&&word(q,3)==word(q,4),"source and kernel CRCs match");
 check(word(q,8)==RETURN_KERNEL_BYTES&&word(q,9)==1,"full LZMA stream consumed");
 const unsigned char *bytes=(const void *)q;const char digits[]="0123456789abcdef";text("ANDROID_RETURN_WIRE ");for(unsigned i=0;i<80;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");
 }
 check(*(const uint32_t *)image==0x14000010&&*(const uint64_t *)(image+16)==RETURN_IMAGE_BYTES,"complete original Image header restored");
 int same=1;for(size_t i=65536;i<RETURN_KERNEL_BYTES;++i)if(image[i]!=(unsigned char)(i^(i>>8))){same=0;break;}check(same,"every synthetic kernel tail byte restored");
 same=1;for(size_t i=RETURN_KERNEL_BYTES;i<RETURN_IMAGE_BYTES;++i)if(image[i]){same=0;break;}check(same,"original declared BSS tail cleared");
 const fdt64_t *start=fdt_getprop(fdt,node,"linux,initrd-start",&len);check(start&&len==8,"initrd start");uint64_t a=start?word(start,0):0;
 const fdt64_t *end=fdt_getprop(fdt,node,"linux,initrd-end",&len);check(end&&len==8&&word(end,0)==a+RETURN_RAMDISK_BYTES,"initrd end restored to original ramdisk bytes");
 const char *id=fdt_getprop(fdt,node,"raphael,sec-dxe-id",NULL);check(id&&!strcmp(id,"qemu-android-return-v1"),"unique receiver nonce");
 const fdt64_t *d=fdt_getprop(fdt,node,"raphael,sec-dxe",&len);check(d&&len==48*8,"independent SEC record");if(d&&len==48*8){
 uint64_t ctl,daif,vbar,tpidr,tcr,ttbr0,ttbr1,mair,cpacr;
 __asm__ volatile("mrs %0,sctlr_el1":"=r"(ctl));__asm__ volatile("mrs %0,daif":"=r"(daif));__asm__ volatile("mrs %0,vbar_el1":"=r"(vbar));__asm__ volatile("mrs %0,tpidr_el0":"=r"(tpidr));
 __asm__ volatile("mrs %0,tcr_el1":"=r"(tcr));__asm__ volatile("mrs %0,ttbr0_el1":"=r"(ttbr0));__asm__ volatile("mrs %0,ttbr1_el1":"=r"(ttbr1));__asm__ volatile("mrs %0,mair_el1":"=r"(mair));__asm__ volatile("mrs %0,cpacr_el1":"=r"(cpacr));
 check(word(d,27)==RETURN_STAGE&&word(d,28)==0,"expected SEC or DXE stage, zero status");check(ctl==word(d,7)&&(ctl&0x1005)==0,"SCTLR restored and cache MMU off");check(daif==word(d,8),"DAIF restored");
 check(vbar==word(d,12)&&tpidr==word(d,13),"VBAR TPIDR restored");check(tcr==word(d,14)&&ttbr0==word(d,15)&&ttbr1==word(d,16),"TCR TTBR0 TTBR1 restored");check(mair==word(d,17)&&cpacr==word(d,18),"MAIR CPACR restored");
 if(RETURN_STAGE==2)check(word(d,31)==0&&word(d,30)==0,"pre-MMU return created no translation root");
 else check(word(d,31)>=((uintptr_t)image+RETURN_IMAGE_BYTES),"MMU root survives decoded kernel extent");check(word(d,23)==(uintptr_t)fdt&&(uintptr_t)fdt>=((uintptr_t)image+RETURN_IMAGE_BYTES),"FDT copy survives decoded kernel extent");
 if(RETURN_STAGE>=6)check(word(d,38)==1&&word(d,39)==1&&word(d,44)==0&&word(d,45)==1,"real DXE service CRC map and allocate/free");
 const char *log=fdt_getprop(fdt,node,"raphael,sec-dxe-log",&len);if(log){text("LOG_BEGIN\n");for(int i=0;i<len;++i)*uart=(unsigned char)log[i];text("\nLOG_END\n");}
 }
 if(RETURN_NATIVE_STAGING){
 const fdt64_t *p=fdt_getprop(fdt,node,"raphael,payload-diagnostic",&len);check(p&&len==16*8,"native staging payload wire");
 if(p&&len==16*8){if(RETURN_STAGE==2)check(word(p,0)==1&&word(p,1)==1&&word(p,3)==0,"pre-MMU payload remains unmaterialized");
 else check(word(p,0)==1&&word(p,1)==(RETURN_STAGE>=6?3:2)&&word(p,3)==RETURN_NATIVE_FAT_BYTES,"native FAT size and correct checkpoint");
 if(RETURN_STAGE>=6)check(word(p,6)==1&&word(p,7)==1&&word(p,8)==1&&word(p,9)==1&&word(p,11)==1&&word(p,12)==0&&word(p,13)==1&&word(p,14)==word(p,15),"real FAT readonly config full UniXNURun and unchanged CRC");}
 }
 if(RETURN_STAGE>=7){
 const fdt64_t *n=fdt_getprop(fdt,node,"raphael,native-load",&len);check(n&&len==16*8,"native loaded-memory wire");
 if(n&&len==16*8){check(word(n,0)==(RETURN_STAGE>=8?2:1)&&word(n,1)==(RETURN_STAGE>=8?4:3)&&word(n,12)==1&&word(n,15)==0,"original loader validated and exited through notification");
 const unsigned char *bytes=(const void *)n;const char digits[]="0123456789abcdef";text("NATIVE_LOAD_WIRE ");for(unsigned i=0;i<16*8;++i){*uart=digits[bytes[i]>>4];*uart=digits[bytes[i]&15];}text("\n");}
 if(RETURN_STAGE==9){const fdt64_t *e=fdt_getprop(fdt,node,"raphael,native-entry",&len);check(e&&len==40*8,"native entry wire");
 if(e&&len==40*8){check(word(e,0)==1&&word(e,1)==3&&word(e,2)==1&&word(e,3)==1&&word(e,37)==0,"native instructions and restored checkpoint");const unsigned char *b=(const void *)e;const char h[]="0123456789abcdef";text("NATIVE_ENTRY_WIRE ");for(unsigned i=0;i<40*8;++i){*uart=h[b[i]>>4];*uart=h[b[i]&15];}text("\n");}}

 if(RETURN_STAGE>=10){const unsigned char *t=fdt_getprop(fdt,node,"raphael,native-mmu-tables",&len);check(t&&len==65536,"full native bootstrap table snapshot");if(t&&len==65536){text("NATIVE_MMU_TABLES ");const char h[]="0123456789abcdef";for(unsigned i=0;i<65536;++i){*uart=h[t[i]>>4];*uart=h[t[i]&15];}text("\n");}}
 if(RETURN_STAGE>=11){int early_len=0;const fdt64_t *early_header=fdt_getprop(fdt,node,"raphael,native-early-c",&early_len);int delta_limit=early_header&&early_len==800&&word(early_header,0)==9?0x100000:0x80000;const unsigned char *t=fdt_getprop(fdt,node,"raphael,native-early-delta",&len);check(t&&len>0&&len<=delta_limit&&len%12==0,"early C changed-word delta");if(t&&len>0&&len<=delta_limit){text("NATIVE_EARLY_DELTA ");const char h[]="0123456789abcdef";for(int i=0;i<len;++i){*uart=h[t[i]>>4];*uart=h[t[i]&15];}text("\n");}
 const fdt64_t *e=fdt_getprop(fdt,node,"raphael,native-early-c",&len);check(e&&(len==320||len==416||len==608||len==800),"early C wire");if(e&&(len==320||len==416||len==608||len==800)){check((RETURN_STAGE>=13?(word(e,0)==3||word(e,0)==4||word(e,0)==5||word(e,0)==6||word(e,0)==7||word(e,0)==8||word(e,0)==9):word(e,0)==(RETURN_STAGE==12?2:1))&&word(e,1)==3&&word(e,2)==0&&word(e,13)==(word(e,0)>=9?8:word(e,0)>=8?5:3)&&word(e,14)==(word(e,0)>=9?8:word(e,0)>=8?5:3)&&word(e,15)==1,"early C restoration and argument copy");const unsigned char *b=(const void *)e;const char h[]="0123456789abcdef";text("NATIVE_EARLY_WIRE ");for(unsigned i=0;i<(unsigned)len;++i){*uart=h[b[i]>>4];*uart=h[b[i]&15];}text("\n");}}
 if(RETURN_STAGE>=10){const fdt64_t *e=fdt_getprop(fdt,node,"raphael,native-mmu",&len);check(e&&len==72*8,"native MMU wire");
 if(e&&len==72*8){check(word(e,0)==(RETURN_STAGE>=12?2:1)&&word(e,1)==3&&word(e,2)==1&&word(e,3)==1&&word(e,56)==0,"native MMU checkpoint and restored state");const unsigned char *b=(const void *)e;const char h[]="0123456789abcdef";text("NATIVE_MMU_WIRE ");for(unsigned i=0;i<72*8;++i){*uart=h[b[i]>>4];*uart=h[b[i]&15];}text("\n");}}

 }
 if(RETURN_STAGE>=13){
 const fdt64_t *g=fdt_getprop(fdt,node,"raphael,native-gic",&len);
 if(g){check(len==448&&word(g,0)==1&&word(g,1)==3&&word(g,5)==1,"native boot CPU GIC restoration");
 if(len==448){text("NATIVE_GIC_WIRE ");const char h[]="0123456789abcdef";const unsigned char *b=(const void *)g;for(unsigned i=0;i<448;++i){*uart=h[b[i]>>4];*uart=h[b[i]&15];}text("\n");}}

 const fdt64_t *p=fdt_getprop(fdt,node,"raphael,native-platform",&len);check(p&&len==144,"platform timer wire");
 if(p&&len==144){check(word(p,0)==1&&word(p,1)==3&&word(p,17)==1,"original platform prefix and timer restoration");const unsigned char *b=(const void *)p;const char h[]="0123456789abcdef";text("NATIVE_PLATFORM_WIRE ");for(unsigned i=0;i<144;++i){*uart=h[b[i]>>4];*uart=h[b[i]&15];}text("\n");}
 }
 if(RETURN_STAGE>=12){
 const unsigned char *a=fdt_getprop(fdt,node,"raphael,native-pmap-adt",&len);check(a&&len>0&&len<=65536,"original XNU ADT mutation snapshot");if(a&&len>0&&len<=65536){text("NATIVE_PMAP_ADT ");const char h[]="0123456789abcdef";for(int i=0;i<len;++i){*uart=h[a[i]>>4];*uart=h[a[i]&15];}text("\n");}
 const unsigned char *x=fdt_getprop(fdt,node,"raphael,native-pmap-transition",&len);check(x&&len==16384,"exact-grant transition table snapshot");if(x&&len==16384){text("NATIVE_PMAP_TRANSITION ");const char h[]="0123456789abcdef";for(int i=0;i<len;++i){*uart=h[x[i]>>4];*uart=h[x[i]&15];}text("\n");}
 const fdt64_t *p=fdt_getprop(fdt,node,"raphael,native-pmap",&len);check(p&&len==256,"post-pmap wire");if(p&&len==256){check(word(p,0)==1&&word(p,1)==3&&word(p,2)==0&&word(p,7)==1&&word(p,17)==1&&word(p,18)==1&&word(p,21)==1&&word(p,29)==1&&word(p,31)==1,"post-pmap transition and original table checks");const unsigned char *b=(const void *)p;const char h[]="0123456789abcdef";text("NATIVE_PMAP_WIRE ");for(unsigned i=0;i<256;++i){*uart=h[b[i]>>4];*uart=h[b[i]&15];}text("\n");}
 const unsigned char *t=fdt_getprop(fdt,node,"raphael,native-pmap-tables",&len);check(t&&len>0&&len<=524288,"bounded active pmap sparse snapshot");if(t&&len>0&&len<=524288){text("NATIVE_PMAP_TABLES ");const char h[]="0123456789abcdef";for(int i=0;i<len;++i){*uart=h[t[i]>>4];*uart=h[t[i]&15];}text("\n");}
 }
 text(failures?"ANDROID_RETURN_QEMU_FAILED\n":"ANDROID_RETURN_QEMU_OK\n");uint64_t status[2]={0x20026,failures};register uint64_t x0 __asm__("x0")=0x20;register void *x1 __asm__("x1")=status;__asm__ volatile("hlt #0xf000":"+r"(x0),"+r"(x1)::"memory");for(;;)__asm__ volatile("wfe");
}
