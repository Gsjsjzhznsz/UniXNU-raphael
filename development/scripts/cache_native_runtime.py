#!/usr/bin/env python3
"""Fetch fixed runtime source subtrees with a tree filter for unreliable links."""
import json,os,subprocess
from pathlib import Path
from entry_probe import ROOT,sha

def cache_runtime(tree,allow_fetch=False):
 definitions=[('llvm-project','https://github.com/llvm/llvm-project','58c46bae21181fb4240cf964461bea738d96d50e',['/compiler-rt/lib/profile/','/compiler-rt/include/profile/']),('Libc','https://github.com/apple-oss-distributions/Libc.git','899a3b2d52d95d75e05fb286a5e64975ec3de757',['/include/'])]
 result=[]
 for name,url,commit,patterns in definitions:
  directory=tree/'.cache/linux'/name;directory.mkdir(parents=True,exist_ok=True)
  def git(*args):return subprocess.run(['git','-C',str(directory),'-c','http.version=HTTP/1.1',*args],check=True)
  if not (directory/'.git').exists():git('init','-q')
  head=subprocess.run(['git','-C',str(directory),'rev-parse','HEAD'],capture_output=True,text=True)
  if head.returncode or head.stdout.strip()!=commit:
   if not allow_fetch:raise RuntimeError('Pinned runtime source is missing locally: '+name+' '+commit+'; automatic fetch is disabled')
   remote=subprocess.run(['git','-C',str(directory),'remote','get-url','origin'],capture_output=True,text=True)
   if remote.returncode:git('remote','add','origin',url)
   else:assert remote.stdout.strip()==url
   git('config','remote.origin.promisor','true');git('config','remote.origin.partialclonefilter','tree:0')
   git('sparse-checkout','set','--cone',*[p.strip('/') for p in patterns])
   git('fetch','--no-tags','--depth','1','--filter=tree:0','origin',commit)
   git('checkout','--detach',commit)
  assert subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()==commit
  assert not subprocess.check_output(['git','-C',str(directory),'diff','--name-only'],text=True).strip()
  inputs=[dict(path=str(p.relative_to(directory)),sha256=sha(p.read_bytes())) for p in directory.rglob('*') if p.is_file() and '.git' not in p.relative_to(directory).parts]
  assert inputs
  result.append(dict(name=name,url=url,commit=commit,patterns=patterns,files=inputs))
  print('Verified runtime source subtree',name,len(inputs),flush=True)
 return result
