#!/usr/bin/env python3
"""Independent raw evidence audit for original loader pre-exit handset loading."""
import argparse
import datetime as dt
import json
import lzma
import re
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from entry_probe import ROOT, sha
from native_load import make_policy, decode as decode_load
from inspect_device import read_fdt, registers
from inspect_diagnostic_fd import inspect_fd, PAYLOAD_GUID, PAYLOAD_PART1_GUID, NATIVE_LOAD_GUID
from validate_native_staging_evidence import bind, file_read
from validate_android_return_evidence import load, chosen
from payload_probe import decode as decode_payload
from private_android_image import read_boot, repack
from kernel_window import check_log

def parse_adt(raw):
    at=0
    def visit(depth):
        nonlocal at
        assert depth<=64 and at+8<=len(raw)
        props,children=struct.unpack_from('<2I',raw,at);at+=8;values={}
        for _ in range(props):
            assert at+36<=len(raw)
            name,n=struct.unpack_from('<32sI',raw,at);at+=36
            assert b'\0' in name and at+n<=len(raw)
            key=name.split(b'\0')[0].decode();assert key not in values
            values[key]=raw[at:at+n];at=(at+n+3)&~3
        assert 'name' in values and values['name'].endswith(b'\0')
        result=dict(properties=values,children={})
        for _ in range(children):
            child=visit(depth+1);name=child['properties']['name'].rstrip(b'\0').decode()
            assert name not in result['children'];result['children'][name]=child
        return result
    result=visit(0);assert at==len(raw);return result

def audit_adt(adt, source, window, frequency, affinity):
    t=parse_adt(adt);p=t['properties'];children=t['children'];f=read_fdt(source)
    assert p['model']==f.properties['model'] and p['compatible']==f.properties['compatible']
    assert set(children)=={'chosen','cpus','arm-io','defaults','options'}
    cpus=children['cpus']['children'];assert list(cpus)==['cpu0'];cpu=cpus['cpu0']['properties']
    fcpus=next(n for n in f.children if n.name=='cpus')
    fc=next(n for n in fcpus.children if n.properties.get('device_type')==b'cpu\0' and int.from_bytes(n.properties['reg'],'big')==affinity)
    assert cpu['compatible']==fc.properties['compatible'] and cpu['device_type']==b'cpu\0' and cpu['state']==b'running\0'
    expected={'reg':affinity,'timebase-frequency':frequency,'unixnu,boot-cpu':1,'unixnu,physical-timer':1}
    timer=next(n for n in f.walk() if b'arm,armv8-timer' in n.properties.get('compatible',b'').split(b'\0'))
    ints=timer.cells('interrupts');assert ints[3]==1
    expected.update({'unixnu,timer-intid':16+ints[4],'unixnu,timer-flags':ints[5]&15})
    for key,value in expected.items():assert cpu[key]==struct.pack('<I',value),key
    gic=next(n for n in f.walk() if b'arm,gic-v3' in n.properties.get('compatible',b'').split(b'\0'))
    regs=registers(gic);io=children['arm-io'];ranges=struct.unpack('<3Q',io['properties']['ranges'])
    assert ranges==(0,min(a for a,n in regs),max(a+n for a,n in regs)-min(a for a,n in regs))
    assert list(io['children'])==['intc'];gp=io['children']['intc']['properties']
    assert gp['compatible']==b'arm,gic-v3\0'
    assert gp['reg']==struct.pack('<4Q',*[v for a,n in regs for v in [a-ranges[1],n]])
    banks=[reg for n in f.children if n.properties.get('device_type')==b'memory\0' for reg in registers(n)]
    selected=[(a,n) for a,n in banks if a<=window['base'] and window['base']+window['bytes']<=a+n];assert len(selected)==1
    c=children['chosen']['properties']
    assert (int.from_bytes(c['dram-base'],'little'),int.from_bytes(c['dram-size'],'little'))==selected[0]
    assert len(c['random-seed'])==64 and not children['chosen']['children']['memory-map']['children']
    from unixnu.devicetree import empty_nvram_proxy
    for key,value in empty_nvram_proxy():assert c[key]==value
    return dict(source_fdt_sha256=sha(source),adt_sha256=sha(adt),selected_physical_bank=selected[0],
        frequency=frequency,affinity=affinity,timer_intid=16+ints[4],gic_registers=regs)

def inspect_build(base, br, revision, bound):
    assert br['native_load_test'] and br['sparse_arena'] and br['android_return'] and not br['native_handoff']
    binding=dict(br);binding['upstream_inputs']=br['upstream_inputs']+br['darwin_inputs'];bind(base,binding,revision,bound)
    image=(base/'diagnostic.Image').read_bytes();l=br['layout'];assert len(image)==l['StackBase']+l['StackSize']-l['ImageBase']
    assert struct.unpack_from('<Q',image,16)[0]==len(image)
    fd=image[l['FdBase']-l['ImageBase']:l['FdBase']-l['ImageBase']+l['FdSize']];assert sha(fd)==br['firmware_sha256']
    s=inspect_fd(fd,l['FdBase']);parts=[]
    for guid in [PAYLOAD_GUID,PAYLOAD_PART1_GUID,NATIVE_LOAD_GUID]:
        file=next(f for f in s['files'] if f['guid']==guid);[section]=file['sections']
        data=fd[section['offset']+4:section['offset']+section['bytes']]
        if guid!=NATIVE_LOAD_GUID:parts.append(data)
        else:manifest=data
    fat=(base/'diagnostic-payload.img').read_bytes();assert b''.join(parts)==fat and sha(fat)==br['payload']['image_sha256']
    kernel=subprocess.check_output(['mtype','-i',str(base/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho'])
    adt=subprocess.check_output(['mtype','-i',str(base/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho.adt'])
    assert sha(kernel)==br['payload']['kernel_sha256'] and sha(adt)==br['payload']['adt_sha256']
    c=br['native_load_contract'];policy,expected=make_policy(kernel,adt,br['kernel_window'],c['frequency'],c['affinity'],exit_complete=br.get('native_exit_complete',False))
    assert policy==manifest==(base/'native-load-policy.bin').read_bytes() and c==expected
    assert c['kernel_sha256']=='96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722'
    return image,kernel,adt

def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--negative-report',type=Path,required=True);p.add_argument('--exit-complete',action='store_true');a=p.parse_args()
    revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.revision],text=True).strip()
    parent=ROOT/'artifacts/native-load-verification';parent.mkdir(exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
    run=a.run.resolve();rr=load(run/'report.json');assert rr['passed'] and rr['stage']==(8 if a.exit_complete else 7) and rr['native_load_verified'] and rr['unassisted_android_return']
    assert not rr.get('auto_recovered_from_bootloader') and not (run/'bootloader-recovery.json').exists()
    build=ROOT/rr['build'];br=load(build/'report.json');assert sha((build/'report.json').read_bytes())==rr['build_report_sha256'];bound=set()
    image,kernel,adt=inspect_build(build,br,revision,bound)
    original=read_boot(ROOT/'evidence/private/device/20261027T120325Z');assert sha(original['raw'])==br['source_sha256']
    rd=(build/'expanded-ramdisk.bin').read_bytes();cap=br['capsule'];policy=cap['policy_words']
    restored=lzma.decompress(rd[(cap['ramdisk_bytes']+7)&~7:],format=lzma.FORMAT_ALONE)
    assert restored==original['image'] and rd[:cap['ramdisk_bytes']]==original['ramdisk']
    assert sha(restored)==cap['kernel_sha256'] and zlib.crc32(restored)==policy[9]
    packed=(build/'boot-android-return.img').read_bytes();assert repack(original,image,ramdisk=rd)==packed
    assert sha(packed)==br['image_sha256']==rr['image_sha256'] and sha(rd)==cap['expanded_ramdisk_sha256']
    f=chosen((run/'after.dtb').read_bytes());d=struct.unpack('>48Q',f.properties['raphael,sec-dxe']);w=struct.unpack('>10Q',f.properties['raphael,android-return'])
    assert f.strings('raphael,sec-dxe-id')==[br['identifier']] and list(d)==rr['sec_words'] and d[27:29]==(rr['stage'],0)
    assert list(w)==rr['return_words'] and w[0:2]==(1,3) and w[2]==w[7]==policy[8] and w[3]==w[4]==policy[9] and w[8]==len(restored) and w[9]==1
    assert w[5:7]==(br['kernel_window']['base']+br['kernel_window']['bytes']-0x40000,br['kernel_window']['base']+br['kernel_window']['bytes'])
    assert int.from_bytes(f.properties['linux,initrd-end'],'big')-int.from_bytes(f.properties['linux,initrd-start'],'big')==len(original['ramdisk'])
    observation=decode_load(f.properties['raphael,native-load'],br['native_load_contract']);assert observation==rr['native_load']
    decode_payload(f.properties['raphael,payload-diagnostic'],br['layout'],6,native_staging=True)
    log=f.properties['raphael,sec-dxe-log'];assert log==(run/'sec-dxe.log').read_bytes()
    assert file_read(log,br['layout'],kernel)==rr['staging_file_read'] and check_log(log,br['kernel_window'])['passed']
    assert b'DARWINBOOT: inputs validated; exiting boot services' in log and b'DARWINBOOT: command line: -v keepsyms=1 cpus=1' in log
    darwin=struct.unpack('>18Q',f.properties['raphael,darwin-diagnostic']);assert darwin[3:6]==(1,1,0x20000) and darwin[13]==int(a.exit_complete)
    physical=None
    if a.exit_complete:
        from native_exit import decode_physical
        physical=decode_physical((run/'after.dtb').read_bytes(),build)
        assert physical==rr['physical_timer_evidence'] and rr['physical_timer_verified']
        assert observation['exit_boot_services_completed']
    provenance=audit_adt(adt,(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes(),br['kernel_window'],19200000,0)
    qp=ROOT/br['qemu_evidence'];q=load(qp);assert sha(qp.read_bytes())==br['qemu_evidence_sha256'] and q['passed'] and q['stage']==rr['stage']
    _,qkernel,qadt=inspect_build(qp.parent,q,revision,bound);assert qkernel==kernel
    qlog=(qp.parent/'serial.log').read_bytes();match=re.search(rb'NATIVE_LOAD_WIRE ([0-9a-f]+)',qlog);assert match
    assert decode_load(bytes.fromhex(match[1].decode()),q['native_load_contract'])==q['native_load_observation']
    assert b'ANDROID_RETURN_QEMU_OK' in qlog and b'FAIL ' not in qlog
    for name in ['before.dtb','cleanup.dtb']:
        assert not any(k.startswith('raphael,') for k in chosen((run/name).read_bytes()).properties)
    commands=load(run/'commands.json');boots=[x for x in commands if 'fastboot.exe' in x['command'][0] and 'boot' in x['command']]
    assert len(boots)==1 and boots[0]['returncode']==0 and not any(set(x['command']) & {'flash','erase','format'} for x in commands)
    for x in commands:
        if x.get('file'):assert sha((run/x['file']).read_bytes())==x['sha256']
    hashes=[x for x in commands if any('sha256sum /dev/block/bootdevice/by-name/boot' in v for v in x['command'])]
    assert len(hashes)>=3 and all(x['returncode']==0 and x['stdout'].split()[0]==br['source_sha256'] for x in hashes)
    assert (run/'before-boot-id.txt').read_bytes()!=(run/'after-boot-id.txt').read_bytes()
    assert all(rr[k] for k in ['cleanup_android_completed','cleanup_root_verified','cleanup_boot_unchanged','cleanup_transient_properties_absent'])
    np=a.negative_report.resolve();negative=load(np);assert negative['passed'] and negative['positive_report']==str(qp.relative_to(ROOT))
    assert negative['positive_report_sha256']==sha(qp.read_bytes()) and negative['loaded_memory']['file_segments_ok']==observation['segment_count']-1
    assert b'Breakpoint 1,' in (np.parent/'gdb.log').read_bytes() and b'ANDROID_RETURN_QEMU_FAILED' in (np.parent/'serial.log').read_bytes()
    report=dict(passed=True,implementation_revision=revision,private_run=str(run.relative_to(ROOT)),run_report_sha256=sha((run/'report.json').read_bytes()),
        private_build=str(build.relative_to(ROOT)),build_report_sha256=sha((build/'report.json').read_bytes()),image_sha256=br['image_sha256'],firmware_sha256=br['firmware_sha256'],
        kernel_sha256=sha(kernel),adt=provenance,loaded_memory=observation,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),
        negative_report=str(np.relative_to(ROOT)),negative_report_sha256=sha(np.read_bytes()),git_bound_input_count=len(bound),source_paths=sorted(bound),
        physical_timer=physical,xnu_handset_executed=False,exit_boot_services_completed=a.exit_complete,verifier_sha256=sha(Path(__file__).read_bytes()),
        limits=['No XNU branch; exact service-exit boundary is recorded separately','CRC diagnostic is not whole-RAM or hidden DMA ownership proof','No GOP or phone XNU instruction execution'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,git_bound_inputs=len(bound),segments=observation['segment_count']),indent=2))
if __name__=='__main__':main()
