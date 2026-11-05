#!/usr/bin/env python3
"""Execute the actual C collector with mocked reads and mutated handset FDTs."""
import ctypes as c
import datetime as dt
import json
import struct
import subprocess
from pathlib import Path
from entry_probe import ROOT, LIBFDT, sha
from display_probe import recipe, decode, OFFSETS, route_addresses


class Snapshot(c.Structure):
    _fields_=[('version',c.c_uint64),('status',c.c_uint64),('count',c.c_uint64),
              ('samples',(c.c_uint64*2)*1024)]


def main():
    out=ROOT/'artifacts/display-probe-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/DisplayProbe.c'
    names={'FdtGetProp':'fdt_getprop','FdtParentOffset':'fdt_parent_offset',
           'FdtPathOffset':'fdt_path_offset','FdtAddressCells':'fdt_address_cells','FdtSizeCells':'fdt_size_cells',
           'FdtNodeOffsetByCompatible':'fdt_node_offset_by_compatible','FdtNodeOffsetByPhandle':'fdt_node_offset_by_phandle'}
    core=ROOT/'sources/mu_basecore/MdePkg/Include'
    command=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar',
             '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),
             '-I'+str(LIBFDT)]
    command += ['-D'+name+'='+target for name,target in names.items()]
    command += [str(source)]+[str(LIBFDT/(name+'.c')) for name in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_addresses']]
    command += ['-o',str(out/'display-probe.so')]
    run=subprocess.run(command,capture_output=True)
    (out/'build.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,run.stderr.decode()
    lib=c.CDLL(str(out/'display-probe.so'))
    read_type=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p)
    collect=lib.RaphaelCollectDisplay
    collect.argtypes=[c.c_void_p,c.POINTER(Snapshot),read_type,c.c_void_p]
    lib.fdt_path_offset.argtypes=[c.c_void_p,c.c_char_p];lib.fdt_path_offset.restype=c.c_int
    lib.fdt_setprop.argtypes=[c.c_void_p,c.c_int,c.c_char_p,c.c_void_p,c.c_int]
    lib.fdt_open_into.argtypes=[c.c_void_p,c.c_void_p,c.c_int]
    blob=(ROOT/'evidence/private/device/20261027T120325Z/live.dtb').read_bytes()
    plan=recipe(blob); mdp_path=plan['regions']['mdp']['source'].split(':')[0]
    def mutated(edits):
        buffer=c.create_string_buffer(len(blob)+65536)
        assert lib.fdt_open_into(blob,buffer,len(buffer))==0
        for path,key,value in edits:
            node=lib.fdt_path_offset(buffer,path.encode()); assert node>=0
            assert lib.fdt_setprop(buffer,node,key.encode(),value,len(value))==0
        return buffer
    def be(*values): return struct.pack('>'+'I'*len(values),*values)
    expected=plan['gates']+[plan['regions']['mdp']['base']]
    expected += [plan['regions']['mdp']['base']+p+o for p in plan['pipes'] for o in OFFSETS]
    expected += route_addresses(plan)
    cases=[]
    def case(name,status,sequence,edits=(),gate_values=(1,0x80000000,1,1), independent_decode=False, revision=0x50000001, extra_values=None):
        values=dict(zip(plan['gates'],gate_values)); reads=[]
        values[plan['regions']['mdp']['base']]=revision
        values.update(extra_values or {})
        @read_type
        def read(address,context):
            reads.append(address)
            return values.get(address,0)
        result=Snapshot(); buffer=mutated(edits)
        collect(buffer,c.byref(result),read,None)
        passed=result.version==3 and result.status==status and result.count==len(sequence) and reads==sequence
        assert passed,(name,result.version,result.status,result.count,reads)
        if independent_decode:
            words=[result.version,result.status,result.count]
            for i in range(result.count): words.extend(result.samples[i])
            decoded=decode(struct.pack('>'+'Q'*len(words),*words),blob)
            assert decoded['gates_and_read_sequence_verified']
            if extra_values:
                assert decoded['routing']['programmed_ctls'][0]['mixers'][0]['vig0_rect0_blend_index']==0
                assert decoded['routing']['interfaces'][1]['pingpong_selection']==0
                assert decoded['routing']['interfaces'][1]['autorefresh_enable']
                assert decoded['routing']['programmed_mixers'][0]['blend_stages'][0]['foreground_alpha']==255
                assert not decoded['routing']['iommu_description']['boot_mapping_proven']
        cases.append(dict(name=name,passed=passed,status=result.status,reads=len(reads),
                          mocked_mmio=True,independent_decoder=independent_decode))
    case('powered source: exact bounded read sequence',7,expected,independent_decode=True)
    case('GCC enabled HWCG idle: clock-off may be set',7,expected,gate_values=(0x80000003,0x80000000,1,1),independent_decode=True)
    case('GCC HWCG cannot bypass software disable',3,plan['gates'][:1],gate_values=(0x80000002,0x80000000,1,1),independent_decode=True)
    for i in range(4):
        gates=[1,0x80000000,1,1];gates[i]=0 if i==1 else 0x80000000
        case('gate '+str(i)+' blocks all dependent reads',3+i,plan['gates'][:i+1],gate_values=gates,independent_decode=True)
    case('clock enable bit required even if CLK_OFF clear',3,plan['gates'][:1],gate_values=(0,0x80000000,1,1))
    case('out of bounds pipe: no reads',2,[],[(mdp_path,'qcom,sde-sspp-off',be(0xfffffff0))])
    case('duplicate pipes: no reads',2,[],[(mdp_path,'qcom,sde-sspp-off',be(0x5000,0x5000))])
    case('unaligned pipe: no reads',2,[],[(mdp_path,'qcom,sde-sspp-off',be(1))])
    case('too many pipes: no reads',2,[],[(mdp_path,'qcom,sde-sspp-off',be(*range(9)))])
    case('truncated cells: no reads',2,[],[(mdp_path,'qcom,sde-sspp-off',b'bad')])
    case('short source register region: no reads',2,[],[(mdp_path,'qcom,sde-sspp-src-size',be(0x100))])
    case('nonidentity bus mapping: no reads',2,[],[('/soc','ranges',be(0,0,1,0xffffffff))])
    case('identity window too short: no reads',2,[],[('/soc','ranges',be(0,0,0,1))])
    case('unexpected cell geometry: no reads',2,[],[('/soc','#address-cells',be(2))])
    case('disabled display node: no reads',2,[],[(mdp_path,'status',b'disabled\0')])
    case('unsupported compatible: no reads',1,[],[(mdp_path,'compatible',b'unsupported\0')])
    case('unknown MDSS major: no pipe or routing reads',8,expected[:5],revision=0x40000001,independent_decode=True)
    for key,max_count,size_key,min_size in [
        ('ctl',6,'ctl',0xf8),('mixer',6,'mixer',8),('intf',4,'intf',0x2b8),('pp',6,'pp',0xcc)]:
        prop='qcom,sde-'+key+'-off'; offsets=plan['routing'][key]
        case(key+' window outside MDP: no reads',2,[],[(mdp_path,prop,be(0xfffffff0))])
        case(key+' windows overlap: no reads',2,[],[(mdp_path,prop,be(offsets[0],offsets[0]+4))])
        case(key+' exceeds supported count: no reads',2,[],[(mdp_path,prop,be(*range(max_count+1)))])
        case(key+' short block: no reads',2,[],[(mdp_path,'qcom,sde-'+size_key+'-size',be(min_size-4))])
    case('CTL aliases SSPP window: no reads',2,[],[(mdp_path,'qcom,sde-ctl-off',be(plan['pipes'][0]))])
    case('blend outside LM window: no reads',2,[],[(mdp_path,'qcom,sde-mixer-blend-op-off',be(0xfffffff0)),
         (mdp_path,'qcom,sde-mixer-blendstages',be(1))])
    case('overlapping blend registers: no reads',2,[],[(mdp_path,'qcom,sde-mixer-blend-op-off',be(0x20,0x24)),
         (mdp_path,'qcom,sde-mixer-blendstages',be(2))])
    case('blend count mismatch: no reads',2,[],[(mdp_path,'qcom,sde-mixer-blendstages',be(1))])
    # Construct semantic values independently of the collector's loops. LM5's
    # special layer offset and separate interface TE location are exercised.
    mdp=plan['regions']['mdp']['base'];ctl=mdp+plan['routing']['ctl'][0]
    lm=mdp+plan['routing']['mixer'][0];intf=mdp+plan['routing']['intf'][1]
    extra={ctl+0x14:1<<17,ctl+0xf4:2,ctl:2,lm+4:(2340<<16)|1080,
           lm+plan['routing']['blend'][0]+4:255<<16,intf+0x25c:0,intf+0x2b4:0x80000001}
    case('VIG0 blend and interface TE semantic round trip',7,expected,extra_values=extra,independent_decode=True)
    # Wire decoder must reject any read outside the independently built list.
    @read_type
    def valid_read(address,context):
        return dict(zip(plan['gates'],[1,0x80000000,1,1])).get(address,0x50000001 if address==mdp else 0)
    result=Snapshot();collect(mutated([]),c.byref(result),valid_read,None)
    words=[result.version,result.status,result.count]
    for i in range(result.count):words.extend(result.samples[i])
    for label,change in [('missing last sample',lambda w:w[:-2]),
                         ('invented MMIO address',lambda w:w[:13]+[0xdead0000]+w[14:]),
                         ('appended sample',lambda w:[w[0],w[1],w[2]+1]+w[3:]+[0xdead0000,0])]:
        try:decode(struct.pack('>'+'Q'*len(change(words)),*change(words)),blob)
        except AssertionError:cases.append(dict(name=label,passed=True,mocked_mmio=True,decoder_rejection=True))
        else:raise AssertionError(label)
    report=dict(kind='host execution of actual C display collector; mocked hardware only',command=command,
                passed=all(x['passed'] for x in cases),cases=cases,case_count=len(cases),
                source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in
                               [source,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelDisplayProbe.h']],
                input_fdt_sha256=sha(blob),shared_object_sha256=sha((out/'display-probe.so').read_bytes()),
                handset_executed=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'UniXNU-raphael/evidence/display-probe-host.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],cases=len(cases),hardware_reads=False),indent=2));print(out)


if __name__=='__main__': main()
