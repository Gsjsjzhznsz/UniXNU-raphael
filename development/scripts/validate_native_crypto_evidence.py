#!/usr/bin/env python3
"""Independently verify pinned source-provider provenance and frozen execution evidence."""
import hashlib,json,subprocess
from pathlib import Path
from entry_probe import ROOT,sha

def load(path):return json.loads(path.read_text())
def record(path):return dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
def main():
 source_path=ROOT/'UniXNU-raphael/evidence/native-crypto-source.json'
 source=load(source_path);raw_report=ROOT/source['source_report']
 assert source['passed'] and not source['authentication_against_apple_archive'] and not source['provider_qualified']
 assert sha(raw_report.read_bytes())==source['source_report_sha256']
 raw=load(raw_report);assert raw['files']==source['files'] and len(raw['files'])==809 and raw['kernel_c_sources']==529
 repo=ROOT/'artifacts/native-bootstrap/feeds/corecrypto-2023-c0651bae'
 assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==source['source_revision']
 assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True)
 for item in raw['files']:
  name=item['path'];assert not Path(name).is_absolute() and '..' not in Path(name).parts
  data=(repo/name).read_bytes()
  assert len(data)==item['bytes'] and sha(data)==item['sha256']
  assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['git_blob_sha1']
  assert subprocess.check_output(['git','-C',str(repo),'rev-parse',source['source_revision']+':'+name],text=True).strip()==item['git_blob_sha1']
 build_path=ROOT/'UniXNU-raphael/evidence/native-bootstrap-host.json';build=load(build_path)
 assert build['passed'] and build['source_crypto_evaluation'] and build['outputs_frozen']
 assert not build['handset_executed'] and not build['prelink_executed']
 for item in build['source_inputs']:
  assert sha((ROOT/item['path']).read_bytes())==item['sha256']
 for item in build['auxiliary_artifacts']+build['logs']:
  assert sha((ROOT/item['path']).read_bytes())==item['sha256']
 for item in build['frozen_compile_records']:
  assert sha((ROOT/build['compile_records_root']/item['path']).read_bytes())==item['sha256']
 assert len(build['frozen_compile_records'])==build['compile_records']==887
 image=ROOT/build['native_macho']['path'];assert sha(image.read_bytes())==build['native_macho']['sha256']
 auxiliary=ROOT/build['artifact_directory']/'auxiliary/corecrypto-2023'
 for name in ['build-report.json','build-report-namespaced.json']:
  r=load(auxiliary/name);assert r['compiled_sources']==r['object_architecture_and_deployment_audited']==529 and not r['failures']
 survey=load(auxiliary/'link-survey-namespaced.json');assert not survey['missing_kernel_names'] and not survey['duplicate_kernel_names']
 qpath=ROOT/'UniXNU-raphael/evidence/native-xnu-qemu-20261028T094943.352011Z.json';q=load(qpath);out=ROOT/q['artifact_directory']
 assert qpath.read_bytes()==(out/'report.json').read_bytes()
 assert q['kernel_sha256']==build['native_macho']['sha256']==sha((out/'native-kernel.macho').read_bytes())
 for item in q['evidence_files']:assert sha((out/item['path']).read_bytes())==item['sha256']
 observed=load(out/'debugger-observation.json');assert q['debugger']==observed
 assert q['xnu_entry_verified'] and q['xnu_arm_init_verified'] and q['kernel_unchanged'] and q['esp_unchanged']
 assert observed['loaded_file_bytes_match'] and len(observed['loaded_segments'])==10
 expected={s['name']:s for s in q['layout']['segments']}
 for segment in observed['loaded_segments']:
  assert segment['sha256']==expected[segment['name']]['sha256'] and segment['bytes']==expected[segment['name']]['file_bytes']
 assert observed['source_crypto_post']['mode']==0 and observed['source_crypto_post']['returned'] and observed['source_crypto_post']['status']==0
 assert observed['source_crypto_start_status']==0 and observed['source_crypto_provider']['initialized']
 assert observed['source_crypto_provider']['status']==0 and observed['source_crypto_provider']['crypto_init']==1 and observed['source_crypto_provider']['functions']!=0
 assert q['default_source_crypto_post_and_registration_verified']
 assert not q['passed'] and not observed['target_reached'] and q['stop_at']=='bsd_init'
 assert 'Unable to find driver for this platform' in q['target_failure']
 assert q['kalloc_budget_override']==observed['kalloc_policy']['budget']==200
 assert not q['handset_executed'] and not q['full_xnu_boot_verified']
 report=dict(passed=True,source=record(source_path),build=record(build_path),qemu=record(qpath),
  kernel_sha256=q['kernel_sha256'],verified_source_files=809,archive_c_sources_each=529,frozen_kernel_records=887,
  loaded_segments_verified=10,default_post_and_registration_verified=True,bsd_init_reached=False,
  target_failure=q['target_failure'],emulator_kalloc_budget=200,handset_executed=False,
  authenticated_against_apple_archive=False,provider_qualified=False,runner_sha256=sha(Path(__file__).read_bytes()))
 target=ROOT/'UniXNU-raphael/evidence/native-crypto-verification.json';target.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
