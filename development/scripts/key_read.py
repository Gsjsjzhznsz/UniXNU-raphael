#!/usr/bin/env python3
"""Decode fixed one-byte read transactions independently; no device I/O."""
import struct
FIELDS='version status transactions completed start end timeout_ticks error'.split()
REGFIELDS='sid address observer command completion polls value error'.split()
def decode(raw,mapping,frequency):
    assert len(raw)==(8+6*8)*8
    w=struct.unpack('>'+'Q'*56,raw);o=dict(zip(FIELDS,w));assert o['version']==1
    o['registers']=[dict(zip(REGFIELDS,w[8+i*8:16+i*8])) for i in range(6)]
    assert o['status']==3 and o['transactions']==o['completed']==6 and o['error']==0
    assert o['timeout_ticks']==(frequency+999)//1000
    for i,row in enumerate(o['registers']):
        kind='volume' if i<5 else 'pon';offset=[4,5,0x40,0x46,0x10,0x10][i]
        assert row['sid']==mapping[kind+'_sid']
        assert row['address']==(mapping[kind+'_address']&~255)+offset
        assert row['observer']==mapping['observer_base']+0x10000*mapping['ee']+0x80*mapping[kind+'_apid']
        assert row['command']==(1<<27)|(offset<<4)
        assert row['completion']&15==1 and 1<=row['polls']<=100000 and row['value']<=255 and row['error']==0
    v=[r['value'] for r in o['registers']]
    direction=(v[2]&3) if v[1] in [0x10,0x11] else ((v[2]>>4)&7)
    input_config=v[0]==0x10 and v[1] in [1,5,9,13,0x10,0x11] and direction in [0,2] and bool(v[3]&128)
    return dict(**o,all_six_read_transactions_verified=True,gpio_input_configuration_verified=input_config,
        current_keys=dict(volume_up=not bool(v[4]&1),volume_down=bool(v[5]&2),power=bool(v[5]&1)),
        observer_command_mmio_writes=6,pmic_register_writes=0,physical_key_action_verified=False)
