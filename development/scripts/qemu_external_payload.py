"""RAM-only QEMU hardware-description derivative of a frozen handset FAT."""
import json,os,shutil,struct,hashlib,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from prepare_handset_payload import MAGIC

def make_fixture(out,source,adt):
 assert out.resolve().is_relative_to(ROOT/'artifacts/native-staging-qemu')
 image=out/'qemu-payload.img';hashes=out/'qemu-payload-hashes.bin'
 if source.get('trust_cache'):
  from native_trust import with_placeholder
  adt.write_bytes(with_placeholder(adt.read_bytes()))
 if source.get('ramdisk'):
  from native_ramdisk import with_placeholder
  adt.write_bytes(with_placeholder(adt.read_bytes()))
 shutil.copyfile(ROOT/source['payload'],image)
 subprocess.run(['mcopy','-o','-i',str(image),str(adt),'::/EFI/UniXNU/kernel.macho.adt'],env=dict(os.environ,MTOOLS_SKIP_CHECK='1'),check=True,capture_output=True)
 blob=image.read_bytes();table=struct.pack('<4Q',MAGIC,1,len(blob),len(blob)//4096)+b''.join(hashlib.sha256(blob[i:i+4096]).digest() for i in range(0,len(blob),4096));hashes.write_bytes(table)
 result=dict(source,payload=str(image.relative_to(ROOT)),payload_sha256=sha(blob),hashes=str(hashes.relative_to(ROOT)),hashes_sha256=sha(table),adt=str(adt.relative_to(ROOT)),adt_sha256=sha(adt.read_bytes()),qemu_only=True,source_payload_sha256=source['payload_sha256'],scope='Only the ADT file differs; exact frozen native kernel; QEMU RAM preload, no handset UFS or MMIO')
 path=out/'qemu-payload-report.json';path.write_text(json.dumps(result,indent=2)+'\n');return path,result
