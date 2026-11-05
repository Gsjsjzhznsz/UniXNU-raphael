#!/usr/bin/env python3
"""Actual independent input C collector with mock MMIO, FDT mutations and decoder."""
import ctypes as c,datetime as dt,json,struct,subprocess
from entry_probe import ROOT,LIBFDT,sha
from input_probe import HEADER,MAX_APIDS,recipe,decode

def main():
    out=ROOT/'artifacts/input-probe-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
    src=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/InputProbe.c';core=ROOT/'sources/mu_basecore/MdePkg/Include'
    names={'FdtGetProp':'fdt_getprop','FdtParentOffset':'fdt_parent_offset','FdtPathOffset':'fdt_path_offset','FdtAddressCells':'fdt_address_cells','FdtSizeCells':'fdt_size_cells','FdtNodeOffsetByCompatible':'fdt_node_offset_by_compatible','FdtNodeOffsetByPhandle':'fdt_node_offset_by_phandle','FdtFirstSubnode':'fdt_first_subnode','FdtNextSubnode':'fdt_next_subnode'}
    command=['gcc','-shared','-fPIC','-O1','-g','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=undefined',
      '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),'-I'+str(LIBFDT)]
    command+=['-D'+k+'='+v for k,v in names.items()]
    command+=[str(src)]+[str(LIBFDT/(s+'.c')) for s in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_addresses']]+['-o',str(out/'input-probe.so')]
    run=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,run.stderr.decode()
    lib=c.CDLL(str(out/'input-probe.so'));cbtype=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p)
    words=len(HEADER)+MAX_APIDS*2
    class Guarded(c.Structure):_fields_=[('before',c.c_uint64),('words',c.c_uint32*words),('after',c.c_uint64)]
    lib.RaphaelCollectInputMap.argtypes=[c.c_void_p,c.c_void_p,cbtype,c.c_void_p]
    lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_path_offset.restype=c.c_int
    lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int];lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int]
    blob=(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes();p=recipe(blob);arb=p['arbiter'];soc='/soc'
    corebase=p['regions']['core']['base'];cfg=p['regions']['cnfg']['base'];count=(p['regions']['core']['size']-0x900)//4
    # Artificial maps exercise duplicate PPIDs and EE precedence; these are not hardware observations.
    table={2:(p['pon_sid']<<16)|((p['pon_address']>>8)<<8)|1,7:(p['volume_sid']<<16)|((p['volume_address']>>8)<<8)|1,9:(p['pon_sid']<<16)|((p['pon_address']>>8)<<8)|1,10:0x1000001}
    owners={2:3,7:0,9:0,10:2};cases=[]
    def be(*v):return struct.pack('>'+'I'*len(v),*v)
    def case(name,status,edits=(),version=0x50000000,map_override=None,owner_override=None,expect_reads=None,check_decoder=True):
        buf=c.create_string_buffer(len(blob)+65536);assert lib.fdt_open_into(blob,buf,len(buf))==0
        for path,key,value in edits:
            n=lib.fdt_path_offset(buf,path.encode());assert n>=0
            assert lib.fdt_setprop(buf,n,key.encode(),value,len(value))==0
        maps=dict(table if map_override is None else map_override);own=dict(owners if owner_override is None else owner_override)
        values={corebase:version};sequence=[corebase]
        if status in [4,5]:
            for i in range(count):
                values[corebase+0x900+4*i]=maps.get(i,0);sequence.append(corebase+0x900+4*i)
                if maps.get(i):values[cfg+0x700+4*i]=own.get(i,0);sequence.append(cfg+0x700+4*i)
        if status in [1,2]:sequence=[]
        if expect_reads is not None:sequence=expect_reads
        reads=[];bad=[]
        @cbtype
        def read(at,context):
            reads.append(at)
            if at not in values:bad.append(at)
            return values.get(at,0)
        result=Guarded();result.before=result.after=0x123456789abcdef0
        lib.RaphaelCollectInputMap(buf,c.byref(result,Guarded.words.offset),read,None)
        assert result.before==result.after==0x123456789abcdef0
        got=dict(zip(HEADER,result.words));assert got['status']==status,(name,got)
        assert reads==sequence,(name,reads,sequence);assert not bad,(name,bad)
        if check_decoder:
            raw=be(*result.words);dtb=bytes(buf)[:struct.unpack_from('>I',bytes(buf),4)[0]];d=decode(raw,dtb)
            assert d['status']==status
        cases.append(dict(name=name,passed=True,reads=len(reads),status=status,actual_c_executed=True,mocked_mmio=True,decoder_checked=check_decoder))
        return got
    a=case('v5 full map and EE-preferred duplicate',4);assert a['pon_apid']==9 and a['pon_matches']==2 and a['volume_apid']==7
    case('future v5 minor',4,version=0x50010000)
    for v in [0,0x30000000,0x4fffffff,0x60000000,0xffffffff]:case('unsupported version '+hex(v),3,version=v)
    case('empty mapping stops before target use',5,map_override={})
    case('missing volume PPID',5,map_override={2:table[2]})
    a=case('no owner match uses first PPID for read-only report',4,owner_override={2:3,7:3,9:4,10:2});assert a['pon_apid']==2
    for name,edits in [
      ('no compatible arbiter',[(arb,'compatible',b'unknown\0')]),
      ('disabled arbiter',[(arb,'status',b'disabled\0')]),
      ('missing EE',[(arb,'qcom,ee',b'')]),('invalid EE',[(arb,'qcom,ee',be(6))]),
      ('invalid channel',[(arb,'qcom,channel',be(6))]),('translated bus',[(soc,'ranges',be(0,0,0x1000,0xffffffff))]),
      ('wrong bus cells',[(soc,'#address-cells',be(2))]),
      ('bad region names',[(arb,'reg-names',b'core\0chnls\0unknown\0intr\0cnfg\0')]),
      ('unterminated region names',[(arb,'reg-names',b'core\0chnls\0obsrvr\0intr\0cnfg')]),
      ('truncated regions',[(arb,'reg',be(corebase,0x1100))]),
      ('unknown key controller',[(p['gpio_provider'],'compatible',b'unknown\0')]),
      ('disabled key provider',[(p['gpio_provider'],'status',b'disabled\0')]),
      ('wrong gpio cells',[(p['gpio_provider'],'#gpio-cells',be(3))]),
      ('gpio zero rejected',[(p['volume_source'],'gpios',be(0x66b,0,1))]),
      ('gpio exceeds physical range',[(p['volume_source'],'gpios',be(0x66b,11,1))]),
      ('gpio disallowed physical number',[(p['volume_source'],'gpios',be(0x66b,5,1))]),
      ('unsupported polarity',[(p['volume_source'],'gpios',be(0x66b,6,0))]),
      ('missing GPIO phandle',[(p['volume_source'],'gpios',be(0xdead,6,1))]),
      ('truncated GPIO spec',[(p['volume_source'],'gpios',be(0x66b,6))]),
      ('oversized debounce',[(p['volume_source'],'debounce-interval',be(1001))]),
      ('missing power key',[(p['pon_source']+'/qcom,pon_1','linux,code',be(1))]),
      ('wrong power PON type',[(p['pon_source']+'/qcom,pon_1','qcom,pon-type',be(1))]),
      ('missing volume down key',[(p['pon_source']+'/qcom,pon_2','linux,code',be(1))]),
      ('disabled PON',[(p['pon_source'],'status',b'disabled\0')])]:
        case(name,1 if name=='no compatible arbiter' else 2,edits=edits,check_decoder=name=='no compatible arbiter')
    original=[]
    for key in ['core','chnls','obsrvr','intr','cnfg']:original.extend([p['regions'][key]['base'],p['regions'][key]['size']])
    for name,index,value in [('oversized APID table',1,0x1104),('no APID span',1,0x900),('short owner region',9,0x700),('short observer region',5,0x80),('unaligned region',0,corebase+1),('overlapping owner region',8,corebase)]:
        reg=list(original);reg[index]=value;case(name,2,edits=[(arb,'reg',be(*reg))],check_decoder=False)
    inputs=[src,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelInputProbe.h',ROOT/'scripts/input_probe.py',ROOT/'scripts/validate_input_probe.py']
    report=dict(passed=True,case_count=len(cases),cases=cases,command=command,undefined_behavior_sanitizer=True,guard_canaries_verified=True,
        handset_executed=False,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],fdt_sha256=sha(blob))
    for target in [out/'report.json',ROOT/'UniXNU-raphael/evidence/input-probe-host.json']:target.write_text(json.dumps(report,indent=2)+'\n')
    print(dict(passed=True,cases=len(cases)));print(out)
if __name__=='__main__':main()
