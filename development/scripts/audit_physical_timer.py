#!/usr/bin/env python3
"""Review pinned primary interfaces and inspect the independently built driver."""
import argparse,json,re,subprocess
from pathlib import Path
from entry_probe import ROOT,sha
from physical_timer import verify_result_storage
REV='cfb93724a06ff86ff5ba971413368a7809ee42a5'
def main():
 p=argparse.ArgumentParser();p.add_argument('--qemu-report',required=True,type=Path);a=p.parse_args();qp=a.qemu_report.resolve();q=json.loads(qp.read_text())
 assert q['qemu_passed'] and q['physical_timer_arch'] and q['stop_stage']==4
 for i in q['source_inputs']:assert sha((ROOT/i['path']).read_bytes())==i['sha256']
 core=ROOT/'sources/mu_basecore';sources=[]
 specs={
 'ArmPkg/Drivers/CpuDxe/CpuDxe.c':['HardwareInterruptProtocolNotify','mCpu.EnableInterrupt   = CpuEnableInterrupt','gHardwareInterruptProtocolGuid','CpuRegisterInterruptHandler'],
 'ArmPkg/Drivers/CpuDxe/Exception.c':['ArmEnableAsynchronousAbort','DEBUG_CODE','RegisterCpuInterruptHandler'],
 'ArmPkg/Drivers/ArmGicDxe/ArmGicCommonDxe.c':['return This->EnableInterruptSource (This, Source)','ARM_ARCH_EXCEPTION_IRQ'],
 'MdeModulePkg/Core/Dxe/Event/Timer.c':['CoreTimerTick','TimerPeriodic','TimerRelative'],
 'MdePkg/Include/Protocol/Timer.h':['EFI_TIMER_REGISTER_HANDLER','EFI_TIMER_SET_TIMER_PERIOD','EFI_TIMER_GET_TIMER_PERIOD','EFI_TIMER_GENERATE_SOFT_INTERRUPT'],
 'EmbeddedPkg/Include/Protocol/HardwareInterrupt.h':['RegisterInterruptSource','EnableInterruptSource','EndOfInterrupt'],
 'UefiCpuPkg/Library/CpuExceptionHandlerLib/AArch64/ExceptionSupport.S':['SPSR','CommonCExceptionHandler'],
 'MdePkg/Library/ArmLib/AArch64/ArmLibSupportV8.S':['DAIF_WR_IRQ_BIT','ArmEnableInterrupts','ArmDisableInterrupts'],
 }
 for name,markers in specs.items():
  raw=subprocess.check_output(['git','-C',str(core),'show',REV+':'+name]);assert raw==(core/name).read_bytes()
  lines=raw.decode().splitlines();anchors={m:[n+1 for n,x in enumerate(lines) if m in x] for m in markers};assert all(anchors.values()),(name,anchors)
  sources.append(dict(repository='sources/mu_basecore',revision=REV,path=name,sha256=sha(raw),anchors=anchors))
 src=ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/PhysicalTimerDxe/PhysicalTimer.c';text=src.read_text()
 # Review optimized C MSR sites, including unknown-ID cleanup. The ArmLib
 # assembly object also contains unused virtual timer APIs; these are not called.
 obj=qp.parent/'Build/RaphaelDiagnostic/DEBUG_CLANGPDB/AARCH64/RaphaelPkg/Drivers/PhysicalTimerDxe/PhysicalTimerDxe/DEBUG/RaphaelPhysicalTimerDxe.dll'
 full_dis=subprocess.check_output(['llvm-objdump','-d',str(obj)],text=True)
 mp=obj.parent.parent/'OUTPUT/RaphaelPhysicalTimerDxe.map'
 spans=[(int(m[1],16),int(m[2],16)) for m in re.finditer(r'(?m)^([0-9a-f]+) ([0-9a-f]+)\s+\d+.*dll\.lto\.obj:\(\.text\)\s*$',mp.read_text()) if int(m[2],16)]
 assert spans
 dis='\n'.join(line for line in full_dis.splitlines() if (m:=re.match(r'\s*([0-9a-f]+):',line)) and any(a<=int(m[1],16)<a+n for a,n in spans))
 allowed={'ArmReadCntPct','ArmWriteCntpCtl','ArmInstructionSynchronizationBarrier','ArmReadCntpCtl','ArmWriteCntpCval','ArmReadCntpCval','ArmDisableInterrupts'}
 assert set(re.findall(r'\b(Arm[A-Za-z0-9]+)\s*\(',text))<=allowed

 assert 'ICC_IAR1_EL1' in dis and 'ICC_EOIR1_EL1' in dis and 'ICC_IGRPEN1_EL1' in dis
 for reg in ['CNTV_CTL_EL0','CNTV_CVAL_EL0','ICC_PMR_EL1','ICC_BPR1_EL1','ICC_CTLR_EL1','ICC_DIR_EL1']:
  assert not any('msr' in line and reg in line for line in dis.splitlines()),reg
 assert 'ArmGic' not in text and 'PcdArmArchTimer' not in text and 'PcdGic' not in text
 assert 'Source!=mR->Intid' in text and 'mLimit' in text and 'N<1000000' in text
 assert text.index('MaskSource();\n  mR->SourceMasked')<text.index('SourceEoi(&mInterrupt,Source)')
 paths=[src,src.with_name('PhysicalTimerDxe.inf'),ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Include/RaphaelPhysicalTimer.h',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Sec/Sec.c',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/DiagnosticReturnDxe/PhysicalTimerTest.c',ROOT/'UniXNU-raphael/package/firmware/RaphaelPkg/Library/RaphaelDiagnosticDebugLib/Debug.c']
 report=dict(passed=True,qemu_report=str(qp.relative_to(ROOT)),qemu_report_sha256=sha(qp.read_bytes()),primary_sources=sources,
  source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in paths],decoder_sha256=sha((ROOT/'scripts/physical_timer.py').read_bytes()),compiled_object_sha256=sha(obj.read_bytes()),reviewed_lto_code_spans=spans,arm_library_calls=sorted(allowed),result_storage=verify_result_storage(qp.parent),
  physical_ppi_only=True,generic_cpu_and_vectors_unmodified=True,other_timer_sources_never_written=True,eoi_mode_zero_only=True,source_masked_before_eoi=True,independent_counter_and_poll_bounds=True,
  protocol_negative_requests_checked_in_qemu=True,period_change_and_stopped_irq_stability_checked_in_qemu=True,handset_executed=False,
  limitations=['Diagnostic service lifetime at most ten seconds; not permanent TimerArch','Only one FDT-resolved physical PPI supported','NS enable views are non-atomic and do not establish Secure ownership','A full OS memory handoff is not implemented'])
 (ROOT/'UniXNU-raphael/evidence/physical-timer-source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('pinned CPU/vector/event protocols, physical-only writes, source-before-EOI, storage reviewed')
if __name__=='__main__':main()
