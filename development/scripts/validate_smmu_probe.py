#!/usr/bin/env python3
"""Execute actual display/SMMU C collectors with mock MMIO and local FDT mutations."""
import ctypes as c
import datetime as dt
import json
import struct
import subprocess
from entry_probe import ROOT, LIBFDT, sha
from display_probe import recipe as display_recipe, route_addresses, OFFSETS, decode
from smmu_probe import recipe, CB_OFFSETS
from validate_display_probe import Snapshot


def main():
    out=ROOT/'artifacts/smmu-probe-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    sources=[ROOT/('UniXNU-raphael/package/firmware/RaphaelPkg/Sec/'+s+'.c') for s in ['DisplayProbe','SmmuProbe']]
    names={'FdtGetProp':'fdt_getprop','FdtParentOffset':'fdt_parent_offset','FdtPathOffset':'fdt_path_offset',
           'FdtAddressCells':'fdt_address_cells','FdtSizeCells':'fdt_size_cells',
           'FdtNodeOffsetByCompatible':'fdt_node_offset_by_compatible','FdtNodeOffsetByPhandle':'fdt_node_offset_by_phandle',
           'FdtFirstSubnode':'fdt_first_subnode','FdtNextSubnode':'fdt_next_subnode'}
    core=ROOT/'sources/mu_basecore/MdePkg/Include'
    command=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar',
             '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),'-I'+str(LIBFDT)]
    command+=['-D'+k+'='+v for k,v in names.items()]
    command+=[str(s) for s in sources]+[str(LIBFDT/(s+'.c')) for s in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_addresses']]
    command+=['-o',str(out/'smmu-probe.so')]
    run=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,run.stderr.decode()
    lib=c.CDLL(str(out/'smmu-probe.so'));read_type=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p)
    for name in ['RaphaelCollectDisplay','RaphaelCollectSmmu']:
        getattr(lib,name).argtypes=[c.c_void_p,c.POINTER(Snapshot),read_type,c.c_void_p]
    lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_path_offset.restype=c.c_int
    lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int]
    lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int]
    blob=(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes()
    plan=recipe(blob);dp=display_recipe(blob);base=plan['smmu']['base'];size=plan['smmu']['size']
    sp=plan['smmu']['source'].split(':')[0];mp=plan['source'].split(':')[0]
    t0=plan['tbus'][0]['source'];t1=plan['tbus'][1]['source']
    gp=plan['tbus'][0]['power']['source'].split(':')[0]
    prefix=dp['gates']+[dp['regions']['mdp']['base']]
    prefix += [dp['regions']['mdp']['base']+p+o for p in dp['pipes'] for o in OFFSETS]+route_addresses(dp)
    assert len(prefix)==507
    initial=dict(zip(dp['gates'],[1,1<<31,1,1]));initial[dp['regions']['mdp']['base']]=0x50000001
    # These IDs and table values are artificial test inputs, never handset evidence.
    initial.update({a:1<<31 for a in plan['power_addresses']})
    initial.update({base+0x20:0x48000008,base+0x24:0x60000008,base+0x28:0x1000,
                    base+0x800:0x84200800,base+0xc00:2,base+0x1000+8:1<<16,base+0x1800+8:1})
    def be(*v):return struct.pack('>'+'I'*len(v),*v)
    def mutated(edits):
        b=c.create_string_buffer(len(blob)+65536);assert lib.fdt_open_into(blob,b,len(b))==0
        for path,key,value in edits:
            node=lib.fdt_path_offset(b,path.encode());assert node>=0
            assert lib.fdt_setprop(b,node,key.encode(),value,len(value))==0
        return b
    power=plan['power_addresses'];ids=[base+o for o in [0x20,0x24,0x28,0]]
    smrs=[base+0x800+i*4 for i in range(8)]
    stream=[smrs[0],base+0xc00]+smrs[1:]
    cb=base+size//2+2*0x1000
    contexts=[base+0x1000+8,base+0x1800+8]+[cb+o for o in CB_OFFSETS]
    full=power+ids+stream+contexts;cases=[];valid_words=None
    def case(name,status,sequence,changes=None,edits=(),decoder=True):
        nonlocal valid_words
        values=dict(initial);values.update(changes or {});reads=[]
        @read_type
        def read(address,context):reads.append(address);return values.get(address,0)
        result=Snapshot();b=mutated(edits)
        lib.RaphaelCollectDisplay(b,c.byref(result),read,None)
        first=list(reads);assert result.version==3
        lib.RaphaelCollectSmmu(b,c.byref(result),read,None)
        assert result.version==4 and result.status==status,(name,result.version,result.status,status)
        assert reads==first+sequence,(name,reads[len(first):],sequence)
        assert result.count==len(reads) and result.count<=1024
        words=[4,status,result.count]
        for i in range(result.count):words.extend(result.samples[i])
        if decoder:
            total=struct.unpack_from('>I',bytes(b),4)[0]
            decoded=decode(struct.pack('>'+'Q'*len(words),*words),bytes(b)[:total])
            assert decoded['gates_and_read_sequence_verified']
            if status>=10:assert decoded['smmu_probe']['read_sequence_verified']
            if name=='translation context enabled':assert decoded['smmu_probe']['contexts'][0]['translation_enabled']
            if name=='translation context disabled':assert not decoded['smmu_probe']['contexts'][0]['translation_enabled']
            if name=='translation context disabled':valid_words=words
        cases.append(dict(name=name,passed=True,status=status,reads=len(reads),extra_smmu_reads=len(sequence),
                          actual_c_executed=True,mocked_mmio=True,independent_decoder=decoder))
    case('translation context disabled',13,full)
    case('translation context enabled',13,full,{cb:1})
    case('first TBU power off',10,power[:1],{power[0]:0})
    case('second TBU power off',10,power,{power[1]:0})
    for name,changes in [
        ('no stream matching',{base+0x20:0x40000008}),
        ('no translation support',{base+0x20:0x08000008}),
        ('extended stream IDs rejected',{base+0x20:0x48000108}),
        ('zero groups',{base+0x20:0x48000000}),
        ('zero context banks',{base+0x24:0x60000000}),
        ('excess context banks',{base+0x24:0x60000081}),
        ('S2 count exceeds total',{base+0x24:0x60090008}),
        ('ID1 geometry differs from FDT',{base+0x24:0x50000008}),
        ('CB span exceeds half',{base+0x24:0xa0000009})]:
        case(name,11,power+ids,changes)
    case('duplicate stream match stops before second S2CR',12,power+ids+stream[:3],{smrs[1]:0x84200800})
    case('no stream matches',14,power+ids+smrs,{smrs[0]:0})
    case('partial stream coverage',14,power+ids+stream,{smrs[0]:0x80000800})
    case('invalid context bank',12,power+ids+stream[:2],{base+0xc00:8})
    case('reserved S2CR type',12,power+ids+stream[:2],{base+0xc00:3<<16})
    case('bypass has no context reads',13,power+ids+stream,{base+0xc00:1<<16})
    case('fault has no context reads',13,power+ids+stream,{base+0xc00:2<<16})
    # Split the four SIDs into two groups referencing one CB: it is read once.
    split=dict({smrs[0]:0x84000800,smrs[1]:0x84000820,base+0xc04:2})
    case('multiple groups share one bank',13,power+ids+stream[:3]+[base+0xc04]+stream[3:]+contexts,split)
    case('64K register pages derived from ID1',13,power+ids+stream+
         [base+0x10000+8,base+0x10800+8]+[base+size//2+2*0x10000+o for o in CB_OFFSETS],
         {base+0x24:0xa0000008})
    for name,edits in [
        ('missing IOMMU cells',[(sp,'#iommu-cells',b'')]),
        ('wrong IOMMU cells',[(sp,'#iommu-cells',be(1))]),
        ('invalid phandle',[(mp,'iommus',be(0xdead,0x800,0x420))]),
        ('truncated iommus',[(mp,'iommus',be(0x26,0x800))]),
        ('too many SID mask bits',[(mp,'iommus',be(0x26,0x800,0x1f))]),
        ('unsupported root compatible',[(sp,'compatible',b'unknown\0')]),
        ('disabled root',[(sp,'status',b'disabled\0')]),
        ('secure alias requested',[(sp,'calxeda,smmu-secure-config-access',b'')]),
        ('static CB requested',[(sp,'qcom,enable-static-cb',b'')]),
        ('unknown root clocks',[(sp,'clock-names',b'unknown\0')]),
        ('unknown root regulator',[(sp,'qcom,regulator-names',b'unknown\0')]),
        ('disabled related TBU',[(t0,'status',b'disabled\0')]),
        ('unknown TBU clock',[(t0,'clock-names',b'unknown\0')]),
        ('unnamed TBU clock',[(t0,'clocks',be(1))]),
        ('additional TBU regulator',[(t0,'qcom,regulator-names',b'vdd\0extra\0')]),
        ('unnamed root clock',[(sp,'clocks',be(1))]),
        ('duplicate TBU coverage',[(t1,'qcom,stream-id-range',be(0x800,0x800))]),
        ('missing TBU coverage',[(t1,'qcom,stream-id-range',be(0x1000,0x100))]),
        ('missing power provider',[(t0,'vdd-supply',be(0xdead))]),
        ('disabled power provider',[(gp,'status',b'disabled\0')]),
        ('wrong GDSCR size',[(gp,'reg',be(power[0],8))]),
        ('GDSCR outside GCC',[(gp,'reg',be(0xdead0000,4))]),
        ('wrong root reg name',[(sp,'reg-names',b'other\0')])]:
        case(name,9,[],edits=edits,decoder=False)
    case('display prerequisite stopped',3,[],{dp['gates'][0]:0})
    for label,change in [
        ('missing final wire sample',lambda w:w[:-2]),
        ('invented SMMU address',lambda w:w[:3+507*2]+[0xdead0000]+w[4+507*2:]),
        ('appended wire sample',lambda w:[w[0],w[1],w[2]+1]+w[3:]+[0xdead0000,0]),
        ('false complete status',lambda w:[w[0],14]+w[2:])]:
        words=change(valid_words)
        try:decode(struct.pack('>'+'Q'*len(words),*words),blob)
        except AssertionError:cases.append(dict(name=label,passed=True,decoder_rejection=True,mocked_mmio=True))
        else:raise AssertionError(label)
    inputs=sources+[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelDisplayProbe.h',
                    ROOT/'scripts/smmu_probe.py',ROOT/'scripts/display_probe.py',Path(__file__)]
    report=dict(kind='actual C SMMU collector host execution with mocked MMIO',passed=True,case_count=len(cases),cases=cases,
                source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],
                command=command,input_fdt_sha256=sha(blob),shared_object_sha256=sha((out/'smmu-probe.so').read_bytes()),
                handset_executed=False,mmio_writes=False)
    for path in [out/'report.json',ROOT/'UniXNU-raphael/evidence/smmu-probe-host.json']:
        path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,cases=len(cases),handset_executed=False)));print(out)


from pathlib import Path
if __name__=='__main__':main()
