#!/usr/bin/env python3
"""Actual C PPI permission collector with FDT mutations, guards and WI models."""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from entry_probe import ROOT,LIBFDT,sha
from validate_gic_probe import Snapshot as GicSnapshot
from validate_icc_probe import Snapshot as IccSnapshot
from gic_probe import recipe
from ppi_probe import FIELDS,decode,resource
from inspect_device import read_fdt,node_path
class Snapshot(c.Structure):_fields_=[(k,c.c_uint64) for k in FIELDS]
class Guard(c.Structure):_fields_=[('before',c.c_ubyte*64),('result',Snapshot),('after',c.c_ubyte*64)]
def main():
 parent=ROOT/'artifacts/ppi-probe-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/PpiProbe.c';core=ROOT/'sources/mu_basecore/MdePkg/Include'
 aliases={'FdtCheckHeader':'fdt_check_header','FdtGetProp':'fdt_getprop','FdtNextNode':'fdt_next_node','FdtParentOffset':'fdt_parent_offset'}
 command=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all',
 '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),'-I'+str(LIBFDT)]
 command+=['-D'+a+'='+b for a,b in aliases.items()]
 command+=[str(source),*[str(LIBFDT/(n+'.c')) for n in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_addresses']],'-o',str(out/'ppi-probe.so')]
 p=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
 lib=c.CDLL(str(out/'ppi-probe.so'));rt=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p);wt=c.CFUNCTYPE(None,c.c_uint64,c.c_uint32,c.c_void_p);ct=c.CFUNCTYPE(c.c_uint64,c.c_void_p)
 collect=lib.RaphaelProbePhysicalPpi;collect.argtypes=[c.c_void_p,c.POINTER(GicSnapshot),c.POINTER(IccSnapshot),c.POINTER(Snapshot),rt,wt,ct,c.c_void_p]
 lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int];lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_path_offset.restype=c.c_int
 lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int];lib.fdt_delprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p]
 lib.fdt_add_subnode.argtypes=[c.c_void_p,c.c_int,c.c_char_p]
 blob=(ROOT/'evidence/private/interrupt-audit/20261027T203039.031418Z/live.dtb').read_bytes();plan=recipe(blob);intid,flags=resource(blob)
 be=lambda *v:struct.pack('>'+'I'*len(v),*v)
 def mutate(edits):
  b=c.create_string_buffer(len(blob)+65536);assert lib.fdt_open_into(blob,b,len(b))==0
  for path,key,value in edits:
   n=lib.fdt_path_offset(b,path.encode());assert n>=0
   if key=='__add_node__':assert lib.fdt_add_subnode(b,n,value)>=0
   elif value is None:assert lib.fdt_delprop(b,n,key.encode())==0
   else:assert lib.fdt_setprop(b,n,key.encode(),value,len(value))==0
  return b
 cases=[];sgi=plan['gicr']+5*plan['stride']+0x10000;rd=sgi-0x10000;mask=1<<intid
 def case(name,status,edits=(),gchange=None,ichange=None,ivals=None,ignored=False,clear_ignored=False,
          rwp=0,stuck_counter=False,fresh=None,other_change=False,pending_after=False,no_gic=False,no_icc=False,no_read=False,no_write=False,no_counter=False):
  b=mutate(edits);g=GicSnapshot();g.version=1;g.status=4;g.gicd=plan['gicd'];g.gicd_bytes=plan['gicd_bytes'];g.gicr=plan['gicr'];g.gicr_bytes=plan['gicr_bytes'];g.stride=plan['stride'];g.frame_count=8;g.boot_index=5;g.mpidr=0x81000000;g.affinity=0;g.frames[5].base=rd;g.frames[5].typer=0;g.ctlr=0x10;g.sgi[1]=0x80
  i=IccSnapshot();i.version=1;i.status=5;i.attempted=i.completed=16;i.failed_selector=(1<<64)-1;i.values[0]=4;i.values[1]=0x3c0;i.values[2]=g.mpidr;i.values[3]=1;i.values[15]=19200000
  for k,v in (gchange or {}).items():setattr(g,k,v)
  for k,v in (ichange or {}).items():setattr(i,k,v)
  for k,v in (ivals or {}).items():i.values[k]=v
  values={plan['gicd']:g.ctlr,rd:0,sgi+0x100:0x80,sgi+0x200:0,sgi+0x300:0};values.update(fresh or {})
  reads=[];writes=[];bad=[];clock=[1000];busy=[rwp]
  @rt
  def read(address,context):
   reads.append(address)
   if address not in values:bad.append(address);return 0
   if address==rd and len(writes)==2 and busy[0]:
    if busy[0]>0:busy[0]-=1
    return 8
   return values[address]
  @wt
  def write(address,value,context):
   writes.append((address,value))
   if address not in [sgi+0x100,sgi+0x180] or value!=mask:bad.append((address,value));return
   if address==sgi+0x100:
    if not ignored:values[sgi+0x100]|=value
    if other_change:values[sgi+0x100]^=1<<5
   elif not clear_ignored:values[sgi+0x100]&=~value
   if pending_after:values[sgi+0x200]|=mask
  @ct
  def counter(context):
   v=clock[0]
   if not stuck_counter:clock[0]+=19200
   return v
  guard=Guard()
  for n in range(64):guard.before[n]=guard.after[n]=0xa5
  collect(b,None if no_gic else c.byref(g),None if no_icc else c.byref(i),c.byref(guard.result),rt() if no_read else read,wt() if no_write else write,ct() if no_counter else counter,None)
  o=guard.result
  assert not bad,(name,bad)
  assert bytes(guard.before)==bytes(guard.after)==b'\xa5'*64
  assert o.version==1 and o.status==status and o.read_count==len(reads) and o.write_count==len(writes),(name,o.status,o.reason,len(reads),writes)
  if status in [1,2]:assert not writes
  if status==1 or status==2 and o.reason==1:assert not reads
  if writes:assert writes==[(sgi+0x100,mask),(sgi+0x180,mask)]
  raw=struct.pack('>20Q',*struct.unpack('<20Q',bytes(o)));gd=dict(boot_index=5,ctlr=g.ctlr,frames=[dict(base=0) for _ in range(5)]+[dict(base=rd)],sgi=dict(enabled=0x80))
  if status in [3,6]:assert decode(raw,b.raw,gd)['passed']
  else:
   try:decode(raw,b.raw,gd)
   except (AssertionError,ValueError):pass
   else:raise AssertionError('failed result accepted '+name)
  cases.append(dict(name=name,status=status,reads=len(reads),writes=len(writes),passed=True));return raw,gd
 wire,gd=case('single dynamically selected PPI writable and restored',6)
 case('nonsecure write ignored is diagnostic not permission',3,ignored=True)
 case('RWP delayed propagation completes',6,rwp=3)
 case('RWP timeout still reads final state',5,rwp=-1)
 case('RWP poll count bounded with stopped counter',5,rwp=-1,stuck_counter=True)
 case('clear ignored is not restored',5,clear_ignored=True)
 case('unexpected other enable change is rejected',5,other_change=True)
 case('unexpected target pending is rejected',5,pending_after=True)
 for label,kw in [('no GIC',dict(no_gic=True)),('no ICC',dict(no_icc=True)),('no read',dict(no_read=True)),('no write',dict(no_write=True)),('no counter',dict(no_counter=True))]:case(label,1,**kw)
 for k,v in [('version',2),('status',3),('frame_count',0),('frame_count',9),('boot_index',8),('gicd',0),('gicd_bytes',4),('gicr',0),('gicr_bytes',0),('affinity',1)]:case('GIC prerequisite '+k,1,gchange={k:v})
 for k,v in [('version',2),('status',4),('attempted',15),('completed',15),('failed_selector',1),('trap_esr',1),('trap_elr',1)]:case('ICC prerequisite '+k,1,ichange={k:v})
 for k,v in [(0,8),(1,0x340),(2,1),(3,0),(7,1),(10,1),(10,8),(15,0),(15,1000000001)]:case('ICC value '+str(k),1,ivals={k:v})
 for name,values in [('fresh distributor changed',{plan['gicd']:0x12}),('fresh enable changed',{sgi+0x100:0}),('target already pending',{sgi+0x200:mask}),('target active',{sgi+0x300:mask}),('RD write already pending',{rd:8})]:case(name,2,fresh=values)
 timer='/soc/timer';pdc='/soc/interrupt-controller@0xb220000';gic='/soc/interrupt-controller@17a00000'
 bad_edits=[('root unknown',[('/','compatible',b'unknown\0')]),('root malformed',[('/','compatible',b'qcom,sm8150')]),('timer disabled',[(timer,'status',b'disabled\0')]),('missing frequency',[(timer,'clock-frequency',None)]),('wrong frequency',[(timer,'clock-frequency',be(1))]),('short frequency',[(timer,'clock-frequency',b'0')]),('short interrupts',[(timer,'interrupts',be(1,2,0xf08))]),('extended interrupts',[(timer,'interrupts-extended',b'')]),('timer parent invalid',[(timer,'interrupt-parent',be(0xffff))]),('PDC wrong cells',[(pdc,'#interrupt-cells',be(2))]),('PDC wrong compatible',[(pdc,'compatible',b'unknown\0')]),('PDC disabled',[(pdc,'status',b'disabled\0')]),('GIC wrong cells',[(gic,'#interrupt-cells',be(2))]),('GIC disabled',[(gic,'status',b'disabled\0')]),('duplicate timer',[('/soc','__add_node__',b'other-timer'),('/soc/other-timer','compatible',b'arm,armv8-timer\0')]),('duplicate GIC',[('/soc','__add_node__',b'other-gic'),('/soc/other-gic','compatible',b'arm,gic-v3\0')])]
 tree=read_fdt(blob);nodes={node_path(n):n for n in tree.walk()}
 gh=nodes[gic].cells('phandle')[0];ph=nodes[pdc].cells('phandle')[0]
 bad_edits.extend([
  ('PDC self cycle',[(pdc,'interrupt-parent',be(ph))]),
  ('PDC no controller flag',[(pdc,'interrupt-controller',None)]),
  ('GIC no controller flag',[(gic,'interrupt-controller',None)]),
  ('PDC malformed controller flag',[(pdc,'interrupt-controller',be(1))]),
  ('conflicting GIC handle alias',[(gic,'linux,phandle',be(gh+10000))]),
  ('duplicate GIC handle',[('/soc','__add_node__',b'dup-handle'),('/soc/dup-handle','phandle',be(gh))]),
  ('phone bypasses PDC',[(timer,'interrupt-parent',be(gh))])])
 for name,edits in bad_edits:case('FDT '+name,2,edits=edits)
 specs=[1,1,0xf08,1,2,0xf08,1,3,0xf08,1,0,0xf08]
 for idx,value,label in [(3,0,'not PPI'),(4,16,'out of range'),(5,1,'edge'),(5,0x10000,'unknown flags'),(4,1,'aliases secure PPI')]:
  changed=list(specs);changed[idx]=value;case('FDT '+label,2,edits=[(timer,'interrupts',be(*changed))])
 changed={'version':2,'status':5,'reason':1,'intid':30,'flags':4,'sgi_base':0,'mask':1,'enabled_before':0,'enabled_during':0,'enabled_after':0,'active_before':mask,'pending_before':mask,'rwp_polls':0,'write_count':1,'ctlr_before':1,'ctlr_after':0,'read_count':0,'restore_ok':0,'pending_after':mask,'active_after':mask}
 for field,value in changed.items():
  raw=bytearray(wire);struct.pack_into('>Q',raw,FIELDS.index(field)*8,value)
  try:decode(raw,blob,gd)
  except (AssertionError,ValueError):cases.append(dict(name='wire rejects '+field,passed=True))
  else:raise AssertionError(field)
 for label,raw in [('short',wire[:-8]),('long',wire+b'0')]:
  try:decode(raw,blob,gd)
  except AssertionError:cases.append(dict(name='wire rejects '+label,passed=True))
  else:raise AssertionError(label)
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPpiProbe.h']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=command,snapshot_bytes=c.sizeof(Snapshot),guard_canaries_verified=True,undefined_behavior_sanitizer=True,
  mmio_model_only=True,handset_executed=False,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],
  decoder_sha256=sha((ROOT/'scripts/ppi_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/ppi-probe-host.json').write_text(json.dumps(report,indent=2)+'\n')
 print(len(cases),'actual C/FDT/UBSan/guard/independent wire checks passed');print(out)
if __name__=='__main__':main()
