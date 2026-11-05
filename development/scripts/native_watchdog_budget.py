#!/usr/bin/env python3
"""Explicit ADT contract for a bounded observer petting the qualified 20s WDT."""
import argparse,datetime,json,struct,sys
from pathlib import Path
from entry_probe import ROOT
KEY='unixnu,diagnostic-watchdog'
QUALIFICATION=ROOT/'evidence/private/android-return-run/20261101T030853Z/report.json'
def decode(raw):
 assert len(raw) in (48,56)
 version,base,size,frequency,seconds,budget=struct.unpack_from('<6Q',raw)
 observer=40000 if len(raw)==48 else struct.unpack_from('<Q',raw,48)[0]
 assert (version,len(raw),budget,observer) in [(1,48,60000,40000),(2,56,180000,120000),(3,56,300000,240000),(4,56,420000,360000),(5,56,780000,720000),(6,56,1860000,1800000)]
 assert base>0 and base%4096==0 and base<=2**64-4096 and size==4096
 assert 0<frequency<=(2**32-1)//21 and seconds==20
 return dict(base=base,bytes=size,frequency=frequency,seconds=seconds,budget_ms=budget,observer_ms=observer,contract_version=version)
def qualified(raw):
 d=decode(raw);r=json.loads(QUALIFICATION.read_text());w=r['native_watchdog']
 assert r['passed'] and r['native_watchdog_verified'] and r['cleanup_transient_properties_absent']
 assert all(w[k]==d[k] for k in ['base','frequency','seconds'])
 return d
def from_adt(raw):
 from validate_handset_adt import parse
 tree,end=parse(raw);assert end==len(raw)
 value=tree['nodes']['cpus']['nodes']['cpu0']['props'].get(KEY)
 return qualified(value) if value is not None else None
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--adt',type=Path,required=True);p.add_argument('--data-report',type=Path,help='Preserve the existing ephemeral Data binding while changing only the observer contract');p.add_argument('--shorten',action='store_true',help='Explicitly reduce an existing qualified observer/pet contract in a new ADT; hardware thresholds remain unchanged');p.add_argument('--budget-ms',type=int,choices=[60000,180000,300000,420000,780000,1860000],default=60000);a=p.parse_args()
 from validate_handset_adt import parse
 tree,end=parse(a.adt.read_bytes());assert end==a.adt.stat().st_size
 r=json.loads(QUALIFICATION.read_text());w=r['native_watchdog']
 version,observer={60000:(1,40000),180000:(2,120000),300000:(3,240000),420000:(4,360000),780000:(5,720000),1860000:(6,1800000)}[a.budget_ms]
 value=struct.pack('<6Q',version,w['base'],4096,w['frequency'],20,a.budget_ms) if version==1 else struct.pack('<7Q',version,w['base'],4096,w['frequency'],20,a.budget_ms,observer);d=qualified(value)
 props=tree['nodes']['cpus']['nodes']['cpu0']['props']
 if a.shorten:
  assert KEY in props,'Shortening requires an existing qualified contract'
  old=qualified(props[KEY]);assert d['budget_ms']<old['budget_ms'] and d['observer_ms']<old['observer_ms'],'Both observer and pet bounds must decrease'
 elif KEY in props:assert a.budget_ms>qualified(props[KEY])['budget_ms']
 props[KEY]=value
 sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'));from unixnu.devicetree import node
 def encode(t):return node(t['props']['name'].rstrip(b'\0').decode(),[(k,v) for k,v in t['props'].items() if k!='name'],[encode(c) for c in t['nodes'].values()])
 out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-watchdog-budget');out.mkdir(parents=True,mode=0o700)
 path=out/'kernel.macho.adt';path.write_bytes(encode(tree));assert from_adt(path.read_bytes())==d
 from entry_probe import sha
 provenance=json.loads((a.adt.parent/'adt-provenance.json').read_text());provenance.update(adt_sha256=sha(path.read_bytes()),adt_bytes=path.stat().st_size,diagnostic_watchdog_budget=d,diagnostic_watchdog_source_adt=str(a.adt))
 (out/'adt-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 (out/'report.json').write_text(json.dumps(dict(passed=True,adt=str(path.relative_to(ROOT)),source_adt=str(a.adt),qualification=str(QUALIFICATION.relative_to(ROOT)),contract=d,shortened=a.shorten,handset_verified=False),indent=2)+'\n')
 if a.data_report:
  data=json.loads(a.data_report.read_text())
  assert data['passed'] and data['persistent'] is False and (ROOT/data['adt']).resolve()==a.adt.resolve()
  data.update(adt=str(path.relative_to(ROOT)),source_data_report=str(a.data_report.resolve().relative_to(ROOT)),watchdog_budget_contract=d,source_watchdog_report=json.loads((out/'report.json').read_text()),handset_qualified=False,handset_verified=False)
  (out/'data-report.json').write_text(json.dumps(data,indent=2)+'\n')
 print(out)
if __name__=='__main__':main()
