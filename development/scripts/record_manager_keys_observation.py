#!/usr/bin/env python3
"""Bind manager-keys stages to Git and independently audit actual handset runs."""
import argparse,json,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from inspect_device import read_fdt
from manager_ui import decode as decode_ui
from manager_probe import decode as decode_manager
from sec_build_provenance import verify_archived_build
EVIDENCE=ROOT/'UniXNU-raphael/evidence'

def binding_path(stage):
    return EVIDENCE/f'manager-keys-source-binding-stage{stage}.json'

def bind(build):
    d=json.loads((build/'report.json').read_text())
    assert d['manager_keys'] and d['visible_manager'] and d['physical_timer_arch'] and d['payload_test']
    stage={2:2,3:3,4:6}[d['stop_stage']]
    revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    qpath=ROOT/d['qemu_evidence'];q=json.loads(qpath.read_text())
    assert q['qemu_passed'] and q['manager_keys'] and q['visible_manager']
    for group,repo,rev,prefix in [('source_inputs',ROOT,revision,''),('upstream_inputs',ROOT/'sources/UniXNU',d['unixnu_revision'],'sources/UniXNU/')]:
        assert d[group]==q[group]
        for item in d[group]:
            raw=(build/'source-snapshot'/item['path']).read_bytes()
            assert sha(raw)==item['sha256']
            assert raw==subprocess.check_output(['git','-C',str(repo),'show',rev+':'+item['path'][len(prefix):]])
    names=['manager_keys.py','validate_manager_keys.py','validate_manager_input.py','validate_manager.py','manager_ui.py','manager_probe.py','gop_probe.py','input_dxe.py','build_sec_dxe.py','build_handset_sec_dxe.py','inspect_diagnostic_fd.py','run_sec_dxe.py','sec_build_provenance.py','reboot_after_probe.py','record_manager_keys_observation.py','run_payload_fixture.py','validate_manager_ui.py','validate_manager_ui_wire.py']
    checks=[]
    for name in names:
        path=ROOT/'scripts'/name;raw=path.read_bytes()
        assert raw==subprocess.check_output(['git','-C',str(ROOT),'show',revision+':scripts/'+name])
        checks.append(dict(path='scripts/'+name,sha256=sha(raw)))
    phases=[]
    if stage!=2:
        prev=json.loads(binding_path(2 if stage==3 else 3).read_text())
        for key,value in [('source_revision',revision),('unixnu_revision',d['unixnu_revision']),('source_inputs',d['source_inputs']),('upstream_inputs',d['upstream_inputs']),('verification_inputs',checks)]:assert prev[key]==value,key
        phases=prev['phases']
    phases.append(dict(stage=stage,private_build=str(build.relative_to(ROOT)),image_sha256=d['image_sha256'],firmware_sha256=d['firmware_sha256'],qemu_report=d['qemu_evidence'],qemu_report_sha256=sha(qpath.read_bytes())))
    result=dict(source_revision=revision,unixnu_revision=d['unixnu_revision'],source_inputs=d['source_inputs'],upstream_inputs=d['upstream_inputs'],verification_inputs=checks,phases=phases,handset_executed=False)
    path=binding_path(stage);assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(verify_archived_build(build,d,path),indent=2))

def record(cleanup):
    bp=binding_path(6);binding=json.loads(bp.read_text())
    assert [p['stage'] for p in binding['phases']]==[2,3,6]
    phases=[];final=None
    for phase in binding['phases']:
        stage=phase['stage'];build=ROOT/phase['private_build'];d=json.loads((build/'report.json').read_text())
        verified=verify_archived_build(build,d,bp)
        hp=EVIDENCE/f'sec-manager-keys-stage{stage}-handoff.json';h=json.loads(hp.read_text())
        for key in ['firmware_checkpoint_passed','manager_ui_checkpoint_verified','manager_keys_checkpoint_verified','manager_checkpoint_verified','physical_timer_checkpoint_verified','payload_checkpoint_verified','gop_checkpoint_verified','input_dxe_checkpoint_verified','nonce_matched','root_verified','boot_partition_unchanged','android_boot_completed']:assert h[key],(stage,key)
        assert h['sec_dxe_stage_verified']==stage and h['private_build']==phase['private_build']
        assert h['build_source_verification']['source_revision']==verified['source_revision']
        for key in ['image_sha256','firmware_sha256']:assert h[key]==phase[key]==d[key]
        private=ROOT/h['private_readback'];ap=EVIDENCE/f'sec-dxe-attempt-{private.name}.json';a=json.loads(ap.read_text())
        assert h.keys()-a.keys()=={'fdt_sha256','limits','log_sha256','map_sha256','source'}
        assert a.keys()-h.keys()=={'observation_seconds','started_utc'}
        assert all(h[k]==a[k] for k in h.keys()&a.keys()) and a['started_utc']==private.name
        fdt=(private/'after.dtb').read_bytes();assert sha(fdt)==h['fdt_sha256']
        tree=read_fdt(fdt);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
        raw=(private/'manager-ui.bin').read_bytes();assert chosen.properties['raphael,manager-ui']==raw
        assert decode_ui(raw,stage,h['gop'])==h['manager_ui']
        raw=(private/'manager-run.bin').read_bytes();assert chosen.properties['raphael,manager-run']==raw
        assert decode_manager(raw,stage,h['payload'],h['entry']['cntfrq'],visible=True,manual=True)==h['manager']
        log=(private/'firmware.log').read_bytes();assert sha(log)==h['log_sha256']
        from manager_keys import decode as decode_keys
        assert decode_keys(log,stage,h['manager'],h['input_dxe'])==h['manager_keys']
        phases.append(dict(stage=stage,attempt=private.name,handoff=str(hp.relative_to(ROOT)),handoff_sha256=sha(hp.read_bytes()),immutable_attempt=str(ap.relative_to(ROOT)),immutable_attempt_sha256=sha(ap.read_bytes()),image_sha256=h['image_sha256'],firmware_sha256=h['firmware_sha256']))
        final=h
    cp=cleanup/'report.json';assert cp.is_relative_to(ROOT/'evidence/private/entry-probe-cleanup') and cleanup.name>phases[-1]['attempt']
    c=json.loads(cp.read_text())
    assert all(c[k] for k in ['normal_android_reboot','android_boot_completed','root_verified','boot_partition_unchanged','transient_probe_absent']) and not c['flash_or_restore_performed']
    timer=final['physical_timer'];assert timer['physical_only_timer_arch_verified'] and timer['restore_ok']
    assert timer['irq_count']==timer['eoi_count']==timer['notify_count']>0 and timer['unexpected']==timer['spurious']==0
    ui=final['manager_ui'];assert ui['manager_framebuffer_changed_and_restored'] and not ui['human_visibility_verified']
    result=dict(passed=True,source_revision=binding['source_revision'],unixnu_revision=binding['unixnu_revision'],source_binding=str(bp.relative_to(ROOT)),source_binding_sha256=sha(bp.read_bytes()),phases=phases,manager=final['manager'],manager_ui=ui,input_dxe=final['input_dxe'],payload=final['payload'],physical_timer=timer,manager_elapsed_seconds=(final['manager']['end_counter']-final['manager']['start_counter'])/final['manager']['frequency'],handset_executed=True,complete_unixnu_manager_executed=True,manager_framebuffer_changed_and_restored=True,human_visibility_verified=False,physical_keys_in_complete_manager_verified=final['manager_keys']['physical_three_keys_verified'],manager_keys=final['manager_keys'],darwin_boot_executed=False,xnu_executed=False,partition_writes_performed=False,cleanup=str(cp.relative_to(ROOT)),cleanup_sha256=sha(cp.read_bytes()),recorder_sha256=sha(Path(__file__).read_bytes()))
    target=EVIDENCE/f'manager-keys-observation-{phases[-1]["attempt"]}.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
    (EVIDENCE/'boot-manager-keys-observation.json').write_bytes(target.read_bytes())
    print(target);print(json.dumps(dict(elapsed=result['manager_elapsed_seconds'],changed=ui['pixels_changed'],restored=ui['pixels_restored'],irq=timer['irq_count']),indent=2))

def human(observation):
    source=EVIDENCE/'boot-manager-keys-observation.json';d=json.loads(source.read_text())
    assert d['passed'] and d['physical_keys_in_complete_manager_verified'] and d['manager_keys']['physical_three_keys_verified']
    attempt=d['phases'][-1]['attempt'];machine=EVIDENCE/f'manager-keys-observation-{attempt}.json';assert source.read_bytes()==machine.read_bytes()
    result=dict(passed=True,source_revision=d['source_revision'],attempt=attempt,machine_observation=str(machine.relative_to(ROOT)),machine_observation_sha256=sha(machine.read_bytes()),human_statement=observation,human_visibility_verified=True,human_up_down_power_verified=True,same_run_log_sequence=d['manager_keys']['events'],physical_keys_in_complete_manager_verified=True,darwin_boot_executed=False,xnu_executed=False)
    target=EVIDENCE/f'manual-manager-keys-observation-{attempt}.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n');print(target)

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    b=s.add_parser('bind');b.add_argument('--build',required=True,type=Path)
    r=s.add_parser('record');r.add_argument('--cleanup',required=True,type=Path)
    h=s.add_parser('human');h.add_argument('--observation',required=True)
    a=p.parse_args()
    if a.mode=='bind':bind(a.build.resolve())
    elif a.mode=='record':record(a.cleanup.resolve())
    else:human(a.observation)
if __name__=='__main__':main()
