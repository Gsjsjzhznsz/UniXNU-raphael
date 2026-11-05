#!/usr/bin/env python3
"""Decode original arm_init timer side effects and bounded restoration."""
import struct
FIELDS="version status saved_physical_control saved_physical_compare saved_virtual_control saved_virtual_compare saved_kernel_control observed_physical_control observed_physical_compare observed_virtual_control observed_virtual_compare observed_kernel_control restored_physical_control restored_physical_compare restored_virtual_control restored_virtual_compare restored_kernel_control restore_ok".split()
def decode(raw,stop=0):
 assert len(raw)==144
 d=dict(zip(FIELDS,struct.unpack('>18Q',raw)))
 assert d['version']==1 and d['status']==3 and d['restore_ok']==1
 for timer in ['physical','virtual']:
  assert d['restored_'+timer+'_control']&3==d['saved_'+timer+'_control']&3
  assert d['restored_'+timer+'_compare']==d['saved_'+timer+'_compare']
 assert d['restored_kernel_control']==d['saved_kernel_control']
 assert d['observed_kernel_control']&15==15 and (d['observed_kernel_control']^d['saved_kernel_control'])&~255==0
 if stop in (0,6):
  assert d['observed_physical_control']&3==2 and d['observed_virtual_control']&3==1
  assert d['observed_physical_compare']==d['saved_physical_compare']
 return dict(**d,checkpoint_id=stop,machine_startup_entry_reached=stop in (0,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20),machine_startup_body_executed=stop in (6,7,8,9,10,11,12,13,14,15,16,17,18,19,20),kernel_bootstrap_entry_reached=stop in (6,7,8,9,10,11,12,13,14,15,16,17,18,19,20),kernel_bootstrap_prefix_executed=stop in (7,8,9,10,11,12,13,14,15,16,17,18,19,20),vm_bootstrap_entry_reached=stop in (7,8,9,10,11,12,13,14,15,16,17,18,19,20),vm_bootstrap_returned=stop in (7,9,10,11,12,13,14,15,16,17,18,19,20),sched_init_returned=stop in (10,11,12,13,14,15,16,17,18,19,20),first_thread_entry_reached=stop in (11,12,13,14,15,16,17,18,19,20),first_thread_prefix_executed=stop in (12,13,14,15,16,17,18,19,20),iokit_returned=stop in (13,14,15,16,17,18,19,20),irq_unmask_returned=stop in (14,15,16,17,18,19,20),pre_lockdown_prefix_reached=stop in (16,17,18,19,20),machine_lockdown_returned=stop in (17,18,19,20),iokit_matching_started=stop in (18,19,20),root_observer_completed=stop==20,bsd_init_prefix_executed=stop in (19,20),timer_sleep_returned=stop in (19,20),scheduler_body_executed=stop in (19,20),normal_xnu_irq_verified=False)
