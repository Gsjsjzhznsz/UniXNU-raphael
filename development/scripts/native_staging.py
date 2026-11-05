#!/usr/bin/env python3
"""Freeze local workflow inputs separately from compiled firmware inputs."""
from entry_probe import ROOT, sha

# Host design budget: live handset FDT plus complete native recovery records.
# This does not enlarge the XNU grant or the downloaded Image.
NATIVE_RETURN_FDT_BYTES = 0x400000

def freeze_workflow(out):
    inputs = []
    for path in sorted((ROOT / 'scripts').rglob('*')):
        if not path.is_file() or path.suffix not in ['.py', '.c', '.h', '.S', '.ld']:
            continue
        relative = path.relative_to(ROOT)
        raw = path.read_bytes()
        target = out / 'workflow-snapshot' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        inputs.append(dict(path=str(relative), sha256=sha(raw)))
    return inputs
