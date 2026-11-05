#!/usr/bin/env python3
"""Independent validation of the physical-only UEFI timer service and restoration."""
import struct
FIELDS=['version', 'status', 'reason', 'gic_d', 'gic_d_bytes', 'gic_r', 'gic_r_bytes', 'rd_base', 'sgi_base', 'intid', 'flags', 'frequency', 'saved_dist', 'saved_igrpen', 'saved_ctl', 'saved_cval', 'saved_daif', 'saved_enable', 'saved_pending', 'saved_active', 'saved_vctl', 'saved_vcval', 'mapped_verified', 'cpu_protocol', 'irq_registered', 'hw_protocol', 'timer_protocol', 'period', 'irq_count', 'eoi_count', 'spurious', 'unexpected', 'source_masked', 'notify_count', 'first_counter', 'last_counter', 'start_counter', 'end_counter', 'relative_fired', 'relative_ticks', 'periodic_count', 'periodic_ticks', 'cancel_stable', 'cancel_ticks', 'timer_stopped', 'restore_ok', 'dist_after', 'igrpen_after', 'ctl_after', 'cval_after', 'enable_after', 'pending_after', 'active_after', 'daif_after', 'vctl_after', 'vcval_after']
def decode(raw,stage,gic,route,icc):
 assert len(raw)==len(FIELDS)*8
 r=dict(zip(FIELDS,struct.unpack('>'+str(len(FIELDS))+'Q',raw)))
 assert r['version']==1 and r['status']=={2:1,3:2,6:4}[stage] and r['reason']==0
 assert gic['passed'] and route['passed'] and icc['passed']
 assert r['gic_d']==gic['gicd'] and r['gic_r']==gic['gicr']
 assert r['rd_base']==gic['frames'][gic['boot_index']]['base'] and r['sgi_base']==r['rd_base']+0x10000
 assert r['gic_d_bytes']==gic['gicd_bytes'] and r['gic_r_bytes']==gic['gicr_bytes']
 assert r['intid']==route['intid'] and r['flags']==route['flags'] and r['frequency']==icc['cntfrq']
 assert r['saved_dist']==route['original_dist'] and r['saved_igrpen']==0
 assert r['saved_ctl']==icc['cntp_ctl'] and r['saved_cval']==icc['cntp_cval']
 assert r['saved_daif']==route['daif_before'] and r['saved_enable']==r['saved_active']==0
 assert r['saved_pending']==route['pending_before'] and r['saved_vctl']==icc['cntv_ctl'] and r['saved_vcval']==icc['cntv_cval']
 assert r['mapped_verified']==int(stage>=3)
 if stage<6:
  assert all(r[n]==0 for n in FIELDS[FIELDS.index('cpu_protocol'):])
 else:
  assert all(r[n]==1 for n in ['cpu_protocol','irq_registered','hw_protocol','timer_protocol','relative_fired','cancel_stable','timer_stopped','restore_ok','source_masked'])
  assert r['period']==0 and r['irq_count']==r['eoi_count'] and r['irq_count']>=20
  assert 0<r['notify_count']<=r['irq_count'] and r['spurious']==r['unexpected']==0
  freq=r['frequency']
  assert freq*8//100<=r['relative_ticks']<=freq and freq*8//100<=r['periodic_ticks']<=freq and r['periodic_count']>=5
  assert freq//10<=r['cancel_ticks']<=freq
  assert r['start_counter']<=r['first_counter']<=r['last_counter']<=r['end_counter']<r['start_counter']+freq*10
  for a,b in [('dist','dist'),('igrpen','igrpen'),('cval','cval'),('enable','enable'),('active','active'),('daif','daif'),('vcval','vcval')]:
   assert r[a+'_after']==r['saved_'+b]
  assert (r['ctl_after']^r['saved_ctl'])&3==0 and (r['vctl_after']^r['saved_vctl'])&3==0
  assert (r['pending_after']^r['saved_pending'])&(1<<r['intid'])==0
 return dict(**r,passed=True,physical_only_timer_arch_verified=stage==6,relative_periodic_cancel_verified=stage==6,full_unixnu_verified=False)

def verify_result_storage(build):
 import json,re
 from inspect_diagnostic_fd import SEC_GUID
 fd=json.loads((build/'fd-inspection.json').read_text());assert fd['passed']
 sec=next(f for f in fd['files'] if f['guid']==SEC_GUID);section=next(s for s in sec['sections'] if 'pe' in s);pe=section['pe']
 mp=build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Sec/Sec/OUTPUT/RaphaelSec.dll.map'
 m=re.search(r'(?m)^([0-9a-f]+)\s+[0-9a-f]+\s+\d+\s+mPhysicalTimer\s*$',mp.read_text());assert m
 rva=int(m[1],16);size=len(FIELDS)*8+64;data=next(s for s in pe['sections'] if s['name']=='.data')
 assert data['rva']<=rva and rva+size<=data['rva']+data['virtual_bytes'] and data['rva']==data['raw_offset'] and data['bytes']>=data['virtual_bytes']
 raw=(build/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/FV/RAPHAELDIAG.fd').read_bytes();offset=section['offset']+4+rva
 assert offset+size<=section['offset']+section['bytes'] and raw[offset:offset+size]==bytes(size)
 return dict(bytes=size,rva=rva,physical_address=pe['image_base']+rva,fd_offset=offset,materialized_zero_data=True)
