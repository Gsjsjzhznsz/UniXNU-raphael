// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelIccProbe.h>
#define RAPHAEL_READ_SITE(Id,Name,Reg) extern BOOLEAN Name(UINT64 *,UINT64 *,UINT64 *);
#include "IccReadSites.inc"
#undef RAPHAEL_READ_SITE
BOOLEAN RaphaelReadIccRegister(UINT32 R,UINT64 *V,UINT64 *Esr,UINT64 *Elr,VOID *C) {
 (VOID)C;if(!V||!Esr||!Elr)return FALSE;
 switch(R) {
#define RAPHAEL_READ_SITE(Id,Name,Reg) case Id:return Name(V,Esr,Elr);
#include "IccReadSites.inc"
#undef RAPHAEL_READ_SITE
 default:return FALSE;
 }
}
