#!/usr/bin/env python3
"""Independent FDT input recipe and arbiter wire decoder; no hardware I/O."""
import struct
from inspect_device import read_fdt, node_path
HEADER='version status hardware_version count read_count ee channel core_base core_size cnfg_base cnfg_size observer_base observer_size pon_sid pon_address volume_sid volume_address gpio_number gpio_flags debounce_ms pon_apid volume_apid pon_matches volume_matches pon_owner volume_owner'.split()
MAX_APIDS=512

def recipe(blob):
    tree=read_fdt(blob);nodes=list(tree.walk())
    def cells(n,k):
        p=n.properties[k];assert len(p)%4==0
        return list(struct.unpack('>'+'I'*(len(p)//4),p))
    def comp(n,c):return c.encode() in n.properties.get('compatible',b'').split(b'\0')
    arb,=[n for n in nodes if comp(n,'qcom,spmi-pmic-arb')]
    names=arb.properties['reg-names'].rstrip(b'\0').decode().split('\0');reg=cells(arb,'reg')
    assert len(reg)==2*len(names) and len(set(names))==len(names)
    regions={name:dict(base=reg[i*2],size=reg[i*2+1]) for i,name in enumerate(names)}
    keys,=[n for n in nodes if comp(n,'gpio-keys')]
    up,=[n for n in keys.children if cells(n,'linux,code')==[115]]
    ph,pin,flags=cells(up,'gpios');gpio,=[n for n in nodes if n.properties.get('phandle')==struct.pack('>I',ph)]
    assert comp(gpio,'qcom,spmi-gpio') and pin not in cells(gpio,'qcom,gpios-disallowed')
    base,size=cells(gpio,'reg');assert 1<=pin<=size//0x100
    volume_sid,typ=cells(gpio.parent,'reg');assert typ==0
    choices=[]
    for n in nodes:
        if not comp(n,'qcom,qpnp-power-on'):continue
        pairs=[(cells(c,'linux,code')[0],cells(c,'qcom,pon-type')[0]) for c in n.children if 'linux,code' in c.properties]
        if (116,0) in pairs and (114,1) in pairs:choices.append(n)
    pon,=choices;pon_base,pon_size=cells(pon,'reg');pon_sid,typ=cells(pon.parent,'reg');assert typ==0
    assert gpio.parent.parent is arb and pon.parent.parent is arb
    return dict(arbiter=node_path(arb),ee=cells(arb,'qcom,ee')[0],channel=cells(arb,'qcom,channel')[0],regions=regions,
        pon_sid=pon_sid,pon_address=pon_base+0x10,pon_source=node_path(pon),
        volume_sid=volume_sid,volume_address=base+(pin-1)*0x100+0x10,volume_source=node_path(up),
        gpio_provider=node_path(gpio),gpio_number=pin,gpio_flags=flags,debounce_ms=cells(up,'debounce-interval')[0])

def decode(raw,blob):
    assert len(raw)==(len(HEADER)+2*MAX_APIDS)*4
    words=struct.unpack('>'+'I'*(len(raw)//4),raw);o=dict(zip(HEADER,words));assert o['version']==1
    if o['status']==1:
        assert not any(words[2:]);return dict(**o,hardware_missing=True,mmio_writes=False,pmic_transactions=0)
    plan=recipe(blob)
    for k in ['ee','channel','pon_sid','pon_address','volume_sid','volume_address','gpio_number','gpio_flags','debounce_ms']:assert o[k]==plan[k],k
    for name in ['core','cnfg','observer']:
        region=plan['regions']['obsrvr' if name=='observer' else name]
        assert o[name+'_base']==region['base'] and o[name+'_size']==region['size']
    assert o['status'] in [3,4,5]
    if o['status']==3:
        assert not (0x50000000<=o['hardware_version']<0x60000000) and o['read_count']==1
        return dict(**o,mmio_writes=False,pmic_transactions=0,targets_verified=False)
    assert 0x50000000<=o['hardware_version']<0x60000000
    assert o['count']==(o['core_size']-0x900)//4<=MAX_APIDS
    table=words[len(HEADER):len(HEADER)+MAX_APIDS];owners=words[len(HEADER)+MAX_APIDS:]
    assert not any(table[o['count']:]) and not any(owners[o['count']:])
    assert o['read_count']==1+o['count']+sum(bool(x) for x in table)
    for kind in ['pon','volume']:
        target=o[kind+'_sid']<<8|o[kind+'_address']>>8
        matches=[i for i,v in enumerate(table) if v and (v>>8)&0xfff==target]
        assert len(matches)==o[kind+'_matches']
        selected=next(iter(matches),0xffffffff)
        for i in matches:
            if owners[i]&7==o['ee']:selected=i
        assert selected==o[kind+'_apid']
        assert o[kind+'_owner']==(owners[selected]&7 if matches else 0xffffffff)
    assert (o['status']==4)==bool(o['pon_matches'] and o['volume_matches'])
    return dict(**o,targets_verified=o['status']==4,mmio_writes=False,pmic_transactions=0,
        register_read_sequence_count_verified=True,map=[dict(apid=i,raw=v,ppid=(v>>8)&0xfff,owner_raw=owners[i],write_ee=owners[i]&7,irq_owner=bool(v&(1<<24))) for i,v in enumerate(table) if v],
        limitations=['Arbiter configuration only; no PMIC register or physical key sampled','EE owner is configuration evidence, not proof observer transactions succeed'])
