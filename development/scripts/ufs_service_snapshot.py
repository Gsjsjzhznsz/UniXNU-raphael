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

def decode_backboard_receiver(words,frequency=None):
 assert len(words)>=8 and words[:2]==[0x31524242485052,1]
 pid,count,truncated,width,counter,freq=words[2:8]
 assert 0<=pid<2147483648 and 0<=count<=32 and truncated in (0,1) and width==128
 assert (pid>0 or count==0) and counter>0 and 0<freq<=1000000000
 assert frequency is None or freq==frequency
 assert len(words)==8+count*128
 return dict(pid=pid,captured=pid>0,thread_capacity=32,threads_truncated=bool(truncated),counter=counter,counter_frequency=freq,threads=[decode_service_thread(words[8+i*128:8+(i+1)*128],128,lambda pc:None) for i in range(count)])

def decode_saved_path(words):
 assert len(words)==64
 if not any(words):return None
 assert words[0]==0x31544850485052 and words[4]<=448 and words[5] in range(7)
 raw=struct.pack('<56Q',*words[8:]);length=words[4]
 if words[5]==1:assert length>0 and raw[length-1]==0
 return dict(tid=words[1],saved_x16=words[2],argument_address=words[3],captured_bytes=length,status=words[5],user_pc=words[6],path=raw[:length].split(b'\0',1)[0].decode(errors='replace'),scope='Saved argument candidate only;confirm syscall stub from user PC before treating as active operation.')

def decode_all_processes(sections,frequency=None):
 if 'ALLPROC_BEGIN' not in sections:return None
 begin=sections['ALLPROC_BEGIN'];assert len(begin)==4 and begin[0]==1 and begin[3]==512
 assert begin[1]>0 and 0<begin[2]<=1000000000 and (frequency is None or begin[2]==frequency)
 groups={}
 for name,w in sorted(sections.items()):
  if not name.startswith('ALLPROC_') or name in ('ALLPROC_BEGIN','ALLPROC_END'):continue
  match=re.fullmatch(r'ALLPROC_([0-9]{4,})_([0-9]{3})',name);assert match
  assert len(w)>=16 and w[:2]==[0x31504152485052,1]
  seq,pid,state,total,count,first,n,width,counter,freq=w[2:12]
  assert seq==int(match[1]) and first==int(match[2])*32 and 0<=pid<2147483648
  assert 0<=count<=512 and count<=total and 0<=n<=32 and n==min(32,count-first) and first<=count and width==192
  assert len(w)==16+n*width and counter>=begin[1] and freq==begin[2]
  comm=struct.pack('<4Q',*w[12:16]).split(b'\0',1)[0].decode(errors='replace')
  if seq not in groups:
   assert first==0
   groups[seq]=dict(sequence=seq,pid=pid,state=state,name=comm,total_threads=total,captured_threads=count,threads_truncated=total>count,first_counter=counter,last_counter=counter,counter_frequency=freq,threads=[])
  g=groups[seq]
  assert (g['pid'],g['name'],g['total_threads'],g['captured_threads'])==(pid,comm,total,count)
  assert first==len(g['threads']);g['last_counter']=counter
  for i in range(n):
   row=w[16+i*width:16+(i+1)*width];t=decode_service_thread(row[:128],128,lambda pc:None)
   t['saved_path']=decode_saved_path(row[128:]);g['threads'].append(t)
 for g in groups.values():
  assert len(g['threads'])==g['captured_threads'] and len({t['tid'] for t in g['threads']})==len(g['threads'])
 complete='ALLPROC_END' in sections;summary=sections.get('ALLPROC_END');elapsed=None
 if complete:
  assert len(summary)==9 and summary[0]==1 and summary[5]==begin[1] and summary[7:]==[begin[2],512] and summary[6]>=summary[5]
  assert summary[1:5]==[len(groups),sum(g['captured_threads'] for g in groups.values()),sum(g['total_threads'] for g in groups.values()),sum(g['threads_truncated'] for g in groups.values())]
  assert all(g['last_counter']<=summary[6] for g in groups.values())
  elapsed=(summary[6]-summary[5])/summary[7]
 return dict(complete=complete,processes=list(groups.values()),process_count=len(groups),captured_threads=sum(g['captured_threads'] for g in groups.values()),truncated_processes=sum(g['threads_truncated'] for g in groups.values()),capture_elapsed_seconds=elapsed,scope='Original allproc enumeration snapshot;processes exiting before callback may be absent,newly spawned processes after enumeration may be absent.Each process references at most512 threads;explicit total and truncation retained.')

def decode_early_processes(sections):
 result=[]
 for sequence in (1,2):
  prefix=f'EARLY{sequence:02d}_'
  subset={name[len(prefix):]:words for name,words in sections.items() if name.startswith(prefix)}
  if 'ALLPROC_END' not in subset:continue
  group=decode_all_processes(subset)
  if group is not None:result.append(dict(sequence=sequence,**group))
 return result

def decode_ls_paths(sections):
 result=[]
 for name,w in sorted(sections.items()):
  if not name.startswith('LS_PATH_'):continue
  assert re.fullmatch(r'LS_PATH_[0-9]{2}',name) and len(w)>=8 and w[:2]==[0x3150544c485052,1] and w[5]<=8 and w[6]==64 and len(w)==8+w[5]*64
  result.append(dict(name=name,counter=w[2],counter_frequency=w[3],pid=w[4],paths=[decode_saved_path(w[8+i*64:8+(i+1)*64]) for i in range(w[5])]))
 return result

def decode(text,kernel):
 sections,incomplete=parse(text)
 if not sections:return dict(captured=False,incomplete_sections=incomplete)
 required={'context','display','_raphael_native_watchdog_record','_raphael_watchdog_client_record','_raphael_watchdog_method_record','_raphael_native_root_record','_raphael_native_user_record','_raphael_service_record_words','_raphael_service_header','_raphael_service_processes','_raphael_service_threads','_raphael_service_kernel_probe','_raphael_service_exceptions'}
 missing=sorted(required-set(sections))
 if missing:return dict(captured=False,missing_sections=missing,incomplete_sections=incomplete,ls_progress=decode_ls_progress(sections),ls_paths=decode_ls_paths(sections),early_processes=decode_early_processes(sections))
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
 result=dict(ls_progress=progress,captured=services['captured'],full_checkpoint_verified=False,scope='Independent UFS copy of existing bounded observer records; no completed diagnostic handback or desktop acceptance implied.',services=services,service_exceptions=exceptions,display=dict(zip(DISPLAY_FIELDS,sections['display'])),watchdog_budget=budget,watchdog_client=dict(stage=client[1],opens=client[2],closes=client[3],checkins=client[4],last_checkin_counter=client[5],monitoring=bool(client[6]),counter_frequency=client[7],failures=client[8],last_selector=client[9],missed_checkin=bool(client[10])),watchdog_method=dict(complete=method[1]==2,calls=method[2],result=method[3],selector=method[4]),root=dict(polls=root[2],observer_limit_polls=root[7]),init_syscalls=sections['_raphael_native_user_record'][1],sections=len(sections))

 if incomplete:
  result.update(captured=False,named_services_captured=services['captured'],incomplete_sections=incomplete,full_stream_complete=False)
 early=decode_early_processes(sections)
 if early:result["early_processes"]=early
 if "BACKBOARD_RECEIVER" in sections:result["backboard_receiver"]=decode_backboard_receiver(sections["BACKBOARD_RECEIVER"],frequency)
 if "ALLPROC_BEGIN" in sections:result["all_processes"]=decode_all_processes(sections,frequency)
 if any(n.startswith("LS_PATH_") for n in sections):result["ls_paths"]=decode_ls_paths(sections)
 return result
