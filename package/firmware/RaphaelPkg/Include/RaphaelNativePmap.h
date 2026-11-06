// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_PMAP_H
#define RAPHAEL_NATIVE_PMAP_H
#include <Uefi.h>
// The return bridge may straddle an architectural 2 MiB block boundary.
// Test the complete checked extent, never only the first instruction.
STATIC inline BOOLEAN RaphaelNativeRelayBlock(UINT64 Block,UINT64 Relay,UINT64 RelayBytes) {
 return RelayBytes&&Relay<=MAX_UINT64-RelayBytes&&Block<=MAX_UINT64-0x200000ULL&&
   Relay<Block+0x200000ULL&&Block<Relay+RelayBytes;
}
// Exact physical recovery alias: a shortened L1, up to three L2 pages,
// and two partial L3 pages. Legacy grants keep their original four-page ABI.
STATIC inline UINTN RaphaelNativeTransitionPages(UINT64 Bytes) {
 return Bytes==1536ULL*1024*1024?6:4;
}
STATIC inline BOOLEAN RaphaelNativeTransitionTables(UINT64 *Table,UINT64 Root,UINT64 Base,UINT64 Bytes,UINT64 Relay,UINT64 RelayBytes) {
 if((Base&4095)||(Root&4095)||(Bytes&4095)||
    (Bytes!=256ULL*1024*1024&&Bytes!=512ULL*1024*1024&&Bytes!=704ULL*1024*1024&&Bytes!=896ULL*1024*1024&&Bytes!=1536ULL*1024*1024)||
    Base>=(1ULL<<38)||Bytes>(1ULL<<38)-Base||Relay<Base||Relay>=Base+Bytes||!RelayBytes||RelayBytes>2048||RelayBytes>Base+Bytes-Relay)return FALSE;
 UINT64 End=Base+Bytes,First=Base&~0x1fffffULL;
 UINTN Spans=(UINTN)(((End-1)>>30)-(Base>>30)+1),Pages=RaphaelNativeTransitionPages(Bytes),Partial=1+Spans;
 if(Partial+2>Pages)return FALSE;
 for(UINTN I=0;I<Pages*512;++I)Table[I]=0;
 for(UINTN I=0;I<Spans;++I)Table[((Base>>30)+I)&255]=(Root+(1+I)*4096)|3;
 for(UINT64 Block=First;Block<End;Block+=0x200000ULL){
  UINTN L2=1+(UINTN)((Block>>30)-(Base>>30)),Index=L2*512+((Block>>21)&511);
  UINT64 Flags=0x0040000000000601ULL;if(!RaphaelNativeRelayBlock(Block,Relay,RelayBytes))Flags|=1ULL<<53;
  if(Block>=Base&&End-Block>=0x200000ULL)Table[Index]=Block|Flags;
  else {
   if(Partial>=Pages)return FALSE;Table[Index]=(Root+Partial*4096)|3;
   for(UINTN J=0;J<512;++J){UINT64 P=Block+J*4096;if(P>=Base&&P<End)Table[Partial*512+J]=P|(Flags|2);}
   ++Partial;
  }
 }
 return TRUE;
}
// Match original start.s allocation order: both roots, physical L2 pages,
// then virtual L2 pages. Check every descriptor, including unused entries.
STATIC inline BOOLEAN RaphaelNativeBootstrapTablesMatch(CONST UINT64 *Table,UINT64 Root,UINT64 Physical,UINT64 Virtual,UINT64 Bytes,UINT64 Skip) {
 struct {UINT64 Va,Pa;UINTN Count,Page,Side;} Rows[14];UINTN Used=0,Next=2;
 if(Bytes<=Skip||Skip>0xfe00000ULL||(Skip&4095)||Physical>MAX_UINT64-Skip||Virtual>MAX_UINT64-Skip)return FALSE;
 UINT64 Pb=(Physical+Skip)&~0x1fffffULL,Vb=(Virtual+Skip)&((1ULL<<38)-1)&~0x1fffffULL;
 UINTN Blocks=(UINTN)((Bytes-Skip)>>21);if(!Blocks||Blocks>3072)return FALSE;
 for(UINTN Side=0;Side<2;++Side){
  UINT64 Va=Side?Vb:Pb,Pa=Pb;UINTN Left=Blocks;
  while(Left){
   if(Next>=16||Used>=14)return FALSE;
   UINTN Count=512-((Va>>21)&511);if(Count>Left)Count=Left;
   Rows[Used].Va=Va;Rows[Used].Pa=Pa;Rows[Used].Count=Count;Rows[Used].Page=Next++;Rows[Used++].Side=Side;
   Left-=Count;Va+=(UINT64)Count<<21;Pa+=(UINT64)Count<<21;
  }
 }
 for(UINTN Page=0;Page<16;++Page)for(UINTN I=0;I<512;++I){
  UINT64 Expected=0;
  for(UINTN J=0;J<Used;++J){
   if(Page==Rows[J].Side&&I==((Rows[J].Va>>30)&255))Expected=(Root+Rows[J].Page*4096)|3;
   UINTN Start=(Rows[J].Va>>21)&511;
   if(Page==Rows[J].Page&&I>=Start&&I-Start<Rows[J].Count)Expected=(Rows[J].Pa+((UINT64)(I-Start)<<21))|0x601;
  }
  if(Table[Page*512+I]!=Expected)return FALSE;
 }
 return TRUE;
}

#define RAPHAEL_NATIVE_PMAP_SPARSE_BYTES 524288U
// Shared by the producer and SEC serializer: one capacity and owned range.
STATIC inline BOOLEAN RaphaelNativePmapSparseRange(UINT64 At,UINT64 Length,UINT64 Base,UINT64 Bytes) {
 return Length<=RAPHAEL_NATIVE_PMAP_SPARSE_BYTES&&At>=Base&&At-Base<=Bytes&&Length<=Bytes-(At-Base);
}
typedef struct {
 UINT64 Version,Status,Error,TransitionBase,TransitionBytes,TransitionCrcBefore,TransitionCrcAfter,TransitionOk,OriginalTtbr0,OriginalTtbr1,ObservedTransitionTtbr0,CleanBase,CleanBytes,TablePages,NonzeroDescriptors,SparseBytes,SparseCapacity,Root0Empty,RelayUnmapped,HighDataPages,HighProbes,CaptureOk,TableCrcXor,Reserved,AdtPhysical,AdtBytes,AdtCrcBefore,AdtCrcAfter,AdtCrcRestored,AdtRestored,AdtChangedBytes,AdtBackupOk;
} RAPHAEL_NATIVE_PMAP_RESULT;
typedef struct { RAPHAEL_NATIVE_PMAP_RESULT Result;UINT64 Sparse,AdtSnapshot; } RAPHAEL_NATIVE_PMAP_STATE;
EFI_STATUS RaphaelPrepareNativePmap(VOID);
EFI_STATUS RaphaelArmNativePmap(UINT64 Base,UINT64 Bytes,UINT64 Relay,UINT64 RelayBytes,UINT64 Tcr,UINT64 Args);
BOOLEAN RaphaelNativePmapRead(UINT64 Va,UINTN Bytes,VOID *Out,UINT64 *Pa);
UINT64 RaphaelNativePmapRoot(VOID);
UINT64 RaphaelNativePmapState(VOID);
BOOLEAN RaphaelCaptureNativePmap(UINT64 Root0,UINT64 Root1,UINT64 Checkpoint,UINT64 *Physical);
#endif
