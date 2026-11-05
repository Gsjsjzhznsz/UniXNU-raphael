# 诊断后恢复本机 Android 内核

2026-10-29，Asia/Shanghai。本轮实现默认关闭的 `PcdRaphaelAndroidReturn`。手机的小规模 SEC/MMU 阶段3和完整DXE阶段6均已实测，带nonce、解码CRC、原始FDT/wire和正常重启清理记录；不是手机有效XNU交接。

## 实现与输入

64KiB独立接收器提供早期PSCI恢复；新SEC把返回stub复制到已门禁258MiB窗口的最后256KiB，末尾状态通过GUID HOB传给DXE。窗口生命周期、交接前释放和拒绝后恢复都保留该尾部，不包装原Mu分配器。两次手机使用高段 `0xd01c0000..0xd0200000`；它由本机kernel-window-audit和258MiB策略计算，不能当作整段额外2MiB的RAM测试。

本次采集的当前Android内核是定制4.14内核，不称作原厂内核。raw Image为46,813,200字节，声明56,696,832字节。Python LZMA_ALONE preset1压缩为15,373,470字节，附在原444,400字节ramdisk后；原DTB四份逐字保留。压缩输入、输出、ramdisk的CRC和SHA256及来源写入private build报告。通用decoder是固定Mu cfb93724a06ff86ff5ba971413368a7809ee42a5的原始LzmaDec.c；没有网络依赖或修改decoder。

95,440字节位置无关AArch64 stub无未定义符号、动态重定位或未物化BSS。使用高段栈、scratch及异常恢复向量；真实解码后核验完整输入消耗、长度和输出CRC，清除raw Image尾部至原声明大小，收窄FDT initrd-end，清理低/高缓存范围并恢复原架构状态后进入原Android入口。解码失败只尝试PSCI恢复，不执行已部分覆盖的低代码。原Android内核、镜像、固件和原始设备数据都在ignored路径。

## 布局与失败

最初16MiB arena版本在手机fastboot接受后没有返回nonce/SEC/解码记录；电脑随后枚举到Bootloader接口并显式发送fastboot reboot恢复Android。不可变失败为 `evidence/private/android-return-run/20261028T203621Z`，不能把其后Android正常当固件执行成功。125.5MiB旧大布局探针也仍保留为失败，没有新入口证据。

独立保留原Android内核的扩展initrd探针 `entry-probe-run/20261028T204315Z` 带nonce实测：输入FDT 0x845e8000，扩展initrd 0x847e9000..0x856fec8e。前者与原16MiB arena候选重叠。该观察本身不能证明失败轮执行到哪条分支；后续成功的12MiB轮也在入口原始记录中确认相同FDT地址。

小规模profile把arena设为12MiB设计预算，并放在原Image声明范围末端之后，FDT副本在arena之后，避免解码覆盖正在使用的页表和日志。所有入口保护区仍由当轮FDT重新检查，地址不是绕过检查的白名单。大载荷24MiB FV/48MiB arena不能直接沿用该布局，尚需独立安排和验证。

## 四层验证

| 层次 | 本轮结果 |
|---|---|
| 源码 | Wire/PCD/FV/SEC/MMU、原Mu HOB和高段保留；NativeHandoff单独门禁，staging不隐式跳内核 |
| 主机 | 实际Mu decoder的ASan/UBSan 4,107项；本机完整内核也执行同份host harness并逐字比较；原boot默认repack逐字一致 |
| 镜像 | ARM64 ELF无未定义/重定位/BSS；FV/FFS/PE结构和布局检查；所有源码版本、命令、SHA256分别记录 |
| QEMU | 自有SEC/DXE，无AAVMF；恢复46MiB合成接收器，逐字检查tail及8MiB BSS、FDT和架构状态；阶段3/6分别19/20项；默认路径47/44/44项回归；有效XNU的3次物理timer IRQ回归另存 |
| 手机 | 阶段3和6均nonce、完整解码CRC、46,813,200输出字节、FDT原ramdisk跨度、Android/root、原boot哈希及正常重启清理通过；全程临时fastboot boot |

手机阶段3：build 20261028T204804.652938Z-ntmk6_tr，run 20261028T204929Z，boot SHA256 `8788e05d9cdd5c09ad7ad35fdea85b8b276c35270e8c47c69787c9a475ca32e6`。

手机阶段6：build 20261028T204804.651192Z-8hagej1r，run 20261028T205204Z，boot SHA256 `aa8b8c40a329de69e7c12176a873aa4635159ba57e25b1028c1dab5eaa75671b`。

两次约49.6秒返回Android，无bootloader辅助恢复；阶段6额外验证原Mu服务表CRC、map confinement、真实分配/释放及连续窗口生命周期。不能把这些结果扩大为完整UEFI、全面RAM所有权、手机有效XNU或ExitBootServices之后的日志。

## 重现

主机：`python3 scripts/validate_android_return_host.py`。

QEMU：`python3 scripts/run_android_return_qemu.py --stage 3` 和 `--stage 6`。12MiB证据分别为 `artifacts/android-return-qemu/20261028T204709.580863Z-51l51t6e`、`20261028T204709.563807Z-uw0u51cs`。

手机build：`python3 scripts/build_android_return_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report <相同stage的report.json> --stage 3`（或6）。先独立核验输入/结构；实际临时启动由 `run_android_return_handset.py --serial <private serial> --build <private build>` 完成，并按原始FDT、wire和正常重启再次验证。不要将private产物发布。

下一步为不覆盖当轮输入FDT/initrd的大FAT/heap布局与真实UniXNU staging；随后本机ADT和有效DarwinBoot/XNU手机交接。UART引脚、电平、接线及真实输出依然未知；此处是诊断返回通道，没有解决XNU交接后的持久日志。

独立复核：实现提交 `2e7fac1`，`validate_android_return_evidence.py --revision 2e7fac1`于205815Z重新读取原始镜像、FDT、wire、命令、源码快照并逐Git blob绑定166项输入；公共索引为 `UniXNU-raphael/evidence/android-return-verification.json`。
