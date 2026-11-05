#!/usr/bin/env python3
"""Inspect actual native Mach-O, freeze successful output and compile records."""
import argparse,datetime as dt,json,shutil,struct,subprocess
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--build-report',type=Path,required=True);p.add_argument('--index',type=Path,default=ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json',help='Separate evidence index for experimental configurations');a=p.parse_args();bp=a.build_report.resolve();b=json.loads(bp.read_text());assert b['passed'] and b['native_compile_only'] and not b['prelink_executed'] and not b['handset_executed']
 source=ROOT/b['native_macho']['path'];data=source.read_bytes();assert sha(data)==b['native_macho']['sha256']
 magic,cpu,sub,kind,ncmds,nbytes,flags,reserved=struct.unpack_from('<8I',data)
 assert magic==0xfeedfacf and cpu==0x100000c and kind==2 and reserved==0 and 0<ncmds<1024 and 32+nbytes<=len(data)
 commands=[];segments=[];entries=[];symtab=None;offset=32
 def name(raw):return raw.split(b'\0',1)[0].decode('ascii')
 for _ in range(ncmds):
  cmd,size=struct.unpack_from('<2I',data,offset);assert size>=8 and size%8==0 and offset+size<=32+nbytes
  commands.append(dict(command=cmd,bytes=size))
  if cmd==0x19:
   _,_,raw,vm,vs,fo,fs,maxp,initp,ns,sflags=struct.unpack_from('<II16s4Q4I',data,offset)
   assert size==72+ns*80 and vm+vs<1<<64 and fo+fs<=len(data) and fs<=vs and vm%4096==fo%4096==0 and maxp<8 and initp&~maxp==0
   sections=[]
   for i in range(ns):
    sn,sg,address,length,fileoff,align,reloc,nreloc,sf,_,_,_=struct.unpack_from('<16s16sQQ8I',data,offset+72+80*i)
    assert address>=vm and address+length<=vm+vs and align<=31
    if sf&255 not in [1,12,18]:assert fileoff+length<=len(data)
    sections.append(dict(name=name(sn),segment=name(sg),virtual_address=address,bytes=length,file_offset=fileoff,flags=sf))
   segments.append(dict(name=name(raw),virtual_address=vm,virtual_bytes=vs,file_offset=fo,file_bytes=fs,max_protection=maxp,initial_protection=initp,sections=sections))
  elif cmd==5:
   flavor,count=struct.unpack_from('<2I',data,offset+8);assert flavor==6 and count==68 and size==288
   entries.append(struct.unpack_from('<Q',data,offset+16+32*8)[0])
  elif cmd==2:
   assert size==24 and symtab is None;symtab=struct.unpack_from('<4I',data,offset+8)
  offset+=size
 assert offset==32+nbytes and len(entries)==1 and len(segments)>0
 for i,x in enumerate(segments):
  for y in segments[i+1:]:
   if x['virtual_bytes'] and y['virtual_bytes']:assert x['virtual_address']+x['virtual_bytes']<=y['virtual_address'] or y['virtual_address']+y['virtual_bytes']<=x['virtual_address']
 assert any(s['initial_protection']&4 and s['virtual_address']<=entries[0]<s['virtual_address']+s['virtual_bytes'] for s in segments)
 assert symtab
 so,nsy,st,ss=symtab;assert so+nsy*16<=len(data) and st+ss<=len(data)
 undefined=[];starts={}
 for i in range(nsy):
  index,t,sect,desc,value=struct.unpack_from('<IBBHQ',data,so+i*16);assert index<ss
  end=data.find(b'\0',st+index,st+ss);assert end>=0
  symbol=data[st+index:end].decode('utf-8',errors='replace')
  if t&0xe==0 and not t&0xe0 and sect==0:undefined.append(symbol)
  if symbol in ['_start','_start_first_cpu','_arm_init','_kernel_bootstrap']:starts[symbol]=value
 parent=ROOT/'artifacts/native-kernel-inspection';parent.mkdir(parents=True,exist_ok=True)
 out=parent/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(exist_ok=False)
 (out/'native-kernel.macho').write_bytes(data);(out/'build-report.json').write_bytes(bp.read_bytes())
 records_root=ROOT/b['compile_records_root'] if b.get('outputs_frozen') else source.parents[1];records=[]
 if b.get('outputs_frozen'):
  assert records_root.is_relative_to(bp.parent) and source.is_relative_to(bp.parent)
  for item in b['frozen_compile_records']:assert sha((records_root/item['path']).read_bytes())==item['sha256']
 for source_record in records_root.rglob('*.o.json'):
  relative=source_record.relative_to(records_root);target=out/'compile-records'/relative;target.parent.mkdir(parents=True,exist_ok=True);raw=source_record.read_bytes();target.write_bytes(raw);records.append(dict(path=str(relative),sha256=sha(raw)))
 assert len(records)==b['compile_records']
 logs=[]
 for item in b['logs']:
  src=ROOT/item['path'];raw=src.read_bytes();assert sha(raw)==item['sha256'];target=out/'logs'/src.name;target.parent.mkdir(exist_ok=True);target.write_bytes(raw);logs.append(dict(path=str(target.relative_to(ROOT)),sha256=sha(raw)))
 for tool,args in [('llvm-objdump',['--macho','--private-headers']),('llvm-nm',['--undefined-only'])]:
  x=subprocess.run([tool,*args,str(out/'native-kernel.macho')],capture_output=True);(out/(tool+'.log')).write_bytes(x.stdout+x.stderr);assert x.returncode==0
 report=dict(passed=True,artifact_directory=str(out.relative_to(ROOT)),native_macho_sha256=sha(data),native_macho_bytes=len(data),cpu='ARM64',filetype='MH_EXECUTE',load_commands=commands,segments=segments,entry_virtual_address=entries[0],startup_symbols=starts,undefined_symbols=undefined,undefined_symbol_count=len(undefined),compile_record_count=len(records),compile_records=records,logs=logs,build_report_sha256=sha(bp.read_bytes()),prelink_executed=False,handset_executed=False,bootable_phone_image=False,addresses_are_macho_virtual_not_phone_physical=True,inspector_sha256=sha(Path(__file__).read_bytes()))
 for dest in [out/'report.json',a.index.resolve()]:dest.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['passed','artifact_directory','native_macho_sha256','native_macho_bytes','undefined_symbol_count','compile_record_count','prelink_executed','handset_executed']},indent=2))
if __name__=='__main__':main()
