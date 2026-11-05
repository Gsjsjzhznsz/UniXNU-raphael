#!/usr/bin/env python3
"""Actual payload hasher/reader under ASan+UBSan against hashlib vectors."""
import datetime,json,subprocess,tempfile,hashlib,random
from pathlib import Path
from entry_probe import ROOT,sha

def main():
 out=ROOT/'artifacts/payload-hash-host'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
 source=ROOT/'scripts/fixtures/raphael_payload_hash.cpp'
 command=['g++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined',str(source),'-o',str(out/'fixture')]
 subprocess.run(command,check=True,capture_output=True)
 blocks=[bytes(4096),bytes([255])*4096,bytes(range(256))*16]+[random.Random(seed).randbytes(4096) for seed in range(32)]
 result=subprocess.run([str(out/'fixture')],input=b''.join(blocks),capture_output=True,check=True)
 (out/'execution.log').write_bytes(result.stdout+result.stderr)
 lines=result.stdout.decode().splitlines();assert lines[:len(blocks)]==[hashlib.sha256(b).hexdigest() for b in blocks]
 checks=sum(s.startswith('PASS ') for s in lines);assert checks==12
 report=dict(passed=True,sha256_vectors=len(blocks),reader_checks=checks,source_sha256=sha(source.read_bytes()),header_sha256=sha((ROOT/'UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelPayloadHash.h').read_bytes()),command=command,handset_executed=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
