#!/usr/bin/env python3
"""Run the pinned generic component boundary harness with Linux host harness fixes.
No driver or original OS code is patched. This is host interface evidence only.
"""
from pathlib import Path
import datetime,json,shutil,subprocess
from entry_probe import ROOT
source=ROOT/'sources/UniXNU/drivers/AppleKeyStoreState'
out=ROOT/'artifacts/offline-keystore-host'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out.mkdir(parents=True,exist_ok=False)
text=(source/'test_closed_boundary.py').read_text()
needle='constexpr IOReturn kIOReturnSuccess = 0;'
assert text.count(needle)==1 and 'constexpr IOReturn kIOReturnUnsupported' not in text
text=text.replace(needle,needle+'\nconstexpr IOReturn kIOReturnUnsupported = (IOReturn)0xe00002c7;')
text=text.replace('#include <cassert>','#include <cstdint>\n#include <cassert>').replace('if (b != 0x81 || i >= n) return false; l = p[i++]; return true;', 'if (b != 0x81 || i >= n) { return false; } l = p[i++]; return true;')
(out/'test_closed_boundary.py').write_text(text)
shutil.copyfile(source/'NativeKeyStoreEvents.cpp',out/'NativeKeyStoreEvents.cpp')
run=subprocess.run(['python3',str(out/'test_closed_boundary.py')],capture_output=True,text=True)
(out/'host.log').write_text(run.stdout+run.stderr)
report=dict(passed=run.returncode==0,source_revision=subprocess.check_output(['git','-C',source,'rev-parse','HEAD'],text=True).strip(),harness_change='Host-only fake constant, explicit cstdint include and braces for GCC indentation warning; original source and assertions unchanged',returncode=run.returncode,handset_executed=False,real_iokit_registration_tested=False,key_operations_available=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(json.dumps(report,indent=2));raise SystemExit(run.returncode)
