#!/usr/bin/env python3
"""Recollect a project-owned 4KiB plaintext file and its LUN0 mapping, read-only."""
import argparse,datetime as dt,json,shlex,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
ADB='/mnt/d/Android/platform-tools/adb.exe'
def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--source-report',type=Path,required=True);a=p.parse_args()
 source=json.loads(a.source_report.read_text());file=source['source_file']
 assert source['created_only_new_private_stage'] and source['passed'] and file.startswith('/data/unixnu-raphael-stage-') and file.endswith('/probe.bin')
 out=ROOT/'evidence/private/ufs-readonly'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(mode=0o700,parents=True,exist_ok=False);print(out,flush=True)
 commands=[]
 def call(args,timeout=15):
  v=subprocess.run([ADB,'-s',a.serial,*args],capture_output=True,timeout=timeout)
  commands.append(dict(args=args,returncode=v.returncode,stderr=v.stderr.decode(errors='replace')));(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  assert v.returncode==0,v.stderr;return v.stdout
 def root(s):return call(['exec-out','su -c '+shlex.quote(s)])
 inspector='/data/local/tmp/raphael-fiemap-'+out.name
 path=subprocess.check_output(['wslpath','-w',str(ROOT/'artifacts/android-fiemap/inspector')],text=True).strip()
 call(['push',path,inspector]);root('chmod 700 '+shlex.quote(inspector))
 try:
  root('id');assert root('stat -c %s '+shlex.quote(file)).strip()==b'4096'
  mount=root('cat /proc/mounts');(out/'mounts.txt').write_bytes(mount)
  entries=[line.split() for line in mount.splitlines() if line.split()[1:3]==[b'/data',b'ext4']];assert len(entries)==1
  assert root('readlink -f '+shlex.quote(entries[0][0].decode())).strip()==b'/dev/block/sda31'
  raw=root(shlex.quote(inspector)+' '+shlex.quote(file));(out/'fiemap.json').write_bytes(raw);f=json.loads(raw)
  assert f['policy_rc']==-61 and f['flags_rc']==0 and f['fiemap_rc']==0 and not(f['inode_flags']&0x800) and f['count']==1
  e=f['extents'][0];assert e['logical']==0 and e['length']==4096 and e['flags']==1 and e['physical']%4096==0
  geo=root('readlink /sys/class/block/sda/device; cat /sys/class/block/sda/size; cat /sys/class/block/sda/queue/logical_block_size');(out/'lun0-geometry.txt').write_bytes(geo)
  lines=geo.decode().splitlines();assert lines[0].endswith('/0:0:0:0');sectors,block=map(int,lines[-2:]);assert block==4096
  part=root('cat /sys/class/block/sda31/start; cat /sys/class/block/sda31/size');(out/'partition-geometry.txt').write_bytes(part);start,size=map(int,part.split());absolute=start*512+e['physical'];assert absolute%block==0 and absolute+4096<=(start+size)*512<=sectors*512
  content=root('cat '+shlex.quote(file));assert len(content)==4096
  media=root('dd if=/dev/block/sda bs=4096 skip='+str(absolute//block)+' count=1 2>/dev/null');assert media==content
  assert json.loads(root(shlex.quote(inspector)+' '+shlex.quote(file)))==f,'Extent changed during collection'
  (out/'probe.bin').write_bytes(content);(out/'lun0-known-block.bin').write_bytes(media)
  report=dict(passed=True,source_report=str(a.source_report.resolve().relative_to(ROOT)),source_file=file,lba=absolute//block,lun0_byte_offset=absolute,bytes=4096,sha256=sha(content),file_encryption_policy_absent=True,partition_start_512_sectors=start,partition_size_512_sectors=size,extent=e,extent_stable_across_collection=True,media_written=False,handset_native_read_verified=False)
  (out/'read-source.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 finally:root('rm '+shlex.quote(inspector))
if __name__=='__main__':main()
