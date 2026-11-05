#!/usr/bin/env python3
"""Temporary watchdog Image, with bounded USB recovery and boot-reason capture."""
import argparse,datetime as dt,json,subprocess,time
from pathlib import Path
from entry_probe import ROOT
ADB='/mnt/d/Android/platform-tools/adb.exe';FB='/mnt/d/Android/platform-tools/fastboot.exe'
def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--build',type=Path,required=True);a=p.parse_args();build=a.build.resolve();assert build.is_relative_to(ROOT/'evidence/private/watchdog-build')
 desc=json.loads((build/'report.json').read_text());assert desc['passed'] and desc['runtime_fdt_gated']
 out=ROOT/'evidence/private/watchdog-run'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False);print(out,flush=True)
 r=dict(passed=False,hardware_reset_verified=False,used_flash_or_erase=False,build=str(build.relative_to(ROOT)),commands=[])
 def save():(out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
 def call(tool,*args,timeout=8):
  cmd=[tool,'-s',a.serial,*args];start=time.monotonic()
  try:
   v=subprocess.run(cmd,capture_output=True,timeout=timeout);r['commands'].append(dict(command=cmd,returncode=v.returncode,stdout=v.stdout.decode(errors='replace'),stderr=v.stderr.decode(errors='replace'),seconds=time.monotonic()-start));save();return v
  except subprocess.TimeoutExpired:r['commands'].append(dict(command=cmd,timed_out=True));save();return None
 before=call(ADB,'exec-out',"su -c 'cat /proc/sys/kernel/random/boot_id'");assert before and before.returncode==0 and before.stdout.strip()
 r['before_boot_reason']=call(ADB,'shell','getprop ro.boot.bootreason').stdout.decode().strip()
 v=call(ADB,'reboot','bootloader');assert v and v.returncode==0
 v=call(FB,'getvar','unlocked',timeout=20);assert v and v.returncode==0 and b'unlocked: yes' in v.stderr
 path=str(build/'boot-watchdog.img')
 path=subprocess.check_output(['wslpath','-w',path],text=True).strip()
 start=time.monotonic();v=call(FB,'boot',path,timeout=50);r['fastboot_boot_accepted']=bool(v and v.returncode==0);save();assert r['fastboot_boot_accepted'];print('Temporary watchdog boot accepted',flush=True)
 deadline=time.monotonic()+110
 while time.monotonic()<deadline:
  v=call(ADB,'shell','getprop sys.boot_completed',timeout=2)
  if v and v.returncode==0 and v.stdout.strip()==b'1':break
  time.sleep(1)
 else:r['failure']='No automatic Android return within 110 seconds';save();raise SystemExit(1)
 r['wall_seconds_to_android']=time.monotonic()-start
 after=call(ADB,'exec-out',"su -c 'cat /proc/sys/kernel/random/boot_id'");r['new_android_boot_id']=bool(after and after.returncode==0 and after.stdout.strip()!=before.stdout.strip())
 r['after_boot_reason']=call(ADB,'shell','getprop ro.boot.bootreason').stdout.decode().strip()
 p=call(ADB,'exec-out',"su -c 'dmesg'");(out/'dmesg.txt').write_bytes(p.stdout if p else b'')
 r['root_verified']=b'uid=0' in call(ADB,'shell','su','-c','id').stdout
 # No CPU reset instruction exists in the hardware-only qualification Image.
 reason=r['after_boot_reason'].lower();r['hardware_reset_verified']=r['new_android_boot_id'] and (desc.get('no_cpu_reset_instruction',False) or ('watchdog' in reason or 'wdog' in reason or 'wdt' in reason))
 r['passed']=r['hardware_reset_verified'] and r['root_verified'];save();print(json.dumps({k:r[k] for k in ['passed','hardware_reset_verified','after_boot_reason','wall_seconds_to_android']},indent=2))
if __name__=='__main__':main()
