#!/usr/bin/env python3
"""Strict independent decoder of the bounded Darwin refusal checkpoint."""
import struct

FIELDS = ('version status console_installed driver_loaded driver_started protocol_revision '
          'null_status missing_status invalid_status unixnu_status unloaded protocol_removed '
          'console_restored exit_boot_services log_characters services_alive crc_before crc_after').split()


def decode(raw, stage, *, handset=False):
    assert stage in (2, 3, 4, 6)
    assert len(raw) == len(FIELDS) * 8
    result = dict(zip(FIELDS, struct.unpack('>' + 'Q' * len(FIELDS), raw)))
    assert result['version'] == 1 and result['status'] == (3 if stage == 6 else 1)
    if stage != 6:
        assert not any(result[name] for name in FIELDS[2:])
    else:
        for name in ['console_installed', 'driver_loaded', 'driver_started', 'unloaded',
                     'protocol_removed', 'console_restored', 'services_alive']:
            assert result[name] == 1, name
        assert result['protocol_revision'] == 0x20000
        assert result['null_status'] == 0x8000000000000002
        assert result['missing_status'] == 0x800000000000000e
        assert result['invalid_status'] == result['unixnu_status'] == 0x8000000000000001
        assert result['exit_boot_services'] == 0 and 0 < result['log_characters'] <= 8192
        assert result['crc_before'] == result['crc_after'] <= 0xffffffff
    return dict(**result, passed=True, handset_executed=handset and stage==6, xnu_executed=False,
                kernel_handoff_verified=False, periodic_timer_verified=False)
