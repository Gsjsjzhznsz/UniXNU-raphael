#!/usr/bin/env python3
"""Execute actual C MMIO collector; mutations must preserve read boundaries."""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from entry_probe import ROOT,LIBFDT,sha
from gic_probe import recipe,decode,HEADER,FRAME,WORDS,SGI_OFFSETS,affinity

class GicFrame(c.Structure):_fields_=[(k,c.c_uint64) for k in FRAME]
class Snapshot(c.Structure):_fields_=[(k,c.c_uint64) for k in HEADER]+[('frames',GicFrame*8),('sgi',c.c_uint64*15)]
class Guard(c.Structure):_fields_=[('before',c.c_ubyte*64),('result',Snapshot),('after',c.c_ubyte*64)]


def main():
 parent=ROOT/'artifacts/gic-probe-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/GicProbe.c';core=ROOT/'sources/mu_basecore/MdePkg/Include'
 names={'FdtCheckHeader':'fdt_check_header','FdtGetProp':'fdt_getprop','FdtNextNode':'fdt_next_node','FdtParentOffset':'fdt_parent_offset','FdtPathOffset':'fdt_path_offset','FdtAddressCells':'fdt_address_cells','FdtSizeCells':'fdt_size_cells'}
 command=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all',
 '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),'-I'+str(LIBFDT)]
 command+=['-D'+a+'='+b for a,b in names.items()]
 command+=[str(source),*[str(LIBFDT/(n+'.c')) for n in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_addresses']],'-o',str(out/'gic-probe.so')]
 p=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
 lib=c.CDLL(str(out/'gic-probe.so'));read_type=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p)
 collect=lib.RaphaelCollectGic;collect.argtypes=[c.c_void_p,c.c_uint64,c.c_uint64,c.c_uint64,c.POINTER(Snapshot),read_type,c.c_void_p]
 lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int];lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_path_offset.restype=c.c_int
 lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int]
 lib.fdt_add_subnode.argtypes=[c.c_void_p,c.c_int,c.c_char_p]
 lib.fdt_delprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p]
 blob=(ROOT/'evidence/private/interrupt-audit/20261027T203039.031418Z/live.dtb').read_bytes();plan=recipe(blob)
 be=lambda *v:struct.pack('>'+'I'*len(v),*v)
 def mutated(edits):
  b=c.create_string_buffer(len(blob)+65536);assert lib.fdt_open_into(blob,b,len(b))==0
  for path,key,value in edits:
   n=lib.fdt_path_offset(b,path.encode());assert n>=0
   if key=='__add_node__':assert lib.fdt_add_subnode(b,n,value)>=0
   elif value is None:assert lib.fdt_delprop(b,n,key.encode())==0
   else:assert lib.fdt_setprop(b,n,key.encode(),value,len(value))==0
  return b
 # Deliberately permute redistributor affinities, so CPU index is not frame index.
 affinities=[3,7,2,6,1,0,5,4];mpidr=0x80000000
 values={plan['gicd']+0xffe8:0x30,plan['gicd']:0x12,plan['gicd']+4:0x1f,plan['gicd']+8:0x1234}
 prefix=[plan['gicd']+o for o in [0xffe8,0,4,8]]
 for i,a in enumerate(affinities):
  base=plan['gicr']+i*plan['stride'];values.update({base+0xffe8:0x30,base+8:(16 if i==7 else 0),base+12:a,base:0,base+4:0x5678,base+0x14:0 if a==0 else 6})
  prefix += [base+o for o in [0xffe8,8,12,0,4,0x14]]
 selected=plan['gicr']+affinities.index(affinity(mpidr))*plan['stride']+0x10000
 sequence=prefix+[selected+o for o in SGI_OFFSETS]
 for i,o in enumerate(SGI_OFFSETS):values[selected+o]=0x01020304+i
 cases=[]
 def case(name,status,edits=(),override=None,expected=None,mp=mpidr,protected=(0x836a0000,0x84b00000),decode_ok=False,corrupt_header=False,reader=True):
  b=mutated(edits)
  if corrupt_header:b[0]=b'\0'
  data=dict(values);data.update(override or {});reads=[];unexpected=[];guard=Guard()
  for i in range(64):guard.before[i]=guard.after[i]=0xa5
  @read_type
  def read(address,context):
   reads.append(address)
   if address not in data:unexpected.append(hex(address))
   return data.get(address,0)
  collect(b,mp,*protected,c.byref(guard.result),read if reader else read_type(),None);result=guard.result
  assert not unexpected,(name,unexpected)
  assert bytes(guard.before)==bytes(guard.after)==bytes([0xa5])*64
  assert result.version==1 and result.status==status and result.read_count==len(reads),(name,result.status,result.reason,reads)
  assert reads==(sequence if expected is None else expected),(name,reads,expected)
  if decode_ok:
   raw=b''.join(struct.pack('>Q',v) for v in struct.unpack('<'+'Q'*WORDS,bytes(result)))
   assert decode(raw,b.raw,mp)['passed'];assert result.boot_index==5
  cases.append(dict(name=name,status=status,read_count=len(reads),passed=True))
  return bytes(result)
 base=case('permuted affinity selects boot frame5',4,decode_ok=True)
 case('unknown root has no MMIO',1,[('/','compatible',b'vendor,unknown\0')],expected=[])
 case('malformed header has no MMIO',2,corrupt_header=True,expected=[])
 case('null read callback has no MMIO',2,reader=False,expected=[])
 case('malformed matching root compatible',2,[('/','compatible',b'qcom,sm8150')],expected=[])
 case('full Aff3 mapping selects same frame',4,override={plan['gicr']+5*plan['stride']+12:0x01000000},mp=0x180000000,decode_ok=True)
 path=plan['node']
 case('duplicate GIC even if later node',2,[('/soc','__add_node__',b'duplicate-gic'),('/soc/duplicate-gic','compatible',b'arm,gic-v3\0')],expected=[])
 bad=[('disabled GIC',path,'status',b'disabled\0'),('no ranges','/soc','ranges',None),('unreviewed translation','/soc','ranges',be(1,0,0,0xffffffff)),
 ('wrong cells',path,'#interrupt-cells',be(4)),('multiple GICR',path,'#redistributor-regions',be(2)),
 ('missing stride',path,'redistributor-stride',None),('short stride',path,'redistributor-stride',be(0x20000)),
 ('zero stride',path,'redistributor-stride',be(0,0)),('unaligned stride',path,'redistributor-stride',be(0,0x21000)),
 ('oversize stride',path,'redistributor-stride',be(0,0x200000)),('short GICD',path,'reg',be(0x17a00000,0,0x17a60000,0x100000)),
 ('short GICR',path,'reg',be(0x17a00000,0x10000,0x17a60000,0x10000)),('unaligned MMIO',path,'reg',be(0x17a00004,0x10000,0x17a60000,0x100000)),
 ('overlap windows',path,'reg',be(0x17a00000,0x10000,0x17a00000,0x100000)),('RAM alias',path,'reg',be(0x80000000,0x10000,0x17a60000,0x100000)),
 ('protected extent',path,'reg',be(0x836a0000,0x10000,0x17a60000,0x100000)),('unterminated matching compatible',path,'compatible',b'arm,gic-v3')]
 for name,p,k,v in bad:case('reject '+name,2,[(p,k,v)],expected=[])
 case('invalid protected interval',2,protected=(1,1),expected=[])
 case('unsupported distributor PIDR',3,override={plan['gicd']+0xffe8:0x20},expected=prefix[:1])
 case('unsupported first redistributor PIDR',3,override={plan['gicr']+0xffe8:0x20},expected=prefix[:5])
 case('duplicate frame affinity',3,override={plan['gicr']+plan['stride']+12:3},expected=prefix[:4+6*2])
 case('no boot affinity',3,mp=0x88000000ff,expected=prefix)
 case('missing last within capacity',3,override={plan['gicr']+7*plan['stride']+8:0},expected=prefix)
 case('frame scan bounded by region end',3,edits=[(path,'reg',be(0x17a00000,0x10000,0x17a60000,0xe0000))],expected=prefix[:4+6*7])
 case('last VLPI frame also needs full stride',3,override={plan['gicr']+7*plan['stride']+8:18},expected=prefix)
 case('VLPI stride cannot overlap next frame',3,override={plan['gicr']+8:2},expected=prefix[:10])
 # Independent decoder must reject changed identity, length, frame selection and raw widths.
 wire=b''.join(struct.pack('>Q',v) for v in struct.unpack('<'+'Q'*WORDS,base))
 damaged_fields={'version':2,'status':3,'reason':1,'read_count':0,'gicd':1,'gicr':1,'gicd_bytes':0,'gicr_bytes':0,'stride':0,'mpidr':0,'affinity':1,'frame_count':9,'boot_index':0,'pidr2':0x20,'ctlr':1<<32}
 for field,value in damaged_fields.items():
  changed=bytearray(wire);struct.pack_into('>Q',changed,HEADER.index(field)*8,value)
  try:decode(changed,blob,mpidr)
  except AssertionError:cases.append(dict(name='decoder rejects '+field,passed=True))
  else:raise AssertionError(field)
 for label,index,value in [('unaligned frame base',len(HEADER),1),('bad frame PIDR',len(HEADER)+5,0x20),('oversize frame register',len(HEADER)+2,1<<32),('missing last flag',len(HEADER)+7*6+1,affinities[7]<<32),('oversize SGI word',len(HEADER)+8*6,1<<32)]:
  changed=bytearray(wire);struct.pack_into('>Q',changed,index*8,value)
  try:decode(changed,blob,mpidr)
  except AssertionError:cases.append(dict(name='decoder rejects '+label,passed=True))
  else:raise AssertionError(label)
 for label,changed in [('truncated',wire[:-1]),('trailing',wire+b'\0')]:
  try:decode(changed,blob,mpidr)
  except AssertionError:cases.append(dict(name='decoder rejects '+label,passed=True))
  else:raise AssertionError(label)
 inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelGicProbe.h']
 result=dict(passed=True,case_count=len(cases),cases=cases,command=command,undefined_behavior_sanitizer=True,guard_canaries_verified=True,
  source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],fdt_sha256=sha(blob),
  decoder_sha256=sha((ROOT/'scripts/gic_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),
  source_collection='evidence/private/interrupt-audit/20261027T203039.031418Z',handset_executed=False,mmio_model_only=True)
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');dest=ROOT/'UniXNU-raphael/evidence/gic-probe-host.json';dest.write_text(json.dumps(result,indent=2)+'\n')
 print(str(len(cases))+' actual C and independent decoder checks passed');print(out)

if __name__=='__main__':main()
