#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Run actual UEFI collector against live FDT plus rejected resource mutations."""
import ctypes as c,datetime as dt,json,struct,subprocess
from entry_probe import ROOT,LIBFDT
from ufs_handoff import resources,OFFSETS,decode
class Snapshot(c.Structure):
 _fields_=[('version',c.c_uint64),('status',c.c_uint64),('reads',c.c_uint64),('base',c.c_uint64),('size',c.c_uint64),('offsets',c.c_uint64*18),('first',c.c_uint64*18),('second',c.c_uint64*18)]
def main():
 out=ROOT/'artifacts/ufs-handoff-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True);print(out,flush=True)
 core=ROOT/'sources/mu_basecore/MdePkg/Include';src=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/UfsHandoff.c'
 names={'FdtCheckHeader':'fdt_check_header','FdtGetProp':'fdt_getprop','FdtNextNode':'fdt_next_node','FdtParentOffset':'fdt_parent_offset','FdtPathOffset':'fdt_path_offset','FdtAddressCells':'fdt_address_cells','FdtSizeCells':'fdt_size_cells'}
 command=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),'-I'+str(LIBFDT),*['-D'+a+'='+b for a,b in names.items()],str(src),*[str(LIBFDT/(n+'.c')) for n in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_addresses']],'-o',str(out/'collector.so')]
 build=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(build.stdout+build.stderr);assert build.returncode==0,build.stderr.decode()
 lib=c.CDLL(str(out/'collector.so'));reader=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p);collect=lib.RaphaelCollectUfsHandoff;collect.argtypes=[c.c_void_p,c.c_uint64,c.c_uint64,c.POINTER(Snapshot),reader,c.c_void_p]
 lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int];lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int];lib.fdt_add_subnode.argtypes=[c.c_void_p,c.c_int,c.c_char_p]
 blob=(ROOT/'evidence/private/ufs-readonly/20261030T224241Z/live.dtb').read_bytes();plan=resources(blob);cases=[]
 def case(name,status,edits=(),protected=(0x836a0000,0x84b00000)):
  buf=c.create_string_buffer(len(blob)+65536);assert lib.fdt_open_into(blob,buf,len(buf))==0
  for path,key,value in edits:
   node=lib.fdt_path_offset(buf,path.encode());assert node>=0
   if key=='__add__':assert lib.fdt_add_subnode(buf,node,value)>=0
   else:assert lib.fdt_setprop(buf,node,key.encode(),value,len(value))==0
  calls=[]
  @reader
  def read(address,context):calls.append(address);return (address-plan['base'])^0x12345678
  s=Snapshot();collect(buf,*protected,c.byref(s),read,None)
  expected=[plan['base']+o for o in OFFSETS]*2 if status==3 else []
  assert s.status==status and calls==expected and s.reads==len(calls),(name,s.status,calls)
  if status==3:
   raw=struct.pack('>59Q',*struct.unpack('<59Q',bytes(s)));assert decode(raw,buf.raw)['passed']
  cases.append(dict(name=name,status=status,reads=len(calls),passed=True))
 case('two exact bounded read passes',3)
 case('unsupported root no MMIO',1,[('/','compatible',b'linux,dummy-virt\0')])
 case('unterminated root',2,[('/','compatible',b'qcom,sm8150')])
 case('duplicate UFS',2,[('/soc','__add__',b'ufs-duplicate'),('/soc/ufs-duplicate','compatible',b'qcom,ufshc\0')])
 p=plan['node'];be=lambda *v:struct.pack('>'+'I'*len(v),*v)
 for name,path,key,value in [('disabled host',p,'status',b'disabled\0'),('disabled bus','/soc','status',b'disabled\0'),('bad bus mapping','/soc','ranges',be(1,0,0,0xffffffff)),('bad register name',p,'reg-names',b'ufs_ice\0'),('truncated reg',p,'reg',be(plan['base'])),('unaligned base',p,'reg',be(plan['base']+1,plan['bytes'])),('short MMIO',p,'reg',be(plan['base'],0x40)),('RAM alias',p,'reg',be(0x80000000,plan['bytes']))]:case(name,2,[(path,key,value)])
 case('protected image overlap',2,protected=(plan['base'],plan['base']+plan['bytes']))
 case('invalid protected interval',2,protected=(1,1))
 report=dict(passed=True,case_count=len(cases),cases=cases,compile_command=command,undefined_behavior_sanitizer=True,handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,case_count=len(cases))))
if __name__=='__main__':main()
