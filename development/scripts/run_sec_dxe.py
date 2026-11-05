#!/usr/bin/env python3
"""RAM-only handset SEC/DXE test; verify nonce, DXE results and Android return."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import struct
import subprocess
import time
from entry_probe import ROOT, sha
from inspect_device import read_fdt
from display_probe import decode as decode_display, recipe as display_recipe
from smmu_probe import recipe as smmu_recipe

ADB = '/mnt/d/Android/platform-tools/adb.exe'
FB = '/mnt/d/Android/platform-tools/fastboot.exe'
FIELDS = ['x0_fdt', 'x1', 'x2', 'x3', 'lr', 'sp', 'current_el', 'sctlr', 'daif',
          'cntfrq', 'counter', 'mpidr', 'vbar', 'tpidr', 'tcr', 'ttbr0', 'ttbr1', 'mair',
          'cpacr', 'image_base', 'original_image_size', 'original_entry', 'original_instruction',
          'fdt_copy', 'extent_base', 'extent_end', 'finish', 'stage', 'status', 'magic',
          'mmu_sctlr', 'page_table', 'page_table_root_bytes', 'esr', 'elr', 'far',
          'system_table_signature', 'boot_services_signature', 'system_table_crc_ok',
          'boot_services_crc_ok', 'map_key', 'map_bytes', 'descriptor_size', 'descriptor_version',
          'map_violations', 'allocation_probe_ok', 'log_bytes', 'log_dropped']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--historical-binding', type=Path, help='Verify an archived build against its recorded Git revision and snapshot')
    parser.add_argument('--preflight-only', action='store_true', help='Verify build provenance without contacting or rebooting the handset')
    args = parser.parse_args()
    build = args.build.resolve()
    assert build.is_relative_to(ROOT / 'evidence/private/sec-dxe-build')
    description = json.loads((build / 'report.json').read_text())
    expected_stage = {2:2,3:3,4:6}[description.get('stop_stage',4)]
    image = build / 'boot-sec-dxe.img'
    assert sha(image.read_bytes()) == description['image_sha256'] and description['structure_checked']
    if args.historical_binding:
        from sec_build_provenance import verify_archived_build
        provenance = verify_archived_build(build, description, args.historical_binding)
    else:
        for item in description['source_inputs']+description.get('upstream_inputs',[])+description.get('darwin_inputs',[]):
            assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
        provenance = dict(mode='current-worktree', reused_image=False)
    qemu = json.loads((ROOT / description['qemu_evidence']).read_text())
    assert qemu['qemu_passed'] and all(x['passed'] for x in qemu['executions'].values())
    if description.get('darwin_test'):
        for item in description['darwin_refusal_evidence'].values():assert sha((ROOT/item['snapshot']).read_bytes())==item['sha256']
        wire=json.loads((ROOT/description['darwin_refusal_evidence']['wire_host']['snapshot']).read_text())
        assert wire['passed'] and wire['decoder_sha256']==sha((ROOT/'scripts/darwin_probe.py').read_bytes())
        fixture=description['invalid_kernel_fixture'];assert fixture['bytes']==40 and not fixture['valid_kernel']
        invalid=subprocess.check_output(['mtype','-i',str(build/'diagnostic-payload.img'),'::/EFI/UniXNU/invalid.macho'])
        assert len(invalid)==40 and sha(invalid)==fixture['sha256'] and qemu['darwin_test']
    if description.get('ram_read_probe'):
        from ram_read_probe import verify_result_storage,policy
        from audit_ram_read import inspect_load
        metadata=description['ram_read_evidence']
        for item in metadata['sources']+list(metadata['gates'].values()):
            assert sha((ROOT/item['snapshot']).read_bytes())==item['sha256']
        assert policy((build/'ram-read-policy.bin').read_bytes())==metadata['policy']
        assert verify_result_storage(build)==description['ram_result_storage']
        assert inspect_load(build)==description['ram_load_audit']
        assert qemu['ram_read_probe'] and qemu['ram_read_decoder_sha256']==sha((ROOT/'scripts/ram_read_probe.py').read_bytes())
    if description.get('ram_cache_write_pages'):
        from ram_cache_write import verify_storage
        from audit_ram_cache import inspect_cached_write
        assert verify_storage(build)==description['ram_cache_storage']
        assert inspect_cached_write(build)==description['ram_cache_store_audit']
        from audit_ram_cache import inspect_cache
        assert inspect_cache(build)==description['ram_cache_instruction_audit']
        assert qemu['ram_cache_write_pages']==description['ram_cache_write_pages']
        assert qemu['ram_cache_decoder_sha256']==description['ram_cache_decoder_sha256']==sha((ROOT/'scripts/ram_cache_write.py').read_bytes())
    if description.get('ram_mapped_probe'):
        from ram_mapped_probe import verify_storage
        from audit_ram_read import inspect_load
        assert verify_storage(build)==description['ram_mapped_storage']
        assert inspect_load(build,function='ReadMappedRam64')==description['ram_mapped_load_audit']
        assert qemu['ram_mapped_probe'] and qemu['ram_mapped_decoder_sha256']==description['ram_mapped_decoder_sha256']==sha((ROOT/'scripts/ram_mapped_probe.py').read_bytes())
    if description.get('ram_write_pages'):
        from ram_write_probe import verify_storage
        from audit_ram_write import inspect_write
        assert verify_storage(build)==description['ram_write_storage'] and inspect_write(build)==description['ram_store_audit']
        assert qemu['ram_write_pages']==description['ram_write_pages']
        assert qemu['ram_write_decoder_sha256']==description['ram_write_decoder_sha256']==sha((ROOT/'scripts/ram_write_probe.py').read_bytes())
    if description.get('visible_manager'):
        from manager_ui import verify_result_storage
        assert verify_result_storage(build)==description['manager_ui_result_storage']
        for item in description['manager_ui_evidence'].values():assert sha((ROOT/item['snapshot']).read_bytes())==item['sha256']
        assert qemu['visible_manager'] and qemu['manager_ui_decoder_sha256']==sha((ROOT/'scripts/manager_ui.py').read_bytes())
    if description.get('manager_keys'):
        for item in description['manager_keys_evidence'].values():assert sha((ROOT/item['snapshot']).read_bytes())==item['sha256']
        assert qemu['manager_keys'] and description['manager_keys_decoder_sha256']==sha((ROOT/'scripts/manager_keys.py').read_bytes())
    if description.get('kernel_window'):
        from kernel_window import encode_policy
        assert (build/'kernel-window-policy.bin').read_bytes()==encode_policy(description['kernel_window'])
        assert sha((ROOT/description['qemu_evidence']).read_bytes())==description['qemu_evidence_sha256']
        assert qemu['allocation_verification']['passed'] and qemu['kernel_window']['virtual_base']==description['kernel_window']['virtual_base']
    if args.preflight_only:
        print(json.dumps(provenance, indent=2))
        return
    out = ROOT / 'evidence/private/sec-dxe-run' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    records = []
    started = time.monotonic()

    def publish_attempt(report):
        safe = dict(report, private_readback=str(out.relative_to(ROOT)),
                    private_build=str(build.relative_to(ROOT)),
                    started_utc=out.name, observation_seconds=round(time.monotonic() - started, 3))
        evidence = ROOT / 'UniXNU-raphael/evidence'
        # Keep each attempt, including failures. The short name is only an index
        # to the latest attempt; it must never be the sole failure record.
        immutable = evidence / f'sec-dxe-attempt-{out.name}.json'
        assert not immutable.exists()
        payload = json.dumps(safe, indent=2) + '\n'
        immutable.write_text(payload)
        (evidence / 'sec-dxe-attempt.json').write_text(payload)

    def run(tool, *arguments, timeout=15, save=None):
        command = [tool, '-s', args.serial, *arguments]
        try:
            result = subprocess.run(command, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            records.append(dict(command=command, timed_out=True))
            (out / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
            return None
        record = dict(command=command, returncode=result.returncode,
                      utc=dt.datetime.now(dt.timezone.utc).isoformat(), stderr=result.stderr.decode(errors='replace'))
        if save:
            (out / save).write_bytes(result.stdout)
            record.update(file=save, bytes=len(result.stdout), sha256=sha(result.stdout))
        else:
            record['stdout'] = result.stdout.decode(errors='replace')
        records.append(record)
        (out / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        return result

    def root(command, **options):
        return run(ADB, 'exec-out', 'su -c ' + shlex.quote(command), **options)

    result = root('sha256sum /dev/block/bootdevice/by-name/boot')
    assert result and result.returncode == 0 and result.stdout.decode().split()[0] == description['source_sha256']
    result = root('cat /sys/firmware/fdt', save='before.dtb')
    assert result and result.returncode == 0
    if description.get('display_probe'):
        display_audit = ROOT / description['display_evidence'].get('audit_snapshot', description['display_evidence']['audit'])
        assert sha(display_audit.read_bytes()) == description['display_evidence']['audit_sha256']
        assert display_recipe(result.stdout) == json.loads(display_audit.read_text())['recipe'], 'Live display resources differ from audited FDT'
    if description.get('smmu_probe'):
        metadata = description['smmu_evidence']
        smmu_audit = ROOT / metadata['audit_snapshot']
        assert sha(smmu_audit.read_bytes()) == metadata['audit_sha256']
        assert smmu_recipe(result.stdout) == json.loads(smmu_audit.read_text())['recipe']
    if description.get('input_probe'):
        from input_probe import recipe as input_recipe
        input_meta=description['input_evidence'];input_audit=ROOT/input_meta['audit_snapshot']
        assert sha(input_audit.read_bytes())==input_meta['audit_sha256']
        assert input_recipe(result.stdout)==json.loads(input_audit.read_text())['recipe']
    if description.get('gic_probe'):
        from gic_probe import recipe as gic_recipe
        gic_meta=description['gic_evidence'];gic_audit=ROOT/gic_meta['audit_snapshot']
        assert sha(gic_audit.read_bytes())==gic_meta['audit_sha256']
        assert gic_recipe(result.stdout)==json.loads(gic_audit.read_text())['recipe']
    before_tree = read_fdt(result.stdout)
    chosen = next(n for n in before_tree.walk() if n.name == 'chosen' and n.parent is before_tree)
    assert not any(k.startswith(('raphael,darwin-', 'raphael,entry-probe', 'raphael,sec-dxe', 'raphael,display-', 'raphael,input-', 'raphael,payload-', 'raphael,gic-', 'raphael,icc-', 'raphael,timer-', 'raphael,physical-timer-', 'raphael,manager-', 'raphael,ppi-', 'raphael,ram-')) for k in chosen.properties)
    assert run(ADB, 'reboot', 'bootloader').returncode == 0
    ready = False
    for _ in range(45):
        result = run(FB, 'getvar', 'unlocked', timeout=3)
        if result and result.returncode == 0 and b'unlocked: yes' in result.stderr:
            ready = True
            break
        time.sleep(1)
    assert ready, 'Unlocked fastboot did not appear'
    windows_path = subprocess.check_output(['wslpath', '-w', str(image)], text=True).strip()
    result = run(FB, 'boot', windows_path, timeout=90)
    accepted = bool(result and result.returncode == 0)
    print('Fastboot diagnostic boot accepted:', accepted, flush=True)
    if not accepted:
        run(FB, 'reboot')
    complete = False
    for _ in range(210 if description.get("menu_test") else 150 if description.get("pixel_write") or description.get("experimental_gop") else 100):
        result = run(ADB, 'get-state', timeout=3)
        if result and result.returncode == 0 and result.stdout.strip() == b'device':
            result = run(ADB, 'shell', 'getprop sys.boot_completed')
            if result and result.returncode == 0 and result.stdout.strip() == b'1':
                complete = True
                break
        time.sleep(1)
    report = dict(kind='minimal SEC/DXE diagnostic on handset; incomplete UEFI platform',
                  runner_sha256=sha(Path(__file__).read_bytes()),
                  build_source_verification=provenance,
                  fastboot_boot_accepted=accepted, android_boot_completed=complete,
                  image_sha256=description['image_sha256'], firmware_sha256=description['firmware_sha256'],
                  identifier=description['identifier'], used_flash_or_erase=False,
                  requested_stop_stage=description.get('stop_stage', 4),
                  full_uefi_platform=False, display_or_keys_validated=False,
                  boot_partition_unchanged=None, sec_dxe_stage_verified=None)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    if not complete:
        report['result'] = 'No Android return within observation window; execution stage unknown'
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        publish_attempt(report)
    assert complete, 'Android return not established; preserve private logs and inspect connection'
    result = root('id')
    report['root_verified'] = bool(result and result.returncode == 0 and b'uid=0' in result.stdout)
    result = root('sha256sum /dev/block/bootdevice/by-name/boot')
    report['boot_partition_unchanged'] = bool(result and result.returncode == 0 and
                                             result.stdout.decode().split()[0] == description['source_sha256'])
    result = root('cat /sys/firmware/fdt', save='after.dtb')
    assert result and result.returncode == 0
    blob = result.stdout
    assert struct.unpack_from('>II', blob) == (0xd00dfeed, len(blob))
    tree = read_fdt(blob)
    chosen = next(n for n in tree.walk() if n.name == 'chosen' and n.parent is tree)
    report['nonce_matched'] = chosen.strings('raphael,sec-dxe-id') == [description['identifier']]
    data = chosen.properties.get('raphael,sec-dxe')
    report['result_record_found'] = data is not None and len(data) == len(FIELDS) * 8
    report['sec_dxe_diagnostic_passed'] = False
    report['firmware_checkpoint_passed'] = False
    if report['result_record_found']:
        entry = dict(zip(FIELDS, struct.unpack('>' + 'Q' * len(FIELDS), data)))
        gic_raw=chosen.properties.get('raphael,gic-readonly')
        report['gic_checkpoint_verified']=not description.get('gic_probe') and gic_raw is None
        if description.get('gic_probe'):
            from gic_probe import decode as decode_gic
            try:
                assert gic_raw is not None
                (out/'gic-snapshot.bin').write_bytes(gic_raw)
                report['gic']=decode_gic(gic_raw,blob,entry['mpidr'])
                report['gic_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['gic_decode_error']=str(error) or type(error).__name__
        icc_raw=chosen.properties.get('raphael,icc-readonly')
        report['icc_checkpoint_verified']=not description.get('icc_probe') and icc_raw is None
        if description.get('icc_probe'):
            from icc_probe import decode as decode_icc
            try:
                assert icc_raw is not None and not description.get('icc_fault_test')
                (out/'icc-snapshot.bin').write_bytes(icc_raw)
                if len(icc_raw)>=7*8:
                    report['icc_header']=dict(zip(['version','status','attempted','completed','failed_selector','trap_esr','trap_elr'],struct.unpack_from('>7Q',icc_raw)))
                report['icc']=decode_icc(icc_raw,entry['mpidr'],entry['cntfrq'])
                report['icc_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['icc_decode_error']=str(error) or type(error).__name__
        enable_map_raw=chosen.properties.get('raphael,gic-enable-map')
        report['gic_enable_map_checkpoint_verified']=not description.get('gic_enable_map') and enable_map_raw is None
        if description.get('gic_enable_map'):
            from gic_enable_map import HEADER as MAP_HEADER,decode as decode_enable_map
            try:
                assert enable_map_raw is not None
                (out/'gic-enable-map.bin').write_bytes(enable_map_raw)
                if len(enable_map_raw)>=13*8:report['gic_enable_map_header']=dict(zip(MAP_HEADER,struct.unpack_from('>13Q',enable_map_raw)))
                report['gic_enable_map']=decode_enable_map(enable_map_raw,report['gic'])
                report['gic_enable_map_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['gic_enable_map_decode_error']=str(error) or type(error).__name__
        route_raw=chosen.properties.get('raphael,timer-route')
        report['timer_route_checkpoint_verified']=not description.get('timer_route_test') and route_raw is None
        if description.get('timer_route_test'):
            from timer_route import FIELDS as ROUTE_FIELDS,decode as decode_timer_route
            try:
                assert route_raw is not None and not description.get('timer_route_fault_test')
                (out/'timer-route.bin').write_bytes(route_raw)
                if len(route_raw)==len(ROUTE_FIELDS)*8:report['timer_route_raw']=dict(zip(ROUTE_FIELDS,struct.unpack('>'+str(len(ROUTE_FIELDS))+'Q',route_raw)))
                report['timer_route']=decode_timer_route(route_raw,blob,report['gic'],report['gic_enable_map'],report['icc'],expect_irq=bool(description.get('timer_irq_test')))
                report['timer_route_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['timer_route_decode_error']=str(error) or type(error).__name__
        irq_raw=chosen.properties.get('raphael,timer-irq')
        report['timer_irq_checkpoint_verified']=not description.get('timer_irq_test') and irq_raw is None
        if description.get('timer_irq_test'):
            from timer_irq import FIELDS as IRQ_FIELDS,decode as decode_timer_irq,linked_window
            try:
                assert irq_raw is not None
                (out/'timer-irq.bin').write_bytes(irq_raw)
                if len(irq_raw)==24*8:report['timer_irq_raw']=dict(zip(IRQ_FIELDS,struct.unpack('>24Q',irq_raw)))
                report['timer_irq']=decode_timer_irq(irq_raw,report['timer_route'],report['icc'],description['layout'],linked_window(build))
                report['timer_irq_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['timer_irq_decode_error']=str(error) or type(error).__name__
        pt_raw=chosen.properties.get('raphael,physical-timer-arch')
        report['physical_timer_checkpoint_verified']=not description.get('physical_timer_arch') and pt_raw is None
        if description.get('physical_timer_arch'):
            from physical_timer import FIELDS as PT_FIELDS,decode as decode_physical
            try:
                assert pt_raw is not None
                (out/'physical-timer.bin').write_bytes(pt_raw)
                if len(pt_raw)==len(PT_FIELDS)*8:report['physical_timer_raw']=dict(zip(PT_FIELDS,struct.unpack('>'+str(len(PT_FIELDS))+'Q',pt_raw)))
                report['physical_timer']=decode_physical(pt_raw,expected_stage,report['gic'],report['timer_route'],report['icc'])
                report['physical_timer_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['physical_timer_decode_error']=str(error) or type(error).__name__
        ppi_raw=chosen.properties.get('raphael,ppi-enable-probe')
        report['ppi_checkpoint_verified']=not description.get('ppi_enable_probe') and ppi_raw is None
        if description.get('ppi_enable_probe'):
            from ppi_probe import FIELDS as PPI_FIELDS,decode as decode_ppi
            try:
                assert ppi_raw is not None and not description.get('icc_fault_test')
                (out/'ppi-probe.bin').write_bytes(ppi_raw)
                if len(ppi_raw)==20*8:report['ppi_raw']=dict(zip(PPI_FIELDS,struct.unpack('>20Q',ppi_raw)))
                report['ppi']=decode_ppi(ppi_raw,blob,report['gic'])
                report['ppi_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['ppi_decode_error']=str(error) or type(error).__name__
        ts_raw=chosen.properties.get('raphael,timer-source')
        report['timer_source_checkpoint_verified']=not description.get('timer_source_test') and ts_raw is None
        if description.get('timer_source_test'):
            from timer_source import FIELDS as TS_FIELDS,decode as decode_timer_source
            try:
                assert ts_raw is not None and not description.get('icc_fault_test')
                (out/'timer-source.bin').write_bytes(ts_raw)
                if len(ts_raw)==17*8:report['timer_source_raw']=dict(zip(TS_FIELDS,struct.unpack('>17Q',ts_raw)))
                report['timer_source']=decode_timer_source(ts_raw,entry['cntfrq'])
                report['timer_source_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['timer_source_decode_error']=str(error) or type(error).__name__
        display = chosen.properties.get('raphael,display-snapshot')
        report['display_snapshot_verified'] = not description.get('display_probe') and display is None
        if description.get('display_probe'):
            try:
                assert display, 'missing display snapshot'
                assert display_recipe(blob) == json.loads(display_audit.read_text())['recipe']
                if description.get('smmu_probe'):
                    assert smmu_recipe(blob) == json.loads(smmu_audit.read_text())['recipe']
                report['display_probe'] = decode_display(display, blob)
                assert report['display_probe']['version'] == (4 if description.get('smmu_probe') else 3)
                report['display_snapshot_verified'] = entry['status'] == 0
            except (AssertionError, ValueError, KeyError) as error:
                report['display_decode_error'] = str(error) or type(error).__name__
                if display and len(display) >= 24:
                    report['partial_display_header'] = dict(zip(['version','status','count'], struct.unpack_from('>3Q', display)))
        pixel_raw=chosen.properties.get('raphael,display-pixels')
        if description.get('pixel_probe'):
            from pixel_probe import decode as decode_pixels
            try:
                assert pixel_raw is not None
                (out/'pixel-snapshot.bin').write_bytes(pixel_raw)
                report['pixel_probe']=decode_pixels(pixel_raw,blob,report['display_probe'])
                report['display_snapshot_verified'] &= report['pixel_probe']['cpu_sample_read_verified']
            except (AssertionError,ValueError,KeyError) as error:
                report['pixel_decode_error']=str(error) or type(error).__name__
                report['display_snapshot_verified']=False
        else:
            assert pixel_raw is None
        write_raw=chosen.properties.get('raphael,display-write')
        if description.get('pixel_write'):
            from pixel_write import decode as decode_write
            try:
                assert write_raw is not None
                report['pixel_write']=decode_write(write_raw,report['pixel_probe'])
                report['display_snapshot_verified'] &= report['pixel_write']['memory_write_readback_restore_verified']
            except (AssertionError,ValueError,KeyError) as error:
                report['pixel_write_decode_error']=str(error) or type(error).__name__
                report['display_snapshot_verified']=False
        else:
            assert write_raw is None
        gop_raw=chosen.properties.get('raphael,display-gop')
        report['gop_checkpoint_verified']=not description.get('experimental_gop') and gop_raw is None
        if description.get('experimental_gop'):
            from gop_probe import decode as decode_gop
            try:
                assert gop_raw is not None
                stage={2:2,3:3,4:6}[description.get('stop_stage',4)]
                report['gop']=decode_gop(gop_raw,report['pixel_probe'],stage,manager_ui=description.get('visible_manager',False))
                report['gop_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['gop_decode_error']=str(error) or type(error).__name__
        input_raw=chosen.properties.get('raphael,input-map')
        report['input_checkpoint_verified']=not description.get('input_probe') and input_raw is None
        if description.get('input_probe'):
            from input_probe import decode as decode_input,recipe as input_recipe
            try:
                assert input_raw is not None
                assert input_recipe(blob)==json.loads(input_audit.read_text())['recipe']
                report['input_probe']=decode_input(input_raw,blob)
                report['input_checkpoint_verified']=bool(report['input_probe']['status']==4 and report['input_probe']['targets_verified'])
            except (AssertionError,ValueError,KeyError) as error:
                report['input_decode_error']=str(error) or type(error).__name__
        key_raw=chosen.properties.get('raphael,input-registers')
        report['key_read_checkpoint_verified']=not description.get('input_read') and key_raw is None
        if description.get('input_read'):
            from key_read import decode as decode_keys
            try:
                assert key_raw is not None
                report['key_registers']=decode_keys(key_raw,report['input_probe'],entry['cntfrq'])
                report['key_read_checkpoint_verified']=bool(report['key_registers']['all_six_read_transactions_verified'])
            except (AssertionError,ValueError,KeyError) as error:
                report['key_read_decode_error']=str(error) or type(error).__name__
        input_dxe_raw=chosen.properties.get('raphael,input-dxe')
        report['input_dxe_checkpoint_verified']=not description.get('input_protocol') and input_dxe_raw is None
        if description.get('input_protocol'):
            from input_dxe import decode as decode_input_dxe
            try:
                assert input_dxe_raw is not None
                stage={2:2,3:3,4:6}[description.get('stop_stage',4)]
                report['input_dxe']=decode_input_dxe(input_dxe_raw,report['input_probe'],stage,description.get('menu_test',False) or description.get('visible_manager',False))
                report['input_dxe_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['input_dxe_decode_error']=str(error) or type(error).__name__
        payload_raw=chosen.properties.get('raphael,payload-diagnostic')
        report['payload_checkpoint_verified']=not description.get('payload_test') and payload_raw is None
        if description.get('payload_test'):
            from payload_probe import decode as decode_payload
            try:
                assert payload_raw is not None
                report['payload']=decode_payload(payload_raw,description['layout'],{2:2,3:3,4:6}[description.get('stop_stage',4)],manager_keys=description.get('manager_keys',False))
                report['payload_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['payload_decode_error']=str(error) or type(error).__name__
        ui_raw=chosen.properties.get('raphael,manager-ui')
        report['manager_ui_checkpoint_verified']=not description.get('visible_manager') and ui_raw is None
        if description.get('visible_manager'):
            from manager_ui import decode as decode_ui
            try:
                assert ui_raw is not None
                (out/'manager-ui.bin').write_bytes(ui_raw)
                report['manager_ui']=decode_ui(ui_raw,expected_stage,report.get('gop'))
                if expected_stage==6:
                    import re
                    ui_log=chosen.properties.get('raphael,sec-dxe-log',b'')
                    assert re.search(rb'ui: graphics '+str(report['gop']['width']).encode()+rb'x'+str(report['gop']['height']).encode(),ui_log)
                    assert re.search(rb'menu: shown '+(b'2' if description.get('manager_keys') else b'1')+rb' entries,.*input yes',ui_log)
                    assert report['input_dxe']['polls']>0 and report['input_dxe']['errors']==0
                report['manager_ui_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['manager_ui_decode_error']=str(error) or type(error).__name__
        ram_raw=chosen.properties.get('raphael,ram-read')
        report['ram_read_checkpoint_verified']=not description.get('ram_read_probe') and ram_raw is None
        if description.get('ram_read_probe'):
            from ram_read_probe import FIELDS as RAM_FIELDS,decode as decode_ram
            try:
                assert ram_raw is not None
                (out/'ram-read.bin').write_bytes(ram_raw)
                if len(ram_raw)==26*8:report['ram_read_raw']=dict(zip(RAM_FIELDS,struct.unpack('>26Q',ram_raw)))
                report['ram_read']=decode_ram(ram_raw,description['ram_read_evidence']['policy'])
                assert report['ram_read']['frequency']==entry['cntfrq'] and report['ram_read']['sctlr']==entry['sctlr']
                report['ram_read_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['ram_read_decode_error']=str(error) or type(error).__name__
        mapped_raw=chosen.properties.get('raphael,ram-mapped')
        report['ram_mapped_checkpoint_verified']=not description.get('ram_mapped_probe') and mapped_raw is None
        if description.get('ram_mapped_probe'):
            from ram_mapped_probe import decode as decode_mapped,FIELDS as MAPPED_FIELDS
            try:
                assert mapped_raw is not None and report['ram_read_checkpoint_verified']
                (out/'ram-mapped.bin').write_bytes(mapped_raw)
                if len(mapped_raw)==27*8:report['ram_mapped_raw']=dict(zip(MAPPED_FIELDS,struct.unpack('>27Q',mapped_raw)))
                report['ram_mapped']=decode_mapped(mapped_raw,report['ram_read'],expected_stage)
                if expected_stage==3:assert report['ram_mapped']['sctlr']==entry['mmu_sctlr']
                report['ram_mapped_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['ram_mapped_decode_error']=str(error) or type(error).__name__
        cache_raw=chosen.properties.get('raphael,ram-cache-write')
        report['ram_cache_checkpoint_verified']=not description.get('ram_cache_write_pages') and cache_raw is None
        if description.get('ram_cache_write_pages'):
            from ram_cache_write import decode as decode_cache,FIELDS as CACHE_FIELDS
            try:
                assert cache_raw is not None and report['ram_mapped_checkpoint_verified']
                (out/'ram-cache.bin').write_bytes(cache_raw)
                if len(cache_raw)==39*8:report['ram_cache_raw']=dict(zip(CACHE_FIELDS,struct.unpack('>16Q',cache_raw[:128])))
                report['ram_cache']=decode_cache(cache_raw,report['ram_read'],report['ram_mapped'],description['ram_read_evidence']['policy'],description['ram_cache_write_pages'],expected_stage)
                if expected_stage==3:assert report['ram_cache']['sctlr']==entry['mmu_sctlr']
                report['ram_cache_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['ram_cache_decode_error']=str(error) or type(error).__name__
        write_raw=chosen.properties.get('raphael,ram-write')
        report['ram_write_checkpoint_verified']=not description.get('ram_write_pages') and write_raw is None
        if description.get('ram_write_pages'):
            from ram_write_probe import decode as decode_write
            try:
                assert write_raw is not None
                (out/'ram-write.bin').write_bytes(write_raw)
                report['ram_write']=decode_write(write_raw,description['ram_read_evidence']['policy'],description['ram_write_pages'])
                assert report['ram_read_checkpoint_verified'] and report['ram_write']['frequency']==entry['cntfrq']
                assert report['ram_read']['end_counter']<=report['ram_write']['start_counter']
                report['ram_write_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['ram_write_decode_error']=str(error) or type(error).__name__
        manager_raw=chosen.properties.get('raphael,manager-run')
        darwin_raw=chosen.properties.get('raphael,darwin-diagnostic')
        report['darwin_checkpoint_verified']=not description.get('darwin_test') and darwin_raw is None
        if description.get('darwin_test'):
            from darwin_probe import decode as decode_darwin
            try:
                assert darwin_raw is not None
                (out/'darwin.bin').write_bytes(darwin_raw)
                report['darwin']=decode_darwin(darwin_raw,expected_stage,handset=True)
                report['darwin_checkpoint_verified']=True
            except AssertionError as error:
                report['darwin_decode_error']=str(error) or type(error).__name__
        manager_expected=bool(description.get('payload_test') and description.get('physical_timer_arch'))
        report['manager_checkpoint_verified']=not manager_expected and manager_raw is None
        if manager_expected:
            from manager_probe import decode as decode_manager
            try:
                assert manager_raw is not None
                (out/'manager-run.bin').write_bytes(manager_raw)
                report['manager']=decode_manager(manager_raw,expected_stage,report['payload'],entry['cntfrq'],visible=description.get('visible_manager',False),manual=description.get('manager_keys',False))
                report['manager_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['manager_decode_error']=str(error) or type(error).__name__
        report['manager_keys_checkpoint_verified']=not description.get('manager_keys',False)
        if description.get('manager_keys'):
            from manager_keys import decode as decode_manager_keys
            try:
                report['manager_keys']=decode_manager_keys(chosen.properties.get('raphael,sec-dxe-log',b''),expected_stage,report['manager'],report['input_dxe'])
                report['manager_keys_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError,TypeError) as error:
                report['manager_keys_decode_error']=str(error) or type(error).__name__
        menu_raw=chosen.properties.get('raphael,display-menu')
        menu_expected=bool(description.get('menu_test') and description.get('stop_stage')==4)
        report['menu_checkpoint_verified']=not menu_expected and menu_raw is None
        if menu_expected:
            from input_dxe import decode_menu
            try:
                assert menu_raw is not None
                report['menu']=decode_menu(menu_raw,report['gop'],entry['cntfrq'])
                report['menu_checkpoint_verified']=True
            except (AssertionError,ValueError,KeyError) as error:
                report['menu_decode_error']=str(error) or type(error).__name__
        report['entry'] = entry
        report['entry_hex'] = {k: hex(v) for k, v in entry.items()}
        log = chosen.properties.get('raphael,sec-dxe-log', b'')
        mmap = chosen.properties.get('raphael,sec-dxe-map', b'')
        (out / 'firmware.log').write_bytes(log)
        report['kernel_window_checkpoint_verified']=not description.get('kernel_window')
        if description.get('kernel_window'):
            from kernel_window import check_admission,check_log
            try:
                report['kernel_window']=check_log(log,description['kernel_window']) if expected_stage==6 else check_admission(log,description['kernel_window'])
                report['kernel_window_checkpoint_verified']=True
            except (AssertionError,ValueError) as error:
                report['kernel_window_error']=str(error) or type(error).__name__

        (out / 'firmware-memory-map.bin').write_bytes(mmap)
        arena = description['layout']['ArenaBase']
        arena_end = arena + description['layout']['ArenaSize']
        valid_map = (entry['descriptor_size'] >= 40 and len(mmap) == entry['map_bytes'] and
                     len(mmap) > 0 and len(mmap) % entry['descriptor_size'] == 0)
        decoded, bad = [], 0
        if valid_map:
            for at in range(0, len(mmap), entry['descriptor_size']):
                typ, _, physical, virtual, pages, attributes = struct.unpack_from('<II4Q', mmap, at)
                w=description.get('kernel_window')
                window_reserved=bool(w and typ==4 and w['base']<=physical and physical+pages*4096<=w['base']+w['bytes'])
                if typ in [3, 4, 5, 6, 7] and not window_reserved and not (arena <= physical <= arena_end and physical + pages * 4096 <= arena_end):
                    bad += 1
                decoded.append(dict(type=typ, physical=physical, virtual=virtual, pages=pages, attributes=attributes))
        report['decoded_memory_map'] = decoded
        report['independently_checked_map_violations'] = bad
        expected_stage = {2: 2, 3: 3, 4: 6}[description.get('stop_stage', 4)]
        checkpoint_ok = bool(report['kernel_window_checkpoint_verified'] and report['ram_cache_checkpoint_verified'] and report['ram_mapped_checkpoint_verified'] and report['darwin_checkpoint_verified'] and report['ram_write_checkpoint_verified'] and report['manager_keys_checkpoint_verified'] and report['manager_ui_checkpoint_verified'] and report['ram_read_checkpoint_verified'] and report['nonce_matched'] and report['manager_checkpoint_verified'] and report['physical_timer_checkpoint_verified'] and report['timer_irq_checkpoint_verified'] and report['timer_route_checkpoint_verified'] and report['gic_enable_map_checkpoint_verified'] and report['ppi_checkpoint_verified'] and report['timer_source_checkpoint_verified'] and report['icc_checkpoint_verified'] and report['gic_checkpoint_verified'] and report['display_snapshot_verified'] and report['gop_checkpoint_verified'] and report['input_checkpoint_verified'] and report['key_read_checkpoint_verified'] and report['input_dxe_checkpoint_verified'] and report['menu_checkpoint_verified'] and report['payload_checkpoint_verified'] and entry['stage'] == expected_stage and
                             entry['status'] == 0 and entry['current_el'] == 4 and
                             entry['image_base'] == description['layout']['ImageBase'] and
                             entry['fdt_copy'] == description['layout']['FdtBase'] and
                             entry['mmu_sctlr'] & 0x1005 == (0 if expected_stage == 2 else 0x1005) and
                             len(log) == entry['log_bytes'] and len(log) > 0)
        report['sec_dxe_diagnostic_passed'] = bool(
            report['nonce_matched'] and entry['stage'] == 6 and entry['status'] == 0 and
            entry['system_table_signature'] == 0x5453595320494249 and
            entry['boot_services_signature'] == 0x56524553544f4f42 and
            entry['system_table_crc_ok'] == entry['boot_services_crc_ok'] == 1 and
            entry['allocation_probe_ok'] == 1 and entry['map_violations'] == bad == 0 and valid_map and
            entry['mmu_sctlr'] & 0x1005 == 0x1005 and len(log) == entry['log_bytes'] and len(log) > 0)
        report['firmware_checkpoint_passed'] = checkpoint_ok and (expected_stage != 6 or report['sec_dxe_diagnostic_passed'])
        report['sec_dxe_stage_verified'] = entry['stage'] if report['firmware_checkpoint_passed'] else None
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(out)
    report['result'] = ('Nonce-matched checkpoint and Android return verified' if
                        report['firmware_checkpoint_passed'] else
                        'Android returned but requested firmware checkpoint was not established')
    publish_attempt(report)
    assert accepted and all(report.get(k) for k in ['root_verified', 'boot_partition_unchanged',
                                                   'nonce_matched', 'firmware_checkpoint_passed'])
    safe = dict(report, source='new diagnostic FV plus nonce-matched Android FDT readback',
                private_build=str(build.relative_to(ROOT)), private_readback=str(out.relative_to(ROOT)),
                fdt_sha256=sha(blob), log_sha256=sha(log), map_sha256=sha(mmap),
                limits=[f'Only checkpoint stage {expected_stage} is verified by this specific run',
                        'No claim of full UEFI compliance, complete vendor memory ownership or whole-arena RAM testing',
                        'GOP/menu/input evidence covers only the recorded checkpoint; physical observations require separate evidence; Only explicitly decoded refusal records verify DarwinBoot driver execution; kernel handoff and XNU are not executed'])
    filename = (f'sec-manager-keys-stage{expected_stage}-handoff.json' if description.get('manager_keys') else
                f'sec-visible-manager-stage{expected_stage}-handoff.json' if description.get('visible_manager') else
                f'sec-darwin-stage{expected_stage}-handoff.json' if description.get('darwin_test') else
                f'sec-ram-cache-pages{description["ram_cache_write_pages"]}-stage{expected_stage}-handoff.json' if description.get('ram_cache_write_pages') else
                f'sec-ram-mapped-stage{expected_stage}-handoff.json' if description.get('ram_mapped_probe') else
                f'sec-ram-write-stage{expected_stage}-handoff.json' if description.get('ram_write_pages') else
                f'sec-ram-read-stage{expected_stage}-handoff.json' if description.get('ram_read_probe') else
                f'sec-manager-stage{expected_stage}-handoff.json' if description.get('payload_test') and description.get('physical_timer_arch') else
                f'sec-physical-timer-stage{expected_stage}-handoff.json' if description.get('physical_timer_arch') else
                f'sec-timer-irq-stage{expected_stage}-handoff.json' if description.get('timer_irq_test') else
                f'sec-timer-route-stage{expected_stage}-handoff.json' if description.get('timer_route_test') else
                f'sec-gic-enable-map-stage{expected_stage}-handoff.json' if description.get('gic_enable_map') else
                f'sec-ppi-enable-stage{expected_stage}-handoff.json' if description.get('ppi_enable_probe') else
                f'sec-timer-source-stage{expected_stage}-handoff.json' if description.get('timer_source_test') else
                f'sec-icc-readonly-stage{expected_stage}-handoff.json' if description.get('icc_probe') else
                f'sec-gic-readonly-stage{expected_stage}-handoff.json' if description.get('gic_probe') else
                f'sec-payload-stage{expected_stage}-handoff.json' if description.get('payload_test') else
                f'sec-menu-stage{expected_stage}-handoff.json' if description.get('menu_test') else
                f'sec-inputdxe-stage{expected_stage}-handoff.json' if description.get('input_protocol') else
                f'sec-keyread-stage{expected_stage}-handoff.json' if description.get('input_read') else
                f'sec-input-stage{expected_stage}-handoff.json' if description.get('input_probe') else
                f'sec-gop-stage{expected_stage}-handoff.json' if description.get('experimental_gop') else
                'sec-display-handoff.json' if description.get('display_probe') else
                'sec-dxe-handoff.json' if expected_stage == 6 else f'sec-stage{expected_stage}-handoff.json')
    payload=json.dumps(safe, indent=2) + '\n'
    if description.get('ram_cache_write_pages'):
        immutable=ROOT/'UniXNU-raphael/evidence'/(filename[:-5]+'-'+out.name+'.json')
        assert not immutable.exists()
        immutable.write_text(payload)
    (ROOT / 'UniXNU-raphael/evidence' / filename).write_text(payload)


if __name__ == '__main__':
    main()
