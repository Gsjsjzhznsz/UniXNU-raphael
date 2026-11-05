// SPDX-License-Identifier: BSD-2-Clause-Patent
// Freestanding Linux AArch64 read-only FIEMAP/policy inspector. UAPI layouts:
// linux/fiemap.h, linux/fscrypt.h, asm-generic/unistd.h. No FS mutation ioctl.
typedef unsigned long long U64;typedef unsigned int U32;typedef long S;
struct Extent {U64 logical,physical,length,reserved64[2];U32 flags,reserved[3];};
struct Map {U64 start,length;U32 flags,mapped,count,reserved;struct Extent extent[128];};
_Static_assert(sizeof(struct Extent)==56,"Linux FIEMAP extent ABI");
_Static_assert(__builtin_offsetof(struct Map,extent)==32,"Linux FIEMAP header ABI");
static struct Map map;static unsigned char policy[12];static U64 flags;
static char text[32768];static unsigned used;
static S call(S n,S a,S b,S c){register S x0 __asm__("x0")=a;register S x1 __asm__("x1")=b;register S x2 __asm__("x2")=c;register S x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x8):"memory","cc");return x0;}
static void put(const char *p){while(*p&&used<sizeof(text)-1)text[used++]=*p++;}
static void number(U64 n){char b[24];unsigned k=0;do{b[k++]=(char)('0'+n%10);n/=10;}while(n);while(k&&used<sizeof(text)-1)text[used++]=b[--k];}
static void signednum(S n){if(n<0){put("-");number((U64)-n);}else number((U64)n);}
void entry(U64 *sp){
 S rc=2;if(sp[0]!=2)goto done;
 S fd=call(56,-100,(S)sp[2],0x80000);if(fd<0)goto done;
 S pol=call(29,fd,0x400c6615,(S)policy),frc=call(29,fd,0x80086601,(S)&flags);
 map.length=~0ULL;map.count=128;map.flags=1; // FIEMAP_FLAG_SYNC completes this file's allocation.
 S mrc=call(29,fd,0xc020660b,(S)&map);call(57,fd,0,0);
 put("{\"policy_rc\":");signednum(pol);put(",\"flags_rc\":");signednum(frc);put(",\"inode_flags\":");number(flags);put(",\"fiemap_rc\":");signednum(mrc);put(",\"count\":");number(map.mapped);put(",\"extents\":[");
 if(map.mapped>128)goto done;
 for(U32 i=0;i<map.mapped;++i){struct Extent *e=&map.extent[i];if(i)put(",");put("{\"logical\":");number(e->logical);put(",\"physical\":");number(e->physical);put(",\"length\":");number(e->length);put(",\"flags\":");number(e->flags);put("}");}
 put("]}\n");call(64,1,(S)text,used);rc=mrc<0?1:0;
done:call(93,rc,0,0);for(;;){}
}
__asm__(".global _start\n_start:\nmov x0, sp\nbl entry\n");
