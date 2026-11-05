# 主线内核载荷与独立 staging arena

2026-10-29，Asia/Shanghai。实现 a4069e0，保护区和稀疏映射修正 33822d4，分离窗口保护修正 d2d2bc2。上游固定 UniXNU 40d21cc、DarwinBoot 3325e35、Mu cfb9372；本轮没有 fetch/pull。

本轮目标是让自有 SEC/DXE、原 Mu 分配器及原 UniXNU 文件系统完整读取已冻结的有效 XNU 文件。该 profile 仍使用明确无效的 ADT 占位，NativeHandoff=FALSE，不能据此宣称手机执行 XNU。手机阶段 3/6 已通过；360 项冻结输入及原始回传独立复核通过。

## 实现与来源

实际下载的 ARM64 Image 为 25,559,040 字节，header image_size 与实际字节数一致。低 64KiB 为此前验证的 PSCI receiver；其后为 bridge、24MiB FV 和 256KiB 栈。20MiB 只读 FAT 在 SEC 内复制到独立 arena 上部；原 Mu 分配器未修改或包装。

arena 使用 56MiB，FDT 副本另 0x110000；下部 36MiB 中 32MiB 是原生 EfiBootServicesData type bin 预算。48MiB/24MiB bin 失败时，真实 free spans 最大约 15.7MiB，完整文件分配落入内核窗口，被范围检查拒绝。修正采用 56MiB/32MiB 预算，原非稀疏 native profile 仍保持 48MiB/24MiB。

手机候选 arena 由 kernel-window-audit.json 的 structural_unreserved_runs 计算：在已经保留的 258MiB 连续窗口之后留 1MiB 设计间距，再按 2MiB 对齐，取可容纳完整 arena/FDT 的第一个审计区间。当前结果 0xd0400000..0xd3d10000，其中 arena 到 0xd3c00000，随后为 FDT 副本。它是独立且默认关闭的实验性 boot grant，不是 Image 下载范围、原厂授权或全面 RAM/DMA 所有权证明。SEC 仍在本轮入口逐项检查 live FDT RAM、固定保留区、header reserve、输入 FDT/initrd 和原 SP/LR；原连续窗口另行检查全部审计保护区。

稀疏映射只包含原 Android 输出范围、只读 initrd、独立 arena/FDT 和连续窗口。中间空洞不映射、不进入分配器，不进行整段缓存维护。返回 state v2 保留原 19 项架构寄存器偏移，在末端增加 AuxBase/AuxEnd，独立清理 arena 内的 FDT/页表；原低 Image 与高返回 stub 的维护仍各自有界。

DXE 使用真实 SimpleFileSystem 打开 kernel.macho，通过原 AllocatePool 取得整文件缓冲区，要求缓冲区完整位于 arena 的 FAT backing 之前，且在内核窗口之外；验证全部文件字节 CRC、EOF、FreePool 和窗口恢复。验证位置与原 loader 一样在释放连续窗口之后，范围检查没有放宽。

被冻结的 XNU 文件为 18,463,480 字节，SHA256 96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722，CRC32 ea90cabc；来源为 native-kernel-structure.json 的独立结构检查。编译成功、结构正确、完整文件读取和内核指令执行分别记录。

## 主机、镜像和 QEMU

state v2 的真实 Mu decoder ASan/UBSan 4,107 项通过：artifacts/android-return-host/20261028T213842.714476Z-b5f8zfxx。每次手机构建还用同份 host harness 对本机完整私有 Android 内核解码逐字比较。

新版 QEMU 阶段 3/6 分别通过 21/23 项，目录 20261028T214544.292988Z-hbwhwo39 与 20261028T214544.292983Z-i5w3ow38。真实接收器逐字核对原始合成内核、零尾、FDT 和恢复寄存器；阶段 6 完整读取有效 XNU 文件并恢复窗口。没有 AAVMF、手机地址或真实 XNU 分支。

默认关闭 profile 回归 normal/injected_brk/unmapped_udf 为 47/44/44：artifacts/sec-dxe-qemu/20261028T214544.413914Z-3dyjskz3。FD 逐文件/section/PE/入口/重定位及 FAT 两块重组由独立结构检查器检查。手机构建和运行目录分开，所有脚本和编译输入分别冻结；原始 closed kernel、固件、设备 ID 与 boot 镜像留在 ignored private 目录。

## 保留的失败

- 最初手机声明 151,584,768 字节（约 144.56MiB）范围、实际下载约 24MiB 的候选在 QEMU 可运行，手机 20261028T211732Z 无 nonce/SEC/返回记录，bootloader reboot 辅助恢复。固定 ABL 参考 BootLinux.c:674 会拒绝越过输入 FDT 的 ImageSize；此源码与现象相符，但没有证实本机二进制具体分支。新实现不再把 arena 写进 Image header。
- 稀疏 Image 后的首轮 QEMU 20261028T212254Z 因输入 FDT 位于候选 arena 内失败。独立硬件断点捕获 SecFinish(0x102)、plan status 7，证明保护区检查仍拒绝重叠。QEMU fixture 后移其 initrd/arena；手机参数没有复制该布局。
- 手机 20261028T213200Z 自行回 Android，但 nonce/SEC/返回记录缺失，实验失败，正常重启/root/原 boot 哈希和清理均通过。离线发现先前由 initrd 末端推导的 0x85800000 候选跨过 hyp_mem、xbl_aop_mem、smem、removed_regions。缺少回传，不能断言手机具体拒绝分支；构建器现改用完整审计保护区筛选，错误候选未在新代码中继续使用。
- 手机 20261028T214132Z 因低下载到高 arena 的外包保护区包含内核窗口而失败，无 nonce，45.37 秒自行回 Android并正常清理。d2d2bc2 将两块实际保护区分离；QEMU 同步改为低 Image < 窗口 < 高 arena 的相对顺序，避免此前未覆盖这种几何关系。
- 各 48MiB arena 分配失败、旧 125.5MiB 布局、16MiB 小规模入口失败及全部原始镜像/日志继续保留。后续成功不会覆盖这些结果。

## 重现

```sh
python3 scripts/run_native_staging_qemu.py --stage 3
python3 scripts/run_native_staging_qemu.py --stage 6
python3 scripts/build_native_staging_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report <对应新版QEMU报告> --stage 3
python3 scripts/run_android_return_handset.py --serial <本机ID> --build <私有构建目录>
```

先确认阶段 3 的 nonce、状态、恢复和清理后再运行阶段 6。没有 flash/erase/format，也没有修改原备份。后续是来源明确的本机 ADT、原 DarwinBoot 有效加载和内核交接后的诊断；UART 外部接线与真实输出仍未知。

## 手机结果与独立复核

阶段 3：build 20261028T214823.938843Z-p9bq02a0，run 20261028T215039Z，boot SHA256 3ab56736671f0cd31ce61b3206b51b51d82b3f0b789bb97bf62461d8f2906a0e。nonce、SEC stage3/status0、20MiB FAT materialization、高返回 LZMA/CRC 通过，49.668 秒自行回 Android。此阶段没有完整文件读取。

阶段 6：build 20261028T214823.940995Z-3fjvggi4，run 20261028T215331Z，boot SHA256 faf3a7ae6e7106fbd01e9d19b174a4e841acbcebd339d0c7a702611227677f48。真实文件系统和原 AllocatePool 完整读取 18,463,480 字节，buffer 0xd0de3018，CRC ea90cabc，EOF/free/window restore 通过；49.423 秒自行返回。两轮均正常重启清理，root/原 boot 哈希正常且临时属性消失。没有 bootloader 辅助恢复，没有 XNU 指令执行或 ExitBootServices 成功证据。

真实 C 内存合同的 5 项预检分别在 native-staging-plan/20261028T215023.814455Z-vmn5x66o 和 20261028T215331.034896Z-w1nv9wq6 通过；旧宽保护跨度和撞保留区候选均被拒绝。独立 QEMU 负向验证 native-staging-guard-qemu/20261028T215257.157868Z-eu3wqk2p 只修改输入 FDT，将 arena 首 4KiB 标为保留；真实断点捕获 PSCI SYSTEM_RESET 函数号，HVC 后退出且无 receiver 成功标记。手机编译使用 SMC，此处 HVC 仅属 QEMU。

独立复核器修正递归 gitlink 解析后，以父仓库固定提交中的子模块对象为准，不依赖子模块当前 HEAD。最终 artifacts/native-staging-verification/20261028T220144.752197Z-pyx15e4z 逐字重读镜像、原本机 kernel/ramdisk/DTB、完整 repack、wire/log 和正常清理，360 个输入逐 Git blob 一致。三轮手机失败全部保留。公共索引见 UniXNU-raphael/evidence/native-staging-verification.json；私有镜像未提交。
