#!/usr/bin/env python3
"""Audit primary generic architecture/event sources at the pinned Mu commit."""
import json
import subprocess
from entry_probe import ROOT, sha

REVISION='cfb93724a06ff86ff5ba971413368a7809ee42a5'
SPECS={
 'ArmPkg/Drivers/CpuDxe/CpuDxe.c':['InitializeExceptions ();','HardwareInterruptProtocolNotify','ArmEnableInterrupts ();','gEfiCpuArchProtocolGuid'],
 'ArmPkg/Drivers/CpuDxe/Exception.c':['InitializeCpuExceptionHandlers'],
 'ArmPkg/Drivers/ArmGicDxe/GicV3/ArmGicV3Dxe.c':['GicGetCpuRedistributorBase','PcdGicRedistributorsBase','ArmGicV3EnableInterruptInterface','GicCommonInstallAndRegisterInterruptService'],
 'ArmPkg/Drivers/TimerDxe/TimerDxe.c':['TimerInterruptHandler','mTimerNotifyFunction','TimerDriverSetTimerPeriod','TimerVirtIntrNum','TimerSecIntrNum','TimerIntrNum'],
 'ArmPkg/Library/ArmGenericTimerPhyCounterLib/ArmGenericTimerPhyCounterLib.c':['ArmReadCntPct','ArmWriteCntpCval','ArmWriteCntpCtl'],
 'MdeModulePkg/Core/Dxe/Event/Timer.c':['CoreSetTimer','CoreTimerTick','TimerPeriodic','TimerRelative'],
 'UefiCpuPkg/Library/CpuExceptionHandlerLib/DxeCpuExceptionHandlerLib.inf':['MODULE_TYPE','AArch64'],
}


def main():
 core=ROOT/'sources/mu_basecore';sources=[]
 assert subprocess.check_output(['git','-C',str(core),'rev-parse','HEAD'],text=True).strip()==REVISION
 for name,markers in SPECS.items():
  raw=subprocess.check_output(['git','-C',str(core),'show',REVISION+':'+name]);assert raw==(core/name).read_bytes()
  lines=raw.decode().splitlines();anchors={m:[i+1 for i,line in enumerate(lines) if m in line] for m in markers}
  assert all(anchors.values()),(name,anchors)
  sources.append(dict(repository='sources/mu_basecore',revision=REVISION,path=name,sha256=sha(raw),anchors=anchors))
 out=ROOT/'UniXNU-raphael/evidence/qemu-arch-source-audit.json'
 out.write_text(json.dumps(dict(passed=True,primary_sources=sources,upstream_modified=False,
   scope='Generic CPU/GICv3/CNTP TimerArch and DXE events; all resource values come from this QEMU DTB',
   handset_parameters_used=False,handset_gic_restore_verified=False),indent=2)+'\n');print(out)

if __name__=='__main__':main()
