#!/usr/bin/env python3
"""Bind a RAM-write handset artifact to Git, then independently record its run."""
import argparse,json,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from sec_build_provenance import verify_archived_build
from ram_read_probe import decode as decode_read
from ram_write_probe import decode
from inspect_device import read_fdt
BP=None
def bind(build):
 d=json.loads((build/'report.json').read_text());assert d['ram_read_probe'] and d['stop_stage']==2 and d['ram_write_pages']>0
 rev=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 qpath=ROOT/d['qemu_evidence'];q=json.loads(qpath.read_text());assert q['qemu_passed']
 for group,repo,commit,prefix in [('source_inputs',ROOT,rev,''),('upstream_inputs',ROOT/'sources/UniXNU',d['unixnu_revision'],'sources/UniXNU/')]:
  assert d[group]==q[group]
  for i in d[group]:
   raw=(build/'source-snapshot'/i['path']).read_bytes();assert sha(raw)==i['sha256']
   assert raw==subprocess.check_output(['git','-C',str(repo),'show',commit+':'+i['path'][len(prefix):]])
 checks=['ram_read_probe.py','ram_write_probe.py','audit_ram_read.py','audit_ram_write.py','validate_ram_read.py','validate_ram_write.py','run_ram_write_qemu.py','build_sec_dxe.py','build_handset_sec_dxe.py','inspect_diagnostic_fd.py','run_sec_dxe.py','sec_build_provenance.py','reboot_after_probe.py','record_ram_write_observation.py','fixtures/sec_dxe_kernel.c','fixtures/ram_write_host.c']
 verification=[]
 for name in checks:
  p=ROOT/'scripts'/name;raw=p.read_bytes();assert raw==subprocess.check_output(['git','-C',str(ROOT),'show',rev+':scripts/'+name]);verification.append(dict(path='scripts/'+name,sha256=sha(raw)))
 report=dict(source_revision=rev,unixnu_revision=d['unixnu_revision'],source_inputs=d['source_inputs'],upstream_inputs=d['upstream_inputs'],verification_inputs=verification,phases=[dict(stage=2,private_build=str(build.relative_to(ROOT)),image_sha256=d['image_sha256'],firmware_sha256=d['firmware_sha256'],qemu_report=d['qemu_evidence'],qemu_report_sha256=sha(qpath.read_bytes()))],handset_executed=False)
 assert not BP.exists();BP.write_text(json.dumps(report,indent=2)+'\n');print(verify_archived_build(build,d,BP))
def record(cleanup):
 binding=json.loads(BP.read_text());phase=binding['phases'][0];build=ROOT/phase['private_build'];d=json.loads((build/'report.json').read_text());v=verify_archived_build(build,d,BP)
 matches=[]
 for candidate in (ROOT/'UniXNU-raphael/evidence').glob('sec-dxe-attempt-*.json'):
  item=json.loads(candidate.read_text())
  if item.get('private_build')==phase['private_build'] and item.get('ram_write_checkpoint_verified') and item.get('firmware_checkpoint_passed'):matches.append((candidate,item))
 assert matches
 attempt,immutable=sorted(matches,key=lambda pair:pair[0].name)[-1];private=ROOT/immutable['private_readback']
 hp=ROOT/('UniXNU-raphael/evidence/sec-ram-write-stage2-handoff-'+private.name+'.json')
 if not hp.exists():
  latest=ROOT/'UniXNU-raphael/evidence/sec-ram-write-stage2-handoff.json';raw=latest.read_bytes();assert json.loads(raw)['private_readback']==immutable['private_readback'];hp.write_bytes(raw)
 h=json.loads(hp.read_text())
 assert h.keys()-immutable.keys()=={'fdt_sha256','limits','log_sha256','map_sha256','source'}
 assert immutable.keys()-h.keys()=={'observation_seconds','started_utc'}
 assert all(h[k]==immutable[k] for k in h.keys()&immutable.keys())
 for k in ['firmware_checkpoint_passed','ram_write_checkpoint_verified','ram_read_checkpoint_verified','nonce_matched','root_verified','boot_partition_unchanged','android_boot_completed']:assert h[k],k
 assert h['sec_dxe_stage_verified']==2 and h['private_build']==phase['private_build']
 assert h['build_source_verification']['source_revision']==v['source_revision']
 for k in ['image_sha256','firmware_sha256']:assert h[k]==phase[k]==d[k]
 blob=(private/'after.dtb').read_bytes();assert h['fdt_sha256']==sha(blob)
 tree=read_fdt(blob);chosen=next(n for n in tree.walk() if n.name=='chosen' and n.parent is tree)
 raw=(private/'ram-write.bin').read_bytes();assert chosen.properties['raphael,ram-write']==raw
 result=decode(raw,d['ram_read_evidence']['policy'],d['ram_write_pages']);assert result==h['ram_write']
 read=decode_read((private/'ram-read.bin').read_bytes(),d['ram_read_evidence']['policy']);assert read==h['ram_read'] and read['end_counter']<=result['start_counter']
 assert h['log_sha256']==sha((private/'firmware.log').read_bytes())
 cp=cleanup/'report.json';assert cp.is_relative_to(ROOT/'evidence/private/entry-probe-cleanup') and cleanup.name>private.name
 c=json.loads(cp.read_text())
 for k in ['normal_android_reboot','android_boot_completed','root_verified','boot_partition_unchanged','transient_probe_absent']:assert c[k],k
 assert not c['flash_or_restore_performed']
 output=dict(passed=True,source_revision=binding['source_revision'],source_binding=str(BP.relative_to(ROOT)),source_binding_sha256=sha(BP.read_bytes()),handoff=str(hp.relative_to(ROOT)),handoff_sha256=sha(hp.read_bytes()),immutable_attempt=str(attempt.relative_to(ROOT)),immutable_attempt_sha256=sha(attempt.read_bytes()),attempt=private.name,cleanup=str(cp.relative_to(ROOT)),cleanup_sha256=sha(cp.read_bytes()),image_sha256=h['image_sha256'],firmware_sha256=h['firmware_sha256'],ram_write=result,ram_read=read,android_return_and_clean_reboot_verified=True,ram_written=True,new_allocator_memory=False,entire_window_tested=False,ownership_proven=False)
 (ROOT/'UniXNU-raphael/evidence'/('boot-ram-write-observation-pages'+str(d['ram_write_pages'])+'.json')).write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
def main():
 global BP
 p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True);s=p.add_subparsers(dest='mode',required=True);b=s.add_parser('bind');b.add_argument('--build',type=Path,required=True);c=s.add_parser('record');c.add_argument('--cleanup',type=Path,required=True);a=p.parse_args()
 BP=a.binding.resolve();assert BP.is_relative_to(ROOT/'UniXNU-raphael/evidence')
 if a.mode=='bind':bind(a.build.resolve())
 else:record(a.cleanup.resolve())
if __name__=='__main__':main()
