#!/usr/bin/env python3
"""Exact diagnostic IOWatchdog opt-in on the existing qualified hardware."""
import struct
KEY='unixnu,diag-watchdog-client'
def qualify_kernel(path,offline_keystore=False):
 from native_early import image
 symbols=image(path.read_bytes())[1]
 required=['_raphael_watchdog_client_record','_raphael_native_watchdog_begin','_raphael_native_watchdog_pet','_raphael_native_watchdog_end','__ZN25RaphaelDiagnosticWatchdog10gMetaClassE','__ZN25RaphaelWatchdogUserClient10gMetaClassE']
 assert all(k in symbols for k in required),'Original bounded-watchdog client implementation must be linked'
 assert '__ZN10IOWatchdog9MetaClassC1Ev' not in symbols and '__ZN10IOWatchdog9MetaClassC2Ev' not in symbols,'Original abstract class must not be redefined'
 assert ('_raphael_offline_aks_stage' in symbols)==offline_keystore,'Keystore requires the explicit ephemeral scratch-Data payload option'
def qualify_property(value,raw,kernel,offline_keystore=False):
 assert value==struct.pack('<I',1),'Only exact diagnostic watchdog-client opt-in is allowed'
 from native_watchdog_budget import from_adt
 budget=from_adt(raw)
 # The shorter existing v2 contract captures registry/method state before the
 # unexplained v34 late-window stall. It cannot extend daemon or hardware time.
 assert budget and budget['seconds']==20
 assert (budget['contract_version'],budget['observer_ms'],budget['budget_ms']) in ((2,120000,180000),(4,360000,420000),(5,720000,780000),(6,1800000,1860000))
 qualify_kernel(kernel,offline_keystore=offline_keystore)
