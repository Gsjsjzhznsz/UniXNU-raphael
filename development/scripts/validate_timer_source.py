#!/usr/bin/env python3
"""Execute the actual masked-CNTP core, model partial failures and restoration."""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from entry_probe import ROOT,sha
from validate_icc_probe import Snapshot as IccSnapshot
from timer_source import FIELDS,decode
class Snapshot(c.Structure):_fields_=[(k,c.c_uint64) for k in FIELDS]
class Guard(c.Structure):_fields_=[('before',c.c_ubyte*64),('result',Snapshot),('after',c.c_ubyte*64)]
def main():
 parent=ROOT/'artifacts/timer-source-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/TimerSource.c';core=ROOT/'sources/mu_basecore/MdePkg/Include'
 cmd=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all',
      '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),str(source),'-o',str(out/'timer-source.so')]
 result=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,result.stderr.decode()
 lib=c.CDLL(str(out/'timer-source.so'))
 rt=c.CFUNCTYPE(c.c_uint8,c.c_uint32,c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.c_void_p)
 wt=c.CFUNCTYPE(c.c_uint8,c.c_uint32,c.c_uint64,c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.c_void_p)
 collect=lib.RaphaelTestTimerSource;collect.argtypes=[c.POINTER(IccSnapshot),c.POINTER(Snapshot),rt,wt,c.c_void_p]
 cases=[]
 def case(name,status,change=None,values=None,read_fault=None,write_fault=None,partial_write=False,
          ignore_write=None,stuck=False,expired_early=False,backwards=False,state_changed=False,
          counter_start=10000,step=1000,original_ctl=0,original_cval=123,no_icc=False,no_read=False,no_write=False):
  i=IccSnapshot();i.version=1;i.status=5;i.attempted=i.completed=16;i.failed_selector=(1<<64)-1
  i.values[0]=4;i.values[1]=0x3c0;i.values[3]=1;i.values[10]=original_ctl;i.values[11]=original_cval;i.values[15]=1000000
  for k,v in (change or {}).items():setattr(i,k,v)
  for k,v in (values or {}).items():i.values[k]=v
  m=dict(ctl=original_ctl,cval=original_cval,counter=counter_start);reads=[];writes=[];unexpected=[]
  @rt
  def read(reg,v,esr,elr,context):
   reads.append(reg)
   if reg not in [0,1,2]:unexpected.append(reg);return 0
   if len(reads)==read_fault:esr[0]=0x18<<26;elr[0]=0x1000;return 0
   if reg==0:
    v[0]=m['counter']
    m['counter']=(m['counter']+step)&((1<<64)-1)
    if backwards and writes:v[0]=0
   elif reg==1:
    expired=bool(m['ctl']&1 and m['counter']>=m['cval'] and not stuck)
    v[0]=m['ctl']|(4 if expired or expired_early and writes else 0)
    if state_changed and not writes:v[0]^=2
   else:v[0]=m['cval']
   return 1
  @wt
  def write(reg,v,esr,elr,context):
   writes.append((reg,v))
   if reg not in [1,2] or reg==1 and v not in [0,2,3]:unexpected.append((reg,v));return 0
   fault=len(writes)==write_fault
   if (not fault or partial_write) and len(writes)!=ignore_write:
    m['ctl' if reg==1 else 'cval']=v
   if fault:esr[0]=0x18<<26;elr[0]=0x2000;return 0
   return 1
  g=Guard()
  for n in range(64):g.before[n]=g.after[n]=0xa5
  collect(None if no_icc else c.byref(i),c.byref(g.result),rt() if no_read else read,wt() if no_write else write,None)
  o=g.result
  assert not unexpected and bytes(g.before)==bytes(g.after)==b'\xa5'*64
  assert o.version==1 and o.status==status,(name,o.status,o.reason,writes,reads)
  assert len(writes)==o.write_calls
  # Every mutation path must attempt all three restoration operations.
  if writes:
   assert writes[-3:]==[(1,2),(2,original_cval),(1,original_ctl&3)],(name,writes)
   if status!=7:assert m['ctl']==original_ctl&3 and m['cval']==original_cval
  else:assert m['ctl']==original_ctl and m['cval']==original_cval
  raw=struct.pack('>17Q',*struct.unpack('<17Q',bytes(o)))
  if status==8:assert decode(raw,1000000)['passed']
  else:
   try:decode(raw,1000000)
   except AssertionError:pass
   else:raise AssertionError('partial result accepted '+name)
  cases.append(dict(name=name,status=status,read_count=len(reads),write_count=len(writes),polls=o.polls,passed=True))
  return raw,len(reads)
 wire,read_count=case('normal source expires masked and restores',8)
 case('initial IMASK is preserved',8,original_ctl=2,original_cval=0xffffffffffffffff)
 for name,kw in [('null ICC',dict(no_icc=True)),('null read callback',dict(no_read=True)),('null write callback',dict(no_write=True))]:case(name,1,**kw)
 for key,value in [('version',2),('status',4),('attempted',15),('completed',15),('failed_selector',0),('trap_esr',1),('trap_elr',1)]:case('ICC rejected '+key,1,change={key:value})
 for k,v in [(0,8),(1,0x340),(3,0),(10,1),(10,8),(15,999),(15,1000000001)]:case('prerequisite value '+str(k)+'='+str(v),1,values={k:v})
 case('fresh CTL changed before writes',2,state_changed=True)
 case('counter deadline overflow rejected',2,counter_start=(1<<64)-1)
 for n in range(1,read_count+1):
  case('trapped read '+str(n),4 if n<=read_count-2 else 7,read_fault=n)
 for n in [1,2]:
  for partial in [False,True]:case('write trap '+str(n)+' partial='+str(partial),3,write_fault=n,partial_write=partial)
 for n in [3,4,5]:case('restoration write trap '+str(n),7,write_fault=n)
 case('CVAL write ignored',5,ignore_write=1)
 case('CTL write ignored',5,ignore_write=2)
 case('source never reports expiration',6,stuck=True)
 case('bounded polls with stopped counter',6,stuck=True,step=0)
 case('counter reverses after write',5,backwards=True)
 case('ISTATUS before deadline rejected',5,expired_early=True,step=1)
 case('intermediate disable ignored but final restoration succeeds',8,ignore_write=3)
 for n in [4,5]:case('restoration write ignored '+str(n),7,ignore_write=n)
 damaged={'version':2,'status':7,'reason':1,'frequency':0,'original_ctl':1,'original_cval':2,'start_counter':0,'deadline':0,
          'observed_ctl':3,'observed_cval':0,'end_counter':0,'polls':0,'restored_ctl':1,'restored_cval':1,'write_calls':4,'trap_esr':1,'trap_elr':1}
 for k,v in damaged.items():
  raw=bytearray(wire);struct.pack_into('>Q',raw,FIELDS.index(k)*8,v)
  try:decode(raw,1000000)
  except AssertionError:cases.append(dict(name='wire rejects '+k,passed=True))
  else:raise AssertionError(k)
 for label,raw in [('short',wire[:-8]),('long',wire+b'0')]:
  try:decode(raw,1000000)
  except AssertionError:cases.append(dict(name='wire rejects '+label,passed=True))
  else:raise AssertionError(label)
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelTimerSource.h']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,snapshot_bytes=c.sizeof(Snapshot),guard_canaries_verified=True,
  undefined_behavior_sanitizer=True,register_model_only=True,handset_executed=False,
  source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],decoder_sha256=sha((ROOT/'scripts/timer_source.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/timer-source-host.json').write_text(json.dumps(report,indent=2)+'\n')
 print(len(cases),'actual C/UBSan/canary/independent wire checks passed');print(out)
if __name__=='__main__':main()
