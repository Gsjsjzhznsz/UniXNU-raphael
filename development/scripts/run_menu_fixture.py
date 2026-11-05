#!/usr/bin/env python3
"""Positive unchanged UniXNU renderer + actual menu adapter under AAVMF; synthetic input."""
import argparse,datetime as dt,json,pathlib,shutil,socket,subprocess,time,re
from entry_probe import ROOT,sha

def ppm_to_png(source,target):
    import struct,zlib
    magic,dimensions,maximum,pixels=source.read_bytes().split(b'\n',3)
    assert magic==b'P6' and maximum==b'255'
    width,height=map(int,dimensions.split());assert len(pixels)==width*height*3
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    scan=b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    target.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('build',type=pathlib.Path);parser.add_argument('--portrait',action='store_true');args=parser.parse_args();build=args.build.resolve()
    image=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/MenuFixture.efi';assert image.exists()
    out=ROOT/'artifacts/menu-fixture-qemu'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');boot=out/'esp/EFI/BOOT';boot.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(image,boot/'BOOTAA64.EFI');shutil.copyfile('/usr/share/AAVMF/AAVMF_VARS.fd',out/'vars.fd')
    qmp=out/'qmp.sock';log=out/'serial.log'
    command=['qemu-system-aarch64','-machine','virt','-cpu','cortex-a57','-m','512','-nographic','-monitor','none','-no-reboot','-net','none',
      '-drive','if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/AAVMF/AAVMF_CODE.fd',
      '-drive','if=pflash,format=raw,unit=1,file='+str(out/'vars.fd'),'-drive','if=none,id=esp,format=raw,file=fat:rw:'+str(out/'esp'),
      '-device','virtio-blk-device,drive=esp','-device','virtio-gpu-pci'+(',xres=1080,yres=2340' if args.portrait else ''),'-display','none','-qmp','unix:'+str(qmp)+',server=on,wait=off']
    captured=False;start_seen=None
    with log.open('xb') as f:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
        try:
            for _ in range(240):
                time.sleep(.25);raw=log.read_bytes()
                if b'MENU_FIXTURE_START' in raw and start_seen is None:start_seen=time.monotonic()
                if start_seen and not captured and time.monotonic()-start_seen>.65:
                    with socket.socket(socket.AF_UNIX) as s:
                        s.settimeout(3);s.connect(str(qmp));stream=s.makefile('rwb');stream.readline();stream.write(b'{"execute":"qmp_capabilities"}\n');stream.flush()
                        while 'return' not in json.loads(stream.readline()):pass
                        stream.write((json.dumps(dict(execute='screendump',arguments=dict(filename=str(out/'menu.ppm'))))+'\n').encode());stream.flush()
                        while True:
                            response=json.loads(stream.readline())
                            if 'return' in response or 'error' in response:break
                        captured=(out/'menu.ppm').exists()
                if b'MENU_FIXTURE_OK' in raw or b'MENU_FIXTURE_FAIL' in raw or process.poll() is not None:break
        finally:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    raw=log.read_bytes();passed=b'MENU_FIXTURE_OK' in raw and b'MENU_FIXTURE_FAIL' not in raw
    geometry=re.findall(r'MENU_FIXTURE_START synthetic keys; (\d+)x(\d+)',raw.decode(errors='replace'))
    if args.portrait:passed=passed and geometry==[('1080','2340')]
    b=json.loads((build/'report.json').read_text())
    report=dict(passed=passed,kind='positive UniXNU renderer and port menu adapter on AAVMF GOP; synthetic key events',handset_executed=False,
      image_sha256=sha(image.read_bytes()),command=command,screenshot_captured=captured,source_inputs=b['source_inputs'],upstream_inputs=b['upstream_inputs'],unixnu_revision=b['unixnu_revision'],
      geometry=geometry,portrait_requested=args.portrait,results=re.findall(r'MENU_FIXTURE_RESULT[^\r\n]*',raw.decode(errors='replace')),
      limits=['AAVMF supplies generic UEFI services and a virtual GOP','Physical PM8150 access and input are not covered','This adapter uses a bounded counter loop while platform timer architectural support is unfinished'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if captured:
        ppm_to_png(out/'menu.ppm',out/'menu.png')
    print(dict(passed=passed,screenshot=captured));print(out);assert passed,raw[-3500:].decode(errors='replace')
if __name__=='__main__':main()
