#!/usr/bin/env python3
"""Actual C/UBSan mapped-read state machine, bounded callbacks and wire checks."""
import ctypes as c,datetime as dt,json,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from ram_read_probe import FIELDS as BEFORE_FIELDS,MASK
from ram_mapped_probe import FIELDS,decode
from validate_ram_read import Entry,Snapshot
class Result(c.Structure):_fields_=[(name,c.c_uint64) for name in FIELDS]
class Guard(c.Structure):_fields_=[('before',c.c_ubyte*64),('result',Result),('after',c.c_ubyte*64)]
def main():
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=ROOT/'artifacts'))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/RamMapped.c';inc=ROOT/'sources/mu_basecore/MdePkg/Include'
 cmd=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(inc),'-I'+str(inc/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),str(source),'-o',str(out/'mapped.so')]
 r=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()
 lib=c.CDLL(str(out/'mapped.so'));pt=c.POINTER(c.c_uint64)
 tt=c.CFUNCTYPE(c.c_uint8,c.c_uint64,pt,pt,pt,pt,c.c_void_p);rt=c.CFUNCTYPE(c.c_uint8,c.c_uint64,pt,c.c_void_p);ct=c.CFUNCTYPE(c.c_uint64,c.c_void_p)
 call=lib.RaphaelReadMappedRam;call.argtypes=[c.POINTER(Snapshot),c.POINTER(Entry),c.POINTER(Result),tt,rt,ct,c.c_void_p]
 base=0xc0000000;addresses=[base+i*0x200000+t for i in range(128) for t in [0,0x200000-8]]
 digest=14695981039346656037
 for a in addresses:digest=((digest^a)*1099511628211)&MASK;digest=((digest^(a^0x1122334455667788))*1099511628211)&MASK
 defaults=dict(version=1,status=3,reason=0,base=base,bytes=0x10000000,stride=0x200000,requested=256,attempted=256,completed=256,active_address=base+0x10000000-8,digest=digest,nonzero=256,start_counter=10,end_counter=20,frequency=19200000,mmfr0=2,physical_bits=40,ram_ranges=1,policy_guards=1,entry_guards=4,current_el=4,sctlr=0,daif=0x3c0)
 cases=[]
 def case(name,status,bpatch=None,epatch=None,kind=None,step=100,start=1000,fail=None):
  before=Snapshot(**(defaults|dict(bpatch or {})));entry=Entry(4,0x1005,0x3c0,2,40,19200000,0)
  for k,v in (epatch or {}).items():setattr(entry,k,v)
  guard=Guard();c.memset(c.byref(guard),0xa5,c.sizeof(guard));queries=[];reads=[];clocks=[]
  @tt
  def translate(a,r,w,o,z,ctx):
   queries.append(a);r[0]=(0xff<<56)|(a&~4095);w[0]=0x1f;o[0]=z[0]=0x1122
   if kind=='read-fault':r[0]|=1
   if kind=='wrong-pa':r[0]^=4096
   if kind=='wrong-attribute':r[0]^=1<<56
   if kind=='writable':w[0]=0
   if kind=='par-damaged':z[0]^=1
   if kind=='par-inconsistent' and len(queries)==2:o[0]=z[0]=0x3344
   return kind!='query-fail'
  @rt
  def read(a,v,ctx):
   reads.append(a);v[0]=a^0x1122334455667788
   if kind=='changed-value':v[0]^=1
   return len(reads)!=fail
  @ct
  def clock(ctx):
   value=(start+step*len(clocks))&MASK;clocks.append(value);return value
  call(None if kind=='null-before' else c.byref(before),None if kind=='null-entry' else c.byref(entry),c.byref(guard.result),tt() if kind=='null-translate' else translate,rt() if kind=='null-read' else read,ct() if kind=='null-counter' else clock,None)
  o=guard.result;assert bytes(guard.before)==bytes(guard.after)==b'\xa5'*64
  assert o.version==1 and o.status==status,(name,o.status,o.reason)
  assert queries==addresses[:len(queries)] and reads==addresses[:len(reads)]
  assert o.attempted==len(queries) and o.completed==len(reads)-int(fail is not None and fail==len(reads))
  wire=struct.pack('>27Q',*struct.unpack('<27Q',bytes(o)))
  if status==3:assert decode(wire,defaults|dict(passed=True),3)['passed']
  else:
   try:decode(wire,defaults|dict(passed=True),3)
   except AssertionError:pass
   else:raise AssertionError('failed record accepted')
  cases.append(dict(name=name,passed=True,status=status,queries=len(queries),reads=len(reads)));return wire
 wire=case('all identity WB RO translations and unchanged contents',3)
 for field,value in dict(version=2,status=2,reason=1,base=base+8,bytes=0,stride=8,requested=255,attempted=1,completed=1,active_address=0,nonzero=257,current_el=8,sctlr=1,daif=0,ram_ranges=0,policy_guards=0,entry_guards=0,mmfr0=7,physical_bits=52,start_counter=30).items():case('bad pre-map '+field,4,bpatch={field:value})
 for field,value in dict(CurrentEl=8,Sctlr=0,Daif=0,Frequency=0,Mmfr0=3,PhysicalBits=36).items():
  # ctypes fields use lower-case names from the original entry shim.
  key={'CurrentEl':'el','Sctlr':'sctlr','Daif':'daif','Frequency':'frequency','Mmfr0':'mmfr0','PhysicalBits':'bits'}[field]
  case('bad mapped entry '+field,4,epatch={key:value})
 for kind in ['null-before','null-entry','null-translate','null-read','null-counter']:case(kind,4,kind=kind)
 for kind in ['query-fail','read-fault','wrong-pa','wrong-attribute','writable','par-damaged','par-inconsistent']:case(kind,5,kind=kind)
 case('changed sparse values rejected',8,kind='changed-value')
 for at in [1,128,256]:case('read callback fails '+str(at),7,fail=at)
 case('100ms deadline',6,step=1920001);case('counter wrap',6,start=MASK-1)
 for key in FIELDS:
  if key in ['original_par','restored_par']:value=0
  elif key in ['first_read_par','last_read_par']:value=0
  elif key in ['sctlr','daif','last_write_par']:value=0
  else:value=MASK
  damaged=bytearray(wire);struct.pack_into('>Q',damaged,FIELDS.index(key)*8,value)
  try:decode(damaged,defaults|dict(passed=True),3)
  except AssertionError:cases.append(dict(name='wire rejects '+key,passed=True))
  else:raise AssertionError(key)
 for damaged in [wire[:-1],wire+b'0']:
  try:decode(damaged,defaults|dict(passed=True),3)
  except AssertionError:cases.append(dict(name='wire size',passed=True))
  else:raise AssertionError('wire size')
 sources=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelRamMapped.h']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,undefined_behavior_sanitizer=True,guard_canaries_verified=True,wire_bytes=c.sizeof(Result),source_inputs=[dict(path=str(x.relative_to(ROOT)),sha256=sha(x.read_bytes())) for x in sources],decoder_sha256=sha((ROOT/'scripts/ram_mapped_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/ram-mapped-host.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(len(cases),'C/UBSan/canary/wire checks passed')
if __name__=='__main__':main()
