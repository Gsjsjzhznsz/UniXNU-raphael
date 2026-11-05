#!/usr/bin/env python3
"""Verify resource-free handset display enumeration against a frozen ADT."""
import argparse,copy,datetime,json,struct
from pathlib import Path
from entry_probe import ROOT
from native_display_adt import add_display_declaration,strip_display_declaration,KEY
from validate_handset_adt import parse

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--baseline-adt',type=Path,required=True)
 a=p.parse_args();raw=a.baseline_adt.read_bytes();original,end=parse(raw)
 assert end==len(raw)
 tree=copy.deepcopy(original);add_display_declaration(tree)
 clean=copy.deepcopy(tree);assert strip_display_declaration(clean) and clean==original
 checks=['enumeration strips to the exact qualified hardware tree']
 cases=[
  ('extra MMIO',lambda t:t['nodes']['arm-io']['nodes']['raphael-gop']['props'].update(reg=bytes(16))),
  ('extra IRQ',lambda t:t['nodes']['arm-io']['nodes']['raphael-gop']['props'].update(interrupts=bytes(4))),
  ('wrong scale',lambda t:t['nodes']['chosen']['props'].update({'display-scale':bytes(4)})),
  ('missing scale',lambda t:t['nodes']['chosen']['props'].pop('display-scale')),
  ('missing opt-in',lambda t:t['nodes']['chosen']['props'].pop(KEY)),
  ('duplicate subsystem',lambda t:t['nodes']['arm-io']['nodes'].update(other=copy.deepcopy(t['nodes']['arm-io']['nodes']['raphael-gop']))),
 ]
 for name,mutate in cases:
  malformed=copy.deepcopy(tree);mutate(malformed)
  try:strip_display_declaration(malformed)
  except AssertionError:checks.append(name+' rejected')
  else:raise AssertionError(name)
 assert not strip_display_declaration(copy.deepcopy(original));checks.append('legacy ADT accepted')
 # Hardware edits remain visible after normalizing the permitted OS policy.
 changed=copy.deepcopy(tree);io=changed['nodes']['arm-io']['props']
 assert 'ranges' in io;io['ranges']=bytes(len(io['ranges']))
 assert strip_display_declaration(changed) and changed!=original
 checks.append('changed hardware ranges remain unequal')
 out=ROOT/'artifacts/display-enumeration'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 out.mkdir(parents=True)
 report=dict(passed=True,checks=checks,baseline=str(a.baseline_adt.resolve().relative_to(ROOT)),handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(passed=True,checks=len(checks),report=str(out/'report.json'))))
if __name__=='__main__':main()
