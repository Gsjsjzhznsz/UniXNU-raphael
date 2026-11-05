#!/usr/bin/env python3
"""Actual Keys.c transport under UBSan, bounded callbacks and negative cases."""
import ctypes as c,datetime as dt,json,struct,subprocess
from entry_probe import ROOT,sha
from input_probe import HEADER
from key_read import decode

def main():
    out=ROOT/'artifacts/key-read-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
    src=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelKeysLib/Keys.c';inc=ROOT/'sources/mu_basecore/MdePkg/Include'
    command=['gcc','-shared','-fPIC','-O1','-g','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=undefined','-I'+str(inc),'-I'+str(inc/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),str(src),'-o',str(out/'keys.so')]
    b=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(b.stdout+b.stderr);assert b.returncode==0,b.stderr.decode()
    lib=c.CDLL(str(out/'keys.so'));R=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p);W=c.CFUNCTYPE(None,c.c_uint64,c.c_uint32,c.c_void_p);T=c.CFUNCTYPE(c.c_uint64,c.c_void_p)
    lib.RaphaelCollectKeyRegisters.argtypes=[c.c_void_p,c.c_uint32,c.c_void_p,R,W,T,c.c_void_p]
    lib.RaphaelReadKeyState.argtypes=[c.c_void_p,c.c_void_p,R,W,T,c.c_void_p];lib.RaphaelReadKeyState.restype=c.c_bool
    lib.RaphaelKeyTransport.argtypes=[c.c_void_p,c.c_uint32,c.c_void_p];lib.RaphaelKeyTransport.restype=c.c_bool
    baseline=json.loads((ROOT/'UniXNU-raphael/evidence/boot-input-map-observation.json').read_text())['input_probe']
    input_words=[baseline[k] for k in HEADER]+[0]*1024
    for row in baseline['map']:input_words[len(HEADER)+row['apid']]=row['raw'];input_words[len(HEADER)+512+row['apid']]=row['owner_raw']
    pon=baseline['observer_base']+0x80*baseline['pon_apid'];vol=baseline['observer_base']+0x80*baseline['volume_apid'];freq=19200000;cases=[]
    class Guarded(c.Structure):_fields_=[('before',c.c_uint64),('words',c.c_uint64*56),('after',c.c_uint64)]
    def case(name,status=3,changes=None,hw_status=1,delay=0,clock_step=1,clock_start=0,values=None,state=None):
        words=list(input_words)
        for at,value in (changes or {}).items():words[HEADER.index(at) if isinstance(at,str) else at]=value
        inp=(c.c_uint32*len(words))(*words);result=Guarded();result.before=result.after=0x123456789abcdef0
        trace=[];bad=[];current=[None];polls=[0];ticks=[clock_start];bytes_by_offset={4:0x10,5:0x11,0x40:0,0x46:0x80,0x10:1};bytes_by_offset.update(values or {})
        @R
        def read(at,ctx):
            trace.append(('read',at))
            if current[0] is None:bad.append('read before command');return 0
            base,cmd=current[0]
            if at==base+8:
                polls[0]+=1;return 0 if polls[0]<=delay else hw_status
            if at==base+0x18:
                if base==pon:return (state[1] if state is not None else 0)
                return state[0] if state is not None else bytes_by_offset[(cmd>>4)&255]
            bad.append(at);return 0
        @W
        def write(at,v,ctx):
            trace.append(('write',at,v));current[0]=(at,v);polls[0]=0
            if at not in [pon,vol] or v not in [(1<<27)|(x<<4) for x in [4,5,0x40,0x46,0x10]]:bad.append((at,v))
        @T
        def counter(ctx):ticks[0]=(ticks[0]+clock_step)&((1<<64)-1);return ticks[0]
        if state is None:
            lib.RaphaelCollectKeyRegisters(inp,freq,c.byref(result,Guarded.words.offset),read,write,counter,None)
            d=dict(zip(['version','status','transactions','completed','start','end','timeout_ticks','error'],result.words))
            assert d['status']==status,(name,d)
            if status==1:assert not trace
            if status==3:
                decoded=decode(struct.pack('>56Q',*result.words),baseline,freq)
                assert len([t for t in trace if t[0]=='write'])==6
                assert decoded['gpio_input_configuration_verified']
            if status==4:assert len([t for t in trace if t[0]=='write'])==1
        else:
            transport=c.create_string_buffer(40);assert lib.RaphaelKeyTransport(inp,freq,transport)
            key=c.c_uint32(0xffffffff);assert lib.RaphaelReadKeyState(transport,c.byref(key),read,write,counter,None)
            expected=(0 if state[0]&1 else 1)|(2 if state[1]&2 else 0)|(4 if state[1]&1 else 0)
            assert key.value==expected,(name,key.value,expected)
            assert [t for t in trace if t[0]=='write']==[('write',vol,0x08000100),('write',pon,0x08000100)]
        assert result.before==result.after==0x123456789abcdef0 and not bad,(name,bad)
        cases.append(dict(name=name,passed=True,mocked_mmio=True,actual_c_executed=True,operations=len(trace)))
    case('six exact register reads and independent decoder')
    case('delayed successful DONE',delay=4)
    case('counter wrap',clock_start=(1<<64)-5)
    for value in [3,5,9,15]:case('completion error '+hex(value),4,hw_status=value)
    case('time bounded no DONE',4,delay=1000000,clock_step=1920)
    case('stopped counter iteration bound',4,delay=1000000,clock_step=0)
    for key,val in [('version',0),('status',1),('hardware_version',0),('ee',6),('count',0),('count',513),('pon_owner',1),('volume_owner',1),('pon_matches',0),('volume_matches',0),('gpio_flags',0),('pon_sid',16),('volume_sid',16),('pon_address',0x10010),('volume_address',0xc511),('observer_base',0),('observer_base',baseline['observer_base']+1),('observer_size',4),('pon_apid',512),('volume_apid',512)]:
        case('reject invalid '+key+' '+hex(val),1,changes={key:val})
    case('reject wrong selected PPID',1,changes={len(HEADER)+baseline['pon_apid']:1})
    case('reject mismatched selected owner',1,changes={len(HEADER)+512+baseline['volume_apid']:1})
    for vg in [0,1]:
        for ps in [0,1,2,3]:case('key state '+str((vg,ps)),state=(vg,ps))
    inputs=[src,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/Library/RaphaelKeysLib.h',ROOT/'scripts/validate_key_read.py',ROOT/'scripts/key_read.py']
    report=dict(passed=True,case_count=len(cases),cases=cases,undefined_behavior_sanitizer=True,guard_canaries_verified=True,command=command,handset_executed=False,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs])
    for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/key-read-host.json']:p.write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,cases=len(cases)));print(out)
if __name__=='__main__':main()
