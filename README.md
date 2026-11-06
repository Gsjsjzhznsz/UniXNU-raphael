# UniXNU-raphael

Independent [UniXNU](https://github.com/UniXNU/UniXNU) port for **Redmi K20 Pro / Xiaomi Mi 9T Pro (`raphael`, SM8150)**, paired with [UniXNU-sm8150-common](https://github.com/guowenye/UniXNU-sm8150-common).

## Current status - 2026-11-07

The physical raphael handset now reaches the original iPadOS 17.7.11 (21H461) Hello UI and, with the official temporary skip-setup preferences, the native date-and-clock lock screen. The user supplied a lock-screen photograph and confirmed that swiping had no effect. **The icon home screen and touch interaction are not yet verified.**

Continuous UFS logs confirm original SpringBoard entering its UI event loop. Automatic watchdog return and log recovery remain enabled. Current work adds an independent GT9889 touch provider: the pinned Xiaomi source identifies SE19 I2C address 0x5d and the Normandy frame protocol. Host-tested packet decoding is present; native bus/HID integration and physical interaction are pending. See [touch status](docs/TOUCH-DRIVER.zh-CN.md).

Historical raw logs, device data, vendor firmware, OS images and generated boot images remain private. Public notes describe implementation and local results; they do not upgrade the formal porting-record evidence level.

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

## License

Original port code is licensed under [BSD-2-Clause-Patent](LICENSE), matching the existing SPDX declarations and the upstream UniXNU device repositories. Existing per-file copyright and license notices remain applicable to their respective files; third-party dependencies retain their own licenses.
