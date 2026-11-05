# ARM64 入口探针记录

日期：2026-10-27。该探针已在本机执行；它不是完整 UEFI、SEC 或 DXE。

## 目的与实现

先获得 ABL 实际交接证据，避免把原厂默认配置、Android boot header 的 legacy 地址或其他设备配置当作新固件内存布局。

`uefi-raphael/RaphaelPkg/EntryProbe/` 是本次新编写的位置无关 AArch64/C 代码。它只接受本机当前 Image 的直接 B 入口形式，在原 Image 的有效运行范围之后追加自己的代码、16 KiB 栈和 FDT 缓冲区。Image 的 `code0` 和 `image_size` 临时改变；探针正常执行时恢复这两项，并直接转入原 B 的目标，原内核不搬迁。

栈和 FDT 缓冲区来自扩展后的下载 Image，没有使用固定物理地址。FDT 操作复用固定版本的上游 libfdt，不改变原 FDT，只在副本 `/chosen` 中加入版本、随机测试标记和寄存器记录，同时添加本探针存储区的 memreserve。未满足 EL1/EL2、MMU 关闭和 D-cache 关闭条件时直接绕过诊断，继续原入口。

当前手机内核、ramdisk、四份追加 DTB 都来自本次重新采集。打包时逐项比对其字节和哈希，保留原 Android header v1 的接口参数，更新大小和 SHA1；不沿用失效的 AVB footer。镜像包含私有输入，仅保存在 `evidence/private/`，不公开分发。

## 证据与来源

- 本机 ABL 提取出 LinuxLoader：PE SHA-256 `f34c4d72af117b37023dd12f9497bf301a443a29ce48650ed780ed9de610a8d5`。来源、FFS 哈希见 `../UniXNU-raphael/evidence/abl-module-metadata.json`。
- 新获取的 Qualcomm LinuxLoader 接口源码镜像：`arter97/android_bootable_bootloader_edk2`，提交 `fd752ab1b6d81ffaec0a9e86ed2b74e7eac9f4fe`。只阅读通用 BootLib 和协议定义，未使用其板级配置。该第三方镜像不是本机 ABL 的准确源码匹配，不能充当本机地址的权威来源。
- ARM64 启动协议：本次固定的 MiCode 提交中的 `Documentation/arm64/booting.txt`。
- libfdt：Mu Basecore 子模块固定提交 `cfff805481bdea27f900c32698171286542b8d3c`。
- 文件哈希、接口源码行号、原 ABL 中的公开接口标识偏移见 `../UniXNU-raphael/evidence/handoff-source-references.json`。标识匹配不等于完整二进制源码等价或控制流实测。

## 主机与模拟器

```sh
python3 scripts/validate_entry_probe.py
python3 scripts/build_entry_probe.py --collection evidence/private/device/20261027T120325Z
```

使用 AArch64 GCC 13 / GNU binutils，以 freestanding 方式编译，禁止浮点/SIMD 和未初始化存储依赖。链接器要求 `.bss`、`.got` 为空；ELF 不含待处理重定位。

模拟器证据：`artifacts/entry-probe-qemu/20261027T131009Z/report.json`。QEMU 的 EL1、EL2 两种入口各通过 14 项检查，包括 FDT 交接、原启动参数、入口指令与 Image 大小恢复、原内核地址、memreserve 和计数器。接收测试内核仅用于模拟器，串口地址从 QEMU 自己的 FDT 读取。

加入编译输入与工具哈希记录后再次构建/运行，`artifacts/entry-probe-qemu/20261027T132950Z/report.json` 的两种入口仍通过，模拟器 Image SHA-256 保持 `b17715b8693a30f2957e9c9175c0e446bc5cc99101de27008fb23ac1638fd241`。

初次模拟器测试暴露 FDT padding 容量与绝对 GOT 寻址问题；修正后通过。接收测试内核改用显式启用的 semihosting 退出，避免把尚未配置的 PSCI 退出当作探针失败。失败构建和 trace 已保留于本地 artifacts，未据此进行手机试验。

本机使用的探针 ELF/bin 和镜像位于 `evidence/private/entry-probe-build/20261027T131025Z/`。完整编译命令见其中 `commands.json`。

| 产物 | 字节数 | SHA-256 |
|---|---:|---|
| 本机 EntryProbe.bin | 1081344 | `4a06127d6c0d76ce69ca0d7a9390bba95bdf158313e2bf47782e04e75c42c2c8` |
| 私有临时 boot-entry-probe.img | 134217728 | `412f868c355d0091caa02a769cc78d58e2c3e2ede7bfb6036008612d99683bcd` |

## 实机执行

```sh
python3 scripts/run_entry_probe.py --serial <local-device-serial> \
  --build evidence/private/entry-probe-build/20261027T131025Z
```

私有日志：`evidence/private/entry-probe-run/20261027T131225Z/`。公开技术元数据：`../UniXNU-raphael/evidence/entry-handoff.json`。

结果：fastboot 接受非持久下载启动，Android 完成启动，FDT 测试标记匹配本次镜像，root 正常，boot 分区哈希与源镜像相同。没有执行 flash、erase、format 或分区修改。原备份未访问或改动。

随后执行 `python3 scripts/reboot_after_probe.py --serial <local-device-serial>`，正常重启回原 boot 分区。`evidence/private/entry-probe-cleanup/20261027T133114Z/report.json` 确认 Android/root 正常、boot 哈希未变、临时探针属性消失。手机当前已回到无探针的 Android 基线。

| 实测字段 | 值 | 含义/边界 |
|---|---|---|
| CurrentEL | 0x4 | EL1 入口 |
| SCTLR_EL1 | 0xc00808 | M/C/I 均为 0；MMU、D-cache、I-cache 关闭 |
| DAIF | 0x1c0 | A/I/F 屏蔽，D 未置位；新 SEC 仍应明确设置异常屏蔽 |
| x0 | 0x85491000 | 原 FDT 指针，不能改作新堆 |
| x1/x2/x3 | 0/0/0 | 与 ARM64 启动接口一致 |
| Image 起始 | 0x80080000 | 探针通过当前 PC 与已编译相对偏移计算 |
| 原内核入口偏移 | 0x2380000 | 由原 Image 第一条 B 解码 |
| 原 Image 有效长度 | 0x3612000 | 本次当前内核 header，包含运行时空间 |
| 原 SP | 0x9ba29f00 | 历史交接栈指针，不是新栈分配许可 |
| 原 LR | 0x27bf5be48 | 历史返回地址，不是新 FD 分配许可 |
| CNTFRQ | 19200000 | 与本机 live FDT / MiCode 核实值相同 |
| 探针范围 | [0x836a0000, 0x837a8000) | 本轮下载镜像中的临时存储，已通过 FDT memreserve 保留 |
| 新 FDT 副本 | 0x836a7000 | Android 实际读回该副本的新增属性 |

这证明新编写的入口代码已执行并成功继续原 Android。它不证明原厂 UEFI Boot Services 可以复用，也不证明新 FD、GOP、按键、DarwinBoot 或 XNU 已执行。

## 内存合同与候选布局

新库 `RaphaelMemoryContractLib` 对分配区执行地址一致性、溢出、对齐、Image 边界、RAM 包含、保护区与分配区重叠检查。它只判断传入范围的几何关系，调用者必须提供完整的实际内存所有权资料。

```sh
python3 scripts/check_memory_plan.py
python3 scripts/build_diag_edk2.py --platform memory-contract
```

9 个主机用例通过；标准 EDK II AARCH64/CLANGPDB 库编译通过。库产物 9156 字节，SHA-256 `00d42550b57942a89c9c89f5a08819ab21d4121ab4f1da9ee3d26a9801594a43`。

`uefi-raphael/Resources/memory-plan.toml` 提出一个保留原 Android 内核、在其后容纳桥接代码、FD、SEC 栈、DXE arena 和 FDT 副本的设计。容量是明确的设计预算，位置由本机入口与原 Image 长度推导。检查已保护原内核、原 FDT、initrd、固定保留区、原 SP/LR 所在页和原厂默认非 Kernel 区域。

**生产配置仍未启用。** 独立私有诊断构建现已生成本次 PCD 和 3 MiB FD，细节见 `SEC-DXE.zh-CN.md`。扩大 Image size=0x4a80000（78118912 字节）已在本机接受并继续 Android，见 `extent-download.json`；其中 20283392 字节尾部仅为零填充，未由入口探针写入/读回。uefiplatLA.cfg 覆盖机制和完整原固件内存所有权仍不明。上次探针自己新增的 memreserve 在新一轮原始 FDT 中应不存在，此项在报告中显式列为被排除的诊断保留项。

最小 SEC/MMU/HOB、DXE 及回传现已实现并完成结构和模拟器检查；实机按分段门禁推进，保留无回传尝试和恢复证据。上述设计通过范围检查不等于已获得该 arena 的硬件使用权。
