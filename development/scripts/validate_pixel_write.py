#!/usr/bin/env python3
"""Execute actual patch C against simulated RAM, checking full restoration and bounds."""
import ctypes as c
import datetime as dt
import json
import struct
import subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from pixel_probe import WORDS,FIELDS as PF
from pixel_write import decode,FIELDS


def main():
    out=ROOT/'artifacts/pixel-write-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
    prior=json.loads((ROOT/'UniXNU-raphael/evidence/pixel-probe-host.json').read_text())
    source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/PixelWrite.c';command=list(prior['command'])
    command.insert(command.index('-o'),str(source));command[-1]=str(out/'pixel-write.so')
    run=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,run.stderr.decode()
    lib=c.CDLL(str(out/'pixel-write.so'));rt=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p)
    wt=c.CFUNCTYPE(None,c.c_uint64,c.c_uint32,c.c_void_p);ct=c.CFUNCTYPE(c.c_uint64,c.c_void_p)
    Pixels=c.c_uint32*WORDS;Result=c.c_uint64*len(FIELDS)
    lib.RaphaelTestPixelPatch.argtypes=[c.POINTER(Pixels),c.POINTER(Result),rt,wt,ct,c.c_uint64,c.c_uint64,c.c_void_p]
    initial=dict(version=1,status=6,width=1080,height=2340,stride=4320,base_low=0x100000,
                 extent=4320*2340,counter_frequency=1000,grid=64,pixel_count=4096,refresh_count=32)
    addresses=[initial['base_low']+y*4320+x*4 for y in range(128) for x in range(256)]
    cases=[]
    def case(name,status,changes=None,reject_stack=False,drop_write=False):
        p=Pixels();header=dict(initial);header.update(changes or {})
        for k,v in header.items():p[PF.index(k)]=v
        memory={a:(a^0x12345678)&0xffffffff for a in addresses};original=dict(memory);events=[];counter=[0]
        @rt
        def read(a,context):
            assert a in memory,(name,hex(a));events.append(('r',a));return memory[a]
        @wt
        def write(a,v,context):
            assert a in memory,(name,hex(a));events.append(('w',a))
            if drop_write and len(events)==32769:return
            memory[a]=v
        @ct
        def timer(context):counter[0]+=1000;return counter[0]
        result=Result();lib.RaphaelTestPixelPatch(c.byref(p),c.byref(result),read,write,timer,
                         1 if reject_stack else 0,1 if reject_stack else 0xffffffffffffffff,None)
        record=dict(zip(FIELDS,result));assert record['status']==status,(name,record)
        assert memory==original and record['active']==0 and record['backup']==0
        if status==7:
            assert events[:32768]==[('r',a) for a in addresses]
            assert events[32768:65536]==[('w',a) for a in addresses]
            assert events[65536:98304]==[('r',a) for a in addresses]
            assert events[98304:131072]==[('w',a) for a in addresses]
            assert events[131072:]==[('r',a) for a in addresses]
            decode(struct.pack('>'+'Q'*len(FIELDS),*result),dict(header=header))
        elif status in [1,2]:assert not events
        cases.append(dict(name=name,passed=True,status=status,reads=sum(e[0]=='r' for e in events),
                          writes=sum(e[0]=='w' for e in events),all_original_words_restored=True,mocked_hardware=True))
    case('exact save write verify wait restore verify sequence',7)
    case('failed pattern readback still restores every original',4,drop_write=True)
    for name,changes in [
        ('missing successful read-only proof',dict(status=1)),('incomplete pixels',dict(pixel_count=4095)),
        ('incomplete counters',dict(refresh_count=31)),('invalid timer',dict(counter_frequency=0)),
        ('small width',dict(width=128)),('small height',dict(height=64)),
        ('overflow width',dict(width=0x40000001)),('short stride',dict(stride=4)),
        ('unaligned base',dict(base_low=0x100001)),('out of 32-bit PA',dict(base_high=1)),
        ('extent mismatch',dict(extent=1))]:case(name,1,changes)
    case('backup must fit declared stack',2,reject_stack=True)
    inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPixelWrite.h',ROOT/'scripts/pixel_write.py',Path(__file__)]
    report=dict(kind='actual C reversible pixel patch host execution; mocked RAM',passed=True,case_count=len(cases),cases=cases,
        command=command,handset_executed=False,mmio_register_writes=False,
        source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs])
    for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/pixel-write-host.json']:p.write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,cases=len(cases)));print(out)


if __name__=='__main__':main()
