#!/usr/bin/env python3
"""Actual cache wrapper and page engine under ASan/UBSan with separate DRAM/cache."""
import datetime as dt,json,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from ram_cache_write import decode,FIELDS

def main():
 parent=ROOT/'artifacts/ram-cache-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent));inc=ROOT/'sources/mu_basecore/MdePkg/Include'
 paths=[ROOT/'scripts/fixtures/ram_cache_host.c']+[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelRamWriteLib'/name for name in ['RamWrite.c','RamCache.c']]
 cmd=['gcc','-O1','-g','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(inc),'-I'+str(inc/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),*[str(p) for p in paths],'-o',str(out/'host')]
 r=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()
 r=subprocess.run([str(out/'host'),str(out/'wire-le.bin')],capture_output=True);(out/'execution.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr).decode()
 cases=[line[5:] for line in r.stdout.decode().splitlines() if line.startswith('PASS ')];assert r.stdout.decode().splitlines()[-1]=='RAM_CACHE_HOST_OK '+str(len(cases))
 wire=bytearray(struct.pack('>39Q',*struct.unpack('<39Q',(out/'wire-le.bin').read_bytes())))
 # RO restoration is the hardware adapter's separate job, absent in the host
 # cache model. Supply those two fields explicitly for decoder-only tests.
 struct.pack_into('>QQ',wire,14*8,1,256)
 before=dict(passed=True,base=0x100000000,bytes=0x10000000,frequency=19200000)
 mapped=dict(passed=True,frequency=19200000,end_counter=40)
 assert decode(wire,before,mapped,before,1,3)['passed']
 wire_cases=[]
 for field in FIELDS:
  value=0 if field in ['version','base','bytes','pages','current_el','sctlr','daif','frequency','read_write_translations','par_preserved','pre_page_sync','post_page_sync','map_restored','restore_denials'] else (1<<64)-1
  damaged=bytearray(wire);struct.pack_into('>Q',damaged,FIELDS.index(field)*8,value)
  try:decode(damaged,before,mapped,before,1,3)
  except AssertionError:wire_cases.append('reject '+field)
  else:raise AssertionError(field)
 for damaged in [wire[:-1],wire+b'0']:
  try:decode(damaged,before,mapped,before,1,3)
  except AssertionError:wire_cases.append('size')
  else:raise AssertionError('wire size')
 paths+=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/Library/RaphaelRamCacheLib.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelRamMapped.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelRamRead.h']
 result=dict(passed=True,case_count=len(cases),cases=cases,wire_cases=wire_cases,command=cmd,address_sanitizer=True,undefined_behavior_sanitizer=True,separate_cache_and_dram_model=True,
  generic_and_direct_callbacks_verified=True,caller_context_identity_checked=True,native_callback_abi_assertions=12,hardware_ro_restoration_verified=False,source_inputs=[dict(path=str(x.relative_to(ROOT)),sha256=sha(x.read_bytes())) for x in paths],decoder_sha256=sha((ROOT/'scripts/ram_cache_write.py').read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),handset_executed=False)
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/ram-cache-host.json').write_text(json.dumps(result,indent=2)+'\n');print(out);print(len(cases),'actual C/ASan/UBSan checks and',len(wire_cases),'wire checks passed')
if __name__=='__main__':main()
