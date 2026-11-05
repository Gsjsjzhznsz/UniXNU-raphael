#!/usr/bin/env python3
"""Actual route state machine with independently computed timer and GIC models."""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from entry_probe import ROOT,LIBFDT,sha
from validate_gic_probe import Snapshot as GicSnapshot
from validate_icc_probe import Snapshot as IccSnapshot
from validate_gic_enable_map import Snapshot as MapSnapshot
from gic_probe import recipe
from ppi_probe import resource
from timer_route import FIELDS,decode
class Snapshot(c.Structure):_fields_=[(k,c.c_uint64) for k in FIELDS]
class Guard(c.Structure):_fields_=[('before',c.c_ubyte*64),('result',Snapshot),('after',c.c_ubyte*64)]
def main():
 parent=ROOT/'artifacts/timer-route-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 source=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/TimerRoute.c';ppi=source.with_name('PpiProbe.c');core=ROOT/'sources/mu_basecore/MdePkg/Include'
 aliases={'FdtCheckHeader':'fdt_check_header','FdtGetProp':'fdt_getprop','FdtNextNode':'fdt_next_node','FdtParentOffset':'fdt_parent_offset'}
 command=['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=undefined','-fno-sanitize-recover=all',
 '-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),'-I'+str(LIBFDT)]
 command+=['-D'+a+'='+b for a,b in aliases.items()]
 command+=[str(source),str(ppi),*[str(LIBFDT/(n+'.c')) for n in ['fdt','fdt_ro','fdt_rw','fdt_wip','fdt_addresses']],'-o',str(out/'timer-route.so')]
 p=subprocess.run(command,capture_output=True);(out/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
 lib=c.CDLL(str(out/'timer-route.so'));mr=c.CFUNCTYPE(c.c_uint32,c.c_uint64,c.c_void_p);mw=c.CFUNCTYPE(None,c.c_uint64,c.c_uint32,c.c_void_p)
 sr=c.CFUNCTYPE(c.c_uint8,c.c_uint32,c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.c_void_p)
 sw=c.CFUNCTYPE(c.c_uint8,c.c_uint32,c.c_uint64,c.POINTER(c.c_uint64),c.POINTER(c.c_uint64),c.c_void_p)
 collect=lib.RaphaelTestTimerRoute;collect.argtypes=[c.c_void_p,c.POINTER(GicSnapshot),c.POINTER(IccSnapshot),c.POINTER(MapSnapshot),c.POINTER(Snapshot),mr,mw,sr,sw,c.c_void_p]
 window_type=c.CFUNCTYPE(c.c_uint8,c.c_void_p,c.c_uint64,c.c_uint64)
 extended=lib.RaphaelTestTimerRouteWithIrq;extended.argtypes=collect.argtypes+[window_type,c.c_void_p]
 blob=(ROOT/'evidence/private/interrupt-audit/20261027T203039.031418Z/live.dtb').read_bytes();plan=recipe(blob);intid,flags=resource(blob)
 d=plan['gicd'];rd=plan['gicr']+5*plan['stride'];sgi=rd+0x10000;mask=1<<intid;freq=19200000;cases=[]
 def case(name,status=6,gchange=None,ichange=None,ivals=None,mapchange=None,map_array=False,stale=None,wi=None,write_trap=None,read_trap=None,unexpected=False,timeout=False,withdraw_delay=0,rwp_delay=0,rwp_stuck=False,restore_fail=False,no=None,window_mode=None,expire_between=False):
  g=GicSnapshot();g.version=1;g.status=4;g.pidr2=0x3b;g.typer=29;g.ctlr=0x10;g.gicd=d;g.gicd_bytes=plan['gicd_bytes'];g.gicr=plan['gicr'];g.gicr_bytes=plan['gicr_bytes'];g.frame_count=8;g.boot_index=5;g.mpidr=0x81000000;g.affinity=0;g.frames[5].base=rd
  i=IccSnapshot();i.version=1;i.status=5;i.attempted=i.completed=16;i.failed_selector=(1<<64)-1;i.values[0]=4;i.values[1]=0x3c0;i.values[2]=g.mpidr;i.values[3]=1;i.values[5]=0xf0;i.values[8]=255;i.values[9]=1023;i.values[15]=freq
  m=MapSnapshot();m.version=1;m.status=3;m.read_count=93;m.spi_words=29;m.frame_count=8;m.distributor_before=m.distributor_after=0x10;m.all_observed_disabled=1
  for key,value in (gchange or {}).items():setattr(g,key,value)
  for key,value in (ichange or {}).items():setattr(i,key,value)
  for key,value in (ivals or {}).items():i.values[key]=value
  for key,value in (mapchange or {}).items():setattr(m,key,value)
  if map_array:m.spi[28]=1
  state=dict(dist=0x10,enabled=0,pending=0x10080000,active=0,igrpen=0,ctl=0,cval=0,ticks=100000,daif=0x3c0)
  state.update(stale or {});initial=dict(state);bad=[];reads=[];writes=[];sysreads=[];syswrites=[];busy={};clear=[withdraw_delay];expired_between=[False]
  def pending():
   asserted=state['ctl']&1 and not(state['ctl']&2) and state['ticks']>=state['cval']
   if asserted:return state['pending']|mask
   if len(syswrites)>=4 and clear[0]>0:clear[0]-=1;return state['pending']|mask
   return state['pending']
  @mr
  def read(a,context):
   reads.append(a)
   if a==d:
    if busy.get(a,0):busy[a]-=1;return state['dist']|0x80000000
    return state['dist']
   if a==rd:
    if rwp_stuck and len(writes)>1:return 8
    if busy.get(a,0):busy[a]-=1;return 8
    return 0
   if a==rd+0x14:return state.get('waker',0)
   if a==sgi+0x100:return state['enabled']
   if a==sgi+0x200:return pending()
   if a==sgi+0x300:return state['active']
   bad.append(('read',a));return 0
  @mw
  def write(a,v,context):
   writes.append((a,v))
   if a==d:
    if v not in [0x10,0x12]:bad.append(('dist value',v))
    if not(wi=='dist' and v==0x12):state['dist']=v
    if v==0x10:busy[d]=rwp_delay
   elif a==sgi+0x100 and v==mask:
    if wi!='ppi':state['enabled']|=v
   elif a==sgi+0x180 and v==mask:
    if not restore_fail:state['enabled']&=~v
    busy[rd]=rwp_delay
   else:bad.append(('write',a,v))
  @sr
  def sread(n,v,esr,elr,context):
   sysreads.append(n)
   if read_trap and len(sysreads)==read_trap:esr[0]=1<<26;elr[0]=0x1234;return 0
   if n==0:state['ticks']+=freq//1000;value=state['ticks']
   elif n==1:value=state['ctl']|(4 if state['ctl']&1 and state['ticks']>=state['cval'] else 0)
   elif n==2:value=state['cval']
   elif n==3:value=state['igrpen']
   elif n==4:
    if expire_between and not expired_between[0] and state['igrpen'] and state['ctl']==1 and state['ticks']<state['cval']:
     state['ticks']=state['cval'];expired_between[0]=True
    routed=state['dist']&2 and state['enabled']&mask and state['igrpen'] and pending()&mask and not timeout
    value=99 if unexpected and state['igrpen'] else intid if routed else 1023
   elif n==5:value=state['daif']
   else:bad.append(('sysread',n));value=0
   v[0]=value;return 1
  @sw
  def swrite(n,v,esr,elr,context):
   syswrites.append((n,v))
   if n==1 and v in [0,1,2]:state['ctl']=v
   elif n==2:state['cval']=v
   elif n==3 and v<=1:state['igrpen']=v
   else:bad.append(('syswrite',n,v))
   if write_trap and len(syswrites)==write_trap:esr[0]=1<<26;elr[0]=0x1234;return 0
   return 1
  guard=Guard()
  for n in range(64):guard.before[n]=guard.after[n]=0xa5
  window_calls=[]
  @window_type
  def window(result,irq,hz):
   window_calls.append((irq,hz))
   assert result and irq==intid and hz==freq and state['ctl']==1
   assert pending()&mask and state['igrpen']==1 and state['dist']&2 and state['enabled']==mask
   if window_mode=='reject':return 0
   state['ctl']=2;return 1
  arguments=[None if no=='fdt' else blob,None if no=='gic' else c.byref(g),None if no=='icc' else c.byref(i),None if no=='map' else c.byref(m),c.byref(guard.result),mr() if no=='mr' else read,mw() if no=='mw' else write,sr() if no=='sr' else sread,sw() if no=='sw' else swrite,None]
  if window_mode:
   dummy=c.c_uint64();extended(*arguments,window,None if window_mode=='no_result' else c.byref(dummy))
   assert len(window_calls)==int(window_mode in ['success','reject']),name
  else:collect(*arguments)

  o=guard.result
  assert not bad,(name,bad)
  if expire_between:assert expired_between[0],name
  assert bytes(guard.before)==bytes(guard.after)==b'\xa5'*64
  assert o.version==1 and o.status==status and o.mmio_reads==len(reads) and o.mmio_writes==len(writes) and o.sys_reads==len(sysreads) and o.sys_writes==len(syswrites),(name,o.status,o.reason,o.restore_ok,syswrites)
  if status in [1,2]:assert not writes and not syswrites,name
  else:
   assert [a for a,v in writes if a in [sgi+0x100,sgi+0x180]] in [[],[sgi+0x180],[sgi+0x100,sgi+0x180]]
   if status!=5:
    for key in ['dist','enabled','igrpen','ctl','cval','daif']:assert state[key]==initial[key],(name,key,state[key],initial[key])
   assert o.restore_ok==int(status!=5),name
  raw=struct.pack('>'+str(len(FIELDS))+'Q',*struct.unpack('<'+str(len(FIELDS))+'Q',bytes(o)))
  gd=dict(boot_index=5,ctlr=g.ctlr,frames=[dict(base=0)]*5+[dict(base=rd)])
  im=dict(cntp_ctl=i.values[10],cntp_cval=i.values[11],cntfrq=i.values[15]);em=dict(passed=True,status=3,all_observed_disabled=1)
  if status==6:assert decode(raw,blob,gd,em,im)['passed']
  else:
   try:decode(raw,blob,gd,em,im)
   except (AssertionError,ValueError):pass
   else:raise AssertionError('failed route wire accepted '+name)
  cases.append(dict(name=name,status=status,mmio_writes=len(writes),sys_writes=len(syswrites),passed=True))
  return raw,gd,em,im
 wire,gd,em,im=case('local source routed by independently computed model')
 case('source expires between CTL and HPPIR sampling',expire_between=True)
 case('IRQ leaf after expiration between CTL and HPPIR sampling',window_mode='success',expire_between=True)
 case('optional IRQ leaf runs only after HPPIR and pending proof',window_mode='success')
 case('optional IRQ leaf rejection still restores route',3,window_mode='reject')
 case('optional IRQ leaf skipped on PPI write ignored',3,wi='ppi',window_mode='skipped')
 case('optional IRQ leaf needs a result pointer',1,window_mode='no_result')
 case('delayed source withdrawal',withdraw_delay=4)
 case('delayed distributor and redistributor RWP',rwp_delay=3)
 case('PPI write ignored',3,wi='ppi');case('distributor write ignored',3,wi='dist')
 case('HPPIR unexpected interrupt stops experiment',3,unexpected=True)
 case('no route reaches bounded timeout',4,timeout=True)
 case('RWP never clears makes restore fail',5,rwp_stuck=True)
 case('PPI clear ignored makes restore fail',5,restore_fail=True)
 for n in range(1,4):case('write trap after possible effect '+str(n),3,write_trap=n)
 for n in [4,5,6,7]:case('restore write trap still attempts remaining operations '+str(n),5,write_trap=n)
 for n in [1,3,5,6]:case('fresh read trap '+str(n),2,read_trap=n)
 for n in [7,8,9,10]:case('active read trap '+str(n),3,read_trap=n)
 for missing in ['fdt','gic','icc','map','mr','mw','sr','sw']:case('missing '+missing,1,no=missing)
 for key,value in [('version',2),('status',4),('all_observed_disabled',0),('enabled_spi_or',1),('enabled_local_or',1),('lpi_enabled_or',1),('changed_words',1),('frame_count',7),('spi_words',30),('read_count',0),('distributor_after',0x12)]:case('map rejects '+key,1,mapchange={key:value})
 case('nonzero map array with forged OR',1,map_array=True)
 for key,value in [('version',2),('status',4),('trap_esr',1),('completed',15)]:case('ICC rejects '+key,1,ichange={key:value})
 for n,value in [(0,8),(1,0x340),(2,1),(3,0),(5,0),(7,1),(8,0),(9,18),(10,1),(15,0)]:case('ICC rejects value '+str(n),1,ivals={n:value})
 for key,value in [('version',2),('status',3),('pidr2',0x4b),('typer',1<<8),('gicd',d+4),('gicr',rd+4),('boot_index',8)]:case('GIC rejects '+key,1,gchange={key:value})
 for key,value in [('daif',0x340),('igrpen',1),('dist',0x12),('enabled',1),('pending',mask),('active',1),('ctl',1),('cval',1),('waker',2)]:case('fresh rejects '+key,2,stale={key:value})
 for field,value in [('version',2),('status',4),('reason',1),('intid',30),('flags',4),('sgi_base',0),('dist_during',0x10),('restored_dist',0x12),('igrpen_during',0),('restored_igrpen',1),('restored_ctl',1),('restored_cval',1),('deadline',1),('ctl_during',7),('hppir_during',1023),('hppir_after',18),('pending_during',0),('enabled_after',mask),('active_after',1),('daif_after',0),('polls',0),('clear_polls',0),('rwp_polls',0),('mmio_writes',0),('sys_writes',0),('restore_ok',0),('trap_esr',1)]:
  raw=bytearray(wire);struct.pack_into('>Q',raw,FIELDS.index(field)*8,value)
  try:decode(raw,blob,gd,em,im)
  except (AssertionError,ValueError):cases.append(dict(name='wire rejects '+field,passed=True))
  else:raise AssertionError(field)
 inputs=[source,ppi,ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelTimerRoute.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPpiProbe.h']
 report=dict(passed=True,case_count=len(cases),cases=cases,command=command,snapshot_bytes=c.sizeof(Snapshot),guard_canaries_verified=True,undefined_behavior_sanitizer=True,
  model_only=True,handset_executed=False,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in inputs],decoder_sha256=sha((ROOT/'scripts/timer_route.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()))
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/timer-route-host.json').write_text(json.dumps(report,indent=2)+'\n')
 print(len(cases),'actual C/FDT/UBSan/guard/route/withdraw/restore checks passed');print(out)
if __name__=='__main__':main()
