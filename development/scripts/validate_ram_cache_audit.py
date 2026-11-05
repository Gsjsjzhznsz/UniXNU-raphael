#!/usr/bin/env python3
"""Reject native callback opcode/extent mutations and preserve historical audit schemas."""
import argparse
import datetime as dt
import json
import re
import tempfile
from pathlib import Path
from entry_probe import ROOT, sha
from audit_ram_cache import (linked_function, verify_direct_body, inspect_cached_read,
                             inspect_cached_write, inspect_cache)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--historical-audit', action='append', default=[], type=Path)
    args = parser.parse_args()
    build = args.build.resolve()
    cases = []

    def reject(name, callback):
        try:
            callback()
        except AssertionError:
            cases.append('reject ' + name)
        else:
            raise AssertionError('audit accepted ' + name)

    for write, name in [(False, 'ReadCacheRam64'), (True, 'WriteCacheRam64')]:
        body, mapping, _ = linked_function(build, name)
        checkpoint = int(re.search(r'(?m)^([0-9a-f]+)\s+.*\sRaphaelRamWriteCheckpoint$', mapping)[1], 16)
        assert verify_direct_body(body, write, checkpoint)
        cases.append('accept exact linked ' + name)
        for index, (address, opcode, text) in enumerate(body):
            damaged = list(body)
            damaged[index] = (address, opcode ^ 1, text)
            reject(name + ' changed opcode ' + str(index),
                   lambda b=damaged: verify_direct_body(b, write, checkpoint))
        first_ret = next(index for index, item in enumerate(body) if item[1] == 0xd65f03c0)
        reject(name + ' truncated at first RET',
               lambda: verify_direct_body(body[:first_ret + 1], write, checkpoint))
        reject(name + ' added instruction after failure block',
               lambda: verify_direct_body(body + [(body[-1][0] + 4, 0xd503201f, 'nop')], write, checkpoint))
        damaged = [(address + (4 if index == 1 else 0), opcode, text)
                   for index, (address, opcode, text) in enumerate(body)]
        reject(name + ' non-contiguous contribution',
               lambda: verify_direct_body(damaged, write, checkpoint))
        if write:
            reject('wrong checkpoint symbol', lambda: verify_direct_body(body, True, checkpoint + 4))
    read, write, cache = inspect_cached_read(build), inspect_cached_write(build), inspect_cache(build)
    assert read['direct_cache_phase_revision'] == write['direct_cache_phase_revision'] == 3
    assert read['no_second_word_callback'] and write['no_second_word_callback']
    assert cache['dsb_sy_before_maintenance'] and cache['dsb_sy_after_maintenance']
    historical = []
    for path in args.historical_audit:
        path = path.resolve()
        old = json.loads(path.read_text())
        archived = ROOT / old['qemu_reports']['3']['path']
        assert inspect_cached_write(archived.parent) == old['store']
        assert inspect_cache(archived.parent) == old['cache_instructions']
        historical.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()),
                               result_schema_identical=True))
        cases.append('historical schema unchanged ' + str(path.relative_to(ROOT)))
    parent = ROOT / 'artifacts/ram-cache-native-audit'
    parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'), dir=parent))
    source = [ROOT / 'scripts/audit_ram_cache.py', Path(__file__)]
    result = dict(passed=True, case_count=len(cases), cases=cases,
                  build=str(build.relative_to(ROOT)), build_report_sha256=sha((build / 'report.json').read_bytes()),
                  read=read, write=write, cache=cache, historical=historical,
                  source_inputs=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p.read_bytes())) for p in source],
                  handset_executed=False, allocator_enabled=False)
    data = json.dumps(result, indent=2) + '\n'
    (out / 'report.json').write_text(data)
    (ROOT / 'UniXNU-raphael/evidence/ram-cache-native-audit-host.json').write_text(data)
    print(out)
    print(len(cases), 'native opcode/extent and historical compatibility checks passed')


if __name__ == '__main__':
    main()
