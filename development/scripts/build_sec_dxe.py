#!/usr/bin/env python3
"""Build and execute the minimal SEC/DXE diagnostic in QEMU only.

No handset image is accepted/generated here. Placements are derived from the
emulator's receiving Image and explicit budgets, never a different phone port.
"""
import datetime as dt
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time
import tempfile
from entry_probe import ROOT, SOURCE, LIBFDT, align, image_parameters, run, sha
from inspect_diagnostic_fd import inspect_fd, RETURN_GUID
from qemu_arch_probe import generate_resources, decode as decode_arch


def build_fixture(out, expect_fault=False, expected_stage=6, extra_defines=()):
    fixtures = ROOT / 'scripts/fixtures'
    inputs = [fixtures / 'entry_probe_kernel.S', fixtures / 'sec_dxe_kernel.c', SOURCE / 'Runtime.c']
    inputs += [LIBFDT / (name + '.c') for name in ['fdt', 'fdt_ro', 'fdt_rw', 'fdt_wip']]
    flags = ['-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-fpie',
             '-fvisibility=hidden', '-mgeneral-regs-only', '-mstrict-align',
             '-ffunction-sections', '-fdata-sections', '-I' + str(LIBFDT),
             '-DEXPECT_FAULT=' + str(int(expect_fault)), '-DEXPECTED_STAGE=' + str(expected_stage)]
    flags += list(extra_defines)
    objects = []
    for i, source in enumerate(inputs):
        obj = out / f'fixture-{i}.o'
        run(out, ['aarch64-linux-gnu-gcc', *flags, '-c', source, '-o', obj])
        objects.append(obj)
    elf = out / 'fixture.elf'
    run(out, ['aarch64-linux-gnu-gcc', '-nostdlib', '-static', '-no-pie',
              '-Wl,--build-id=none,--gc-sections,-T,' + str(fixtures / 'entry_probe_kernel.ld'),
              '-o', elf, *objects])
    run(out, ['aarch64-linux-gnu-objcopy', '-O', 'binary', elf, out / 'fixture.Image'])
    return (out / 'fixture.Image').read_bytes()


def run_case(out, original, raw, p, values, dtb=None, darwin_test=False, expected_stage=6, qemu_arch=None, gic_probe=False, icc_probe=False, icc_fault_test=False, timer_source_test=False, ppi_enable_probe=False, gic_enable_map=False, timer_route_test=False, timer_route_fault_test=False, timer_irq_test=False, physical_timer_arch=False, payload_test=False, ram_probe=None, memory_mb=512, visible_manager=False, manager_keys=False, ram_write_pages=0, ram_write_fault=False, ram_seed_pages=0, native_staging=False):
    import re
    base, fd, end = values['ImageBase'], values['FdBase'], values['ExtentEnd']
    image = bytearray(original)
    image.extend(bytes(end - base - len(image)))
    image[fd - base:fd - base + len(raw)] = raw
    qemu_entry_setup=None
    entry_target=fd
    if timer_route_test:
        from qemu_arch_probe import parse_resources
        resources=parse_resources(dtb.read_bytes())
        setup=ROOT/'scripts/fixtures/timer_route_entry.S'
        entry_target=values['ExtentBase']+0x800
        assert entry_target%4==0 and entry_target+512<=values['FdBase']
        command=['aarch64-linux-gnu-gcc','-c','-x','assembler-with-cpp',
                 '-DQEMU_GICR='+hex(resources['gicr']),'-DQEMU_TIMER_MASK='+hex(1<<resources['timer_phys']),
                 '-DQEMU_FD='+hex(fd),str(setup),'-o',str(out/'route-entry.o')]
        run(out,command)
        run(out,['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.text',out/'route-entry.o',out/'route-entry.bin'])
        code=(out/'route-entry.bin').read_bytes();assert len(code)<=512
        image[entry_target-base:entry_target-base+len(code)]=code
        qemu_entry_setup=dict(scope='QEMU-only initial conditions; never handset firmware',source=str(setup.relative_to(ROOT)),
            source_sha256=sha(setup.read_bytes()),binary_sha256=sha(code),bytes=len(code),address=entry_target,
            pmr=0xf0,local_group1_mask=1<<resources['timer_phys'],waker=0,command=command)
    struct.pack_into('<I', image, 0, 0x14000000 | ((entry_target - base) // 4))
    struct.pack_into('<Q', image, 16, len(image))
    restored = bytearray(image[:len(original)])
    struct.pack_into('<I', restored, 0, p['instruction'])
    struct.pack_into('<Q', restored, 16, p['image_size'])
    assert restored == original
    (out / 'diagnostic.Image').write_bytes(image)
    command = ['qemu-system-aarch64', '-machine', ('virt,gic-version=3,virtualization=off' if qemu_arch or gic_probe else 'virt,virtualization=off'), '-cpu', 'cortex-a76',
               '-m', str(memory_mb)+'M', '-nographic', '-no-reboot', '-semihosting-config', 'enable=on,target=native',
               '-kernel', str(out / 'diagnostic.Image'), '-append', 'fixture_cookie=unchanged']
    if dtb is not None:
        command += ['-dtb', str(dtb)]
    if ram_write_pages or ram_seed_pages:
        candidate=ram_probe['policy']['base']
        seed=b''.join(struct.pack('<Q',(candidate+i*8)^0x0123456789abcdef) for i in range((ram_write_pages or ram_seed_pages)*512))
        seed_path=out/'ram-original.bin';seed_path.write_bytes(seed)
        command+=['-device','loader,file='+str(seed_path)+',addr='+hex(candidate)]
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, timeout=(60 if ram_seed_pages>4096 else 15))
        log = result.stdout + result.stderr
        passed = result.returncode == 0 and b'SEC_DXE_FIXTURE_OK' in log and b'FAIL ' not in log
    except subprocess.TimeoutExpired as exc:
        log = (exc.stdout or b'') + (exc.stderr or b'')
        passed = False
    (out / 'serial.log').write_bytes(log)
    darwin = None
    if darwin_test:
        from darwin_probe import decode
        import re
        try:
            match = re.search(rb'DARWIN_WIRE ([0-9a-f]+)', log)
            assert match, 'Missing independent Darwin wire record'
            darwin = decode(bytes.fromhex(match[1].decode()), expected_stage)
            if expected_stage == 6:
                assert b'DARWINBOOT: loader v2 installed EL1' in log
                assert b'DARWINBOOT: boot refused: Load Error; firmware retained' in log
        except (AssertionError, ValueError) as error:
            passed = False
            darwin = dict(passed=False, validation_error=str(error))
    architecture = None
    if qemu_arch:
        import re
        try:
            match = re.search(rb'QEMU_ARCH_WIRE ([0-9a-f]+)', log)
            assert match, 'Missing independent QEMU architecture wire record'
            architecture = decode_arch(bytes.fromhex(match[1].decode()), expected_stage, qemu_arch['resources'])
        except (AssertionError, ValueError) as error:
            passed = False
            architecture = dict(passed=False, validation_error=str(error))
    icc = None
    enable_map = None
    if gic_enable_map:
        import re
        from gic_enable_map import decode as decode_enable_map
        enable_map_match=re.search(rb'GIC_ENABLE_MAP_WIRE ([0-9a-f]+)',log)
    ppi = None
    if ppi_enable_probe:
        import re
        from ppi_probe import decode as decode_ppi
        try:
            match=re.search(rb'PPI_WIRE ([0-9a-f]+)',log)
            assert match and dtb
            # GIC is decoded below from its independent wire.
            ppi_raw=bytes.fromhex(match[1].decode())
        except (AssertionError,ValueError) as error:
            passed=False;ppi=dict(passed=False,validation_error=str(error))
    timer_source = None
    if timer_source_test:
        import re
        from timer_source import decode as decode_timer_source
        try:
            match=re.search(rb'TIMER_SOURCE_WIRE ([0-9a-f]+)',log)
            freq=re.search(rb'ICC_FREQ (0x[0-9a-f]+)',log)
            assert match and freq
            timer_source=decode_timer_source(bytes.fromhex(match[1].decode()),int(freq[1],16),icc_fault_test)
        except (AssertionError,ValueError) as error:
            passed=False;timer_source=dict(passed=False,validation_error=str(error))
    if icc_probe:
        import re
        from icc_probe import decode as decode_icc
        try:
            match=re.search(rb'ICC_WIRE ([0-9a-f]+)',log)
            mp=re.search(rb'GIC_MPIDR (0x[0-9a-f]+)',log)
            freq=re.search(rb'ICC_FREQ (0x[0-9a-f]+)',log)
            assert match and mp and freq, "Missing independent ICC wire, MPIDR or frequency"
            icc=decode_icc(bytes.fromhex(match[1].decode()),int(mp[1],16),int(freq[1],16),icc_fault_test)
        except (AssertionError,ValueError) as error:
            passed=False;icc=dict(passed=False,validation_error=str(error))
    gic = None
    if gic_probe:
        import re
        from gic_probe import decode as decode_gic
        try:
            match = re.search(rb'GIC_WIRE ([0-9a-f]+)', log)
            mp = re.search(rb'GIC_MPIDR (0x[0-9a-f]+)', log)
            assert match and mp, 'Missing independent GIC snapshot or MPIDR'
            gic = decode_gic(bytes.fromhex(match[1].decode()), dtb.read_bytes(), int(mp[1], 16))
        except (AssertionError, ValueError) as error:
            passed = False
            gic = dict(passed=False, validation_error=str(error))
    if gic_enable_map:
        try:
            assert enable_map_match and gic and gic.get('passed')
            enable_map=decode_enable_map(bytes.fromhex(enable_map_match[1].decode()),gic)
        except (AssertionError,ValueError,KeyError) as error:
            passed=False;enable_map=dict(passed=False,validation_error=str(error))
    timer_route=None
    if timer_route_test:
        import re
        from timer_route import decode as decode_timer_route
        try:
            wire=re.search(rb'TIMER_ROUTE_WIRE ([0-9a-f]+)',log)
            assert wire and gic and enable_map and icc
            timer_route=decode_timer_route(bytes.fromhex(wire[1].decode()),dtb.read_bytes(),gic,enable_map,icc,timer_route_fault_test,timer_irq_test)
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            passed=False;timer_route=dict(passed=False,validation_error=str(error))
    timer_irq=None
    if timer_irq_test:
        from timer_irq import decode as decode_timer_irq,linked_window
        try:
            wire=re.search(rb'TIMER_IRQ_WIRE ([0-9a-f]+)',log)
            assert wire and timer_route
            timer_irq=decode_timer_irq(bytes.fromhex(wire[1].decode()),timer_route,icc,values,linked_window(out))
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            passed=False;timer_irq=dict(passed=False,validation_error=str(error))
    payload=None
    if payload_test:
        from payload_probe import decode as decode_payload
        try:
            wire=re.search(rb'PAYLOAD_WIRE ([0-9a-f]+)',log);assert wire
            payload=decode_payload(bytes.fromhex(wire[1].decode()),values,expected_stage,manager_keys=manager_keys,native_staging=native_staging)
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            passed=False;payload=dict(passed=False,validation_error=str(error))
    manager=None
    if physical_timer_arch and payload_test:
        from manager_probe import decode as decode_manager
        try:
            wire=re.search(rb'MANAGER_WIRE ([0-9a-f]+)',log);assert wire
            manager=decode_manager(bytes.fromhex(wire[1].decode()),expected_stage,payload,icc['cntfrq'],visible=visible_manager,manual=manager_keys)
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            passed=False;manager=dict(passed=False,validation_error=str(error))
    physical_timer=None
    if physical_timer_arch:
        from physical_timer import decode as decode_physical
        try:
            wire=re.search(rb'PHYSICAL_TIMER_WIRE ([0-9a-f]+)',log)
            assert wire
            physical_timer=decode_physical(bytes.fromhex(wire[1].decode()),expected_stage,gic,timer_route,icc)
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            passed=False;physical_timer=dict(passed=False,validation_error=str(error))
    if ppi_enable_probe and ppi is None:
        try:ppi=decode_ppi(ppi_raw,dtb.read_bytes(),gic)
        except (AssertionError,ValueError,KeyError) as error:
            passed=False;ppi=dict(passed=False,validation_error=str(error))
    manager_ui=None
    if visible_manager:
        from manager_ui import decode as decode_ui
        try:
            wire=re.search(rb'MANAGER_UI_WIRE ([0-9a-f]+)',log);assert wire
            manager_ui=decode_ui(bytes.fromhex(wire[1].decode()),expected_stage,qemu_model=True)
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            passed=False;manager_ui=dict(passed=False,validation_error=str(error))
    ram_read=None
    if ram_probe:
        from ram_read_probe import decode as decode_ram
        try:
            wire=re.search(rb'RAM_READ_WIRE ([0-9a-f]+)',log);assert wire
            ram_read=decode_ram(bytes.fromhex(wire[1].decode()),ram_probe['policy'])
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            passed=False;ram_read=dict(passed=False,validation_error=str(error))
    ram_write=None
    if ram_write_pages:
        from ram_write_probe import decode as decode_write
        try:
            wire=re.search(rb'RAM_WRITE_WIRE ([0-9a-f]+)',log);assert wire
            ram_write=decode_write(bytes.fromhex(wire[1].decode()),ram_probe['policy'],ram_write_pages,ram_write_fault)
        except (AssertionError,ValueError) as error:
            passed=False;ram_write=dict(passed=False,validation_error=str(error))
    return dict(command=command, passed=passed, manager_ui=manager_ui, ram_write=ram_write, ram_read=ram_read, payload=payload, manager=manager, physical_timer=physical_timer, qemu_entry_setup=qemu_entry_setup, timer_irq=timer_irq, timer_route=timer_route, gic_enable_map=enable_map, ppi=ppi, timer_source=timer_source, icc=icc, gic=gic, darwin=darwin, architecture=architecture, image_sha256=sha(image),
                wall_seconds=round(time.monotonic() - started, 3),
                checks=log.decode(errors='replace').splitlines(),
                pass_count=sum(x.startswith(b'PASS ') for x in log.splitlines()))


def build_firmware(out, values, identifier, scope, stop_stage=4, display_probe=False, smmu_probe=False, pixel_probe=False, pixel_write=False, experimental_gop=False, input_probe=False, input_read=False, input_protocol=False, menu_test=False, payload_test=False, darwin_test=False, qemu_arch=None, gic_probe=False, icc_probe=False, icc_fault_test=False, timer_source_test=False, ppi_enable_probe=False, gic_enable_map=False, timer_route_test=False, timer_route_fault_test=False, timer_irq_test=False, physical_timer_arch=False, ram_probe=None, visible_manager=False, manager_keys=False, ram_write_pages=0, ram_mapped_probe=False, ram_cache_write_pages=0, kernel_window=None, native_boot=None, android_return=None, sparse_arena=False, ufs_handoff=False, ufs_read=False, ufs_query_only=False, ufs_reset_on_error=False, ufs_read_lba=0, ufs_extent_plan=None, ufs_write_policy=None):
    assert not sparse_arena or (android_return and native_boot and not native_boot.get("handoff",True))
    assert not android_return or (kernel_window and stop_stage>=3 and not ram_probe)
    assert not android_return or not android_return.get("qemu") or scope=="QEMU only"
    assert not native_boot or (payload_test and kernel_window and not ram_probe)
    native_load_test=bool(native_boot and native_boot.get("load_test"))
    native_video=bool(native_boot and native_boot.get("video"))
    assert not native_video or (native_load_test and experimental_gop and display_probe and smmu_probe and pixel_probe and
        not any([visible_manager,manager_keys,input_probe,input_read,input_protocol,menu_test,pixel_write,qemu_arch,ram_probe]))
    assert not native_load_test or (sparse_arena and android_return and darwin_test and not native_boot.get("handoff",True))
    native_watchdog=native_boot.get('watchdog') if native_boot else None
    watchdog_seconds=native_watchdog.get('seconds',20) if native_watchdog else 20
    hardware_watchdog_return=bool(native_boot and native_boot.get('hardware_watchdog_return'))
    assert not hardware_watchdog_return or (native_watchdog and native_boot.get('platform_test') and native_boot.get('platform_stop')=='root-observer' and scope!='QEMU only'), 'Hardware reset return needs the qualified handset watchdog and UFS observer'
    assert watchdog_seconds in (20,), 'Explicit bounded native watchdog budget required'
    watchdog_map_fixture=bool(native_watchdog and native_watchdog.get('mapping_fixture'))
    assert not watchdog_map_fixture or (scope=='QEMU only' and ufs_read and stop_stage in [3,4] and android_return and android_return.get('qemu'))
    assert not native_watchdog or watchdog_map_fixture or (scope!='QEMU only' and (native_boot.get('platform_test') or (ufs_read and (stop_stage==3 or native_boot.get('external_payload_report')))))
    native_kalloc_zones=int(native_boot.get('kalloc_zones',0)) if native_boot else 0
    assert native_kalloc_zones in [0,200]
    native_platform_test=bool(native_boot and native_boot.get("platform_test"))
    assert not native_platform_test or native_boot.get("pmap_test")
    native_pmap_test=bool(native_boot and native_boot.get("pmap_test"))
    assert not native_pmap_test or native_boot.get("early_test")
    native_early_test=bool(native_boot and native_boot.get("early_test"))
    assert not native_early_test or native_boot.get("mmu_test")
    native_mmu_test=bool(native_boot and native_boot.get("mmu_test"))
    assert not native_mmu_test or native_boot.get("entry_test")
    native_entry_test=bool(native_boot and native_boot.get("entry_test"))
    assert not native_entry_test or native_boot.get("exit_complete")
    native_exit_complete=bool(native_boot and native_boot.get("exit_complete"))
    assert not native_exit_complete or (native_load_test and (physical_timer_arch or qemu_arch))
    native_handoff=bool(native_boot and native_boot.get("handoff",True))
    assert not native_handoff or darwin_test
    assert not native_boot or not native_boot.get("qemu_gate") or native_handoff
    assert not native_boot or not native_boot.get("qemu_gate") or scope=="QEMU only"
    assert 0<=ram_cache_write_pages<=65536 and (not ram_cache_write_pages or (ram_mapped_probe and not ram_write_pages))
    assert 0<=ram_write_pages<=65536 and (not ram_write_pages or ram_probe)
    assert not manager_keys or visible_manager
    assert not visible_manager or (physical_timer_arch and payload_test and experimental_gop and input_protocol and not menu_test)
    assert not ram_mapped_probe or (ram_probe and stop_stage in [2,3] and not ram_write_pages)
    assert not ram_probe or ((stop_stage==2 or ram_mapped_probe) and not any([display_probe,smmu_probe,pixel_probe,pixel_write,experimental_gop,input_probe,input_read,input_protocol,menu_test,payload_test,darwin_test,qemu_arch,gic_probe,icc_probe,timer_source_test,ppi_enable_probe,gic_enable_map,timer_route_test,timer_irq_test,physical_timer_arch]))
    assert not physical_timer_arch or (timer_irq_test and not qemu_arch and (visible_manager or native_video or not any([display_probe,input_probe])))
    assert not timer_irq_test or (timer_route_test and not timer_route_fault_test)
    assert not timer_route_fault_test or timer_route_test
    assert not timer_route_test or gic_enable_map
    assert not gic_enable_map or (icc_probe and (stop_stage==2 or physical_timer_arch) and not ppi_enable_probe and not timer_source_test and not icc_fault_test)
    assert not ppi_enable_probe or (icc_probe and stop_stage==2 and not timer_source_test and not icc_fault_test)
    assert not timer_source_test or (icc_probe and stop_stage==2)
    assert not icc_probe or (gic_probe and (stop_stage==2 or physical_timer_arch))
    assert not icc_fault_test or (icc_probe and scope=='QEMU only')
    if qemu_arch:
        assert scope == 'QEMU only' and payload_test
        assert not any([display_probe,smmu_probe,pixel_probe,pixel_write,experimental_gop,input_probe,input_read,input_protocol,menu_test])
    inputs = sorted(p for p in (ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg').rglob('*') if p.is_file())
    source_inputs = []
    for path in inputs:
        relative = path.relative_to(ROOT)
        snapshot = out / 'source-snapshot' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        raw_source = path.read_bytes()
        snapshot.write_bytes(raw_source)
        source_inputs.append(dict(path=str(relative), sha256=sha(raw_source)))
    upstream_inputs=[]
    for path in sorted((ROOT/'sources/UniXNU/package/UniXNUPkg').rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(ROOT);raw_source=path.read_bytes();snapshot=out/'source-snapshot'/relative
        snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(raw_source)
        upstream_inputs.append(dict(path=str(relative),sha256=sha(raw_source)))
    darwin_inputs=[]
    if darwin_test:
        assert payload_test and (scope == 'QEMU only' or physical_timer_arch or native_load_test), 'Handset refusal checks require bounded physical TimerArch and synthetic FAT'
        assert not any([input_protocol,visible_manager,manager_keys,ram_probe]) and (not experimental_gop or native_video), 'Darwin graphics require the independent native-video transaction'
        driver=ROOT/'sources/UniXNU/drivers/DarwinBoot'
        revision=subprocess.check_output(['git','-C',str(driver),'rev-parse','HEAD'],text=True).strip()
        assert revision=='3325e352d7df68a9f9ad74832ed94a6acbbd7390'
        for path in sorted((driver/'DarwinBootPkg').rglob('*')):
            if not path.is_file():continue
            raw_source=path.read_bytes();local=path.relative_to(driver)
            assert raw_source==subprocess.check_output(['git','-C',str(driver),'show',revision+':'+str(local)])
            relative=path.relative_to(ROOT);target=out/'source-snapshot'/relative
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw_source)
            darwin_inputs.append(dict(path=str(relative),sha256=sha(raw_source)))
    conf = out / 'Conf'
    conf.mkdir()
    core = ROOT / 'sources/mu_basecore'
    tools = core / 'BaseTools'
    for name in ['target', 'tools_def', 'build_rule']:
        shutil.copyfile(tools / 'Conf' / (name + '.template'), conf / (name + '.txt'))
    clang_dir = out / 'toolchain'
    clang_dir.mkdir()
    for name in ['clang', 'clang++', 'lld-link', 'llvm-lib', 'llvm-objcopy']:
        target = shutil.which(name)
        assert target, name
        (clang_dir / name).symlink_to(target)
    packages=[out/'source-snapshot/UniXNU-raphael/package/firmware',out/'source-snapshot/sources/UniXNU/package',core]
    if darwin_test:packages.insert(2,out/'source-snapshot/sources/UniXNU/drivers/DarwinBoot')
    env = dict(os.environ, WORKSPACE=str(out), EDK_TOOLS_PATH=str(tools), CONF_PATH=str(conf),
               PACKAGES_PATH=':'.join(map(str,packages)), PYTHON_COMMAND='python3',
               CLANG_BIN=str(clang_dir) + '/', SOURCE_DATE_EPOCH='1793088000',
               PATH=f'{tools / "BinWrappers/PosixLike"}:{tools / "Source/C/bin"}:' + os.environ['PATH'])
    payload_metadata=None
    external_payload=native_boot.get('external_payload_report') if native_boot else None
    if external_payload:
        from prepare_handset_payload import validate
        external_metadata=validate(Path(external_payload),Path(native_boot['kernel']),Path(native_boot['adt']))
        assert ufs_read and ufs_extent_plan and not ufs_query_only and not ufs_read_lba and not native_handoff
        from ufs_extent_plan import validate_manifest,inspect_policy
        plan=inspect_policy(Path(ufs_extent_plan).read_bytes())
        assert plan['file_bytes']==external_metadata['payload_bytes']
        source=json.loads((Path(ufs_extent_plan).parent/'extent-source.json').read_text())
        stage=json.loads((ROOT/source['stage_report']).read_text())
        disk=next(v for v in stage['disks'] if v['role']=='Payload')
        if external_metadata.get('qemu_only'):
            assert scope=='QEMU only' and android_return and android_return.get('qemu')
            assert Path(external_payload).resolve().is_relative_to(out.resolve())
            assert disk['sha256']==external_metadata['source_payload_sha256']
        else:assert disk['sha256']==external_metadata['payload_sha256']
        assert disk['target']==source['source_file']
        payload=ROOT/external_metadata['payload']
        payload_metadata=dict(image_sha256=external_metadata['payload_sha256'],bytes=external_metadata['payload_bytes'],
            external_payload_report=str(Path(external_payload).resolve().relative_to(ROOT)),
            external_payload_report_sha256=sha(Path(external_payload).read_bytes()),
            design='Immutable handset file streamed through owned UFS DMA with frozen SHA256 for every 4096-byte block')
    if payload_test and not external_payload:
        assert not menu_test and (not experimental_gop or visible_manager or native_video), 'GOP payload requires an explicit framebuffer transaction'
        stage=out/'payload-stage/EFI/UniXNU';stage.mkdir(parents=True)
        config='version = 1\n[boot]\ntimeout = 0\ndefault = "diagnostic-exit"\n[kits]\nautoload = false\n[[entry]]\nid = "diagnostic-exit"\ntitle = "Return to diagnostic"\ntype = "action"\naction = "exit"\n'
        if qemu_arch or physical_timer_arch:config=config.replace('timeout = 0','timeout = 2')
        if native_video:config=config.replace('[kits]', '[ui]\nconsole = "none"\n[kits]')
        if visible_manager:config=config.replace('[kits]', '[ui]\nconsole = \"graphics\"\ntitle = \"UniXNU\"\n[kits]')
        if manager_keys:
            config=config.replace('timeout = 2','timeout = 6').replace('Return to diagnostic','Return to Android')
            config+='[[entry]]\nid = "key-check-exit"\ntitle = "Key test alternate return"\ntype = "action"\naction = "exit"\n'
        (stage/'unixnu.toml').write_text(config)
        if native_boot:
            for name,key in [('kernel.macho','kernel'),('kernel.macho.adt','adt')]:
                shutil.copyfile(native_boot[key],stage/name)
        if darwin_test:
            invalid=struct.pack('<10I',0xfeedfacf,0x100000c,0,2,1,8,0,0,0x19,72)
            (stage/'invalid.macho').write_bytes(invalid)
        for item in [*stage.iterdir(),stage,stage.parent]:os.utime(item,(1793088000,1793088000))
        payload=out/'diagnostic-payload.img';m_env=dict(os.environ,MTOOLS_SKIP_CHECK='1',TZ='UTC')
        payload_commands=[['mformat','-C','-T',str(40960 if native_boot else 2048),'-v','RAPHDIAG','-N','5250484c','-i',str(payload),'::'],
                          ['mcopy','-i',str(payload),'-s','-Q','-m',str(stage.parent),'::/']]
        for cmd in payload_commands:subprocess.run(cmd,env=m_env,capture_output=True,check=True)
        assert payload.stat().st_size==(20*1024*1024 if native_boot else 1048576)
        payload_metadata=dict(image_sha256=sha(payload.read_bytes()),bytes=payload.stat().st_size,config_sha256=sha(config.encode()),commands=payload_commands,
            design=('Synthetic read-only FAT; full UniXNURun two-second IRQ countdown' if qemu_arch or physical_timer_arch else 'Synthetic read-only FAT inside reserved own FV; timeout=0 exits full UniXNURun without a timer requirement'))
    if ram_probe:
        from ram_read_probe import encode,policy
        rb=encode(ram_probe['policy']['base'],[(g['base'],g['bytes']) for g in ram_probe['policy']['guards']])
        assert policy(rb)==ram_probe['policy']
        (out/'ram-read-policy.bin').write_bytes(rb)
    command = ['build', '-p', 'RaphaelPkg/Diagnostic.dsc', '-a', 'AARCH64', '-b', 'DEBUG', '-t', 'CLANGPDB', '-n', '4']
    command += ['-D','RAPHAEL_UFS_PAYLOAD='+('TRUE' if external_payload else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_FAT_BYTES='+str(payload_metadata['bytes'] if external_payload else 20*1048576)]
    if external_payload:command += ['-D','RAPHAEL_UFS_PAYLOAD_HASHES='+str(ROOT/external_metadata['hashes'])]
    command += ['-D','RAPHAEL_SPARSE_ARENA='+('TRUE' if sparse_arena else 'FALSE')]
    if sparse_arena:command += ['-D','RAPHAEL_DOWNLOADED_END='+hex(values['StackBase']+values['StackSize'])]
    if native_boot and not native_handoff:
        import zlib
        kernel_bytes=Path(native_boot['kernel']).read_bytes()
        command += ['-D','RAPHAEL_STAGING_KERNEL_BYTES='+str(len(kernel_bytes)),'-D','RAPHAEL_STAGING_KERNEL_CRC='+hex(zlib.crc32(kernel_bytes))]
    command += ['-D','RAPHAEL_ANDROID_RETURN='+('TRUE' if android_return else 'FALSE')]
    command += ['-D','RAPHAEL_ANDROID_RETURN_QEMU='+('TRUE' if android_return and android_return.get('qemu') else 'FALSE')]
    if android_return:
        (out/'android-return-policy.bin').write_bytes(android_return['policy'])
        (out/'android-return.bin').write_bytes(android_return['stub'])
        command += ['-D','RAPHAEL_ANDROID_RETURN_POLICY='+str(out/'android-return-policy.bin'),'-D','RAPHAEL_ANDROID_RETURN_STUB='+str(out/'android-return.bin')]
    command += ['-D','RAPHAEL_FD_BLOCKS='+hex(values['FdSize']//4096)]
    command += ['-D','RAPHAEL_HARDWARE_WATCHDOG_RETURN='+('TRUE' if hardware_watchdog_return else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_WATCHDOG_BASE='+hex(native_watchdog['base'] if native_watchdog else 0),'-D','RAPHAEL_NATIVE_WATCHDOG_HZ='+str(native_watchdog['frequency'] if native_watchdog else 0),'-D','RAPHAEL_NATIVE_WATCHDOG_SECONDS='+str(watchdog_seconds)]
    command += ['-D','RAPHAEL_NATIVE_KALLOC_ZONES='+str(native_kalloc_zones)]
    command += ['-D','RAPHAEL_NATIVE_PLATFORM_TEST='+('TRUE' if native_platform_test else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_PMAP_TEST='+('TRUE' if native_pmap_test else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_EARLY_TEST='+('TRUE' if native_early_test else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_MMU_TEST='+('TRUE' if native_mmu_test else 'FALSE')]
    native_trust=None;native_ramdisk=None
    if native_load_test and external_payload and external_metadata.get('trust_cache'):
        native_trust=(ROOT/external_metadata['trust_cache']).read_bytes()
    if native_load_test and external_payload and external_metadata.get('ramdisk'):
        native_ramdisk=(ROOT/external_metadata['ramdisk']).read_bytes()
    if native_load_test:
        from native_load import make_policy as make_load_policy
        manifest,native_load_metadata=make_load_policy(Path(native_boot['kernel']).read_bytes(),Path(native_boot['adt']).read_bytes(),kernel_window,native_boot['frequency'],native_boot['affinity'],exit_complete=native_exit_complete,trust_cache=native_trust,ramdisk=native_ramdisk)
    if native_mmu_test:
        from native_mmu import make_policy as make_mmu_policy
        mmu_policy,mmu_metadata=make_mmu_policy(Path(native_boot['kernel']).read_bytes(),Path(native_boot['adt']).read_bytes(),kernel_window,native_boot['frequency'],native_boot['affinity'])
        if native_load_metadata.get('trust_cache'):mmu_metadata['trust_cache']=native_load_metadata['trust_cache']
        if native_load_metadata.get('ramdisk'):mmu_metadata['ramdisk']=native_load_metadata['ramdisk']
        (out/'native-mmu-policy.bin').write_bytes(mmu_policy)
        command += ['-D','RAPHAEL_NATIVE_MMU_POLICY='+str(out/'native-mmu-policy.bin')]
        if native_early_test:
            from native_early import make_policy as make_early_policy
            early_policy,early_metadata=make_early_policy(Path(native_boot['kernel']).read_bytes(),mmu_metadata,pmap=native_pmap_test,platform=native_platform_test,platform_stop=native_boot.get("platform_stop","startup"))
            observer_limit=early_metadata.get('observer_limit_polls')
            if observer_limit is not None and scope!='QEMU only':
                from native_watchdog_budget import from_adt
                pet_budget=from_adt(Path(native_boot['adt']).read_bytes())
                if pet_budget:
                    assert native_watchdog and watchdog_seconds==20 and native_boot.get('platform_stop')=='root-observer'
                    assert all(native_watchdog[k]==pet_budget[k] for k in ['base','frequency'])
                    assert observer_limit*100+5000<=pet_budget['budget_ms']
                    from native_early import image
                    assert '_raphael_native_watchdog_record' in image(Path(native_boot['kernel']).read_bytes())[1]
                    early_metadata['diagnostic_watchdog_budget']=pet_budget
                else:
                    assert native_watchdog and observer_limit*100+10000<=watchdog_seconds*1000, 'Observer requires an explicitly matched watchdog budget plus return margin'
            mmu_metadata['early']=early_metadata
            mmu_metadata['instrumentation']=early_metadata['instrumentation']
            (out/'native-early-policy.bin').write_bytes(early_policy)
            command+=['-D','RAPHAEL_NATIVE_EARLY_POLICY='+str(out/'native-early-policy.bin')]

    command += ['-D','RAPHAEL_NATIVE_ENTRY_TEST='+('TRUE' if native_entry_test else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_EXIT_COMPLETE='+('TRUE' if native_exit_complete else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_LOAD_TEST='+('TRUE' if native_load_test else 'FALSE')]
    assert 0<=ufs_read_lba<=0x00ffffffffffffff and (ufs_read or not ufs_read_lba)
    assert not ufs_read or ufs_handoff
    assert not ufs_query_only or ufs_read
    assert not ufs_reset_on_error or ufs_read
    command += ['-D','RAPHAEL_UFS_RESET_ON_ERROR='+('TRUE' if ufs_reset_on_error else 'FALSE')]
    command += ['-D','RAPHAEL_UFS_QUERY_ONLY='+('TRUE' if ufs_query_only else 'FALSE')]
    command += ['-D','RAPHAEL_UFS_READ_LBA='+str(ufs_read_lba)]
    command += ['-D','RAPHAEL_UFS_EXTENTS='+('TRUE' if ufs_extent_plan else 'FALSE')]
    if ufs_extent_plan:
        assert ufs_read and not ufs_query_only and not ufs_read_lba
        plan=Path(ufs_extent_plan).read_bytes();assert len(plan)==8384
        (out/'ufs-extent-policy.bin').write_bytes(plan)
        command += ['-D','RAPHAEL_UFS_EXTENT_POLICY='+str(out/'ufs-extent-policy.bin')]

    command += ['-D','RAPHAEL_UFS_WRITE_PROBE='+('TRUE' if ufs_write_policy else 'FALSE')]
    if ufs_write_policy:
        assert ufs_read and ufs_handoff and not ufs_query_only and not ufs_extent_plan and not native_load_test and stop_stage==3
        from ufs_write_probe import inspect_policy
        policy=Path(ufs_write_policy).read_bytes();inspect_policy(policy,ufs_read_lba)
        (out/'ufs-write-policy.bin').write_bytes(policy)
        command += ['-D','RAPHAEL_UFS_WRITE_POLICY='+str(out/'ufs-write-policy.bin')]
    command += ['-D','RAPHAEL_UFS_READ='+('TRUE' if ufs_read else 'FALSE')]
    command += ['-D','RAPHAEL_UFS_HANDOFF='+('TRUE' if ufs_handoff else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_VIDEO='+('TRUE' if native_video else 'FALSE')]
    if native_load_test:
        # Manifest was derived once above, including any exact sidecar fixup.
        (out/'native-load-policy.bin').write_bytes(manifest)
        command += ['-D','RAPHAEL_NATIVE_LOAD_POLICY='+str(out/'native-load-policy.bin')]
    command += ['-D','RAPHAEL_NATIVE_HANDOFF='+('TRUE' if native_handoff else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_BOOT='+('TRUE' if native_boot else 'FALSE')]
    command += ['-D','RAPHAEL_NATIVE_QEMU_GATE='+('TRUE' if native_boot and native_boot.get('qemu_gate') else 'FALSE')]
    command += ['-D','RAPHAEL_KERNEL_WINDOW='+('TRUE' if kernel_window else 'FALSE')]
    if kernel_window:
        from kernel_window import encode_policy
        policy_path=out/'kernel-window-policy.bin'
        policy_path.write_bytes(encode_policy(kernel_window))
        command += ['-D','RAPHAEL_KERNEL_WINDOW_POLICY='+str(policy_path)]
    for name, value in values.items():
        command += ['-D', f'RAPHAEL_{name.upper()}={value:#x}']
    command += ['-D','RAPHAEL_MANAGER_KEYS='+('TRUE' if manager_keys else 'FALSE')]
    command += ['-D','RAPHAEL_VISIBLE_MANAGER='+('TRUE' if visible_manager else 'FALSE')]
    command += ['-D','RAPHAEL_RAM_CACHE_WRITE_PAGES='+str(ram_cache_write_pages)]
    command += ['-D','RAPHAEL_RAM_MAPPED_PROBE='+('TRUE' if ram_mapped_probe else 'FALSE')]
    command += ['-D','RAPHAEL_RAM_WRITE_PAGES='+str(ram_write_pages)]
    command += ['-D','RAPHAEL_RAM_READ_PROBE='+('TRUE' if ram_probe else 'FALSE')]
    if ram_probe:command += ['-D','RAPHAEL_RAM_READ_POLICY='+str(out/'ram-read-policy.bin')]
    command += ['-D', 'RAPHAEL_TEST_ID=' + identifier]
    command += ['-D', 'RAPHAEL_STOP_AFTER_STAGE=' + str(stop_stage)]
    command += ['-D', 'RAPHAEL_DISPLAY_PROBE=' + ('TRUE' if display_probe else 'FALSE')]
    command += ['-D', 'RAPHAEL_SMMU_PROBE=' + ('TRUE' if smmu_probe else 'FALSE')]
    command += ['-D', 'RAPHAEL_PIXEL_PROBE=' + ('TRUE' if pixel_probe else 'FALSE')]
    command += ['-D','RAPHAEL_PIXEL_WRITE=' + ('TRUE' if pixel_write else 'FALSE')]
    command += ['-D','RAPHAEL_EXPERIMENTAL_GOP=' + ('TRUE' if experimental_gop else 'FALSE')]
    command += ['-D','RAPHAEL_INPUT_PROBE=' + ('TRUE' if input_probe else 'FALSE')]
    command += ['-D','RAPHAEL_INPUT_READ=' + ('TRUE' if input_read else 'FALSE')]
    command += ['-D','RAPHAEL_INPUT_PROTOCOL=' + ('TRUE' if input_protocol else 'FALSE')]
    command += ['-D','RAPHAEL_MENU_TEST=' + ('TRUE' if menu_test else 'FALSE')]
    command += ['-D','RAPHAEL_PAYLOAD_TEST=' + ('TRUE' if payload_test else 'FALSE')]
    command += ['-D','RAPHAEL_DARWIN_TEST=' + ('TRUE' if darwin_test else 'FALSE')]
    command += ['-D','RAPHAEL_QEMU_ARCH_TEST='+('TRUE' if qemu_arch else 'FALSE')]
    command += ['-D','RAPHAEL_GIC_PROBE='+('TRUE' if gic_probe else 'FALSE')]
    command += ['-D','RAPHAEL_PHYSICAL_TIMER_ARCH='+('TRUE' if physical_timer_arch else 'FALSE')]
    command += ['-D','RAPHAEL_TIMER_IRQ_TEST='+('TRUE' if timer_irq_test else 'FALSE')]
    command += ['-D','RAPHAEL_TIMER_ROUTE_FAULT_TEST='+('TRUE' if timer_route_fault_test else 'FALSE')]
    command += ['-D','RAPHAEL_TIMER_ROUTE_TEST='+('TRUE' if timer_route_test else 'FALSE')]
    command += ['-D','RAPHAEL_GIC_ENABLE_MAP='+('TRUE' if gic_enable_map else 'FALSE')]
    command += ['-D','RAPHAEL_PPI_ENABLE_PROBE='+('TRUE' if ppi_enable_probe else 'FALSE')]
    command += ['-D','RAPHAEL_TIMER_SOURCE_TEST='+('TRUE' if timer_source_test else 'FALSE')]
    command += ['-D','RAPHAEL_ICC_PROBE='+('TRUE' if icc_probe else 'FALSE')]
    command += ['-D','RAPHAEL_ICC_FAULT_TEST='+('TRUE' if icc_fault_test else 'FALSE')]
    if qemu_arch:
        for name,value in qemu_arch['resources'].items():command += ['-D','RAPHAEL_QEMU_'+name.upper()+'='+hex(value)]
    if payload_test:
        if native_boot and not external_payload:
            for i in range(2):
                part=out/('native-payload-part'+str(i)+'.bin')
                part.write_bytes(payload.read_bytes()[i*10*1024*1024:(i+1)*10*1024*1024])
                command += ['-D','RAPHAEL_PAYLOAD_PART'+str(i)+'='+str(part)]
            payload_metadata['kernel_sha256']=sha(Path(native_boot['kernel']).read_bytes())
            payload_metadata['adt_sha256']=sha(Path(native_boot['adt']).read_bytes())
        elif not native_boot:command += ['-D','RAPHAEL_PAYLOAD_IMAGE='+str(payload)]
    with (out / 'edk2-build.log').open('xb') as log:
        result = subprocess.run(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
    report = dict(kind='SEC/DXE diagnostic; incomplete UEFI platform', scope=scope, stop_stage=stop_stage,
                  ram_cache_write_pages=ram_cache_write_pages, ram_mapped_probe=ram_mapped_probe, ram_write_pages=ram_write_pages, manager_keys=manager_keys, visible_manager=visible_manager, ram_read_probe=bool(ram_probe), ram_read_evidence=ram_probe, display_probe=display_probe, smmu_probe=smmu_probe, pixel_probe=pixel_probe, pixel_write=pixel_write, experimental_gop=experimental_gop, input_probe=input_probe, input_read=input_read, input_protocol=input_protocol, menu_test=menu_test, payload_test=payload_test, payload=payload_metadata, darwin_test=darwin_test, darwin_inputs=darwin_inputs,
                  physical_timer_arch=physical_timer_arch, timer_irq_test=timer_irq_test, timer_route_fault_test=timer_route_fault_test, timer_route_test=timer_route_test, gic_enable_map=gic_enable_map, ppi_enable_probe=ppi_enable_probe, timer_source_test=timer_source_test, icc_probe=icc_probe,icc_fault_test=icc_fault_test, gic_probe=gic_probe, qemu_arch_test=bool(qemu_arch), qemu_arch=qemu_arch,
                  command=command, returncode=result.returncode, handset_executed=False,
                  core_revision=subprocess.check_output(['git', '-C', str(core), 'rev-parse', 'HEAD'], text=True).strip())
    # Capture source and compiler hashes even on build failure.
    report['source_inputs'] = source_inputs
    report['kernel_window'] = kernel_window
    report['sparse_arena'] = sparse_arena
    report['arena_grant'] = 'Separate explicit experimental arena grant; active input holes reserved' if sparse_arena else 'Downloaded extension only'
    report['android_return'] = bool(android_return)
    report['android_return_qemu'] = bool(android_return and android_return.get('qemu'))
    report['native_boot'] = bool(native_boot)
    report['native_handoff'] = native_handoff
    report['native_watchdog'] = native_watchdog if native_platform_test else None
    report['hardware_watchdog_return'] = hardware_watchdog_return
    report['return_evidence_scope'] = ('Hardware reset and independent UFS logs; no returned full native checkpoint' if hardware_watchdog_return else 'Original diagnostic handback')
    report['ufs_watchdog'] = native_watchdog if ufs_read else None
    report['ufs_watchdog_mapping_fixture'] = watchdog_map_fixture
    report['ufs_handoff'] = ufs_handoff
    report['ufs_extent_plan_sha256'] = sha(Path(ufs_extent_plan).read_bytes()) if ufs_extent_plan else None
    report['ufs_write_policy_sha256'] = sha(Path(ufs_write_policy).read_bytes()) if ufs_write_policy else None
    report['ufs_read_lba'] = ufs_read_lba
    report['ufs_read'] = ufs_read
    report['ufs_uncached_required'] = ufs_read
    report['ufs_query_only'] = ufs_query_only
    report['ufs_reset_on_error'] = ufs_reset_on_error
    report['native_kalloc_zones'] = native_kalloc_zones
    report['native_boot_arguments'] = '-v keepsyms=1 cpus=1'+(' kt_fixed_zones='+str(native_kalloc_zones) if native_kalloc_zones else '')
    report['native_platform_test'] = native_platform_test
    report['native_pmap_test'] = native_pmap_test
    report['native_early_test'] = native_early_test
    report['native_mmu_test'] = native_mmu_test
    if native_mmu_test:report['native_mmu_contract']=mmu_metadata
    report['native_entry_test'] = native_entry_test
    report['native_exit_complete'] = native_exit_complete
    report['native_load_test'] = native_load_test
    report['native_video'] = native_video
    if native_load_test:report['native_load_contract'] = native_load_metadata
    if native_entry_test:
        from native_entry import make_contract
        report['native_entry_contract']=make_contract(Path(native_boot['kernel']).read_bytes(),Path(native_boot['adt']).read_bytes(),kernel_window,native_boot['frequency'],native_boot['affinity'])
    report['native_qemu_gate'] = bool(native_boot and native_boot.get('qemu_gate'))
    report['upstream_inputs']=upstream_inputs
    report['inspector_sha256']=sha((ROOT/'scripts/inspect_diagnostic_fd.py').read_bytes())
    report['manager_ui_decoder_sha256']=sha((ROOT/'scripts/manager_ui.py').read_bytes())
    report['ram_write_decoder_sha256']=sha((ROOT/'scripts/ram_write_probe.py').read_bytes())
    report['ram_cache_decoder_sha256']=sha((ROOT/'scripts/ram_cache_write.py').read_bytes())
    report['ram_mapped_decoder_sha256']=sha((ROOT/'scripts/ram_mapped_probe.py').read_bytes())
    report['ram_read_decoder_sha256']=sha((ROOT/'scripts/ram_read_probe.py').read_bytes())
    report['manager_decoder_sha256']=sha((ROOT/'scripts/manager_probe.py').read_bytes())
    report['physical_timer_decoder_sha256']=sha((ROOT/'scripts/physical_timer.py').read_bytes())
    report['timer_irq_decoder_sha256']=sha((ROOT/'scripts/timer_irq.py').read_bytes())
    report['timer_route_decoder_sha256']=sha((ROOT/'scripts/timer_route.py').read_bytes())
    report['gic_enable_map_decoder_sha256']=sha((ROOT/'scripts/gic_enable_map.py').read_bytes())
    report['ppi_decoder_sha256']=sha((ROOT/'scripts/ppi_probe.py').read_bytes())
    report['architecture_decoder_sha256']=sha((ROOT/'scripts/qemu_arch_probe.py').read_bytes())
    report['builder_sha256']=sha(Path(__file__).read_bytes())
    report['receiver_source_sha256']=sha((ROOT/'scripts/fixtures/sec_dxe_kernel.c').read_bytes())
    if darwin_test:report['darwin_revision']='3325e352d7df68a9f9ad74832ed94a6acbbd7390'
    report['unixnu_revision']=subprocess.check_output(['git','-C',str(ROOT/'sources/UniXNU'),'rev-parse','HEAD'],text=True).strip()
    report['source_snapshot'] = 'source-snapshot/'
    report['compiled_from_source_snapshot'] = True
    report['compiler_sha256'] = sha(Path(shutil.which('clang')).resolve().read_bytes())
    if result.returncode:
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print((out / 'edk2-build.log').read_text()[-7000:])
        print(out)
        raise SystemExit(result.returncode)
    firmware = out / 'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd'
    raw = firmware.read_bytes()
    return raw, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stop-after-stage', type=int, choices=[2, 3, 4], default=4)
    parser.add_argument('--fdt-copy-capacity', type=lambda x: int(x, 0), default=0x110000,
                        help='QEMU-only FDT copy budget, including 64 KiB edit space')
    parser.add_argument('--manager-keys',action='store_true',help='Six-second full-manager physical key diagnostic with explicitly marked fallback')
    parser.add_argument('--visible-manager',action='store_true',help='Full manager plus inherited GOP/input; QEMU records explicit missing-hardware model')
    parser.add_argument('--display-probe', action='store_true', help='Read-only probe; stage 2 only')
    parser.add_argument('--smmu-probe', action='store_true', help='Append bounded read-only SMMU observations')
    parser.add_argument('--pixel-probe', action='store_true')
    parser.add_argument('--pixel-write', action='store_true')
    parser.add_argument('--experimental-gop', action='store_true')
    parser.add_argument('--input-probe', action='store_true')
    parser.add_argument('--input-read', action='store_true')
    parser.add_argument('--input-protocol', action='store_true')
    parser.add_argument('--menu-test', action='store_true')
    parser.add_argument('--darwin-test', action='store_true', help='QEMU-only driver load and invalid Mach-O return; requires --payload-test')
    parser.add_argument('--payload-test', action='store_true', help='QEMU-only initial headless read-only FAT integration')
    parser.add_argument('--physical-timer-arch',action='store_true',help='Physical-only TimerArch, gated by same-boot IRQ proof and restoration')
    parser.add_argument('--timer-irq-test',action='store_true',help='One-shot current-EL SPx physical timer IRQ/EOI and restoration')
    parser.add_argument('--timer-route-fault-test',action='store_true',help='QEMU-only exact-PC route access recovery test')
    parser.add_argument('--timer-route-test',action='store_true',help='Masked-CPU-IRQ CNTP/HPPIR route and restoration experiment')
    parser.add_argument('--gic-enable-map',action='store_true',help='Read-only two-pass SPI/local/LPI enable map')
    parser.add_argument('--ppi-enable-probe',action='store_true',help='Stage2 single-PPI enable/clear permission test; IRQ stays masked')
    parser.add_argument('--timer-source-test',action='store_true',help='Stage2 masked CNTP source/restore test; requires ICC/GIC probes')
    parser.add_argument('--icc-probe',action='store_true',help='Read-only, fault-aware ICC/timer register probe; requires GIC stage2')
    parser.add_argument('--icc-fault-test',action='store_true',help='QEMU-only intentional UDF reader recovery check')
    parser.add_argument('--gic-probe', action='store_true', help='Stage2-only read-only GIC snapshot from generated GICv3 FDT')
    parser.add_argument('--qemu-arch-test',action='store_true',help='QEMU-only CPU/GICv3/TimerArch and real IRQ events; requires payload')
    args = parser.parse_args()
    if args.manager_keys:args.visible_manager=True
    if args.visible_manager:
        args.physical_timer_arch=args.payload_test=args.display_probe=args.smmu_probe=args.pixel_probe=args.experimental_gop=args.input_probe=args.input_read=args.input_protocol=True
    if args.physical_timer_arch:
        args.gic_probe=args.icc_probe=args.gic_enable_map=args.timer_route_test=args.timer_irq_test=True
    assert not args.display_probe or args.stop_after_stage == 2 or args.experimental_gop
    assert not args.smmu_probe or args.display_probe
    assert not args.pixel_probe or args.smmu_probe
    assert not args.pixel_write or args.pixel_probe
    assert not args.experimental_gop or (args.pixel_probe and not args.pixel_write)
    assert not args.input_read or args.input_probe
    assert not args.input_protocol or args.input_read
    assert not args.menu_test or (args.experimental_gop and args.input_protocol)
    assert not args.payload_test or (not args.menu_test and (not args.experimental_gop or args.visible_manager))
    assert not args.darwin_test or args.payload_test
    assert not args.qemu_arch_test or (args.payload_test and not any([args.display_probe,args.smmu_probe,args.pixel_probe,args.pixel_write,args.experimental_gop,args.input_probe,args.input_read,args.input_protocol,args.menu_test]))
    assert not args.gic_probe or ((args.stop_after_stage == 2 or args.physical_timer_arch) and not args.qemu_arch_test and (args.visible_manager or not any([args.display_probe,args.input_probe])))
    assert not args.timer_irq_test or (args.timer_route_test and not args.timer_route_fault_test)
    assert not args.timer_route_fault_test or args.timer_route_test
    assert not args.timer_route_test or args.gic_enable_map
    assert not args.gic_enable_map or (args.icc_probe and not args.ppi_enable_probe and not args.timer_source_test and not args.icc_fault_test)
    assert not args.ppi_enable_probe or (args.icc_probe and not args.timer_source_test and not args.icc_fault_test)
    assert not args.timer_source_test or args.icc_probe
    assert not args.icc_probe or args.gic_probe
    assert not args.icc_fault_test or args.icc_probe
    expected_stage = 6 if args.stop_after_stage == 4 else args.stop_after_stage
    parent = ROOT / 'artifacts/sec-dxe-qemu'
    parent.mkdir(parents=True,exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
    generated=generate_resources(out) if args.qemu_arch_test or args.gic_probe else None
    qemu_arch=generated if args.qemu_arch_test else None
    original = build_fixture(out, expected_stage=expected_stage,
                             extra_defines=['-DEXPECT_VISIBLE_MANAGER='+str(int(args.visible_manager)),
                                            '-DEXPECT_MANAGER_KEYS='+str(int(args.manager_keys)),'-DEXPECT_PHYSICAL_TIMER='+str(int(args.physical_timer_arch)),'-DEXPECT_TIMER_IRQ='+str(int(args.timer_irq_test)),'-DEXPECT_TIMER_ROUTE_FAULT='+str(int(args.timer_route_fault_test)),'-DEXPECT_TIMER_ROUTE='+str(int(args.timer_route_test)),'-DEXPECT_GIC_ENABLE_MAP='+str(int(args.gic_enable_map)),'-DEXPECT_PPI='+str(int(args.ppi_enable_probe)),'-DEXPECT_TIMER_SOURCE='+str(int(args.timer_source_test)),'-DEXPECT_ICC='+str(int(args.icc_probe)),'-DEXPECT_ICC_FAULT='+str(int(args.icc_fault_test)),
                                            '-DEXPECT_GIC='+str(int(args.gic_probe)),
                                            '-DEXPECT_DISPLAY_PROBE=' + str(int(args.display_probe)),
                                            '-DEXPECT_SMMU_PROBE=' + str(int(args.smmu_probe)),
                                            '-DEXPECT_PIXEL_PROBE=' + str(int(args.pixel_probe)),
                                            '-DEXPECT_PIXEL_WRITE=' + str(int(args.pixel_write)),
                                            '-DEXPECT_GOP=' + str(int(args.experimental_gop)),
                                            '-DEXPECT_INPUT_PROBE='+str(int(args.input_probe)),
                                            '-DEXPECT_INPUT_READ='+str(int(args.input_read)),
                                            '-DEXPECT_INPUT_PROTOCOL='+str(int(args.input_protocol)),
                                            '-DEXPECT_PAYLOAD='+str(int(args.payload_test)),
                                            '-DEXPECT_DARWIN='+str(int(args.darwin_test)),
                                            '-DEXPECT_QEMU_ARCH='+str(int(args.qemu_arch_test))])
    p = image_parameters(original)
    # Emulator virt RAM is configured at 0x40000000; this is not a handset value.
    base = 0x40000000 + p['text_offset']
    extent = base + align(p['image_size'], 65536)
    fd = extent + 65536
    stack = fd + 0x300000
    arena = stack + 0x40000
    fdt = arena + 0x1000000
    assert 0x110000 <= args.fdt_copy_capacity <= 0x410000 and args.fdt_copy_capacity % 4096 == 0
    end = fdt + args.fdt_copy_capacity
    values = dict(ImageBase=base, ImageSize=p['image_size'], OriginalEntry=p['entry'],
                  OriginalInstruction=p['instruction'], ExtentBase=extent, ExtentEnd=end,
                  FdBase=fd, FdSize=0x300000, StackBase=stack, StackSize=0x40000,
                  ArenaBase=arena, ArenaSize=0x1000000, FdtBase=fdt, FdtSize=args.fdt_copy_capacity,
                  ContextBase=extent)
    (out / 'layout.json').write_text(json.dumps(dict(scope='QEMU only', values=values,
                                                   budgets_are_design_choices=True), indent=2) + '\n')
    raw, report = build_firmware(out, values, 'qemu-sec-dxe-v1', 'QEMU only', args.stop_after_stage, args.display_probe, args.smmu_probe, args.pixel_probe, args.pixel_write, args.experimental_gop, args.input_probe, args.input_read, args.input_protocol, args.menu_test, args.payload_test, args.darwin_test, qemu_arch, args.gic_probe, args.icc_probe, args.icc_fault_test, args.timer_source_test, args.ppi_enable_probe, args.gic_enable_map, args.timer_route_test, args.timer_route_fault_test, args.timer_irq_test, args.physical_timer_arch, visible_manager=args.visible_manager, manager_keys=args.manager_keys)
    structure = inspect_fd(raw, fd)
    if args.payload_test:
        asset=next(section for file in structure['files'] for section in file['sections'] if 'payload_sha256' in section)
        assert asset['payload_sha256']==report['payload']['image_sha256']
    (out / 'fd-inspection.json').write_text(json.dumps(structure, indent=2) + '\n')
    normal = run_case(out, original, raw, p, values, dtb=out/'qemu-virt.dtb' if generated else None, darwin_test=args.darwin_test, expected_stage=expected_stage, qemu_arch=qemu_arch, gic_probe=args.gic_probe, icc_probe=args.icc_probe, icc_fault_test=args.icc_fault_test, timer_source_test=args.timer_source_test, ppi_enable_probe=args.ppi_enable_probe, gic_enable_map=args.gic_enable_map, timer_route_test=args.timer_route_test, timer_route_fault_test=args.timer_route_fault_test, timer_irq_test=args.timer_irq_test, physical_timer_arch=args.physical_timer_arch, payload_test=args.payload_test, visible_manager=args.visible_manager, manager_keys=args.manager_keys)
    # Mutate only the diagnostic driver's entry instruction into BRK. Rebuild
    # the receiving fixture to require an exception record and restored state.
    executions = dict(normal=normal)
    if args.stop_after_stage == 4 and not qemu_arch and not args.physical_timer_arch:
        for fault_kind,label,opcode in [(1,'injected_brk',0xd4208420),(2,'unmapped_udf',0)]:
            fault_out = out / ('fault-injection' if fault_kind==1 else 'unmapped-udf-injection')
            fault_out.mkdir()
            fault_original = build_fixture(fault_out, expect_fault=fault_kind, extra_defines=[
                '-DEXPECT_DISPLAY_PROBE='+str(int(args.display_probe)),
                '-DEXPECT_SMMU_PROBE='+str(int(args.smmu_probe)),
                '-DEXPECT_PIXEL_PROBE='+str(int(args.pixel_probe)),
                '-DEXPECT_PIXEL_WRITE='+str(int(args.pixel_write)),
                '-DEXPECT_GOP='+str(int(args.experimental_gop)),
                '-DEXPECT_INPUT_PROBE='+str(int(args.input_probe)),
                                                '-DEXPECT_INPUT_READ='+str(int(args.input_read)),
                                                '-DEXPECT_INPUT_PROTOCOL='+str(int(args.input_protocol)),
                                                '-DEXPECT_PAYLOAD='+str(int(args.payload_test)),
                                                '-DEXPECT_DARWIN='+str(int(args.darwin_test)),
                                                '-DEXPECT_QEMU_ARCH='+str(int(args.qemu_arch_test))])
            assert image_parameters(fault_original) == p
            driver = next(x for x in structure['files'] if x['guid'] == RETURN_GUID)
            entry = next(x['pe']['entry_file_offset'] for x in driver['sections'] if 'pe' in x)
            fault_fd = bytearray(raw)
            struct.pack_into('<I', fault_fd, entry, opcode)  # BRK #0x421
            assert not fault_fd[driver['offset'] + 19] & 0x40, 'Must update FFS data checksum if enabled'
            inspect_fd(bytes(fault_fd), fd)
            fault = run_case(fault_out, fault_original, fault_fd, p, values, darwin_test=args.darwin_test, expected_stage=4)
            fault['mutated_fd_offset'] = entry
            fault['mutated_fd_sha256'] = sha(fault_fd)
            executions[label] = fault
    if qemu_arch or args.physical_timer_arch:report['legacy_brk_test']='Not executed: real CpuDxe owns vectors; old SEC handler injection is inapplicable'
    passed = all(x['passed'] for x in executions.values())
    report.update(firmware_bytes=len(raw), firmware_sha256=sha(raw),
                  structure_checked=True, qemu_passed=passed,
                  executions=executions)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    for name, execution in report['executions'].items():
        print(name, 'passed=', execution['passed'], 'checks=', execution['pass_count'])
        if not execution['passed']:
            print('\n'.join(execution['checks']))
    print(out)
    assert passed


if __name__ == '__main__':
    main()
