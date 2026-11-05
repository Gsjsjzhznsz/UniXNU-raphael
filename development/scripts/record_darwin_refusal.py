#!/usr/bin/env python3
"""Bind exact refusal-only handset builds and record independent wire/cleanup."""
import argparse,json,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from darwin_probe import decode
from sec_build_provenance import verify_archived_build
from inspect_device import read_fdt

def load(p):return json.loads(p.read_text())
def bind(bp,build,previous):
 d=load(build/'report.json');assert d['darwin_test'] and d['physical_timer_arch'] and d['payload_test']
 assert not any(d.get(k) for k in ['ram_read_probe','visible_manager','experimental_gop','input_protocol'])
 rev=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 result=dict(source_revision=rev,unixnu_revision=d['unixnu_revision'],darwin_revision=d['darwin_revision'],phases=[],handset_executed=False)
 qpath=ROOT/d['qemu_evidence'];q=load(qpath);assert q['qemu_passed'] and q['darwin_test']
 for group,repo,commit,prefix in [('source_inputs',ROOT,rev,''),('upstream_inputs',ROOT/'sources/UniXNU',d['unixnu_revision'],'sources/UniXNU/'),('darwin_inputs',ROOT/'sources/UniXNU/drivers/DarwinBoot',d['darwin_revision'],'sources/UniXNU/drivers/DarwinBoot/')]:
  assert d[group]==q[group];result[group]=d[group]
  for item in d[group]:
   raw=(build/'source-snapshot'/item['path']).read_bytes();assert sha(raw)==item['sha256']
   assert raw==subprocess.check_output(['git','-C',str(repo),'show',commit+':'+item['path'][len(prefix):]])
 checks=['record_darwin_refusal.py','build_sec_dxe.py','build_handset_sec_dxe.py','run_sec_dxe.py','sec_build_provenance.py','darwin_probe.py','validate_darwin_wire.py','audit_darwin_sources.py','inspect_diagnostic_fd.py','reboot_after_probe.py','fixtures/sec_dxe_kernel.c']
 result['verification_inputs']=[]
 for name in checks:
  raw=(ROOT/'scripts'/name).read_bytes();assert raw==subprocess.check_output(['git','-C',str(ROOT),'show',rev+':scripts/'+name]);result['verification_inputs'].append(dict(path='scripts/'+name,sha256=sha(raw)))
 if previous:
  old=load(previous)
  for k in ['source_revision','unixnu_revision','darwin_revision','source_inputs','upstream_inputs','darwin_inputs','verification_inputs']:assert old[k]==result[k]
  result['phases']=old['phases']
 stage={2:2,3:3,4:6}[d['stop_stage']];assert [p['stage'] for p in result['phases']]=={2:[],3:[2],6:[2,3]}[stage]
 result['phases'].append(dict(stage=stage,private_build=str(build.relative_to(ROOT)),image_sha256=d['image_sha256'],firmware_sha256=d['firmware_sha256'],qemu_report=d['qemu_evidence'],qemu_report_sha256=sha(qpath.read_bytes())))
 assert not bp.exists();bp.write_text(json.dumps(result,indent=2)+'\n');print(verify_archived_build(build,d,bp))
def record(bp,cleanup):
 binding=load(bp);assert [p['stage'] for p in binding['phases']]==[2,3,6];phases=[]
 for phase in binding['phases']:
  build=ROOT/phase['private_build'];d=load(build/'report.json');v=verify_archived_build(build,d,bp)
  matches=[p for p in (ROOT/'UniXNU-raphael/evidence').glob('sec-dxe-attempt-*.json') if load(p).get('private_build')==phase['private_build'] and load(p).get('darwin_checkpoint_verified')]
  ap=sorted(matches)[-1];attempt=load(ap);private=ROOT/attempt['private_readback'];stage=phase['stage']
  for k in ['firmware_checkpoint_passed','nonce_matched','root_verified','boot_partition_unchanged','android_boot_completed','darwin_checkpoint_verified','physical_timer_checkpoint_verified','manager_checkpoint_verified']:assert attempt[k]
  assert attempt['sec_dxe_stage_verified']==stage and attempt['build_source_verification']['source_revision']==v['source_revision']
  blob=(private/'after.dtb').read_bytes();tree=read_fdt(blob);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
  wire=(private/'darwin.bin').read_bytes();assert wire==chosen.properties['raphael,darwin-diagnostic']
  parsed=decode(wire,stage,handset=True);assert parsed==attempt['darwin']
  hp=ROOT/('UniXNU-raphael/evidence/sec-darwin-stage'+str(stage)+'-handoff-'+private.name+'.json')
  if not hp.exists():
   latest=ROOT/('UniXNU-raphael/evidence/sec-darwin-stage'+str(stage)+'-handoff.json');raw=latest.read_bytes();assert load(latest)['private_readback']==attempt['private_readback'];hp.write_bytes(raw)
  handoff=load(hp);assert handoff['fdt_sha256']==sha(blob) and handoff['log_sha256']==sha((private/'firmware.log').read_bytes())
  assert all(handoff[k]==attempt[k] for k in handoff.keys()&attempt.keys())
  phases.append(dict(stage=stage,attempt=private.name,source_binding=str(bp.relative_to(ROOT)),image_sha256=d['image_sha256'],firmware_sha256=d['firmware_sha256'],immutable_attempt=str(ap.relative_to(ROOT)),immutable_attempt_sha256=sha(ap.read_bytes()),handoff=str(hp.relative_to(ROOT)),handoff_sha256=sha(hp.read_bytes()),darwin=parsed))
 cp=cleanup/'report.json';c=load(cp);assert cp.is_relative_to(ROOT/'evidence/private/entry-probe-cleanup') and cleanup.name>phases[-1]['attempt']
 for k in ['normal_android_reboot','android_boot_completed','root_verified','boot_partition_unchanged','transient_probe_absent']:assert c[k]
 assert not c['flash_or_restore_performed']
 result=dict(passed=True,source_revision=binding['source_revision'],darwin_revision=binding['darwin_revision'],source_binding=str(bp.relative_to(ROOT)),source_binding_sha256=sha(bp.read_bytes()),phases=phases,handset_executed=True,darwinboot_driver_started=True,refusal_lifecycle_verified=True,darwinboot_kernel_handoff_verified=False,xnu_executed=False,new_allocator_memory=False,valid_kernel_supplied=False,partition_writes_performed=False,cleanup=str(cp.relative_to(ROOT)),cleanup_sha256=sha(cp.read_bytes()),recorder_sha256=sha(Path(__file__).read_bytes()))
 target=ROOT/'UniXNU-raphael/evidence/boot-darwin-refusal-observation.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n');print(target)
def main():
 p=argparse.ArgumentParser();p.add_argument('--binding',required=True,type=Path);s=p.add_subparsers(dest='mode',required=True);b=s.add_parser('bind');b.add_argument('--build',required=True,type=Path);b.add_argument('--previous-binding',type=Path);o=s.add_parser('record');o.add_argument('--cleanup',required=True,type=Path);a=p.parse_args();bp=a.binding.resolve();assert bp.is_relative_to(ROOT/'UniXNU-raphael/evidence')
 if a.mode=='bind':bind(bp,a.build.resolve(),a.previous_binding.resolve() if a.previous_binding else None)
 else:record(bp,a.cleanup.resolve())
if __name__=='__main__':main()
