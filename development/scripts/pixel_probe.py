#!/usr/bin/env python3
"""Independent decoder of private pixel samples; exposes only hashes and counter summaries."""
import hashlib
import struct
from inspect_device import read_fdt, node_path, registers, physical
from inspect_boot_display import linear_candidate

GRID=64
ROUNDS=32
FIELDS=['version','status','width','height','stride','base_low','base_high','extent',
        'interface_base','counter_frequency','grid','pixel_count','refresh_count']
WORDS=len(FIELDS)+GRID*GRID+ROUNDS*6


def decode(raw,fdt,display):
    assert len(raw)==WORDS*4
    words=struct.unpack('>'+'I'*WORDS,raw);header=dict(zip(FIELDS,words[:len(FIELDS)]))
    assert header['version']==1 and header['status'] in range(1,7)
    pixels=words[len(FIELDS):len(FIELDS)+GRID*GRID];rest=words[len(FIELDS)+GRID*GRID:]
    assert header['pixel_count']<=GRID*GRID and header['refresh_count']<=ROUNDS
    records=[]
    for i in range(header['refresh_count']):
        lo,hi,status,frame,readptr,line=rest[i*6:i*6+6]
        records.append(dict(counter=lo|(hi<<32),interface_status=status,frame_count=frame,
                            read_pointer_frame_count=readptr>>16,read_pointer_line_count=readptr&65535,
                            write_pointer_line_count=line&65535,raw_line_count=line))
    if header['status']==6:
        assert header['pixel_count']==GRID*GRID and header['refresh_count']==ROUNDS and header['grid']==GRID
        tree=read_fdt(fdt);n=next(n for n in tree.walk() if node_path(n)=='/reserved-memory/cont_splash_region')
        base,size=registers(n)[0];reservation=dict(base=physical(n.parent,base,size),size=size)
        candidates=[linear_candidate(p,reservation) for p in display['programmed_pipes']]
        assert len(candidates)==1 and candidates[0]['candidate_valid']
        candidate=candidates[0]
        assert header['base_high']==0 and header['base_low']==candidate['address_register_value']
        assert [header[k] for k in ['width','height','stride','extent']]==[
            candidate[k] for k in ['width','height','stride_bytes','pixel_bytes']]
        assert not display['smmu_probe']['client_power_down']
        assert display['smmu_probe']['all_declared_streams_uniquely_matched']
        assert all(c['cbar_type']==1 and c['aarch64'] and not c['translation_enabled']
                   for c in display['smmu_probe']['contexts'])
        assert len(records)==ROUNDS and all(a['counter']<b['counter'] for a,b in zip(records,records[1:]))
        assert records[-1]['counter']-records[0]['counter']>=31*(header['counter_frequency']//500)
    result=dict(header=header,wire_sha256=hashlib.sha256(raw).hexdigest(),
        pixel_sample_sha256=hashlib.sha256(struct.pack('<'+'I'*len(pixels),*pixels)).hexdigest(),
        unique_pixel_values=len(set(pixels[:header['pixel_count']])),
        nonzero_pixel_samples=sum(v!=0 for v in pixels[:header['pixel_count']]),
        nonblack_rgb_samples=sum(v&0xffffff!=0 for v in pixels[:header['pixel_count']]),
        refresh=records,mmio_writes=False,pixel_writes=False,
        cpu_sample_read_verified=header['status']==6,actual_pixel_fetch_verified=False,panel_update_verified=False,
        gop_enabled=False)
    result['counter_activity_observed']=len({(i['frame_count'],i['read_pointer_frame_count'],i['read_pointer_line_count'],i['write_pointer_line_count']) for i in records})>1
    return result
