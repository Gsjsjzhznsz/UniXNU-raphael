# 跨页同时标记诊断

## 目的和覆盖范围

此前手机 `0xc0000000..0xd0000000` 的逐页两轮图案与原字恢复测试已经通过，事实和来源仍见 RAM-CACHE-WRITE.zh-CN.md。它每页立即恢复，因此不能排除不同页实际解码到同一 DRAM 存储位置。新 `RaphaelRamAliasLib` 保持所有页的样本标记同时存在，补上这个诊断缺口。

每个连续 4 KiB 页选取首、尾两个 64 位字，完整 65,536 页共 131,072 个样本，需要 **1,048,576 字节调用方拥有的备份区**。库中没有新增本机 RAM 地址；Base、整个候选窗口及保护范围必须来自同轮 policy/read/mapped/live-entry 门禁。主机 fixture 的 `0x100000000` 只是模拟地址，不作为本机板级输入。

通过本诊断只能证明这些样本在当次测试中未显示出别名或图案错误。它不排除任意其他字节的别名、动态重映射、隐藏 DMA 或长期固件所有权，不自动构成连续 UEFI 分配合同。

## 源码与不变量

- `Include/Library/RaphaelRamAliasLib.h`：独立的 312 字节结果与 400 字节恢复状态；旧 RAM read/mapped/write/cache wire 不变。
- `Library/RaphaelRamAliasLib/RamAlias.c`：备份、两轮同时标记、统一读回与强制恢复状态机。
- 新 INF、DEC library class 和 `RamAlias.dsc`：仅用于独立编译，没有 FD、SEC、PCD 或 allocator 集成。
- `scripts/fixtures/ram_alias_host.c`：实际库源码的分离 DRAM/cache、可注入 DRAM 解码别名及故障模型。
- `scripts/validate_ram_alias.py`：先冻结全部输入和头文件，再编译、执行、交叉编译及构建 EDK II library；最后再次核对 live/frozen 输入哈希。

执行顺序：

1. 校验不可变输入互不重叠、备份精确覆盖所有样本，复核 policy 与旧只读、映射和当前 EL1/MCI/DAIF/PA/frequency 门禁。输入或备份不得位于整个候选窗口；不接受 dirty 或正在运行的状态重入。
2. 对每个页首尾执行读、写两种 WB 恒等转换及 PAR 保存恢复查询。完整范围为 131,072 点，任何一点失败都不能开始标记。
3. 先同步整个待测页集合，排空原有脏缓存；再按页同步并读取全部原始样本。**所有样本备份完成前，绝不执行标记 store。** 原始摘要按每个样本的地址和值计算。
4. 两轮互补地址相关标记，每轮先写完全部页并完成 PoC 同步，再统一同步、读回验证。标记对于不同地址互不相同。
5. 每次 store 尝试之前置 Dirty、更新单调 ArmedWords 及其反码并执行 compiler fence。第二轮不重置最大恢复范围；回调可能已经写入后才返回失败。
6. 正常和失败路径均进入恢复。先检查所有备份字的摘要及 journal/bounds，然后在第一个原字 store 前排空所有可能脏的标记页；写回所有已尝试位置并按页同步，再同步、独立读取**全部备份样本**。不同地址仅因 DRAM 别名被间接改写的情况也包含在读回范围内。
7. 所有回调成功、原字逐样本一致且摘要一致后才清除备份、ArmedWords 和 Dirty。恢复失败完整保留原始备份及 journal，禁止继续分配或返回 Android；回调正常返回后可以显式重试。恢复过程中的重入直接拒绝。

前进路径维持原 **8 秒**预算并检测时钟倒退；强制恢复没有诊断超时。正常完成也在原字恢复之后检查总预算。摘要和 journal 反码只用于发现意外损坏，不是密码学完整性或 DMA 防护。

Sync 回调必须真实 clean/invalidate 到 PoC 并具有完成屏障；库本身只定义该接口，尚无已验证的 SEC 原生适配器。compiler fence 不替代硬件缓存屏障。当前主机故障均为正常返回的 callback failure，不构成 AArch64 同步异常恢复事实。

## 主机验证与结构检查

运行：

```sh
cd /home/guo/work/raphael-fresh
python3 scripts/validate_ram_alias.py
```

最新完整运行：`artifacts/ram-alias-host/20261028T155542.543576Z-pm9nqcft`。

| 验证层 | 本轮事实 |
|---|---|
| 源码 | 实际 C 库与 fixture/runner/全部本包头文件在编译前冻结；准确输入 SHA256 存于 report.json |
| 主机执行 | GCC 13.3、ASan/UBSan，249 项检查通过；覆盖 1/3/256/65,536 页首尾样本集合 |
| 故障覆盖 | 全部正常路径读、写、同步、转换位置；写/同步前失败及执行后报错；属性/PA/PAR 错误、时钟倒退与期限；第二轮恢复最大范围不缩小 |
| 别名与缓存 | 同偏移跨页、跨偏移、同页首尾和远距离 DRAM 别名均检出并恢复；预存脏缓存与冲突别名脏行在首次备份前整体排空 |
| 恢复状态 | 完整备份含未 armed 样本的损坏、20 种 journal/回调/范围字段损坏均在恢复 I/O 前拒绝；dirty 重入、恢复重入和显式重试通过 |
| 预算 | 模拟恢复耗时超过 8 秒仍先完成全部原值恢复，随后报告期限失败；恢复中不查询诊断 counter |
| AArch64 编译 | 固定 clang-18 哈希核对，ELF relocatable 对象结构检查通过、未定义符号 0；结果/状态 2 项静态布局断言，静态帧最大 176 字节 |
| EDK II | 固定 mu_basecore `cfb93724a06ff86ff5ba971413368a7809ee42a5`、真实 INF/DEC/DSC + AARCH64/DEBUG/CLANGPDB 编译归档成功；归档成员 bitcode triple 为 AArch64 Windows MSVC，未定义符号 0 |
| 固件镜像 | **本轮未生成新 FD 或可启动镜像，未做新库镜像结构或加载验证** |
| QEMU / 手机 | **新库均未执行**；主机样本模型不等于真实完整 256 MiB 内存或手机恢复证明 |

主机布局另有 4 项编译期断言，包括旧 write/cache 结果尺寸不变。对象、archive、主机可执行文件、命令和输入哈希见 `ram-alias-host-20261028.json` 及原运行目录；对象不是可启动镜像。

首次主机编译因 C/UEFI 头文件 NULL 定义顺序产生 Werror，日志保留于 `20261028T154307.632538Z-lplbpad_`。首次 EDK II 归档构建本身成功，但检查器错误假定成员为普通 COFF；已按实际 CLANGPDB LTO bitcode 成员检查 triple，失败日志保留于 `20261028T155406.217863Z-vvieagwq`。没有覆盖失败目录或将其改记为通过。

## 下一门槛

为 SEC 提供有来源、位于真实保留范围内的 1 MiB 备份区和异常路径可访问的 journal，重新核对 3 MiB FD 容量、实际 .data 落点及所有范围保护。之后才能加入默认关闭的原生 load/store、PoC callback、RW/RO/PAR 恢复与异常跳转路径，并验证 AArch64 机器码、两阶段 QEMU 正向/部分写异常/恢复失败封闭行为，最后按小范围到全范围实机门禁推进。

当前分配器仍只有原 16 MiB 诊断 arena，手机有效 DarwinBoot/XNU 交接、连续 RAM 分配合同、长期所有权及其他外设仍未完成。本轮没有手机操作、分区写入或原备份修改。

实现固定版本：`57555b02d601ded4a0badd7bc9f0fd84b62315c5`。独立证据绑定重新逐项核对全部冻结输入与该提交的 Git blob，并重算可执行文件、ELF 对象、EDK II 归档及原日志哈希；公开索引为 `ram-alias-host-20261028.json`。原运行在实现提交前构建，保留其真实 dirty/head 字段，不能仅用原 source_head 代替冻结输入。

2026-10-29 本地时间的只读容量核查重新计算了既有 `144222Z` FD 哈希、FFS 末尾和全 0xff 空闲尾部：原 3 MiB FD 的对齐空闲尾部为 2426960 字节，原 SEC .data 中的 4 KiB 页备份有实际文件覆盖。扣除拟议 1 MiB 样本备份后仍有 1378384 字节算术余量。这只支持继续评估 `.data` 方案，不证明新增代码、对齐和全部模块重排后一定适配；新存储尚未实现，准确来源/哈希和待验证项见 `ram-alias-storage-20261029.json`。
