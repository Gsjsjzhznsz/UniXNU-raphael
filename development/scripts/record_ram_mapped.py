#!/usr/bin/env python3
"""Bind each RAM mapping build to Git; independently decode both handset phases."""
import argparse,json,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from sec_build_provenance import verify_archived_build
from inspect_device import read_fdt
from ram_read_probe import decode as decode_before
from ram_mapped_probe import decode
EVIDENCE=ROOT/'UniXNU-raphael/evidence'
def ref(path):return dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
def bind(build):
 d=json.loads((build/'report.json').read_text());assert d['ram_mapped_probe'] and d['stop_stage'] in [2,3] and not d['ram_write_pages']
 revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 qpath=ROOT/d['qemu_evidence'];q=json.loads(qpath.read_text());assert q['qemu_passed']
 for group,repo,rev,prefix in [('source_inputs',ROOT,revision,''),('upstream_inputs',ROOT/'sources/UniXNU',d['unixnu_revision'],'sources/UniXNU/')]:
  assert d[group]==q[group]
  for item in d[group]:
   raw=(build/'source-snapshot'/item['path']).read_bytes();assert sha(raw)==item['sha256']
   assert raw==subprocess.check_output(['git','-C',str(repo),'show',rev+':'+item['path'][len(prefix):]])
 names=['ram_mapped_probe.py','ram_read_probe.py','audit_ram_mapped.py','audit_ram_read.py','validate_ram_mapped.py','validate_ram_read.py','run_ram_mapped_qemu.py','build_sec_dxe.py','build_handset_sec_dxe.py','inspect_diagnostic_fd.py','run_sec_dxe.py','sec_build_provenance.py','reboot_after_probe.py','record_ram_mapped.py','fixtures/sec_dxe_kernel.c']
 checks=[]
 for name in names:
  path=ROOT/'scripts'/name;raw=path.read_bytes();assert raw==subprocess.check_output(['git','-C',str(ROOT),'show',revision+':scripts/'+name]);checks.append(ref(path))
 report=dict(source_revision=revision,unixnu_revision=d['unixnu_revision'],source_inputs=d['source_inputs'],upstream_inputs=d['upstream_inputs'],verification_inputs=checks,
  phases=[dict(stage=d['stop_stage'],private_build=str(build.relative_to(ROOT)),image_sha256=d['image_sha256'],firmware_sha256=d['firmware_sha256'],qemu_report=d['qemu_evidence'],qemu_report_sha256=sha(qpath.read_bytes()))],handset_executed=False)
 target=EVIDENCE/('ram-mapped-source-binding-stage'+str(d['stop_stage'])+'-'+build.name+'.json');assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(verify_archived_build(build,d,target),indent=2));print(target)

def record(bindings,cleanup):
 phases=[];sources=None
 for stage,binding_path in zip([2,3],bindings):
  binding=json.loads(binding_path.read_text());phase=binding['phases'][0];assert phase['stage']==stage
  if sources is not None:assert sources==binding['source_inputs']
  sources=binding['source_inputs'];build=ROOT/phase['private_build'];d=json.loads((build/'report.json').read_text());v=verify_archived_build(build,d,binding_path)
  for item in binding['verification_inputs']:
   assert sha(subprocess.check_output(['git','-C',str(ROOT),'show',binding['source_revision']+':'+item['path']]))==item['sha256']
  handoff=EVIDENCE/('sec-ram-mapped-stage'+str(stage)+'-handoff.json');h=json.loads(handoff.read_text());private=ROOT/h['private_readback']
  attempt=EVIDENCE/('sec-dxe-attempt-'+private.name+'.json');a=json.loads(attempt.read_text())
  assert h.keys()-a.keys()=={'fdt_sha256','limits','log_sha256','map_sha256','source'}
  assert a.keys()-h.keys()=={'observation_seconds','started_utc'}
  assert all(h[k]==a[k] for k in h.keys()&a.keys())
  for key in ['firmware_checkpoint_passed','ram_read_checkpoint_verified','ram_mapped_checkpoint_verified','nonce_matched','root_verified','boot_partition_unchanged','android_boot_completed']:assert h[key],key
  assert h['sec_dxe_stage_verified']==stage and h['private_build']==phase['private_build']
  assert h['build_source_verification']['source_revision']==v['source_revision']
  for key in ['image_sha256','firmware_sha256']:assert h[key]==phase[key]==d[key]
  blob=(private/'after.dtb').read_bytes();assert sha(blob)==h['fdt_sha256']
  tree=read_fdt(blob);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
  raw=(private/'ram-read.bin').read_bytes();assert raw==chosen.properties['raphael,ram-read'];before=decode_before(raw,d['ram_read_evidence']['policy']);assert before==h['ram_read']
  raw=(private/'ram-mapped.bin').read_bytes();assert raw==chosen.properties['raphael,ram-mapped'];mapped=decode(raw,before,stage);assert mapped==h['ram_mapped']
  assert sha((private/'firmware.log').read_bytes())==h['log_sha256']
  immutable=EVIDENCE/('sec-ram-mapped-stage'+str(stage)+'-handoff-'+private.name+'.json')
  if immutable.exists():assert immutable.read_bytes()==handoff.read_bytes()
  else:immutable.write_bytes(handoff.read_bytes())
  phases.append(dict(stage=stage,source_binding=ref(binding_path),handoff=ref(immutable),immutable_attempt=ref(attempt),
   private_readback=str(private.relative_to(ROOT)),image_sha256=h['image_sha256'],firmware_sha256=h['firmware_sha256'],before=before,mapped=mapped))
 cp=cleanup/'report.json';assert cp.is_relative_to(ROOT/'evidence/private/entry-probe-cleanup') and cleanup.name>Path(phases[-1]['private_readback']).name
 c=json.loads(cp.read_text())
 for key in ['normal_android_reboot','android_boot_completed','root_verified','boot_partition_unchanged','transient_probe_absent']:assert c[key],key
 assert not c['flash_or_restore_performed']
 output=dict(passed=True,phases=phases,cleanup=ref(cp),mapped_sparse_read_verified=True,read_translation_verified=True,write_translation_denied=True,
  before_and_after_cache_digests_equal=True,android_return_and_clean_reboot_verified=True,ram_written=False,new_allocator_memory=False,
  entire_window_tested=False,ownership_proven=False,handset_xnu_executed=False)
 target=EVIDENCE/'boot-ram-mapped-observation.json';target.write_text(json.dumps(output,indent=2)+'\n');print(target);print('Two handset phases, independent wire/FDT, immutable attempts and normal reboot cleanup verified')
def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='mode',required=True)
 b=sub.add_parser('bind');b.add_argument('--build',type=Path,required=True)
 r=sub.add_parser('record');r.add_argument('--stage2-binding',type=Path,required=True);r.add_argument('--stage3-binding',type=Path,required=True);r.add_argument('--cleanup',type=Path,required=True);a=ap.parse_args()
 if a.mode=='bind':bind(a.build.resolve())
 else:record([a.stage2_binding.resolve(),a.stage3_binding.resolve()],a.cleanup.resolve())
if __name__=='__main__':main()
