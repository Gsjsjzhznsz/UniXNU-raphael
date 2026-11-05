# UniXNU-raphael

Independent [UniXNU](https://github.com/UniXNU/UniXNU) port for **Redmi K20 Pro / Xiaomi Mi 9T Pro (`raphael`, SM8150)**, paired with [UniXNU-sm8150-common](https://github.com/guowenye/UniXNU-sm8150-common).

## Current status — 2026-11-05

Local handset experiments have mounted original APFS/SystemOS, entered original launchd, used ephemeral writable Data, started SpringBoard and submitted display-service frames. The latest recovered 12-minute sample recorded 2,237 completed frames and no display transfer error; the user observed a loading bar followed by a black screen. SpringBoard still waits for LaunchServices database initialization. **A visible desktop and interaction have not been verified.**

The latest candidate adds a 30-minute observation contract and independent LaunchServices progress snapshots every 120 physical seconds. Kernel/payload build, 39 recovery-QEMU checks and boot-image structure checks passed. That candidate has **not** been booted on the handset. Public summaries are source-maintained notes; historical raw device logs remain private and do not establish formal public `device-verified` status.

## Repository layout

- `board.toml`, `feeds.toml`, `unixnu.lock`: format-2 device configuration and pinned sources.
- `porting.toml`: 13 structured porting areas and remaining work.
- `configs/`, `dts/`, `patches/`: selected profiles, board description and ordered patches.
- `package/`: board drivers and diagnostic firmware sources.
- `scripts/`: device build recipes and the standard packaging launcher.
- `development/`: preserved public host orchestration, tests, source/tool locks and project handoff.
- `evidence/`: source-maintained summaries; not the private artifact store.

Shared CPU/GIC/timer, watchdog and UFS operations live in the separately pinned SoC repository. Private dumps, vendor firmware, original OS images, owner keys and generated boot images are not included.

## Checkout and record check

```sh
git clone https://github.com/guowenye/UniXNU-raphael.git
git clone https://github.com/guowenye/UniXNU-sm8150-common.git
git clone https://github.com/UniXNU/UniXNU.git
cd UniXNU
python3 scripts/porting-record.py check --device ../UniXNU-raphael
```

For the existing native backend and its exact source pins, follow [development/README.md](development/README.md). The default `raphael_defconfig` remains compile-only. Complete production firmware/payload/bootimg recipes and a clean-checkout phone-image build remain incomplete; see [packaging](docs/PACKAGING.zh-CN.md). Remote CI checks the porting record, not phone readiness.

See [publication notes](docs/PUBLICATION.zh-CN.md), [current handoff](development/docs/HANDOFF-20261101.zh-CN.md), [hardware evidence](development/docs/HARDWARE.zh-CN.md), and the [porting record](porting.toml).

Official guides: [device repository](https://unixnu.com/zh/porting/device-repository), [SoC support](https://unixnu.com/zh/porting/soc-support), [records](https://unixnu.com/zh/porting/records), [bring-up](https://unixnu.com/zh/porting/bring-up), [log capture](https://unixnu.com/zh/porting/log-capture).
