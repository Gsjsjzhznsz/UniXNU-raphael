#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Decode bounded read-only UFS HCI handoff; no ownership or DMA inference."""
import struct
from inspect_device import read_fdt,registers,physical,node_path
OFFSETS=[0,8,0x18,0x20,0x24,0x30,0x34,0x38,0x3c,0x40,0x44,0x48,0x50,0x54,0x58,0x60,0x78,0x80]
NAMES=['CAP','VER','AHIT','IS','IE','HCS','HCE','UECPA','UECDL','UECN','UECT','UECDME','UTRLBA','UTRLBAU','UTRLDBR','UTRLRSR','UTMRLDBR','UTMRLRSR']
def decode_observation(raw,nonce_matched,decoder,*args):
 # Volatile FDT records can be absent after reset. Absence is unknown execution,
 # never a command failure or permission to interpret another boot's records.
 if not nonce_matched or not raw:
  return dict(passed=False,observed=False,execution_unknown=True,
              reason='nonce mismatch' if not nonce_matched else 'record absent')
 try:
  decoded=decoder(raw,*args)
  return dict(decoded,observed=True)
 except (AssertionError,ValueError,KeyError,struct.error) as error:
  return dict(passed=False,observed=True,execution_unknown=True,
              decode_error=type(error).__name__+': '+str(error))

def resources(blob):
 root=read_fdt(blob)
 assert 'qcom,sm8150' in root.strings('compatible')
 hosts=[n for n in root.walk() if b'qcom,ufshc' in n.properties.get('compatible',b'').split(b'\0')]
 assert len(hosts)==1
 host=hosts[0];assert host.strings('reg-names')[0]=='ufs_mem'
 base,size=registers(host)[0];base=physical(host.parent,base,size)
 return dict(node=node_path(host),base=base,bytes=size)
def decode(raw,blob):
 assert len(raw)==59*8,'UFS snapshot wire length'
 w=struct.unpack('>59Q',raw);assert w[0:3]==(1,3,36)
 res=resources(blob);assert w[3:5]==(res['base'],res['bytes']) and list(w[5:23])==OFFSETS
 first=w[23:41];second=w[41:59];assert all(0<=v<1<<32 for v in first+second)
 snapshots=[dict(zip(NAMES,v)) for v in (first,second)]
 a=snapshots[-1]
 return dict(passed=True,resources=res,snapshots=snapshots,changed=[name for name,x,y in zip(NAMES,first,second) if x!=y],controller_enabled=bool(a['HCE']&1),device_present=bool(a['HCS']&1),transfer_list_ready=bool(a['HCS']&8),outstanding_transfer_mask=a['UTRLDBR'],outstanding_task_mask=a['UTMRLDBR'],dma_address_bits=64 if a['CAP']&(1<<24) else 32,transfer_slots=(a['CAP']&31)+1,native_dma_verified=False,exclusive_ownership_verified=False,scope='ABL to Image entry read-only state only; no controller writes or storage commands')

def decode_read(raw,reference,geometry):
 assert len(raw)==32*8+40+4096,'UFS read probe wire size'
 w=struct.unpack('>32Q',raw[:256]);assert w[0] in (1,2,3,4,5,6)
 lba=w[29]>>8 if w[0] in (2,6) else 0;assert lba==geometry.get('lba',0), 'Requested read address mismatch'
 block=raw[296:];inquiry_data=raw[256:292]
 stage=w[1];takeover=stage>=5;inquiry=stage>=6;tur=inquiry and w[13]==0;capacity=tur and w[14]==0;read=stage>=7 and (w[0]>=3 or not w[30])
 query_only=w[0]<3 and w[30]==1
 checks=dict(all_stages_completed=stage==(6 if query_only else 7),watchdog_armed=w[6]==1,smmu_no_active_translation_gate=w[8]==1,all_secondary_cpus_off=w[24:26]==(8,7),takeover_ok=w[12]==0 if takeover else None,inquiry_ok=w[13]==0 if inquiry else None,tur_ok=w[14]==0 if tur else None,capacity_ok=w[15]==0 if capacity else None,capacity_matches_android=w[16]==geometry['blocks'] and w[17]==geometry['logical_bytes'] if capacity else None,read_ok=w[18]==0 if read else None,ocs_ok=w[19]==0 if inquiry else None,controller_restored=w[20]==0 and w[31]==0 if takeover and w[12]==0 else None,dma_released=w[21]==0 if takeover else None,watchdog_restored=w[22]==1,known_block_matches=block==reference if read else None)

 if 3<=w[0]<=5:
  checks['all_repetitions_verified']=w[30]==(geometry['payload_blocks'] if w[0]>=4 else geometry['extent_repeats'])
  if w[0]>=4:checks['full_payload_blocks_sha256_verified']=w[18]==0 and w[30]==geometry['payload_blocks']
  checks['physical_read_count_verified']=w[29]>>8==geometry['extent_physical_reads']
 if w[0]==6:
  assert w[30] in (0,1,3,7,15,31,63),'Invalid write-probe stage progression'
  checks.update(write_policy_preimage_verified=bool(w[30]&2),write_completed=bool(w[30]&8),synchronous_cache_completed=bool(w[30]&16),write_readback_verified=bool(w[30]&32))
 required=[v for k,v in checks.items() if not query_only or k not in ('read_ok','known_block_matches')]
 return dict(passed=all(required),probe_goal='bounded_single_block_write' if w[0]==6 else 'verified_boot_payload' if w[0]>=4 else 'extent_virtual_disk' if w[0]==3 else 'queries_only' if query_only else 'known_block',checks=checks,words=w,inquiry=inquiry_data.hex(),native_dma_verified=bool(checks['inquiry_ok'] and checks['capacity_ok'] and checks['capacity_matches_android']),native_block_read_verified=bool(checks['read_ok'] and checks['known_block_matches']),recovery_mode={0:'inherited_register_restore',1:'exception_before_dma',2:'transport_poison_hci_reset',3:'exception_hci_reset'}.get(w[31],'unknown'),read_cdb=(w[29]&255 if w[0]>=2 else w[29]) or 16,read_lba=lba,last_completion=dict(response=(w[28]>>32)&255,status=(w[28]>>24)&255,sense_key=(w[28]>>16)&255,asc=(w[28]>>8)&255,ascq=w[28]&255) if w[29] else None,media_written=bool(w[0]==6 and w[30]&8),media_write_attempted=bool(w[0]==6 and w[30]&4),media_may_have_changed=bool(w[0]==6 and w[30]&4),write_completed=bool(w[0]==6 and w[30]&8),write_stages=w[30] if w[0]==6 else None,persistence_after_reboot_verified=False,scope='One explicitly allocated diagnostic block preimage/write/FUA/flush/readback; persistence requires Android readback after normal reboot' if w[0]==6 else 'Complete boot FAT streamed through owned UFS DMA; every block SHA256 checked against frozen firmware references; no XNU execution or filesystem mount' if w[0]>=4 else 'Repeated virtual-sector reads of an immutable file via owned UFS DMA; no filesystem mount' if w[0]==3 else 'One read-only LUN0 block at the declared address; no root volume or persistent writes')
