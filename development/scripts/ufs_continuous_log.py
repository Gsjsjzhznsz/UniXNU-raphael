#!/usr/bin/env python3
"""Private append-only handset console allocation and Android extraction."""
import argparse,datetime as dt,json,shlex,struct,subprocess,uuid,zlib
from pathlib import Path
from entry_probe import ROOT
ADB='/mnt/d/Android/platform-tools/adb.exe'
MAGIC=int.from_bytes(b'RPHLOG01','little');BLOCK=4096;HEADER=64;PAYLOAD=BLOCK-HEADER
GUARD=bytes((i*17+0x35)&255 for i in range(BLOCK))
def connected():
 rows=[x.split()[0] for x in subprocess.check_output([ADB,'devices'],text=True).splitlines()[1:] if len(x.split())==2 and x.split()[1]=='device']
 assert len(rows)==1,'One Android device required';return rows[0]
def root(serial,cmd,data=None):
 p=subprocess.run([ADB,'-s',serial,'exec-in' if data is not None else 'exec-out','su -c '+shlex.quote(cmd)],input=data,capture_output=True,timeout=60)
 assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout
def manifest(path):
 p=path.resolve();assert p.is_relative_to(ROOT/'evidence/private/ufs-console-log');d=json.loads(p.read_text());assert d['prepared'] and d['immutable'] and d['plaintext']
 assert len(d['log_lbas'])==d['log_blocks'] and len(set(d['log_lbas']))==d['log_blocks']
 assert not set(d['guard_lbas'])&set(d['log_lbas'])
 assert d['log_lbas']==list(range(d['log_lbas'][0],d['log_lbas'][0]+d['log_blocks'])),'Console log requires one contiguous allocation'
 assert all(d['partition_first']<=x<d['partition_first']+d['partition_blocks'] and x<=0xffffffff for x in d['log_lbas']+d['guard_lbas'])
 assert d['partition_first']+d['partition_blocks']<=d['lun_blocks']
 return d
def inspect(serial,target,out):
 remote='/data/local/tmp/raphael-log-fiemap-'+uuid.uuid4().hex
 win=subprocess.check_output(['wslpath','-w',str(ROOT/'artifacts/android-fiemap/inspector')],text=True).strip();subprocess.run([ADB,'-s',serial,'push',win,remote],check=True,capture_output=True);root(serial,'chmod 700 '+remote)
 try:return json.loads(root(serial,remote+' '+shlex.quote(target)))
 finally:root(serial,'rm '+remote)
def decode(raw,d):
 assert len(raw)==(d['log_blocks']+2)*BLOCK and raw[:BLOCK]==raw[-BLOCK:]==GUARD,'Log guards changed'
 body=[];records=[];bad=None;nonce=uuid.UUID(d['session']).int;lo=nonce&((1<<64)-1);hi=nonce>>64
 for seq in range(d['log_blocks']):
  block=raw[(seq+1)*BLOCK:(seq+2)*BLOCK]
  if not any(block):break
  words=struct.unpack_from('<8Q',block);magic,nlo,nhi,number,counter,length,dropped,crc=words
  check=bytearray(block);struct.pack_into('<Q',check,56,0)
  if magic!=MAGIC or (nlo,nhi)!=(lo,hi) or number!=seq or length>PAYLOAD or crc!=zlib.crc32(check):bad=dict(block=seq,reason='incomplete or invalid record');break
  body.append(block[HEADER:HEADER+length]);records.append(dict(sequence=seq,counter=counter,bytes=length,dropped=dropped))
 return b''.join(body),dict(valid_records=len(records),bytes=sum(x['bytes'] for x in records),dropped=records[-1]['dropped'] if records else 0,first_counter=records[0]['counter'] if records else None,last_counter=records[-1]['counter'] if records else None,invalid_tail=bad,session=d['session'],guards_unchanged=True)
def qualify_kernel(path,report_path):
 d=manifest(report_path)
 from native_early import image
 raw=path.read_bytes();segments,symbols=image(raw)
 nonce=uuid.UUID(d['session']).int
 words=[int.from_bytes(b'RPHLAL01','little'),d['lun_blocks'],d['partition_first'],d['partition_blocks'],nonce&((1<<64)-1),nonce>>64,d['log_blocks'],4096,*d['log_lbas']]
 expected=struct.pack('<'+'Q'*len(words),*words);va=symbols['_raphael_ufs_log_allocation']
 seg=next(x for x in segments if x['virtual']<=va and va+len(expected)<=x['virtual']+x['file_bytes']);offset=seg['offset']+va-seg['virtual']
 assert raw[offset:offset+len(expected)]==expected,'Compiled log allocation differs from prepared file'
 assert all(x in symbols for x in ['_raphael_ufs_log_capture','_raphael_ufs_log_flush','_raphael_ufs_diagnostic_append'])
 return dict(report=str(report_path.resolve().relative_to(ROOT)),session=d['session'],source_file=d['source_file'],log_blocks=d['log_blocks'])
def check_live(metadata,serial):
 d=manifest(ROOT/metadata['report']);f=inspect(serial,d['source_file'],None);assert f==d['fiemap'],'Log allocation moved'
 start,size=map(int,root(serial,'cat /sys/class/block/sda31/start; cat /sys/class/block/sda31/size').split());assert (start//8,size//8)==(d['partition_first'],d['partition_blocks'])
 for lba in d['guard_lbas']:assert root(serial,'dd if=/dev/block/sda bs=4096 skip='+str(lba)+' count=1 2>/dev/null')==GUARD
 assert root(serial,'dd if=/dev/block/sda bs=4096 skip='+str(d['log_lbas'][0])+' count=1 2>/dev/null')==bytes(BLOCK),'Log session has already been used; allocate a new file'
 return dict(verified=True,log_blocks=d['log_blocks'],guards_unchanged=True,first_slot_unused=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True);a=sub.add_parser('prepare');a.add_argument('--mib',type=int,choices=[2,4,8],default=8);a.add_argument('--resume-stage',type=Path);a=sub.add_parser('extract');a.add_argument('--report',type=Path,required=True);a.add_argument('--label',default='readback');a.add_argument('--kernel',type=Path,help='Decode persisted service snapshots with the matching frozen kernel');a=p.parse_args();serial=connected()
 assert b'uid=0' in root(serial,'id') and root(serial,'getprop sys.boot_completed').strip()==b'1'
 if a.action=='prepare':
  assert b'raphael,' not in root(serial,'ls /sys/firmware/devicetree/base/chosen/'),'Normal Android reboot required'
  stamp=a.resume_stage.name if a.resume_stage else dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'evidence/private/ufs-console-log'/stamp
  if not a.resume_stage:out.mkdir(parents=True,mode=0o700)
  else:assert out.resolve()==a.resume_stage.resolve() and not (out/'report.json').exists()
  print(out,flush=True)
  target='/data/unixnu-raphael-console-'+stamp+'/console.bin';
  if not a.resume_stage:root(serial,'umask 077; mkdir '+shlex.quote(str(Path(target).parent)))
  blocks=a.mib*1048576//BLOCK;raw=GUARD+bytes(blocks*BLOCK)+GUARD
  if not a.resume_stage:
   # Preallocate before streaming: F2FS otherwise split the final log block.
   root(serial,'umask 077; set -C; : > '+shlex.quote(target)+'; fallocate -l '+str(len(raw))+' '+shlex.quote(target))
   root(serial,'dd of='+shlex.quote(target)+' bs=4096 conv=notrunc 2>/dev/null',raw)
  root(serial,'sync; chmod 400 '+shlex.quote(target)+'; chattr +i '+shlex.quote(target))
  f=inspect(serial,target,out);assert f['policy_rc']==-61 and f['fiemap_rc']==f['flags_rc']==0 and f['inode_flags']&0x10 and not f['inode_flags']&0x800
  assert f['count']>0 and f['count']<=128
  start,size=map(int,root(serial,'cat /sys/class/block/sda31/start; cat /sys/class/block/sda31/size').split());assert start%8==size%8==0
  assert root(serial,'readlink -f /dev/block/bootdevice/by-name/userdata').strip()==b'/dev/block/sda31'
  geometry=root(serial,'readlink /sys/class/block/sda/device; cat /sys/class/block/sda/size; cat /sys/class/block/sda/queue/logical_block_size').decode().splitlines();assert geometry[0].endswith('/0:0:0:0') and int(geometry[-1])==4096
  ext=f['extents'];logical=0
  for e in ext:
   assert e['logical']==logical and e['physical']%BLOCK==e['length']%BLOCK==0 and e['flags'] in (0,1);logical+=e['length']
  assert logical==len(raw)
  def lba(offset):
   e=next(e for e in ext if e['logical']<=offset<e['logical']+e['length']);return start//8+(e['physical']+offset-e['logical'])//BLOCK
  guards=[lba(0),lba(len(raw)-BLOCK)]
  for x in guards:assert root(serial,'dd if=/dev/block/sda bs=4096 skip='+str(x)+' count=1 2>/dev/null')==GUARD
  assert root(serial,'dd if=/dev/block/sda bs=4096 skip='+str(lba(BLOCK))+' count=1 2>/dev/null')==bytes(BLOCK)
  d=dict(prepared=True,immutable=True,plaintext=True,source_file=target,fiemap=f,session=str(uuid.uuid4()),log_blocks=blocks,log_lbas=[lba((i+1)*BLOCK) for i in range(blocks)],guard_lbas=guards,lun_blocks=int(geometry[-2])//8,partition_first=start//8,partition_blocks=size//8,android_boot_id=root(serial,'cat /proc/sys/kernel/random/boot_id').decode().strip(),handset_log_verified=False)
  (out/'report.json').write_text(json.dumps(d,indent=2)+'\n');manifest(out/'report.json');print('Prepared',a.mib,'MiB;',len(ext),'physical extents;',blocks,'append slots',flush=True)
 else:
  d=manifest(a.report);out=a.report.parent/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.label);out.mkdir();raw=root(serial,'cat '+shlex.quote(d['source_file']));(out/'console.raw').write_bytes(raw);text,result=decode(raw,d);(out/'console.log').write_bytes(text)
  result['android_boot_changed']=root(serial,'cat /proc/sys/kernel/random/boot_id').decode().strip()!=d['android_boot_id']
  result['persistent_log_verified']=result['valid_records']>0 and result['android_boot_changed']
  result['continuous_log_verified']=result['persistent_log_verified'] and result['valid_records']>=2 and result['last_counter']>result['first_counter']
  result['console_lines']=len(text.splitlines())
  result['progress_lines']=sum(b'RPH tick=' in line for line in text.splitlines())
  if a.kernel:
   qualify_kernel(a.kernel,a.report)
   from ufs_service_snapshot import decode as decode_snapshot
   try:
    snapshot=decode_snapshot(text.decode(errors='replace'),a.kernel)
    (out/'service-snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    result['service_snapshot_captured']=snapshot['captured']
   except (AssertionError,ValueError,KeyError) as error:
    result['service_snapshot_captured']=False
    result['service_snapshot_decode_error']=type(error).__name__+': '+str(error)
  (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(out);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
