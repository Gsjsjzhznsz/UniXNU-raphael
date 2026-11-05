#!/usr/bin/env python3
"""Host execution of actual read-only C pixel collector, using artificial MMIO/memory."""
import ctypes as c
import datetime as dt
import json
import struct
import subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from validate_display_probe import Snapshot
from display_probe import recipe as display_recipe,decode as display_decode
from smmu_probe import recipe
from pixel_probe import GRID,ROUNDS,WORDS,decode


def main():
    out=ROOT/'artifacts/pixel-probe-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    prior=json.loads((ROOT/'UniXNU-raphael/evidence/smmu-probe-host.json').read_text())
    source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/PixelProbe.c'
    command=list(prior['command']);command.insert(command.index('-o'),str(source));command[-1]=str(out/'pixel-probe.so')
    run=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,run.stderr.decode()
    lib=c.CDLL(str(out/'pixel-probe.so'));rt=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p);ct=c.CFUNCTYPE(c.c_uint64,c.c_void_p)
    for name in ['RaphaelCollectDisplay','RaphaelCollectSmmu']:
        getattr(lib,name).argtypes=[c.c_void_p,c.POINTER(Snapshot),rt,c.c_void_p]
    Array=c.c_uint32*WORDS
    lib.RaphaelCollectPixels.argtypes=[c.c_void_p,c.POINTER(Snapshot),c.POINTER(Array),rt,ct,c.c_uint32,c.c_void_p]
    lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_path_offset.restype=c.c_int
    lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int]
    lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int]
    blob=(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes()
    sp=recipe(blob);dp=display_recipe(blob);mdp=dp['regions']['mdp']['base'];pipe=mdp+dp['pipes'][0]
    base=sp['smmu']['base'];cb=base+sp['smmu']['size']//2+2*4096
    intf=mdp+dp['routing']['intf'][1];ctl=mdp+dp['routing']['ctl'][0]
    # Explicit artificial format, source, routing and IDs; source address is
    # derived from the local reserved-memory description, not another board.
    from inspect_device import read_fdt,node_path,registers,physical
    n=next(n for n in read_fdt(blob).walk() if node_path(n)=='/reserved-memory/cont_splash_region')
    pa,length=registers(n)[0];pa=physical(n.parent,pa,length)
    initial=dict(zip(dp['gates'],[1,1<<31,1,1]));initial[mdp]=0x50000001
    initial.update({a:1<<31 for a in sp['power_addresses']})
    initial.update({base+0x20:0x48000008,base+0x24:0x60000008,base+0x800:0x84200800,
        base+0xc00:2,base+0x1008:1<<16,base+0x1808:1,pipe:(2340<<16)|1080,pipe+0xc:(2340<<16)|1080,
        pipe+0x14:pa,pipe+0x24:4320,pipe+0x30:0x237ff,pipe+0x34:0x03020001,pipe+0x38:0x80000000,
        ctl+0x14:1<<17,ctl+0xf4:2,intf+0x284:1,intf+0x2b4:0x80000001})
    expected=[pa+(y*2339//63)*4320+(x*1079//63)*4 for y in range(GRID) for x in range(GRID)]
    expected += [intf+o for i in range(ROUNDS) for o in [0x26c,0xac,0x298,0x2b0]]
    cases=[]
    def case(name,status,changes=None,edits=(),frequency=19200000,decoder=False,stalled=False):
        values=dict(initial);values.update(changes or {});reads=[];counter=[0]
        @rt
        def read(a,context):
            reads.append(a)
            if pa<=a<pa+4320*2340:return a^0xaabbccdd
            return values.get(a,0)
        @ct
        def timer(context):
            if not stalled:counter[0]+=38400
            return counter[0]
        b=c.create_string_buffer(len(blob)+65536);assert lib.fdt_open_into(blob,b,len(b))==0
        for path,key,value in edits:
            node=lib.fdt_path_offset(b,path.encode());assert node>=0
            assert lib.fdt_setprop(b,node,key.encode(),value,len(value))==0
        s=Snapshot();lib.RaphaelCollectDisplay(b,c.byref(s),read,None);lib.RaphaelCollectSmmu(b,c.byref(s),read,None)
        reads.clear();result=Array();lib.RaphaelCollectPixels(b,c.byref(s),c.byref(result),read,timer,frequency,None)
        assert result[0]==1 and result[1]==status,(name,result[1],status)
        assert reads==(expected if status==6 else expected[:4096+4] if stalled else []),(name,len(reads))
        if decoder:
            words=[s.version,s.status,s.count]
            for i in range(s.count):words.extend(s.samples[i])
            display=display_decode(struct.pack('>'+'Q'*len(words),*words),blob)
            decoded=decode(struct.pack('>'+'I'*WORDS,*result),blob,display)
            assert decoded['cpu_sample_read_verified'] and decoded['unique_pixel_values']==GRID*GRID
        cases.append(dict(name=name,passed=True,status=status,reads=len(reads),actual_c_executed=True,mocked_hardware=True))
    case('bounded pixel grid plus time-ordered interface reads',6,decoder=True)
    for name,changes,status in [
        ('source scaling',{pipe+0xc:1},2),('crop',{pipe+8:1},2),('multi-plane',{pipe+0x18:1},2),
        ('short stride',{pipe+0x24:4},2),('wrong byte order',{pipe+0x34:0},2),
        ('compressed format',{pipe+0x30:0x800237ff},2),('secure source',{pipe+0x70:1},2),
        ('address outside reservation',{pipe+0x14:pa+length},2),
        ('translated context',{cb:1},3),('stage2 translation',{base+0x1008:3<<16},3),
        ('32 bit context',{base+0x1808:0},3),('client interface disabled',{base:1},3),
        ('missing stream',{base+0x800:0},1),('missing power',{sp['power_addresses'][0]:0},1),
        ('multiple active CTLs',{mdp+dp['routing']['ctl'][1]+0xf4:2},2),
        ('multiple interfaces',{ctl+0xf4:3},2),('no auto refresh',{intf+0x2b4:0},2)]:
        case(name,status,changes)
    def be(*v):return struct.pack('>'+'I'*len(v),*v)
    case('nonidentity reserved-memory bus',2,edits=[('/reserved-memory','ranges',be(0,0,1,0))])
    case('short splash region',2,edits=[('/reserved-memory/cont_splash_region','reg',be(0,pa,0,4096))])
    case('invalid frequency',2,frequency=0)
    case('stalled timer is bounded',5,stalled=True)
    inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPixelProbe.h',ROOT/'scripts/pixel_probe.py',Path(__file__)]
    report=dict(kind='actual pixel C collector host execution with artificial memory and MMIO',passed=True,
        cases=cases,case_count=len(cases),command=command,input_fdt_sha256=sha(blob),handset_executed=False,
        source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs])
    for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/pixel-probe-host.json']:
        p.write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,cases=len(cases)));print(out)


if __name__=='__main__':main()
