#!/usr/bin/env python3
"""Read frozen handset reports and original APFS launch jobs; never contact a device.
Run with .venv/bin/python (pyfsapfs 20260921). Raw job bytes stay private.
"""
import argparse, collections, datetime as dt, hashlib, json, plistlib, re
from pathlib import Path
import pyfsapfs
from entry_probe import ROOT
from prepare_desktop_data import ReadOnlyRange

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',default='20261102T163215Z')
    ap.add_argument('--comparison-run',default='20261102T161209Z')
    args=ap.parse_args()
    assert re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z',args.run)
    assert re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z',args.comparison_run)
    out=ROOT/'evidence/private/service-startup-audit'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True,mode=0o700)
    p=ROOT/'evidence/private/android-return-run'/args.run/'report.json'
    d=json.loads(p.read_text());assert d['passed'] and d['native_early_verified']
    early=d['native_early'];services=early['init']['services'];processes=services['processes']
    assert services['captured'] and services['scanned_through_pid']==services['pid_capacity']-1
    names=collections.Counter(x['name'] for x in processes)
    console=early['console']['text']
    q=ROOT/'evidence/private/android-return-run'/args.comparison_run/'report.json'
    other=json.loads(q.read_text());glob=other['native_verified_globals']
    assert other['nonce_matched'] and glob['snapshot_crc_verified']
    original_console=(q.parent/'recovered-msgbuf.txt').read_text()
    matches=[]
    for line in original_console.splitlines():
        for service in ['cfprefsd','backboardd']:
            if re.search(r'/'+service+r'\[[0-9]+\]',line):
                t=re.match(r'\[\s*([0-9.]+)\]',line)
                matches.append(dict(service=service,console_line_timestamp_seconds=float(t[1]) if t else None,process_ids=[int(x) for x in re.findall(service+r'\[([0-9]+)\]',line)]))
    disks_path=ROOT/'artifacts/desktop-disks/20261030T075713Z/report.json'
    disks=json.loads(disks_path.read_text());assert disks['passed']
    jobs=[];binaries=[]
    assert pyfsapfs.get_version()=='20260921'
    for disk in disks['disks']:
        description=disk['apfs_containers'][0]
        image=ROOT/disk['path'];assert image.stat().st_size==disk['bytes']
        span=ReadOnlyRange(image,description['offset'],description['bytes'])
        container=pyfsapfs.container();container.open_file_object(span)
        volume=container.get_volume(0)
        assert str(volume.identifier).lower()==description['volumes'][0].lower()
        for directory in ['/System/Library/LaunchDaemons','/System/Library/LaunchAgents']:
            entry=volume.get_file_entry_by_path(directory)
            if entry is None:continue
            for child in entry.sub_file_entries:
                if not any(x in child.name.lower() for x in ['cfpref','backboard','springboard']):continue
                raw=child.read(child.size);job=plistlib.loads(raw)
                target=out/'original-jobs'/disk['role']/directory.lstrip('/')/child.name
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                fields=['Label','Program','ProgramArguments','RunAtLoad','KeepAlive','UserName','POSIXSpawnType','SessionType','LimitLoadToSessionType','Disabled','MachServices']
                jobs.append(dict(role=disk['role'],path=directory+'/'+child.name,sha256=hashlib.sha256(raw).hexdigest(),fields={k:job[k] for k in fields if k in job},session_constraint_present=any(k in job for k in ['SessionType','LimitLoadToSessionType'])))
        for path in ['/usr/sbin/cfprefsd','/usr/libexec/backboardd']:
            entry=volume.get_file_entry_by_path(path)
            binaries.append(dict(role=disk['role'],path=path,exists=entry is not None,bytes=entry.size if entry else None,mode=oct(entry.file_mode) if entry else None))
        container.close();span.file.close()
    board=next(x for x in jobs if x['fields'].get('Label')=='com.apple.backboardd')
    assert board['fields']['RunAtLoad'] and board['fields']['KeepAlive'] and not board['session_constraint_present']
    assert {x['service'] for x in matches}=={'cfprefsd','backboardd'}
    report=dict(passed=True,handset_executed=False,source_run=args.run,source_report_sha256=digest(p),comparison_run=args.comparison_run,comparison_report_sha256=digest(q),
        scope='Read-only frozen reports and original local APFS images; no new handset run; PID scan and selected thread snapshots are different collections.',
        process_count=len(processes),process_names=dict(names),selected_thread_snapshot_count=len(services['services']),pid_scan_max=services['scanned_through_pid'],
        target_processes=[x for x in processes if x['name'] in ['SpringBoard','cfprefsd','backboardd']],
        original_jobs=jobs,binary_metadata=binaries,comparison_console_matches=matches,
        native_observer_ms=early['diagnostic_watchdog_budget']['elapsed_ms'],wall_seconds_to_android=d['wall_seconds_to_android'],
        code_signature_counters=early['init']['native4k_signature'],
        conclusions=dict(four_entries_are_not_full_process_list=True,aqua_constraint_claim_disproved_for_this_backboardd_job=True,
            cfprefsd_and_backboardd_started_in_comparison=True,time_window_hypothesis_unproven=True,xpcproxy_backlog_observed=True),
        limits=['Console line timestamps are not exact exec timestamps; interleaved console output can share a timestamp.',
                'PID scan ends at 255; absent at capture does not prove never launched or permanent failure.',
                'Different runs have different schedules and watchdog behavior; no 250-400 second launch latency is inferred.',
                'Binary presence and plist parsing do not prove all libraries, XPC check-in, service readiness or a visible frame.'])
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(out)
    print(json.dumps(dict(passed=True,processes=len(processes),selected_threads=len(services['services']),xpcproxy=names['xpcproxy'],backboardd_run_at_load=True,backboardd_session_constraint=False,comparison_services=sorted({x['service'] for x in matches}))))
if __name__=='__main__':main()
