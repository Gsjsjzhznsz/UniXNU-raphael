#!/usr/bin/env python3
"""Generate exact original-family imports and build independent inherited GOP display."""
import hashlib,json,os,struct,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'kits/XnuPrelink'))
from native_prelink import macho,backed_offset,exports
out=root/'build/native-legacy-display';out.mkdir(parents=True,exist_ok=True)
p=Path(os.environ['RAPHAEL_DISPLAY_CANDIDATE']);raw=p.read_bytes();plan=json.loads(p.with_suffix('.json').read_text());image=macho(raw)
assert plan['original_sha256']=='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7'
def read(a,n):
 at=backed_offset(image['segments'],a,n,len(raw));return raw[at:at+n]
family='com.apple.iokit.IOMobileGraphicsFamily'
e=next(e for e in plan['extents'] if e['module']==family and e['segment']=='__TEXT_EXEC')
assert hashlib.sha256(read(e['va'],e['size'])).hexdigest()==plan['original_executable_sha256'][family]=='2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b'
# OS software virtual addresses, never handset resources. This constructor's
# ADRP/ADD determines the vptr; original metadata constructor supplies 0x18a0.
a,b,c=struct.unpack('<3I',read(0xfffffff0057865d8,12));assert (a,b,c)==(0xd0003d88,0x91158108,0x91004108)
vptr=0xfffffff005f38570;methods=struct.unpack('<358Q',read(vptr,358*8))
names={n:a for a,ns in exports(raw,image).items() for n in ns}
pure=[i for i,a in enumerate(methods) if a==names['___cxa_pure_virtual']]
assert pure==[211,213,245,246,306,307,337,338,345] and read(vptr+358*8,24)==bytes(24)
assert read(0xfffffff0057866b4,4)==bytes.fromhex('03148352') # mov w3,#0x18a0
assert read(0xfffffff00579fcbc,4)==bytes.fromhex('08b156b9') # ldr w8,[x8,#0x16b0]
# Height immediately follows width in the original getter; preserve both fields.
assert bytes.fromhex('08b556b9') in read(methods[249],160)
assert read(0xfffffff005787efc,4)==bytes.fromhex('088144f9') # original start dispatches slot 288
assert methods[288]==0xfffffff00579278c and read(methods[288]+8,8)==bytes.fromhex('0800805200010012')
assert methods[290]==0xfffffff005794030 and methods[295]==0xfffffff005795b88
assert methods[296]==0xfffffff005795bb4 and methods[354]==0xfffffff0057970cc
# Original logical display-state ABI; software offsets, never MMIO.
assert read(0xfffffff005797130,4)==bytes.fromhex('080540b9') # requested input +4
assert read(0xfffffff005797154,4)==bytes.fromhex('28cd16b9') # requested field +0x16cc
assert read(0xfffffff005797184,4)==bytes.fromhex('080d40b9') # powered input +12
assert read(0xfffffff0057971a8,4)==bytes.fromhex('28d116b9') # powered field +0x16d0
assert read(0xfffffff005790570,4)==bytes.fromhex('08cd56b9') # submit reads requested
assert read(0xfffffff005790584,4)==bytes.fromhex('28008052') # requested zero forces skip
# Fixed OS queue ABI: original method 346 reads current/head and removes the
# pending request using the standard TAILQ links. These are software offsets.
assert bytes.fromhex('08b14af9') in read(methods[346],0x500) # current +0x1560
assert bytes.fromhex('08b54af9') in read(methods[346],0x500) # pending +0x1568
# Original IOSurface accessor functions in this same frozen system version.
# Each is a plain ldr from the named software field followed by ret. Import
# the original getters rather than shipping copied surface memory layouts.
surface_getters={
 'descriptor':(0xfffffff004b9eac8,48,8),
 'width':(0xfffffff004b9ebbc,88,8),
 'height':(0xfffffff004b9ebc4,96,8),
 'stride':(0xfffffff004b9ebd4,104,8),
 'format':(0xfffffff004b9ebac,128,4),
 'allocation':(0xfffffff004b9ebfc,144,8),
 'planes':(0xfffffff004b9ebf4,152,4),
}
for label,(address,offset,size) in surface_getters.items():
 op=(0xf9400000 if size==8 else 0xb9400000)|((offset//size)<<10)
 assert read(address,8)==struct.pack('<II',op,0xd65f03c0),(label,hex(address))

header="""// Generated OS ABI, private storage opaque; not a hardware memory map.
#pragma once
#include <IOKit/IOService.h>
#include <IOKit/IOUserClient.h>
class IOMobileFramebufferLegacy : public IOService {
 OSDeclareAbstractStructors(IOMobileFramebufferLegacy)
 unsigned char originalPrivate[0x18a0-sizeof(IOService)];
public:
 void free() override;
 bool init(OSDictionary *properties=nullptr) override;
 IOReturn setProperties(OSObject *) override;
 void systemWillShutdown(IOOptionBits) override;
 IOService *probe(IOService *,SInt32 *) override;
 bool start(IOService *) override;
 void stop(IOService *) override;
 IOWorkLoop *getWorkLoop() const override;
 IOReturn newUserClient(task_t,void *,UInt32,IOUserClient **) override;
 IOReturn setPowerState(unsigned long,IOService *) override;
 void installBootDimensions(uint32_t w,uint32_t h) {memcpy((char *)this+0x16b0,&w,4);memcpy((char *)this+0x16b4,&h,4);}
"""
known={184:'IOReturn supportedFrameInfo(uint32_t,uint32_t *,char *,uint32_t *)',188:'IOReturn getDotPitch(uint32_t *)',213:'bool isMainDisplay()',249:'void getDisplayDimensions(uint32_t *,uint32_t *)',288:'bool startHardware()',290:'void kickSwapQueue()',295:'void completeCurrentSwap()',296:'bool validateSwap(const void *)',301:'bool getRefreshAttributes(uint64_t *,bool)',354:'int setDisplayState(void *,bool)',337:'IOReturn collectCompletionReports(uint32_t,void *,uint32_t *,uint32_t)'}
for i in range(168,358):header+=' virtual '+known.get(i,'void opaque%d()'%i)+('=0' if i in pure else '')+';\n'
header+='};\nstatic_assert(sizeof(IOService)==136 && sizeof(IOMobileFramebufferLegacy)==0x18a0);\n'
(out/'OriginalLegacyFramebufferABI.h').write_text(header)
(out/'NativeLegacyRequest.h').write_bytes((Path(os.environ['RAPHAEL_WORKSPACE'])/'sources/UniXNU/drivers/GopFramebuffer/NativeLegacyRequest.h').read_bytes())
source_input=Path(os.environ['RAPHAEL_DISPLAY_SOURCE']) if os.environ.get('RAPHAEL_DISPLAY_SOURCE') else root/'kits/raphael/drivers/RaphaelDesktopDisplay.cpp'
source_bytes=source_input.read_bytes()
if os.environ.get('RAPHAEL_DISPLAY_SOURCE'):
 assert hashlib.sha256(source_bytes).hexdigest()==os.environ['RAPHAEL_DISPLAY_SOURCE_SHA256']
source=out/'RaphaelDesktopDisplay.cpp';source.write_bytes(source_bytes)
recipe=json.loads((root/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
obj=out/'RaphaelDesktopDisplay.o';args=recipe['arguments'];cmd=[];i=0
while i<len(args):
 v=args[i]
 if v==recipe['file']:cmd.append(str(source))
 elif v=='-o':cmd+=['-o',str(obj)];i+=1
 elif v in ('-MF','-MJ'):i+=1
 elif v=='-Xclang' and args[i+1].startswith('-W'):i+=1
 elif v not in ('-MD','-MP') and not v.startswith('-W'):cmd.append(v)
 i+=1
# Pinned XNU allocation macros omit the trailing kt_zshared field; retain -Werror
# while allowing that zero-initialized SDK macro field, as in the UFS recipe.
cmd+=['-I'+str(root/'drivers/GopFramebuffer'),'-I'+str(out),'-I'+str(root/'.cache/xnu-work/osfmk'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-missing-designated-field-initializers','-Wno-c99-designator','-Wno-reorder-init-list','-Wno-deprecated-enum-enum-conversion','-Wno-unnecessary-virtual-specifier']
(out/'compile-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
offline_aks=os.environ.get('RAPHAEL_OFFLINE_KEYSTORE')=='1'
handset_display=os.environ.get('RAPHAEL_HANDSET_DISPLAY')=='1'
assert not handset_display or os.environ.get('RAPHAEL_HANDSET_UFS')=='1'
cmd+=['-DRAPHAEL_OFFLINE_KEYSTORE='+str(int(offline_aks)),'-DRAPHAEL_HANDSET_DISPLAY='+str(int(handset_display))]
if os.environ.get('RAPHAEL_UFS_CONSOLE_LOG_REPORT'):
 cmd+=['-DRAPHAEL_UFS_CONSOLE_LOG=1']
 (out/'RaphaelFrameProbe.h').write_bytes((root/'kits/raphael/drivers/RaphaelFrameProbe.h').read_bytes())
r=subprocess.run(cmd,cwd=recipe['directory'],capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr)
if r.returncode:raise SystemExit(r.stderr[-5000:])
buf=obj.read_bytes();im=macho(buf);st=next(p for c,p,_ in im['commands'] if c==2);sy,count,strings,_=struct.unpack_from('<4I',buf,st+8);symbols=[]
for i in range(count):
 ix,kind,section,_,va=struct.unpack_from('<IBBHQ',buf,sy+i*16)
 symbols.append((buf[strings+ix:buf.index(b'\0',strings+ix)].decode(),va,kind))
vt=next(va for n,va,k in symbols if n=='__ZTV21RaphaelDesktopDisplay');relocs={}
for seg in im['segments']:
 for sec in seg['sections']:
  if sec['va']<=vt<sec['va']+sec['size']:
   ro,rc=struct.unpack_from('<2I',buf,sec['command_offset']+56)
   for i in range(rc):
    offset,bits=struct.unpack_from('<2I',buf,ro+i*8)
    if bits>>27&1 and bits>>28==0 and bits>>25&3==3:relocs[sec['va']+offset]=symbols[bits&0xffffff][0]
compiled=[relocs.get(vt+16+i*8) for i in range(358)]
assert all(compiled) and vt+16+358*8 not in relocs and '___cxa_pure_virtual' not in compiled
bindings={'__ZN25IOMobileFramebufferLegacyC2EPK11OSMetaClass':0xfffffff0057865cc,'__ZN25IOMobileFramebufferLegacyD2Ev':0xfffffff005786618,'__ZN25IOMobileFramebufferLegacy10gMetaClassE':0xfffffff006b35940,'__ZTV25IOMobileFramebufferLegacy':vptr-16}
bindings.update({'_raphael_surface_'+label:address for label,(address,offset,size) in surface_getters.items()})
bindings['_raphael_legacy_mark_swap']=0xfffffff005789d78
# Pinned original OS software refresh publisher dispatches virtual slot301.
assert methods[301]==0xfffffff00579ea5c
assert read(0xfffffff00579ebb8,12)==bytes.fromhex('ff0302d1fd7b07a9fdc30191')
assert bytes.fromhex('08b544f9') in read(0xfffffff00579ebb8,0x130)
bindings['_raphael_legacy_set_refresh']=0xfffffff00579ebb8
owned=[]
for i,n in enumerate(compiled):
 if n.startswith(('__ZN21RaphaelDesktopDisplay','__ZNK21RaphaelDesktopDisplay')):owned.append(i)
 elif '25IOMobileFramebufferLegacy' in n:bindings[n]=methods[i]
 else:assert names.get(n)==methods[i],(i,n,hex(methods[i]),names.get(n))
imports={n for n,va,k in symbols if k==1 and '25IOMobileFramebufferLegacy' in n}
assert imports<=set(bindings),imports-set(bindings)
asm=out/'original-bindings.S';asm.write_text(''.join('.globl %s\n.set %s, %#x\n'%(n,n,a) for n,a in sorted(bindings.items()) if n in imports or n.startswith(('_raphael_surface_','_raphael_legacy_'))))
subprocess.run(['xcrun','clang','-target','arm64-apple-ios17.0','-Wno-incompatible-sysroot','-c',asm,'-o',out/'bindings.o'],check=True)
late=out/'RaphaelDesktopDisplay.late.o'
subprocess.run(['llvm-objcopy','--remove-section=__DATA,__mod_init_func',obj,late],check=True)
archive=out/'libNativeLegacyDisplay.late.a';archive.unlink(missing_ok=True)
subprocess.run(['xcrun','ar','rcs',archive,late,out/'bindings.o'],check=True)
if offline_aks:
 # Generic pinned OS ABI component; no other board callbacks or hardware data.
 default_keystore=Path(os.environ['RAPHAEL_WORKSPACE'])/'sources/UniXNU/drivers/AppleKeyStoreState'
 override_keystore=os.environ.get('RAPHAEL_KEYSTORE_SOURCE')
 upstream=Path(override_keystore).resolve() if override_keystore else default_keystore
 revision=subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()
 expected='8c70daf814aafdf4a3d35e40dde0322655fd0a83' if override_keystore else '42ff83e08b2265fe741d4adaf084bebe003452ba'
 assert revision==expected
 software_wrapping=bool(override_keystore)
 # Freeze the selected generic implementation beside its compile record.
 keystore_source=out/'NativeKeyStoreEvents.cpp';keystore_source.write_bytes((upstream/'NativeKeyStoreEvents.cpp').read_bytes())
 objects=[]
 for name,original in [('NativeKeyStoreEvents',keystore_source),('RaphaelOfflineKeyStore',root/'kits/raphael/drivers/RaphaelOfflineKeyStore.cpp')]:
  target=out/(name+'.o');commands=[str(target) if v==str(obj) else str(original) if v==str(source) else v for v in cmd]
  result=subprocess.run(commands,cwd=recipe['directory'],capture_output=True,text=True)
  (out/(name+'-compile.log')).write_text(result.stdout+result.stderr)
  if result.returncode:raise SystemExit(result.stderr[-5000:])
  objects.append(target)
 subprocess.run(['xcrun','ar','rcs',archive,*objects],check=True)
 (out/'offline-keystore.json').write_text(json.dumps(dict(component='AppleKeyStoreState',revision=revision,source=str(upstream),ephemeral_unprotected_data_only=True,key_operations_available=software_wrapping,software_wrapping=software_wrapping,hardware_protection=False,handset_qualified=False,boot_argument='raphael-offline-keystore=1'),indent=2)+'\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'build-report.json').write_text(json.dumps(dict(archive_sha256=sha(archive),source_sha256={str(p.relative_to(root)):sha(p) for p in [source,out/'OriginalLegacyFramebufferABI.h',out/'NativeLegacyRequest.h']},original_family_text_sha256=plan['original_executable_sha256'][family],virtual_entries=358,owned_entries=owned,bindings={n:hex(a) for n,a in bindings.items()},surface_getters={n:dict(address=hex(a),offset=o,size=z) for n,(a,o,z) in surface_getters.items()},runtime_qualified=False,handset_qualified=False,handset_candidate=handset_display,inherited_framebuffer_only=True),indent=2)+'\n')
print('RaphaelDesktopDisplay: 358-slot original ABI bound; real ARM64 archive built; runtime pending')
