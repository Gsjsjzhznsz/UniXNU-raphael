#!/usr/bin/env python3
"""Re-read private wire/command evidence behind the sanitized public index."""
import json,struct,subprocess
from entry_probe import ROOT,sha
from inspect_device import read_fdt

def main():
 public=ROOT/'UniXNU-raphael/evidence/psci-recovery-verification.json';index=json.loads(public.read_text());revision=index['implementation_revision']
 query_path=ROOT/index['query']['private_report'];reset_path=ROOT/index['recovery']['private_report']
 assert sha(query_path.read_bytes())==index['query']['report_sha256'] and sha(reset_path.read_bytes())==index['recovery']['report_sha256']
 qr=json.loads(query_path.read_text());rr=json.loads(reset_path.read_text());assert qr['passed'] and rr['passed']
 query=query_path.parent;reset=reset_path.parent;build=ROOT/rr['private_build'];br=json.loads((build/'report.json').read_text())
 for items,snapshot,key in [(qr['source_inputs'],query/'snapshot','file'),(br['source_inputs'],build/'snapshot','path')]:
  for item in items:
   raw=(snapshot/item[key]).read_bytes();assert sha(raw)==item['sha256']
   if not item[key].startswith('sources/'):
    original=subprocess.check_output(['git','-C',str(ROOT),'show',revision+':'+item[key]]);assert raw==original,item[key]
 blob=(query/'after.dtb').read_bytes();tree=read_fdt(blob);chosen=next(n for n in tree.children if n.name=='chosen')
 assert chosen.strings('raphael,entry-probe-id')==[qr['identifier']]
 assert struct.unpack('>6Q',chosen.properties['raphael,psci-query'])==(1,1,65537,0,4,0)
 assert sha(blob)==qr['observation']['fdt_sha256']
 assert sha((build/'boot-psci-reset.img').read_bytes())==rr['image_sha256']==br['packed_image_sha256']==index['recovery']['image_sha256']
 assert sha((build/'reset.Image').read_bytes())==br['standalone_image_sha256'] and len((build/'reset.Image').read_bytes())==65536
 tree=read_fdt((reset/'after.dtb').read_bytes());chosen=next(n for n in tree.children if n.name=='chosen');assert not any(k.startswith('raphael,') for k in chosen.properties)
 assert (reset/'before-boot-id.txt').read_bytes()!=(reset/'after-boot-id.txt').read_bytes()
 for path in [query/'device-commands.json',reset/'commands.json']:
  commands=json.loads(path.read_text());assert not any(any(x in ['flash','erase','format','set_active'] for x in c['command']) for c in commands)
  hashes=[c['stdout'].split()[0] for c in commands if 'sha256sum /dev/block/bootdevice/by-name/boot' in ' '.join(c['command']) and c.get('returncode')==0]
  assert len(hashes)==2 and hashes[0]==hashes[1]==br['source_boot_sha256']
 assert not index['recovery']['reset_instruction_trace_verified'] and not index['used_flash_or_erase']
 print('PSCI query wire, source blobs and automatic recovery evidence verified')
if __name__=='__main__':main()
