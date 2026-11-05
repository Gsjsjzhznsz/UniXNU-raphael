#!/usr/bin/env python3
"""Bind private, actual-volume policies to the pinned generic block verifier."""
import json
import os
from pathlib import Path
import struct
import subprocess

root=Path(__file__).resolve().parents[1]
policy_path=Path(os.environ['RAPHAEL_ROOT_POLICY'])
policy=json.loads(policy_path.read_text());assert policy['passed']
base=policy_path.parent
out=root/'build/raphael-root-policy';out.mkdir(parents=True,exist_ok=True)
policies={x['role']:x for x in policy['policies']};assert set(policies)=={'OS','SystemOS'}
anchor=(base/'OS/trusted-key.bin').read_bytes()
assert anchor==(base/'SystemOS/trusted-key.bin').read_bytes() and len(anchor)==395
# Handset manifests are immutable bytes, not late-initialized globals.
# Keep them in an existing RNX segment so bounded early-C recovery continues
# to preserve every complete mutable segment without copying 73 MiB of hashes.
manifest_section='__TEXT,__rph_verified' if os.environ.get('RAPHAEL_HANDSET_UFS')=='1' else '__DATA_CONST,__const'
assembly=['.section '+manifest_section,'.balign 8']
records=[]
for role,symbol in [('OS','_verified_root_manifest'),('SystemOS','_verified_root_systemos_manifest')]:
    path=base/role/'manifest.bin';size=path.stat().st_size
    assert size==544+policies[role]['block_count']*32
    assembly += ['.balign 8','.globl '+symbol,symbol+':','.incbin '+json.dumps(str(path))]
    records.append((symbol,size))
assembly += ['.section __DATA_CONST,__const','.balign 8','.globl _verified_root_manifest_bytes','_verified_root_manifest_bytes:',f'.quad {records[0][1]}',
             '.globl _verified_root_key','_verified_root_key:', '.incbin '+json.dumps(str(base/'OS/trusted-key.bin')),
             '.balign 8','.globl _verified_root_policies','_verified_root_policies:']
assembly += [f'.quad {symbol}, {size}' for symbol,size in records]
assembly += ['.globl _verified_root_policy_count','_verified_root_policy_count:','.quad 2']
# The upstream optional crypto self-check uses exact first/middle/last source blocks.
manifest=policies['OS'];count=manifest['block_count'];indices=[0,1,count//2,count-1]
source_report=json.loads((base/'disks.json').read_text())
os_disk=next(d for d in source_report['disks'] if d['role']=='OS')
workspace=Path(os.environ['RAPHAEL_WORKSPACE'])
lengths=[];samples=out/'samples.bin'
with (workspace/os_disk['path']).open('rb') as image,samples.open('wb') as stream:
    for index in indices:
        image.seek(index*4096);block=image.read(min(4096,manifest['image_bytes']-index*4096));lengths.append(len(block));stream.write(block)
        if len(block)<4096:stream.write(bytes(4096-len(block)))
for symbol,values in [('_verified_root_sample_indices',indices),('_verified_root_sample_lengths',lengths)]:
    assembly += ['.balign 8','.globl '+symbol,symbol+':','.quad '+','.join(map(str,values))]
assembly += ['.globl _verified_root_samples','_verified_root_samples:','.incbin '+json.dumps(str(samples))]
inputs=out/'inputs.S';inputs.write_text('\n'.join(assembly)+'\n')
recipe=json.loads((root/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/bsd_init.o.json').read_text().strip().rstrip(','))
# Mach-O kernel links cannot leave this optional weak import unresolved.
# No UFS transport exists in this emulator configuration; -1 means 'not a UFS device'.
assert os.environ.get('XNU_NATIVE_UFS','0')=='0'
absent=out/'absent_ufs.c'
absent.write_text('#include <stdint.h>\nint native_ufs_block_authenticates(void *device,const char *uuid,uint8_t *digest) { (void)device; (void)uuid; (void)digest; return -1; }\n')
objects=[]
for source in ([] if os.environ.get('RAPHAEL_HANDSET_UFS')=='1' else [absent])+[root/'kits/VerifiedRoot/src/verified_root.c',root/'kits/VerifiedRoot/adapters/xnu_crypto.c',root/'scripts/qemu-entry/verified-root-probe.c']:
    obj=out/(source.stem+'.o');command=[];arguments=recipe['arguments'];index=0
    while index<len(arguments):
        value=arguments[index]
        if value==recipe['file']:command.append(str(source))
        elif value=='-o':command += ['-o',str(obj)];index+=1
        elif value in ('-MF','-MJ'):index+=1
        elif value=='-Xclang' and arguments[index+1].startswith('-W'):index+=1
        elif value not in ('-MD','-MP') and not value.startswith('-W'):command.append(value)
        index+=1
    command += ['-I'+str(root/'kits/VerifiedRoot/include'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-missing-include-dirs']
    result=subprocess.run(command,cwd=recipe['directory'],capture_output=True,text=True)
    (out/(source.stem+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stderr[-4000:])
    assert struct.unpack_from('<4I',obj.read_bytes())==(0xfeedfacf,0x100000c,0,1)
    objects.append(obj)
input_obj=out/'inputs.o'
subprocess.run(['xcrun','clang','-target','arm64-apple-ios17.0','-Wno-incompatible-sysroot','-c',inputs,'-o',input_obj],check=True)
archive=out/'libVerifiedRootProbe.a';archive.unlink(missing_ok=True)
subprocess.run(['xcrun','ar','rcs',archive,*objects,input_obj],check=True)
subprocess.run(['python3',root/'scripts/build-arm-driver.py','VirtioMmioBlock','--verified-root','--verified-root-bundle'],check=True)
subprocess.run(['python3',root/'scripts/build-virtio-mmio-bindings.py','--directory',root/'build/virtio-mmio-block-verified-bundle'],check=True)
(out/'provenance.json').write_text(json.dumps(dict(policy_source=str(policy_path),two_actual_volume_policies=True,
    owner_root_alternative_to_apple_seal=True,apple_auth_checks_retained=True,
    immutable_manifest_section=manifest_section,manifest_bytes=sum(size for _,size in records),
    runtime_block_verification=True,handset_qualified=False),indent=2)+'\n')
