// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <stdio.h>
#include <stdlib.h>
#undef NULL
#include <RaphaelNativePmap.h>
static void check(int ok,const char *name) {
 if(!ok){fprintf(stderr,"FAIL %s\n",name);exit(1);}printf("PASS %s\n",name);
}
int main(void) {
 const UINT64 base=0x100000,bytes=0x100000;
 check(RaphaelNativePmapSparseRange(base,65536,base,bytes),"legacy 64 KiB");
 check(RaphaelNativePmapSparseRange(base,65537,base,bytes),"cross old limit");
 check(RaphaelNativePmapSparseRange(base,RAPHAEL_NATIVE_PMAP_SPARSE_BYTES,base,bytes),"full producer capacity");
 check(!RaphaelNativePmapSparseRange(base,RAPHAEL_NATIVE_PMAP_SPARSE_BYTES+1,base,bytes),"reject over capacity");
 check(!RaphaelNativePmapSparseRange(base-1,1,base,bytes),"reject below owned arena");
 check(!RaphaelNativePmapSparseRange(base+bytes+1,1,base,bytes),"reject above owned arena");
 check(!RaphaelNativePmapSparseRange(base+bytes-65535,65536,base,bytes),"reject range crossing arena end");
 check(RaphaelNativePmapSparseRange(base+bytes-RAPHAEL_NATIVE_PMAP_SPARSE_BYTES,RAPHAEL_NATIVE_PMAP_SPARSE_BYTES,base,bytes),"exact owned end");
 check(!RaphaelNativePmapSparseRange(0xffffffffffffffffULL,RAPHAEL_NATIVE_PMAP_SPARSE_BYTES,base,bytes),"reject arithmetic wrap");
 check(RaphaelNativeRelayBlock(0x60800000,0x609fff88,0x300),"relay first block");
 check(RaphaelNativeRelayBlock(0x60a00000,0x609fff88,0x300),"relay crosses into second block");
 check(!RaphaelNativeRelayBlock(0x60600000,0x609fff88,0x300),"relay excludes preceding block");
 check(!RaphaelNativeRelayBlock(0x60c00000,0x609fff88,0x300),"relay excludes following block");
 check(!RaphaelNativeRelayBlock(0x60a00000,0x609fff88,0x78),"relay ends exactly at block boundary");
 check(RaphaelNativeRelayBlock(0x60a00000,0x60a00000,4),"relay starts exactly at block boundary");
 check(!RaphaelNativeRelayBlock(0x60a00000,0x60a00000,0),"relay rejects empty extent");
 check(!RaphaelNativeRelayBlock(0x60a00000,0xffffffffffffffffULL,4),"relay rejects overflowing extent");
 check(!RaphaelNativeRelayBlock(0xffffffffffffffffULL,0x60a00000,4),"relay rejects overflowing block");
 return 0;
}
