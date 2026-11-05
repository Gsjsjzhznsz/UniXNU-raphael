#!/usr/bin/env python3
"""Validate the actual bounded proxy capture branch and its decoder; no device I/O."""
import datetime as dt,hashlib,importlib.util,json,os,struct,subprocess,sys
from pathlib import Path
from entry_probe import ROOT

def main():
 out=ROOT/'artifacts/service-spawn-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');out.mkdir(parents=True)
 source=ROOT/'UniXNU-raphael/package/drivers/RaphaelServiceObserver.c'
 code=source.read_text().split('// First real user exception')[0]
 code='\n'.join(l for l in code.splitlines() if not l.startswith('#include'))
 prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
typedef int pid_t;
struct fake_thread {uint64_t id;int refs;};
typedef struct fake_thread *thread_t;
struct uthread {thread_t thread;struct uthread *next;};
struct fake_head {struct uthread *first;};
struct fake_proc {int p_stat;char p_comm[32];struct fake_head p_uthlist;int refs;bool locked;};
typedef struct fake_proc *proc_t;
static struct fake_proc procs[256];
static struct fake_thread ts[256][2];
static struct uthread uts[256][2];
static unsigned captures;
#define TAILQ_FOREACH(v,h,field) for((v)=(h)->first;(v);(v)=(v)->next)
static size_t strlcpy(char *d,const char *s,size_t n){size_t l=strlen(s);if(n){size_t k=l<n-1?l:n-1;memcpy(d,s,k);d[k]=0;}return l;}
static proc_t proc_find(pid_t p){if(!procs[p].p_comm[0])return NULL;assert(!procs[p].refs);++procs[p].refs;return &procs[p];}
static void proc_rele(proc_t p){assert(p->refs==1 && !p->locked);--p->refs;}
static void proc_lock(proc_t p){assert(!p->locked);p->locked=true;}
static void proc_unlock(proc_t p){assert(p->locked);p->locked=false;}
static thread_t get_machthread(struct uthread *ut){return ut->thread;}
static void thread_reference(thread_t t){assert(t->refs==1);++t->refs;}
static void thread_deallocate(thread_t t){assert(t->refs==2);--t->refs;}
void raphael_service_thread_capture(thread_t t,volatile uint64_t *out){
 assert(t->refs==2);++captures;out[1]=t->id;out[58]=0xffffffff;
 out[10]=0x1110;out[12]=0x1000;out[60]=1;out[61]=1;out[64]=0x1000;out[65]=0x2220;
}
void raphael_service_kernel_probe_capture(void){}
'''
 suffix=r'''
int main(int argc,char **argv){
 assert(argc==5);int proxies=atoi(argv[1]),threads=atoi(argv[2]);
 // All proxy PIDs start at 1, exercising the shared launchd selection branch.
 for(int p=1;p<=proxies;++p){
  procs[p].p_stat=2;strcpy(procs[p].p_comm,"xpcproxy");
  for(int j=0;j<threads;++j){ts[p][j].id=p*10+j;ts[p][j].refs=1;uts[p][j].thread=&ts[p][j];if(j+1<threads)uts[p][j].next=&uts[p][j+1];}
  if(threads)procs[p].p_uthlist.first=&uts[p][0];
 }
 raphael_native_services_capture();
 assert(raphael_service_header[1]==2 && raphael_service_header[2]==255);
 assert(raphael_service_header[3]==(unsigned)proxies);
 assert(raphael_service_header[4]==(proxies?1:0));
 for(int p=1;p<=proxies;++p){assert(!procs[p].refs && !procs[p].locked);for(int j=0;j<threads;++j)assert(ts[p][j].refs==1);}
#if RAPHAEL_SERVICE_SPAWN_WAITS
 int n=proxies<64?proxies:64;
 assert(raphael_service_spawn_header[2]==2);
 assert(raphael_service_spawn_header[3]==(unsigned)proxies && raphael_service_spawn_header[4]==(unsigned)n);
 assert(captures==(unsigned)((proxies?threads:0)+(threads?n:0)));
 for(int i=0;i<n;++i){volatile uint64_t *o=raphael_service_spawn_threads[i];assert(o[0]==(unsigned)(i+1) && o[1]==(threads?1:0) && o[2]==(threads>1) && o[3]==2);if(threads)assert(o[9]==(unsigned)((i+1)*10));}
 FILE *f=fopen(argv[3],"wb");assert(f);assert(fwrite((void *)raphael_service_spawn_header,1,64,f)==64);assert(fwrite((void *)raphael_service_spawn_threads,1,sizeof(raphael_service_spawn_threads),f)==sizeof(raphael_service_spawn_threads));assert(!fclose(f));
#else
 assert(captures==(unsigned)(proxies?threads:0));
#endif
 FILE *g=fopen(argv[4],"wb");assert(g);assert(fwrite((void *)raphael_service_header,1,sizeof(raphael_service_header),g)==sizeof(raphael_service_header));assert(fwrite((void *)raphael_service_processes,1,sizeof(raphael_service_processes),g)==sizeof(raphael_service_processes));assert(fwrite((void *)raphael_service_threads,1,sizeof(raphael_service_threads),g)==sizeof(raphael_service_threads));assert(!fclose(g));
 return 0;
}
'''
 fixture=out/'capture.c';fixture.write_text(prefix+code+suffix)
 env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=1';env['UBSAN_OPTIONS']='halt_on_error=1'
 for enabled in [0,1]:
  cmd=['gcc','-std=c11','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-pie','-no-pie',f'-DRAPHAEL_SERVICE_SPAWN_WAITS={enabled}',str(fixture),'-o',str(out/f'capture-{enabled}')]
  result=subprocess.run(cmd,capture_output=True,text=True);(out/f'compile-{enabled}.log').write_text(result.stdout+result.stderr);assert not result.returncode,result.stderr
 from native_early import decode_service_spawn_snapshot
 checks=[]
 for proxies,threads in [(0,1),(1,1),(41,1),(64,1),(65,1),(255,1),(41,0),(41,2)]:
  for enabled in [0,1]:
   wire=out/f'wire-{proxies}-{threads}.bin';original=out/f'original-{enabled}-{proxies}-{threads}.bin'
   result=subprocess.run([str(out/f'capture-{enabled}'),str(proxies),str(threads),str(wire),str(original)],capture_output=True,text=True,env=env)
   (out/f'run-{enabled}-{proxies}-{threads}.log').write_text(result.stdout+result.stderr);assert not result.returncode,result.stderr
  assert (out/f'original-0-{proxies}-{threads}.bin').read_bytes()==original.read_bytes()
  blob=wire.read_bytes();symbols={'_raphael_service_spawn_header':0,'_raphael_service_spawn_threads':64}
  decoded=decode_service_spawn_snapshot(lambda a,n:blob[a:a+n],symbols,lambda pc:None)
  assert decoded['captured'] and decoded['observed_proxies']==proxies and len(decoded['processes'])==min(proxies,64)
  assert decoded['processes_truncated']==(proxies>64)
  assert all(len(p['threads'])==(1 if threads else 0) and p['threads_truncated']==(threads>1) for p in decoded['processes'])
  checks.append(dict(proxies=proxies,threads=threads,named_record_byte_equivalent=True,passed=True))
 # Reject malformed capacity/count/record states and duplicate or wrong identities.
 blob=(out/'wire-41-1.bin').read_bytes();rejects=[]
 for label,offset,value in [('version',8,2),('stage',16,3),('observed-overflow',24,256),('row-overflow',32,65),('incomplete-full-scan',32,40),('capacity',40,65),('thread-size',48,64),('row-size',56,135),('pid',64,256),('thread-count',72,2),('completion',88,1),('user-frames',64+(8+60)*8,17),('duplicate-pid',64+136*8,1),('wrong-name',64+32,0)]:
  changed=bytearray(blob);struct.pack_into('<Q',changed,offset,value)
  try:decode_service_spawn_snapshot(lambda a,n:changed[a:a+n],symbols,lambda pc:None)
  except (AssertionError,ValueError,struct.error):rejects.append(label)
  else:raise AssertionError('Accepted malformed '+label)
 assert decode_service_spawn_snapshot(lambda a,n:bytes(n),symbols,lambda pc:None)==dict(captured=False)
 # The refactor of the original thread decoder must reproduce all frozen threads.
 import native_early
 current=ROOT/'artifacts/service-spawn-review/current-work.json';work=ROOT/json.loads(current.read_text())['directory']
 spec=importlib.util.spec_from_file_location('before_native_early',work/'before/scripts/native_early.py');before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before)
 # Same synthetic original records include one/two/zero threads and empty scans.
 for proxies,threads in [(0,1),(41,0),(41,1),(41,2)]:
  raw=(out/f'original-1-{proxies}-{threads}.bin').read_bytes()
  syms={'_raphael_service_header':0,'_raphael_service_processes':64,'_raphael_service_threads':64+256*64,'_raphael_service_record_words':len(raw)}
  def reader(a,n):return struct.pack('<Q',128) if a==len(raw) else raw[a:a+n]
  assert native_early.decode_service_snapshot(reader,syms)==before.decode_service_snapshot(reader,syms)
 report=dict(passed=True,handset_executed=False,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),actual_capture_branch_host_asan_ubsan=True,capture_cases=checks,decoder_rejections=rejects,original_decoder_regression_cases=4,limits=['Mock process/thread objects validate bounded selection, lifetime and serialization; no handset scheduling or MMIO is covered.'])
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(json.dumps({'passed':True,'capture_cases':len(checks),'decoder_rejections':len(rejects),'original_decoder_regressions':4}))
if __name__=='__main__':main()
