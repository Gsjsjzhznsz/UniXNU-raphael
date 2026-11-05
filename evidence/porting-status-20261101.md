> Historical 2026-11-01 snapshot. See README.md and development/docs/HANDOFF-20261101.zh-CN.md for the 2026-11-05 status. Later local runs reached launchd main and display-service frames, but no visible desktop.

# Sanitized local progress, 2026-11-01

This is a source-maintained summary of existing local runs, not a replacement for immutable, publicly accessible device logs. No complete commit captures the dirty device/SoC/workspace implementation. Consequently porting.toml uses implemented/planned levels, not formal host-verified/device-verified status. Local hardware results below remain real observations with that publication limit.

Successful handset run: workspace private `android-return-run/20261101T041841Z/report.json`, passed and experiment_passed true, native XNU execution confirmed. Frozen prelink `20261101T041703Z`, QEMU `20261101T041725.976494Z-verjeof8`, handset build `20261101T041809.698335Z-hktbyhsd`. Runtime-only: no new full boot-partition hash check.

- Original APFS root disk1s1 mounted; SystemOS stage6/status0, authorized1/mount_status0/readonly1/native_union1/root_recheck1.
- Original /sbin/launchd exec succeeded; PID1 EL0 issued 22 Unix syscalls. Last observed fcntl command97/F_ADDFILESIGS_RETURN was reading storage; errno16 followed deliberate terminal diagnostic read abort and is not an independent launchd failure.
- 2159 UFS requests, 30929920 bytes, zero hardware failures; one deliberate diagnostic abort. Immutable OS/SystemOS extents and signed per-block owner authentication. Apple root autherr80 remains; Apple seal/signature-chain success is not claimed.
- Single boot CPU, physical timer INTID18/19.2MHz; 1493 IRQs and 1493 EOIs, IPI0. No SMP qualification.
- Hardware watchdog20s with bounded60000ms pet budget, minimum500ms between pets; 25 pets. 100 nominal100ms polls measured13.1421009896s. Returned to Android in209.504s; normal reboot/root and transient-property cleanup passed.
- Original trust-cache61356 bytes/2554 entries, no owner cdhash insertion; no full Apple chain claim.
- Kernel124444672 bytes/15 segments; SHA256 1bfc48d52cbb7b57ed19191f6ff55fb615e292e6069dcb2953af8956b858746b. Diagnostic boot image SHA256 785fd511c8f8b1066705430bf6114255ed7d2fa189e494f15a8bfce01efa6c92.

There is no handset proof of dyld completion, launchd main, service readiness, SpringBoard, desktop, touch or GPU. Firmware GOP/pixel/input diagnostics and QEMU display/keystore tests are separate stages.

The later 500-poll candidate failed its QEMU gate (`20261101T042318.236406Z-trko7gz0`, AMFI No PMGR, returncode2,37 passing checks) and has not been built/run on the phone. A fixture lacking handset UFS is not evidence of a new phone failure. Its physical runtime must fit the existing bounded watchdog before any device trial.

Canonical sources after layout migration: board adapters and firmware in package/; shared CPU/watchdog/UFS in the selected SoC kits/Sm8150Platform. Historical reports retain original paths. See docs/REPOSITORY-COMPLIANCE.zh-CN.md for validation and outstanding publication requirements.
