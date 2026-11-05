#!/usr/bin/env python3
"""Build bounded diagnostics using the original BSD and OSFMK compile recipes."""
import json,os,struct,subprocess,sys,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1]
assert os.environ.get('RAPHAEL_NATIVE_DIAGNOSTIC')=='1' and os.environ.get('RAPHAEL_HANDSET_UFS')=='1'
out=root/'build/raphael-service-observer';out.mkdir(parents=True,exist_ok=True)
objects=[]
recipes=[('RaphaelServiceObserver','bsd/DEVELOPMENT/bsd_init.o.json'),('RaphaelServiceThreadObserver','osfmk/DEVELOPMENT/startup.o.json')]
if os.environ.get('RAPHAEL_NATIVE_CONSOLE')=='1':recipes.append(('RaphaelNativeConsole','osfmk/DEVELOPMENT/startup.o.json'))
log_report=os.environ.get('RAPHAEL_UFS_CONSOLE_LOG_REPORT')
if log_report:
 sys.path.insert(0,str(Path(os.environ['RAPHAEL_WORKSPACE'])/'scripts'))
 from ufs_continuous_log import manifest
 a=manifest(Path(log_report));nonce=uuid.UUID(a['session']).int
 words=[int.from_bytes(b'RPHLAL01','little'),a['lun_blocks'],a['partition_first'],a['partition_blocks'],nonce&((1<<64)-1),nonce>>64,a['log_blocks'],4096,*a['log_lbas']]
 (out/'RaphaelUfsLogAllocation.h').write_text('const uint64_t raphael_ufs_log_allocation[] = {'+','.join(str(x)+'ULL' for x in words)+'};\n')
 recipes.append(('RaphaelUfsConsoleLog','osfmk/DEVELOPMENT/startup.o.json'))
for name,record in recipes:
 source=root/('kits/raphael/drivers/'+name+'.c');obj=out/(name+'.o')
 recipe=json.loads((root/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'/record).read_text().strip().rstrip(','))
 args=recipe['arguments'];cmd=[];i=0
 while i<len(args):
  v=args[i]
  if v==recipe['file']:cmd.append(str(source))
  elif v=='-o':cmd+=['-o',str(obj)];i+=1
  elif v in ('-MF','-MJ'):i+=1
  elif v=='-Xclang' and args[i+1].startswith('-W'):i+=1
  elif v not in ('-MD','-MP') and not v.startswith('-W'):cmd.append(v)
  i+=1
 if name=='RaphaelServiceObserver' and os.environ.get('RAPHAEL_SERVICE_SPAWN_WAITS')=='1':cmd+=['-DRAPHAEL_SERVICE_SPAWN_WAITS=1']
 if os.environ.get('RAPHAEL_NATIVE_CONSOLE')=='1':cmd+=['-DRAPHAEL_NATIVE_CONSOLE=1']
 if log_report:cmd+=['-DRAPHAEL_UFS_CONSOLE_LOG=1','-I',str(out)]
 cmd+=['-Wall','-Wextra','-Werror','-Wno-unused-parameter']
 (out/(name+'-command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 r=subprocess.run(cmd,cwd=recipe['directory'],capture_output=True,text=True);(out/(name+'-compile.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise SystemExit(r.stderr[-5000:])
 assert struct.unpack_from('<4I',obj.read_bytes())==(0xfeedfacf,0x100000c,0,1)
 (out/source.name).write_bytes(source.read_bytes());objects.append(obj)
archive=root/'build/armcpu/libArmCpu.a';assert archive.exists()
subprocess.run(['xcrun','ar','rcs',archive,*objects],check=True)
print('Bounded service snapshots: actual BSD and OSFMK -Werror objects linked into explicit diagnostic archive')
