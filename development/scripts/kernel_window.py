#!/usr/bin/env python3
"""Explicit boot-policy grant; neither RAM test nor hardware ownership proof."""
import struct

MAGIC = int.from_bytes(b'RAPHWIN1', 'little')
WINDOW = 0x10000000
BLOCK = 0x200000


def encode_policy(policy):
    base, size, virtual = (policy[k] for k in ('base', 'bytes', 'virtual_base'))
    guards = policy['guards']
    owned = policy.get('window_bytes', WINDOW)
    assert owned in (WINDOW, 2*WINDOW, 704*1048576), 'Only explicit 256/512/704 MiB recovery windows are supported by this implementation'
    assert policy['experimental_boot_grant'] is True
    assert base > 0 and base % BLOCK == 0 and size == owned + BLOCK
    assert base + size < 1 << 64 and virtual % 4096 == 0
    assert 1 <= len(guards) <= 128
    for g in guards:
        a, n = g['base'], g['bytes']
        assert a >= 0 and n > 0 and a + n < 1 << 64
        assert not (base < a + n and a < base + size), g
    return struct.pack('<8Q', MAGIC, 1, 64 + 16 * len(guards), base, size,
                       virtual, owned, len(guards)) + b''.join(
        struct.pack('<2Q', g['base'], g['bytes']) for g in guards)


def check_admission(raw, policy):
    import re
    match = re.search(rb'KERNEL_WINDOW admitted base=([0-9a-f]+) bytes=([0-9a-f]+) candidate=([0-9a-f]+) owned=([0-9a-f]+)', raw, re.I)
    assert match, 'Missing admission record'
    base, size, candidate, window = (int(x, 16) for x in match.groups())
    assert (base, size, window) == (policy['base'], policy['bytes'], policy.get('window_bytes', WINDOW))
    assert candidate == base + (policy['virtual_base'] & (BLOCK - 1))
    return dict(base=base, bytes=size, candidate=candidate, window_bytes=window)


def check_log(raw, policy):
    import re
    admitted = check_admission(raw, policy)
    life = re.search(rb'KERNEL_WINDOW lifecycle status=(\d+) reserved=(\d+) released=(\d+) allocated=(\d+) restored=(\d+) error=([0-9a-f]+)', raw, re.I)
    assert life and tuple(int(x) for x in life.groups()[:5]) == (4, 1, 1, 1, 1)
    assert int(life[6], 16) == 0
    return dict(passed=True, **admitted,
                reserved_map_verified=True, released_map_verified=True,
                allocate_address_loader_code_verified=True, restored_map_verified=True,
                full_physical_ownership_proven=False, kernel_executed=False)
