#!/usr/bin/env python3
"""Exact owned packed APFS Data sidecar, retaining the pinned loader format."""
import struct,zlib,sys
from entry_probe import ROOT,align,sha
from native_trust import property_offset,parse_adt,encode_adt

def validate_packed(raw):
 sys.path.insert(0,str(ROOT/'sources/UniXNU/drivers/DarwinBoot/Test'))
 from packed_ramdisk import regions
 assert 32<=len(raw)<=8*1048576
 logical,extents=regions(raw)
 assert logical in (512*1048576,1024*1048576) and extents and extents[0][0]==0
 assert bytes(extents[0][1][32:36])==b'NXSB'
 return dict(bytes=len(raw),logical_bytes=logical,crc32=zlib.crc32(raw),sha256=sha(raw),extent_count=len(extents),persistent=False)

def with_placeholder(raw):
 t=parse_adt(raw);memory=t['nodes']['chosen']['nodes']['memory-map']
 assert 'RAMDisk' not in memory['props'] and 'PackedRAMDisk' not in memory['props']
 memory['props']['PackedRAMDisk']=bytes(16);return encode_adt(t)

def bind_adt(raw,tree_physical,packed):
 m=validate_packed(packed);m.update(physical=align(tree_physical+len(raw),4096),adt_offset=property_offset(raw,'PackedRAMDisk'),source_adt_crc32=zlib.crc32(raw),source_adt_sha256=sha(raw))
 return apply_binding(raw,m),m

def apply_binding(raw,m):
 assert zlib.crc32(raw)==m['source_adt_crc32'] and sha(raw)==m['source_adt_sha256']
 offset=property_offset(raw,'PackedRAMDisk');assert offset==m['adt_offset']
 out=bytearray(raw);struct.pack_into('<2Q',out,offset,m['physical'],m['bytes']);return bytes(out)
