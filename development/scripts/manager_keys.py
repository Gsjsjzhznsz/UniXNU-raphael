#!/usr/bin/env python3
"""Independent full-manager key log decoder, tied to same-run PMIC wire data."""
import re

def decode(log,stage,manager,input_dxe):
 assert stage in (2,3,6) and manager['passed']
 starts=re.findall(rb'RAPHAEL manager input start=(\d+) deadline=(\d+) frequency=(\d+)',log)
 keys=re.findall(rb'RAPHAEL manager key scan=(\d+) unicode=(\d+) automatic=(\d+) ticks=(\d+)',log)
 sums=re.findall(rb'RAPHAEL manager keys up/down/enter/automatic/errors/delivered=(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)',log)
 cleanup=re.findall(rb'RAPHAEL manager input cleanup console=(\d+) uninstall=(\d+) close=(\d+)',log)
 if stage<6:
  assert not starts and not keys and not sums and not cleanup and not input_dxe['events']
  return dict(passed=True,executed=False,physical_three_keys_verified=False)
 assert len(starts)==len(sums)==len(cleanup)==1 and tuple(map(int,cleanup[0]))==(1,1,1)
 start,deadline,freq=map(int,starts[0]);up,down,enter,automatic,errors,delivered=map(int,sums[0])
 assert freq==manager['frequency'] and deadline-start==6*freq and 0<start<=manager['start_counter']<manager['end_counter']
 assert errors==input_dxe['errors']==0 and delivered==len(keys)==up+down+enter+automatic
 counts=[0,0,0,0];events=[];previous=0;selection=0;mask=0
 for scan,unicode,auto,ticks in keys:
  scan,unicode,auto,ticks=map(int,(scan,unicode,auto,ticks))
  assert auto in (0,1) and ticks>=previous and start+ticks<=manager['end_counter']
  previous=ticks
  if auto:
   assert (scan,unicode)==(0,13) and ticks>=6*freq and automatic==1
   index=3;name='automatic_enter'
  else:
   assert ticks<6*freq and (scan,unicode) in ((1,0),(2,0),(0,13))
   index={(1,0):0,(2,0):1,(0,13):2}[(scan,unicode)];mask|=1<<index
   name=('up','down','enter')[index]
  counts[index]+=1
  if index in (0,1):selection=1-selection
  events.append(dict(key=name,ticks=ticks,selected=selection))
 assert counts==[up,down,enter,automatic]
 assert input_dxe['events']==up+down+enter and input_dxe['read_calls']>=input_dxe['events']
 assert input_dxe['pressed_mask']==mask and input_dxe['released_mask']&~mask==0
 if events:
  assert events[-1]['key'] in ('enter','automatic_enter')
  assert sum(e['key'] in ('enter','automatic_enter') for e in events)==1
  assert re.search(rb'menu: enter, booting '+str(selection).encode(),log)
 else:
  assert manager['end_counter']-start>=6*freq and b'menu: timeout, booting default 0' in log
 physical=[e['key'] for e in events]==['up','down','enter'] and automatic==0
 return dict(passed=True,executed=True,start=start,deadline=deadline,frequency=freq,up=up,down=down,enter=enter,automatic=automatic,errors=errors,delivered=delivered,events=events,selected=selection,console_restored=True,physical_three_keys_verified=physical,human_visibility_verified=False)
