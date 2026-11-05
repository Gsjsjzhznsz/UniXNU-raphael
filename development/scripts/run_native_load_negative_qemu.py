#!/usr/bin/env python3
"""Mutate one loaded kernel byte at the real pre-exit callback; QEMU only."""
import argparse
import datetime as dt
import json
import re
import subprocess
import tempfile
import time
import struct
from pathlib import Path
from entry_probe import ROOT, sha
from native_load import FIELDS

def main():
    p=argparse.ArgumentParser();p.add_argument('--positive-report',type=Path,required=True);a=p.parse_args()
    qp=a.positive_report.resolve();q=json.loads(qp.read_text())
    assert q['passed'] and q['stage'] in [7,8] and q['native_load_test'] and q['android_return_qemu']
    original=qp.parent;serial=(original/'serial.log').read_bytes()
    match=re.search(rb'Loading driver at 0x([0-9a-f]+) EntryPoint=0x[0-9a-f]+ DiagnosticReturnDxe.efi',serial,re.I);assert match
    base=int(match[1],16)
    mp=original/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Drivers/DiagnosticReturnDxe/DiagnosticReturnDxe/DEBUG/DiagnosticReturnDxe.map'
    matches=re.findall(r'^([0-9a-f]+)\s+[0-9a-f]+\s+0\s+ExitNotice$',mp.read_text(),re.M);assert len(matches)==1
    target=base+int(matches[0],16);at=q['native_load_contract']['physical_base']
    parent=ROOT/'artifacts/native-load-negative-qemu';parent.mkdir(exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));print(out,flush=True)
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    sock='/tmp/rnl-'+out.name[:22]+'.sock'
    script='set pagination off\nset architecture aarch64\ntarget remote '+sock+'\nhbreak *'+hex(target)+'\ncontinue\ninfo registers pc\nx/bx '+hex(at)+'\nset {unsigned char}'+hex(at)+' = (*(unsigned char *)'+hex(at)+') ^ 1\nx/bx '+hex(at)+'\ndetach\nquit\n'
    (out/'fault.gdb').write_text(script)
    command=q['command']+['-S','-gdb','unix:'+sock+',server=on,wait=off']
    report=dict(passed=False,runner_sha256=sha(Path(__file__).read_bytes()),positive_report=str(qp.relative_to(ROOT)),positive_report_sha256=sha(qp.read_bytes()),
        map_sha256=sha(mp.read_bytes()),callback_address=target,mutated_address=at,command=command,
        scope='One-byte debugger corruption of loaded memory at actual original-loader exit notification; QEMU only',handset_executed=False,xnu_executed=False)
    proc=None
    try:
        with (out/'serial.log').open('wb') as log:
            proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);time.sleep(.3)
            g=subprocess.run(['gdb-multiarch','-q','-batch','-x',str(out/'fault.gdb')],capture_output=True,timeout=35)
            (out/'gdb.log').write_bytes(g.stdout+g.stderr);assert g.returncode==0 and b'Breakpoint 1,' in g.stdout
            code=proc.wait(timeout=35)
        raw=(out/'serial.log').read_bytes();match=re.search(rb'NATIVE_LOAD_WIRE ([0-9a-f]+)',raw);assert match
        wire=bytes.fromhex(match[1].decode());d=dict(zip(FIELDS,struct.unpack('>16Q',wire)))
        assert d['version']==(2 if q.get('native_exit_complete') else 1) and d['status']==2 and d['error']==1 and d['exit_notice_count']==1
        assert d['segment_count']==d['zero_segments_ok'] and d['file_segments_ok']==d['segment_count']-1
        assert d['args_ok']==1 and d['tree_crc']==q['native_load_contract']['adt_crc32']
        assert code!=0 and b'ANDROID_RETURN_QEMU_FAILED' in raw and b'PASS real high stub decode completed' in raw
        report.update(passed=True,returncode=code,loaded_memory=d,negative_validation='One file-segment CRC refused; Android receiver still restored; expected receiver status failure')
    finally:
        if proc and proc.poll() is None:proc.terminate();proc.wait()
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],negative_validation=report.get('negative_validation')),indent=2))
if __name__=='__main__':main()
