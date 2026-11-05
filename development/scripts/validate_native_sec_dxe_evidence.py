#!/usr/bin/env python3
"""Independently bind own-UEFI native execution to frozen inputs and Git blobs."""
import argparse,datetime as dt,json,re,struct,subprocess,tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from inspect_diagnostic_fd import inspect_fd,PAYLOAD_GUID,PAYLOAD_PART1_GUID

def main():
 p=argparse.ArgumentParser();p.add_argument('--implementation',required=True);p.add_argument('reports',nargs='+',type=Path);a=p.parse_args()
 revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.implementation],text=True).strip()
 parent=ROOT/'artifacts/native-sec-dxe-verification';parent.mkdir(parents=True,exist_ok=True)
 out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=parent))
 checked=[]
 for path in a.reports:
  path=path.resolve();r=json.loads(path.read_text());base=path.parent;assert r['passed'] and not r['handset_executed'] and not r['full_xnu_boot_verified']
  b=r['build'];assert b['native_boot'] and b['native_qemu_gate'] and b['returncode']==0
  bindings=[]
  for item in b['source_inputs']:
   frozen=(base/'source-snapshot'/item['path']).read_bytes();assert sha(frozen)==item['sha256']
   original=subprocess.check_output(['git','-C',str(ROOT),'show',revision+':'+item['path']]);assert frozen==original,item['path']
   bindings.append(item)
  for key,repository,expected in [('upstream_inputs','sources/UniXNU',b['unixnu_revision']),('darwin_inputs','sources/UniXNU/drivers/DarwinBoot',b['darwin_revision'])]:
   for item in b[key]:
    frozen=(base/'source-snapshot'/item['path']).read_bytes();assert sha(frozen)==item['sha256']
    local=str(Path(item['path']).relative_to(repository));assert frozen==subprocess.check_output(['git','-C',str(ROOT/repository),'show',expected+':'+local])
  for name,filename in [('runner.py','scripts/run_native_sec_dxe_qemu.py'),('observer.py','scripts/fixtures/native_xnu_gdb.py')]:
   assert (base/name).read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',revision+':'+filename]),name
  kernel=(base/'native-kernel.macho').read_bytes();assert len(kernel)==r['kernel_bytes'] and sha(kernel)==r['kernel_sha256']
  fd=(base/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes();structure=inspect_fd(fd,r['layout']['FdBase']);assert sha(fd)==r['firmware_sha256']
  chunks=[]
  for guid in [PAYLOAD_GUID,PAYLOAD_PART1_GUID]:
   f=next(f for f in structure['files'] if f['guid']==guid);[s]=f['sections'];chunks.append(fd[s['offset']+4:s['offset']+s['bytes']])
  fat=b''.join(chunks);assert fat==(base/'diagnostic-payload.img').read_bytes() and sha(fat)==b['payload']['image_sha256'] and len(fat)==20*1024*1024
  extracted=subprocess.check_output(['mtype','-i',str(base/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho']);assert extracted==kernel
  adt=subprocess.check_output(['mtype','-i',str(base/'diagnostic-payload.img'),'::/EFI/UniXNU/kernel.macho.adt']);assert sha(adt)==b['payload']['adt_sha256']
  image=(base/'native-uefi.Image').read_bytes();assert sha(image)==r['image_sha256'];assert struct.unpack_from('<Q',image,16)[0]==len(image)
  offset=r['layout']['FdBase']-r['layout']['ImageBase'];assert image[offset:offset+len(fd)]==fd
  commands=json.loads((base/'commands.json').read_text());qemu=commands[0];assert '-kernel' in qemu and '-bios' not in qemu and '-drive' not in qemu and 'AAVMF' not in ' '.join(qemu)
  d=json.loads((base/'debugger-observation.json').read_text());assert d==r['debugger'] and d['exit_notice_count']==1 and d['native_instruction_executed'] and d['loaded_file_bytes_match'] and d['target_reached']
  source=d['kernel_file_buffer'];assert source['bytes']==len(kernel) and source['sha256']==sha(kernel) and source['file_bytes_match'] and source['free_called_after_load']
  arena=r['layout']['ArenaBase'];assert arena<=source['address'] and source['address']+len(kernel)<=arena+r['layout']['ArenaSize']
  loaded=d['observed_loader_layout'];window=r['kernel_window'];assert loaded['physical_base']==window['base']+(window['virtual_base']&0x1fffff) and loaded['window']==0x10000000
  assert not(source['address']<loaded['physical_base']+loaded['window'] and loaded['physical_base']<source['address']+len(kernel))
  for actual in d['loaded_segments']:
   segment=next(s for s in r['loader_layout']['segments'] if s['name']==actual['name']);data=kernel[segment['file_offset']:segment['file_offset']+segment['file_bytes']]
   assert actual['sha256']==sha(data) and actual['bytes']==len(data)
  initial=next(s for s in d['stops'] if s['label']=='native-entry');assert initial['pc']==loaded['entry'] and initial['x0']==loaded['args'] and initial['cpsr']&15==5 and initial['cpsr']&0x3c0==0x3c0 and initial['sctlr_el1']&0x1005==0
  text=(base/'serial.log').read_text();assert 'KERNEL_WINDOW lifecycle status=4 reserved=1 released=1 allocated=1 restored=1 error=0' in text and 'payload status=3 block/ro/write/fs=1/1/1/1' in text
  for item in r['evidence_files']:assert sha((base/item['path']).read_bytes())==item['sha256']
  if r['stop_at']=='timer_irq':
   cpu=d['cpu_state'];assert cpu['stage']==5 and cpu['registered']==1 and cpu['physical_timer']==1 and cpu['timer_irqs']>0 and cpu['eois']>=cpu['timer_irqs'] and cpu['pthread_status']==0 and cpu['pthread_functions']!=0
   assert d['source_crypto_post']['mode']==0 and d['source_crypto_post']['status']==0 and d['source_crypto_post']['returned']
  checked.append(dict(report=str(path.relative_to(ROOT)),report_sha256=sha(path.read_bytes()),stop_at=r['stop_at'],source_files=len(bindings),kernel_sha256=sha(kernel),firmware_sha256=sha(fd),image_sha256=sha(image),kernel_file_buffer=source,loader_layout=loaded,reached_symbols=d['reached_symbols'],cpu_state=d.get('cpu_state'),passed=True))
 result=dict(passed=True,implementation_revision=revision,artifact_directory=str(out.relative_to(ROOT)),executions=checked,handset_executed=False,full_xnu_boot_verified=False,limits=['Own SEC/DXE and original loader verified on QEMU only','No root volume, userspace or phone XNU claim'])
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');(ROOT/'UniXNU-raphael/evidence/native-sec-dxe-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(out);print('verified',len(checked),'own-UEFI native runs')
if __name__=='__main__':main()
