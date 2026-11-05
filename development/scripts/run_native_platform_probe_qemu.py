#!/usr/bin/env python3
"""Focused runtime probes of the current Image, with no repeated source hashes."""
import argparse,datetime,json,re,struct,subprocess,tempfile,time
from pathlib import Path
from entry_probe import ROOT
from native_early import image
from native_mmu import FIELDS
from native_platform import decode as timers

def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',type=Path,required=True);p.add_argument('--mode',choices=['panic','mainline'],required=True);p.add_argument('--target',default='_bsd_init');p.add_argument('--kalloc-zones',type=int);a=p.parse_args()
 qp=a.qemu_report.resolve();q=json.loads(qp.read_text());assert q['passed'] and q['native_platform_test']
 out=Path(tempfile.mkdtemp(prefix=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=ROOT/'artifacts'));print(out,flush=True)
 k=subprocess.check_output(['mtype','-i',str(qp.parent/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho']);segs,sy=image(k);c=q['native_mmu_contract'];sock='/tmp/rplatform-'+out.name[:20]+'.sock'
 def raw(v,n):
  z=next(s for s in segs if s['virtual']<=v<v+n<=s['virtual']+s['file_bytes']);at=z['offset']+v-z['virtual'];return k[at:at+n]
 for v,n,name in [(c['policy']['low_vectors'],4096,'low-vectors.bin'),(c['policy']['high_vectors'],2048,'high-vectors.bin'),(sy['_panic'],4,'panic.bin'),(sy['_panic_with_options'],4,'panic-options.bin')]: (out/name).write_bytes(raw(v,n))
 marker=k.index(b'kprintf initialized'+bytes([10]));z=next(s for s in segs if s['offset']<=marker<s['offset']+s['file_bytes']);fmt=z['virtual']+marker-z['offset']
 names=['_serial_init','_kprintf','_kernel_bootstrap','_vm_mem_bootstrap','_PE_init_iokit','_bsd_init','_IOFindBSDRoot','_panic','_panic_with_options']
 spec=dict(output=str(out),mode=a.mode,target=a.target,socket=sock,contract=c,symbols={n:sy[n] for n in names},format_address=fmt,kalloc_zones=a.kalloc_zones)
 (out/'spec.json').write_text(json.dumps(spec,indent=2)+chr(10));observer=ROOT/'scripts/fixtures/native_platform_probe_gdb.py';(out/'observer.py').write_bytes(observer.read_bytes());(out/'debug.gdb').write_text('python'+chr(10)+'SPEC='+repr(str(out/'spec.json'))+chr(10)+'exec(compile(open('+repr(str(out/'observer.py'))+').read(),"observer.py","exec"))'+chr(10)+'end'+chr(10)+'quit'+chr(10))
 command=q['command']+['-S','-gdb','unix:'+sock+',server=on,wait=off'];r=dict(passed=False,qemu_only=True,handset_executed=False,mode=a.mode,positive_report=str(qp.relative_to(ROOT)),command=command);proc=None
 try:
  with (out/'serial.log').open('xb') as log:
   proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);time.sleep(.2)
   g=subprocess.run(['gdb-multiarch','-q','--nx','--batch','-x',str(out/'debug.gdb')],capture_output=True,timeout=50);(out/'gdb.log').write_bytes(g.stdout+g.stderr)
   obs=json.loads((out/'observation.json').read_text());r['observation']=obs
   if a.mode=='panic':
    rc=proc.wait(timeout=8);lograw=(out/'serial.log').read_bytes();m=re.search(rb'NATIVE_MMU_WIRE ([0-9a-f]+)',lograw);assert m
    d=dict(zip(FIELDS,struct.unpack('>72Q',bytes.fromhex(m[1].decode()))));assert d['esr']==0xf2005353 and d['elr']==sy['_panic'] and d['status']==2 and d['trap_count']==1
    assert all(d[n]==1 for n in ['patch_restored','tables_restored','mmu_restored']) and d['segments_ok']==d['zero_ok']==10
    m=re.search(rb'NATIVE_PLATFORM_WIRE ([0-9a-f]+)',lograw);assert m;v=timers(bytes.fromhex(m[1].decode()),c['early']['policy']['reserved2']);assert v['restore_ok']==1
    assert b'PASS real high stub decode completed' in lograw and b'ANDROID_RETURN_QEMU_FAILED' in lograw and rc!=0
    r.update(passed=True,expected_target_failure=True,recovery_executed=True,mmu=d,timers=v)
   else:
    r['passed']=obs['target_reached'];r['blocked_by_panic']=bool(obs.get('panic'))
    if obs.get('panic'):
     byaddr=sorted((v,n) for n,v in sy.items())
     import bisect
     callchain=[]
     for frame in obs['panic']['frames']:
      i=bisect.bisect_right(byaddr,(frame['lr'],chr(0x10ffff)))-1;v,n=byaddr[i];callchain.append(dict(symbol=n,offset=frame['lr']-v))
     r['panic_callchain']=callchain
 except Exception as e:r['failure']=str(e);raise
 finally:
  if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
  (out/'report.json').write_text(json.dumps(r,indent=2)+chr(10))
 print(json.dumps({k:r[k] for k in ['passed','mode']},indent=2))
 if a.mode=='mainline' and r.get('blocked_by_panic'):print(json.dumps(r['observation']['panic'],indent=2))
if __name__=='__main__':main()
