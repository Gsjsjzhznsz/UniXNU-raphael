#!/usr/bin/env python3
"""Prove frozen handset manifests reside in RNX text; bound full mutable backup."""
import argparse,datetime as dt,json,struct
from pathlib import Path
from entry_probe import ROOT,sha
from native_early import image

def audit(inspection,root_policy):
 meta=json.loads(inspection.read_text());assert meta['passed']
 kernel=ROOT/meta['artifact_directory']/'native-kernel.macho';raw=kernel.read_bytes();assert sha(raw)==meta['native_macho_sha256']
 policy=json.loads(root_policy.read_text());assert policy['passed']
 segments,symbols=image(raw);sections=[];at=32
 for _ in range(struct.unpack_from('<I',raw,16)[0]):
  cmd,n=struct.unpack_from('<II',raw,at)
  if cmd==0x19:
   for i in range(struct.unpack_from('<I',raw,at+64)[0]):
    s=at+72+i*80;name=raw[s:s+16].rstrip(b'\0').decode();seg=raw[s+16:s+32].rstrip(b'\0').decode();va,size=struct.unpack_from('<QQ',raw,s+32);sections.append((seg,name,va,size))
  at+=n
 def read(va,n):
  hits=[s for s in segments if s['virtual']<=va and va+n<=s['virtual']+s['file_bytes']];assert len(hits)==1
  s=hits[0];return raw[s['offset']+va-s['virtual']:s['offset']+va-s['virtual']+n],s
 records=[]
 for role,symbol in [('OS','_verified_root_manifest'),('SystemOS','_verified_root_systemos_manifest')]:
  manifest=(root_policy.parent/role/'manifest.bin').read_bytes();actual,segment=read(symbols[symbol],len(manifest))
  assert actual==manifest and segment['name']=='__TEXT' and segment['protection']==1
  assert len([s for s in sections if s[0:2]==('__TEXT','__rph_verified') and s[2]<=symbols[symbol] and symbols[symbol]+len(manifest)<=s[2]+s[3]])==1
  records.append(dict(role=role,symbol=symbol,virtual=hex(symbols[symbol]),bytes=len(manifest),sha256=sha(manifest),segment=segment['name'],protection=segment['protection']))
 assert struct.unpack('<Q',read(symbols['_verified_root_policy_count'],8)[0])[0]==2
 table=struct.unpack('<4Q',read(symbols['_verified_root_policies'],32)[0]);assert table==tuple(v for record in records for v in (int(record['virtual'],16),record['bytes']))
 mutable=[s for s in segments if s['name'] in ('__DATA_CONST','__DATA','__BOOTDATA','__KLD','__KLDDATA')]
 assert len(mutable)==5 and sum(s['bytes'] for s in mutable)<=3*1048576
 assert all(s['virtual']%4096==s['bytes']%4096==0 for s in mutable)
 return dict(passed=True,inspection=str(inspection.resolve().relative_to(ROOT)),kernel_sha256=sha(raw),manifests=records,mutable_backup_bytes=sum(s['bytes'] for s in mutable),complete_mutable_segments=mutable,handset_executed=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--inspection',type=Path,required=True);p.add_argument('--root-policy',type=Path,required=True);a=p.parse_args();report=audit(a.inspection,a.root_policy)
 out=ROOT/'artifacts/handset-root-layout'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
