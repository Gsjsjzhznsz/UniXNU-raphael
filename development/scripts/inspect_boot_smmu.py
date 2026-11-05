#!/usr/bin/env python3
"""Interpret nonce-bound wire-v4 readback; never assert physical mapping from a register."""
import json
from entry_probe import ROOT, sha
from inspect_device import read_fdt, node_path
from display_probe import decode
from inspect_boot_route import route_candidate
from smmu_probe import recipe


def main():
    path=ROOT/'UniXNU-raphael/evidence/sec-display-handoff.json';handoff=json.loads(path.read_text())
    assert all(handoff[k] for k in ['nonce_matched','firmware_checkpoint_passed','root_verified','boot_partition_unchanged'])
    blob=(ROOT/handoff['private_readback']/'after.dtb').read_bytes();assert sha(blob)==handoff['fdt_sha256']
    chosen=next(n for n in read_fdt(blob).walk() if node_path(n)=='/chosen')
    decoded=decode(chosen.properties['raphael,display-snapshot'],blob)
    assert decoded==handoff['display_probe'] and decoded['version']==4
    route=route_candidate(decoded);assert route['register_configuration_consistent']
    smmu=decoded['smmu_probe']
    report=dict(kind='nonce-bound handset SMMU register interpretation; no page-table or pixel access',
        handoff=str(path.relative_to(ROOT)),handoff_sha256=sha(path.read_bytes()),
        private_readback=handoff['private_readback'],private_build=handoff['private_build'],
        fdt_sha256=sha(blob),recipe=recipe(blob),smmu=smmu,display_route=route,
        firmware_checkpoint_passed=True,read_count=decoded['sample_count'],
        mmio_written=False,physical_mapping_verified=False,page_tables_read=False,pixel_output_verified=False,
        gop_enabled=False,analysis_sources=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes()))
            for p in [ROOT/'scripts/display_probe.py',ROOT/'scripts/smmu_probe.py',
                      ROOT/'scripts/inspect_boot_route.py',Path(__file__)]],
        limitations=['Unique stream matching is register configuration evidence only',
                     'CLIENTPD, SCTLR.M and CBAR must be interpreted together before choosing any memory walk',
                     'Neither a TTBR nor a bypass setting proves CPU buffer ownership, cache policy or visible refresh'])
    (ROOT/'UniXNU-raphael/evidence/boot-smmu-observation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=smmu['status_name'],reads=decoded['sample_count'],
                         stream_matches=smmu.get('stream_matches'),contexts=smmu.get('contexts')),indent=2))


from pathlib import Path
if __name__=='__main__':main()
