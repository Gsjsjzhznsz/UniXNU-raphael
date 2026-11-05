#!/usr/bin/env python3
"""Materialize only pinned provider inputs; verify each raw file as a Git blob.

The upstream dependency is a third-party snapshot. Matching its commit does not
authenticate it against an Apple source archive or qualify a crypto provider.
"""
import argparse,concurrent.futures,datetime as dt,gzip,hashlib,io,json,posixpath,re,subprocess,sys,time,urllib.request
from pathlib import Path,PurePosixPath
from entry_probe import ROOT,sha
REVISION='11fba65b12d8830630e248dfa8344caf8b065f26'
SOURCE=ROOT/'artifacts/native-bootstrap/feeds/corecrypto-2023-c0651bae'
sys.path.insert(0,str(ROOT/'sources/UniXNU/scripts'))
import pbxproj

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project',required=True,type=Path);ap.add_argument('--cache-report',type=Path);a=ap.parse_args()
 previous=None
 if a.cache_report:
  previous=a.cache_report.resolve();assert previous.is_relative_to(ROOT/'artifacts/corecrypto-source-subset')
  assert json.loads(previous.read_text())['source_revision']==REVISION
 assert subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()==REVISION
 assert not subprocess.check_output(['git','-C',str(SOURCE),'status','--porcelain'],text=True)
 entries={}
 for item in subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-rz',REVISION]).split(b'\0'):
  if not item:continue
  head,name=item.split(b'\t',1);mode,kind,oid=head.decode().split();name=name.decode()
  assert kind=='blob' and not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
  entries[name]=(mode,oid)
 raw=a.project.read_bytes();project_name='corecrypto.xcodeproj/project.pbxproj'
 def oid(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 assert oid(raw)==entries[project_name][1]
 objects=pbxproj.load(a.project)['objects'];parents={child:key for key,value in objects.items() for child in value.get('children',[])}
 def resolve(key):
  entry=objects[key];path=entry.get('path','')
  if entry.get('sourceTree')=='SOURCE_ROOT' or key not in parents:return PurePosixPath(path)
  assert entry.get('sourceTree')=='<group>'
  return resolve(parents[key])/path
 target=next(v for v in objects.values() if v.get('isa')=='PBXNativeTarget' and v.get('name')=='corecrypto_kext')
 phase=next(objects[key] for key in target['buildPhases'] if objects[key]['isa']=='PBXSourcesBuildPhase')
 required={str(resolve(objects[key]['fileRef'])) for key in phase['files'] if objects[objects[key]['fileRef']].get('path','').endswith('.c')}
 sources=len(required);required.add(project_name)
 required.update(name for name in entries if name.endswith(('.h','.inc')) and 'test' not in name.lower())
 # The upstream builder links every */corecrypto/*.h, including FIPS helper
 # names containing test. These are real provider inputs, not test bypasses.
 required.update(name for name in entries if name.endswith('.h') and len(PurePosixPath(name).parts)==3 and PurePosixPath(name).parts[1]=='corecrypto')
 assert required<=entries.keys() and all(entries[name][0] in ['100644','100755'] for name in required)
 out=ROOT/'artifacts/corecrypto-source-subset'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
 cache=out/'blobs';cache.mkdir();records=[];failures=[]
 report=dict(passed=False,source_revision=REVISION,source_url='https://github.com/ONLYA/corecrypto-2023',authentication_against_apple_archive=False,required_files=len(required),kernel_c_sources=sources,runner_sha256=sha(Path(__file__).read_bytes()))
 def publish():
  report.update(files=sorted(records,key=lambda x:x['path']),failures=failures)
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 publish()
 def fetch(name):
  expected=entries[name][1];dest=cache/expected
  if name==project_name:data=raw
  elif previous and (previous.parent/'blobs'/expected).is_file():data=(previous.parent/'blobs'/expected).read_bytes()
  elif (SOURCE/name).is_file():data=(SOURCE/name).read_bytes()
  else:
   error=None
   for attempt in range(2):
    try:
     request=urllib.request.Request('https://raw.githubusercontent.com/ONLYA/corecrypto-2023/'+REVISION+'/'+name,headers={'Accept-Encoding':'gzip'})
     with urllib.request.urlopen(request,timeout=30) as response:
      data=response.read(16*1024*1024+1);assert len(data)<=16*1024*1024
      if response.headers.get('Content-Encoding')=='gzip':
       data=gzip.GzipFile(fileobj=io.BytesIO(data)).read(16*1024*1024+1);assert len(data)<=16*1024*1024
     error=None;break
    except Exception as e:error=e
   if error:raise error
  assert oid(data)==expected,name
  dest.write_bytes(data)
  return dict(path=name,git_blob_sha1=expected,sha256=sha(data),bytes=len(data))
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
  futures={executor.submit(fetch,name):name for name in sorted(required)}
  for future in concurrent.futures.as_completed(futures):
   name=futures[future]
   try:records.append(future.result())
   except Exception as e:failures.append(dict(path=name,error=type(e).__name__+': '+str(e)))
   if (len(records)+len(failures))%50==0:publish();print(len(records),'verified;',len(failures),'failed',flush=True)
 # Follow exact relative quoted includes as well. In particular the intact
 # FIPS ECDSA POST consumes .kat files under test_vectors during real startup.
 while not failures:
  additional=set()
  for item in records:
   data=(cache/item['git_blob_sha1']).read_bytes()
   for include in re.findall(rb'^\s*#\s*include\s*"([^"]+)"',data,re.M):
    name=posixpath.normpath(posixpath.join(posixpath.dirname(item['path']),include.decode()))
    if name in entries and name not in required:additional.add(name)
  if not additional:break
  assert all(entries[name][0] in ['100644','100755'] for name in additional)
  required.update(additional);report['required_files']=len(required)
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
   futures={executor.submit(fetch,name):name for name in sorted(additional)}
   for future in concurrent.futures.as_completed(futures):
    try:records.append(future.result())
    except Exception as e:failures.append(dict(path=futures[future],error=type(e).__name__+': '+str(e)))
  publish();print('Relative include closure:',len(records),'verified',flush=True)
 publish();assert not failures,failures[:3]
 # Populate only content already checked against the pinned tree. No network is
 # needed for the subsequent sparse checkout, and existing tracked files must
 # still match the immutable commit before this mutation.
 assert not subprocess.check_output(['git','-C',str(SOURCE),'status','--porcelain'],text=True)
 for item in records:
  data=(cache/item['git_blob_sha1']).read_bytes();assert sha(data)==item['sha256']
  actual=subprocess.check_output(['git','-C',str(SOURCE),'hash-object','-w','--stdin'],input=data).decode().strip();assert actual==item['git_blob_sha1']
 patterns=''.join('/'+name+'\n' for name in sorted(required))
 assert all(not any(c in name for c in '*?[\\') for name in required)
 command=['git','-C',str(SOURCE),'-c','remote.origin.promisor=false','sparse-checkout','set','--no-cone','--stdin']
 x=subprocess.run(command,input=patterns,text=True,capture_output=True,timeout=60)
 (out/'checkout.log').write_text(x.stdout+x.stderr);report['checkout_returncode']=x.returncode;publish();assert x.returncode==0
 for item in records:assert sha((SOURCE/item['path']).read_bytes())==item['sha256']
 assert not subprocess.check_output(['git','-C',str(SOURCE),'status','--porcelain'],text=True)
 report.update(passed=True,checkout_command=command,tracked_inputs_verified=len(records));publish();print(out,flush=True)
if __name__=='__main__':main()
