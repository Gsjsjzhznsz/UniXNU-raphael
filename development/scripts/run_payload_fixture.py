#!/usr/bin/env python3
"""Build/run unchanged UniXNU RAM disk, FAT, EFI handoff and full manager on AAVMF only."""
import argparse,datetime as dt,json,os,pathlib,re,shutil,socket,subprocess,time
from entry_probe import ROOT,sha
from source_pins import locked_revision
from run_menu_fixture import ppm_to_png

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manager-ui',action='store_true');args=parser.parse_args()
    out=ROOT/('artifacts/manager-ui-fixture-qemu' if args.manager_ui else 'artifacts/payload-fixture-qemu')/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False);snap=out/'snapshot';inputs=[];commands=[]
    core=ROOT/'sources/mu_basecore';up=ROOT/'sources/UniXNU'
    revisions={str(p.relative_to(ROOT)):subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip() for p in [core,up]}
    assert revisions['sources/mu_basecore']=='cfb93724a06ff86ff5ba971413368a7809ee42a5'
    assert revisions['sources/UniXNU']==locked_revision('UniXNU')
    for folder in ['tests/RaphaelTestPkg','sources/UniXNU/package/UniXNUPkg']+(['UniXNU-raphael/package/firmware/RaphaelPkg'] if args.manager_ui else []):
        for p in sorted((ROOT/folder).rglob('*')):
            if not p.is_file():continue
            relative=p.relative_to(ROOT);target=snap/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
            inputs.append(dict(path=str(relative),sha256=sha(p.read_bytes())))
    conf=out/'Conf';conf.mkdir()
    for name in ['target','tools_def','build_rule']:shutil.copyfile(core/'BaseTools/Conf'/(name+'.template'),conf/(name+'.txt'))
    tools=out/'toolchain';tools.mkdir()
    for name in ['clang','clang++','lld-link','llvm-lib','llvm-objcopy']:
        actual=shutil.which(name);assert actual,name;(tools/name).symlink_to(actual)
    env=dict(os.environ,WORKSPACE=str(out),CONF_PATH=str(conf),EDK_TOOLS_PATH=str(core/'BaseTools'),
        PACKAGES_PATH=':'.join(map(str, [snap/'tests', snap/'sources/UniXNU/package'] + ([snap/'UniXNU-raphael/package/firmware'] if args.manager_ui else []) + [core])),CLANG_BIN=str(tools)+'/',PYTHON_COMMAND='python3',
        SOURCE_DATE_EPOCH='1793088000',PATH=f'{core / "BaseTools/BinWrappers/PosixLike"}:{core / "BaseTools/Source/C/bin"}:'+os.environ['PATH'])
    def run(command,**kw):
        commands.append([str(x) for x in command]);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        return subprocess.run(command,check=True,**kw)
    command=['build','-p','RaphaelTestPkg/ManagerUiFixture.dsc' if args.manager_ui else 'RaphaelTestPkg/PayloadFixture.dsc','-a','AARCH64','-b','DEBUG','-t','CLANGPDB','-n','4']
    with (out/'build.log').open('xb') as f:
        run(command,cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT)
    binary=out/('Build/RaphaelManagerUiFixture/DEBUG_CLANGPDB/AARCH64' if args.manager_ui else 'Build/RaphaelPayloadFixture/DEBUG_CLANGPDB/AARCH64')
    esp=out/'esp';boot=esp/'EFI/BOOT';boot.mkdir(parents=True);shutil.copyfile(binary/('ManagerUiFixture.efi' if args.manager_ui else 'PayloadFixture.efi'),boot/'BOOTAA64.EFI')
    stage=out/'fat-stage';cfg=stage/'EFI/UniXNU';cfg.mkdir(parents=True);shutil.copyfile(binary/'PayloadProbe.efi',cfg/'PayloadProbe.efi')
    (cfg/'unixnu.toml').write_text('version = 1\n[boot]\ntimeout = 2\ndefault = "exit"\n[ui]\ntitle = "UniXNU"\n[kits]\nautoload = false\n[[entry]]\nid = "probe"\ntitle = "EFI probe"\ntype = "efi"\npath = "PayloadProbe.efi"\nargs = "raphael-fixture-only"\n[[entry]]\nid = "exit"\ntitle = "Return to fixture"\ntype = "action"\naction = "exit"\n')
    if args.manager_ui:
        # The two UI destinations must both exit. Keep the separate EFI child
        # solely for the earlier explicit payload handshake.
        path=cfg/'unixnu.toml';text=path.read_text()
        probe='[[entry]]\nid = "probe"\ntitle = "EFI probe"\ntype = "efi"\npath = "PayloadProbe.efi"\nargs = "raphael-fixture-only"\n'
        alternate='[[entry]]\nid = "alternate"\ntitle = "Alternate return"\ntype = "action"\naction = "exit"\n'
        assert probe in text;path.write_text(text.replace(probe,alternate)+probe)
    volume=esp/'payload.img';m_env=dict(os.environ,MTOOLS_SKIP_CHECK='1',TZ='UTC')
    run(['mformat','-C','-T','2048','-v','RAPHTEST','-N','5250484c','-i',str(volume),'::'],env=m_env,capture_output=True)
    for item in sorted(stage.iterdir()):run(['mcopy','-i',str(volume),'-s','-Q','-m',str(item),'::/'],env=m_env,capture_output=True)
    assert volume.stat().st_size==1048576
    shutil.copyfile('/usr/share/AAVMF/AAVMF_VARS.fd',out/'vars.fd');qmp=out/'qmp.sock'
    command=['qemu-system-aarch64','-machine','virt','-cpu','cortex-a57','-m','512','-nographic','-monitor','none','-no-reboot','-net','none',
      '-drive','if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/AAVMF/AAVMF_CODE.fd',
      '-drive','if=pflash,format=raw,unit=1,file='+str(out/'vars.fd'),'-drive','if=none,id=esp,format=raw,file=fat:rw:'+str(esp),
      '-device','virtio-blk-device,drive=esp','-device','virtio-gpu-pci,xres=1080,yres=2340','-display','none',
      '-qmp','unix:'+str(qmp)+',server=on,wait=off']
    commands.append(command);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    captured=False;seen=None;log=out/'serial.log'
    with log.open('xb') as f:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
        try:
            for _ in range(300):
                time.sleep(.2);raw=log.read_bytes()
                if b'PAYLOAD_FIXTURE_MENU' in raw and seen is None:seen=time.monotonic()
                if seen and not captured and time.monotonic()-seen>.5 and process.poll() is None:
                    with socket.socket(socket.AF_UNIX) as s:
                        s.settimeout(3);s.connect(str(qmp));stream=s.makefile('rwb');stream.readline()
                        for request in [dict(execute='qmp_capabilities'),dict(execute='screendump',arguments=dict(filename=str(out/'menu.ppm')))]:
                            stream.write((json.dumps(request)+'\n').encode());stream.flush()
                            while True:
                                response=json.loads(stream.readline())
                                if 'return' in response or 'error' in response:break
                    captured=(out/'menu.ppm').exists()
                if b'PAYLOAD_FIXTURE_FAILED' in raw or b'PAYLOAD_FIXTURE_OK' in raw or process.poll() is not None:break
        finally:
            if process.poll() is None:
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    raw=log.read_bytes();checks=re.findall(r'PAYLOAD_FIXTURE_(?:PASS|FAIL) [^\r\n]*',raw.decode(errors='replace'))
    passed=b'PAYLOAD_FIXTURE_OK' in raw and b'PAYLOAD_FIXTURE_FAIL' not in raw and len(checks)>=17
    if captured:ppm_to_png(out/'menu.ppm',out/'menu.png')
    report=dict(passed=passed,artifact_directory=str(out.relative_to(ROOT)),runner_sha256=sha(pathlib.Path(__file__).read_bytes()),screenshot_sha256=sha((out/'menu.png').read_bytes()) if captured else None,manager_input_results=re.findall(r'MANAGER_INPUT_FIXTURE_RESULT[^\r\n]*',raw.decode(errors='replace')),manager_ui_transaction=args.manager_ui,manager_ui_results=re.findall(r'MANAGER_UI_FIXTURE_RESULT[^\r\n]*',raw.decode(errors='replace')),host_build_passed=True,handset_executed=False,revisions=revisions,source_inputs=inputs,
      image_sha256=sha((binary/('ManagerUiFixture.efi' if args.manager_ui else 'PayloadFixture.efi')).read_bytes()),payload_probe_sha256=sha((binary/'PayloadProbe.efi').read_bytes()),
      fat_sha256=sha(volume.read_bytes()),fat_bytes=volume.stat().st_size,checks=checks,check_count=len(checks),screenshot_captured=captured,
      results=re.findall(r'PAYLOAD_FIXTURE_RESULT[^\r\n]*',raw.decode(errors='replace')),
      limits=['QEMU/AAVMF provides DiskIo/FAT, CPU and periodic timer architecture services',
              'Actual unchanged RAM-disk source entry uses a synthetic FDT and module-local HOB list',
              'No handset storage or handset full UniXNURun/DarwinBoot/XNU execution is established'])
    if args.manager_ui:
        passed=bool(passed and len(report['manager_ui_results'])==3 and len(report['manager_input_results'])==3 and report['check_count']>=23 and captured)
        report['passed']=passed
        (ROOT/'UniXNU-raphael/evidence/manager-ui-fixture-qemu.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(dict(passed=passed,checks=len(checks),screenshot=captured));print(out)
    assert passed,raw[-4500:].decode(errors='replace')
if __name__=='__main__':main()
