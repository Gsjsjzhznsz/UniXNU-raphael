# Raphael board package

The assembler exposes this directory as `tree/kits/raphael`.

- `drivers/`: board display and offline keystore adapters. These are emulator development providers; they do not establish phone display or secure keystore support.
- `firmware/RaphaelPkg/`: independent SEC/DXE diagnostic package, DSC/FDF, return bridge and board services.
- `firmware/Resources/`: observed memory contracts and disabled production inputs.

Kernel recipes live in `../scripts/build-raphael-*.py`. Display recipes consume this package through the assembled `kits/raphael` path. Firmware recipes are the workspace `scripts/build_sec_dxe.py` and `scripts/build_handset_sec_dxe.py`; they freeze sources before building with Mu Basecore. The workspace orchestrator is still required for diagnostic payload, storage ABI and hardware gates. `board.toml` intentionally has no production firmware recipe.

No Kit.toml driver entry is declared: these objects are statically linked, and the diagnostic firmware starts its services through its DSC/FDF. Adding a dynamic kit would require actual EFI outputs and a matching startup contract.

With the explicit UFS console profile, the original watchdogd selector2 text is persisted before panic in normal thread context. Log flushing is serialized with the observer; console and IRQ capture remain nonblocking.

The explicit 1800-second observer also streams full live-process snapshots at 600 and 1000 seconds, using separate early section names and the existing thread-reference bounds. These snapshots survive an original watchdogd panic before the final observer deadline. Original services and watchdog behavior remain in effect.


The explicit `RAPHAEL_KEYSTORE_SOURCE` candidate selects AppleKeyStoreState
`8c70daf814aafdf4a3d35e40dde0322655fd0a83` for software key wrapping. The normal
source pin remains unchanged. `RaphaelOfflineKeyStore.cpp` supplies the existing
16-byte private port-assigned ADT UUID; missing identity fails the operation.
This supports the unprotected ephemeral Data fixture and does not provide
hardware key protection or passcode operations. Handset effect remains pending.

The explicit896MiB development candidate uses a larger existing audited RAM interval and the same single-L1 recovery shape. High-PA QEMU passes39 checks; the896MiB handset contrast returned automatically with complete UFS logs, but still showed a progress bar and original service failures. It does not grant general RAM ownership.

`build_native_staging_handset.py --hardware-watchdog-return` explicitly selects reset after capture using the already qualified APSS watchdog. It requires the persistent UFS log input and watchdog qualification; the selected mode yields independent UFS evidence rather than a returned full FDT checkpoint. Real automatic Android recovery remains to be verified.

The1536MiB development grant uses exact multi-L1 recovery tables, retaining the original four-page wire representation for smaller grants. The new grant remains within an existing handset-audited interval. The actual firmware mapping and bootstrap matcher pass sanitizer and independent serializer checks; the full build and high-PA original-kernel recovery QEMU39 checks pass. The handset comparison returned automatically. Between600s and1000s, matched-name replacement instances fell from136 at896MiB to4; original BackBoard and LS survived. SpringBoard still waits for migration, all8 RGB samples show a loading bar, and the4096-slot log exhausted before final capture. No desktop is verified. Original XNU bootstrap and userspace services remain unchanged.

The service-thread observer stores optional IPC destination and special-reply send-once copyout identities in previously unused words106..127 of the existing128-word record. Diagnostic locks use try-locks and record contention. Consumers must confirm the saved PC is in the matching mach_msg2 stub before interpreting saved arguments; a copyout PID is not necessarily the service destination. Original fairplay/location exit reasons use the existing console queue. Original services are unchanged; this telemetry has host validation only.
