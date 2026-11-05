#!/usr/bin/env python3
"""Resolve active source gates from the committed lock; historical reports keep their pins."""
import json
import re
from pathlib import Path


def locked_revision(name):
    root = Path(__file__).resolve().parents[1]
    entries = json.loads((root / 'sources.lock.json').read_text())['sources']
    matches = [entry for entry in entries if entry['name'] == name]
    assert len(matches) == 1, ('source lock must contain one entry', name)
    revision = matches[0]['revision']
    assert re.fullmatch(r'[0-9a-f]{40}', revision), ('not an exact Git commit', name)
    return revision
