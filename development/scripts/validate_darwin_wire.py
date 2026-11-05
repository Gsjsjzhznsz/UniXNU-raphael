#!/usr/bin/env python3
"""Replay actual emulator records and reject independently corrupted wire fields."""
import json
import re
import struct
from pathlib import Path
from entry_probe import ROOT, sha
from darwin_probe import decode, FIELDS


def main():
    reports = sorted((ROOT/'artifacts/sec-dxe-qemu').glob('*/report.json'))
    selected = {}
    for report in reports:
        data=json.loads(report.read_text())
        if not data.get('darwin_test') or not data.get('qemu_passed'):continue
        for name, run in data['executions'].items():
            stage=4 if name=='injected_brk' else (6 if data['stop_stage']==4 else data['stop_stage'])
            log=report.parent/('fault-injection/serial.log' if name=='injected_brk' else 'serial.log')
            match=re.search(rb'DARWIN_WIRE ([0-9a-f]+)',log.read_bytes())
            assert match
            selected[stage]=(report,bytes.fromhex(match[1].decode()))
    assert set(selected)=={2,3,4,6}
    checks=[]
    for stage,(path,raw) in sorted(selected.items()):
        assert decode(raw,stage)['passed']
        checks.append(dict(name='actual stage '+str(stage),passed=True,source=str(path.relative_to(ROOT)),wire_sha256=sha(raw)))
    assert decode(selected[6][1],6,handset=True)['handset_executed']
    assert not decode(selected[2][1],2,handset=True)['handset_executed']
    checks += [dict(name='handset mode marks only executed stage6',passed=True),dict(name='handset early stage is not driver execution',passed=True)]
    base=selected[6][1]
    corruptions={'version':2,'status':2,'console_installed':2,'driver_loaded':0,'driver_started':0,
        'protocol_revision':0x10000,'null_status':0,'missing_status':0,'invalid_status':0,'unixnu_status':0,
        'unloaded':0,'protocol_removed':0,'console_restored':0,'exit_boot_services':1,
        'log_characters':0,'services_alive':0,'crc_before':0x100000000}
    for field,value in corruptions.items():
        damaged=bytearray(base);struct.pack_into('>Q',damaged,FIELDS.index(field)*8,value)
        try:decode(damaged,6)
        except AssertionError:checks.append(dict(name='reject corrupted '+field,passed=True))
        else:raise AssertionError(field)
    for name,raw,stage in [('truncated',base[:-1],6),('trailing',base+b'\0',6),('late record at early stage',base,3)]:
        try:decode(raw,stage)
        except AssertionError:checks.append(dict(name='reject '+name,passed=True))
        else:raise AssertionError(name)
    result=dict(passed=True,command='python3 scripts/validate_darwin_wire.py',check_count=len(checks),checks=checks,
        decoder_sha256=sha((ROOT/'scripts/darwin_probe.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),handset_executed=False)
    out=ROOT/'UniXNU-raphael/evidence/darwin-wire-host.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(str(len(checks))+' wire checks passed');print(out)


if __name__=='__main__':main()
