# Raphael board package

The assembler exposes this directory as `tree/kits/raphael`.

- `drivers/`: board display and offline keystore adapters. These are emulator development providers; they do not establish phone display or secure keystore support.
- `firmware/RaphaelPkg/`: independent SEC/DXE diagnostic package, DSC/FDF, return bridge and board services.
- `firmware/Resources/`: observed memory contracts and disabled production inputs.

Kernel recipes live in `../scripts/build-raphael-*.py`. Display recipes consume this package through the assembled `kits/raphael` path. Firmware recipes are the workspace `scripts/build_sec_dxe.py` and `scripts/build_handset_sec_dxe.py`; they freeze sources before building with Mu Basecore. The workspace orchestrator is still required for diagnostic payload, storage ABI and hardware gates. `board.toml` intentionally has no production firmware recipe.

No Kit.toml driver entry is declared: these objects are statically linked, and the diagnostic firmware starts its services through its DSC/FDF. Adding a dynamic kit would require actual EFI outputs and a matching startup contract.

With the explicit UFS console profile, the original watchdogd selector2 text is persisted before panic in normal thread context. Log flushing is serialized with the observer; console and IRQ capture remain nonblocking.
