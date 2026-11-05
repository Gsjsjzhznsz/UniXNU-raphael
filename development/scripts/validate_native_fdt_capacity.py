#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Exercise actual libfdt capacity with a verified returned handset FDT.
QEMU delta is used for its serialized size only; never phone execution proof.
"""
import argparse,ctypes,ctypes.util,datetime as dt,json,re,struct,tempfile
from pathlib import Path
from entry_probe import ROOT
from native_staging import NATIVE_RETURN_FDT_BYTES

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--handset-report',type=Path,required=True)
 p.add_argument('--qemu-report',type=Path,required=True)
 a=p.parse_args();phone=a.handset_report.resolve();qemu=a.qemu_report.resolve()
 assert phone.is_relative_to(ROOT/'evidence/private/android-return-run')
 assert qemu.is_relative_to(ROOT/'artifacts/native-staging-qemu')
 h=json.loads(phone.read_text());q=json.loads(qemu.read_text())
 assert h['passed'] and h['nonce_matched'] and h['native_early_verified'] and q['passed']
 raw=(phone.parent/'after.dtb').read_bytes()
 serial=(qemu.parent/'serial.log').read_bytes()
 wire=re.search(rb'NATIVE_EARLY_DELTA ([0-9a-f]+)',serial);assert wire
 delta=bytes.fromhex(wire[1].decode());assert len(delta)==q['native_early_observation']['delta_bytes']
 lib=ctypes.CDLL(ctypes.util.find_library('fdt'))
 lib.fdt_open_into.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int]
 lib.fdt_path_offset.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
 lib.fdt_setprop.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_int]
 lib.fdt_pack.argtypes=[ctypes.c_void_p]
 lib.fdt_check_full.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
 def exercise(capacity,worst=False):
  source=ctypes.create_string_buffer(raw);buffer=ctypes.create_string_buffer(capacity)
  opened=lib.fdt_open_into(source,buffer,capacity)
  if opened:return dict(capacity=capacity,worst_case=worst,events=[dict(operation="fdt_open_into",status=opened)],fit=False)
  node=lib.fdt_path_offset(buffer,b'/chosen');assert node>=0
  changes={'raphael,native-early-delta':bytes(0x100000) if worst else delta}
  if worst:changes.update({'raphael,native-pmap-tables':bytes(524288),'raphael,native-pmap-adt':bytes(65536),'raphael,sec-dxe-log':bytes(65536),'raphael,sec-dxe-map':bytes(16384)})
  events=[]
  for key,value in changes.items():
   payload=ctypes.create_string_buffer(value);status=lib.fdt_setprop(buffer,node,key.encode(),payload,len(value));events.append(dict(property=key,bytes=len(value),status=status))
   if status:return dict(capacity=capacity,worst_case=worst,events=events,fit=False)
  assert lib.fdt_pack(buffer)==0
  packed=struct.unpack_from('>I',buffer.raw,4)[0];assert lib.fdt_check_full(buffer,packed)==0
  return dict(capacity=capacity,worst_case=worst,events=events,fit=True,packed_bytes=packed,headroom=capacity-packed)
 old=exercise(0x110000);current=exercise(NATIVE_RETURN_FDT_BYTES);worst=exercise(NATIVE_RETURN_FDT_BYTES,True)
 # Historical smaller capacity is reported; its fit depends on the supplied run.
 assert current['fit'] and worst['fit']
 parent=ROOT/'artifacts/native-fdt-capacity';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 report=dict(passed=True,kind='actual libfdt capacity regression',handset_fdt_bytes=len(raw),handset_report=str(phone.relative_to(ROOT)),qemu_report=str(qemu.relative_to(ROOT)),delta_size_source='QEMU serialized record only',cases=[old,current,worst],handset_executed=False,source_files_modified=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
