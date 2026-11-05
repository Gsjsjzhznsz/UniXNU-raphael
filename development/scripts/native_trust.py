#!/usr/bin/env python3
"""Exact original TrustCache sidecar layout and loader ADT fixup contract."""
import struct,zlib
from entry_probe import align,sha

def validate_bundle(raw):
 raw=bytes(raw)
 assert 8<=len(raw)<=16*1048576
 count=struct.unpack_from('<I',raw)[0]
 assert 1<=count<=1024 and 4+4*count<=len(raw)
 offsets=struct.unpack_from('<'+str(count)+'I',raw,4)
 assert offsets[0]==4+4*count and list(offsets)==sorted(set(offsets))
 modules=[]
 for index,offset in enumerate(offsets):
  end=offsets[index+1] if index+1<count else len(raw)
  assert offset+24<=end<=len(raw)
  version=struct.unpack_from('<I',raw,offset)[0];entries=struct.unpack_from('<I',raw,offset+20)[0]
  assert version in (1,2) and entries>0
  stride=22 if version==1 else 24
  assert offset+24+entries*stride==end
  hashes=[raw[offset+24+i*stride:offset+44+i*stride] for i in range(entries)]
  assert hashes==sorted(set(hashes))
  modules.append(dict(version=version,entries=entries,offset=offset))
 return dict(bytes=len(raw),crc32=zlib.crc32(raw),sha256=sha(raw),modules=modules)

def parse_adt(raw):
 def node(at,depth):
  assert depth<32 and at+8<=len(raw)
  count,children=struct.unpack_from('<2I',raw,at);at+=8;props={};nodes={}
  assert count<=1024 and children<=1024
  for _ in range(count):
   assert at+36<=len(raw)
   name=raw[at:at+32].split(b'\0',1)[0].decode();size=struct.unpack_from('<I',raw,at+32)[0];at+=36
   assert name not in props and at+size<=len(raw)
   props[name]=raw[at:at+size];at=align(at+size,4)
  for _ in range(children):
   child,at=node(at,depth+1);name=child['props']['name'].rstrip(b'\0').decode()
   assert name not in nodes;nodes[name]=child
  return dict(props=props,nodes=nodes),at
 tree,end=node(0,0);assert end==len(raw);return tree

def encode_adt(tree):
 props=tree['props'];nodes=tree['nodes'];out=struct.pack('<2I',len(props),len(nodes))
 for name,value in props.items():
  key=name.encode();assert 0<len(key)<32
  out+=key.ljust(32,b'\0')+struct.pack('<I',len(value))+value+bytes((-len(value))%4)
 return out+b''.join(encode_adt(child) for child in nodes.values())

def with_placeholder(raw):
 tree=parse_adt(raw);chosen=tree['nodes']['chosen']
 memory=chosen['nodes'].setdefault('memory-map',dict(props={'name':b'memory-map\0'},nodes={}))
 assert memory['props'].get('TrustCache',bytes(16))==bytes(16)
 memory['props']['TrustCache']=bytes(16)
 return encode_adt(tree)

def property_offset(raw,key='TrustCache'):
 assert key in ('TrustCache','PackedRAMDisk')
 result=[]
 def node(at,path,depth):
  assert depth<32 and at+8<=len(raw)
  count,children=struct.unpack_from('<2I',raw,at);at+=8;props={};locations={}
  for _ in range(count):
   assert at+36<=len(raw)
   name=raw[at:at+32].split(b'\0',1)[0].decode();size=struct.unpack_from('<I',raw,at+32)[0];at+=36
   assert name not in props and at+size<=len(raw)
   props[name]=raw[at:at+size];locations[name]=at;at=align(at+size,4)
  here=path+(props['name'].rstrip(b'\0').decode(),)
  if here[-2:]==('chosen','memory-map') and key in props:
   assert props[key]==bytes(16);result.append(locations[key])
  for _ in range(children):at=node(at,here,depth+1)
  return at
 assert node(0,(),0)==len(raw) and len(result)==1
 return result[0]

def bind_adt(raw,tree_physical,bundle,ramdisk_bytes=0):
 metadata=validate_bundle(bundle);offset=property_offset(raw)
 address=align(tree_physical+len(raw),4096)+align(ramdisk_bytes,4096)
 metadata.update(adt_offset=offset,physical=address,source_adt_crc32=zlib.crc32(raw),source_adt_sha256=sha(raw))
 bound=apply_binding(raw,metadata)
 metadata['loaded_adt_crc32']=zlib.crc32(bound)
 return bound,metadata

def apply_binding(raw,metadata):
 assert zlib.crc32(raw)==metadata['source_adt_crc32'] and sha(raw)==metadata['source_adt_sha256']
 offset=property_offset(raw);assert offset==metadata['adt_offset']
 out=bytearray(raw);struct.pack_into('<2Q',out,offset,metadata['physical'],metadata['bytes']);return bytes(out)
