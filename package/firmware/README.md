# Raphael UEFI bring-up

This directory contains new board bring-up code. Shared UEFI type definitions and
infrastructure come from pinned Mu Basecore and Mu-Silicium under `../sources`.
No existing raphael UEFI package or another board's platform configuration is used.

`RaphaelDiag.efi` is a diagnostic UEFI application, not a standalone firmware FD
or an Android boot image. It needs an already initialized UEFI system table.
It does not establish SEC, RAM ownership, MMU mappings, clocks, GOP or input drivers.
Those platform steps remain under development and must have their own evidence.

`RaphaelPkg/EntryProbe` is a new, position-independent Linux-entry instrument.
It has executed on this handset and returned evidence through a copied FDT to
the original Android kernel. It is not SEC or a complete UEFI implementation.
See `../docs/ENTRY-PROBE.zh-CN.md` for exact hashes and validation boundaries.

`RaphaelMemoryContractLib` builds with EDK II and rejects invalid interval plans.
`Resources/memory-plan.toml` remains explicitly disabled: passing interval checks
does not establish ownership or prove the larger firmware arena on hardware.

`RaphaelPkg/Diagnostic.dsc` and `Diagnostic.fdf` now build a standalone,
incomplete SEC/DXE diagnostic FD. Own SEC, exceptions, memory logging and return
DXE wrap pinned generic Basecore components. Handset testing is staged and
RAM-only. Source/host/structure/emulator/handset results, failed attempts and
recovery records are kept separately in `../docs/SEC-DXE.zh-CN.md`. It provides
no GOP, keys, BDS, complete architectural protocols, DarwinBoot or XNU support.
