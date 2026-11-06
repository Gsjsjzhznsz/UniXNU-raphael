#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Explicit21H461 original FairPlayIOKit import; preserve audited symbol addends."""
from pathlib import Path
import json
import copy
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'sources/UniXNU/kits/XnuPrelink'))
import native_prelink
import emit_prelink

_UPSTREAM_EMIT = emit_prelink.emit
_UPSTREAM_INVENTORY = emit_prelink.instruction_inventory

# The original FairPlayIOKit relocation table contains biased import pointers.
# Keep the original symbolic byte addend when rebinding to the same native
# export. No nearest-symbol or arbitrary interior-function fallback is used.
IMPORT_ADDENDS = {
    '_IOMallocAligned': {2, 3}, '_IOMallocData': {2, 3},
    '_IOMallocTypeImpl': {3}, '_ipc_port_release_send': {2},
    '_IOFreeData': {2, 3}, '_ipc_kernel_map': {3},
    '_IOFreeTypeVarImpl': {2, 3}, '_IOFreeTypeImpl': {2, 3},
    '_strlen': {2}, '_memcpy': {2}, '_IOFreeAligned': {2, 3},
    '_random': {3}, '_kernel_map': {7}, '_IOLog': {3},
    '_IOMalloc': {3}, '_IOMallocTypeVarImpl': {2, 3},
    '_host_priv_self': {3}, '_PAGE_SHIFT_CONST': {3},
    '_host_get_special_port': {3},
}

def instruction_inventory(original, parent, modules):
    identifier = 'com.apple.driver.FairPlayIOKit'
    manifest = json.loads((ROOT / 'UniXNU-raphael/evidence/fairplay-inline-data-21H461.json').read_text())
    expected = {int(va, 16) for va in manifest['word_addresses']}
    if identifier not in modules or len(expected) != 155:
        raise ValueError('Explicit21H461 FairPlay inline-data map required')
    filtered = copy.deepcopy(modules)
    for segment in filtered[identifier]['segments']:
        if segment['name'] == '__TEXT_EXEC':
            segment['filesize'] = 0
    result = _UPSTREAM_INVENTORY(original, parent, filtered)
    extents = [s for m in modules.values() for s in m['segments']
               if s['size'] and s['name'] != '__LINKEDIT']
    seen, incoming, protected = set(), [], []
    for name, module in modules.items():
        for segment in module['segments']:
            if segment['name'] != '__TEXT_EXEC' or not segment['filesize']:
                continue
            at = native_prelink.backed_offset(parent, segment['va'], segment['filesize'], len(original))
            blob = original[at:at+segment['filesize']]
            for offset in range(0, len(blob)-3, 4):
                pc = segment['va'] + offset
                word = struct.unpack_from('<I', blob, offset)[0]
                decoded = emit_prelink.pc_relative_target(word, pc)
                if decoded is None:
                    continue
                target, page = decoded
                if not page and target & ~3 in expected:
                    incoming.append(dict(module=name, pc=hex(pc), target=hex(target)))
                if name != identifier:
                    continue
                if pc in expected:
                    previous = struct.unpack_from('<I', blob, offset-4)[0] if offset >= 4 else 0
                    if not (previous & 0xfffffc1f == 0xd61f0000 or previous & 0xfc000000 == 0x14000000):
                        raise ValueError('FairPlay inline word has a fallthrough predecessor')
                    seen.add(pc)
                    protected.append(dict(va=hex(pc), size=4))
                    continue
                internal = any((s['va'] & ~4095) <= target < emit_prelink.align(s['va']+s['size'])
                               for s in extents) if page else any(s['va'] <= target < s['va']+s['size'] for s in extents)
                if not internal:
                    raise ValueError('Unclassified FairPlay PC-relative encoding at '+hex(pc))
                result['pc_relative_encodings_preserved'] += 1
    if seen != expected or incoming:
        raise ValueError('FairPlay inline map missing entries or has incoming references')
    result['fairplay_inline_data'] = dict(ranges=protected, direct_incoming=incoming,
        original_executable_bytes_modified=False, register_dataflow_qualified=False,
        scope='Frozen21H461 branch-skipped original padding, copied byte-for-byte; indirect control flow remains an experimental handset validation boundary.')
    return result

def emit(native_data, original_data, roots, slide, initializers=None):
    if 'com.apple.driver.FairPlayIOKit' not in roots:
        raise ValueError('FairPlay import adapter requires the explicit original driver')
    original_binding = native_prelink.unique_kernel_binding
    bindings = {}
    def bind(address, original_exports, native_by_name):
        try:
            return original_binding(address, original_exports, native_by_name)
        except ValueError as exact_error:
            choices = {}
            for name, addends in IMPORT_ADDENDS.items():
                for addend in addends:
                    base = address - addend
                    if name not in original_exports.get(base, []):
                        continue
                    replacement = original_binding(base, original_exports, native_by_name) + addend
                    choices.setdefault(replacement, []).append((name, addend))
            if len(choices) != 1:
                raise exact_error
            replacement, names = next(iter(choices.items()))
            bindings[address] = dict(original_target=address, new_target=replacement,
                                     symbolic_addends=[dict(symbol=n, addend=a) for n,a in names])
            return replacement
    native_prelink.unique_kernel_binding = bind
    emit_prelink.instruction_inventory = instruction_inventory
    try:
        image, report = _UPSTREAM_EMIT(native_data, original_data, roots, slide, initializers)
    finally:
        native_prelink.unique_kernel_binding = original_binding
        emit_prelink.instruction_inventory = _UPSTREAM_INVENTORY
    report['fairplay_symbol_addends'] = list(bindings.values())
    report['fairplay_addend_scope'] = 'Explicit audited21H461 symbolic byte addends retained;original executable instructions unchanged;runtime unqualified.'
    return image, report

def main():
    original_emit = emit_prelink.emit
    emit_prelink.emit = emit
    try:
        emit_prelink.main()
    finally:
        emit_prelink.emit = original_emit

if __name__ == '__main__':
    main()
