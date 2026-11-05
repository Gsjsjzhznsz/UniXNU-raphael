#!/usr/bin/env python3
import datetime as dt,json,lzma,tempfile,os
from pathlib import Path
from entry_probe import ROOT,run,sha
from android_return import RETURN,SDK,build_stub
parent=ROOT/'artifacts/android-return-host';parent.mkdir(parents=True,exist_ok=True)
out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
try:
 raw,report=build_stub(out)
 # Real SDK decoder, with sanitizer bounds and output-tail checks.
 fixture=ROOT/'scripts/fixtures/android_return_host.c'
 run(out,['gcc','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie','-Wall','-Wextra','-Werror','-I'+str(RETURN),'-I'+str(SDK),fixture,RETURN/'ReturnStub.c',SDK/'LzmaDec.c','-o',out/'host-test'])
 data=bytes(range(256))*16384
 (out/'input.bin').write_bytes(data);(out/'input.lzma').write_bytes(lzma.compress(data,format=lzma.FORMAT_ALONE,preset=1))
 log=run(out,[out/'host-test',out/'input.lzma',out/'input.bin']);(out/'host-test.log').write_bytes(log);assert b'ANDROID_RETURN_HOST_OK' in log
 report.update(passed=True,host_sanitizers=['ASan','UBSan'],host_fixture_sha256=sha(fixture.read_bytes()),limits=['Host decode and AArch64 structure only; no SEC integration or handset execution'])
except Exception as e:
 report=dict(passed=False,error=str(e));(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');raise
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(log.decode());print('stub bytes',len(raw))
