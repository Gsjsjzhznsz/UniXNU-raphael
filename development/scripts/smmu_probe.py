#!/usr/bin/env python3
"""Independent SMMUv2 read recipe and wire-v4 validation; no hardware access."""
import struct
from inspect_device import read_fdt, node_path, registers, physical

CB_OFFSETS = [0,4,0x10,0x20,0x24,0x28,0x2c,0x30,0x34,0x38,0x3c]
STATUS = {9:'invalid-iommu-description',10:'tbu-power-off',11:'unsupported-smmu-geometry',
          12:'ambiguous-stream-configuration',13:'smmu-collected',14:'missing-stream-match'}


def recipe(blob):
    nodes=list(read_fdt(blob).walk())
    mdp=next(n for n in nodes if b'qcom,sde-kms' in n.properties.get('compatible',b'').split(b'\0'))
    gcc=next(n for n in nodes if b'qcom,gcc-sm8150-v2' in n.properties.get('compatible',b'').split(b'\0'))
    handle,sid,mask=mdp.cells('iommus')
    smmu=next(n for n in nodes if n.cells('phandle')==[handle])
    assert smmu.cells('#iommu-cells')==[2] and sid<=32767 and mask<=32767 and mask.bit_count()<=4
    def first(n):
        base,size=registers(n)[0]
        return dict(base=physical(n.parent,base,size),size=size,source=node_path(n)+':reg[0]')
    sids=[i for i in range(32768) if (i ^ sid) & (~mask & 32767)==0]
    power=[];tbus=[]
    for n in nodes:
        if n.parent is not smmu or b'qcom,qsmmuv500-tbu' not in n.properties.get('compatible',b'').split(b'\0'):continue
        start,count=n.cells('qcom,stream-id-range')
        matched=[i for i in sids if start<=i<start+count]
        if not matched:continue
        handle,=n.cells('vdd-supply');gdsc=next(g for g in nodes if g.cells('phandle')==[handle])
        reg=first(gdsc);power.append(reg['base'])
        tbus.append(dict(source=node_path(n),matching_streams=matched,power=reg))
    assert len(power)==len(set(power)) and sorted(i for t in tbus for i in t['matching_streams'])==sids
    return dict(smmu=first(smmu),gcc=first(gcc),target_sid=sid,target_mask=mask,target_streams=sids,
                power_addresses=power,tbus=tbus,source=node_path(mdp)+':iommus',
                mmio_writes=False,root_bus_access_assumption='existing boot firmware leaves APPS SMMU global register path accessible',
                root_bus_vote_verified=False)


def decode(pairs, plan, status):
    cursor=0;records=[];contexts=[];matches={i:[] for i in plan['target_streams']}
    def take(address):
        nonlocal cursor
        assert cursor<len(pairs),'missing SMMU sample'
        observed,value=pairs[cursor];assert observed==address,('SMMU read sequence',hex(observed),hex(address))
        cursor+=1;return value
    def finish(expected):
        assert status==expected and cursor==len(pairs),(status,expected,cursor,len(pairs))
        return dict(status=status,status_name=STATUS[status],read_sequence_verified=True,
                    register_writes=False,stream_matches=records,contexts=contexts,
                    target_streams=plan['target_streams'],cpu_physical_mapping_verified=False,
                    iommu_page_tables_read=False,actual_pixel_fetch_verified=False)
    for address in plan['power_addresses']:
        if not take(address)&0x80000000:return finish(10)
    base=plan['smmu']['base'];size=plan['smmu']['size']
    id0,id1,id2,cr0=[take(base+o) for o in [0x20,0x24,0x28,0]]
    groups=id0&255;pgshift=16 if id1>>31 else 12;num_cb=id1&255;num_s2=(id1>>16)&255
    half=size//2;page=1<<pgshift
    supported=(bool(id0&(1<<27)) and bool(id0&(3<<29)) and not id0&(1<<8) and groups and
               0<num_cb<=128 and num_s2<=num_cb and 1<<(((id1>>28)&7)+1+pgshift)==half and
               num_cb*page<=half and page+0xa00<=half)
    if not supported:return finish(11)
    banks=[]
    for i in range(groups):
        smr=take(base+0x800+i*4)
        if not smr&(1<<31):continue
        smr_mask=(smr>>16)&32767;smr_id=smr&32767
        hit=[sid for sid in plan['target_streams'] if (sid^smr_id)&~smr_mask==0]
        for sid in hit:
            matches[sid].append(i)
            if len(matches[sid])!=1:return finish(12)
        if not hit:continue
        s2cr=take(base+0xc00+i*4);typ=(s2cr>>16)&3;bank=s2cr&255
        records.append(dict(index=i,smr=smr,id=smr_id,mask=smr_mask,matched_streams=hit,s2cr=s2cr,
                            type=typ,type_name=['translation','bypass','fault','reserved'][typ],context_bank=bank if typ==0 else None))
        if typ==3 or typ==0 and bank>=num_cb:return finish(12)
        if typ==0 and bank not in banks:banks.append(bank)
    if any(len(m)!=1 for m in matches.values()):return finish(14)
    for bank in banks:
        cbar=take(base+page+bank*4);cba2r=take(base+page+0x800+bank*4)
        cb=base+half+bank*page;values={o:take(cb+o) for o in CB_OFFSETS}
        contexts.append(dict(index=bank,register_base=cb,cbar=cbar,cba2r=cba2r,
            cbar_type=(cbar>>16)&3,aarch64=bool(cba2r&1),sctlr=values[0],translation_enabled=bool(values[0]&1),
            actlr=values[4],ttbcr2=values[0x10],ttbr0=values[0x20]|values[0x24]<<32,
            ttbr1=values[0x28]|values[0x2c]<<32,ttbcr=values[0x30],contextidr=values[0x34],
            mair0=values[0x38],mair1=values[0x3c]))
    result=finish(13)
    result.update(id0=id0,id1=id1,id2=id2,cr0=cr0,client_power_down=bool(cr0&1),
                  num_stream_groups=groups,num_context_banks=num_cb,page_shift=pgshift,
                  all_declared_streams_uniquely_matched=True)
    return result


def decode_wire4(words, blob, legacy_decode):
    from display_probe import recipe as display_recipe, route_addresses, OFFSETS
    version,status,count=words[:3]
    assert version==4 and 0<=status<=14 and count<=1024 and len(words)==3+count*2
    pairs=list(zip(words[3::2],words[4::2]));assert all(a%4==0 and v<=0xffffffff for a,v in pairs)
    if status<=8:
        base=legacy_decode(struct.pack('>'+'Q'*len(words),3,*words[1:]),blob)
        base.update(version=4,smmu_probe=dict(status_name='not-run-display-prerequisite-incomplete',register_writes=False))
        return base
    plan=display_recipe(blob)
    prefix=5+len(plan['pipes'])*len(OFFSETS)+len(route_addresses(plan))
    assert count>=prefix
    prior_words=[3,7,prefix]+list(words[3:3+prefix*2])
    base=legacy_decode(struct.pack('>'+'Q'*len(prior_words),*prior_words),blob)
    if status==9:
        assert count==prefix, 'invalid SMMU FDT must cause no additional MMIO'
        smmu=dict(status=9,status_name=STATUS[9],read_sequence_verified=True,register_writes=False,
                  cpu_physical_mapping_verified=False,iommu_page_tables_read=False,actual_pixel_fetch_verified=False)
    else:
        smmu=decode(pairs[prefix:],recipe(blob),status)
    base.update(version=4,status=status,status_name=STATUS[status],sample_count=count,
                samples=[dict(address=a,address_hex=hex(a),value=v,value_hex=hex(v)) for a,v in pairs],smmu_probe=smmu)
    return base
