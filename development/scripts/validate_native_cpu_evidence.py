#!/usr/bin/env python3
"""Independently re-read frozen native CPU build, loader and IRQ observations."""
import datetime as dt,hashlib,json,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
BUILD='artifacts/native-bootstrap-attempt/20261028T175838Z/report.json'
INSPECTION='artifacts/native-kernel-inspection/20261028T180002Z/report.json'
RUN='artifacts/native-xnu-qemu/20261028T180349.726107Z-e13esz8b/report.json'

def main():
 report=dict(passed=False,handset_executed=False,full_xnu_boot_verified=False,upstream_sync_executed=False)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=ROOT/'artifacts/native-cpu-verification'))
 def load(name):
  p=ROOT/name;raw=p.read_bytes();report.setdefault('reports',[]).append(dict(path=name,sha256=sha(raw)));return json.loads(raw)
 def check_file(name,digest):
  p=ROOT/name;assert sha(p.read_bytes())==digest,name
 try:
  build=load(BUILD);inspection=load(INSPECTION);run=load(RUN)
  assert build['passed'] and inspection['passed'] and run['passed']
  assert build['independent_cpu_enabled'] and build['source_pthread_enabled'] and not build['upstream_armcpu_linked']
  assert not build['module_upstream_sync_executed']
  digest=build['native_macho']['sha256'];check_file(build['native_macho']['path'],digest)
  assert inspection['native_macho_sha256']==run['kernel_sha256']==digest
  assert inspection['undefined_symbol_count']==0 and inspection['compile_record_count']==build['compile_records']==887
  for entry in build['source_inputs']:check_file(str(Path(build['artifact_directory'])/'snapshot'/entry['path']),entry['sha256'])
  for entry in build['auxiliary_artifacts']+build['logs']:check_file(entry['path'],entry['sha256'])
  for entry in build['frozen_compile_records']:check_file(str(Path(build['compile_records_root'])/entry['path']),entry['sha256'])
  auxiliary=ROOT/build['artifact_directory']/'auxiliary'
  provenance=json.loads((auxiliary/'armcpu/provenance.json').read_text())
  assert not provenance['upstream_armcpu_linked']
  assert sha((auxiliary/'armcpu/RaphaelBootCpu.cpp').read_bytes())==provenance['source_sha256']
  assert sha((auxiliary/'armcpu/libArmCpu.a').read_bytes())==provenance['archive_sha256']
  members=subprocess.check_output(['llvm-ar','t',auxiliary/'armcpu/libArmCpu.a'],text=True).splitlines()
  assert members==['RaphaelBootCpu.o'],members
  pthread=json.loads((auxiliary/'libpthread-kernel/report.json').read_text())
  assert pthread['sources']==3 and pthread['missing_kernel_names']==[]
  assert pthread['revision']=='c0e60fb5ecfc54cf379c261d3f9572cc22ded891'
  platform=next(m for m in build['modules'] if m['name']=='ArmDTPlatform')
  assert platform['commit']=='417ff95d6a6e8607ddea9309ec45c3bfd4a67c60'
  platform_raw=subprocess.check_output(['git','-C',platform['path'],'show',platform['commit']+':ArmDTPlatform.cpp'])
  assert platform_raw==(Path(platform['path'])/'ArmDTPlatform.cpp').read_bytes()
  nm=subprocess.check_output(['llvm-nm','--defined-only',ROOT/build['native_macho']['path']],text=True)
  assert '__ZN14RaphaelBootCpu5startEP9IOService' in nm and '_armcpu_registered' not in nm
  observation=load(str(Path(run['artifact_directory'])/'debugger-observation.json'))
  assert observation==run['debugger']
  for e in run['evidence_files']:check_file(str(Path(run['artifact_directory'])/e['path']),e['sha256'])
  for e in run['source_inputs']:check_file(str(Path(run['artifact_directory'])/'snapshot'/e['path']),e['sha256'])
  assert observation['loaded_file_bytes_match'] and len(observation['loaded_segments'])==10
  platform_state=observation['platform_configure']
  assert platform_state['returned_true'] and platform_state['return_value']==1
  cpu=observation['cpu_start'];assert cpu['returned_true'] and cpu['return_value']==1
  returns=[s for s in observation['stops'] if '_raphael_cpu_start_return' in s.get('symbols',[])]
  assert len(returns)==1 and returns[0]['pc']==cpu['return_target'] and returns[0]['x0']==1
  state=observation['cpu_state'];assert state['stage']==5 and state['registered']==1
  assert state['physical_timer']==1 and state['timer_irqs']>0 and state['eois']>=state['timer_irqs']
  assert state['pthread_status']==0 and state['pthread_functions']!=0
  assert '_rtclock_intr' in observation['reached_symbols'] and '_bsd_init' in observation['reached_symbols']
  assert observation['target_reached'] and observation['irq_calls']
  assert observation['stops'][-1]['pc'] in [v['return_target'] for v in observation['irq_calls']]
  resources=run['independent_cpu_resources'];assert resources['timer']=='physical'
  assert resources['timer_fdt_specifier'][0]==1 and state['intid']==resources['timer_fdt_specifier'][1]+16==resources['timer_intid']
  assert state['dist_pa']==resources['gic_registers'][0][0]
  assert resources['gic_registers'][1][0]<=state['redist_pa']<sum(resources['gic_registers'][1])
  assert run['cpu_entry_observation']['counter_frequency']==state['frequency']
  assert run['default_source_crypto_post_and_registration_verified'] and run['esp_unchanged']
  assert not run['handset_executed'] and not run['full_xnu_boot_verified']
  report.update(passed=True,kernel_sha256=digest,source_sha256=provenance['source_sha256'],
   platform_source_sha256=sha(platform_raw),cpu_archive_sha256=provenance['archive_sha256'],cpu_state=state,
   independent_cpu_start_verified=True,real_timer_callback_and_eoi_verified=True,bsd_init_reached=True,
   verified_source_input_count=len(build['source_inputs']),frozen_auxiliary_count=len(build['auxiliary_artifacts']),frozen_compile_record_count=887)
 except Exception as error:
  import traceback
  report['failure']=type(error).__name__+': '+str(error);(out/'exception.txt').write_text(traceback.format_exc())
 report['artifact_directory']=str(out.relative_to(ROOT))
 report['limits']=['QEMU GICv3 physical timer INTID comes only from that emulator DTB',
  'Handset GIC ownership, constant operation, SMP and power management remain unqualified',
  'No handset XNU, storage, mounted root or userspace result']
 for destination in [out/'report.json',ROOT/'UniXNU-raphael/evidence/native-cpu-verification.json']:
  destination.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
 if not report['passed']:raise SystemExit(1)
if __name__=='__main__':
 (ROOT/'artifacts/native-cpu-verification').mkdir(parents=True,exist_ok=True);main()
