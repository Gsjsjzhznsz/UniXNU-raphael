#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Compile the independent UFS provider and verify shared original imports."""
import json,os,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];workspace=Path(os.environ['RAPHAEL_WORKSPACE'])
assert os.environ.get('RAPHAEL_HANDSET_UFS')=='1'
logs=root/'build/raphael-ufs';logs.mkdir(parents=True,exist_ok=True)
audit=root/'build/storage-abi/interface-audit.json';candidate=Path(os.environ['RAPHAEL_STORAGE_CANDIDATE'])
v=subprocess.run(['python3',workspace/'scripts/build_raphael_ufs_object.py','--tree',root],capture_output=True,text=True)
(logs/'compile-run.log').write_text(v.stdout+v.stderr);assert v.returncode==0,v.stdout[-6000:]
out=Path(v.stdout.splitlines()[0]);assert out.is_relative_to(workspace/'artifacts/raphael-ufs-object')
subprocess.run(['python3',workspace/'scripts/bind_raphael_ufs_storage.py','--object-report',out/'report.json','--audit',audit,'--candidate',candidate],check=True)
# The generic query helper already binds the original storage class. Require
# exact equality, then link only our object to avoid duplicate absolute aliases.
shared=json.loads((root/'build/virtio-mmio-block-verified-bundle/bindings.json').read_text())['bindings']
# Parse only the generated audited .set records; these are OS virtual addresses.
import re
own=dict(re.findall(r'^\.set (\S+), (0x[0-9a-f]+)$',(out/'original-storage-bindings.S').read_text(),re.M))
assert all(int(shared.get(name,'-1'),16)==int(value,16) for name,value in own.items()),'Original storage aliases disagree'
shutil.copyfile(out/'RaphaelUfsBlock.o',logs/'RaphaelUfsBlock.o')
(logs/'provenance.json').write_text(json.dumps(dict(object_report=str(out/'report.json'),storage_abi_report=str(out/'storage-bindings.json'),handset_executed=False),indent=2)+'\n')
