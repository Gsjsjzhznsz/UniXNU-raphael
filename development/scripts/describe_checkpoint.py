#!/usr/bin/env python3
"""Create a compact public-safe verification index from local evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def latest(folder, filename):
    paths = sorted((ROOT / folder).glob('*/' + filename))
    assert paths, (folder, filename)
    return paths[-1]


def load(path):
    return json.loads(path.read_text())


def main():
    build = latest('artifacts/edk2-diag', 'report.json')
    qemu = latest('artifacts/qemu-diag', 'report.json')
    backup = latest('evidence/private/backup-verification', 'report.json')
    reference = latest('evidence/private/reference-boot', 'report.json')
    entry_probe = latest('evidence/private/entry-probe-run', 'report.json')
    entry_qemu = latest('artifacts/entry-probe-qemu', 'report.json')
    memory = latest('artifacts/memory-contract', 'report.json')
    memory_edk2 = latest('artifacts/edk2-memory-contract', 'report.json')
    cleanup = latest('evidence/private/entry-probe-cleanup', 'report.json')
    b, q, v, r = map(load, [build, qemu, backup, reference])
    report = dict(
        source_implementation=['binary-safe collector', 'legacy boot/DTBO parser', 'original XBL extraction and metadata',
                               'source-derived core DTS', 'protocol-only diagnostic UEFI application',
                               'ARM64 entry instrumentation with original Android continuation',
                               'RaphaelMemoryContractLib and disabled design-only memory plan'],
        host_build=dict(command=b['command'], result=b['returncode'] == 0, core_revision=b['core_revision'],
                        image_bytes=b['bytes'], image_sha256=b['sha256']),
        image_checks=dict(raw_diagnostic='AArch64 PE32+, EFI application, valid entry RVA, base relocation directory',
                          current_phone_boot='Android header v1, page 4096, binary part sizes checked',
                          dtbo='Header and every entry bounded and FDT structurally parsed',
                          observed_dts=load(ROOT / 'artifacts/observed-dts/report.json')),
        emulated_runtime=dict(passed=q['passed'], gop_available=q['gop_available'], markers=q['markers'],
                              image_sha256=q['image_sha256'], handset_execution=False),
        handset=dict(fastboot_unlocked=True, reference_android_boot_accepted=r['fastboot_boot_accepted'],
                     reference_image_sha256=r['image_sha256'], android_boot_completed=r['android_boot_completed'],
                     root_verified=r['root_verified'], boot_partition_unchanged=r['boot_partition_unchanged'],
                     own_complete_uefi_booted=False, own_gop_or_keys_verified=False, darwinboot_started=False, xnu_started=False),
        protected_backup=dict(sha256_entries_verified=v['verified_files'], passed=v['passed'],
                              restored=False, complete_phone_backup=False),
        local_evidence=dict(edk2_build=str(build.relative_to(ROOT)), qemu=str(qemu.relative_to(ROOT)),
                            backup=str(backup.relative_to(ROOT)), reference_boot=str(reference.relative_to(ROOT))),
        limits='No handset execution of new UEFI. Vendor-declared addresses are not approved new allocations.')
    target = ROOT / 'docs/validation-checkpoint.json'
    report['entry_probe'] = dict(handset=load(entry_probe), emulator=load(entry_qemu),
                                host_image_checks=True, is_complete_uefi=False,
                                normal_reboot_cleanup=load(cleanup))
    report['memory_contract'] = dict(host_cases=load(memory)['cases'], edk2_build=load(memory_edk2),
                                     boot_enabled=False, full_arena_handset_verified=False)
    window_path=ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json'
    host_path=ROOT/'UniXNU-raphael/evidence/kernel-window-host.json'
    if window_path.exists() and host_path.exists():
        window,host=load(window_path),load(host_path)
        assert window['passed'] and host['passed']
        assert host['audit_sha256']==hashlib.sha256(window_path.read_bytes()).hexdigest()
        assert not window['boot_enabled'] and not window['new_uefi_memory_registered']
        report['kernel_window_analysis']=dict(
            audit=str(window_path.relative_to(ROOT)),audit_sha256=hashlib.sha256(window_path.read_bytes()).hexdigest(),
            host=str(host_path.relative_to(ROOT)),host_sha256=hashlib.sha256(host_path.read_bytes()).hexdigest(),
            minimum_bytes=window['darwin_minimum_window_bytes'],candidates=window['candidates'],
            host_checks=host['checks'],hardware_window_access_verified=False,
            allocator_enabled=False,full_ownership_proven=False)

    report['handset']['own_entry_probe_executed'] = load(entry_probe)['nonce_matched']
    report['handset']['transient_probe_removed_after_normal_reboot'] = load(cleanup)['transient_probe_absent']
    report['local_evidence'].update(entry_probe=str(entry_probe.relative_to(ROOT)),
                                    entry_qemu=str(entry_qemu.relative_to(ROOT)),
                                    memory_contract=str(memory.relative_to(ROOT)),
                                    memory_contract_edk2=str(memory_edk2.relative_to(ROOT)),
                                    entry_probe_cleanup=str(cleanup.relative_to(ROOT)))
    firmware_reports = sorted((ROOT / 'artifacts/sec-dxe-qemu').glob('*/report.json'))
    if firmware_reports:
        firmware = load(firmware_reports[-1])
        report['diagnostic_firmware'] = dict(
            source_implemented=True, full_uefi_platform=False,
            emulator=firmware, image_structure=load(firmware_reports[-1].parent / 'fd-inspection.json'),
            source_scope='Own SEC, exception/return path, memory log and diagnostic DXE; pinned generic DXE/RuntimeDxe')
        report['local_evidence']['sec_dxe_qemu'] = str(firmware_reports[-1].relative_to(ROOT))
        checkpoints = {}
        for path in firmware_reports:
            item = load(path)
            checkpoints[str(item.get('stop_stage', 4))] = dict(
                report=str(path.relative_to(ROOT)), passed=item.get('qemu_passed', False),
                firmware_sha256=item.get('firmware_sha256'), display_probe=item.get('display_probe', False),
                source_inputs=item.get('source_inputs', []),
                payload_test=item.get('payload_test', False), darwin_test=item.get('darwin_test', False),
                checks={name: run['pass_count'] for name, run in item.get('executions', {}).items()})
        report['diagnostic_firmware']['emulator_checkpoints'] = checkpoints
    extent_path = ROOT / 'UniXNU-raphael/evidence/extent-download.json'
    if extent_path.exists():
        report['candidate_extent_download'] = load(extent_path)
    attempts = sorted((ROOT / 'evidence/private/sec-dxe-run').glob('*/report.json'))
    if attempts:
        attempt_path = attempts[-1]
        attempt = load(attempt_path)
        report['handset']['own_uefi_attempted'] = True
        report['handset']['sec_dxe_diagnostic_passed'] = any(load(p).get('sec_dxe_diagnostic_passed', False) for p in attempts)
        report['handset']['latest_attempt_sec_dxe_diagnostic_passed'] = attempt.get('sec_dxe_diagnostic_passed', False)
        report['handset']['diagnostic_success_scope'] = 'Historical results are bound to their own build snapshots; latest source is not implicitly verified at every stage'
        report['handset']['complete_uefi_platform_verified'] = False
        report['handset']['verified_diagnostic_stages'] = sorted({
            load(p)['sec_dxe_stage_verified'] for p in attempts
            if load(p).get('firmware_checkpoint_passed')})
        report['diagnostic_firmware']['latest_handset_attempt'] = attempt
        report['local_evidence']['sec_dxe_handset_attempt'] = str(attempt_path.relative_to(ROOT))
        cleanup_is_later = cleanup.parent.name > attempt_path.parent.name
        current = load(cleanup) if cleanup_is_later else attempt
        report['handset']['current_android_state_confirmed'] = bool(current.get('android_boot_completed'))
        for key in ['android_boot_completed', 'root_verified', 'boot_partition_unchanged']:
            report['handset'][key] = current.get(key)
        report['handset']['transient_probe_removed_after_normal_reboot'] = bool(
            cleanup_is_later and load(cleanup)['transient_probe_absent'])
        report['handset']['last_cleanup_precedes_firmware_attempt'] = not cleanup_is_later
        report['diagnostic_firmware']['handset_history'] = [dict(
            report=str(p.relative_to(ROOT)), requested_stop_stage=load(p).get('requested_stop_stage'),
            android_boot_completed=load(p).get('android_boot_completed'),
            stage_verified=load(p).get('sec_dxe_stage_verified'),
            checkpoint_passed=load(p).get('firmware_checkpoint_passed', False)) for p in attempts]
        report['limits'] = ('Only nonce-matched diagnostic stages with a passing report are handset-verified. '
                            'Earlier failed attempts remain separate from later success or recovery. '
                            'No complete UEFI/GOP/keys/DarwinBoot/XNU or full vendor memory ownership claim.')
    regression = ROOT / 'UniXNU-raphael/evidence/fdt-traversal-regression.json'
    if regression.exists():
        report['diagnostic_firmware']['fdt_traversal_regression'] = load(regression)
    display = ROOT / 'UniXNU-raphael/evidence/sec-display-handoff.json'
    if display.exists():
        report['display_probe'] = dict(handset=load(display),
            source_audit=load(ROOT / 'UniXNU-raphael/evidence/display-source-audit.json'),
            host_tests=load(ROOT / 'UniXNU-raphael/evidence/display-probe-host.json'),
            framebuffer_or_gop_verified=False)
        route = ROOT / 'UniXNU-raphael/evidence/boot-display-route-observation.json'
        if route.exists():
            observation = load(route)
            report['display_probe']['route_observation'] = dict(
                path=str(route.relative_to(ROOT)), sha256=hashlib.sha256(route.read_bytes()).hexdigest(),
                register_configuration_consistent=observation['candidate']['register_configuration_consistent'],
                physical_mapping_verified=False, pixel_output_verified=False)
        report['display_probe']['historical_version2_handoff'] = 'UniXNU-raphael/evidence/sec-display-handoff-v2.json'
        binding = ROOT / 'UniXNU-raphael/evidence/sec-display-source-binding.json'
        if binding.exists():
            report['display_probe']['source_binding'] = dict(path=str(binding.relative_to(ROOT)),
                sha256=hashlib.sha256(binding.read_bytes()).hexdigest(), source_revision=load(binding)['source_revision'])
    smmu = ROOT / 'UniXNU-raphael/evidence/boot-smmu-observation.json'
    if smmu.exists():
        report['smmu_probe'] = dict(observation=load(smmu),
            source_audit=load(ROOT/'UniXNU-raphael/evidence/smmu-source-audit.json'),
            host_tests=load(ROOT/'UniXNU-raphael/evidence/smmu-probe-host.json'),
            source_binding=load(ROOT/'UniXNU-raphael/evidence/sec-smmu-source-binding.json'),
            cleanup=load(ROOT/'UniXNU-raphael/evidence/sec-smmu-cleanup.json'))
    pixels=ROOT/'UniXNU-raphael/evidence/boot-pixel-observation.json'
    if pixels.exists():
        report['pixel_probe']=dict(observation=load(pixels),
            host_tests=load(ROOT/'UniXNU-raphael/evidence/pixel-probe-host.json'),
            source_binding=load(ROOT/'UniXNU-raphael/evidence/sec-pixel-source-binding.json'),
            cleanup=load(ROOT/'UniXNU-raphael/evidence/sec-pixel-cleanup.json'))
    write = ROOT/'UniXNU-raphael/evidence/boot-pixel-write-observation.json'
    if write.exists():
        report['pixel_write'] = dict(observation=load(write),
            source_binding=load(ROOT/'UniXNU-raphael/evidence/sec-pixel-write-source-binding.json'),
            host_tests=load(ROOT/'UniXNU-raphael/evidence/pixel-write-host.json'),
            cleanup=load(ROOT/'UniXNU-raphael/evidence/sec-pixel-write-cleanup.json'))
        report['handset']['sec_bounded_pixel_output_human_verified'] = load(write)['human_observation']['visible_output_verified']
    gop = ROOT/'UniXNU-raphael/evidence/boot-gop-observation.json'
    if gop.exists():
        report['gop'] = dict(observation=load(gop),
            host_tests=load(ROOT/'UniXNU-raphael/evidence/gop-host.json'),
            route_tests=load(ROOT/'UniXNU-raphael/evidence/gop-route-host.json'),
            source_binding=load(ROOT/'UniXNU-raphael/evidence/sec-gop-source-binding.json'),
            source_audit=load(ROOT/'UniXNU-raphael/evidence/gop-source-audit.json'),
            cleanup=load(ROOT/'UniXNU-raphael/evidence/sec-gop-cleanup.json'))
        report['handset']['inherited_single_mode_gop_verified'] = bool(load(gop)['gop']['protocol_and_blt_memory_verified'])
        report['handset']['gop_output_human_verified'] = bool(load(gop)['human_observation']['visible_output_verified'])
        report['handset']['own_gop_or_keys_verified'] = report['handset']['inherited_single_mode_gop_verified']
        report['limits'] = ('Nonce-matched SEC/DXE and inherited single-mode GOP diagnostics verified. '
                            'No complete UEFI, mode reinitialization, menu, keys, DarwinBoot, XNU or full vendor memory ownership claim.')
    for name,filename in [('input_map','boot-input-map-observation.json'),('key_registers','boot-key-register-observation.json')]:
        p=ROOT/'UniXNU-raphael/evidence'/filename
        if p.exists():report[name]=load(p)
    menu=ROOT/'UniXNU-raphael/evidence/boot-menu-observation.json'
    if menu.exists():
        report['menu_input']=dict(observation=load(menu),
            source_binding=load(ROOT/'UniXNU-raphael/evidence/sec-menu-source-binding.json'),
            cleanup=load(ROOT/'UniXNU-raphael/evidence/sec-menu-cleanup.json'),
            host_tests=load(ROOT/'UniXNU-raphael/evidence/input-dxe-host.json'),
            source_audit=load(ROOT/'UniXNU-raphael/evidence/menu-source-audit.json'))
        report['handset']['simple_text_input_protocol_installed']=bool(load(menu)['input_dxe']['protocol_installed'])
        report['handset']['menu_framebuffer_changed_and_restored']=load(menu)['menu']['menu_framebuffer_changed_and_restored']
        report['handset']['menu_human_visibility_verified']=load(menu)['human_observation']['menu_visible_verified']
        report['handset']['physical_keys_verified']=load(menu)['human_observation']['physical_keys_verified']
        report['limits']='Diagnostic SEC/DXE, inherited GOP and bounded menu memory restore verified. No full UEFI/TimerArch/UniXNURun, physical key, DarwinBoot, XNU or full vendor memory ownership claim.'
    payload=ROOT/'UniXNU-raphael/evidence/payload-sec-source-binding.json'
    if payload.exists():
        report['payload_integration']=dict(handset_executed=False,
            source_binding=load(payload),
            positive_aavmf_fixture=load(ROOT/'UniXNU-raphael/evidence/payload-fixture-qemu.json'),
            primary_source_audit=load(ROOT/'UniXNU-raphael/evidence/payload-source-audit.json'),
            wire_host=load(ROOT/'UniXNU-raphael/evidence/payload-wire-host.json'))
    darwin=ROOT/'UniXNU-raphael/evidence/darwin-sec-source-binding.json'
    if darwin.exists():
        report['darwinboot_interface']=dict(handset_executed=False, xnu_executed=False,
            source_binding=load(darwin),
            aavmf_fixture=load(ROOT/'UniXNU-raphael/evidence/darwin-fixture-qemu.json'),
            primary_source_audit=load(ROOT/'UniXNU-raphael/evidence/darwin-source-audit.json'),
            wire_host=load(ROOT/'UniXNU-raphael/evidence/darwin-wire-host.json'))
    interrupts=ROOT/'UniXNU-raphael/evidence/interrupt-resource-contract.json'
    if interrupts.exists():
        report['interrupt_resources']=dict(contract=load(interrupts),
            host_tests=load(ROOT/'UniXNU-raphael/evidence/interrupt-contract-host.json'),
            uefi_timer_arch_on_handset_verified=False)
    architecture=ROOT/'UniXNU-raphael/evidence/qemu-arch-sec-source-binding.json'
    if architecture.exists():
        report['own_qemu_architecture']=dict(source_binding=load(architecture),
            source_audit=load(ROOT/'UniXNU-raphael/evidence/qemu-arch-source-audit.json'),
            wire_host=load(ROOT/'UniXNU-raphael/evidence/qemu-arch-wire-host.json'),
            handset_executed=False,gic_full_restore_verified=False,xnu_executed=False)
    handoff=ROOT/'UniXNU-raphael/evidence/handoff-fixture-qemu.json'
    if handoff.exists():
        report['synthetic_darwin_handoff']=dict(fixture=load(handoff),
            boot_args_layout=load(ROOT/'UniXNU-raphael/evidence/boot-args-abi.json'),
            handset_executed=False,xnu_executed=False,own_sec_dxe_handoff_verified=False)
    overnight=ROOT/'UniXNU-raphael/evidence/overnight-automatic-status.json'
    if overnight.exists():report['historical_overnight_status']=load(overnight)
    # Combine human observations only with their independently successful attempt.
    manual=[]
    for path in sorted((ROOT/'UniXNU-raphael/evidence').glob('manual-menu-observation-*.json')):
        observation=load(path);attempt=load(ROOT/observation['attempt'])
        assert observation['image_sha256']==attempt['image_sha256']
        if 'firmware_sha256' in observation:assert observation['firmware_sha256']==attempt['firmware_sha256']
        assert observation['source_revision']==attempt['build_source_verification']['source_revision']
        assert observation['firmware_checkpoint_passed'] and attempt['firmware_checkpoint_passed']
        manual.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),observation=observation))
    if manual:
        report['manual_menu_retests']=manual
        report['handset']['menu_human_visibility_verified']=any(x['observation'].get('menu_visibility_verified') for x in manual)
        report['handset']['physical_keys_verified']=any(x['observation'].get('physical_keys_verified') and
            x['observation'].get('device_events')==dict(up=1,down=1,enter=1) and x['observation'].get('input_errors')==0 for x in manual)
    scoped={}
    for key,observation,binding in [
        ('gic_readonly','boot-gic-readonly-observation.json','gic-probe-source-binding.json'),
        ('icc_readonly','boot-icc-readonly-observation.json','icc-probe-source-binding.json'),
        ('timer_source','boot-timer-source-observation.json','timer-source-source-binding.json'),
        ('ppi_enable','boot-ppi-enable-observation.json','ppi-probe-source-binding.json'),
        ('gic_enable_map','boot-gic-enable-map-observation.json','gic-enable-map-source-binding.json'),
        ('timer_route','boot-timer-route-observation.json','timer-route-source-binding.json'),
        ('timer_irq','boot-timer-irq-observation.json','timer-irq-source-binding.json'),
        ('physical_timer_arch','boot-physical-timer-observation.json','physical-timer-source-binding.json'),
        ('unixnu_manager','boot-manager-observation.json','manager-source-binding.json'),
        ('ram_sparse_read','boot-ram-read-observation.json','ram-read-source-binding.json'),
        ('visible_manager','boot-visible-manager-observation.json','visible-manager-source-binding-stage6.json'),
        ('manager_keys','boot-manager-keys-observation.json','manager-keys-source-binding-stage6.json')]:
        path=ROOT/'UniXNU-raphael/evidence'/observation;bp=ROOT/'UniXNU-raphael/evidence'/binding
        if not path.exists():continue
        item=load(path);bound=load(bp)
        assert item.get('passed',item.get('firmware_checkpoint_passed')) and item['source_revision']==bound['source_revision']
        scoped[key]=dict(observation=str(path.relative_to(ROOT)),observation_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         source_binding=str(bp.relative_to(ROOT)),source_binding_sha256=hashlib.sha256(bp.read_bytes()).hexdigest(),
                         source_revision=item['source_revision'],result=item)
    report['scoped_hardware_diagnostics']=scoped
    report['handset']['icc_register_read_access_verified']=bool(scoped.get('icc_readonly',{}).get('result',{}).get('icc',{}).get('passed'))
    timer=scoped.get('timer_source',{}).get('result',{}).get('timer_source',{})
    report['handset']['physical_timer_source_expiration_verified']=bool(timer.get('physical_source_expiration_verified'))
    report['handset']['physical_timer_registers_restored']=bool(timer.get('cntp_registers_restored'))
    ppi=scoped.get('ppi_enable',{}).get('result',{}).get('ppi',{})
    report['handset']['physical_timer_ppi_enable_writable']=bool(ppi.get('ppi_enable_writable'))
    report['handset']['physical_timer_ppi_enabled_bit_restored']=bool(ppi.get('enabled_bit_restored'))
    enable_map=scoped.get('gic_enable_map',{}).get('result',{}).get('gic_enable_map',{})
    report['handset']['gic_nonsecure_enables_observed_disabled']=bool(enable_map.get('passed') and enable_map.get('all_observed_disabled'))
    route=scoped.get('timer_route',{}).get('result',{}).get('timer_route',{})
    report['handset']['physical_timer_route_observed_with_irq_masked']=bool(route.get('physical_timer_route_observed'))
    report['handset']['physical_timer_route_registers_restored']=bool(route.get('registers_restored'))
    irq=scoped.get('timer_irq',{}).get('result',{}).get('timer_irq',{})
    report['handset']['timer_irq_delivery_verified']=bool(irq.get('single_irq_handler_verified'))
    report['handset']['single_target_ppi_acknowledge_and_eoi_verified']=bool(irq.get('expected_ppi_acknowledged_once'))
    physical=scoped.get('physical_timer_arch',{}).get('result',{}).get('physical_timer',{})
    report['handset']['bounded_physical_timer_arch_verified']=bool(physical.get('physical_only_timer_arch_verified'))
    report['handset']['timer_relative_periodic_cancel_verified']=bool(physical.get('relative_periodic_cancel_verified'))
    report['handset']['physical_timer_arch_registers_restored']=bool(physical.get('restore_ok'))
    ram=scoped.get('ram_sparse_read',{}).get('result',{}).get('ram_read',{})
    report['handset']['candidate_ram_sparse_read_verified']=bool(ram.get('passed'))
    writes=[]
    for path in sorted((ROOT/'UniXNU-raphael/evidence').glob('boot-ram-write-observation-pages*.json')):
        item=load(path)
        for key in ['source_binding','handoff','immutable_attempt','cleanup']:
            linked=ROOT/item[key]
            assert hashlib.sha256(linked.read_bytes()).hexdigest()==item[key+'_sha256'], (path,key)
        bound=load(ROOT/item['source_binding']); handoff=load(ROOT/item['handoff'])
        assert item['passed'] and item['source_revision']==bound['source_revision']
        assert handoff['ram_write']==item['ram_write'] and handoff['private_build']==bound['phases'][0]['private_build']
        result=item['ram_write']
        assert result['passed'] and result['original_words_restored'] and result['dirty']==result['backup_words']==0
        assert result['completed_pages']==result['restored_pages']==result['requested_pages']
        assert item['android_return_and_clean_reboot_verified'] and not item['new_allocator_memory'] and not item['ownership_proven']
        writes.append(dict(observation=str(path.relative_to(ROOT)),observation_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           source_revision=item['source_revision'],base=result['base'],
                           verified_bytes=result['page_bytes']*result['completed_pages'],result=item))
    report['reversible_ram_write_diagnostics']=writes
    report['handset']['candidate_ram_write_verified']=bool(writes)
    report['handset']['candidate_ram_contiguous_write_restored_bytes']=max((x['verified_bytes'] for x in writes),default=0)
    report['handset']['entire_kernel_window_write_verified']=False
    report['handset']['kernel_window_ownership_proven']=False
    report['handset']['kernel_window_allocator_enabled']=False
    report['handset']['full_timer_arch_verified']=False
    manager=scoped.get('unixnu_manager',{}).get('result',{})
    report['handset']['complete_unixnu_manager_executed']=bool(manager.get('complete_unixnu_manager_executed'))
    report['handset']['unixnu_manager_countdown_verified']=bool(manager.get('manager',{}).get('countdown_verified'))
    report['handset']['visible_complete_unixnu_manager_verified']=bool(manager.get('visible_manager_verified'))
    visible=scoped.get('visible_manager',{}).get('result',{})
    manual_visible=sorted((ROOT/'UniXNU-raphael/evidence').glob('manual-visible-manager-observation-*.json'))
    report['complete_manager_visibility_observations']=[]
    for path in manual_visible:
        item=load(path)
        assert item['passed'] and item['observation_sha256']==hashlib.sha256((ROOT/item['observation']).read_bytes()).hexdigest()
        report['complete_manager_visibility_observations'].append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),result=item))
    report['handset']['complete_manager_framebuffer_changed_and_restored']=bool(visible.get('manager_framebuffer_changed_and_restored'))
    report['handset']['visible_complete_unixnu_manager_verified']=bool(visible.get('passed') and any(load(p).get('human_visibility_verified') for p in manual_visible))
    keys=scoped.get('manager_keys',{}).get('result',{})
    report['complete_manager_key_observations']=[]
    for path in sorted((ROOT/'UniXNU-raphael/evidence').glob('manual-manager-keys-observation-*.json')):
        item=load(path);machine=ROOT/item['machine_observation']
        assert item['passed'] and item['machine_observation_sha256']==hashlib.sha256(machine.read_bytes()).hexdigest()
        assert load(machine)['manager_keys']['physical_three_keys_verified'] and item['source_revision']==load(machine)['source_revision']
        report['complete_manager_key_observations'].append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),result=item))
    report['handset']['physical_keys_in_complete_manager_verified']=bool(keys.get('physical_keys_in_complete_manager_verified') and report['complete_manager_key_observations'])
    nt=ROOT/'UniXNU-raphael/evidence/native-toolchain-host.json'
    if nt.exists():report['native_toolchain_host']=load(nt)
    native=ROOT/'UniXNU-raphael/evidence/native-kernel-structure.json'
    if native.exists():
        structure=load(native);artifact=ROOT/structure['artifact_directory']
        build=load(artifact/'build-report.json')
        assert structure['passed'] and build['passed']
        assert hashlib.sha256((artifact/'build-report.json').read_bytes()).hexdigest()==structure['build_report_sha256']
        assert hashlib.sha256((artifact/'native-kernel.macho').read_bytes()).hexdigest()==structure['native_macho_sha256']==build['native_macho']['sha256']
        assert structure['undefined_symbol_count']==0 and structure['compile_record_count']==build['compile_records']
        assert not structure['prelink_executed'] and not structure['handset_executed'] and not structure['bootable_phone_image']
        report['native_kernel_host']=dict(passed=True,structure_report=str(native.relative_to(ROOT)),
            structure_report_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),artifact_directory=structure['artifact_directory'],
            sha256=structure['native_macho_sha256'],bytes=structure['native_macho_bytes'],compile_records=structure['compile_record_count'],
            undefined_symbols=0,prelink_executed=False,handset_executed=False,phone_boot_qualified=False)
    emulated=[]
    for path in sorted((ROOT/'UniXNU-raphael/evidence').glob('native-xnu-qemu-20*.json')):
        item=load(path);out=ROOT/item['artifact_directory']
        assert path.read_bytes()==(out/'report.json').read_bytes()
        assert hashlib.sha256((out/'native-kernel.macho').read_bytes()).hexdigest()==item['kernel_sha256']
        for evidence in item.get('evidence_files',[]):
            assert hashlib.sha256((out/evidence['path']).read_bytes()).hexdigest()==evidence['sha256']
        observed=load(out/'debugger-observation.json')
        assert item['debugger']==observed and not item['handset_executed'] and not item['full_xnu_boot_verified']
        if item['xnu_entry_verified']:
            assert observed['native_instruction_executed'] and observed['loaded_file_bytes_match']
        emulated.append(dict(report=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            passed=item['passed'],target=item['stop_at'],native_entry=item['xnu_entry_verified'],
            arm_init=item['xnu_arm_init_verified'],reached=observed['reached_symbols'],
            target_reached=observed['target_reached'],kernel_sha256=item['kernel_sha256'],handset_executed=False))
    report['native_kernel_emulator']=emulated
    crypto_path=ROOT/'UniXNU-raphael/evidence/native-crypto-verification.json'
    if crypto_path.exists():
        crypto=load(crypto_path)
        assert crypto['passed'] and crypto['default_post_and_registration_verified']
        assert not crypto['bsd_init_reached'] and not crypto['handset_executed'] and not crypto['provider_qualified']
        for key in ['source','build','qemu']:
            assert hashlib.sha256((ROOT/crypto[key]['path']).read_bytes()).hexdigest()==crypto[key]['sha256']
        report['native_source_crypto']=dict(verification=str(crypto_path.relative_to(ROOT)),
            verification_sha256=hashlib.sha256(crypto_path.read_bytes()).hexdigest(),result=crypto)
    report['emulated_runtime']['real_native_xnu_entry_verified']=any(x['native_entry'] for x in emulated)
    report['emulated_runtime']['real_native_xnu_kernel_bootstrap_reached']=any(x['passed'] and x['target']=='kernel_bootstrap' for x in emulated)
    refusal=ROOT/'UniXNU-raphael/evidence/boot-darwin-refusal-observation.json'
    if refusal.exists():
        item=load(refusal);binding=ROOT/item['source_binding']
        assert item['passed'] and item['refusal_lifecycle_verified'] and item['darwinboot_driver_started']
        assert hashlib.sha256(binding.read_bytes()).hexdigest()==item['source_binding_sha256']
        assert not any(item[k] for k in ['darwinboot_kernel_handoff_verified','xnu_executed','new_allocator_memory','valid_kernel_supplied','partition_writes_performed'])
        assert [x['stage'] for x in item['phases']]==[2,3,6]
        for phase in item['phases']:
            for key in ['immutable_attempt','handoff']:
                assert hashlib.sha256((ROOT/phase[key]).read_bytes()).hexdigest()==phase[key+'_sha256']
            assert phase['darwin']==load(ROOT/phase['immutable_attempt'])['darwin']
        final=item['phases'][-1]['darwin']
        assert final['passed'] and final['handset_executed'] and final['unloaded']==final['protocol_removed']==final['console_restored']==1 and final['exit_boot_services']==0
        assert hashlib.sha256((ROOT/item['cleanup']).read_bytes()).hexdigest()==item['cleanup_sha256']
        report['darwin_refusal_handset']=dict(observation=str(refusal.relative_to(ROOT)),sha256=hashlib.sha256(refusal.read_bytes()).hexdigest(),result=item)
        report['handset'].update(darwinboot_started=True,darwinboot_refusal_lifecycle_verified=True,darwinboot_kernel_handoff_verified=False,xnu_started=False)
    mapped_path=ROOT/'UniXNU-raphael/evidence/boot-ram-mapped-observation.json'
    if mapped_path.exists():
        mapped=load(mapped_path)
        assert mapped['passed'] and mapped['mapped_sparse_read_verified'] and mapped['before_and_after_cache_digests_equal']
        assert not any(mapped[key] for key in ['ram_written','new_allocator_memory','entire_window_tested','ownership_proven','handset_xnu_executed'])
        assert [phase['stage'] for phase in mapped['phases']]==[2,3]
        for phase in mapped['phases']:
            for key in ['source_binding','handoff','immutable_attempt']:
                assert hashlib.sha256((ROOT/phase[key]['path']).read_bytes()).hexdigest()==phase[key]['sha256']
            assert phase['mapped']['passed'] and phase['before']['passed']
        assert mapped['phases'][0]['mapped']['status']==1 and not mapped['phases'][0]['mapped']['mapped_reads_verified']
        final=mapped['phases'][-1]['mapped']
        assert final['status']==3 and final['read_translations']==final['write_denied']==final['completed']==256
        assert hashlib.sha256((ROOT/mapped['cleanup']['path']).read_bytes()).hexdigest()==mapped['cleanup']['sha256']
        report['ram_mapped_handset']=dict(observation=str(mapped_path.relative_to(ROOT)),sha256=hashlib.sha256(mapped_path.read_bytes()).hexdigest(),result=mapped)
        report['handset']['candidate_ram_readonly_wb_identity_map_sample_verified']=True
    cached = []
    for path in sorted((ROOT/'UniXNU-raphael/evidence').glob('boot-ram-cache-observation-pages*.json')):
        # Only the stable per-page-count indexes; dated immutable copies remain
        # linked independently inside each report.
        if path.stem.split('pages')[-1].isdigit():
            item = load(path)
            assert item['passed'] and item['cache_poc_maintenance_verified']
            assert item['all_tested_original_bytes_restored'] and item['read_only_mapping_restored']
            assert not any(item[k] for k in ['new_allocator_memory','cross_page_alias_tested','ownership_proven','handset_xnu_executed'])
            for phase in item['phases']:
                for key in ['source_binding','handoff','immutable_attempt']:
                    assert hashlib.sha256((ROOT/phase[key]['path']).read_bytes()).hexdigest() == phase[key]['sha256']
                assert phase['cache'] == load(ROOT/phase['handoff']['path'])['ram_cache']
            assert hashlib.sha256((ROOT/item['cleanup']['path']).read_bytes()).hexdigest() == item['cleanup']['sha256']
            cached.append(dict(observation=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), result=item))
    report['ram_cached_write_handset'] = cached
    report['handset']['reversible_cached_ram_tested_bytes'] = max((x['result']['tested_bytes'] for x in cached), default=0)
    cache_verification = ROOT/'UniXNU-raphael/evidence/ram-cache-independent-verification.json'
    if cache_verification.exists():
        verified = load(cache_verification)
        assert verified['passed'] and verified['maximum_tested_bytes'] == report['handset']['reversible_cached_ram_tested_bytes']
        for observation in verified['observations']:
            assert hashlib.sha256((ROOT/observation['observation']['path']).read_bytes()).hexdigest() == observation['observation']['sha256']
        report['ram_cached_write_independent_verification'] = dict(path=str(cache_verification.relative_to(ROOT)), sha256=hashlib.sha256(cache_verification.read_bytes()).hexdigest())
    timeout_verification = ROOT/'UniXNU-raphael/evidence/ram-cache-qemu-timeout-verification.json'
    if timeout_verification.exists():
        failures = load(timeout_verification)
        assert failures['negative_evidence_checks_passed'] and failures['all_full_range_runs_failed']
        assert len(failures['cases']) == 4
        for case in failures['cases']:
            assert not case['full_range_passed'] and not case['handset_executed']
            ref = case['failure_report']
            assert hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest() == ref['sha256']
        report['ram_cache_full_range_negative_evidence'] = dict(
            path=str(timeout_verification.relative_to(ROOT)),
            sha256=hashlib.sha256(timeout_verification.read_bytes()).hexdigest(),
            full_range_passed=False, all_four_simulator_runs_failed=True)
    # Preserve old failure evidence while exposing the distinct new full-window
    # execution; a historical negative report must not describe all current runs.
    full_cache = ROOT/'UniXNU-raphael/evidence/ram-cache-source-audit-pages65536.json'
    if full_cache.exists():
        audit = load(full_cache)
        assert audit['passed'] and audit['ram_cache_write_pages'] == 65536
        full_runs = {}
        for phase in ['2', '3']:
            reference = audit['qemu_reports'][phase]
            qpath = ROOT/reference['path']
            assert hashlib.sha256(qpath.read_bytes()).hexdigest() == reference['sha256']
            q = load(qpath)
            assert q['qemu_passed'] and q['ram_cache_write_pages'] == 65536
            full_runs[phase] = reference
        report['ram_cache_full_range_qemu'] = dict(
            audit=str(full_cache.relative_to(ROOT)), audit_sha256=hashlib.sha256(full_cache.read_bytes()).hexdigest(),
            passed=True, pages=65536, bytes=268435456, phases=full_runs,
            allocator_enabled=False, ownership_proven=False)
    if 'ram_cache_full_range_negative_evidence' in report:
        report['ram_cache_full_range_negative_evidence']['historical_only'] = True
        report['ram_cache_full_range_negative_evidence']['scope'] = 'Four older implementations/runs; independent of new positive results'
    report['limits']=('Version-bound SEC/DXE, inherited GOP, human-observed bounded menu and three single physical key presses are verified. '
        'ICC reads, masked physical timer source/restoration and one local PPI enable permission have independent evidence. '
        'Two read-only passes found standard Non-secure SPI/local enables and LPI switches off, without proving full GIC ownership. '
        'CNTP/PPI/HPPIR route and withdrawal with masked CPU IRQ are independently verified and restored. '
        'A single target physical timer IRQ and EOI with complete route restoration is verified. '
        'A bounded physical-only TimerArch with relative/periodic/cancel and stopped-IRQ checks is independently verified and restored. '
        'The fixed complete UniXNURun executes a two-second synthetic exit configuration, changes and restores the full framebuffer, with a separate user visibility confirmation. '
        'A separately version-bound full-manager run verifies physical Up/Down/Enter with user observation and zero automatic keys. Reversible page diagnostics verify only their recorded byte ranges. Native XNU compiles and links on the host, without handset qualification. Fixed DarwinBoot driver refusal and unload are handset-verified separately, with zero ExitBootServices. No permanent TimerArch, complete UEFI, handset kernel handoff/XNU or full RAM ownership claim.')
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(target)


if __name__ == '__main__':
    main()
