#!/usr/bin/env python3
"""Decode service records persisted by the bounded native observer to UFS."""
import re,struct
from pathlib import Path
from native_early import image,decode_service_snapshot,decode_service_exceptions,decode_service_thread

DISPLAY_FIELDS=['clients','validations','rejected','kicks','frames','blank_frames','retired','reject_reason','transfer_status','client_status','power_status','bytes','nonblack']

def parse(text):
 sections={};closed=set()
 for match in re.finditer(r'(?:^|\n)RPH SNAP ([^\n]+)\n',text):
  fields=match[1].split();kind,name=fields[:2]
  if kind=='BEGIN':
   assert len(fields)==3 and name not in sections,'Duplicate snapshot section'
   count=int(fields[2]);assert 0<=count<=65536
   sections[name]={'count':count,'words':[]}
  elif kind=='WORDS':
   assert name in sections and name not in closed and 4<=len(fields)<=11
   section=sections[name];assert int(fields[2])==len(section['words']),'Missing or repeated snapshot row'
   assert all(re.fullmatch(r'[0-9a-f]{16}',word) for word in fields[3:])
   section['words'] += [int(word,16) for word in fields[3:]]
   assert len(section['words'])<=section['count']
  elif kind=='END':
   assert len(fields)==2 and name in sections and name not in closed
   assert len(sections[name]['words'])==sections[name]['count'],'Truncated snapshot section'
   closed.add(name)
  else:raise ValueError('Unknown snapshot row')
 return {name:section['words'] for name,section in sections.items() if name in closed},sorted(set(sections)-closed)

def decode_ls_progress(sections,counter=None,frequency=None):
 progress=[]
 for name,words in sorted(sections.items()):
  if not name.startswith('LS_PROGRESS_'):continue
  assert re.fullmatch(r'LS_PROGRESS_[0-9]{2}',name)
  assert len(words)>=8 and words[:2]==[0x3150474c485052,1] and (frequency is None or words[3]==frequency)
  assert 0<words[2] and (counter is None or words[2]<=counter) and 0<words[3]<=1000000000 and 0<=words[4]<256 and 0<=words[5]<=8 and words[6] in (0,1)
  assert len(words)==8+words[5]*128
  progress.append(dict(name=name,counter=words[2],counter_frequency=words[3],pid=words[4],threads_truncated=bool(words[6]),poll=words[7],threads=[decode_service_thread(words[8+i*128:8+(i+1)*128],128,lambda pc:None) for i in range(words[5])]))
 return progress

def decode(text,kernel):
 sections,incomplete=parse(text)
 if not sections:return dict(captured=False,incomplete_sections=incomplete)
 required={'context','display','_raphael_native_watchdog_record','_raphael_watchdog_client_record','_raphael_watchdog_method_record','_raphael_native_root_record','_raphael_native_user_record','_raphael_service_record_words','_raphael_service_header','_raphael_service_processes','_raphael_service_threads','_raphael_service_kernel_probe','_raphael_service_exceptions'}
 missing=sorted(required-set(sections))
 if missing or incomplete:return dict(captured=False,missing_sections=missing,incomplete_sections=incomplete,ls_progress=decode_ls_progress(sections))
 _,symbols=image(Path(kernel).read_bytes());spans=[]
 for name,words in sections.items():
  if name.startswith('_'):
   assert name in symbols,'Snapshot symbol absent from this kernel'
   spans.append((symbols[name],struct.pack('<'+'Q'*len(words),*words)))
 def read(address,size):
  for start,raw in spans:
   if start<=address and address+size<=start+len(raw):return raw[address-start:address-start+size]
  raise ValueError('Snapshot does not contain requested bytes: '+hex(address))
 services=decode_service_snapshot(read,symbols)
 exceptions=decode_service_exceptions(read,symbols)
 assert len(sections['display'])==len(DISPLAY_FIELDS)
 counter,frequency=sections['context'];w=sections['_raphael_native_watchdog_record'];client=sections['_raphael_watchdog_client_record'];method=sections['_raphael_watchdog_method_record'];root=sections['_raphael_native_root_record']
 budget=None
 if w[0]:
  assert w[0]==0x3154445748505255 and w[14]==frequency and frequency>0 and w[6]<=counter
  budget=dict(hardware_seconds=w[4],budget_ms=w[5],observer_seconds=w[11]/frequency,start_counter=w[6],capture_counter=counter,counter_frequency=frequency,elapsed_ms=(counter-w[6])*1000/frequency,observer_deadline_reached=bool(w[13]),pets=w[8],last_pet_counter=w[9],status=w[1])
 progress=decode_ls_progress(sections,counter,frequency)
 return dict(ls_progress=progress,captured=services['captured'],full_checkpoint_verified=False,scope='Independent UFS copy of existing bounded observer records; no completed diagnostic handback or desktop acceptance implied.',services=services,service_exceptions=exceptions,display=dict(zip(DISPLAY_FIELDS,sections['display'])),watchdog_budget=budget,watchdog_client=dict(stage=client[1],opens=client[2],closes=client[3],checkins=client[4],last_checkin_counter=client[5],monitoring=bool(client[6]),counter_frequency=client[7],failures=client[8],last_selector=client[9],missed_checkin=bool(client[10])),watchdog_method=dict(complete=method[1]==2,calls=method[2],result=method[3],selector=method[4]),root=dict(polls=root[2],observer_limit_polls=root[7]),init_syscalls=sections['_raphael_native_user_record'][1],sections=len(sections))
