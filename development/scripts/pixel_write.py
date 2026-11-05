#!/usr/bin/env python3
"""Decode the reversible pixel patch result; memory readback is not visibility."""
import struct
FIELDS=['version','status','base','width','height','stride','count','written','verified','restored',
        'mismatches','original_digest','pattern_digest','restored_digest','start','end','hold_ticks','backup','active']


def decode(raw,pixels):
    assert len(raw)==len(FIELDS)*8
    record=dict(zip(FIELDS,struct.unpack('>'+'Q'*len(FIELDS),raw)))
    assert record['version']==1 and record['status'] in range(1,9)
    passed=record['status']==7
    if passed:
        p=pixels['header']
        assert record['base']==p['base_low'] and record['stride']==p['stride']
        assert record['width']==256 and record['height']==128 and record['count']==32768
        assert record['written']==record['verified']==record['restored']==record['count']
        assert record['original_digest']==record['restored_digest'] and record['pattern_digest']!=record['original_digest']
        assert record['mismatches']==record['backup']==record['active']==0
        assert record['end']-record['start']>=record['hold_ticks']==10*p['counter_frequency']
    return dict(**record,memory_write_readback_restore_verified=passed,visible_output_verified=False,
                display_registers_written=False,persistent_storage_written=False,gop_verified=False)
