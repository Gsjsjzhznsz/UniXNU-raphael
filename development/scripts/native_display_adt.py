#!/usr/bin/env python3
"""Opt in to inherited handset display without changing hardware resources."""
import argparse,datetime,json,struct,sys
from pathlib import Path
from entry_probe import ROOT,sha
KEY='unixnu,diagnostic-display'
DISPLAY_NAME='raphael-gop'
SCALE_KEY='display-scale'

def display_node():
 # The original iomfb_populate_all_display_infos scans direct arm-io children.
 # This declares the inherited framebuffer, without a controller reg or IRQ.
 return dict(props={'name':b'raphael-gop\0','device_type':b'display-subsystem\0',
                    'compatible':b'raphael,firmware-gop\0'},nodes={})

def strip_display_declaration(tree):
 """Remove only our exact OS enumeration policy for hardware comparison."""
 chosen=tree['nodes']['chosen']['props'];io=tree['nodes']['arm-io']['nodes']
 declared=DISPLAY_NAME in io;scaled=SCALE_KEY in chosen
 if not declared and not scaled:return False
 assert declared and scaled, 'Inherited display declaration and scale must be paired'
 assert chosen.get(KEY)==struct.pack('<I',1), 'Display enumeration requires explicit handset opt-in'
 assert chosen[SCALE_KEY]==struct.pack('<I',1), 'Only one logical pixel per inherited framebuffer pixel is declared'
 assert io[DISPLAY_NAME]==display_node(), 'Display declaration cannot introduce hardware resources'
 assert sum(n['props'].get('device_type')==b'display-subsystem\0' for n in io.values())==1
 del io[DISPLAY_NAME];del chosen[SCALE_KEY]
 return True

def add_display_declaration(tree):
 chosen=tree['nodes']['chosen']['props'];io=tree['nodes']['arm-io']['nodes']
 assert chosen.get(KEY)==struct.pack('<I',1)
 assert DISPLAY_NAME not in io and SCALE_KEY not in chosen
 assert not any(n['props'].get('device_type')==b'display-subsystem\0' for n in io.values())
 io[DISPLAY_NAME]=display_node();chosen[SCALE_KEY]=struct.pack('<I',1)

def qualify_kernel(path,offline_keystore=False):
 from native_early import image
 symbols=image(path.read_bytes())[1]
 assert all(k in symbols for k in ['_raphael_display_stage','_raphael_display_frames','_raphael_display_guard','_native_legacy_display_late_probe','_native_owner_data_stage','_raphael_data_seed_status'])
 assert ('_raphael_offline_aks_stage' in symbols)==offline_keystore,'Keystore requires the explicit ephemeral scratch-Data payload option'
 if offline_keystore:assert all(k in symbols for k in ['_native_aks_state_enabled','_native_aks_lock_state','_native_aks_call','_native_keyevents_allocate'])
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-report',type=Path,required=True);p.add_argument('--enumeration-only',action='store_true',help='Keep an existing inherited display opt-in and all qualified resource/budget bytes');a=p.parse_args()
 source=a.data_report.resolve();assert source.is_relative_to(ROOT/'evidence/private/handset-storage-adt')
 data=json.loads(source.read_text());assert data['passed'] and not data['persistent']
 adt=ROOT/data['adt'];raw=adt.read_bytes()
 from validate_handset_adt import parse
 tree,end=parse(raw);assert end==len(raw)
 from native_watchdog_budget import from_adt
 budget=from_adt(raw);assert budget is not None
 assert a.enumeration_only or budget['observer_ms']==240000
 assert tree['nodes']['chosen']['props']['darwinboot-memory-size']==struct.pack('<Q',512*1048576)
 props=tree['nodes']['chosen']['props']
 if a.enumeration_only:assert props.get(KEY)==struct.pack('<I',1)
 else:
  assert KEY not in props;props[KEY]=struct.pack('<I',1)
 add_display_declaration(tree)
 sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'));from unixnu.devicetree import node
 def encode(t):return node(t['props']['name'].rstrip(b'\0').decode(),[(k,v) for k,v in t['props'].items() if k!='name'],[encode(c) for c in t['nodes'].values()])
 out=ROOT/'evidence/private/handset-storage-adt'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-inherited-display');out.mkdir(parents=True,mode=0o700)
 result=encode(tree);assert from_adt(result)==budget
 target=out/'kernel.macho.adt';target.write_bytes(result)
 provenance=json.loads((adt.parent/'adt-provenance.json').read_text());provenance.update(adt_sha256=sha(result),adt_bytes=len(result),inherited_display_source_adt=str(adt.relative_to(ROOT)),inherited_display_candidate=True,display_enumeration=True,display_scale_policy=1)
 (out/'adt-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 data.update(adt=str(target.relative_to(ROOT)),source_data_report=str(source.relative_to(ROOT)),inherited_display_candidate=True,display_enumeration=True,display_scale_policy=1,handset_qualified=False)
 (out/'report.json').write_text(json.dumps(data,indent=2)+'\n');print(out)
if __name__=='__main__':main()
