#!/usr/bin/env python3
"""Actual C route gate over this handset's nonce-bound snapshot and mutations."""
import ctypes as c
import datetime as dt
import json
import struct
import subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from validate_display_probe import Snapshot
from display_probe import recipe
from inspect_device import read_fdt,node_path
from pixel_probe import WORDS

def main():
    out=ROOT/'artifacts/gop-route-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
    prior=json.loads((ROOT/'UniXNU-raphael/evidence/pixel-probe-host.json').read_text())
    source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/GopRoute.c';command=list(prior['command'])
    command.insert(command.index('-o'),str(source));command[-1]=str(out/'gop-route.so')
    built=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(built.stdout+built.stderr)
    assert built.returncode==0,built.stderr.decode()
    lib=c.CDLL(str(out/'gop-route.so'));Pixels=c.c_uint32*WORDS
    lib.RaphaelSplashRouteReady.argtypes=[c.c_void_p,c.POINTER(Snapshot),c.POINTER(Pixels)]
    lib.RaphaelSplashRouteReady.restype=c.c_uint8
    handoff=json.loads((ROOT/'UniXNU-raphael/evidence/sec-pixel-write-handoff.json').read_text())
    blob=(ROOT/handoff['private_readback']/'after.dtb').read_bytes();assert sha(blob)==handoff['fdt_sha256']
    chosen=next(n for n in read_fdt(blob).walk() if node_path(n)=='/chosen')
    wire=chosen.properties['raphael,display-snapshot'];words=struct.unpack('>'+'Q'*(len(wire)//8),wire)
    pixel=chosen.properties['raphael,display-pixels'];pv=struct.unpack('>'+'I'*WORDS,pixel)
    plan=recipe(blob);mdp=plan['regions']['mdp']['base'];rt=plan['routing']
    ctl=mdp+rt['ctl'][0];mix=mdp+rt['mixer'][0];intf=mdp+rt['intf'][1];pp=mdp+rt['pp'][0]
    cases=[]
    def case(name,expect,edits=None,version=None,missing=None,duplicate=None,pixel_status=None):
        snap=Snapshot();snap.version,snap.status,snap.count=words[:3]
        for i in range(snap.count):snap.samples[i][:]=words[3+i*2:5+i*2]
        for i in range(snap.count):
            a,v=snap.samples[i]
            if edits and a in edits:snap.samples[i][1]=edits[a]
            if a==missing:snap.samples[i][0]=0
        if duplicate is not None:
            snap.samples[snap.count][:]=next(pair for pair in snap.samples[:snap.count] if pair[0]==duplicate)
            snap.count+=1
        if version is not None:snap.version=version
        p=Pixels(*pv)
        if pixel_status is not None:p[1]=pixel_status
        assert bool(lib.RaphaelSplashRouteReady(blob,c.byref(snap),c.byref(p)))==expect,name
        cases.append(dict(name=name,passed=True,accepted=expect,mocked_hardware=True))
    case('nonce-bound local VIG0 LM PP DSI opaque route',True)
    for name,changes in [
      ('pixel alpha dependence',{mix+rt['blend'][3]:0x402}),
      ('unsupported blend bits',{mix+rt['blend'][3]:0x10400}),
      ('transparent foreground',{mix+rt['blend'][3]+4:0}),
      ('nonzero background',{mix+rt['blend'][3]:0}),
      ('mixer geometry differs',{mix+4:1}),
      ('unhandled base stage',{ctl:0x01000001}),
      ('second rectangle',{ctl+0xa0:1}),
      ('no active interface',{ctl+0xf4:0}),
      ('multiple active interfaces',{ctl+0xf4:3}),
      ('undescribed interface',{ctl+0xf4:1<<31}),
      ('not command mode',{ctl+0x14:0}),
      ('unexpected pingpong mux',{intf+0x25c:15}),
      ('compressed panel path',{pp+0xa0:1}),
      ('TE disabled',{intf+0x284:0}),
      ('autorefresh disabled',{intf+0x2b4:1}),
      ('zero autorefresh count',{intf+0x2b4:0x80000000})]:case(name,False,changes)
    case('missing sampled blend',False,missing=mix+rt['blend'][3])
    case('duplicate sampled blend',False,duplicate=mix+rt['blend'][3])
    case('wrong wire version',False,version=3)
    case('incomplete pixel proof',False,pixel_status=5)
    inputs=[source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelFramebuffer.h',Path(__file__)]
    report=dict(passed=True,kind='actual C route gate with local register fixture; no MMIO access',case_count=len(cases),cases=cases,command=command,
      fixture_fdt_sha256=sha(blob),fixture_snapshot_sha256=sha(wire),handset_executed=False,
      source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs])
    for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/gop-route-host.json']:p.write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,cases=len(cases)));print(out)

if __name__=='__main__':main()
