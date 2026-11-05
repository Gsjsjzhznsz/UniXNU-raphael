#!/usr/bin/env python3
"""Cache Apple public headers with Git blob checks for unmodified preparation."""
import hashlib,json,subprocess,urllib.parse
from pathlib import Path
from entry_probe import ROOT,sha

def cache_headers(tree):
 cache=ROOT/'artifacts/native-public-headers';cache.mkdir(parents=True,exist_ok=True)
 source=tree/'.cache/sources';source.mkdir(parents=True,exist_ok=True)
 definitions=[('driverkit','xnu-driverkit-10063.121.3.json','iokit/DriverKit','xnu-10063.121.3'),('driverkit-crypto','xnu-driverkit-crypto-10063.121.3.json','iokit/DriverKit/crypto','xnu-10063.121.3'),('trustcache','xnu-trustcache-8796.101.5.json','EXTERNAL_HEADERS/TrustCache','xnu-8796.101.5')]
 evidence=[]
 for label,name,path,tag in definitions:
  api=cache/(label+'-api.json');url='https://api.github.com/repos/apple-oss-distributions/xnu/contents/'+path+'?ref='+tag
  if not api.exists():
   existing=source/name
   if existing.exists() and b'file://' not in existing.read_bytes():api.write_bytes(existing.read_bytes())
   else:subprocess.run(['curl','--fail','--location','--retry','5','--retry-all-errors','--connect-timeout','15','--max-time','60','--output',str(api),url],check=True)
  entries=json.loads(api.read_text());assert isinstance(entries,list)
  local=[]
  for entry in entries:
   item=dict(entry)
   if item['type']=='file' and item['name'].endswith('.h'):
    assert '/' not in item['name'] and item['name'] not in ('.','..')
    origin=item['download_url'];assert urllib.parse.urlsplit(origin).hostname=='raw.githubusercontent.com'
    target=cache/'blobs'/item['sha'];target.parent.mkdir(exist_ok=True)
    if not target.exists():
     previous=tree/'.cache/xnu-work'/path/item['name']
     if previous.exists():target.write_bytes(previous.read_bytes())
     else:subprocess.run(['curl','--silent','--show-error','--fail','--location','--retry','5','--retry-all-errors','--connect-timeout','15','--max-time','60','--output',str(target),origin],check=True)
    data=target.read_bytes();digest=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert digest==item['sha']
    evidence.append(dict(path=path+'/'+item['name'],tag=tag,download_url=origin,git_blob=digest,sha256=sha(data),bytes=len(data)))
    item['download_url']=target.as_uri()
   local.append(item)
  (source/name).write_text(json.dumps(local,indent=2)+'\n')
  print('Verified cached Apple headers:',label,flush=True)
 report=dict(passed=True,headers=evidence,api_snapshots=[dict(path=str((cache/(x[0]+'-api.json')).relative_to(ROOT)),sha256=sha((cache/(x[0]+'-api.json')).read_bytes())) for x in definitions],generic_source_modified=False,uses_local_urls_only_for_verified_cache=True)
 (cache/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
