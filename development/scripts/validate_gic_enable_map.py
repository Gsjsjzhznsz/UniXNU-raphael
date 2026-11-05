#!/usr/bin/env python3
"""Run the actual read-only C collector with UBSan and strict MMIO models."""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from entry_probe import ROOT,sha
from validate_gic_probe import Snapshot as GicSnapshot
from gic_enable_map import HEADER,WORDS,decode
class Snapshot(c.Structure):
 _fields_=[(k,c.c_uint64) for k in HEADER]+[('spi',c.c_uint64*31),('local',c.c_uint64*8),('ctlr',c.c_uint64*8)]
class Guard(c.Structure):
 _fields_=[('before',c.c_ubyte*64),('result',Snapshot),('after',c.c_ubyte*64)]
def main():
 parent=ROOT/'artifacts/gic-enable-map-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/GicEnableMap.c';core=ROOT/'sources/mu_basecore/MdePkg/Include'
 command=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all',
 '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),str(source),'-o',str(out/'gic-enable-map.so')]
 p=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
 lib=c.CDLL(str(out/'gic-enable-map.so'));rt=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p)
 collect=lib.RaphaelCollectGicEnableMap;collect.argtypes=[c.POINTER(GicSnapshot),c.POINTER(Snapshot),rt,c.c_void_p]
 # Synthetic addresses exercise the interface; no handset board address is used.
 cases=[];d=0x10000000;r=0x20000000
 def case(name,status=3,words=29,frames=8,changes=None,frame_changes=None,values=None,second=None,header=None,after=None,no_gic=False,no_read=False,no_output=False):
  g=GicSnapshot();g.version=1;g.status=4;g.pidr2=0x3b;g.typer=words;g.ctlr=0x10;g.frame_count=frames;g.boot_index=0
  g.gicd=d;g.gicd_bytes=0x10000;g.gicr=r;g.gicr_bytes=0x100000
  for n in range(min(frames,8)):g.frames[n].base=r+n*0x20000
  for key,value in (changes or {}).items():setattr(g,key,value)
  for n,value in (frame_changes or {}).items():g.frames[n].base=value
  normal={d:g.ctlr,d+4:g.typer}
  for n in range(words):normal[d+0x104+n*4]=0
  for n in range(min(frames,8)):normal[r+n*0x20000]=normal[r+n*0x20000+0x10100]=0
  normal.update(values or {});second=second or {};header=header or {}
  accesses=[];bad=[];count={}
  @rt
  def read(address,context):
   accesses.append(address);seen=count.get(address,0);count[address]=seen+1
   if address not in normal:bad.append(address);return 0
   if address in header:return header[address]
   if address==d and seen and after is not None:return after
   return second.get(address,normal[address]) if seen else normal[address]
  guard=Guard()
  for n in range(64):guard.before[n]=guard.after[n]=0xa5
  collect(None if no_gic else c.byref(g),None if no_output else c.byref(guard.result),rt() if no_read else read,None)
  assert not bad,(name,bad)
  assert bytes(guard.before)==bytes(guard.after)==b'\xa5'*64,name
  o=guard.result
  if no_output:assert not accesses
  else:
   assert o.version==1 and o.status==status and o.read_count==len(accesses),(name,o.status,len(accesses))
   if status==1:assert not accesses,name
   elif status==2:assert accesses==[d,d+4],name
   else:
    once=[d+0x104+n*4 for n in range(words)]
    once += [a for n in range(frames) for a in (r+n*0x20000+0x10100,r+n*0x20000)]
    assert accesses==[d,d+4]+once+once+[d],name
    raw=struct.pack('>60Q',*struct.unpack('<60Q',bytes(o)))
    gd=dict(pidr2=g.pidr2,typer=g.typer,frame_count=g.frame_count,ctlr=g.ctlr)
    decoded=decode(raw,gd);assert decoded['passed']
    expected_disabled=not any(values.values()) if values else True
    if status==4:assert decoded['changed_words'] and not decoded['all_observed_disabled']
  cases.append(dict(name=name,status=status if not no_output else None,reads=len(accesses),passed=True))
  if status in [3,4] and not no_output:return raw,gd
 wire,gd=case('29 SPI words and eight redistributors')
 case('zero SPI words and one redistributor',words=0,frames=1)
 case('all 31 standard SPI words',words=31)
 case('one nonzero SPI enable',values={d+0x104+28*4:0x80000000})
 case('last redistributor PPI enabled',values={r+7*0x20000+0x10100:1<<18})
 case('LPI enabled',values={r+5*0x20000:1})
 case('non LPI CTLR flag remains visible',values={r+5*0x20000:8})
 case('SPI changes second pass',4,second={d+0x104:2})
 case('local changes second pass',4,second={r+0x10100:4})
 case('LPI changes second pass',4,second={r:1})
 case('non LPI CTLR changes second pass',4,second={r:8})
 case('distributor changes after samples',4,after=0x12)
 case('first enabled then zero is still in accumulated OR',4,values={d+0x104:0x80},second={d+0x104:0})
 case('header distributor changed',2,header={d:0x12})
 case('header TYPER changed',2,header={d+4:30})
 for name,kw in [('null GIC',dict(no_gic=True)),('null read',dict(no_read=True)),('null output',dict(no_output=True))]:case(name,1,**kw)
 for key,value in [('version',2),('status',3),('pidr2',0x4b),('typer',1<<8),('typer',1<<9),('typer',1<<11),('typer',1<<15),('typer',1<<32),('frame_count',0),('frame_count',9),('boot_index',8),('gicd',0),('gicd',d+4),('gicd_bytes',0xffff),('gicd',(1<<64)-0x10000),('gicr',0),('gicr',r+4),('gicr_bytes',0x1ffff),('gicr',(1<<64)-0x10000),('gicd',r)]:case('reject '+key+' '+str(value),1,changes={key:value})
 for name,value in [('misaligned',r+1),('below region',r-0x20000),('beyond region',r+0x100000),('duplicate',r)]:case('reject frame '+name,1,frame_changes={7:value})
 mutations={'version':2,'status':2,'reason':1,'read_count':1,'spi_words':31,'frame_count':7,'enabled_spi_or':1,'enabled_local_or':1,'lpi_enabled_or':1,'changed_words':1,'distributor_before':0x12,'distributor_after':0x12,'all_observed_disabled':0}
 def reject(name,raw):
  try:decode(raw,gd)
  except (AssertionError,ValueError):cases.append(dict(name='wire rejects '+name,passed=True))
  else:raise AssertionError('accepted corrupt wire '+name)
 for key,value in mutations.items():
  raw=bytearray(wire);struct.pack_into('>Q',raw,HEADER.index(key)*8,value);reject(key,raw)
 for index,value in [(13+29,1),(44,1<<40),(52,1<<40)]:
  raw=bytearray(wire);struct.pack_into('>Q',raw,index*8,value);reject('array '+str(index),raw)
 reject('short',wire[:-8]);reject('long',wire+b'0')
 changed,changed_gd=case('changed wire reference',4,second={d+0x104:2})
 for key,value in [('enabled_spi_or',1<<32),('enabled_local_or',1<<32),('lpi_enabled_or',2),('changed_words',100)]:
  raw=bytearray(changed);struct.pack_into('>Q',raw,HEADER.index(key)*8,value);reject('changed '+key,raw)
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelGicEnableMap.h']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=command,snapshot_bytes=c.sizeof(Snapshot),guard_canaries_verified=True,undefined_behavior_sanitizer=True,
  mmio_model_only=True,mmio_write_callback=False,handset_executed=False,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],
  decoder_sha256=sha((ROOT/'scripts/gic_enable_map.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/gic-enable-map-host.json').write_text(json.dumps(report,indent=2)+'\n')
 print(len(cases),'actual C/MMIO/UBSan/guard/independent wire checks passed');print(out)
if __name__=='__main__':main()
