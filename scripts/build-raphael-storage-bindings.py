#!/usr/bin/env python3
"""Reuse pinned OS software interfaces for QEMU block I/O; contains no board MMIO."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

root=Path(__file__).resolve().parents[1]
assert os.environ.get('XNU_NATIVE_VIRTIO_BLOCK')=='1'
path=Path(os.environ['RAPHAEL_STORAGE_AUDIT'])
audit=json.loads(path.read_text())
candidate=Path(os.environ['RAPHAEL_STORAGE_CANDIDATE'])
assert audit['live_native_4k'] and audit['method_slots']==190
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==audit['candidate_sha256']
plan=json.loads(candidate.with_suffix('.json').read_text())
assert plan['original_sha256']=='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7'
# These are original software-module virtual addresses, never hardware resources.
module=[e for e in plan['extents'] if e['module']=='com.apple.iokit.IOCryptoAcceleratorFamily']
assembly=root/'scripts/data/native-aes-original-bindings.S'
for address in re.findall(r'^\.set \S+, (0x[0-9a-f]+)$',assembly.read_text(),re.M):
    value=int(address,16)
    assert any(e['va']<=value<e['va']+e['size'] for e in module)
local=root/'build/storage-abi/interface-audit.json'
local.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(path,local)
subprocess.run(['python3',root/'scripts/build-software-aes-bindings.py'],check=True)
subprocess.run(['python3',root/'scripts/build-virtio-mmio-bindings.py'],check=True)
(root/'build/storage-abi/raphael-provenance.json').write_text(json.dumps(dict(
    purpose='QEMU-only read-only original OS block integration',
    audit_source=str(path),live_report=audit['live_report'],
    candidate_sha256=audit['candidate_sha256'],hardware_addresses_imported=False,
    handset_storage_qualified=False),indent=2)+'\n')
