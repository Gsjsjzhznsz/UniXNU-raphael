#!/usr/bin/env python3
"""Build the explicit xpcproxy snapshot at the original first-method stop with inputs recovered from 163215Z.
Default: validate inputs only. --build compiles and freezes a kernel; no device I/O.
"""
import argparse,datetime as dt,hashlib,json,os,struct,subprocess,sys
from pathlib import Path
from entry_probe import ROOT

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    group=ap.add_mutually_exclusive_group()
    group.add_argument('--build',action='store_true')
    group.add_argument('--preflight-only',action='store_true')
    args=ap.parse_args()
    baseline=ROOT/'artifacts/native-bootstrap-attempt/20261102T162658Z/report.json'
    frozen=json.loads(baseline.read_text());assert frozen['passed'] and frozen['watchdog_method_checkpoint']
    inputs=dict(scratch_data=ROOT/'evidence/private/desktop-data/20261030T155658Z/report.json',
        root_policy=ROOT/'evidence/private/desktop-root-policy/20261030T081351Z/report.json',
        storage_audit=ROOT/'artifacts/native-bootstrap-attempt/20261102T162658Z/auxiliary/storage-abi/interface-audit.json',
        storage_candidate=ROOT/'artifacts/desktop-prelink/20261030T072416Z/kernel.macho')
    scratch=json.loads(inputs['scratch_data'].read_text())
    assert scratch['passed'] and not scratch['handset_executed'] and scratch['volume_uuid']
    assert (inputs['scratch_data'].parent/'seed.bin').stat().st_size==scratch['seed_bytes']==611715
    provenance=json.loads((baseline.parent/'auxiliary/raphael-data-seed/provenance.json').read_text())
    assert inputs['scratch_data']==Path(provenance['scratch_source'])
    root=json.loads(inputs['root_policy'].read_text());assert root['passed']
    assert {p['role'] for p in root['policies']}=={'OS','SystemOS'}
    for policy in root['policies']:
        base=inputs['root_policy'].parent/policy['role']
        assert (base/'manifest.bin').stat().st_size==544+policy['block_count']*32
        assert digest(base/'trusted-key.bin')==policy['trusted_key_sha256']
    audit=json.loads(inputs['storage_audit'].read_text())
    assert audit['live_native_4k'] and audit['method_slots']==190
    assert digest(inputs['storage_candidate'])==audit['candidate_sha256']
    assert inputs['storage_candidate'].read_bytes()[:4]==bytes.fromhex('cffaedfe')
    plan=json.loads(inputs['storage_candidate'].with_suffix('.json').read_text())
    assert plan['original_sha256']=='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7'
    base_patch='UniXNU-raphael/patches/xnu/raphael-watchdog-method-checkpoint.patch'
    expected=next(x['sha256'] for x in frozen['source_inputs'] if x['path']==base_patch)
    assert digest(ROOT/base_patch)==expected,'First-method baseline must remain unchanged; select the separate post-method patch'
    command=[sys.executable,'scripts/build_native_bootstrap.py','--native-diagnostic','--handset-display','--handset-data','--handset-ufs','--service-observer','--watchdog-method-checkpoint','first-method','--service-spawn-waits']
    for key,path in inputs.items():command += ['--'+key.replace('_','-'),str(path)]
    out=ROOT/'artifacts/service-spawn-build'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');out.mkdir(parents=True)
    changed=[x['path'] for x in frozen['source_inputs'] if (ROOT/x['path']).is_file() and digest(ROOT/x['path'])!=x['sha256']]
    report=dict(passed=True,preflight_only=not args.build,handset_executed=False,baseline=str(baseline.relative_to(ROOT)),inputs={k:dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for k,p in inputs.items()},command=command,source_changes_from_success=changed)
    (out/'preflight.json').write_text(json.dumps(report,indent=2)+'\n');print(out,flush=True)
    if not args.build:
        print('Input schemas, candidate hash, root manifests, seed and unchanged first-method patch verified.');return
    env=dict(os.environ);env['PATH']='/opt/unixnu-linux/bin:'+env['PATH']
    # Isolate the snapshot addition while preserving the live driver's status fix.
    display='UniXNU-raphael/package/drivers/RaphaelDesktopDisplay.cpp'
    frozen_display=baseline.parent/'snapshot'/display
    expected_display=next(x['sha256'] for x in frozen['source_inputs'] if x['path']==display)
    assert digest(frozen_display)==expected_display
    env['RAPHAEL_DISPLAY_SOURCE']=str(frozen_display)
    env['RAPHAEL_DISPLAY_SOURCE_SHA256']=expected_display
    report['selected_display_source']=dict(path=str(frozen_display.relative_to(ROOT)),sha256=expected_display,
        live_source_preserved=True,live_source_sha256=digest(ROOT/display))
    with (out/'build.log').open('w') as log:result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    report['build_exit_code']=result.returncode
    log=(out/'build.log').read_text();at=log.rfind('{\n  "passed":')
    if at>=0:
        final=json.loads(log[at:]);bp=Path(final['artifact_directory'])/'report.json'
        assert bp.resolve().is_relative_to(ROOT/'artifacts/native-bootstrap-attempt')
        report['kernel_build_report']=str(bp.relative_to(ROOT))
        build=json.loads(bp.read_text());assert build['watchdog_checkpoint_mode']=='first-method' and build['service_spawn_waits']
        report['passed']=result.returncode==0 and build['passed']
    else:report['passed']=False
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ['passed','kernel_build_report','build_exit_code']},indent=2))
    if not report['passed']:
        print(log[-5000:]);raise SystemExit(result.returncode or 1)
if __name__=='__main__':main()
