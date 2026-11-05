#!/usr/bin/env python3
"""Reject inconsistent physical/automatic full-manager key evidence."""
import datetime as dt,json,copy
from pathlib import Path
from entry_probe import ROOT,sha
from manager_keys import decode

def main():
 out=ROOT/'artifacts/manager-keys-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
 manager=dict(passed=True,frequency=1000,start_counter=110,end_counter=3300)
 wire=dict(events=3,errors=0,read_calls=3,pressed_mask=7,released_mask=3)
 log=b'RAPHAEL manager input start=100 deadline=6100 frequency=1000\nRAPHAEL manager key scan=1 unicode=0 automatic=0 ticks=1000\nRAPHAEL manager key scan=2 unicode=0 automatic=0 ticks=2000\nRAPHAEL manager key scan=0 unicode=13 automatic=0 ticks=3000\nmenu: enter, booting 0\nRAPHAEL manager keys up/down/enter/automatic/errors/delivered=1/1/1/0/0/3\nRAPHAEL manager input cleanup console=1 uninstall=1 close=1\n'
 cases=[]
 def accept(name,l=log,m=manager,w=wire,stage=6,physical=True):
  value=decode(l,stage,m,w);assert value['passed'] and value['physical_three_keys_verified']==physical;cases.append(name)
 def reject(name,l=log,m=manager,w=wire,stage=6):
  try:decode(l,stage,m,w)
  except (AssertionError,ValueError,KeyError):cases.append('reject '+name)
  else:raise AssertionError(name)
 accept('same-run physical Up Down Enter')
 for a,b in [(b'deadline=6100',b'deadline=6101'),(b'frequency=1000',b'frequency=1001'),(b'console=1',b'console=0'),(b'uninstall=1',b'uninstall=0'),(b'close=1',b'close=0'),(b'ticks=2000',b'ticks=999'),(b'ticks=3000',b'ticks=6000'),(b'scan=1',b'scan=9'),(b'unicode=13',b'unicode=12'),(b'automatic=0 ticks=3000',b'automatic=1 ticks=3000'),(b'1/1/1/0/0/3',b'1/1/1/0/0/4'),(b'booting 0',b'booting 1')]:reject(a.decode(),log.replace(a,b))
 reject('missing summary',log[:log.index(b'RAPHAEL manager keys')]);reject('duplicate summary',log+log[log.index(b'RAPHAEL manager keys'):]);reject('log after manager returned',m=dict(manager,end_counter=3000));reject('wrong frequency',m=dict(manager,frequency=999));reject('wire events',w=dict(wire,events=2));reject('wire errors',w=dict(wire,errors=1));reject('wire pressed mask',w=dict(wire,pressed_mask=3));reject('wire released mask',w=dict(wire,released_mask=8));reject('insufficient driver read calls',w=dict(wire,read_calls=2));reject('DXE key logs in SEC phase',stage=2)
 fallback=log.replace(b'RAPHAEL manager key scan=2 unicode=0 automatic=0 ticks=2000\n',b'').replace(b'automatic=0 ticks=3000',b'automatic=1 ticks=6000').replace(b'1/1/1/0/0/3',b'1/0/0/1/0/2').replace(b'booting 0',b'booting 1')
 accept('automatic deadline after physical Up is not physical Enter',l=fallback,m=dict(manager,end_counter=6200),w=dict(wire,events=1,read_calls=1,pressed_mask=1,released_mask=1),physical=False)
 reject('automatic key mislabeled physical',l=fallback.replace(b'automatic=1',b'automatic=0'),m=dict(manager,end_counter=6200),w=dict(wire,events=1,pressed_mask=1,released_mask=1))
 empty=b'RAPHAEL manager input start=100 deadline=6100 frequency=1000\nmenu: timeout, booting default 0\nRAPHAEL manager keys up/down/enter/automatic/errors/delivered=0/0/0/0/0/0\nRAPHAEL manager input cleanup console=1 uninstall=1 close=1\n'
 zero=dict(wire,events=0,read_calls=0,pressed_mask=0,released_mask=0)
 accept('upstream timeout without invented keys',l=empty,m=dict(manager,end_counter=6200),w=zero,physical=False)
 reject('early timeout',l=empty,w=zero)
 accept('SEC2 never executed keys',l=b'',stage=2,w=zero,physical=False);accept('MMU3 never executed keys',l=b'',stage=3,w=zero,physical=False)
 p=ROOT/'scripts/manager_keys.py';paths=[p,Path(__file__)]
 report=dict(passed=True,case_count=len(cases),cases=cases,decoder_sha256=sha(p.read_bytes()),source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],handset_executed=False)
 for target in [out/'report.json',ROOT/'UniXNU-raphael/evidence/manager-keys-host.json']:target.write_text(json.dumps(report,indent=2)+'\n')
 print(len(cases),'independent log/wire key checks');print(out)
if __name__=='__main__':main()
