# 2026-10-28 上游更新

权威源码位于 `/home/guo/work/raphael-fresh/sources/UniXNU`。本轮重新执行 `git fetch origin`，核对远端 main/HEAD 后，以 `git merge --ff-only 40d21cc65171c3a24faa130a2a8e899f85790485` 更新干净的上游工作树。随后再次以 `git ls-remote origin HEAD refs/heads/main` 确认远端仍指向这一版本。

| 项目 | 准确版本 |
|---|---|
| 更新前 UniXNU | `0fc0fc1f9ddd0fbd4787738afef38667df5e0a95` |
| 更新后 UniXNU | `40d21cc65171c3a24faa130a2a8e899f85790485` |
| DarwinBoot（未变化） | `3325e352d7df68a9f9ad74832ed94a6acbbd7390` |
| mu_basecore（未变化） | `cfb93724a06ff86ff5ba971413368a7809ee42a5` |
| Mu-Silicium（未变化） | `4cba43c90e02cdbefbcd9fcdbda33d2328deaec0` |

新增 4 个提交，73 个文件变化。内容主要为设备记录刷新，以及通用移植日志指南加入 recovery/ADB 读取器、范围核对和手动循环要求，移除 sheng 专用站内日志页。新指南中的存储偏移和 PMIC 等参数仍须按本机来源独立确定；本轮没有创建日志分区或接入其他设备的配置。

逐 Git object 核对 `package`、`profiles`、`feeds.toml`、`components.toml`、`.gitmodules`、`patches`、`drivers`、`tests`、`unixnu`、`scripts/unixnu` 在新旧版本之间完全相同。因此不需要升级 Mu/Basecore、DarwinBoot、XNU 或 source-crypto 的固定依赖。`scripts/sync-devices.py` 的变化只涉及设备文档生成。

## 实现与保留

- `sources.lock.json` 已记录新 SHA、旧 SHA 和更新证据；7 个当前构建/审计脚本通过 `source_pins.py` 读取这份精确锁定版本，继续检查实际 checkout。历史回放校验器仍使用实测时的旧 SHA。
- 上游仓库保留 `refs/heads/raphael-baseline-20261028-0fc0fc1`；旧对象、历史镜像、源码快照和证据均保留。没有重写旧手机结果中的版本号。
- 当前 RAM 直接回调优化的 6 个未提交文件，与更新前保存的 binary patch 逐字一致。patch SHA256 为 `fe7be337b2e4cb23674aa1456f618940dd05e5fea70de0d07943b85d0a8c663f`。该优化仍需完整机器码审计和实机门禁。
- 修复普通 payload fixture 的旧路径错误：未选择 manager-ui 时，不再将不存在的 `snapshot/uefi-raphael` 加入 PACKAGES_PATH。首轮失败日志保留，修复后的重跑通过。

## 主机、结构与模拟器验证

| 命令 | 结果 |
|---|---|
| `python3 -m unittest discover -s tests/terminal -v`，在上游目录执行 | 运行 45 项，44 通过、1 跳过 |
| `python3 scripts/run_payload_fixture.py` | 编译及 QEMU/AAVMF 17 项通过，完整 UniXNURun 菜单截图已保存 |
| `python3 scripts/run_darwin_fixture.py` | ARM64 PE/重定位检查及 QEMU 拒绝/生命周期 38 项通过 |
| `python3 scripts/run_handoff_fixture.py --ramdisk-mode packed` | ARM64 PE/重定位检查及 QEMU 合成 Mach-O 正向交接 25 项通过 |
| `python3 scripts/build_sec_dxe.py` | FD 结构检查，QEMU 正常 47 项、BRK 恢复 44 项、UDF 恢复 44 项通过；RAM 写诊断默认关闭 |

4 份构建报告的 371 项归档输入分别核对快照 SHA256；其中 206 项上游输入与新版本/DarwinBoot 的准确 Git blob 一致。构建时根工作树含明确保留的未提交 RAM 优化，故源码绑定依靠归档快照及逐文件哈希，不能只用根 HEAD 代表全部输入。上游源码保持干净且未经修改。

主要产物 SHA256：

| 产物 | SHA256 |
|---|---|
| PayloadFixture.efi | `230d431abb9583a70cc7ad85b92f1b05883ccaacea4b066928bd301d611e0a4f` |
| DarwinFixture.efi | `9a9a01a67f9e167ae6fd894c8d1bec0c08ca33e23725184c685a7151b10b9445` |
| HandoffFixture.efi | `bb07bee9aa24dd5a216d3aaf890a2b6663d9d1a597f5e0b8bd5d02d210b67d8f` |
| 默认诊断 FD | `f18c9d588fa764b935ec9d666dc790913714650e583c87bbcc0433f5aa962474` |

完整提交列表、变更文件、命令、报告路径、输入计数、产物及日志哈希见 `../UniXNU-raphael/evidence/upstream-refresh-20261028.json`。本地完整日志在 `artifacts/upstream-refresh/20261028T133534Z`；历史目录未覆盖。

## 实机范围与下一步

本轮没有手机启动实验、分区写入或备份修改。此前手机菜单、按键、缓存 RAM 等结果仍属于各自记录的旧源码版本；模拟器合成接收器不等于手机 XNU 成功。

继续完成直接回调优化的机器码审计、完整 256 MiB 有界 QEMU 与恢复验证，再按单页到扩大窗口的实机门禁推进。完整 RAM 所有权、跨页别名、分配合同和手机 DarwinBoot/XNU 正向交接仍未完成。


## 23 点后的上游复核与候选分支（2026-10-28，Asia/Shanghai）

再次执行 `git fetch --prune origin`，并在全部主机检查后用 `git ls-remote` 重新核对。`main`/远端 HEAD 仍为 `40d21cc65171c3a24faa130a2a8e899f85790485`，当前移植的 `sources.lock.json` 与活动依赖保持原样。

本次实际新增的是 `feat/ipados27-gpu-parity` 分支的两个提交：`fb5cdd6e0660de5d6688696679972a1febb03abe` 与 `63cc454dd5999383b720ad8646d8d2b47762494a`。已将后者固定检出到独立源码目录 `/home/guo/work/raphael-fresh/sources/UniXNU-gpu-parity-63cc454`，其 19 个子模块全部按该提交的 gitlink 检出。该分支与 main 已分叉：main 独有 7 个提交，候选分支独有 28 个提交，不能直接快进替换活动版本。

候选分支包含 arm64e/iPadOS 26、27 配置、XNU 12377 补丁、目标架构构建、native-only 内核暂存与预链接发布调整，以及 9 个驱动/工具依赖更新。相对本次 fetch 前的候选分支，新增变化集中在 AdrenoMetal、bridge 构建和 Mac 主机检查脚本。它是候选源码，未纳入手机构建。具体差异列表和全部依赖 SHA 见 [机器可读记录](upstream-recheck-20261028.json)。

| 本次候选版本检查 | 实际结果 |
|---|---|
| 活动主仓库、候选主仓库及候选 19 个子模块 | 21 个仓库、2,490 个文件逐 Git blob/原始字节及执行位一致；工作树干净 |
| `python3 -m unittest discover -s scripts/unixnu -t scripts -v` | 10 项通过，涵盖 native-only 和预链接失败时保留原产物 |
| `python3 -m unittest discover -s tests/terminal -v` | 44 项通过、1 项跳过 |
| DarwinBoot `Test/test-kernel-parser.py` | 实际 C 编译与解析器检查通过 |
| DarwinBoot `Test/test-packed-ramdisk.py` | 实际 C 编译、稀疏恢复和 13 个拒绝样本通过 |
| XnuPrelink `python3 -m unittest discover -p 'test_*.py' -v` | 59 项通过 |
| 本分支相对 main 的 37 份 Python 变更 | 语法编译通过 |

总计 114 项 unittest，113 通过、1 跳过，另有两组实际 C 检查通过。以上是主机源码检查；没有为候选版本生成新固件、执行 QEMU 或手机启动。Mac Metal 主机脚本依赖 `xcrun`、Foundation/Metal/IOSurface 及 Vulkan loader，本轮 WSL 未执行，不能称为 GPU 验证。

本机暂不切换到候选分支的依据：

- arm64e 指南要求逐核验证 PAC、密钥寄存器和相关指令，本机尚无这组事实，保留当前 arm64 OS profile。
- 新 ArmCpu 仍处理定时器中断号 27；本机物理定时器已实测为 PPI 18，当前本机实现继续独立维护。
- 新 DarwinBoot 代码已加入 MH_FILESET 成员检查及 RootPolicies sidecar，README 的“fileset 不支持”描述与代码存在差异；本轮仅确认主机检查通过，未验证完整新 loader 的固件或手机交接。

原本机 UEFI/SoC/设备源码和所有历史证据保留。原备份未改动；本次未操作手机或分区。完整日志和逐文件清单位于 `artifacts/upstream-refresh/recheck-20261028T151458.572984Z`，公开记录仅含源码版本、哈希和验证结果。


## 2026-10-29：重新拉取到 9fe4855

本轮开始时远端 main/HEAD 仍为 `40d21cc65171c3a24faa130a2a8e899f85790485`。先 fetch 到 `feat/ipados27-gpu-parity` 的 `2c40ae9a7bf61325b298f36cd2379d8223a4ab00`；主机检查期间上游又推送了 `9fe4855117709d1a0119baefaa66180682dee52c`，因此再次 fetch 并将后者独立固定到 `/home/guo/work/raphael-fresh/sources/UniXNU-gpu-parity-9fe4855`。两个新快照和此前 `63cc454` 均保留。最后一次远端核对的准确 UTC 时间见 [机器记录](upstream-refresh-20261029.json) 的 `final_remote_check`。

19 个子模块全部按最新候选的 gitlink 初始化。相对 `63cc454` 新增两个主仓库提交，变化为：

| 来源 | 新版本或变化 |
|---|---|
| AdrenoMetal | `ded1122911337050bb6e71110d2a41b33607040c`；Core Image kernel library、绘制路径补丁、Metal 编译器路径探测及日志 |
| Adreno740 | `ab11d980d434a57ac4a4fd2749efc06f28f6dafa`；GPU 重启前终止挂起的 SMMU 故障，按故障任务的 VM 读取诊断缓冲区 |
| Turnip Darwin patch | 对已在同一 ring 提交的同步不再由 CPU 等待完成；尚未提交的同步等待其提交 |
| bridge 构建器 | 加入 `0024..0037` 共 14 份补丁，按记录顺序执行 |

最新候选、其 19 个子模块以及活动 main 共 21 仓库、2,504 个文件，原字节 Git blob 与执行位全部一致，工作树干净。latest 源码下重新执行 native/UDIF 10 项、terminal 45 项、XnuPrelink 59 项，共 113 通过、1 跳过；DarwinBoot 实际 C kernel parser 与 packed ramdisk 两组检查另行通过。bridge Python 语法检查通过。

从上游构建器读取其完整补丁列表，重新获取固定的 metal2vulkan `720ef1ce9ae2a2068999a8675717418b9416283e` Git tree，在独立 scratch index 中按顺序成功应用全部 37 份补丁并逐步记录 tree SHA；最终 tree 为 `092c2c77976ebd23add7cbb6db6aa8d7d370262b`。Turnip patch 的 Git hunk 结构检查通过。这仅证明精确来源与补丁序列可应用，不证明编译、并发语义或 GPU 运行。首次不带 filter 的参考源码 fetch 240 秒超时、partial clone 的普通 write-tree 60 秒超时均保留；最终以 blob filter 和 `write-tree --missing-ok` 避免下载未改动的大块输入，原候选源码未改写。

main 与最新候选为 7/30 提交分叉，活动 `sources.lock.json` 仍固定 main。Adreno740 的上游范围为 A740/SM8550；本机没有接入其寄存器、故障恢复序列或板级参数。ArmCpu 仍固定 timer ID27，本机已记录的物理 PPI18、逐核 PAC 未核实及新 DarwinBoot 手机交接缺口仍需独立处理。此轮没有编译候选固件、检查候选 FD、执行候选 QEMU/手机，也没有运行依赖 macOS 的 Metal 主机验证。

本机 UEFI/SoC/设备代码、Mu/Basecore 与当前内核依赖保持原样，原备份未改动。本轮只操作主机源码与记录，没有手机命令或分区写入。完整命令、子模块精确 SHA、文件/日志哈希与验证边界见 [upstream-refresh-20261029.json](upstream-refresh-20261029.json)，原日志位于 `artifacts/upstream-refresh/refresh-20261028T161148.466808Z`。继续原 SEC 跨页 RAM 诊断的备份存储和真实异常恢复接入，完整移植仍未完成。


## 远端及源码复核（2026-10-29 01:08:08 +08:00）

再次实际执行 `git fetch --prune origin` 和全分支 `git ls-remote --symref`。远端 main/HEAD 仍为 `40d21cc65171c3a24faa130a2a8e899f85790485`，最新候选 `feat/ipados27-gpu-parity` 仍为 `9fe4855117709d1a0119baefaa66180682dee52c`，与上一轮拉取后相同。候选已完整固定于 `sources/UniXNU-gpu-parity-9fe4855`，19 子模块精确匹配，独立重查 21 仓库、2,504 文件原字节 Git blob/执行位全部一致且工作树干净。

重新核对上一轮 11 份证据文件与 5 份实际测试日志的 SHA256，均匹配；同一源码的 113 通过/1 跳过、两组实际 C 检查及 37 份 bridge 补丁序列记录保留原时间，本次没有重复执行。main/候选仍为 7/30 提交分叉，活动 source lock 与 11 份本地 RAM alias 未提交文件逐字保留。只完成主机源码复核，未构建或启动候选固件，未操作手机或原备份。见 [本次复核记录](upstream-reconfirm-20261029.json)。


## 2026-10-31：用户明确要求的单次重拉

独立clone完成，远端main仍为f0721e9745c45ad2600cd69c74730f1cca55d56a，没有新main提交。候选feat/ipados27-gpu-parity从310fb75更新至6fd55dc1fab0b3ef28ee56df4d90f7d8df0981ed，新增5提交，隔离检出sources/UniXNU-gpu-parity-6fd55dc；GopFramebuffer b6e53e7、Adreno740 d9f0cc8、AdrenoMetal de38c6f已实际取得。变化集中于GPU/direct scanout完成等待、swap生命周期诊断、GMEM实验和CLI选择OS，未将sheng硬件参数或A740后端导入raphael。活动sources/UniXNU及其现有dirty子模块未改动，现有已冻结内核运行继续；main无需替换。机器记录见upstream-refresh-20261031.json与artifacts/upstream-refresh/explicit-20261030T163819Z。


## 2026-11-03：GPU/基带单次同步

main `3fa5ff5f409398c0555a9561d6437ce5d4c3b3b7` 与基带分支 `0ecc91f9c37ba931fe9b7f47cc44b71299e4100a` 已独立同步，41仓库/3544文件核对通过。基带组件 `6080e6a8ea22` 的通用桥归档通过，协议功能模型6/7；GPU更新仍针对A740，未替代本机A640后端。当前手机与打包pin保留。详见 [本次同步报告](UPSTREAM-20261103.zh-CN.md)及 `upstream-refresh-20261103.json`；主机检查与已知失败在报告中分别列出。


## 2026-11-05 用户明确授权的单次拉取

main350ddc2及20个gitlink子模块已独立取得，比11月3日候选新增43提交。QcomBaseband已进入main；GopFramebuffer仅trace事件名变化，未发现当前LS seeding直接修复。vendor_boot离线7项通过；活动pin及dirty源码保留，未将上游候选上手机。详见[本次报告](UPSTREAM-20261105.zh-CN.md)。
