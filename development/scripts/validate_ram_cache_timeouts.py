#!/usr/bin/env python3
"""Re-decode failed full-window emulator runs without converting them into success."""
import json,re,struct,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from ram_read_probe import decode as decode_read,policy
from ram_mapped_probe import decode as decode_mapped
from ram_write_probe import FIELDS as ENGINE_FIELDS
from ram_cache_write import FIELDS as CACHE_FIELDS
from audit_ram_cache import inspect_cache,inspect_cached_write

REV='bec9798ff8c31d0df90160387f831d66cd18c889'
UPSTREAM='0fc0fc1f9ddd0fbd4787738afef38667df5e0a95'
EVIDENCE=ROOT/'UniXNU-raphael/evidence'

def ref(path):return dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))

def check_case(path):
    item=json.loads(path.read_text());assert not item['passed'] and not item['handset_executed']
    run=(ROOT/item['run']).resolve();assert run.is_relative_to(ROOT/'artifacts/sec-dxe-qemu')
    serial=(run/'serial.log').read_bytes();assert sha(serial)==item['serial_sha256']
    def wire(name):
        matches=re.findall(rb'(?m)^'+name.encode()+rb' ([0-9a-f]+)$',serial)
        assert len(matches)==1,name
        return bytes.fromhex(matches[0].decode())
    before=decode_read(wire('RAM_READ_WIRE'),policy((run/'ram-read-policy.bin').read_bytes()))
    mapped=decode_mapped(wire('RAM_MAPPED_WIRE'),before,3)
    raw=wire('RAM_CACHE_WIRE');assert len(raw)==312
    if 'wire_sha256' in item:assert item['wire_sha256']==sha(raw)
    c=dict(zip(CACHE_FIELDS,struct.unpack('>16Q',raw[:128])))
    w=dict(zip(ENGINE_FIELDS,struct.unpack('>23Q',raw[128:])))
    assert c['version']==w['version']==1 and c['status']==w['status']==6
    assert c['reason']==3 and w['reason']==6 and c['pages']==w['requested_pages']==item['requested_pages']==65536
    assert c['base']==w['base']==before['base'] and c['bytes']==w['bytes']==before['bytes']==268435456
    assert c['current_el']==4 and c['sctlr']&0x1005==0x1005 and c['daif']&0x3c0==0x3c0
    assert c['frequency']==w['frequency']==before['frequency']==mapped['frequency']
    assert c['read_write_translations']==c['par_preserved']==c['restore_denials']==256 and c['map_restored']==1
    assert w['page_bytes']==4096 and 0<w['completed_pages']<65536
    assert w['completed_pages']<=w['restored_pages']<=w['completed_pages']+1
    assert w['backup_words']==w['dirty']==w['pattern_mismatches']==w['restore_mismatches']==0
    assert w['restore_words']==w['restored_pages']*512
    assert w['active_page']==w['base']+w['completed_pages']*4096
    assert c['pre_page_sync'] in [w['restored_pages'],w['restored_pages']+1]
    assert 3*w['completed_pages']<=c['post_page_sync']<=3*w['restored_pages']
    assert w['end_counter']-w['start_counter']>8*w['frequency']
    elapsed=(w['end_counter']-w['start_counter'])*1000/w['frequency'];assert elapsed==item['elapsed_ms']
    for key in ['completed_pages','restored_pages','dirty','backup_words']:assert w[key]==item[key]
    failures=re.findall(rb'(?m)^FAIL (.+)$',serial)
    assert sorted(failures)==sorted([b'all requested cached pages completed',b'diagnostic exit status']),failures
    assert b'PASS independent MMU-off receiver verifies every restored DRAM word' in serial
    assert b'PASS read-only map restored and queried' in serial
    assert b'SEC_DXE_FIXTURE_FAILED' in serial and b'SEC_DXE_FIXTURE_OK' not in serial
    snapshots=[]
    files=sorted(p for p in (run/'source-snapshot').rglob('*') if p.is_file());assert len(files)==149
    for source in files:
        relative=source.relative_to(run/'source-snapshot').as_posix();data=source.read_bytes()
        if relative.startswith('sources/UniXNU/'):
            expected=subprocess.check_output(['git','-C',str(ROOT/'sources/UniXNU'),'show',UPSTREAM+':'+relative[len('sources/UniXNU/'):]])
        else:
            assert relative.startswith('UniXNU-raphael/package/firmware/RaphaelPkg/')
            expected=subprocess.check_output(['git','-C',str(ROOT),'show',REV+':'+relative])
        if item.get('uncommitted_direct_loop_experiment') and relative.endswith('/Sec/RamCacheAdapter.c'):
            assert data!=expected and sha(data)==item['source_snapshot_sha256']
        else:assert data==expected,relative
        snapshots.append(dict(path=relative,sha256=sha(data)))
    if not item.get('uncommitted_direct_loop_experiment'):
        assert inspect_cache(run)['boundary_completion_revision']==2
        assert inspect_cached_write(run)['single_64bit_store_only']
    if item.get('instruction_clock_experiment'):
        assert not item['adopted'] and item['source_changes_reverted']
        for x in item['experimental_harness']:assert ref(ROOT/x['path'])==x
    fd=run/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd'
    return dict(failure_report=ref(path),serial=ref(run/'serial.log'),firmware=ref(fd),
                wire_sha256=sha(raw),archived_source_inputs=snapshots,
                completed_pages=w['completed_pages'],restored_pages=w['restored_pages'],elapsed_ms=elapsed,
                raw_before_and_mapped_gates_verified=True,timeout_enforced=True,dirty_and_backup_cleared=True,
                read_only_map_restored=True,independent_receiver_original_bytes_check_recorded=True,
                all_requested_pages_completed=False,full_range_passed=False,handset_executed=False)

def main():
    paths=sorted(EVIDENCE.glob('ram-cache-qemu-timeout-[0-9]*.json'));assert len(paths)==4
    cases=[check_case(p) for p in paths]
    result=dict(negative_evidence_checks_passed=True,all_full_range_runs_failed=True,
                cases=cases,runner_sha256=sha(Path(__file__).read_bytes()),
                limits='Re-decodes archived simulator failure/recovery records. Does not prove full-range success, handset timing, ownership or new allocator memory.')
    target=EVIDENCE/'ram-cache-qemu-timeout-verification.json';target.write_text(json.dumps(result,indent=2)+'\n')
    print('Verified four failed full-range runs, 596 archived source files and original raw recovery records; full-range success remains false.')
    print(target)

if __name__=='__main__':main()
