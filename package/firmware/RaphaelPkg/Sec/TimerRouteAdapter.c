// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelTimerRoute.h>
#include <Library/PcdLib.h>
extern BOOLEAN RaphaelRouteInjectedUndefined(UINT64,UINT64 *,UINT64 *);
extern BOOLEAN RaphaelWriteRouteIgrpen1(UINT64,UINT64 *,UINT64 *);
BOOLEAN RaphaelTimerRouteRead(UINT32 N,UINT64 *V,UINT64 *E,UINT64 *L,VOID *C) {
 if(N<=RAPHAEL_TIMER_CVAL)return RaphaelTimerSourceRead(N,V,E,L,C);
 if(N==RAPHAEL_ROUTE_IGRPEN1)return RaphaelReadIccRegister(RaphaelSysIgrpen1,V,E,L,C);
 if(N==RAPHAEL_ROUTE_HPPIR1)return RaphaelReadIccRegister(RaphaelSysHppir1,V,E,L,C);
 if(N==RAPHAEL_ROUTE_DAIF)return RaphaelReadIccRegister(RaphaelSysDaif,V,E,L,C);
 return FALSE;
}
BOOLEAN RaphaelTimerRouteWrite(UINT32 N,UINT64 V,UINT64 *E,UINT64 *L,VOID *C) {
 if(!E||!L)return FALSE;
 if(N<=RAPHAEL_TIMER_CVAL)return RaphaelTimerSourceWrite(N,V,E,L,C);
 if(FixedPcdGetBool(PcdRaphaelTimerRouteFaultTest)&&N==RAPHAEL_ROUTE_IGRPEN1&&V==1)return RaphaelRouteInjectedUndefined(V,E,L);
 if(N==RAPHAEL_ROUTE_IGRPEN1&&V<=1)return RaphaelWriteRouteIgrpen1(V,E,L);
 return FALSE;
}
