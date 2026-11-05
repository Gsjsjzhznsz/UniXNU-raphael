#!/usr/bin/env python3
"""Pin primary interfaces used by the synthetic read-only payload integration."""
import json,subprocess
from entry_probe import ROOT,sha
from source_pins import locked_revision

def main():
    specs={
      'sources/UniXNU':(locked_revision('UniXNU'),{
        'package/UniXNUPkg/Driver/UniXNURamDiskDxe/UniXNURamDiskDxe.c':['mEntryArgHobGuid','ReadOnly','EFI_WRITE_PROTECTED','UniXNURamDiskDxeEntry'],
        'package/UniXNUPkg/Library/UniXNULib/Main.c':['UniXNURun','UniXNUConfigLoad','UniXNUMenuRun'],
        'package/UniXNUPkg/Library/UniXNULib/Config.c':['TryVolume','UniXNUConfigLoad'],
        'package/UniXNUPkg/Library/UniXNULib/Volume.c':['UniXNUReadFile','EFI_FILE_MODE_READ'],
        'package/UniXNUPkg/Library/UniXNULib/Boot.c':['UniXNUBootEntry','LoadImage','StartImage']}),
      'sources/mu_basecore':('cfb93724a06ff86ff5ba971413368a7809ee42a5',{
        'EmbeddedPkg/Library/PrePiLib/FwVol.c':['FfsFindSectionData','FfsFindFileByName'],
        'MdePkg/Library/DxeHobLib/HobLib.c':['GetHobList','mHobList'],
        'MdeModulePkg/Universal/Disk/DiskIoDxe/DiskIo.c':['DiskIoDriverBindingStart','gEfiDiskIoProtocolGuid'],
        'FatPkg/EnhancedFatDxe/Fat.c':['FatDriverBindingStart','FatEntryPoint'],
        'FatPkg/EnhancedFatDxe/UnicodeCollation.c':['InitializeUnicodeCollationSupport','gEfiUnicodeCollation2ProtocolGuid']})}
    refs=[]
    for repo,(rev,files) in specs.items():
        root=ROOT/repo;actual=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip();assert actual==rev
        for path,markers in files.items():
            raw=subprocess.check_output(['git','-C',str(root),'show',rev+':'+path]);assert raw==(root/path).read_bytes(),path
            lines=raw.decode().splitlines();anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers};assert all(anchors.values()),(path,anchors)
            refs.append(dict(repository=repo,revision=rev,path=path,sha256=sha(raw),anchors=anchors))
    p=ROOT/'UniXNU-raphael/evidence/payload-source-audit.json'
    p.write_text(json.dumps(dict(passed=True,primary_sources=refs,private_modules_linked=False,
        design_budgets=dict(fat_bytes=1048576,synthetic_fdt_bytes=4096),
        scope='Own reserved FV synthetic read-only initrd; does not replace Android initrd or establish handset payload execution'),indent=2)+'\n');print(p)
if __name__=='__main__':main()
