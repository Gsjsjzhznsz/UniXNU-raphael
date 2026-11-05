# 本机 UFS 有界写入验证

2026-11-02 最新状态：用户重新授权原生 XNU 写入实机验证，现已整轮完成。**原生 XNU 单块 UFS 写入及跨普通重启持久性均通过**：`evidence/private/android-return-run/20261102T100353Z/report.json` 的 `passed=true`、`xnu_executed=true`、`native_ufs_write_verified=true`。本轮未启用 SEC 写探针，写入由正常内核观察线程显式调用 `raphael_ufs_diagnostic_write` 完成。

同轮匹配 nonce、完整原生检查点和恢复均通过：调用次数1、阶段63（原内容/WRITE10-FUA/同步/立即读回）、result/OCS0、权限已撤销；原 APFS 根仍只读。观察10poll、实际1402.405ms、喂狗3次；20秒硬件阈值、120秒观察上限/180秒绝对pet预算不变。205.900秒自动回 Android，再普通重启后新boot ID、root和临时FDT清理通过；Android文件与原始LUN的12KiB三块完全一致，中间4KiB为本轮新内容，两侧保护块未变。没有flash/erase、GPT修改或新分区；runtime-only未重读boot分区。

完整887记录XNU构建、预链接、最终内核唯一调用点与精确8256字节策略核对、恢复QEMU39项均通过。源码入口只在显式 `--native-ufs-write-policy` 私有诊断构建启用；默认配置不调用。第一次原生写探针094934Z已写入并跨重启保留，但约208ms即结束、仅一次pet，被原完整检查点至少两次pet的门禁拒绝；原失败报告保留，独立写入证明为其 `native-ufs-write-redecode.json`。第二轮只将收尾延至至少10poll并换用新分配策略，未放宽门禁。

**接续边界：** 这是本机单块原生写入证明，还不是连续启动日志、panic/IRQ日志、可写IOMedia或持久APFS Data。两轮测试块现均已变更，原preimage/镜像不能直接复跑；后续先建立新精确策略，再开发有界多块日志、启动ID/序号/CRC、刷盘与Android提取。可见桌面与基本交互仍未完成。当前无运行中的实验、构建或自动后续任务。证据索引：`UniXNU-raphael/evidence/native-ufs-write.json`；实施说明：`UniXNU-raphael/docs/HANDSET-UFS-WRITE.zh-CN.md`。

## 冻结证据与实现

- 完整原生构建：`artifacts/native-bootstrap-attempt/20261102T095737Z/report.json`（887记录）。
- 预链接与结构：`artifacts/desktop-prelink/20261102T100010Z/inspection.json`。
- 模块与190-slot绑定：`artifacts/raphael-ufs-object/20261102T095758.682649Z-818i8yew/storage-bindings.json`。
- 恢复QEMU：`artifacts/native-staging-qemu/20261102T100031.739559Z-obqrpjx3/report.json`（39项）。
- 冻结手机构建：`evidence/private/android-return-build/20261102T100220.841816Z-9uzhpxo7/report.json`。
- 本轮新分配：`evidence/private/ufs-write/20261102T095651Z/report.json`；LUN0，LBA29667393，仅1块4096字节，两侧保护块保留。
- 单变量补丁对照：`artifacts/session-logs/20261102-native-ufs-write-v1-v2-comparison.json`。
- 写入验收拒绝用例：`artifacts/session-logs/20261102-native-ufs-write-v2-acceptance.json`（7项）。

显式板级调用方为 `package/drivers/RaphaelUfsWriteProbe.inc`，仅私有构建器物化策略并编入模块，不将原内容和新内容写入仓库源码。`patches/xnu/native-ufs-write.series` 在正常观察线程调用一次性worker，完成后的后续poll直接读取完成标记，不重复写入。最终手机镜像构建器核对内核中的策略与唯一调用点，并拒绝省略原生写入preflight的镜像。主机在返回时按匹配nonce和完整检查点检查原生记录，普通重启后独立核对文件、物理块和保护块。

原生记录中的 `persistence_after_reboot_verified=false` 只表示该内核快照只能证明立即读回；同轮报告独立的 `native_ufs_write_persistence.verified=true` 才是普通重启后的持久性证明。不得仅根据内核记录升级这一结论。原094934Z失败报告不改判；其恢复快照可以独立证明写入，完整检查点仍被拒绝。

## 先前 SEC 与模块实现记录（历史）
2026-11-02。当前为显式诊断候选，不是通用可写 UFS、持久 APFS Data 或启动日志已完成。

依据固定 UniXNU `docs/zh/porting/ufs.md`：继承固件配置的控制器/PHY/时钟/SMMU所有权、DMA与命令完成、根卷、持久化分别验收。SM8550/sheng硬件常量和布局不移入raphael。

共享传输保留原只读默认，只有容量匹配、LUN0、完整4096字节块和固定授权窗口才能启用 WRITE10。WRITE10要求FUA；随后在同一授权范围执行IMMED0的 SYNCHRONIZE CACHE10，拒绝残差、OCS、SCSI或超时成功化，也不隐式重试。恢复或HCI错误复位撤销写权限；超时仍保留DMA隔离规则。

单块实机探针只使用本次新建的未加密、不可变项目文件，文件共12KiB，仅中间4KiB可写，前后各4KiB作保护。host冻结FIEMAP、userdata与LUN边界、原始内容及新内容；进入bootloader前再次确认。固件必须先读回并匹配原内容，再写入新内容、同步、立即读回。保留20秒硬件看门狗、其他七核OFF和无活动SMMU翻译门禁；不修改GPT、不写OS/SystemOS。

返回记录继续4392字节，version6的word30是单调阶段位：1策略、2原内容、4已尝试写、8写完成、16同步完成、32新内容读回。缺失回传保持原生执行未知；已尝试写不等于持久化成功。Android正常重启之后必须再次核对文件、物理块与两侧保护块，才能确认这一块跨重启保留。

初版真实QEMU模型68项及重启后40项通过；最终模型72/40项通过。手机SEC单块写入与跨重启读回已由下文012856Z整轮报告验证；原生XNU接口尚未执行。后续日志通道需要另行实现有界序号/nonce/CRC记录与刷盘时机，不能称为所有启动日志。


## 2026-11-02 UFS 写探针与对齐修复

- 写探针 `evidence/private/android-return-run/20261102T010758Z/report.json` 在111.770秒回到Android，但nonce不匹配，无SEC/UFS记录；执行未知。普通重启、root与临时属性清理完成，文件/原始介质三块均保持原内容。
- 第二轮 `evidence/private/android-return-run/20261102T011430Z/report.json` 只开启既有HCI错误复位，140秒窗口无回传、屏幕全黑，用户强制重启回Android。独立恢复 `evidence/private/android-manual-recovery/20261102T011914Z-ufs-write/report.json` 确认新boot ID、root、清理、原内容及两侧保护块；没有写入成功证据。
- 冻结SEC机器码发现确定的对齐缺陷：C++构建规则遗漏已有C的CC_XIPFLAGS，`Completion{}`被合并为对`Transport+0x26c`的未对齐64位store。SEC INF现显式追加`-mstrict-align`，不改传输策略、测试块、布局、watchdog或返回合同。是否解释这两轮手机无回传，尚待实机记录。
- 实际AArch64回归 `artifacts/ufs-alignment/20261102T012708Z/report.json`：M/C/I关闭、显式开启SCTLR.A。原编译触发EC0x25/DFSC0x21 alignment fault；strict编译正常完成。QEMU默认MMU-off RAM不强制同等检查，因此测试明确开启A，不能称为SM8150 Device内存模型。
- 完整SEC/DXE与恢复QEMU `artifacts/native-staging-qemu/20261102T012508.605058Z-07tqvn3h/report.json` 通过21项；手机候选 `evidence/private/android-return-build/20261102T012749.748332Z-1yomsloa` 完整构建通过，最终指令使用自然对齐访问。冻结对照 `artifacts/session-logs/20261102-ufs-write-strict-comparison.json` 只变更`Sec/Sec.inf`。

写入跨重启持久性、日志通道和通用可写Data仍须分别验证。原OS/SystemOS保持只读。


## 2026-11-02 UFS 持久写入通过；按用户要求停止

实机最终报告：`evidence/private/android-return-run/20261102T012856Z/report.json`。`passed=true`，nonce与恢复记录匹配、word30=63、WRITE10/FUA、SYNCHRONIZE CACHE10与立即读回通过；约71.528秒自动返回Android。随后普通重启、新boot ID、root和临时FDT清理通过，文件与原始LUN的12KiB三块读回一致，中间4KiB为新内容、两侧保护块未变。`runtime-only`未重读boot分区；本轮不执行XNU。此前两个无回传报告及人工恢复记录原样保留，不再重跑。

XNU新增正常线程上下文的内核接口 `IOReturn raphael_ufs_diagnostic_write(const void *policy, uint32_t bytes, uint64_t *stages)`。它复制8256字节策略到对齐的自有内存，在生命周期锁与IO锁内检查会话/容量/原内容及OS/SystemOS extent排除，执行同一单块写/同步/读回helper，撤销一次性写权限；错误将存储离线并按既有DMA隔离合同回收。不能在panic/IRQ上下文调用。没有自动启动调用、用户态入口或可写IOMedia。`raphael_ufs_write_probe_record[8]`以最后的release-store提交版本，快照解码区分未调用、未完成、立即读回与尚待重启证明。

该接口的最终完整模块archive（含190槽ABI绑定）为 `artifacts/raphael-ufs-object/20261102T014158.478920Z-p2029ayy/storage-bindings.json`，未链接进新的完整XNU/prelink，也没有原生写入实机执行。主机最终检查：真实UFS模型72项、进程重启后40项；只读extent/写排除32项；M/C/I关闭并显式SCTLR.A的原故障/修复对照；完整SEC/DXE与恢复QEMU21项；原生记录解码7项。共享策略移至SoC唯一源码并由固件Include相对链接引用。

接续必须先建立新的preimage/replacement政策。现有Android不可变项目文件已包含成功探针的新内容，旧 `write-policy.bin` 的原内容已过时；保留文件与保护块，不能重跑成功/无回传旧镜像。后续依次为：显式内核调用方与同轮native记录、跨重启读回、再实现有界持久日志的nonce/序号/CRC和刷盘时机。尚无专用日志分区、全部启动日志、通用可写UFS卷、持久APFS Data或桌面/交互完成证明。

按用户“写完正在做的事，更新交接，然后停止”的要求，到此停止；不自动启动下一轮实验。最终证据索引为 `UniXNU-raphael/evidence/native-ufs-write.json`。
