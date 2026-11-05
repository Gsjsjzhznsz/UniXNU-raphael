#!/usr/bin/env python3
"""Bind the supplied OS abstract watchdog ABI; never define its metaclass."""
import argparse,json,os,struct,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--object',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'kits/XnuPrelink' if (root/'kits/XnuPrelink').exists() else root.parent/'sources/UniXNU/kits/XnuPrelink'))
from native_prelink import macho,backed_offset,exports
raw=a.candidate.read_bytes();plan=json.loads(a.candidate.with_suffix('.json').read_text());image=macho(raw);slide=plan['slide']
assert plan['original_sha256']=='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7'
def read(va,n):
 o=backed_offset(image['segments'],va,n,len(raw));return raw[o:o+n]
def original(va,n):return read(va+slide,n)
def adrp(pc,w):
 v=(((w>>5)&0x7ffff)<<2)|((w>>29)&3)
 if v&(1<<20):v-=1<<21
 return (pc&~4095)+(v<<12)
def branch(pc,w):
 v=w&0x3ffffff
 if v&(1<<25):v-=1<<26
 return pc+4*v
def stub(pc):
 x,y,z=struct.unpack('<3I',read(pc,12));assert x&0x9f00001f==0x90000010 and y&0xffc003ff==0xf9400210 and z==0xd61f0200
 return struct.unpack('<Q',read(adrp(pc,x)+((y>>10)&4095)*8,8))[0]
names={n:va for va,ns in exports(raw,image).items() for n in ns}
init=0xfffffff00663f58c+slide;x,y=struct.unpack('<2I',read(init,8));assert x&0x9f00001f==0x90000000 and y&0xffc003ff==0x91000000
meta=adrp(init,x)+((y>>10)&4095);assert meta==0xfffffff007b2d268+slide
assert original(0xfffffff00663f5a4,4)==struct.pack('<I',0x52801f03)
# Actual parent's metadata comes from this supplied image's import pointer.
x,y=struct.unpack('<2I',original(0xfffffff00663f59c,8));parent=struct.unpack('<Q',read(adrp(0xfffffff00663f59c+slide,x)+((y>>10)&4095)*8,8))[0]
assert parent==names['__ZN9IOService10gMetaClassE']
ctor=0xfffffff00663e400+slide;dtor=0xfffffff00663e420+slide;vp=0xfffffff006f247e8+slide
w=struct.unpack('<8I',read(ctor,32));assert w[0:2]==(0xa9bf7bfd,0x910003fd) and w[-2:]==(0xa8c17bfd,0xd65f03c0)
assert stub(branch(ctor+8,w[2]))==names['__ZN9IOServiceC2EPK11OSMetaClass']
assert adrp(ctor+12,w[3])+((w[4]>>10)&4095)==vp and w[5]==0xf9000008
w=struct.unpack('<I',read(dtor,4))[0];assert w&0xfc000000==0x14000000 and stub(branch(dtor,w))==names['__ZN9IOServiceD2Ev']
methods=struct.unpack('<171Q',read(vp,171*8));assert read(vp+171*8,8)==bytes(8)
assert [i for i,v in enumerate(methods) if v==names['___cxa_pure_virtual']]==[168,169,170]
assert methods[86]==names['__ZN9IOService5startEPS_'] and methods[21]==names['__ZN9IOService4initEP12OSDictionary'] and methods[14]==names['__ZN9IOService4freeEv']
assert methods[87]==0xfffffff00663eb6c+slide and methods[140]==0xfffffff00663ee14+slide
header="""// Generated from the supplied21H461 original abstract class. OS ABI only.
#pragma once
#include <IOKit/IOService.h>
class IOWatchdog : public IOService {
 OSDeclareAbstractStructors(IOWatchdog)
 unsigned char originalPrivate[0xf8-sizeof(IOService)];
public:
 void stop(IOService *) override;
 IOReturn newUserClient(task_t,void *,UInt32,OSDictionary *,IOUserClient **) override;
 virtual void originalHardware168()=0;
 virtual void originalHardware169()=0;
 virtual void originalHardware170()=0;
};
static_assert(sizeof(IOService)==0x88 && sizeof(IOWatchdog)==0xf8);
"""
a.out.mkdir(parents=True,exist_ok=True);(a.out/'OriginalWatchdogABI.h').write_text(header)
report=dict(original_instance_bytes=248,virtual_entries=171,original_metaclass=hex(meta),parent=hex(parent),original_constructor=hex(ctor),original_destructor=hex(dtor),original_private_initialization_called=False,original_apple_hardware_called=False,original_class_redefined=False,handset_executed=False)
if a.object:
 obj=a.object.read_bytes();im=macho(obj);off=next(at for c,at,z in im['commands'] if c==2);sy,count,st,z=struct.unpack_from('<4I',obj,off+8);symbols=[]
 for i in range(count):
  ix,k,sec,desc,va=struct.unpack_from('<IBBHQ',obj,sy+16*i);symbols.append((obj[st+ix:obj.index(b'\0',st+ix)].decode(),va,k))
 vt=next(va for n,va,k in symbols if n=='__ZTV25RaphaelDiagnosticWatchdog');rel={}
 for seg in im['segments']:
  for sec in seg['sections']:
   if sec['va']<=vt<sec['va']+sec['size']:
    ro,rc=struct.unpack_from('<2I',obj,sec['command_offset']+56)
    for i in range(rc):
     at,bits=struct.unpack_from('<2I',obj,ro+8*i)
     if bits>>27&1 and bits>>28==0 and bits>>25&3==3:rel[sec['va']+at]=symbols[bits&0xffffff][0]
 compiled=[rel.get(vt+16+i*8) for i in range(171)];assert all(compiled) and vt+16+171*8 not in rel
 owned=[]
 for i,n in enumerate(compiled):
  if n.startswith(('__ZN25RaphaelDiagnosticWatchdog','__ZNK25RaphaelDiagnosticWatchdog')):owned.append(i)
  else:assert names.get(n)==methods[i],(i,n,hex(methods[i]),names.get(n))
 assert owned==[0,1,7,86,87,140,168,169,170],owned
 bindings={'__ZN10IOWatchdogC2EPK11OSMetaClass':ctor,'__ZN10IOWatchdogD2Ev':dtor,'__ZN10IOWatchdog10gMetaClassE':meta,'__ZTV10IOWatchdog':vp-16}
 imports={n for n,va,k in symbols if k==1 and '10IOWatchdog' in n};assert imports and imports<=set(bindings),imports
 assert not any(k!=1 and '10IOWatchdog' in n for n,va,k in symbols),'Original class must never be defined'
 asm=a.out/'original-watchdog-bindings.S';asm.write_text(''.join('.globl %s\n.set %s, %#x\n'%(n,n,bindings[n]) for n in sorted(imports)))
 subprocess.run(['xcrun','clang','-target','arm64-apple-ios17.0','-c',str(asm),'-o',str(a.out/'original-watchdog-bindings.o')],check=True)
 late=a.out/'RaphaelDiagnosticWatchdog.late.o';subprocess.run(['llvm-objcopy','--remove-section=__DATA,__mod_init_func',str(a.object),str(late)],check=True)
 assert not any(sec['name']=='__mod_init_func' for seg in macho(late.read_bytes())['segments'] for sec in seg['sections'])
 report.update(compiled_owned_slots=owned,original_imports=sorted(imports),automatic_registration_removed=True,passed=True)
(a.out/'watchdog-abi.json').write_text(json.dumps(report,indent=2)+'\n')
