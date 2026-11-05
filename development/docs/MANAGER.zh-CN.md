# 手机完整UniXNURun诊断

2026-10-28。目标是在已验证的本机物理TimerArch下实际调用固定、未修改的UniXNURun，读取自有只读RAM FAT中的配置，执行两秒倒计时并自动退出。该诊断不加载OS，不访问本机存储；当前采用无GOP的输出路径，不据此宣称完整管理器可见菜单。原诊断菜单和实体三键的历史证据保持独立。

## 实现与来源

--physical-timer-arch --payload-test组合启用，DarwinBoot仍为模拟器专用门禁。1MiB FAT放在既有自有FV内，SEC生成单独4KiB initrd FDT/HOB，复用固定UniXNURamDiskDxe、DiskIo与Fat。配置固定单条action=exit，timeout=2，kits自动加载关闭。Android原initrd、FDT与磁盘分区不替换。DXE检查RAM卷身份、ReadOnly及写请求被拒绝，读取配置后调用真实UniXNURun；CRC前后必须相等。

新增独立6×u64 manager wire记录真实调用前后物理counter、频率和配置超时。结果放SEC静态状态，TimerArch原448字节wire保持不变；状态总大小从原版本464增加到512，context未扩大。进入管理器前必须已安装真实物理TimerArch且未发生中断错误，结束后继续relative/periodic/cancel/停表检查并完整恢复。

## 主机与模拟器

最终同源码QEMU：014306.081636Z-wxaam11x为stage2/56项，014306.076877Z-cqfabojg为stage3/58项，014306.094350Z-vb7m_kx7为stage6/72项。route-local UDF恢复52项、默认/BRK/白名单外UDF42/39/39项、原通用架构与Darwin拒绝路径61项均通过。完整日志/命令/哈希在artifacts/sec-dxe-qemu各目录。

18项独立manager wire/倒计时边界/跨证据检查及8项实际C ABI断言通过；TimerArch63项/58项C断言和单次IRQ32项/25项断言继续通过。主机实际C路由测试增至107项。

保留失败：013735.392187Z-a0qqk0vo在route前置证明中拒绝，未进管理器。CTL读取早于HPPIR，source恰在两次读之间到期时会误拒绝。已在看到目标HPPIR后重新读取CTL/counter并约束原100ms上限；新增两个独立模型在读间推进到deadline，分别验证路由与IRQ leaf门禁。它们在旧代码会失败，现通过。没有把不完整快照放宽为成功。

构建命令为python3 scripts/build_sec_dxe.py --physical-timer-arch --payload-test [--stop-after-stage 2|3]；手机生成命令追加--collection evidence/private/device/20261027T120325Z，并使用--stop-after-stage 2|3|4。各阶段必须有同源码先前手机检查点。实现、编译、结构与手机执行分开记录。

## 手机三阶段结果

固定实现 `0a91c564e4bb21a1ba64e5eafcdfd68cef9fea56` 的 SEC2、MMU3、DXE6 均已实机通过。84项自有固件输入和47项UniXNU输入逐Git blob、不可变构建快照及同阶段QEMU报告匹配；16项构建/验证脚本另行绑定。

| 阶段 | 构建UTC | 手机运行UTC | FD SHA-256 | boot SHA-256 |
|---|---|---|---|---|
| 2 | 20261028T014626Z | 20261028T015002Z | `fb3f56f3a4e65c0f24850387245e0e2c88e8c5f577fdb82d525c814643594216` | `93cef862fa9f98f166d9a6f159117866ff5bc8fff56a9a184a4fc3ad14f4221c` |
| 3 | 20261028T015545Z | 20261028T015637Z | `1739dd3a31f81acb9bacd4bed911985e46eab22382d3f9bff0c10c1b846b4619` | `53d8bc9e87434778b935332cc9dad09ebe818a209f86154dab0da7583b4ab051` |
| 6 | 20261028T015908Z | 20261028T020020Z | `1e5a593325ac986abf3002bab59f5bec54687be1bc519e6bea524a7543dac4f8` | `250f52cc75c57b1eb2b359e96fa80993187aaea9506fb8f47828948fd315fd55` |

DXE6真实调用从counter 1074337903至1112810452，频率19200000Hz，共38472549ticks，即2.00377859375秒。配置timeout=2、action=exit，UniXNURun返回EFI_SUCCESS。1MiB只读RAM卷WriteBlocks被拒绝、FAT/配置来源正确，CRC前后均3332669622。

物理PPI18持续IRQ/EOI/notify各262，无spurious/unexpected。随后relative约100.001198ms、periodic五次约104.999167ms，取消与停表稳定检查通过。GICD_CTLR恢复0x10；IGRPEN1、CNTP_CTL/CVAL、local enable/active均0，pending0x10080000、DAIF0x3c0恢复；CNTV_CTL5、CVAL235337914保持原值。所有阶段nonce、Android/root/原boot哈希通过。

正常重启清理分别为015449Z、015858Z、020320Z，临时FDT属性消失。没有flash/erase/format，原备份未修改。

验证运行：`python3 scripts/record_manager_observation.py --cleanup evidence/private/entry-probe-cleanup/20261028T020320Z`。记录器重新验证三份历史固件的Git/快照/产物/QEMU绑定、独立manager wire、不可变attempt与handoff的公共字段、FDT哈希和清理。汇总为`boot-manager-observation.json`，绑定为`manager-source-binding.json`与三份不可变阶段绑定；`validation-checkpoint.json`将完整管理器执行与可见性分开。

首次记录器将handoff与attempt要求全对象相等，因两者各自的元数据字段不同而拒绝；现严格检查差异字段集合和全部共同字段，并核对真实FDT哈希。该失败不属于固件或手机失败。

## 下一步与限制

本轮仅验证无GOP、合成只读退出配置的完整管理器调用；原可见诊断菜单与三键来自独立历史实测，不能拼接成完整管理器UI的人工验证。下一步结合可见GOP与输入，再推进DarwinBoot至少256MiB连续窗口、RAM保留/所有权及真正XNU平台。当前16MiB诊断arena和十秒有界TimerArch仍不是完整OS平台。
