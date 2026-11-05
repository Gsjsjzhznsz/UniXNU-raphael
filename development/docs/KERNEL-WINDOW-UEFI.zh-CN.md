# 手机主线：DarwinBoot 连续分配合同

2026-10-29，Asia/Shanghai。手机已通过独立 SEC/MMU/DXE 的连续分配生命周期。**本轮没有执行 DarwinBoot 有效内核加载、ExitBootServices 或手机 XNU。** 完整移植继续进行。

## 源码实现

实现提交 `7265f5676851298000346176971658223c7a36fb`。通用 UniXNU 40d21cc、DarwinBoot 3325e352、Mu Basecore cfb93724、XNU d8b80295 保持固定，本轮没有同步上游。RAM alias stash 没有应用，没有扩展 RAM 诊断。

`RaphaelPkg/Sec/KernelWindow.c` 从不可变 FV RAW 资源读取显式启动策略；SEC 重新解析当轮入口 FDT 的 RAM、固定/header 保留区、initrd、原 Image、FDT、SP/LR，并检查整个下载扩展与策略中的 95 项历史保守排除区。新窗口还必须满足现场 CPU PA 能力、2 MiB 对齐、原 loader 的 256 MiB 请求及实际 Mach-O 低 21 位偏移。

窗口作为独立 HOB 交给原 DXE core，最初整段为 `EfiBootServicesData`，普通 DXE 堆仍限原 16 MiB arena。`KernelWindowTest.c` 通过真实 `FreePages`/`AllocatePages(AllocateAddress, EfiLoaderCode)` 执行“保留→释放→分配 256 MiB→释放并重新保留”；各阶段用不分配内存的缓冲区重新核对内存图。代码不直接向候选窗口写测试图案。

| 输入 | 数值 | 来源与边界 |
|---|---|---|
| 策略窗口 | `[0xc0000000,0xd0200000)`，258 MiB | 本次 `kernel-window-audit.json` 第一候选剩余区间内；256 MiB 加 2 MiB 是显式对齐预算 |
| 原 loader 请求 | 256 MiB | 固定 DarwinBoot `WindowSize.h` 与 `AllocateWindow`，没有缩减 |
| Mach-O 基址 | `0xfffffff007004000` | 冻结原生内核的独立结构检查；不是手机物理地址 |
| 实际页面请求地址 | `0xc0004000` | 原 loader 对齐公式及上述 Mach-O 偏移；手机 AllocateAddress 成功 |
| 排除区 | 95 项 | 本次 FDT/Linux memory views、本机 XBL 静态声明和原诊断布局；当轮入口保护区另行重验 |

**设计假设不是已验证事实：** 此实验显式接管候选范围，依赖固件已经初始化这部分 DRAM，并假设没有未声明的存活固件/DMA 使用者。Mu core 要求 PI `TESTED` 属性才将资源纳入页面分配器，源码明确把此属性列为实验启动策略，不能用该位反过来证明物理 RAM 已全面测试。历史可恢复写入只覆盖前 256 MiB；额外 2 MiB 是容量余量。隐藏所有权、跨页别名和长期 DMA 不因本轮分配通过而变为已验证。

## 主机构建与结构

```sh
python3 scripts/run_kernel_window_qemu.py
python3 scripts/build_kernel_window_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report artifacts/kernel-window-uefi-qemu/20261028T184446.737030Z-kdsnse6s/report.json --inspection artifacts/native-kernel-inspection/20261028T180002Z/report.json --stop-after-stage 4
```

手机分别编译 stop stage 2、3、4；最后一种实际返回 stage 6。三个 FD 均为 3 MiB，FV/FFS/PE/XIP、策略范围/尺寸/哈希检查通过。原 Android kernel/ramdisk/DTB 保留在私有临时镜像内，未写原 boot 分区。

| stage | 私有 build UTC | boot SHA256 | FD SHA256 |
|---|---|---|---|
| 2 | 20261028T184541Z | 827a44c756232a2811566d7e31136cfe019fa967e83d815890590e93fdf9a303 | fb0d6529a4fa26c7b310f9d0af3604a2333a1bc46fb544fd545a3bdc9893a201 |
| 3 | 20261028T184926Z | 93e8d403a14121ea4b28390d07de349bb0e438db96a6a4a3cb2dee52993ed7c3 | effb6c3acf50c910aaf4b360bc2d7d9bd11ebf850ab27e3b2d33a4516681b0eb |
| 6 | 20261028T185353Z | 17e05649bfa079a5bb8d7dfba513712b90dbc1f33634224f51c7512c49966d91 | 97b7fd558949e225799227d624b353d5ee00c399b48fb7b6e5ab406f605ff792 |

失败保留：首编 PCD token 0x79 与既有 TimerArch 冲突，改为未使用的 0x80；结构检查先后遗漏新 FREEFORM 类型、出现局部变量遮蔽 FD base/file size，修正检查器后通过。最初 512 MiB QEMU profile 没有返回诊断记录且接收器 ID 不匹配，不能认定唯一根因；最终改用同轮生成的 1 GiB FDT、RAM 中点及正确接收器 ID。各次目录、冻结源码和原日志没有删除或改写成成功。

## 实际执行

QEMU `20261028T184446.737030Z-kdsnse6s` 使用自有 SEC/DXE，**不是 AAVMF 提供分配器**；47 项检查通过，四个生命周期状态均为 1。QEMU 地址 `0x60000000/0x10200000` 只来自其当轮生成的 1 GiB RAM，不能代入手机。

关闭新功能的默认固件回归 `artifacts/sec-dxe-qemu/20261028T184734.881342Z-diuvv9d1`：正常 47、BRK 44、UDF 44 项通过。

手机临时 `fastboot boot`：

| run UTC | 结果 |
|---|---|
| 20261028T184704Z | stage 2，入口策略/当轮 FDT 几何接受，回 Android |
| 20261028T185040Z | stage 3，新窗口加入 MMU/HOB 后正常返回；不是逐页物理访问证明 |
| 20261028T185509Z | stage 6，256 MiB AllocateAddress 成功；reserved/released/allocated/restored=1/1/1/1，status=4、error=0，最终整段为 BootServicesData |

三轮 nonce、Android/root、原 boot 哈希均通过，每轮之间正常重启清理。最后清理 `20261028T185721Z`：Android/root/boot 哈希正常、临时标记全部消失，无 flash/erase/format。原备份未改动。

`validate_kernel_window_evidence.py` 重新读取三轮原 FDT、48 字段 wire、固件日志、内存图、冻结 FD/boot 镜像、策略及源码快照；逐项核对实现提交 Git blob，并独立核对最终整个 258 MiB 的 BootServicesData 覆盖与普通堆边界。`artifacts/kernel-window-verification/20261028T185948.596656Z-35roft67/report.json` 通过，公共摘要为 `UniXNU-raphael/evidence/kernel-window-uefi-verification.json`。

## 后续主线

下一步接入有效原生内核载荷和原 DarwinBoot。当前诊断 FV 的 FAT 仅 1 MiB，普通 DXE heap 仅 16 MiB；18,463,480 字节的原内核不能直接沿用该装载预算。后续需要明确的载荷与 staging 内存布局，不能让源文件缓冲区占用待分配的内核窗口。

可以从当前“原 Android 后追加诊断”的布局转为独立小 Image/UEFI 入口，以在已接受的下载范围内安排较大的 FV 和堆；这是设计方向，**尚未实现或实机验证**。本机已采集 FDT 声明 `arm,psci-1.0/method=smc`，但 PSCI 重启尚未执行；不得据此宣称自动故障恢复已经可用。继续使用已有 GOP/日志回传，UART 接线与真实输出仍待核实。有效交接后的持久化日志也尚未分配存储范围。
