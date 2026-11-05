#!/usr/bin/env python3
"""Compile exact primary Apple declarations and compare the consumed boot_args ABI."""
import datetime as dt
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
from entry_probe import ROOT,sha

APPLE='1031c584a5e37aff177559b9f69dbd3c8c3fd30a'
TAG_OBJECT='a653a70d861014a544bffa506779088605bbabac'
DARWIN='3325e352d7df68a9f9ad74832ed94a6acbbd7390'
FIELDS=[('Revision','Revision'),('Version','Version'),('virtBase','VirtualBase'),('physBase','PhysicalBase'),
 ('memSize','MemorySize'),('topOfKernelData','TopOfKernelData'),('Video','Video'),('machineType','MachineType'),
 ('deviceTreeP','DeviceTree'),('deviceTreeLength','DeviceTreeLength'),('CommandLine','CommandLine'),
 ('bootFlags','BootFlags'),('memSizeActual','MemorySizeActual')]


def pinned(repository,revision,name):
 path=ROOT/repository
 assert subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()==revision
 raw=subprocess.check_output(['git','-C',str(path),'show',revision+':'+name]);assert raw==(path/name).read_bytes()
 return raw


def main():
 apple=pinned('sources/apple-xnu-abi',APPLE,'pexpert/pexpert/arm64/boot.h')
 darwin=pinned('sources/UniXNU/drivers/DarwinBoot',DARWIN,'DarwinBootPkg/Driver/BootArgs.h')
 repo=ROOT/'sources/apple-xnu-abi'
 assert subprocess.check_output(['git','-C',str(repo),'rev-parse',TAG_OBJECT+'^{commit}'],text=True).strip()==APPLE
 parent=ROOT/'artifacts/boot-args-abi';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 text=apple.decode()
 video=re.search(r'struct Boot_Video \{.*?\n\};',text,re.S).group()
 args=re.search(r'typedef struct boot_args \{.*?\n\} boot_args;',text,re.S).group()
 line=re.search(r'^#define BOOT_LINE_LENGTH\s+(\d+)',text,re.M);assert line and line[1]=='1024'
 declarations=video+'\ntypedef struct Boot_Video Boot_Video;\n#define BOOT_LINE_LENGTH '+line[1]+'\n'+args+'\n'
 source='#include <stdint.h>\n#include "BootArgs.h"\n'+declarations
 values=['sizeof(boot_args)','sizeof(DARWIN_BOOT_ARGS)','_Alignof(boot_args)','_Alignof(DARWIN_BOOT_ARGS)']
 for a,b in FIELDS:
  values+=['__builtin_offsetof(boot_args,'+a+')','__builtin_offsetof(DARWIN_BOOT_ARGS,'+b+')']
  source+='_Static_assert(__builtin_offsetof(boot_args,'+a+')==__builtin_offsetof(DARWIN_BOOT_ARGS,'+b+'),"'+a+' offset");\n'
 source+='_Static_assert(sizeof(boot_args)==sizeof(DARWIN_BOOT_ARGS),"size");\n'
 source+='__attribute__((used,section(".abi_layout"))) const uint64_t abi_layout[]={'+','.join(values)+'};\n'
 (out/'abi.c').write_text(source);commands=[];reports={}
 core=ROOT/'sources/mu_basecore/MdePkg/Include';driver=ROOT/'sources/UniXNU/drivers/DarwinBoot/DarwinBootPkg/Driver'
 for target,cc,objcopy,arch in [('host','gcc','objcopy','X64'),('aarch64','aarch64-linux-gnu-gcc','aarch64-linux-gnu-objcopy','AArch64')]:
  command=[cc,'-fshort-wchar','-ffreestanding','-Wall','-Wextra','-Werror','-I'+str(core),'-I'+str(core/arch),'-I'+str(driver),'-c',str(out/'abi.c'),'-o',str(out/(target+'.o'))]
  commands.append(command);p=subprocess.run(command,capture_output=True);(out/(target+'-build.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
  command=[objcopy,'-O','binary','-j','.abi_layout',str(out/(target+'.o')),str(out/(target+'.bin'))]
  commands.append(command);subprocess.run(command,capture_output=True,check=True)
  raw=(out/(target+'.bin')).read_bytes();assert len(raw)==len(values)*8
  v=struct.unpack('<'+'Q'*len(values),raw);assert v[0]==v[1]==0x480 and v[2]==v[3]==8
  offsets={}
  for i,(a,b) in enumerate(FIELDS):assert v[4+i*2]==v[5+i*2];offsets[a]=dict(darwin_field=b,offset=v[4+i*2])
  reports[target]=dict(size=v[0],alignment=v[2],fields=offsets,object_sha256=sha((out/(target+'.o')).read_bytes()),compiler_version=subprocess.check_output([cc,'--version'],text=True).splitlines()[0])
 assert (out/'host.bin').read_bytes()==(out/'aarch64.bin').read_bytes()
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 result=dict(passed=True,check_count=len(FIELDS)+2,command='python3 scripts/audit_boot_args_abi.py',
   source='Apple official xnu-10002.1.13 arm64 boot.h',apple_tag_object=TAG_OBJECT,apple_commit=APPLE,apple_boot_h_sha256=sha(apple),
   darwin_commit=DARWIN,darwin_boot_args_sha256=sha(darwin),targets=reports,
   extraction='Exact Boot_Video and boot_args declarations, excluding kernel-only includes; no structure rewrite',
   build_commands=commands,artifact_directory=str(out.relative_to(ROOT)),runner_sha256=sha(Path(__file__).read_bytes()),
   handset_executed=False,xnu_built=False,xnu_executed=False,os_profile_selected=False,
   limits='Only boot_args structure layout at one Apple release. No proof of platform ABI, early MMU mappings, drivers or kernel execution.')
 dest=ROOT/'UniXNU-raphael/evidence/boot-args-abi.json';dest.write_text(json.dumps(result,indent=2)+'\n')
 print(str(result['check_count'])+' boot_args layout comparisons passed on host and AArch64');print(dest)

if __name__=='__main__':main()
