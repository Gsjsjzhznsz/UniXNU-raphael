#!/usr/bin/env python3
"""Independent read-only GIC snapshot provenance and wire validation."""
import struct
from inspect_device import ROOT,read_fdt,registers,physical,node_path,number,sha

HEADER='version status reason read_count gicd gicd_bytes gicr gicr_bytes stride mpidr affinity frame_count boot_index ctlr typer iidr pidr2'.split()
FRAME='base typer ctlr iidr waker pidr2'.split()
SGI_OFFSETS=[0x80,0x100,0x200,0x300,0xd00,0xc00,0xc04,*range(0x400,0x420,4)]
SGI_NAMES=['group','enabled','pending','active','group_modifier','config_sgi','config_ppi',*['priority_'+str(i) for i in range(8)]]
WORDS=len(HEADER)+8*len(FRAME)+len(SGI_NAMES)


def recipe(blob):
 root=read_fdt(blob);compatible=root.strings('compatible')
 assert 'qcom,sm8150' in compatible or 'linux,dummy-virt' in compatible
 nodes=[n for n in root.walk() if b'arm,gic-v3' in n.properties.get('compatible',b'').split(b'\0')]
 assert len(nodes)==1
 n=nodes[0];n.strings('compatible');assert n.enabled() and 'interrupt-controller' in n.properties
 assert n.cells('#interrupt-cells')==[3] and n.cells('#redistributor-regions')==[1]
 spans=[(physical(n.parent,b,s),s) for b,s in registers(n)];assert len(spans)==2
 for a,s in spans:assert a>0 and s>0 and (a|s)%0x10000==0 and a+s<(1<<64)
 assert spans[0][0]+spans[0][1]<=spans[1][0] or spans[1][0]+spans[1][1]<=spans[0][0]
 stride=number(n.cells('redistributor-stride')) if 'redistributor-stride' in n.properties else 0
 if stride:assert stride>=0x20000 and stride%0x10000==0 and spans[1][1]%stride==0
 if 'qcom,sm8150' in compatible:assert stride>0
 return dict(gicd=spans[0][0],gicd_bytes=spans[0][1],gicr=spans[1][0],gicr_bytes=spans[1][1],stride=stride,node=node_path(n))


def affinity(mpidr):return ((mpidr>>32)&255)<<24|(mpidr&0xffffff)


def decode(raw,blob,expected_mpidr):
 assert len(raw)==WORDS*8
 words=struct.unpack('>'+'Q'*WORDS,raw);r=dict(zip(HEADER,words))
 assert r['version']==1 and r['status']==4 and r['reason']==0
 plan=recipe(blob)
 for k in ['gicd','gicd_bytes','gicr','gicr_bytes','stride']:assert r[k]==plan[k],k
 assert r['mpidr']==expected_mpidr and r['affinity']==affinity(expected_mpidr)
 assert 1<=r['frame_count']<=8 and r['boot_index']<r['frame_count']
 assert r['read_count']==4+6*r['frame_count']+len(SGI_NAMES)
 frames=[];at=r['gicr'];seen=set();start=len(HEADER)
 for i in range(8):
  f=dict(zip(FRAME,words[start+i*len(FRAME):start+(i+1)*len(FRAME)]))
  if i>=r['frame_count']:assert not any(f.values());continue
  assert f['base']==at and at>=r['gicr'] and at+0x20000<=r['gicr']+r['gicr_bytes']
  assert ((f['pidr2']>>4)&15) in (3,4) and f['pidr2']<=0xffffffff
  assert all(f[k]<=0xffffffff for k in ['ctlr','iidr','waker'])
  aff=f['typer']>>32;assert aff not in seen;seen.add(aff)
  assert bool(f['typer']&16)==(i+1==r['frame_count'])
  step=r['stride'] or (0x40000 if f['typer']&2 else 0x20000)
  assert step>=(0x40000 if f['typer']&2 else 0x20000)
  at+=step;frames.append(f)
 assert frames[r['boot_index']]['typer']>>32==r['affinity']
 assert ((r['pidr2']>>4)&15) in (3,4) and all(r[k]<=0xffffffff for k in ['ctlr','typer','iidr','pidr2'])
 sgi=dict(zip(SGI_NAMES,words[start+8*len(FRAME):]));assert all(v<=0xffffffff for v in sgi.values())
 return dict(**r,frames=frames,sgi=sgi,passed=True,write_callbacks_provided=False,
  interrupt_acknowledged=False,icc_registers_accessed=False,irq_delivery_verified=False,
  gic_state_restore_verified=False,complete_memory_ownership_verified=False)
