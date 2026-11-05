#!/usr/bin/env python3
"""Run the actual ICC gate/collector with bounded models and guard canaries."""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from entry_probe import ROOT,sha
from validate_gic_probe import Snapshot as GicSnapshot
from icc_probe import HEADER,REGISTERS,FAULT,FIELDS,decode

class Snapshot(c.Structure):
 _fields_=[(k,c.c_uint64) for k in HEADER]+[('values',c.c_uint64*16)]+[(k,c.c_uint64) for k in FAULT]
class Guard(c.Structure):_fields_=[('before',c.c_ubyte*64),('result',Snapshot),('after',c.c_ubyte*64)]

def main():
 parent=ROOT/'artifacts/icc-probe-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/IccProbe.c';core=ROOT/'sources/mu_basecore/MdePkg/Include'
 cmd=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all',
      '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),str(source),'-o',str(out/'icc-probe.so')]
 result=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,result.stderr.decode()
 lib=c.CDLL(str(out/'icc-probe.so'));read_type=c.CFUNCTYPE(c.c_uint8,c.c_uint32,c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.c_void_p)
 collect=lib.RaphaelCollectIcc;collect.argtypes=[c.POINTER(GicSnapshot),c.POINTER(Snapshot),read_type,c.c_void_p]
 model=[4,0x3c0,0x81000000,7,0x400,0xf8,3,0,255,1023,0,0xffff,0,0xffffffff,0,24000000]
 cases=[]
 def case(name,status,count=0,change_gic=None,change_values=None,fail=None,no_gic=False,no_reader=False):
  g=GicSnapshot();g.version=1;g.status=4;g.frame_count=1;g.boot_index=0;g.mpidr=model[2];g.affinity=0;g.frames[0].typer=16
  if change_gic:
   for k,v in change_gic.items():setattr(g,k,v)
  values=list(model)
  for k,v in (change_values or {}).items():values[k]=v
  guard=Guard();reads=[];unexpected=[]
  for i in range(64):guard.before[i]=guard.after[i]=0xa5
  @read_type
  def read(index,value,esr,elr,context):
   reads.append(index)
   if index>=16:unexpected.append(index);return 0
   if index==fail:esr[0]=0x18<<26;elr[0]=0x1000+index*4;value[0]=0xdeadbeef;return 0
   value[0]=values[index];return 1
  collect(None if no_gic else c.byref(g),c.byref(guard.result),read_type() if no_reader else read,None)
  o=guard.result
  assert not unexpected and reads==list(range(count)),(name,reads)
  assert bytes(guard.before)==bytes(guard.after)==bytes([0xa5])*64
  assert o.version==1 and o.status==status and o.attempted==count,(name,o.status,o.attempted)
  assert o.completed==count-(fail is not None)
  assert list(o.values[:o.completed])==values[:o.completed] and not any(o.values[o.completed:])
  if fail is not None:assert o.failed_selector==fail and o.trap_esr==0x18<<26 and o.trap_elr==0x1000+fail*4
  else:assert o.trap_esr==o.trap_elr==0
  raw=struct.pack('>'+'Q'*len(FIELDS),*struct.unpack('<'+'Q'*len(FIELDS),bytes(o)))
  if status==5:assert decode(raw,model[2],model[15])['passed']
  else:
   try:decode(raw,model[2],model[15])
   except AssertionError:pass
   else:raise AssertionError(name+' partial record accepted')
  cases.append(dict(name=name,status=status,reads=count,passed=True));return raw
 wire=case('complete bounded model',5,16)
 for name,options in [('null GIC',dict(no_gic=True)),('null reader',dict(no_reader=True))]:case(name,1,**options)
 for field,value in [('version',2),('status',3),('frame_count',0),('frame_count',9),('boot_index',1),('affinity',1)]:case('GIC gate '+field+'='+str(value),1,change_gic={field:value})
 case('wrong EL',2,1,change_values={0:8})
 for bit in [0x40,0x80,0x100,0x200]:case('DAIF not fully masked '+hex(bit),2,2,change_values={1:0x3c0^bit})
 case('different CPU',2,3,change_values={2:0x81000100})
 case('SRE disabled prevents remaining reads',3,4,change_values={3:6})
 for i in range(16):case('trapped selector '+REGISTERS[i],4,i+1,fail=i)
 damaged={'version':2,'status':4,'attempted':15,'completed':15,'failed_selector':0,'trap_esr':1,'trap_elr':1,'current_el':8,'daif':0,'mpidr':1,'sre':6,'ctlr':1<<32,'pmr':256,'bpr1':8,'igrpen1':2,'rpr':256,'hppir1':1<<24,'cntp_ctl':8,'cntv_ctl':8,'cntkctl':1<<32,'cntfrq':1,'injected_fault_recovered':1,'injected_fault_esr':1,'injected_fault_elr':1}
 for field,value in damaged.items():
  changed=bytearray(wire);struct.pack_into('>Q',changed,FIELDS.index(field)*8,value)
  try:decode(changed,model[2],model[15])
  except AssertionError:cases.append(dict(name='decoder rejects '+field,passed=True))
  else:raise AssertionError(field)
 fault=bytearray(wire)
 for field,value in [('injected_fault_recovered',1),('injected_fault_esr',0x2000000),('injected_fault_elr',0x1000)]:struct.pack_into('>Q',fault,FIELDS.index(field)*8,value)
 assert decode(fault,model[2],model[15],True)['passed'];cases.append(dict(name='separate injected-fault wire',passed=True))
 for label,raw in [('short',wire[:-8]),('extra',wire+b'0')]:
  try:decode(raw,model[2],model[15])
  except AssertionError:cases.append(dict(name='decoder rejects '+label,passed=True))
  else:raise AssertionError(label)
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelIccProbe.h']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,snapshot_bytes=c.sizeof(Snapshot),
  guard_canaries_verified=True,undefined_behavior_sanitizer=True,register_model_only=True,handset_executed=False,
  source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],
  decoder_sha256=sha((ROOT/'scripts/icc_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/icc-probe-host.json').write_text(json.dumps(report,indent=2)+'\n')
 print(str(len(cases))+' ICC actual C/independent decoder checks passed');print(out)

if __name__=='__main__':main()
