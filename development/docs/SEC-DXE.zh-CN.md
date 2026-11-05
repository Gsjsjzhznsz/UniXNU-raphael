# 最小 SEC / DXE 诊断固件

日期：2026-10-27。当前代码是有意提前返回 Android 的诊断平台，尚不具备完整 UEFI 的硬件与架构协议。

## 实现边界

保留原 Android Image 的地址和内容，在其有效运行范围之后放置新 FD。只修改原 Image 第一条 B 和 image_size。FV reset branch 进入新编写的 SEC；它保存交接寄存器、设置自己的栈与异常向量，并验证实际 FDT、RAM、保留区、initrd、原内核和原 SP/LR 所在页。

FDT 副本带随机标记和整个扩展区的 memreserve。HOB 只允许专用 arena 参与 DXE 分配，其他扩展区均标保留。复用固定版本 Mu Basecore 的 PrePi、ArmMmuLib、DxeCore、RuntimeDxe；新诊断 DXE 校验 ST/BS 签名与 CRC、执行 AllocatePages→写→FreePages 并审计内存图。

日志、阶段、寄存器和内存图通过 FDT→原 Android 回传。退出汇编恢复原 Image 头和交接状态。仅 SEC 时不操作未曾改变的翻译寄存器、不清理整个扩展区；MMU 已开启时仅清理自己的扩展区并恢复寄存器。没有使用 Basecore 在该架构上会断言的整缓存占位 API。

未实现：GOP、显示、BDS、存储、实体按键、GIC/硬件中断、完整 Timer/CPU 架构协议、UniXNU 菜单、DarwinBoot 和 XNU。CpuExceptionHandlerLibNull 只保留本项目诊断向量，不能当成完整 UEFI 异常支持。

## 地址来源与预算

所有地址从本机已验证 Image base `0x80080000`、原 image_size `0x3612000`、64 KiB 向上对齐及下列显式设计预算推导。没有复用其他手机配置，也没有直接占用原厂 FD 或栈地址。

| 区域 | 起始 | 容量/来源 |
|---|---|---|
| bridge/context | 0x836a0000 | 64 KiB 设计预算 |
| 新 FD | 0x836b0000 | 3 MiB 设计预算 |
| SEC 栈 | 0x839b0000 | 256 KiB 设计预算 |
| DXE arena（包含页表） | 0x839f0000 | 16 MiB 设计预算 |
| FDT 副本 | 0x849f0000 | 1 MiB 输入 + 64 KiB 编辑空间 |
| 结束 | 0x84b00000 | 整体 Image size 为 0x4a80000 |

`memory-plan.toml` 的 `boot_enabled=false` 仍禁止生产固件配置。私有诊断镜像另行要求当前源文件哈希、对应阶段 QEMU、内存几何和扩大 Image 下载证据全部匹配，然后生成本次 PCD。

扩大 Image 已在本机下载并继续 Android，见 `extent-download.json`；其中 20283392 字节尾部只是零填充，没有由该探针写入/读回。这个结果不证明全部 arena 完整可用，也不解决原厂配置覆盖和隐藏所有权问题。

## 阶段门禁

| 构建参数 | 要求返回阶段 | 执行范围 |
|---|---:|---|
| `--stop-after-stage 2` | 2 | SEC、FDT 验证和复制；不建立 MMU/HOB |
| `--stop-after-stage 3` | 3 | 增加 HOB 与 MMU；不进入 DXE |
| `--stop-after-stage 4` | 6 | 进入通用 DXE 并执行本项目诊断驱动 |

手机构建脚本默认只生成阶段 2。阶段 3/4 构建现在要求所有先前阶段的手机证据通过，并且完整固件源码哈希与当前模拟器输入一致；源文件变化后需重新验证前置阶段。各阶段成功必须同时有本次 nonce、状态、Android/root 回传和 boot 分区哈希证明。

## 已保留的失败与恢复

| 实机尝试（UTC） | 目标 | 结果 |
|---|---|---|
| 20261027T142837Z | 完整诊断路径 | fastboot 接受，观察窗口未返回；用户报告黑屏，执行阶段未知 |
| 20261027T144555Z | 阶段 2 | fastboot 接受，观察窗口未返回；执行阶段未知 |

两次均未刷写。用户分别长按电源恢复 Android；144152Z、145249Z 的只读审核确认 Android/root 正常、boot 哈希未变、临时标记消失。恢复元数据单独关联原失败记录，不把失败改写为成功。

公开记录在 `UniXNU-raphael/evidence/sec-dxe-attempt-*.json` 与 `sec-dxe-recovery-*.json`；完整命令、原始 FDT、私有 boot 镜像仅保存在 `evidence/private/`。

## 大型 FDT 排查

新增 `replay_sec_fdt.py`，将本次采集的 FDT 结构送入 QEMU。QEMU 会修改 memory/chosen，UART 节点来自模拟器自己的 FDT；这不是手机硬件或所有权的完整重现。

QEMU 对外部 FDT 的填充使 totalsize 达到 0x14c488，超过手机当前 1 MiB 输入预算。因此仅本项模拟测试将复制预算设为 0x210000；手机预算保持 0x110000。源码按 PCD 容量减去 64 KiB 决定输入上限。

旧实现对每个节点调用 FdtParentOffset，libfdt 每次从根重扫。私有回放 20261027T145933Z 在 15 秒内没有结果；QMP 停机观测仍处于 stage 1 的 libfdt 遍历路径，无异常记录。新实现保留有界祖先栈，单次遍历获得父节点，避免反复扫描。

修正后同一份源 FDT 的回放 `20261027T150505Z` 用时约 0.228 秒，16 项通过。该对照隔离了遍历修正（两份回放均已使用收窄后的返回路径）。这是已确认的软件性能缺陷；是否导致此前手机黑屏仍须实机分段证据判断。

## 构建与结构检查

```sh
python3 scripts/build_sec_dxe.py --stop-after-stage 2
python3 scripts/build_sec_dxe.py --stop-after-stage 3
python3 scripts/build_sec_dxe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --fdt-copy-capacity 0x210000
python3 scripts/replay_sec_fdt.py --firmware-build artifacts/sec-dxe-qemu/20261027T150348Z \
  --fdt evidence/private/sec-dxe-run/20261027T144555Z/before.dtb
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z \
  --stop-after-stage 2
python3 scripts/run_sec_dxe.py --serial <local-device-serial> --build <private-build-directory>
python3 scripts/reboot_after_probe.py --serial <local-device-serial> --verify-only
```

`inspect_diagnostic_fd.py` 检查 FV/FFS 校验、全部段边界、PE 架构/入口/重定位、SEC XIP、reset branch、RuntimeDxe 64 KiB 对齐和 apriori 内容。RuntimeDxe 在此提供真正的 CRC 服务。

构建保存包内 22 个文件的源码快照与哈希，新构建从快照编译，避免实时目录变化影响输入。早期两份手机镜像的源码快照是后来按原报告重建并逐项核对，manifest 明确标明这一点。

模拟器完整路径还将诊断 DXE 的首条指令注入 `BRK #0x421`，检查异常记录和返回状态。这仅验证模拟器异常返回，不验证手机复位。各次构建命令、哈希、结构报告及执行结果分别保存，不把编译通过当作实机启动成功。

## 新增实机成功证据

- 20261027T151020Z：stage=2/status=0，EL1，MMU/cache 未开启，FDT copy=0x849f0000，52 字节 SEC 日志。nonce、Android/root 和原 boot 哈希均匹配。151244Z 正常重启清理通过。
- 20261027T151417Z：stage=3/status=0，MMU SCTLR=0xc0180d，页表根=0x849ef000，110 字节日志。nonce、Android/root 和原 boot 哈希均匹配。

- 20261027T151738Z：stage=6/status=0，ST/BS 签名与 CRC 正确，分配/写入/释放探针通过，内存图 720 字节/15 项，固件与主机独立检查的 arena 越界数均为 0；日志 2535 字节，丢弃 0。nonce、Android/root 和原 boot 哈希均匹配。
- 20261027T151911Z：正常重启回原 Android，root/boot 哈希正常，临时标记全部清除。

这证明本项目 SEC、FDT、HOB/MMU 和最小 DXE 分段路径已在本机执行。尚未证明完整 UEFI、GOP 或按键。硬件回传记录保存的是入口寄存器和启用后 MMU 状态；寄存器恢复的逐项检查目前来自 QEMU，硬件上确认了成功继续 Android。

HOB 的 TESTED 位目前用于允许诊断 DXE 分配，不是独立 RAM 测试结果。尚未逐区写入/读回整个 arena；完整固件必须进一步建立可验证的内存初始化和所有权策略。

## 后续

阶段 2/3/6 均已有实机证据，最后已正常重启并清理。日志路径稳定后，重新核实启动 framebuffer 与显示/电源/按键模块依赖，逐步接入 GOP、菜单和按键。

## 成功构建的精确版本和哈希

固件源码提交：`1009c7b7751b185ca6e5ac822c60711214df4381`。构建发生在提交前，随后对每份构建记录的 22 项固件包输入逐一读取该提交的 Git blob 并比较 SHA-256，全部匹配。该绑定不套用到两次早期失败镜像；它们保持自己的源码快照和原报告。完整绑定见 `sec-dxe-source-binding.json`。

所有手机 FD 均为 3145728 字节，私有 boot.img 均为 134217728 字节。

| 返回阶段 | 私有构建（UTC） | FD SHA-256 | 私有 boot SHA-256 |
|---:|---|---|---|
| 2 | 20261027T150738Z | `7b2e22f73bcf85be656b70f392bca7e1dbe7bc1bc95d8f4010fdf3575253a464` | `2f4405658ed601c1822aa073bdfed3f666c5f92986d669214e9e247ae2e07613` |
| 3 | 20261027T151245Z | `49d8911c8aaa0451955b325f6bff224c325b3f0eba4ef867b2443738228837a2` | `04cf3e224be289d137dbc88204ac3534c3faa369f2cd90d13d07a46f9234ee0a` |
| 6 | 20261027T151602Z | `d1e06a1cb88332c2a9e6643df800123e0bb657d5f5f03ddb604d03cb8da05491` | `8af2fb0ef3b063128678a091f441ed17fd924a57fd41cdc1066bb78c10d78833` |

| 模拟器目标 | 最新报告 | 结果 |
|---|---|---|
| SEC/FDT，1 MiB 输入预算 | artifacts/sec-dxe-qemu/20261027T150543Z/report.json | 16 项通过 |
| HOB/MMU | artifacts/sec-dxe-qemu/20261027T150505Z/report.json | 16 项通过 |
| 完整最小 DXE | artifacts/sec-dxe-qemu/20261027T150903Z/report.json | 正常 21 项、BRK 注入 18 项通过 |
| 大型本机 FDT 结构回放 | evidence/private/sec-fdt-replay/20261027T150505Z/report.json | 16 项通过，约 0.228 秒 |

最后正常重启清理结果见 `UniXNU-raphael/evidence/sec-dxe-cleanup.json`。原 boot 分区 SHA-256 始终与本次原始采集相同：`cbd91d814396ea0aab1cbca25d4f4f904805c69e4bb38b5a35a51b98858b96ec`。没有恢复备份，也没有将新 FD 写入分区。


## 后续只读显示扩展

新增 `--display-probe --stop-after-stage 2` 的默认禁用采样路径，已经完成主机、结构、模拟器、两轮本机返回和清理；详细证据见 `DISPLAY-PROBE.zh-CN.md`。本轮未重新验证修改后源码的stage3/6，原有成功不自动迁移。采样不是GOP，未写framebuffer。
