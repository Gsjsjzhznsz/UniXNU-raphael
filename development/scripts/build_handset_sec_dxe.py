#!/usr/bin/env python3
"""Private diagnostic image, gated by this session's extent and emulator tests.

Only the downloaded extension is made available to new DXE allocations. This
is not an installable or complete phone UEFI, and this command never executes it.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import uuid
from entry_probe import ROOT, sha, image_parameters, instrument
from build_sec_dxe import build_firmware
from inspect_diagnostic_fd import inspect_fd
from private_android_image import read_boot, repack


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--stop-after-stage', type=int, choices=[2, 3, 4], default=2)
    parser.add_argument('--display-probe', action='store_true', help='Read-only probe; stage 2 only')
    parser.add_argument('--smmu-probe', action='store_true')
    parser.add_argument('--pixel-probe', action='store_true')
    parser.add_argument('--pixel-write', action='store_true')
    parser.add_argument('--experimental-gop', action='store_true')
    parser.add_argument('--input-probe', action='store_true')
    parser.add_argument('--input-read', action='store_true')
    parser.add_argument('--input-protocol', action='store_true')
    parser.add_argument('--menu-test', action='store_true')
    parser.add_argument('--manager-keys',action='store_true',help='Six-second full-manager physical key diagnostic with explicitly marked fallback')
    parser.add_argument('--visible-manager',action='store_true',help='Complete UniXNURun graphics plus input and physical TimerArch; reversible frame')
    parser.add_argument('--ram-write-pages',type=int,choices=[0,1,8,256],default=0,help='Stage2 reversible sourced RAM pages; defaults off')
    parser.add_argument('--ram-cache-write-pages',type=int,choices=[0,1,8,256,4096,16384,65536],default=0,help='Reversible page test with cache PoC maintenance; stages 2/3')
    parser.add_argument('--ram-mapped-probe',action='store_true',help='Read-only sourced WB/RO RAM map, stages 2/3; no new allocator')
    parser.add_argument('--ram-read-probe',action='store_true',help='Stage2-only sparse read of sourced candidate; no writes/allocator')
    parser.add_argument('--darwin-test',action='store_true',help='Pinned loader refusal/lifecycle only; no valid kernel or ExitBootServices')
    parser.add_argument('--payload-test',action='store_true',help='Read-only synthetic FAT and full two-second manager; physical TimerArch required')
    parser.add_argument('--physical-timer-arch',action='store_true')
    parser.add_argument('--timer-irq-test',action='store_true')
    parser.add_argument('--timer-route-test',action='store_true')
    parser.add_argument('--gic-enable-map',action='store_true')
    parser.add_argument('--ppi-enable-probe',action='store_true')
    parser.add_argument('--timer-source-test',action='store_true')
    parser.add_argument('--icc-probe',action='store_true',help='Stage2-only read-only ICC probe; requires GIC probe')
    parser.add_argument('--gic-probe', action='store_true', help='Stage2-only read-only GIC snapshot')
    args = parser.parse_args()
    if args.ram_cache_write_pages:args.ram_mapped_probe=True
    if args.ram_mapped_probe:
        assert args.stop_after_stage in [2,3] and not args.ram_write_pages
        args.ram_read_probe=True
    if args.darwin_test:
        assert not any([args.ram_read_probe,args.ram_write_pages,args.visible_manager,args.manager_keys,args.menu_test,args.experimental_gop,args.input_protocol])
        args.payload_test=args.physical_timer_arch=True
    if args.ram_write_pages:args.ram_read_probe=True
    assert not args.ram_read_probe or ((args.stop_after_stage==2 or args.ram_mapped_probe) and not any([args.display_probe,args.smmu_probe,args.pixel_probe,args.pixel_write,args.experimental_gop,args.input_probe,args.input_read,args.input_protocol,args.menu_test,args.payload_test,args.gic_probe,args.icc_probe,args.timer_source_test,args.ppi_enable_probe,args.gic_enable_map,args.timer_route_test,args.timer_irq_test,args.physical_timer_arch]))
    if args.manager_keys:args.visible_manager=True
    if args.visible_manager:
        args.physical_timer_arch=args.payload_test=args.display_probe=args.smmu_probe=args.pixel_probe=args.experimental_gop=args.input_probe=args.input_read=args.input_protocol=True
    if args.physical_timer_arch:
        args.gic_probe=args.icc_probe=args.gic_enable_map=args.timer_route_test=args.timer_irq_test=True
    assert not args.payload_test or args.physical_timer_arch
    assert not args.display_probe or args.stop_after_stage == 2 or args.experimental_gop
    assert not args.smmu_probe or args.display_probe
    assert not args.pixel_probe or args.smmu_probe
    assert not args.pixel_write or args.pixel_probe
    assert not args.experimental_gop or (args.pixel_probe and not args.pixel_write)
    assert not args.input_read or args.input_probe
    assert not args.input_protocol or args.input_read
    assert not args.menu_test or (args.experimental_gop and args.input_protocol)
    assert not args.gic_probe or ((args.stop_after_stage == 2 or args.physical_timer_arch) and not args.menu_test and (args.visible_manager or not any([args.display_probe,args.input_probe])))
    assert not args.timer_irq_test or args.timer_route_test
    assert not args.timer_route_test or args.gic_enable_map
    assert not args.gic_enable_map or (args.icc_probe and not args.ppi_enable_probe and not args.timer_source_test)
    assert not args.ppi_enable_probe or (args.icc_probe and not args.timer_source_test)
    assert not args.timer_source_test or args.icc_probe
    assert not args.icc_probe or args.gic_probe
    candidates = sorted((ROOT / 'artifacts/sec-dxe-qemu').glob('*/report.json'))
    qemu_path = next(p for p in reversed(candidates)
                     if json.loads(p.read_text()).get('stop_stage', 4) == args.stop_after_stage
                     and json.loads(p.read_text()).get('ram_cache_write_pages',0)==args.ram_cache_write_pages
                     and json.loads(p.read_text()).get('ram_mapped_probe',False)==args.ram_mapped_probe
                     and json.loads(p.read_text()).get('ram_read_probe',False)==args.ram_read_probe
                     and json.loads(p.read_text()).get('ram_write_pages',0)==args.ram_write_pages
                     and json.loads(p.read_text()).get('visible_manager',False)==args.visible_manager
                     and json.loads(p.read_text()).get('manager_keys',False)==args.manager_keys
                     and json.loads(p.read_text()).get('display_probe', False) == args.display_probe
                     and json.loads(p.read_text()).get('smmu_probe', False) == args.smmu_probe
                     and json.loads(p.read_text()).get('pixel_probe', False) == args.pixel_probe
                     and json.loads(p.read_text()).get('pixel_write', False) == args.pixel_write
                     and json.loads(p.read_text()).get('experimental_gop',False)==args.experimental_gop
                     and json.loads(p.read_text()).get('input_probe',False)==args.input_probe
                     and json.loads(p.read_text()).get('input_read',False)==args.input_read
                     and json.loads(p.read_text()).get('input_protocol',False)==args.input_protocol
                     and json.loads(p.read_text()).get('menu_test',False)==args.menu_test
                     and json.loads(p.read_text()).get('gic_probe',False)==args.gic_probe
                     and json.loads(p.read_text()).get('physical_timer_arch',False)==args.physical_timer_arch
                     and json.loads(p.read_text()).get('timer_irq_test',False)==args.timer_irq_test
                     and json.loads(p.read_text()).get('timer_route_test',False)==args.timer_route_test
                     and not json.loads(p.read_text()).get('timer_route_fault_test',False)
                     and json.loads(p.read_text()).get('gic_enable_map',False)==args.gic_enable_map
                     and json.loads(p.read_text()).get('ppi_enable_probe',False)==args.ppi_enable_probe
                     and json.loads(p.read_text()).get('timer_source_test',False)==args.timer_source_test
                     and json.loads(p.read_text()).get('icc_probe',False)==args.icc_probe
                     and not json.loads(p.read_text()).get('icc_fault_test',False)
                     and json.loads(p.read_text()).get('payload_test',False)==args.payload_test
                     and json.loads(p.read_text()).get('darwin_test',False)==args.darwin_test
                     and not json.loads(p.read_text()).get('qemu_arch_test',False))
    qemu = json.loads(qemu_path.read_text())
    assert qemu['qemu_passed'] and qemu['structure_checked']
    for item in qemu['source_inputs']:
        assert sha((ROOT / item['path']).read_bytes()) == item['sha256'], item['path']
    for item in qemu.get('darwin_inputs',[]):assert sha((ROOT/item['path']).read_bytes())==item['sha256']
    for item in qemu.get('upstream_inputs',[]):assert sha((ROOT/item['path']).read_bytes())==item['sha256']
    darwin_refusal_evidence=None
    if args.darwin_test:
        from darwin_probe import decode
        audit=ROOT/'UniXNU-raphael/evidence/darwin-source-audit.json';wire=ROOT/'UniXNU-raphael/evidence/darwin-wire-host.json'
        au,wi=[json.loads(p.read_text()) for p in [audit,wire]]
        assert au['passed'] and wi['passed'] and wi['decoder_sha256']==sha((ROOT/'scripts/darwin_probe.py').read_bytes())
        assert qemu['darwin_test'] and qemu['darwin_inputs'] and qemu['executions']['normal']['darwin']['passed']
        darwin_refusal_evidence={k:dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for k,p in [('source_audit',audit),('wire_host',wire)]}
    manager_ui_evidence=None
    if args.visible_manager:
        hp=ROOT/'UniXNU-raphael/evidence/manager-ui-host.json';fp=ROOT/'UniXNU-raphael/evidence/manager-ui-fixture-qemu.json';wp=ROOT/'UniXNU-raphael/evidence/manager-ui-wire-host.json'
        host,fixture=[json.loads(p.read_text()) for p in [hp,fp]]
        assert host['passed'] and host['address_sanitizer'] and host['undefined_behavior_sanitizer'] and host['case_count']>=31
        assert fixture['passed'] and fixture['manager_ui_transaction'] and fixture['screenshot_captured'] and len(fixture['manager_ui_results'])==3 and len(fixture['manager_input_results'])==3
        for i in host['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
        fixture_hashes={i['path']:i['sha256'] for i in fixture['source_inputs']}
        for i in qemu['source_inputs']+qemu['upstream_inputs']:assert fixture_hashes[i['path']]==i['sha256']
        wire=json.loads(wp.read_text());assert wire['passed'] and wire['decoder_sha256']==qemu['manager_ui_decoder_sha256']==sha((ROOT/'scripts/manager_ui.py').read_bytes())
        assert fixture['runner_sha256']==sha((ROOT/'scripts/run_payload_fixture.py').read_bytes())
        manager_ui_evidence=dict(host=dict(path=str(hp.relative_to(ROOT)),sha256=sha(hp.read_bytes())),fixture=dict(path=str(fp.relative_to(ROOT)),sha256=sha(fp.read_bytes())),wire=dict(path=str(wp.relative_to(ROOT)),sha256=sha(wp.read_bytes())))
    manager_keys_evidence=None
    if args.manager_keys:
        manager_keys_evidence={}
        for name in ['manager-input-host','manager-keys-host']:
            p=ROOT/'UniXNU-raphael/evidence'/(name+'.json');m=json.loads(p.read_text());assert m['passed']
            for i in m['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
            if name=='manager-input-host':assert m['case_count']>=24 and m['address_sanitizer'] and m['undefined_behavior_sanitizer']
            else:assert m['decoder_sha256']==sha((ROOT/'scripts/manager_keys.py').read_bytes())
            manager_keys_evidence[name]=dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes()))
    ram_probe=None
    if args.ram_read_probe:
        from ram_read_probe import sourced_policy
        ram_probe,_=sourced_policy()
        gates={}
        for name in (['ram-read-host'] if args.ram_mapped_probe else ['ram-read-host','ram-read-source-audit']):
            path=ROOT/'UniXNU-raphael/evidence'/(name+'.json');gate=json.loads(path.read_text())
            assert gate['passed'] and gate['decoder_sha256']==qemu['ram_read_decoder_sha256']==sha((ROOT/'scripts/ram_read_probe.py').read_bytes())
            for i in gate['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
            gates[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
            if name.endswith('audit'):
                assert gate['qemu_report']==str(qemu_path.relative_to(ROOT)) and gate['qemu_report_sha256']==sha(qemu_path.read_bytes())
                assert gate['fatal_load_site_udf_return_verified'] and gate['load']['no_store_through_candidate']
        assert qemu['executions']['normal']['ram_read']['passed']
        if args.ram_mapped_probe:
            audit_name=('ram-cache-source-audit-pages'+str(args.ram_cache_write_pages)) if args.ram_cache_write_pages else 'ram-mapped-source-audit'
            for name in ['ram-mapped-host',audit_name]:
                path=ROOT/'UniXNU-raphael/evidence'/(name+'.json');gate=json.loads(path.read_text())
                assert gate['passed'] and gate['decoder_sha256']==sha((ROOT/'scripts/ram_mapped_probe.py').read_bytes())
                for item in gate['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
                if name.endswith('host'):assert gate['case_count']>=74 and gate['undefined_behavior_sanitizer'] and gate['guard_canaries_verified']
                else:
                    selected=gate['qemu_reports'][str(args.stop_after_stage)]
                    assert selected['path']==str(qemu_path.relative_to(ROOT)) and selected['sha256']==sha(qemu_path.read_bytes())
                    assert gate['fatal_mapped_load_udf_return_verified'] and gate['mapped_load']['no_store_through_candidate']
                    if args.ram_cache_write_pages:
                        assert gate['ram_cache_write_pages']==args.ram_cache_write_pages and gate['partial_cached_write_udf_recovery_verified']
                        assert gate['cache_decoder_sha256']==qemu['ram_cache_decoder_sha256']==sha((ROOT/'scripts/ram_cache_write.py').read_bytes())
                gates[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
            assert qemu['executions']['normal']['ram_mapped']['passed']
            if args.ram_cache_write_pages:
                name='ram-cache-host';path=ROOT/'UniXNU-raphael/evidence'/(name+'.json');host=json.loads(path.read_text())
                assert host['passed'] and host['case_count']>=44 and host['address_sanitizer'] and host['undefined_behavior_sanitizer'] and host['separate_cache_and_dram_model']
                for item in host['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
                assert host['decoder_sha256']==sha((ROOT/'scripts/ram_cache_write.py').read_bytes())
                gates[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
                assert qemu['executions']['normal']['ram_cache']['passed']
        else:assert qemu['executions']['load_site_udf']['passed']
        if args.ram_write_pages:
            from ram_write_probe import verify_storage
            for name in ['ram-write-host','ram-write-source-audit']:
                path=ROOT/'UniXNU-raphael/evidence'/(name+'.json');gate=json.loads(path.read_text());assert gate['passed']
                for i in gate['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
                assert gate['decoder_sha256']==qemu['ram_write_decoder_sha256']==sha((ROOT/'scripts/ram_write_probe.py').read_bytes())
                if name.endswith('host'):assert gate['case_count']>=43 and gate['wire_case_count']>=25 and gate['address_sanitizer'] and gate['undefined_behavior_sanitizer']
                else:
                    assert gate['qemu_report']==str(qemu_path.relative_to(ROOT)) and gate['qemu_report_sha256']==sha(qemu_path.read_bytes())
                    assert gate['partial_page_udf_recovery_verified'] and gate['store']['single_64bit_store_only']
                gates[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
            assert qemu['executions']['normal']['ram_write']['passed'] and qemu['executions']['partial_write_udf']['ram_write']['passed']
            verify_storage(qemu_path.parent)
        ram_probe['gates']=gates
    manager_evidence=None
    if args.payload_test:
        ap=ROOT/'UniXNU-raphael/evidence/payload-source-audit.json'
        hp=ROOT/'UniXNU-raphael/evidence/manager-host.json'
        audit,host=[json.loads(p.read_text()) for p in [ap,hp]]
        assert audit['passed'] and host['passed']
        for item in audit['primary_sources']:
            assert sha((ROOT/item['repository']/item['path']).read_bytes())==item['sha256']
        for item in host['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        final=ROOT/host['qemu_report'];assert sha(final.read_bytes())==host['qemu_report_sha256']
        assert json.loads(final.read_text())['source_inputs']==qemu['source_inputs']
        assert host['decoder_sha256']==qemu['manager_decoder_sha256']==sha((ROOT/'scripts/manager_probe.py').read_bytes())
        assert qemu['executions']['normal']['manager']['passed']
        manager_evidence=dict(audit=str(ap.relative_to(ROOT)),audit_sha256=sha(ap.read_bytes()),host=str(hp.relative_to(ROOT)),host_sha256=sha(hp.read_bytes()))
    gic_evidence = None
    if args.gic_probe:
        from gic_probe import recipe as gic_recipe
        audit_path=ROOT/'UniXNU-raphael/evidence/gic-probe-source-audit.json'
        host_path=ROOT/'UniXNU-raphael/evidence/gic-probe-host.json'
        audit,host=[json.loads(p.read_text()) for p in [audit_path,host_path]]
        assert audit['passed'] and audit['wire_version']==1 and not audit['mmio_write_callback']
        assert host['passed'] and host['case_count']>=55
        for item in host['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/'scripts/gic_probe.py').read_bytes())==audit['decoder_sha256']==host['decoder_sha256']
        assert sha((ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/GicProbe.c').read_bytes())==audit['source_sha256']
        assert gic_recipe((args.collection/'live.dtb').read_bytes())==audit['recipe']
        assert qemu['executions']['normal']['gic']['passed']
        gic_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),
                          host_test=str(host_path.relative_to(ROOT)),host_test_sha256=sha(host_path.read_bytes()))
    icc_evidence = None
    if args.icc_probe:
        audit_path=ROOT/'UniXNU-raphael/evidence/icc-probe-source-audit.json'
        host_path=ROOT/'UniXNU-raphael/evidence/icc-probe-host.json'
        audit,host=[json.loads(p.read_text()) for p in [audit_path,host_path]]
        assert audit['passed'] and audit['register_read_site_count']==16 and not audit['cpu_register_writes_in_reader']
        assert host['passed'] and host['case_count']>=59 and host['snapshot_bytes']==208
        for item in host['source_inputs']+audit['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/'scripts/icc_probe.py').read_bytes())==host['decoder_sha256']==audit['decoder_sha256']
        assert str(qemu_path.relative_to(ROOT))==audit['qemu_report'] and sha(qemu_path.read_bytes())==audit['qemu_report_sha256']
        assert qemu['executions']['normal']['icc']['passed'] and not qemu['icc_fault_test']
        icc_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),
                          host_test=str(host_path.relative_to(ROOT)),host_test_sha256=sha(host_path.read_bytes()))
    physical_timer_evidence=None
    if args.physical_timer_arch:
        from physical_timer import verify_result_storage
        hp=ROOT/'UniXNU-raphael/evidence/physical-timer-host.json'
        ap=ROOT/'UniXNU-raphael/evidence/physical-timer-source-audit.json'
        host,audit=[json.loads(p.read_text()) for p in [hp,ap]]
        assert host['passed'] and audit['passed']
        for item in host['source_inputs']+audit['source_inputs']:
            assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert host['decoder_sha256']==audit['decoder_sha256']==qemu['physical_timer_decoder_sha256']==sha((ROOT/'scripts/physical_timer.py').read_bytes())
        for meta in [host,audit]:
            final=ROOT/meta['qemu_report'];assert sha(final.read_bytes())==meta['qemu_report_sha256']
            assert json.loads(final.read_text())['source_inputs']==qemu['source_inputs']
        assert qemu['executions']['normal']['physical_timer']['passed']
        verify_result_storage(qemu_path.parent)
        physical_timer_evidence=dict(host=str(hp.relative_to(ROOT)),host_sha256=sha(hp.read_bytes()),audit=str(ap.relative_to(ROOT)),audit_sha256=sha(ap.read_bytes()))
    timer_irq_evidence=None
    if args.timer_irq_test:
        audit_path=ROOT/'UniXNU-raphael/evidence/timer-irq-source-audit.json'
        host_path=ROOT/'UniXNU-raphael/evidence/timer-irq-host.json'
        audit,host=[json.loads(p.read_text()) for p in [audit_path,host_path]]
        assert audit['passed'] and audit['stack_spill_bytes']==80 and audit['eoi_mode_zero_only']
        assert host['passed'] and host['case_count']>=32 and host['wire_bytes']==192 and host['actual_c_offset_assertions']==25
        for item in host['source_inputs']+audit['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/'scripts/timer_irq.py').read_bytes())==host['decoder_sha256']==audit['decoder_sha256']==qemu['timer_irq_decoder_sha256']
        assert str(qemu_path.relative_to(ROOT))==audit['qemu_report']==host['qemu_report'] and sha(qemu_path.read_bytes())==audit['qemu_report_sha256']==host['qemu_report_sha256']
        assert qemu['executions']['normal']['timer_irq']['single_irq_handler_verified']
        timer_irq_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),host_test=str(host_path.relative_to(ROOT)),host_test_sha256=sha(host_path.read_bytes()))
    timer_route_evidence=None
    if args.timer_route_test:
        audit_path=ROOT/'UniXNU-raphael/evidence/timer-route-source-audit.json'
        host_path=ROOT/'UniXNU-raphael/evidence/timer-route-host.json'
        audit,host=[json.loads(p.read_text()) for p in [audit_path,host_path]]
        assert audit['passed'] and audit['cpu_irq_mask_preserved'] and not audit['acknowledge_register_access']
        assert host['passed'] and host['case_count']>=101 and host['snapshot_bytes']==352
        for item in host['source_inputs']+audit['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/'scripts/timer_route.py').read_bytes())==host['decoder_sha256']==audit['decoder_sha256']==qemu['timer_route_decoder_sha256']
        assert str(qemu_path.relative_to(ROOT))==audit['qemu_report'] and sha(qemu_path.read_bytes())==audit['qemu_report_sha256']
        fault_path=ROOT/audit['fault_qemu_report'];assert sha(fault_path.read_bytes())==audit['fault_qemu_report_sha256']
        fault=json.loads(fault_path.read_text());assert fault['qemu_passed'] and fault['timer_route_fault_test'] and fault['source_inputs']==qemu['source_inputs']
        assert qemu['executions']['normal']['timer_route']['physical_timer_route_observed']
        timer_route_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),host_test=str(host_path.relative_to(ROOT)),host_test_sha256=sha(host_path.read_bytes()))
    gic_enable_map_evidence=None
    if args.gic_enable_map:
        audit_path=ROOT/'UniXNU-raphael/evidence/gic-enable-map-source-audit.json'
        host_path=ROOT/'UniXNU-raphael/evidence/gic-enable-map-host.json'
        audit,host=[json.loads(p.read_text()) for p in [audit_path,host_path]]
        assert audit['passed'] and not audit['mmio_write_callback']
        assert host['passed'] and host['case_count']>=60 and host['snapshot_bytes']==480
        for item in host['source_inputs']+audit['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/'scripts/gic_enable_map.py').read_bytes())==host['decoder_sha256']==audit['decoder_sha256']==qemu['gic_enable_map_decoder_sha256']
        assert str(qemu_path.relative_to(ROOT))==audit['qemu_report'] and sha(qemu_path.read_bytes())==audit['qemu_report_sha256']
        assert qemu['executions']['normal']['gic_enable_map']['passed']
        gic_enable_map_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),host_test=str(host_path.relative_to(ROOT)),host_test_sha256=sha(host_path.read_bytes()))
    ppi_evidence=None
    if args.ppi_enable_probe:
        from ppi_probe import resource
        audit_path=ROOT/'UniXNU-raphael/evidence/ppi-probe-source-audit.json';host_path=ROOT/'UniXNU-raphael/evidence/ppi-probe-host.json'
        audit,host=[json.loads(p.read_text()) for p in [audit_path,host_path]]
        assert audit['passed'] and audit['permitted_write_offsets']==[0x100,0x180] and audit['write_one_mask_only']
        assert host['passed'] and host['case_count']>=94 and host['snapshot_bytes']==160
        for item in host['source_inputs']+audit['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/'scripts/ppi_probe.py').read_bytes())==host['decoder_sha256']==audit['decoder_sha256']==qemu['ppi_decoder_sha256']
        assert str(qemu_path.relative_to(ROOT))==audit['qemu_report'] and sha(qemu_path.read_bytes())==audit['qemu_report_sha256']
        assert resource((args.collection/'live.dtb').read_bytes())==(audit['timer_intid'],audit['timer_flags'])
        assert qemu['executions']['normal']['ppi']['passed']
        ppi_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),host_test=str(host_path.relative_to(ROOT)),host_test_sha256=sha(host_path.read_bytes()))
    timer_source_evidence=None
    if args.timer_source_test:
        audit_path=ROOT/'UniXNU-raphael/evidence/timer-source-audit.json'
        host_path=ROOT/'UniXNU-raphael/evidence/timer-source-host.json'
        audit,host=[json.loads(p.read_text()) for p in [audit_path,host_path]]
        assert audit['passed'] and audit['physical_timer_msr_count']==2 and audit['recovery_site_count']==3
        assert host['passed'] and host['case_count']>=82 and host['snapshot_bytes']==136
        for item in host['source_inputs']+audit['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/'scripts/timer_source.py').read_bytes())==host['decoder_sha256']==audit['decoder_sha256']
        assert str(qemu_path.relative_to(ROOT))==audit['qemu_report'] and sha(qemu_path.read_bytes())==audit['qemu_report_sha256']
        fault_path=ROOT/audit['fault_qemu_report'];assert sha(fault_path.read_bytes())==audit['fault_qemu_report_sha256']
        fault=json.loads(fault_path.read_text())
        assert fault['qemu_passed'] and fault['timer_source_test'] and fault['icc_fault_test'] and fault['source_inputs']==qemu['source_inputs']
        assert qemu['executions']['normal']['timer_source']['passed']
        timer_source_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),host_test=str(host_path.relative_to(ROOT)),host_test_sha256=sha(host_path.read_bytes()))
    display_evidence = None
    if args.display_probe:
        audit_path = ROOT / 'UniXNU-raphael/evidence/display-source-audit.json'
        audit = json.loads(audit_path.read_text())
        assert audit['passed'] and audit['wire_version'] == 3 and not audit['private_modules_linked']
        test_path = ROOT / 'UniXNU-raphael/evidence/display-probe-host.json'
        tests = json.loads(test_path.read_text())
        assert tests['passed'] and tests['case_count'] >= 44
        for item in tests['source_inputs']:
            assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
        assert audit['fdt_sha256'] == sha((args.collection / 'live.dtb').read_bytes())
        display_evidence = dict(audit=str(audit_path.relative_to(ROOT)), audit_sha256=sha(audit_path.read_bytes()),
                                host_test=str(test_path.relative_to(ROOT)), host_test_sha256=sha(test_path.read_bytes()))
    smmu_evidence = None
    if args.smmu_probe:
        audit_path = ROOT / 'UniXNU-raphael/evidence/smmu-source-audit.json'
        test_path = ROOT / 'UniXNU-raphael/evidence/smmu-probe-host.json'
        audit, tests = map(lambda p: json.loads(p.read_text()), [audit_path, test_path])
        assert audit['passed'] and audit['wire_version'] == 4
        assert tests['passed'] and tests['case_count'] >= 20
        for item in tests['source_inputs']:
            assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
        assert audit['fdt_sha256'] == sha((args.collection / 'live.dtb').read_bytes())
        smmu_evidence = dict(audit=str(audit_path.relative_to(ROOT)), audit_sha256=sha(audit_path.read_bytes()),
                             host_test=str(test_path.relative_to(ROOT)), host_test_sha256=sha(test_path.read_bytes()))
    pixel_evidence = None
    if args.pixel_probe:
        audit_path=ROOT/'UniXNU-raphael/evidence/pixel-source-audit.json'
        test_path=ROOT/'UniXNU-raphael/evidence/pixel-probe-host.json'
        audit,tests=[json.loads(p.read_text()) for p in [audit_path,test_path]]
        assert audit['passed'] and tests['passed'] and tests['case_count']>=22
        for item in tests['source_inputs']:
            assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert audit['fdt_sha256']==sha((args.collection/'live.dtb').read_bytes())
        pixel_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),
                            host_test=str(test_path.relative_to(ROOT)),host_test_sha256=sha(test_path.read_bytes()))
    write_evidence=None
    if args.pixel_write:
        test_path=ROOT/'UniXNU-raphael/evidence/pixel-write-host.json'
        tests=json.loads(test_path.read_text());assert tests['passed'] and tests['case_count']>=14
        for item in tests['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        prior=ROOT/'UniXNU-raphael/evidence/boot-pixel-observation.json'
        observed=json.loads(prior.read_text());assert observed['cpu_sample_read_verified']
        write_evidence=dict(host_test=str(test_path.relative_to(ROOT)),host_test_sha256=sha(test_path.read_bytes()),
                            prior_cpu_observation=str(prior.relative_to(ROOT)),prior_cpu_observation_sha256=sha(prior.read_bytes()))
    gop_evidence=None
    if args.experimental_gop:
        host=ROOT/'UniXNU-raphael/evidence/gop-host.json'
        tested=json.loads(host.read_text());assert tested['passed']
        for item in tested['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        audit=ROOT/'UniXNU-raphael/evidence/gop-source-audit.json'
        audited=json.loads(audit.read_text());assert audited['passed'] and not audited['private_modules_linked']
        route=ROOT/'UniXNU-raphael/evidence/gop-route-host.json'
        route_test=json.loads(route.read_text());assert route_test['passed']
        for item in route_test['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        prior=ROOT/'UniXNU-raphael/evidence/boot-pixel-write-observation.json'
        visible=json.loads(prior.read_text());assert visible['human_observation']['visible_output_verified']
        gop_evidence=dict(host_test=str(host.relative_to(ROOT)),host_test_sha256=sha(host.read_bytes()),
                          visible_sec_output=str(prior.relative_to(ROOT)),visible_sec_output_sha256=sha(prior.read_bytes()),
                          route_test=str(route.relative_to(ROOT)),route_test_sha256=sha(route.read_bytes()),
                          source_audit=str(audit.relative_to(ROOT)),source_audit_sha256=sha(audit.read_bytes()))
    input_evidence=None
    if args.input_probe:
        audit_path=ROOT/'UniXNU-raphael/evidence/input-source-audit.json'
        test_path=ROOT/'UniXNU-raphael/evidence/input-probe-host.json'
        audit,tests=[json.loads(p.read_text()) for p in [audit_path,test_path]]
        assert audit['passed'] and tests['passed'] and tests['case_count']>=40
        for item in tests['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert audit['fdt_sha256']==sha((args.collection/'live.dtb').read_bytes())
        input_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),
                            host_test=str(test_path.relative_to(ROOT)),host_test_sha256=sha(test_path.read_bytes()))
    key_read_evidence=None
    if args.input_read:
        audit_path=ROOT/'UniXNU-raphael/evidence/key-read-source-audit.json'
        test_path=ROOT/'UniXNU-raphael/evidence/key-read-host.json'
        audit,tests=[json.loads(p.read_text()) for p in [audit_path,test_path]]
        assert audit['passed'] and tests['passed'] and tests['case_count']>=39
        for item in tests['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        assert sha((ROOT/audit['prerequisite']).read_bytes())==audit['prerequisite_sha256']
        key_read_evidence=dict(audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),
                              host_test=str(test_path.relative_to(ROOT)),host_test_sha256=sha(test_path.read_bytes()))
    input_dxe_evidence=None
    if args.input_protocol:
        host=ROOT/'UniXNU-raphael/evidence/input-dxe-host.json';tests=json.loads(host.read_text())
        assert tests['passed'] and tests['case_count']>=26
        for item in tests['source_inputs']:assert sha((ROOT/item['path']).read_bytes())==item['sha256']
        prior=ROOT/'UniXNU-raphael/evidence/boot-key-register-observation.json'
        observed=json.loads(prior.read_text());assert observed['key_registers']['gpio_input_configuration_verified']
        input_dxe_evidence=dict(host_test=str(host.relative_to(ROOT)),host_test_sha256=sha(host.read_bytes()),
            prior_registers=str(prior.relative_to(ROOT)),prior_registers_sha256=sha(prior.read_bytes()))
    menu_evidence=None
    if args.menu_test:
        paths=sorted((ROOT/'artifacts/menu-fixture-qemu').glob('*/report.json'))
        fixture_path=next(p for p in reversed(paths) if json.loads(p.read_text()).get('passed'))
        fixture=json.loads(fixture_path.read_text())
        assert fixture['source_inputs']==qemu['source_inputs'] and fixture['upstream_inputs']==qemu['upstream_inputs']
        audit_path=ROOT/'UniXNU-raphael/evidence/menu-source-audit.json'
        audit=json.loads(audit_path.read_text());assert audit['passed'] and audit['generic_renderer_unmodified']
        for item in audit['primary_sources']:
            assert sha((ROOT/'sources/UniXNU'/item['path']).read_bytes())==item['sha256']
        assert len(audit['positive_fixtures'])==2
        for item in audit['positive_fixtures']:
            p=ROOT/item['path'];assert sha(p.read_bytes())==item['sha256']
            f=json.loads(p.read_text());assert f['passed'] and f['screenshot_captured']
            assert f['source_inputs']==qemu['source_inputs'] and f['upstream_inputs']==qemu['upstream_inputs']
        menu_evidence=dict(qemu_positive_renderer=str(fixture_path.relative_to(ROOT)),qemu_positive_renderer_sha256=sha(fixture_path.read_bytes()),
                           source_audit=str(audit_path.relative_to(ROOT)),source_audit_sha256=sha(audit_path.read_bytes()))
    prerequisites = []
    for stage in range(2, args.stop_after_stage):
        path = ROOT / f'UniXNU-raphael/evidence/sec-ram-cache-pages{args.ram_cache_write_pages}-stage{stage}-handoff.json' if args.ram_cache_write_pages else ROOT / f'UniXNU-raphael/evidence/sec-ram-mapped-stage{stage}-handoff.json' if args.ram_mapped_probe else ROOT / f'UniXNU-raphael/evidence/sec-darwin-stage{stage}-handoff.json' if args.darwin_test else ROOT / f'UniXNU-raphael/evidence/sec-manager-keys-stage{stage}-handoff.json' if args.manager_keys else ROOT / f'UniXNU-raphael/evidence/sec-visible-manager-stage{stage}-handoff.json' if args.visible_manager else ROOT / f'UniXNU-raphael/evidence/sec-manager-stage{stage}-handoff.json' if args.payload_test else ROOT / f'UniXNU-raphael/evidence/sec-physical-timer-stage{stage}-handoff.json' if args.physical_timer_arch else ROOT / f'UniXNU-raphael/evidence/sec-menu-stage{stage}-handoff.json' if args.menu_test else ROOT / f'UniXNU-raphael/evidence/sec-inputdxe-stage{stage}-handoff.json' if args.input_protocol else ROOT / f'UniXNU-raphael/evidence/sec-keyread-stage{stage}-handoff.json' if args.input_read else ROOT / f'UniXNU-raphael/evidence/sec-input-stage{stage}-handoff.json' if args.input_probe else ROOT / f'UniXNU-raphael/evidence/sec-gop-stage{stage}-handoff.json' if args.experimental_gop else ROOT / f'UniXNU-raphael/evidence/sec-stage{stage}-handoff.json'
        passed = json.loads(path.read_text())
        assert passed['firmware_checkpoint_passed'] and passed['sec_dxe_stage_verified'] == stage
        assert passed['nonce_matched'] and passed['root_verified'] and passed['boot_partition_unchanged']
        earlier = json.loads((ROOT / passed['private_build'] / 'report.json').read_text())
        assert earlier.get('upstream_inputs',[])==qemu.get('upstream_inputs',[]), 'Generic source changed; repeat earlier stage'
        assert earlier['source_inputs'] == qemu['source_inputs'] and earlier.get('darwin_inputs',[])==qemu.get('darwin_inputs',[]), 'Retest earlier stage after changing firmware sources'
        prerequisites.append(dict(stage=stage, evidence=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes())))
    extent_path = ROOT / 'UniXNU-raphael/evidence/extent-download.json'
    extent = json.loads(extent_path.read_text())
    assert all(extent[k] for k in ['fastboot_boot_accepted', 'android_boot_completed', 'nonce_matched',
                                  'root_verified', 'boot_partition_unchanged', 'candidate_extent_download_test'])
    plan_path = ROOT / 'UniXNU-raphael/evidence/memory-plan-check.json'
    plan = json.loads(plan_path.read_text())
    assert plan['passed'] and not plan['boot_enabled']
    assert plan['requested_image_size'] == extent['downloaded_arm64_image_bytes']
    entry = extent['entry']
    assert entry['current_el'] == 4 and entry['sctlr'] & 0x1005 == 0
    assert entry['image_base'] == plan['requested_image_base']
    boot = read_boot(args.collection.resolve())
    p = image_parameters(boot['image'])
    assert p['image_size'] == entry['original_image_size'] and p['entry'] == entry['original_entry_offset']
    bridge, fd, stack, arena, fdt = plan['regions']
    values = dict(ImageBase=entry['image_base'], ImageSize=p['image_size'], OriginalEntry=p['entry'],
                  OriginalInstruction=p['instruction'], ExtentBase=bridge['base'],
                  ExtentEnd=plan['requested_image_end'], FdBase=fd['base'], FdSize=fd['length'],
                  StackBase=stack['base'], StackSize=stack['length'], ArenaBase=arena['base'],
                  ArenaSize=arena['length'], FdtBase=fdt['base'], FdtSize=fdt['length'], ContextBase=bridge['base'])
    out = ROOT / 'evidence/private/sec-dxe-build' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    if darwin_refusal_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for item in darwin_refusal_evidence.values():
            saved=out/'evidence-inputs'/Path(item['path']).name;saved.write_bytes((ROOT/item['path']).read_bytes());item['snapshot']=str(saved.relative_to(ROOT))
    if manager_ui_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for item in manager_ui_evidence.values():
            saved=out/'evidence-inputs'/Path(item['path']).name
            saved.write_bytes((ROOT/item['path']).read_bytes());item['snapshot']=str(saved.relative_to(ROOT))
    if manager_keys_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for item in manager_keys_evidence.values():
            saved=out/'evidence-inputs'/Path(item['path']).name;saved.write_bytes((ROOT/item['path']).read_bytes());item['snapshot']=str(saved.relative_to(ROOT))
    if ram_probe:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for item in ram_probe['sources']+list(ram_probe['gates'].values()):
            saved=out/'evidence-inputs'/Path(item['path']).name
            assert not saved.exists()
            saved.write_bytes((ROOT/item['path']).read_bytes());item['snapshot']=str(saved.relative_to(ROOT))
    if gic_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(gic_evidence[name]).name
            saved.write_bytes((ROOT/gic_evidence[name]).read_bytes())
            gic_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if manager_evidence:
        for name in ['host','audit']:
            saved=out/'evidence-inputs'/Path(manager_evidence[name]).name
            saved.parent.mkdir(parents=True,exist_ok=True)
            saved.write_bytes((ROOT/manager_evidence[name]).read_bytes())
            manager_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if physical_timer_evidence:
        for name in ['host','audit']:
            saved=out/'evidence-inputs'/Path(physical_timer_evidence[name]).name
            saved.parent.mkdir(parents=True,exist_ok=True)
            saved.write_bytes((ROOT/physical_timer_evidence[name]).read_bytes())
            physical_timer_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if timer_irq_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(timer_irq_evidence[name]).name
            saved.write_bytes((ROOT/timer_irq_evidence[name]).read_bytes())
            timer_irq_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if timer_route_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(timer_route_evidence[name]).name
            saved.write_bytes((ROOT/timer_route_evidence[name]).read_bytes())
            timer_route_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if gic_enable_map_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(gic_enable_map_evidence[name]).name
            saved.write_bytes((ROOT/gic_enable_map_evidence[name]).read_bytes())
            gic_enable_map_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if ppi_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(ppi_evidence[name]).name
            saved.write_bytes((ROOT/ppi_evidence[name]).read_bytes())
            ppi_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if timer_source_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(timer_source_evidence[name]).name
            saved.write_bytes((ROOT/timer_source_evidence[name]).read_bytes())
            timer_source_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if icc_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(icc_evidence[name]).name
            saved.write_bytes((ROOT/icc_evidence[name]).read_bytes())
            icc_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if display_evidence:
        snapshots = out / 'evidence-inputs'
        snapshots.mkdir(exist_ok=True)
        for name in ['audit', 'host_test']:
            content = (ROOT / display_evidence[name]).read_bytes()
            assert sha(content) == display_evidence[name + '_sha256']
            saved = snapshots / Path(display_evidence[name]).name
            saved.write_bytes(content)
            display_evidence[name + '_snapshot'] = str(saved.relative_to(ROOT))
    if smmu_evidence:
        for name in ['audit', 'host_test']:
            content = (ROOT / smmu_evidence[name]).read_bytes()
            assert sha(content) == smmu_evidence[name + '_sha256']
            saved = out / 'evidence-inputs' / Path(smmu_evidence[name]).name
            saved.write_bytes(content)
            smmu_evidence[name + '_snapshot'] = str(saved.relative_to(ROOT))
    if pixel_evidence:
        for name in ['audit','host_test']:
            content=(ROOT/pixel_evidence[name]).read_bytes()
            saved=out/'evidence-inputs'/Path(pixel_evidence[name]).name
            saved.write_bytes(content);pixel_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if write_evidence:
        for name in ['host_test','prior_cpu_observation']:
            saved=out/'evidence-inputs'/Path(write_evidence[name]).name
            saved.write_bytes((ROOT/write_evidence[name]).read_bytes())
            write_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if gop_evidence:
        for name in ['host_test','visible_sec_output','route_test','source_audit']:
            saved=out/'evidence-inputs'/Path(gop_evidence[name]).name
            saved.write_bytes((ROOT/gop_evidence[name]).read_bytes())
            gop_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if input_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            content=(ROOT/input_evidence[name]).read_bytes()
            saved=out/'evidence-inputs'/Path(input_evidence[name]).name
            saved.write_bytes(content);input_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if key_read_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['audit','host_test']:
            saved=out/'evidence-inputs'/Path(key_read_evidence[name]).name
            saved.write_bytes((ROOT/key_read_evidence[name]).read_bytes())
            key_read_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    if input_dxe_evidence:
        (out/'evidence-inputs').mkdir(exist_ok=True)
        for name in ['host_test','prior_registers']:
            saved=out/'evidence-inputs'/Path(input_dxe_evidence[name]).name
            saved.write_bytes((ROOT/input_dxe_evidence[name]).read_bytes())
            input_dxe_evidence[name+'_snapshot']=str(saved.relative_to(ROOT))
    identifier = 'raphael-sec-dxe-v1-' + uuid.uuid4().hex
    raw, report = build_firmware(out, values, identifier, 'private handset diagnostic; RAM-only test', args.stop_after_stage, args.display_probe, args.smmu_probe, args.pixel_probe, args.pixel_write, args.experimental_gop, args.input_probe, args.input_read, args.input_protocol, args.menu_test, gic_probe=args.gic_probe, icc_probe=args.icc_probe, timer_source_test=args.timer_source_test, ppi_enable_probe=args.ppi_enable_probe, gic_enable_map=args.gic_enable_map, timer_route_test=args.timer_route_test, timer_irq_test=args.timer_irq_test, physical_timer_arch=args.physical_timer_arch, payload_test=args.payload_test, darwin_test=args.darwin_test, ram_probe=ram_probe, visible_manager=args.visible_manager, manager_keys=args.manager_keys, ram_write_pages=args.ram_write_pages, ram_mapped_probe=args.ram_mapped_probe, ram_cache_write_pages=args.ram_cache_write_pages)
    report['darwin_refusal_evidence']=darwin_refusal_evidence
    if args.darwin_test:
        import struct,subprocess
        invalid=struct.pack('<10I',0xfeedfacf,0x100000c,0,2,1,8,0,0,0x19,72)
        extracted=subprocess.check_output(['mtype','-i',str(out/'diagnostic-payload.img'),'::/EFI/UniXNU/invalid.macho'])
        assert extracted==invalid and len(invalid)==40
        report['invalid_kernel_fixture']=dict(bytes=40,sha256=sha(invalid),load_command_bytes=8,required_segment_command_bytes=72,valid_kernel=False)
    structure = inspect_fd(raw, fd['base'])
    (out / 'fd-inspection.json').write_text(json.dumps(structure, indent=2) + '\n')
    if args.ram_cache_write_pages:
        from ram_cache_write import verify_storage
        from audit_ram_cache import inspect_cached_write
        report['ram_cache_storage']=verify_storage(out)
        report['ram_cache_store_audit']=inspect_cached_write(out)
        from audit_ram_cache import inspect_cache
        report['ram_cache_instruction_audit']=inspect_cache(out)
    if args.ram_mapped_probe:
        from ram_mapped_probe import verify_storage
        from audit_ram_read import inspect_load
        report['ram_mapped_storage']=verify_storage(out)
        report['ram_mapped_load_audit']=inspect_load(out,function='ReadMappedRam64')
    manager_ui_result_storage=None
    if args.visible_manager:
        from manager_ui import verify_result_storage
        manager_ui_result_storage=verify_result_storage(out)
    ram_result_storage=None
    ram_load_audit=None
    if ram_probe:
        from ram_read_probe import verify_result_storage
        from audit_ram_read import inspect_load
        ram_result_storage=verify_result_storage(out);ram_load_audit=inspect_load(out)
        asset=next(s['ram_read_policy'] for f in structure['files'] for s in f['sections'] if 'ram_read_policy' in s)
        assert asset==ram_probe['policy']
    ram_write_storage=None;ram_store_audit=None
    if args.ram_write_pages:
        from ram_write_probe import verify_storage
        from audit_ram_write import inspect_write
        ram_write_storage=verify_storage(out);ram_store_audit=inspect_write(out)
    physical_timer_result_storage=None
    if args.physical_timer_arch:
        from physical_timer import verify_result_storage
        physical_timer_result_storage=verify_result_storage(out)
    timer_irq_result_storage=None
    if args.timer_irq_test:
        from timer_irq import verify_result_storage
        timer_irq_result_storage=verify_result_storage(out)
    timer_route_result_storage=None
    if args.timer_route_test:
        from timer_route import verify_result_storage
        timer_route_result_storage=verify_result_storage(out)
    gic_enable_map_result_storage=None
    if args.gic_enable_map:
        from gic_enable_map import verify_result_storage
        gic_enable_map_result_storage=verify_result_storage(out)
    ppi_result_storage=None
    if args.ppi_enable_probe:
        from ppi_probe import verify_result_storage
        ppi_result_storage=verify_result_storage(out)
    # FV's ARM64 reset branch enters our SEC. The old kernel stays in place.
    parameters = dict(p, probe_offset=fd['base'] - entry['image_base'])
    payload = raw + bytes(plan['requested_image_end'] - fd['base'] - len(raw))
    image = instrument(boot['image'], payload, parameters)
    assert len(image) == plan['requested_image_size']
    packed = repack(boot, image)
    (out / 'boot-sec-dxe.img').write_bytes(packed)
    (out / 'layout.json').write_text(json.dumps(values, indent=2) + '\n')
    report.update(identifier=identifier, image_sha256=sha(packed), image_bytes=len(packed),
                  firmware_sha256=sha(raw), firmware_bytes=len(raw), layout=values,
                  structure_checked=True, source_sha256=sha(boot['raw']),
                  unchanged_original_kernel_sha256=sha(boot['image']),
                  unchanged_ramdisk_sha256=sha(boot['ramdisk']), unchanged_dtbs=boot['dtbs'],
                  qemu_evidence=str(qemu_path.relative_to(ROOT)),
                  prior_handset_checkpoints=prerequisites, ram_write_storage=ram_write_storage, ram_store_audit=ram_store_audit, manager_keys_evidence=manager_keys_evidence, manager_keys_decoder_sha256=sha((ROOT/'scripts/manager_keys.py').read_bytes()), manager_ui_evidence=manager_ui_evidence, manager_ui_result_storage=manager_ui_result_storage, ram_result_storage=ram_result_storage, ram_load_audit=ram_load_audit, manager_evidence=manager_evidence, physical_timer_evidence=physical_timer_evidence, physical_timer_result_storage=physical_timer_result_storage, timer_irq_evidence=timer_irq_evidence, timer_irq_result_storage=timer_irq_result_storage, timer_route_evidence=timer_route_evidence, timer_route_result_storage=timer_route_result_storage, gic_enable_map_evidence=gic_enable_map_evidence, gic_enable_map_result_storage=gic_enable_map_result_storage, ppi_evidence=ppi_evidence, ppi_result_storage=ppi_result_storage, timer_source_evidence=timer_source_evidence, icc_evidence=icc_evidence, gic_evidence=gic_evidence, display_evidence=display_evidence, smmu_evidence=smmu_evidence, pixel_evidence=pixel_evidence, pixel_write_evidence=write_evidence, gop_evidence=gop_evidence, input_evidence=input_evidence, key_read_evidence=key_read_evidence, input_dxe_evidence=input_dxe_evidence, menu_evidence=menu_evidence,
                  extent_evidence_sha256=sha(extent_path.read_bytes()), plan_sha256=sha(plan_path.read_bytes()),
                  proprietary=True, publicly_redistributable=False,
                  original_kernel_relocated=False, avb_footer_copied=False,
                  handset_executed=False, full_uefi_platform=False,
                  limitations=['Inherited splash GOP is experimental when explicitly enabled; no keys, BDS, hardware interrupt/timer or storage drivers',
                               'Default whole-cache APIs are not used; enabled RAM cache diagnostics clean each tested candidate page explicitly',
                               'Extent acceptance is not proof of complete vendor memory ownership',
                               'Runtime live FDT, PC, Image, SP/LR and allocation geometry are checked before HOB/MMU/DXE'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['identifier', 'firmware_sha256', 'firmware_bytes',
                                           'image_sha256', 'image_bytes', 'structure_checked', 'handset_executed']}, indent=2))
    print(out)


if __name__ == '__main__':
    main()
