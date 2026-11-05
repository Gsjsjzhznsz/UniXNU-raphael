#!/usr/bin/env python3
"""Compare frozen service waits without running or modifying a handset experiment."""
import argparse,collections,datetime as dt,hashlib,json,re
from pathlib import Path
from entry_probe import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-run',default='20261102T163215Z');ap.add_argument('--comparison-run',default='20261102T161209Z');a=ap.parse_args()
 assert all(re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z',v) for v in [a.source_run,a.comparison_run])
 out=ROOT/'evidence/private/service-wait-analysis'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');out.mkdir(parents=True,mode=0o700)
 inputs={};runs={}
 for run in [a.source_run,a.comparison_run]:
  base=ROOT/'evidence/private/android-return-run'/run
  d=json.loads((base/'report.json').read_text());sym=json.loads((base/'services-symbolicated.json').read_text())
  assert d['nonce_matched'] and sym['cache_uuid_matches']
  inputs[run]={p.name:sha(p) for p in [base/'report.json',base/'services-symbolicated.json']}
  runs[run]=(d,sym)
 d,sym=runs[a.source_run];e=d['native_early'];i=e['init'];s=i['services']
 assert d['passed'] and d['native_early_verified'] and s['captured'] and sym['full_checkpoint_verified']
 stacks=[]
 for proc in sym['services']:
  for thread in proc['threads']:
   symbols=[thread.get('pc',{}).get('symbol')]+[f.get('symbol') for f in thread.get('frames',[]) if f]
   stacks.append(dict(pid=proc['pid'],name=proc['name'],tid=thread['tid'],state=thread['state'],symbols=[x for x in symbols if x]))
 spring=next(t for t in stacks if t['name']=='SpringBoard' and '_CFPREFERENCES_IS_WAITING_FOR_SYSTEM_AND_USER_CFPREFSDS' in t['symbols'])
 direct=next(t for t in stacks if t['name']=='keybagd' and '_CFPREFERENCES_IS_WAITING_FOR_DIRECT_CFPREFSD' in t['symbols'])
 handler=next(t for t in stacks if t['name']=='keybagd' and any('CFPrefsDaemon handleSourceMessage:' in x for x in t['symbols']))
 proxies=[p for p in s['processes'] if p['name']=='xpcproxy'];assert proxies and all(p['service_slot'] is None for p in proxies)
 other,other_sym=runs[a.comparison_run];glob=other['native_verified_globals'];assert not other['passed'] and glob['snapshot_crc_verified'] and not glob['full_checkpoint_verified']
 console=(ROOT/'evidence/private/android-return-run'/a.comparison_run/'recovered-msgbuf.txt');inputs[a.comparison_run][console.name]=sha(console)
 named={}
 for name in ['cfprefsd','backboardd']:
  named[name]=sorted({int(v) for v in re.findall(r'/'+name+r'\[([0-9]+)\]',console.read_text())});assert named[name]
 # Re-decode the actual returned memory with both decoder versions.
 import native_early,importlib.util
 work=ROOT/json.loads((ROOT/'artifacts/service-spawn-review/current-work.json').read_text())['directory']
 spec=importlib.util.spec_from_file_location('before_wait_audit_native',work/'before/scripts/native_early.py');before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before)
 reader_results=[]
 for run in [a.source_run,a.comparison_run]:
  report=runs[run][0];base=ROOT/'evidence/private/android-return-run'/run
  build=json.loads((ROOT/report['build']/'report.json').read_text())
  contract=build['native_mmu_contract']
  payload=json.loads((ROOT/build['payload']['external_payload_report']).read_text())
  kernel=(ROOT/payload['kernel']).read_bytes()
  read,symbols=native_early.recovered_snapshot_reader((base/'native-early-wire.bin').read_bytes(),(base/'native-early-delta.bin').read_bytes(),kernel,contract)
  actual=native_early.decode_service_snapshot(read,symbols)
  assert actual==before.decode_service_snapshot(read,symbols)
  expected=(report.get('native_early') or report['native_verified_globals'])['init']['services']
  assert actual==expected
  reader_results.append(dict(run=run,returned_snapshot_crc_verified=True,old_and_new_decoders_equal=True,published_report_matches=True))
 report=dict(passed=True,handset_executed=False,source_run=a.source_run,comparison_run=a.comparison_run,inputs=inputs,
  source_normal_checkpoint=True,source_processes=len(s['processes']),source_proxy_count=len(proxies),proxy_thread_snapshots=0,
  selected_threads=stacks,observed_waits=dict(SpringBoard=spring,keybagd_direct_wait=direct,keybagd_CFPrefs_message_handler=handler),
  comparison_named_console_processes=named,comparison_normal_checkpoint=False,
  source_display=i['display'],comparison_display=glob['init']['display'],
  conclusions=['SpringBoard waits for a synchronous CFPrefs reply at capture.',
   'keybagd has both a direct CFPrefs wait and a thread inside CFPrefsDaemon source-message handling; daemon name absence alone does not prove no CFPrefs servicing.',
   'All 41 xpcproxy processes lack thread snapshots in the successful record; their job identity, startup stage and reason for waiting remain unknown.',
   'The comparison console proves named cfprefsd/backboardd presence in that failed run only; clients=3 does not independently prove original newUserClient returned successfully.',
   'No specific service root cause or safe behavioral fix is established by the existing records.'],
  missing_fields=['xpcproxy kernel continuation, saved user PC and original-cache frames at the successful stop',
   'job label or target argv for each proxy; a sampled thread alone will not prove it',
   'CFPrefs request/reply correlation and peer identity',
   'actual return from backboardd display-client call'],
  next_observation=dict(checkpoint='unchanged first-method marker1 after at least10poll',
   single_variable='explicit additional bounded read-only proxy-thread capture',proxy_capacity=64,threads_per_proxy=1,pid_scan_max=255,
   hardware_threshold_seconds=20,observer_limit_seconds=360,absolute_pet_budget_seconds=420,
   excluded_claims=['no longer wait','no service/plist rewrite','no desktop acceptance']),
  limits=['A single stack is not proof of permanent deadlock, successful check-in, peer identity or reply completion.',
   'First thread in the BSD list is a referenced thread sample, not a verified main-thread identity.',
   'Separate runs must not be concatenated into one continuous boot.'],reader_preflight=reader_results)
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(out)
if __name__=='__main__':main()
