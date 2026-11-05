#!/usr/bin/env python3
"""Build explicit ephemeral Data initialization; Apple bytes stay in ignored inputs."""
import json,os,struct,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
report_path=Path(os.environ['RAPHAEL_SCRATCH_DATA']).resolve()
report=json.loads(report_path.read_text());assert report['passed'] and not report['handset_executed']
assert os.environ['XNU_OWNER_DATA_MOUNT']=='1' and os.environ['XNU_OWNER_UNION_SYSTEMOS']=='1'
assert os.environ.get('XNU_NATIVE_RAM_BLOCK')=='1'
subprocess.run(['python3',root/'scripts/build-virtio-mmio-bindings.py','--component','RamBlock','--directory',root/'build/ram-block'],check=True)
# The generic combination check still uses the component id as its object name.
# Alias the actual audited object; do not synthesize a second ABI definition.
for folder,alias,actual in [('ram-block','RamBlock.o','NativeRamBlock.o'),('virtio-mmio-block-verified-bundle','VirtioMmioBlock.o','NativeVirtioBlock.o')]:
 path=root/'build'/folder/alias
 if not path.exists():path.symlink_to(actual)
 assert path.resolve()==(root/'build'/folder/actual).resolve()
seed=json.loads((report_path.parent/'seed.json').read_text());payload=report_path.parent/'seed.bin'
assert payload.stat().st_size==report['seed_bytes']
out=root/'build/raphael-data-seed';out.mkdir(parents=True,exist_ok=True)
header=['struct seed_entry { const char *path, *target; unsigned kind, uid, gid, mode; uint64_t offset, length; };','static const struct seed_entry seed_entries[] = {']
for entry in seed['entries']:
 assert entry['path']=='/private/var' or entry['path'].startswith('/private/var/')
 kind={'directory':1,'file':2,'symlink':3}[entry['kind']]
 offset=entry.get('offset',0);length=entry.get('bytes',0);assert 0<=offset<=offset+length<=payload.stat().st_size
 header.append('{'+','.join([json.dumps(entry['path']),json.dumps(entry.get('target','')),str(kind),str(entry['uid']),str(entry['gid']),str(entry['mode']),str(offset),str(length)])+'},')
header.append('};');(out/'seed_entries.h').write_text('\n'.join(header)+'\n')
assembly=out/'payload.S';assembly.write_text('.section __DATA_CONST,__const\n.balign 8\n.globl _raphael_default_var_payload\n_raphael_default_var_payload:\n.incbin '+json.dumps(str(payload))+'\n')
recipe=json.loads((root/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/bsd_init.o.json').read_text().strip().rstrip(','))
source=root/'scripts/desktop-data-seed.c';obj=out/'seed.o';command=[];arguments=recipe['arguments'];index=0
while index<len(arguments):
 value=arguments[index]
 if value==recipe['file']:command.append(str(source))
 elif value=='-o':command+=['-o',str(obj)];index+=1
 elif value in ('-MF','-MJ'):index+=1
 elif value=='-Xclang' and arguments[index+1].startswith('-W'):index+=1
 elif value not in ('-MD','-MP') and not value.startswith('-W'):command.append(value)
 index+=1
command+=['-I'+str(out),'-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-missing-include-dirs']
r=subprocess.run(command,cwd=recipe['directory'],capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr)
if r.returncode:raise SystemExit(r.stderr[-5000:])
assert struct.unpack_from('<4I',obj.read_bytes())==(0xfeedfacf,0x100000c,0,1)
asm=out/'payload.o';subprocess.run(['xcrun','clang','-target','arm64-apple-ios17.0','-Wno-incompatible-sysroot','-c',assembly,'-o',asm],check=True)
import shutil
archive=out/'libVerifiedRootWithData.a';shutil.copyfile(root/'build/raphael-root-policy/libVerifiedRootProbe.a',archive)
subprocess.run(['xcrun','ar','rcs',archive,obj,asm],check=True)
(out/'provenance.json').write_text(json.dumps(dict(scratch_source=str(report_path),source_volume=seed['source_volume'],entry_counts=report['entry_counts'],seed_bytes=report['seed_bytes'],metadata_source=seed['metadata_source'],emulator_only=os.environ.get('RAPHAEL_HANDSET_UFS')!='1',handset_candidate=os.environ.get('RAPHAEL_HANDSET_UFS')=='1',persistent_store_enabled=False,handset_qualified=False),indent=2)+'\n')
