#!/usr/bin/env python3
"""Independent wire validation for the synthetic read-only FV payload diagnostic."""
import struct
FIELDS='version status base bytes fdt hob_present block_io read_only write_denied file_system config_entries config_ok run_status run_completed crc_before crc_after'.split()
def decode(raw,layout,stage,manager_keys=False,native_staging=False,fat_bytes=20*1048576,external_payload=False):
    assert len(raw)==len(FIELDS)*8
    o=dict(zip(FIELDS,struct.unpack('>'+'Q'*len(FIELDS),raw)))
    assert o['version']==1 and o['status']=={2:1,3:2,6:3}[stage]
    if stage==2:
        assert not any(o[k] for k in FIELDS[2:])
    else:
        assert o['bytes']==(fat_bytes if native_staging else 1048576) and o['hob_present']==1
        source='Arena' if native_staging else 'Fd'
        assert layout[source+'Base']<=o['base'] and o['base']+o['bytes']<=layout[source+'Base']+layout[source+'Size']
        if native_staging:assert o['base']==layout['ArenaBase']+layout['ArenaSize']-o['bytes']
        assert layout['ArenaBase']<=o['fdt'] and o['fdt']+4096<=layout['ArenaBase']+layout['ArenaSize']
        if stage==3:
            assert not any(o[k] for k in FIELDS[6:14])
            assert o['crc_before']==(1 if external_payload else 0) and o['crc_after']==0
        else:
            assert all(o[k]==1 for k in ['block_io','read_only','write_denied','file_system','config_ok','run_completed'])
            assert o['config_entries']==(2 if manager_keys else 1)
            assert o['run_status']==0 and o['crc_before']==o['crc_after']<=0xffffffff
    return dict(**o,read_only_payload_checkpoint_verified=True,full_unixnu_invocation_verified=stage==6,
      periodic_timer_verified=False,efi_child_on_handset_verified=False,xnu_executed=False)
