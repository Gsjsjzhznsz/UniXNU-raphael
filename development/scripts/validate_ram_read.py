#!/usr/bin/env python3
"""Execute actual sparse-read C with libfdt/UBSan and protected result buffers."""
import ctypes as c,datetime as dt,json,struct,subprocess,tempfile
from entry_probe import ROOT,LIBFDT,sha
from ram_read_probe import FIELDS,encode,policy,decode,sourced_policy,MASK
class Range(c.Structure):_fields_=[('base',c.c_uint64),('bytes',c.c_uint64)]
class Entry(c.Structure):_fields_=[(k,c.c_uint64) for k in ['el','sctlr','daif','mmfr0','bits','frequency','count']]+[('guards',Range*8)]
class Snapshot(c.Structure):_fields_=[(k,c.c_uint64) for k in FIELDS]
class Guard(c.Structure):_fields_=[('before',c.c_ubyte*64),('result',Snapshot),('after',c.c_ubyte*64)]
def main():
 parent=ROOT/'artifacts/ram-read-host';parent.mkdir(exist_ok=True,parents=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/RamRead.c';core=ROOT/'sources/mu_basecore/MdePkg/Include'
 shim=out/'shim.c';shim.write_text('#include <stdint.h>\nuint32_t Fdt32ToCpu(uint32_t v){return __builtin_bswap32(v); }\n')
 aliases={'FdtCheckHeader':'fdt_check_header','FdtGetProp':'fdt_getprop','FdtNextNode':'fdt_next_node','FdtAddressCells':'fdt_address_cells','FdtSizeCells':'fdt_size_cells','FdtPathOffset':'fdt_path_offset'}
 cmd=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),'-I'+str(LIBFDT)]+['-D'+a+'='+b for a,b in aliases.items()]+[str(source),str(shim)]+[str(LIBFDT/(n+'.c')) for n in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_check','fdt_addresses']]+['-o',str(out/'ram-read.so')]
 p=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
 lib=c.CDLL(str(out/'ram-read.so'));rt=c.CFUNCTYPE(c.c_uint8,c.c_uint64,c.POINTER(c.c_uint64),c.c_void_p);ct=c.CFUNCTYPE(c.c_uint64,c.c_void_p)
 call=lib.RaphaelReadRamWindow;call.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(Entry),c.POINTER(Snapshot),rt,ct,c.c_void_p]
 lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int];lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int];lib.fdt_add_mem_rsv.argtypes=[c.c_void_p,c.c_uint64,c.c_uint64]
 provenance,raw=sourced_policy();expected=policy(raw);base=expected['base'];blob=(ROOT/json.loads((ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json').read_text())['collection']/'live.dtb').read_bytes()
 cases=[]
 def case(name,status,patch=None,epatch=None,edits=(),fail=None,step=100,start=10000,back=False,header_guard=False,entry_guard=False,null=None,raw_blob=None):
  b=c.create_string_buffer(len(blob)+65536);assert lib.fdt_open_into(blob,b,len(b))==0
  for path,key,value in edits:
   n=lib.fdt_path_offset(b,path.encode());assert n>=0
   assert lib.fdt_setprop(b,n,key.encode(),value,len(value))==0
  if header_guard:assert lib.fdt_add_mem_rsv(b,base,4096)==0
  if raw_blob is not None:b=c.create_string_buffer(raw_blob)
  e=Entry(4,0,0x3c0,2,40,19200000,1);e.guards[0]=Range(0x80000000,0x4b00000)
  if entry_guard:e.guards[0]=Range(base+8,4096)
  for k,v in (epatch or {}).items():setattr(e,k,v)
  rb=bytearray(raw)
  for off,v in (patch or {}).items():struct.pack_into('<Q',rb,off*8,v)
  pol=c.create_string_buffer(bytes(rb));g=Guard();c.memset(c.byref(g),0xa5,c.sizeof(g));reads=[];clocks=[]
  @rt
  def read(address,value,ctx):
   reads.append(address);value[0]=(address^0x1122334455667788)&MASK
   return int(len(reads)!=fail)
  @ct
  def clock(ctx):
   value=(start+len(clocks)*step)&MASK
   if back and len(clocks)==2:value=start+1
   clocks.append(value);return value
  call(None if null=='fdt' else b,None if null=='policy' else pol,len(rb),None if null=='entry' else c.byref(e),c.byref(g.result),rt() if null=='read' else read,ct() if null=='counter' else clock,None)
  o=g.result;assert bytes(g.before)==bytes(g.after)==b'\xa5'*64
  assert o.version==1 and o.status==status,(name,o.status,o.reason,o.attempted)
  assert o.attempted==len(reads) and o.completed==len(reads)-int(fail is not None and len(reads)==fail)
  assert reads==[base+i*0x200000+j for i in range(128) for j in [0,0x200000-8]][:len(reads)],name
  wire=struct.pack('>26Q',*struct.unpack('<26Q',bytes(o)))
  if status==3:
   assert decode(wire,expected)['passed']
   digest=14695981039346656037
   for a in reads:digest=((digest^a)*1099511628211)&MASK;digest=((digest^(a^0x1122334455667788))*1099511628211)&MASK
   assert o.digest==digest and o.completed==256 and o.nonzero==256
  else:
   try:decode(wire,expected)
   except AssertionError:pass
   else:raise AssertionError('partial wire accepted '+name)
  cases.append(dict(name=name,passed=True,status=status,reads=len(reads)));return wire
 wire=case('sourced phone FDT and all 256 exact sparse addresses',3)
 for k in ['fdt','policy','entry','read','counter']:case('null '+k,5 if k=='fdt' else 4,null=k)
 for field,val in [(0,2),(1,63),(2,0),(3,base+8),(3,MASK-0xffff),(4,0),(4,0x20000000),(5,4096),(6,255),(7,0),(7,129)]:case('policy field '+str(field)+' value '+str(val),4,patch={field:val})
 for k,v in [('el',8),('sctlr',1),('sctlr',4),('sctlr',4096),('daif',0x340),('frequency',999),('frequency',1000000001),('count',0),('count',9)]:case('entry rejects '+k+str(v),4,epatch={k:v})
 for k,v in [('mmfr0',7),('bits',36),('mmfr0',0)]:case('PA rejects '+k+str(v),4,epatch={k:v})
 case('live SP/LR guard overlap',5,entry_guard=True)
 case('policy guard overlap',5,patch={8:base,9:4096})
 case('policy guard overflow',5,patch={8:MASK,9:1})
 case('header reservation overlap',5,header_guard=True)
 case('unsupported compatible',5,edits=[('/','compatible',b'wrong\0')])
 case('unterminated compatible',5,edits=[('/','compatible',b'qcom,sm8150')])
 case('malformed cells',5,edits=[('/','#address-cells',struct.pack('>I',3))])
 case('nonempty ranges',5,edits=[('/reserved-memory','ranges',struct.pack('>I',0))])
 case('initrd overlap',5,edits=[('/chosen','linux,initrd-start',struct.pack('>Q',base)),('/chosen','linux,initrd-end',struct.pack('>Q',base+4096))])
 case('initrd reversed',5,edits=[('/chosen','linux,initrd-end',struct.pack('>Q',1))])
 case('bad magic',5,raw_blob=b'BAD!'+blob[4:])
 for n in [1,2,128,256]:case('callback failure '+str(n),7,fail=n)
 case('100ms time bound',6,step=1920001)
 case('nonmonotonic counter',6,back=True)
 case('counter wrap rejected',6,start=MASK-1)
 for key,val in dict(version=2,status=2,reason=1,base=0,bytes=0,stride=0,requested=255,attempted=255,completed=0,active_address=0,nonzero=257,start_counter=MASK,end_counter=MASK,frequency=0,mmfr0=7,physical_bits=36,ram_ranges=0,fixed_reservations=129,header_reservations=129,policy_guards=0,entry_guards=0,current_el=8,sctlr=1,daif=0).items():
  damaged=bytearray(wire);struct.pack_into('>Q',damaged,FIELDS.index(key)*8,val)
  try:decode(damaged,expected)
  except AssertionError:cases.append(dict(name='wire rejects '+key,passed=True))
  else:raise AssertionError(key)
 for damaged in [wire[:-8],wire+b'0']:
  try:decode(damaged,expected)
  except AssertionError:cases.append(dict(name='wire size rejected',passed=True))
  else:raise AssertionError('wire size')
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelRamRead.h']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,undefined_behavior_sanitizer=True,guard_canaries_verified=True,snapshot_bytes=c.sizeof(Snapshot),policy_evidence=provenance,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],decoder_sha256=sha((ROOT/'scripts/ram_read_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/ram-read-host.json').write_text(json.dumps(report,indent=2)+'\n');print(len(cases),'actual C/libfdt/UBSan/canary/wire checks passed');print(out)
from pathlib import Path
if __name__=='__main__':main()
