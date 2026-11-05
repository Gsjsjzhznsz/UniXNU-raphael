#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Check the actual 190-slot OS storage ABI and bind only audited base imports.

Uses the relocation method from pinned UniXNU build-virtio-mmio-bindings.py.
"""
import argparse,json,os,re,struct,subprocess,sys
from pathlib import Path
from entry_probe import ROOT,sha
sys.path.insert(0,str(ROOT/'sources/UniXNU/kits/XnuPrelink'))
import native_prelink as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--object-report',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
 build=json.loads(a.object_report.read_text());assert build['passed'];out=a.object_report.resolve().parent
 objpath=out/'RaphaelUfsBlock.o';obj=objpath.read_bytes();assert sha(obj)==build['object_sha256']
 audit=json.loads(a.audit.read_text());assert audit['live_native_4k'] and audit['method_slots']==190 and audit['abstract_complete_destructors_trap']
 assert sha(a.candidate.read_bytes())==audit['candidate_sha256']
 image=np.macho(obj);offset=next(at for cmd,at,size in image['commands'] if cmd==2);sy,count,st,_=struct.unpack_from('<4I',obj,offset+8)
 symbols=[]
 for i in range(count):
  ix,kind,_,_,value=struct.unpack_from('<IBBHQ',obj,sy+i*16);symbols.append((obj[st+ix:obj.index(b'\0',st+ix)].decode(),value,kind))
 name='RaphaelUfsVolume';mangled=str(len(name))+name;vtable=next(v for n,v,k in symbols if n=='__ZTV'+mangled);relocations={}
 for segment in image['segments']:
  for section in segment['sections']:
   if section['va']<=vtable<section['va']+section['size']:
    ro,rc=struct.unpack_from('<II',obj,section['command_offset']+56)
    for i in range(rc):
     address,word=struct.unpack_from('<II',obj,ro+i*8)
     if word>>27&1 and word>>28==0 and word>>25&3==3:relocations[section['va']+address]=symbols[word&0xffffff][0]
 compiled=[relocations.get(vtable+16+i*8) for i in range(190)]
 assert all(compiled) and vtable+16+190*8 not in relocations and '___cxa_pure_virtual' not in compiled
 allnames=list(dict.fromkeys(compiled+[row['reference_name'] for row in audit['methods']]))
 env=os.environ.copy();env['PATH']='/opt/unixnu-linux/bin:'+env['PATH']
 demangled=subprocess.check_output(['xcrun','c++filt'],input='\n'.join(n[1:] for n in allnames)+'\n',text=True,env=env).splitlines();readable=dict(zip(allnames,demangled));overrides=0
 for row,actual in zip(audit['methods'],compiled):
  expected=row['reference_name'];own=actual.startswith(('__ZN'+mangled,'__ZNK'+mangled))
  if expected=='___cxa_pure_virtual':assert own
  elif actual!=expected:assert own and (row['slot'] in (0,1) or readable[actual].split('::',1)[1]==readable[expected].split('::',1)[1]),row
  overrides+=own
 possible={row['reference_name']:int(row['candidate_target'],16) for row in audit['methods'] if not row['kernel_names']}
 possible.update({'__ZN20IOBlockStorageDeviceC2EPK11OSMetaClass':int(audit['original_protected_constructor'],16),'__ZN20IOBlockStorageDeviceD2Ev':int(audit['original_base_destructor'],16),'__ZN20IOBlockStorageDevice10gMetaClassE':int(audit['original_metaclass'],16),'__ZTV20IOBlockStorageDevice':int(audit['vtable'],16)})
 undefined=[n for n,v,k in symbols if k==1 and 'IOBlockStorageDevice' in n]
 assert all(n in possible for n in undefined) and not any(re.search(r'IOBlockStorageDeviceD[01]Ev$',n) for n in undefined)
 assembly=out/'original-storage-bindings.S';assembly.write_text(''.join(f'.globl {n}\n.set {n}, {possible[n]:#x}\n' for n in sorted(undefined)))
 bound=out/'original-storage-bindings.o';subprocess.run(['xcrun','clang','-target','arm64-apple-ios17.0','-c',str(assembly),'-o',str(bound)],env=env,check=True)
 archive=out/'libRaphaelUfs.a';assert not archive.exists();subprocess.run(['xcrun','ar','rcs',str(archive),str(objpath),str(bound)],env=env,check=True)
 report=dict(passed=True,virtual_methods_checked=190,concrete_overrides=overrides,original_imports_checked=len(undefined),archive_sha256=sha(archive.read_bytes()),original_candidate_sha256=audit['candidate_sha256'],object_sha256=sha(obj),handset_executed=False,linked_in_kernel=False,root_authentication_implemented=True,root_authentication_executed=False)
 (out/'storage-bindings.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
