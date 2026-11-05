#!/usr/bin/env python3
"""Run real RAM transaction C under ASan/UBSan with exhaustive callback faults."""
import datetime as dt,json,subprocess,tempfile,struct
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 parent=ROOT/'artifacts/ram-write-host';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 core=ROOT/'sources/mu_basecore/MdePkg/Include'
 paths=[ROOT/'scripts/fixtures/ram_write_host.c',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelRamWriteLib/RamWrite.c']
 cmd=['gcc','-O1','-g','-Wall','-Wextra','-Werror','-fshort-wchar','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(core),'-I'+str(core/'X64'),'-I'+str(ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include'),*[str(p) for p in paths],'-o',str(out/'host')]
 x=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,x.stderr.decode()
 x=subprocess.run([str(out/'host'),str(out/'result-le.bin')],capture_output=True);(out/'execution.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr).decode()
 cases=[l[5:] for l in x.stdout.decode().splitlines() if l.startswith('PASS ')];assert x.stdout.decode().splitlines()[-1]=='RAM_WRITE_HOST_OK '+str(len(cases))
 from ram_write_probe import decode,FIELDS
 raw=struct.pack('>23Q',*struct.unpack('<23Q',(out/'result-le.bin').read_bytes()))
 expected=dict(base=0x100000000,bytes=0x10000000);assert decode(raw,expected,1)['passed']
 wire_cases=[]
 values=dict(version=2,status=2,reason=1,base=0,bytes=0,page_bytes=8,requested_pages=2,completed_pages=0,active_page=1,backup_words=512,dirty=1,restored_pages=0,read_attempts=2047,write_attempts=1535,pattern_words=0,pattern_mismatches=1,restore_words=0,restore_mismatches=1,original_digest=0,restore_digest=1,start_counter=99999,end_counter=99999,frequency=0)
 for field,value in values.items():
  damaged=bytearray(raw);struct.pack_into('>Q',damaged,FIELDS.index(field)*8,value)
  try:decode(damaged,expected,1)
  except AssertionError:wire_cases.append('wire rejects '+field)
  else:raise AssertionError('damaged wire accepted: '+field)
 for damaged in [raw[:-8],raw+b'0']:
  try:decode(damaged,expected,1)
  except AssertionError:wire_cases.append('wire size rejected')
  else:raise AssertionError('damaged wire size accepted')
 paths+=[ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/Library/RaphaelRamWriteLib.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelRamRead.h',Path(__file__)]
 result=dict(passed=True,case_count=len(cases),cases=cases,command=cmd,address_sanitizer=True,undefined_behavior_sanitizer=True,injected_fault_positions=512+2048+1024+1024+512+512+512+10,wire_case_count=len(wire_cases),wire_cases=wire_cases,decoder_sha256=sha((ROOT/'scripts/ram_write_probe.py').read_bytes()),handset_executed=False,source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],limitations=['Host callbacks return normally; no real synchronous data abort exercised.','Synthetic memory and bounds are not phone RAM access or ownership evidence.','This host report does not validate SEC or handset execution.'])
 for p in [out/'report.json',ROOT/'UniXNU-raphael/evidence/ram-write-host.json']:p.write_text(json.dumps(result,indent=2)+'\n')
 print(len(cases),'actual RAM transaction C/ASan/UBSan checks');print(out)
if __name__=='__main__':main()
