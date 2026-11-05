#!/usr/bin/env python3
"""Select the pinned generic pthread recipe only for profiles that use it."""
import os,subprocess,sys
from pathlib import Path
if os.environ.get('XNU_SOURCE_PTHREAD')=='1':
 subprocess.run([sys.executable,str(Path(__file__).with_name('build-libpthread-kernel.py'))],check=True)
else:
 print('Source pthread: disabled by the selected configuration')
