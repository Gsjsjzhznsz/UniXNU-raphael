# Redmi K20 Pro / UniXNU 开发交接报告

## 当前状态（2026-11-03 最新核对）

本次按用户要求同步上游main `3fa5ff5`及独立基带分支 `0ecc91f`，19/20子模块准确冻结；详情见 [GPU与基带同步报告](UPSTREAM-20261103.zh-CN.md)。当前手机后端f0721e9和打包后端c96b299保留，本轮没有新的手机实验或桌面/GPU/基带实机验收。

最新手机170735Z已结束：664.598秒未建立Android回连，`passed=false`、`xnu_executed=null`。用户实体电源恢复后，`evidence/private/android-manual-recovery/20261102T172400Z-display-client-return/report.json` 通过Android完成启动、root、新boot ID及无临时FDT属性核查；不是自动返回。163215Z仍为最近一次正常原生诊断成功：首次原watchdog方法和1次check-in通过，尚无持续心跳/桌面首帧。当前无运行中的手机实验或构建。

后续每完成一个小任务立即更新根 `TODO.md` 并同步 `D:/project/unixnu/todo.md`。首次方法后5秒候选仅为待办，尚未实现或上机。

## 以下接续记录为历史，保留当时措辞


修正状态标记的marker3候选已通过QEMU39项与手机镜像门禁，`evidence/private/android-return-run/20261102T170735Z/report.json` 临时启动已接受，目前原生回传与显示结果待定。固定原watchdogd只读指令审计显示监控循环使用10秒名义dispatch期限（`artifacts/session-logs/20261103-original-watchdogd-interval.json`）；这不是实机持续check-in证据，也未改变20秒硬件阈值或420秒绝对pet预算。


164851Z超时后，用户实体电源恢复。独立 `evidence/private/android-manual-recovery/20261102T170319Z-display-client/report.json` **passed=true**：Android新boot ID、root、临时FDT属性不存在；未取得匹配nonce，仍 `xnu_executed=null`，不能称自动返回或原生验收。现在仅对marker3修正候选继续QEMU/镜像门禁，通过后进行一轮临时启动。


2026-11-03 后续 `20261102T164851Z`：从163215Z成功基线仅将诊断停点移到原watchdog方法后的首个display client；164318Z完整887记录构建、164648Z QEMU39项通过，但手机665.674秒内没有Android回连或原生记录，**passed=false、xnu_executed=null**。用户先观察到本轮固件菜单，超时后确认全黑；电脑ADB/fastboot均无设备，正在等待实体电源恢复。保留镜像与失败报告，不原样重跑。

停点主机复查发现返回码初始0可能与尚未返回的newUserClient混淆，故旧marker2只能称“客户端进入”，不能宣称成功返回。源码现先记录NotReady再计进入、原调用返回后发布实际状态；新marker3明确区分。165046Z完整887记录内核与本地预链接/载荷已准备，**未上机**；后续依赖当前手机Android恢复与清理，不能自动继续启动。刚通过的163215Z首次原watchdog方法/check-in证据不受此未知轮影响。


2026-11-03 桌面主线接续：发现手机 ADT 缺少原用户态所需的显示子系统声明与逻辑缩放，现已在显式继承显示生成器补齐。`20261102T155924Z` 使用 `204217Z` 原冻结内核、512MiB、240秒/300秒合同，仅改这组无 MMIO/IRQ 的 OS 枚举输入，**整轮实机通过并463.187秒自动回 Android**；普通重启/root/临时属性清理通过。原显示 family/IOSurface/meta 与映射均正常，但 **clients/frames仍0**，没有桌面。

原task slide和UUID匹配共享缓存的只读符号化显示SpringBoard仍在 `_CFPREFERENCES_IS_WAITING_FOR_SYSTEM_AND_USER_CFPREFSDS`，快照未见backboardd。用户提供实拍是UniXNU固件菜单，只确认面板输出，不能当XNU停点或桌面。照片已保存在该run私有目录。

2026-11-03 显示枚举第二轮 `20261102T161209Z` 已结束：匹配 nonce 与 CRC 验证的恢复 globals 显示 **display clients=3**、family/surface/meta/client 状态0，原控制台证明 backboardd57 启动；validation/kick/frame/retired 仍0。捕获的首异常中未再见 SpringBoard 的 missing-main-CADisplay 断言，但这不证明它已就绪。原 watchdogd 缺失服务断言及第五次关键进程退出触发 `_proc_exit` panic，**passed=false、experiment_passed=false，正常 checkpoint 未通过**。520.653秒自动回Android，全屏恢复、普通重启/root/临时FDT清理通过；不能把独立恢复 globals 当作正常 checkpoint。

当前显式候选新增 `--watchdog-method-checkpoint`：保持 v4 的360秒物理观察上限/420秒绝对pet、20秒硬件阈值和原方法参数检查，在首次原 watchdogd externalMethod 完成后至少10poll提前收尾；解码分别标记 first-watchdog-method-complete 与完整观察到期，不将提前退出当360秒覆盖。默认构建不启用，原生写探针与此选项互斥。`162658Z` 完整887记录XNU构建与 `163031.517829Z-22bhcg7a` QEMU39项通过。手机run `20261102T163215Z` **整轮通过**：nonce/完整checkpoint/全屏恢复/Android清理成立，452.986秒自动回Android；原watchdogd首次selector0成功、3次方法调用、1次check-in、0失败/0首异常。1819poll、物理231300.639ms、437次pet后以 first-watchdog-method-complete 提前退出，不能当完整360秒观察。此时clients/frames0，SpringBoard仍等待原CFPrefs回复。摘要 `UniXNU-raphael/evidence/native-watchdog-client.json`。下一候选只将停点移到原方法完成后的首次显示client成功打开，构建中，尚未上机。不重复旧v34无回传镜像。用户更正本次附件属于上一轮菜单画面，不能归入此候选；当前屏幕未知。

源码索引 `UniXNU-raphael/evidence/native-display-enumeration.json`，说明 `UniXNU-raphael/docs/HANDSET-DISPLAY.zh-CN.md`。原生UFS写入成功与旧失败产物保留。

## 前次交接内容（历史记录原样保留）


2026-11-02 最新状态：用户重新授权原生 XNU 写入实机验证，现已整轮完成。**原生 XNU 单块 UFS 写入及跨普通重启持久性均通过**：`evidence/private/android-return-run/20261102T100353Z/report.json` 的 `passed=true`、`xnu_executed=true`、`native_ufs_write_verified=true`。本轮未启用 SEC 写探针，写入由正常内核观察线程显式调用 `raphael_ufs_diagnostic_write` 完成。

同轮匹配 nonce、完整原生检查点和恢复均通过：调用次数1、阶段63（原内容/WRITE10-FUA/同步/立即读回）、result/OCS0、权限已撤销；原 APFS 根仍只读。观察10poll、实际1402.405ms、喂狗3次；20秒硬件阈值、120秒观察上限/180秒绝对pet预算不变。205.900秒自动回 Android，再普通重启后新boot ID、root和临时FDT清理通过；Android文件与原始LUN的12KiB三块完全一致，中间4KiB为本轮新内容，两侧保护块未变。没有flash/erase、GPT修改或新分区；runtime-only未重读boot分区。

完整887记录XNU构建、预链接、最终内核唯一调用点与精确8256字节策略核对、恢复QEMU39项均通过。源码入口只在显式 `--native-ufs-write-policy` 私有诊断构建启用；默认配置不调用。第一次原生写探针094934Z已写入并跨重启保留，但约208ms即结束、仅一次pet，被原完整检查点至少两次pet的门禁拒绝；原失败报告保留，独立写入证明为其 `native-ufs-write-redecode.json`。第二轮只将收尾延至至少10poll并换用新分配策略，未放宽门禁。

**接续边界：** 这是本机单块原生写入证明，还不是连续启动日志、panic/IRQ日志、可写IOMedia或持久APFS Data。两轮测试块现均已变更，原preimage/镜像不能直接复跑；后续先建立新精确策略，再开发有界多块日志、启动ID/序号/CRC、刷盘与Android提取。可见桌面与基本交互仍未完成。当前无运行中的实验、构建或自动后续任务。证据索引：`UniXNU-raphael/evidence/native-ufs-write.json`；实施说明：`UniXNU-raphael/docs/HANDSET-UFS-WRITE.zh-CN.md`。

## 前一轮停止时的记录（历史，以下保留原文）
2026-11-02 最新状态：按用户要求在完成当前 UFS 接口并更新交接后停止。没有运行中的手机实验、构建或自动后续任务；最后一轮已自动回 Android，普通重启、root 与临时 FDT 属性清理完成。

**新增实机里程碑：SEC 单块 UFS 写入已跨普通重启保留。** `evidence/private/android-return-run/20261102T012856Z/report.json` 整轮通过：4096字节 WRITE10/FUA、同步缓存和立即读回完成；71.528秒自动回 Android。再普通重启后，Android文件与原始LUN读回均为新内容，两侧保护块未变。只授权一个12KiB新分配项目文件的中间4KiB；没有新分区、GPT修改、flash或erase。这不是原生XNU写入或持久APFS Data证明。

**当前源码收尾：** XNU存储模块已增加 `raphael_ufs_diagnostic_write`，原190-slot存储ABI编译、绑定和完整模块archive通过；默认没有调用方，没有生成或启动新的原生写入内核。接口按生命周期/IO锁串行执行，验证对齐复制的策略、实际容量和原内容，拒绝覆盖OS/SystemOS物理extent；WRITE10/FUA+同步+立即读回后撤销一次性权限，失败按原DMA隔离合同回收。新增运行记录解码保留“立即读回”与“跨重启”的区别。可见桌面与交互仍未完成。

源码/证据索引：`UniXNU-raphael/evidence/native-ufs-write.json`，实施与接续说明：`UniXNU-raphael/docs/HANDSET-UFS-WRITE.zh-CN.md`。下一次只有在用户重新要求继续后，才准备精确新preimage策略、接入显式内核调用方并做同轮原生记录/重启读回；本次不继续该实验。成功探针已经改变测试块，原镜像/原preimage不能直接复跑。持久启动日志的分配、nonce/序号/CRC、刷盘时机尚未实现。

2026-11-02 显示主线历史记录（后续已切换到UFS，v35未上机）：v33/223537Z 已完成匹配 nonce 的原生回传与普通重启/root/临时属性清理，505.165秒观察到 Android；原生检查未通过。服务 opens3/closes2、checkins0，无 externalMethod 入口记录。重新以原程序 BRK 和两级返回地址核对，v32/v33 均停在原 IOPMUPrimary=1 服务查找断言（原 PC0x10000b160），此前“selector0失败”的判断已更正。SpringBoard 首个异常已定位到 FBSDisplayMonitor 初始化。v34 仅在显式有界 watchdog 服务发布诊断用 numeric IOPMUPrimary 注册句柄，并验证原属性匹配；继承 setProperties 仍返回 Unsupported，不承认 PMU 硬件、boot-stage 或前台应用持久化。v34/225501Z 完整构建与原属性匹配 QEMU 通过，临时启动已接受，但664.258秒内未取得 Android USB 或原生回传，xnu_executed=null；用户确认全黑并强制重启；20261102T004239Z独立核查Android/root/新boot ID/临时属性清理通过，非自动返回。v35首次沿用冻结3600poll内核被手机构建预算门禁拒绝、未上机；现同步收短为1200poll并重建，独立ADT采用既有version2的120秒物理观察/180秒绝对pet预算，方法检查与20秒硬件不变；待主机和同轮实机验证，不原样重跑v34。20秒硬件与360秒观察/420秒绝对预算不变。最新正常 checkpoint 仍204217Z；display clients/frames0，桌面和交互未完成。

最新更新：2026-11-02，Asia/Shanghai。产物目录名以 UTC `Z` 记时；`20261101T190907Z` 是北京时间 2026-11-02 03:09:07。文件名保留以兼容已有引用。

**主线仍未完成。以下190907Z为历史Data里程碑：原APFS根与SystemOS、原launchd main、独立可写易失APFS Data均有同轮证据；原控制台记录 Early boot complete，并观察到SpringBoard PID26及多个系统服务。尚无手机桌面画面或基本交互证据。**

Data stage4/status0/readonly0；226项原var初始化、611715字节写入与读回一致；稀疏RamBlock逻辑1GiB，实际驻留1437696字节、130次写入、失败0。原内核真实512MiB，240052.549ms有界观察结束，PID1累计6677次syscall，53个签名对象，UFS3215979520字节且失败0。442.754秒自动回Android，nonce、完整checkpoint、八段恢复、正常重启/root及临时属性清理均通过。无flash/erase；runtime-only未重读boot分区。Data仅在RAM，原OS/SystemOS UFS仍只读。

当前继续构建显式handset-display候选：只在已验证的Data/512MiB/240秒合同上接入原IOMobileGraphicsFamily/IOSurface适配器，精确ADT opt-in；沿用同次继承framebuffer与完整画面备份恢复。192545Z完整887编译记录和预链接通过；staging QEMU39项、另193342Z显式启用分支39项通过（原family/IOSurface/metaclass均0、headless零帧）。193023Z手机整轮及清理已通过，详细最新结果见本文顶部。未改keystore或面板MMIO策略。旧v21编排已完成，不能重启。

上一轮185720Z证明512MiB分配和恢复，但由tzinit PID17 exit30触发原proc_exit panic，整轮失败保留；182935Z同样已证明原launchd main，不是PID1退出。190907Z可写var后已越过这处panic并完成early boot。

公开摘要：[可写易失Data](../UniXNU-raphael/evidence/native-ephemeral-data.json)、[Data合同](../UniXNU-raphael/docs/HANDSET-DATA.zh-CN.md)。完整报告为`evidence/private/android-return-run/20261101T190907Z/report.json`；原始控制台`recovered-msgbuf.txt`；主机追加解码`normal-checkpoint-redecode.json`，原报告保留未覆盖。

2026-11-02 打包规范追加：已原样接入官方 `templates/package.sh`，补齐 package/defconfig 映射、设备和工作区的手动 macOS 工作流、私有 build 输入示例及 packaging 记录。21 项本地检查通过，默认/17/完整配置名均解析同一 62 个补丁；完整镜像配方仍缺 8 个字段，尚未生成新镜像、未运行远端 CI、没有新增实机证据。已按本会话用户要求完成一次上游拉取：独立候选为 `c96b29975645b711dc06bc435c3ad27321ce817c`，本机另设 `sources/UniXNU-packaging` 供打包入口使用；实机 backend `sources/UniXNU` 保持原 pin。详情见第 12 节及[打包说明](../UniXNU-raphael/docs/PACKAGING.zh-CN.md)。

2026-11-01 仓库规范整改追加：板级驱动和UEFI已归入 `UniXNU-raphael/package/`，共享平台源码移至 `UniXNU-sm8150-common/kits/Sm8150Platform/`；当前源码表已更新，历史冻结路径保持原样。已补13区 `porting.toml`、规范DTS/config、私有输入清单、设备/工作区CI及本地检查入口。887记录CPU诊断内核、固件QEMU及UFS/显示对象回归通过，没有新实机结果；发布/完整源码commit/生产recipe仍待完成。详见[规范整改说明](../UniXNU-raphael/docs/REPOSITORY-COMPLIANCE.zh-CN.md)。

## 1. 接手后先看这些信息

| 项目 | 当前状态 |
|---|---|
| 活动仓库 | WSL `Ubuntu-24.04` 的 `/home/guo/work/raphael-fresh` |
| Windows 交接副本 | `D:\project\unixnu\HANDOFF-20261101.zh-CN.md`；此目录不是活动 Git 工作树 |
| 工具链 | `/opt/unixnu-linux`；已有完整 XNU、UEFI 构建证据 |
| ADB / fastboot | `D:\Android\platform-tools`；WSL 可用 `/mnt/d/Android/platform-tools/adb.exe` |
| 手机最近一次核查 | 163215Z首次原watchdog方法/check-in整轮通过；452.986秒自动Android，全屏恢复、普通重启/root/临时FDT清理通过 |
| 运行中任务 | 当前无手机实验或构建；170735Z超时，172400Z人工恢复核查通过；最新上游已独立同步 |
| 最新成功实机 | `evidence/private/android-return-run/20261102T163215Z/report.json`；155924Z完整240秒通过，161209Z独立globals见3clients但原panic拒收 |
| 最深实机能力 | 同轮APFS root/SystemOS、原launchd main/early boot、可写易失Data；SpringBoard26已启动，尚无桌面画面 |
| 当前阻塞 | 首次watchdog方法和check-in已通过，持续心跳及原cfprefsd/backboardd/显示提交尚待后续；桌面与输入未完成 |
| 活动源码窗口 | 默认源码仍1200poll；显式watchdog checkpoint为3600poll/360秒物理观察上限、420秒绝对pet、20秒硬件。163215Z提前止于231.301秒；QEMU为40秒rootless夹具 |
| 上游更新 | 本会话用户要求的一次拉取完成：`artifacts/upstream-candidates/20261101T144956Z/UniXNU`，提交 `c96b299`，19 个子模块；实机 backend 未覆盖，不重复自动 fetch |
| 打包入口 | `UniXNU-raphael/scripts/package.sh` 使用独立 `sources/UniXNU-packaging`；21 项本地检查/62 补丁解析通过，完整镜像构建未完成 |
| Git 工作区 | 大量 dirty/untracked，必须保留；HEAD 不能重建当前进度 |
| 原备份 | `D:\PhoneBackups\raphael\2026-10-27`，不删除或覆盖；非完整备份，未验证恢复 |

2026-11-01 12:36 的只读状态及当时修改前的两份交接文档保存在 `evidence/private/handoff/20261101T043630Z-desktop-progress`，现场详细输出为其 `state.json`。设备标识与原始 ADB 输出仅保存在私有目录。初版快照 `evidence/private/handoff/20261031T172508Z/state.json` 仍保留，但不代表当前进度。

## 2. 目标验收与距离桌面的实际位置

| 层级 | 验收条件 | 当前结论 |
|---|---|---|
| 首次真实桌面 | 本机目标 OS 的桌面进程生成真实画面并保持至少 60 秒，排除预制图片、UEFI 菜单和启动进度条 | 未达到 |
| 基本可操作 | 在上述基础上有目标 OS 输入，可打开/退出基本应用并连续操作 10 分钟；触摸与外接输入分别记录，需要可写 Data 与必要服务 | 未达到 |
| GPU 与外设完善 | A640 提交、完成/fence、渲染、呈现闭环，以及触摸、USB、电源、休眠、声音、网络等 | 未达到，逐项独立验收 |

目前处于 **“原launchd early boot已完成、可写易失Data与服务启动成立，正在接入本机原系统显示”**。存储与根挂载不再是零进度，但其长期稳定性、较大读请求、服务就绪、持久Data、持续显示与输入仍有工作。不能给可靠完成百分比或桌面 ETA；诊断次数、编译成功和 QEMU 帧数不能换算为剩余时间。

## 3. 源码版本和已完成的上游同步

### 3.1 活动版本与脏修改

| 来源 | 活动提交 / 基线 | 本次核查 |
|---|---|---|
| 根仓库 | `14d0e6ad84f5950411e687b01868fba8647c9609` | 2026-11-02 本次修改前 porcelain 有 228 个非 `??` 条目、221 个 `??` 条目；包含目录项，不是精确文件数；未提交改动继续保留 |
| `sources/UniXNU` | `f0721e9745c45ad2600cd69c74730f1cca55d56a` | 实机 backend 未迁移；打包验证时源码 diff 为空，子模块内未跟踪缓存仍保留 |
| `sources/UniXNU-packaging` | `c96b29975645b711dc06bc435c3ad27321ce817c` | 从本次已拉取候选本地复制的打包运行库；入口/预检查已验证，完整 kernel/firmware/payload 构建未验证 |
| `sources/mu_basecore` | `cfb93724a06ff86ff5ba971413368a7809ee42a5` | 干净 |
| `sources/apple-xnu-native` | `d8b80295118ef25ac3a784134bcf95cd8e88109f`，`xnu-10063.141.1` | 原始仓库干净；实际补丁/编译树在 artifacts |
| DarwinBoot | `3325e352d7df68a9f9ad74832ed94a6acbbd7390` | 有 `Test/__pycache__/` |
| VerifiedRoot | `def026642c6c6e71be0dea267d989df1d29ddc64` | 有 `tools/__pycache__/` |
| Xiaomi 固定内核资料 | `663db50e195a8a54c8565ac4ab0c6d9ba7d80db0` | 来源 pin 在 `sources.lock.json` |

继续使用 **iPadOS 17.7.11 (21H461)、Darwin 23.6 ABI**。`ipados27` 候选分支名称不等于已经切换系统。保留 dirty、untracked、冻结内核、编译记录和失败产物；不运行 reset/clean 或递归子模块重置。

### 3.2 此前同步记录（历史候选）

此前记录：`docs/upstream-refresh-20261101-235342Z.json`；独立目录 `artifacts/upstream-candidates/20261031T235342Z`，当时取得 19 个依赖 pin。此条已不是最近一次拉取，当前记录见 3.3。活动 `sources/UniXNU` 仍为上表版本。

| 项目 | 该次历史候选提交 | 状态 |
|---|---|---|
| UniXNU main | `407db1aefd4e4e50a944fcda73442bde566dbce1` | 独立候选；VerifiedRoot、XnuPrelink、DarwinBoot 的新接口尚未整体合入手机主线 |
| Adreno740 GPU parity | `10ac0eaa0ad8f24426da85d3570026081dc50bc5` | 候选源码；不是 A640 本机驱动证明 |
| AdrenoMetal GPU parity | `a0a34fa2588efa982edc890980a27dbb4efff732` | 候选源码；未验证本机 ABI/渲染 |
| GopFramebuffer GPU parity | `74ff4c4165c0d84bbca82b1ec732677d2d62a98b` | 相对此前候选未变；无此版本手机桌面证据 |

较早一次同步仍在 `artifacts/upstream-candidates/20261031T163925Z`，记录 `docs/upstream-refresh-20261101.json`；它不再是最近一次拉取。后续不要把重复下载当作推进，也不要直接用新主干覆盖本地适配。

### 3.3 本会话授权的最近一次拉取与独立打包运行库

记录：`docs/upstream-refresh-20261101T144956Z.json`，`passed=true`。候选目录 `artifacts/upstream-candidates/20261101T144956Z/UniXNU`，提交 `c96b29975645b711dc06bc435c3ad27321ce817c`，19 个锁定子模块均已取得。目录 UTC 时间 `20261101T144956Z` 对应北京时间 **2026-11-01 22:49:56**；打包接入和预检查跨至 **2026-11-02**，不能混用日期。

`board.toml` 的 `[package] unixnu` 指向独立 `../sources/UniXNU-packaging`。该运行库从上述候选本地复制，不再次联网；`unixnu_repository` 和 `unixnu_revision` 明确记录来源与完整 pin。`UniXNU-raphael/scripts/package.sh` 与该提交的 `templates/package.sh` 逐字节一致。实机 `sources/UniXNU`、Apple XNU pin、私有系统盘、成功和失败冻结产物均保留。

本次采用的是新打包入口和预检查接口，**不是将 c96b299 全部驱动/内核变更迁入实机主线**。两个运行库不可混称；新的 `--check` 成功仅证明配置/组件/补丁路径解析，不能冒充完整编译或手机启动。先前 reference clone 遇到 `unresolved deltas` 的失败目录 `artifacts/upstream-candidates/20261101T144743Z` 保留；随后独立浅克隆成功，没有用失败产物覆盖原源码。

## 4. 硬件来源与当前实验布局

硬件输入来自本机 live FDT、入口观测及固定 Xiaomi 资料。完整历史依据在 `docs/HARDWARE.zh-CN.md` 与 `UniXNU-raphael/evidence/`；不导入其他 raphael 移植包或其他板地址。

| 项目 | 当前依据 / 范围 |
|---|---|
| 设备 | Redmi K20 Pro / raphael，SM8150，SoC ID339/revision2.2 |
| Android 返回内核 | 采集时为 `4.14.253-Marisa-r14`；原厂 MIUI 包不是自动返回时使用的当前内核 |
| 入口 | EL1，Image `0x80080000`，CNTFRQ 19200000Hz；x0/FDT/SP 是每轮观测，不能当固定分配区 |
| GIC / timer | GICD `0x17a00000/0x10000`，GICR `0x17a60000/0x100000`，本机 physical timer INTID18；已有真实 IRQ/EOI 与调度证据 |
| 启动显示 | 继承 1080×2340、stride4320、BGRA32、buffer `0x9c000000`；UEFI GOP/可见菜单成立，目标 OS 持续显示未验证 |
| 实体按键 | 本机 SPMI/PMIC + UEFI SimpleTextIn；不是目标 OS 触摸/HID |
| UFS | `/soc/ufshc@1d84000`，长度9472；LUN0 Samsung KLUEG8U1EA-B0C1，60884992×4096 字节；常驻只读请求已有实机证据 |
| 看门狗 | `0x17c10000/0x1000`，配置32765Hz、硬件20秒；旧 `0x17be0000` 转写错误不可复用 |
| RAM | 初始 FDT 与 Linux RAM 量、保留区和隐藏 DMA 所有权分别处理；当前实验 grant 不是全 RAM 授权 |
| 触摸 | Android goodix_ts，固定本机 DTS 为 GT9889；Darwin 触摸/HID 尚未实现 |

### 4.1 历史041841Z成功实机使用的布局

冻结依据：`evidence/private/android-return-build/20261101T041809.698335Z-hktbyhsd/report.json`。**当前不是初版 72MiB arena / 20MiB FAT 的单块 stage3 镜像。**

| 区域 | 基址 | 大小 / 范围 |
|---|---|---|
| 诊断 Image 头 | `0x80080000` | `0x10000` |
| context / extent 起点 | `0x80090000` | 按构建记录分段使用 |
| FD | `0x800a0000` | 24MiB |
| SEC 栈 | `0x818a0000` | 256KiB |
| kernel window | `0xc0000000` | 256MiB 实验 grant，另有显式对齐预算与 guard |
| DXE arena | `0xd0400000` | 320MiB |
| FDT 副本 | `0xe4400000` | 2MiB |
| 载荷 FAT | arena 内按冻结报告保留 | 128MiB，由手机不可变 Payload 文件读取 |
| OS 预链接内核 | FAT 内 | 124444672 字节，15 个装载段 |

`ExtentEnd=0xe4600000`。布局跨度不是整段空洞都可读写的授权；不要简单提高 grant、覆盖 input hole、返回区或 FDT。最新成功 run 的构建与当前 500-poll 源码不同，以冻结目录为准。

## 5. 实机进度与精确证据

### 5.1 最新成功实机：20261101T041841Z

| 项目 | 同轮已验证的事实 |
|---|---|
| 总结果 | `passed=true`、`experiment_passed=true`、`xnu_executed=true` |
| 根卷 | APFS `disk1s1`，`apfs_root_mounted_verified=true`、owner_accepted1、readonly1 |
| SystemOS | stage6/status0/authorized1/mount_status0/readonly1/native_union1/root_recheck1 |
| PID1 | 原 `/sbin/launchd` exec error0，process_name=launchd，真实 EL0 syscall 已记录；开发版 launchd 路径 ENOENT 是前一探测，不是原 launchd 不存在 |
| 最新进展 | 22 次 Unix syscall，最新 syscall92/fcntl、command97 `F_ADDFILESIGS_RETURN`；采样栈在真实存储读取路径 |
| UFS 常驻服务 | 终止诊断前在线，2159 次上层读取、30929920 字节、硬件失败0 |
| 终止行为 | 主动诊断中断大读1次，随后完成 DMA/控制器交还；末尾 fcntl errno16 是终止诊断引起，不能据此判独立启动故障 |
| 有界喂狗 | 硬件阈值仍20秒，最大刷新预算60000ms，至少500ms间隔；25次 pet，terminal status2 |
| 观察时长 | 100 polls 的名义10秒；物理 counter 计算实际约 13.142101 秒，不能当精确10秒 |
| 恢复 | 209.504 秒自动回 Android，新 boot ID/root 及普通重启后临时属性清理通过 |
| 尚未证明 | dyld 完成、launchd main、服务就绪、SpringBoard、持续用户态帧、可写 Data、桌面操作 |

冻结证据链：

- 原生构建/结构检查来源见 `artifacts/session-logs/20261101-pid1-pet10-v3-build.py` 及相应日志。
- 预链接与 inspection：`artifacts/desktop-prelink/20261101T041703Z/report.json`、`artifacts/desktop-prelink/20261101T041703Z/inspection.json`。
- QEMU：`artifacts/native-staging-qemu/20261101T041725.976494Z-verjeof8/report.json`，39 项通过；无手机 MMIO/系统盘运行证明。
- 手机构建：`evidence/private/android-return-build/20261101T041809.698335Z-hktbyhsd/report.json`。
- 实机：`evidence/private/android-return-run/20261101T041841Z/report.json`。
- 看门狗索引：`UniXNU-raphael/evidence/native-watchdog-budget.json`。

根认证边界仍明确：Apple 原认证 `owner_apple_autherr=80`，最终使用已启用的所有者签名与只读逐块认证策略；这不是 Apple 原厂封印认证成功。TrustCache 为原记录 61356 字节/2554 条，未增加 owner cdhash；也不能宣称完整 Apple 签名链认证成功。

`storage.online=0` 是终止诊断后的状态；`diagnostic_online_before=1` 和同轮实际请求量证明诊断前服务在线，不要把终止后零值误判为驱动从未运行。

### 5.2 关键阶段的先后关系

以下每行独立依据自己的冻结实机报告，不把它们合成一次完整启动。

| UTC run | 结果与变化 |
|---|---|
| `20261031T180012Z` / `20261031T180840Z` | OS / SystemOS 各16轮、128次真实物理读取，首尾/跨块/extent样本一致，恢复清理通过 |
| `20261031T194037Z` / `20261031T194529Z` | 分别证明128MiB载荷认证读取、15段真实OS内核装载；不是桌面 |
| `20261101T003353Z` | 常驻 UFS start_stage4、online_before1；此轮上层requests0 |
| `20261101T010035Z` | 首次 APFS root 挂载，186次/734208字节，零失败；详见 `UniXNU-raphael/evidence/native-apfs-root.json` |
| `20261101T014449Z` / `20261101T015623Z` | SystemOS组合挂载成功，但exec安全策略拒绝、主动panic；不能标整轮成功 |
| `20261101T020626Z` | 补齐原 TrustCache 后原 launchd exec/EL0通过，最初3次Unix syscall |
| `20261101T022035Z` | shared_region_check_np 返回 ENOMEM12 是空共享区探测；不是全局内存耗尽证明 |
| `20261101T023001Z` | copyin遇PAN权限异常循环，约495万次；已有精确ESR/PC/FAR |
| `20261101T024411Z` | handset profile启用既有PAN支持后循环消失，推进到22次syscall；173次同步异常、6次内核VM fault；1827次/25564160字节读取零失败 |
| `20261101T025627Z` | 回Android但nonce不匹配、无原生回传，xnu_executed=null；保留失败，不推断复位原因 |
| `20261101T030853Z` | 大读可在终止诊断的已认证16KiB chunk边界退出，5.018ms交还DMA；2141次/30647296字节、硬件失败0 |
| `20261101T032441Z` / `20261101T033532Z` / `20261101T034425Z` | 90/60秒硬件阈值严格读回失败，均在XNU前拒绝；Android恢复/清理通过，不能标XNU执行 |
| `20261101T040501Z` | 新喂狗计时汇编缺MRS导致record异常，整轮failed；原生checkpoint与恢复返回，不追认计时成功 |
| `20261101T041841Z` | 修正真实MRS并审计最终指令，100-poll窗口25次pet及全轮恢复通过；当前最新成功 |

以上实机报告均位于 `evidence/private/android-return-run/` 下对应 run 的 `report.json`。PAN与PID1详细索引为 `UniXNU-raphael/evidence/native-pid1-pan.json`、`UniXNU-raphael/evidence/native-pid1-el0.json`、`UniXNU-raphael/evidence/native-pid1-service-window.json`。索引中的 next 字段可能是旧轮次计划，以本交接当前阻塞与原报告为准。

### 5.3 历史单块 UFS 成功链（已被后续系统盘与用户态进度超越）

| 环节 | 冻结路径 | 结果 |
|---|---|---|
| 本机重新采集文件/extent/LUN参考 | `evidence/private/ufs-readonly/20261031T170219Z/read-source.json` | passed；4096字节、无fscrypt policy、FIEMAP前后稳定、原始LUN读与文件全等 |
| QEMU门禁 | `artifacts/native-staging-qemu/20261031T170320.681591Z-pk1nez4d/report.json` | passed；看门狗mapping fixture、uncached切换/返回合同；不访问手机MMIO |
| 主机手机镜像构建 | `evidence/private/android-return-build/20261031T170606.664993Z-nuw1p97a/report.json` | passed、结构检查通过；构建报告的handset_executed=false只描述构建阶段 |
| 实机启动与读块 | `evidence/private/android-return-run/20261031T170816Z/report.json` | passed、nonce/stage3匹配，READ10成功、4096字节全等 |
| Android返回和清理 | 同一170816Z报告 | 71.479561秒自动回Android；新boot ID、root及普通重启后临时属性清理通过 |

本机文件：`/data/unixnu-raphael-stage-20261030T235925Z/probe.bin`。

- userdata 挂载别名解析为 `/dev/block/sda31`；分区起始4063232×512字节。
- FIEMAP物理偏移215287345152（相对分区），长度4096。
- 对应LUN0字节偏移217367719936，即4096字节块LBA53068291。
- 该LBA是**这次文件extent的冻结快照**，不是板级硬件常量，文件重建/移动后必须重新采集。
- 命令INQUIRY、TUR、CAPACITY16、READ10，OCS、容量与Android比对、自有DMA、SMMU无活动转换、其他CPU关闭、控制器/看门狗恢复均通过。
- 该历史单块实验 `xnu_executed=null`；该短路径没有XNU执行证明，不能用它更新最深XNU停点。
- `ufs_handoff.native_dma_verified=false`是只读入口快照的范围声明；真正读操作在`ufs_read.native_dma_verified=true`，不要把两个字段混读成矛盾。
- 只读采集文件`read-source.json`当时的`handset_native_read_verified=false`保留原状；后续170816Z是新增的实机证明，不改写旧采集事实。

首块成功另见 `evidence/private/android-return-run/20261031T165548Z/report.json`，70.207742秒回Android。两次都是单块测试，未读取OS卷、没有持久写入。

该历史单块镜像：`evidence/private/android-return-build/20261031T170606.664993Z-nuw1p97a/boot-android-return.img`，134217728字节。报告已记录SHA256 `a90403a0209af32b76000bc651bbd7848e829c3be7b331825d48554a11b5a02a`。这里只转录既有标识，不重新执行整盘或备份哈希审计。probe参考摘要及各源码/产物摘要见原报告。

### 5.4 能力状态总表

| 能力 | 状态 | 当前边界 |
|---|---|---|
| SEC/DXE、DarwinBoot、Android返回 | 本机已验证 | 显式有界诊断与恢复；不是日用固件 |
| GOP与可见菜单、实体三键 | 本机已验证 | UEFI继承模式；不能代替OS帧或触摸 |
| 原XNU、pmap、CPU/timer、BSD调度 | 本机已验证 | 已推进至原用户态的有界执行；长期持续系统另验 |
| OS/SystemOS不可变extent与只读块接口 | 本机已验证 | 已真实供给挂载与PID1读盘；写入、长期压力与并发另验 |
| 128MiB FAT及约124MB系统内核载荷 | 本机已验证 | 成功装载/执行；256MiB kernel grant仍是实验限制 |
| APFS根卷、SystemOS组合挂载 | 本机已验证 | 只读owner策略；不是Apple封印验证成功 |
| 原launchd exec与EL0 | 本机已验证 | 22次Unix syscall；main及服务就绪尚未验证 |
| 有界喂狗 | 本机已验证（100-poll窗口） | 20秒硬件阈值、60秒最大刷新预算；长窗口尚未通过 |
| dyld完成与launchd主函数 | 尚需开发/定位 | 当前在fcntl文件签名相关的读盘路径；未证明永久卡死 |
| 可写Data及服务启动 | 尚需开发 | QEMU scratch Data不能冒充手机支持 |
| 持续桌面画面与合成 | 上游可复用但本机未验证 | QEMU旧进度条与GOP菜单都不是手机桌面 |
| 目标OS输入/HID与A640 GPU/外设 | 尚需开发 | GT9889、A640需本机独立实现/验收 |

## 6. 实现、修复及保留的失败记录

### 6.1 stage3 UFS看门狗映射门禁

冻结旧候选161936Z的PCD组合是UfsRead=1、NativeWatchdogBase=`0x17c10000`、NativeMmuTest=0。原SEC只在NativeMmuTest允许看门狗映射，导致此组合在Android返回胶囊准备前必然`SecFinish(0x23e)`。

已修正为明确允许 AndroidReturn + UfsRead + StopStage3 的配置，仍要求本机FDT资源匹配。新增QEMU `--ufs-watchdog-map-fixture`，合成地址`0x0b000000`仅验证映射分支；该值不得用于手机。手机stage3构建现在必须取得`ufs_watchdog_mapping_verified=true`的QEMU报告。

不能据此追认所有早期无记录失败都执行过UFS或都死于这个门禁。

### 6.2 uncached回调后的旧cache line

164138Z实机UFS查询完成，但回传inside=0、callback=0，整轮严格失败。原进入前清cache时，后续range table访问可能重填干净旧cache line；uncached更新完成后直接恢复缓存可再次看到旧内容。

已在`UfsUncached.S`中于M/C关闭时对同样三个owned ranges执行DC IVAC、DSB后再恢复SCTLR；不用可能把旧数据写回的新一轮CIVAC。增加CTR line<=4096门禁，不改变TTBR/TCR/MAIR/DAIF或扩大内存授权。

164737Z及后续成功报告确认before12589069、inside12584968（before & ~0x1005）、after等于before、callback1。QEMU只测切换合同，不模拟本机真实缓存一致性。

### 6.3 返回Android后的清理判断

`run_android_return_handset.py`现在在缺少记录/解码异常后仍执行清理；缺证据保持unknown。普通`adb reboot`返回超时也继续采集恢复状态。清理必须等待与回到Android之后的旧boot ID不同的新ID，不能把旧Android的`sys.boot_completed=1`当成重启成功。

- 164737Z实验通过，但原清理命令超时；原失败状态不抹去。
- 165044Z重放采集仍见旧boot，严格判清理未通过。
- `165044Z/delayed-cleanup-report.json`后来独立确认普通重启完成、新ID/root/临时属性清除。
- 准备过`android_sync_reboot.c`及`artifacts/android-sync-reboot/reboot-helper`，但ADB push失败，**未上传、未执行强制重启helper**。
- 随后的165548Z、170816Z完整实验与新ID清理通过；当前最新结果另见5.1。

### 6.4 显式LBA与诊断wire

新增UINT64 `PcdRaphaelUfsReadLba`，token0x99，默认0，贯穿DEC、DSC、SEC INF、C/C++接口和构建/QEMU/解码脚本。CLI为`--ufs-read-lba`。

UFS wire保持4392字节（32Q+40+4096），版本2将Word29编码为`(Lba << 8) | CDB`；主机兼容版本1，旧报告已重放验证。非零LBA构建必须有成功`read-source.json`，核对无加密、稳定extent、地址及参考内容。

任何扩展都继续守住`sizeof(RAPHAEL_DIAGNOSTIC) <= 0xf000`；不能为塞更多观测而破坏FDT记录预算。

### 6.5 IOKit时间初始化判断的更正

实际冻结手机Mach-O中`_IOKitInitializeTime`地址`0xfffffff0078f1a94`，首指令`0x17e6463e`直接分支到`_clock_initialize_calendar`（`0xfffffff00728338c`）。这个函数中没有此前推测的30秒IORTC等待。记录：`UniXNU-raphael/evidence/native-iokit-time-linked.json`。

初次调查未找到对应compile record；当时空`llvm-nm.log`也不能证明符号不存在。后续不要继续围绕“未去掉30秒等待”安排实验，亦不从BCM2837目录名推定本机配置。

### 6.6 早期保留的失败和未知

| 记录 | 可确认的结果 | 不能声称 |
|---|---|---|
| 004718Z提前准备返回胶囊候选 | 未回USB、人工恢复；该API随后限制QEMU-only | 不能说自动恢复可靠 |
| 162556Z及更早若干无nonce/SEC记录轮次 | 手机回Android或后续人工恢复，但停点未知 | 不能判定XNU/UFS已经运行或具体复位原因 |
| 164138Z查询轮 | 查询完成但cache回传矛盾，整轮failed | 不能因大部分门禁通过改为成功 |
| READ16历史轮 | 有效SCSI错误、OCS0，旧wire未保留sense | 不能断言本机不支持READ16或给定唯一原因 |
| 旧QEMU桌面长跑 | 真实显示帧持续变化，仍为启动进度条 | 不能验收桌面，也不能把等待采样一律判成死锁 |

相同无记录镜像不原样重跑；先分析实际改变和可解释的正负结果。没有外部串口不是所有实验的绝对禁令，但没有可读结果也不能自动升级成硬件进展。

### 6.7 本轮 PID1、存储终止和有界喂狗的改动

| 源码位置 | 当前实现与必要注意事项 |
|---|---|
| `UniXNU-raphael/configs/raphael_handset_storage_defconfig` | 启用既有 `CONFIG_XNU_NATIVE_PAN=y`，最终copyin/copyout成对PAN指令已有核查及实机对照 |
| `UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelUfsBlock.cpp` | 常驻控制器与两只读卷；终止诊断先发布shutdown，在已验签16KiB chunk边界中止大读，保留实际bytes与DMA交还门禁 |
| `UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelDiagnosticWatchdog.h` | 可独立host测试的有界刷新状态机：20秒硬件配置、500ms最小间隔、60000ms物理计数器绝对到期、stop后不pet、不能restart |
| `UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelDiagnosticWatchdog.cpp` | 仅diagnostic archive；从 `/cpus/cpu0` 的gIODTPlane读取显式合同，uncached MMIO映射；该发现路径已在实机成功，不要凭猜测更换 |
| `UniXNU-raphael/scripts/build-raphael-cpu.py` | 链接新diagnostic对象，冻结源码与反汇编，要求最终ARM64对象至少三处 `CNTPCT_EL0`，覆盖begin/pet/end |
| `UniXNU-raphael/patches/xnu/raphael-service-window.patch` | observer循环前begin、每poll pet、结束end；当前源码limit500，冻结成功内核limit100 |
| `scripts/native_watchdog_budget.py` | 生成/解码/资格核查；CPU0属性 `unixnu,diagnostic-watchdog` 为6Q：version1、base398524416、bytes4096、frequency32765、seconds20、budget_ms60000 |
| `scripts/native_early.py` | 从真实Mach-O取observer limit并解码watchdog record；显式预算存在时必须有有效record，核对物理计数顺序、至少两次pet与terminal status2 |
| `scripts/build_sec_dxe.py` | 长观察只接受显式同机qualified合同与watchdog_record符号，核对名义observer_ms+5000<=60000；这条名义检查尚不足以覆盖实际调度延迟 |
| `scripts/prepare_handset_payload.py` | 对已验证ADT只放行精确qualified watchdog合同等明确允许差异，其他硬件属性逐项一致 |
| `scripts/build_native_staging_handset.py`、`scripts/run_native_staging_qemu.py`、`UniXNU-raphael/package/firmware/RaphaelPkg/Drivers/DiagnosticReturnDxe/NativeWatchdog.c` | watchdog阈值当前只允许20秒；日志保留requested/readback/saved，不能猜更大硬件阈值 |

有效喂狗ADT：`evidence/private/handset-storage-adt/20261101T040328Z-watchdog-budget/kernel.macho.adt`，附同目录 provenance。早先 `handset-watchdog-adt/` 下的候选被payload路径门禁拒绝，不能替代有效路径。

关键失败与修复：Darwin内联汇编中的 `isb; mrs ...` 最终只生成ISB，计数记录成高VA；040501Z status3/pets1。改成真实换行分隔 `isb` 和 `mrs %0,cntpct_el0`，增加实际指令审计后，041841Z通过。不要误诊成CPU0属性发现失败，也不要部署基于缺MRS内核的 `pet50-v3`。

硬件阈值失败有实测读回：90秒requested2948850/2981615、readback851698/884463，差2×2^20；60秒requested1965900/1998665、readback917324/950089，差2^20。当前实验只沿用已验证20秒655300/688065，不禁用watchdog，不继续猜阈值。刷新线程卡住或到60000ms时停止pet，硬件仍提供最终复位保护；原返回路径恢复寄存器。

主机验证：`artifacts/session-logs/20261101-diagnostic-watchdog-host.json` 为g++ ASan/UBSan状态机测试；`artifacts/session-logs/20261101-diagnostic-watchdog-adt-host.json` 为9项ADT资格检查。clang++-18 sanitizer runtime缺失的首次失败保留，后用已有g++通过，没有为此安装依赖。`RaphaelBootCpu.cpp` 其他分号汇编写法尚未在本轮修正，须后续独立核查，不混入长窗口单变量实验。

## 7. 系统材料、载荷与 QEMU 当前状态

### 7.1 OS/SystemOS 已在手机，不要重传或重新做整盘哈希

来源为原17.7.11 (21H461) OS材料。Apple树只提供OS ABI/身份输入，不是SM8150硬件树。

| 材料 | 冻结路径 / 状态 |
|---|---|
| 主机OS原盘 | `artifacts/desktop-disks/20261030T075713Z/OS.raw`，6077580800字节，APFS offset17408 |
| 主机SystemOS原盘 | 同目录 `SystemOS.raw`，3303014400字节，APFS offset0 |
| 手机不可变原盘 | `/data/unixnu-raphael-system-20261031T174325Z/` 下OS.raw/SystemOS.raw；完整校验早已通过，分别66/27个extent |
| 原盘stage报告 | `evidence/private/handset-system-disks/20261031T174325Z/report.json` |
| OS extent策略 | `evidence/private/ufs-readonly/20261031T175351Z/extent-policy.bin` |
| SystemOS extent策略 | `evidence/private/ufs-readonly/20261031T180246Z/extent-policy.bin` |
| owner-root策略 | `evidence/private/desktop-root-policy/20261030T081351Z/report.json`，私钥只保留私有目录 |
| 原TrustCache索引 | `artifacts/desktop-trust/20261030T081913Z/report.json`，61356字节/2554条 |
| 已验证外置载荷容量基线 | `evidence/private/android-return-run/20261031T194529Z/report.json` |

后续复用原盘和extent，保留每次启动前已有size/FIEMAP/immutable预检。文件移动/改写会使extent失效，不能把旧probe LBA硬编码为系统盘地址。逐块内容认证是读取路径自身的要求，不等于需要重复整盘/备份SHA审计。

### 7.2 最新 500-poll 候选：准备完成，QEMU失败，未上手机

编排脚本为 `artifacts/session-logs/20261101-pid1-pet50-v4-mainline.py`，构建脚本为 `artifacts/session-logs/20261101-pid1-pet50-v4-build.py`。构建与mainline进程均已退出，不存在可继续等待的运行session。

| 阶段 | 冻结产物 | 结果 |
|---|---|---|
| native构建、结构/预链接 | `artifacts/desktop-prelink/20261101T042003Z/report.json` 及同目录inspection | 通过；实际计时MRS已修正 |
| 新Payload FAT | `evidence/private/handset-payload/20261101T042029Z/report.json` | 通过 |
| Payload上传/锁定 | `evidence/private/handset-system-disks/20261101T042303Z/report.json` | 通过 |
| Payload extent | `evidence/private/ufs-readonly/20261101T042314Z/extent-policy.bin` | 已生成 |
| QEMU | `artifacts/native-staging-qemu/20261101T042318.236406Z-trko7gz0/report.json` | failed，37项PASS，returncode2，约38.767秒结束 |
| 手机构建/运行 | 此候选尚无相应产物 | QEMU失败后编排退出，未执行这两步 |

QEMU冻结panic：`native_panic.format` 为 `"AMFI: No PMGR?\n" @%s:%d`，`checkpoint_reached=false`；CPU stage5，root stage3，UFS online0/requests无实机意义，init exec0/syscall0。这是使用独立QEMU硬件ADT、无手机UFS的恢复夹具；不能与手机已经挂载根卷的状态混淆。短窗口同类QEMU在约18.960秒完成39项，通过不能证明50秒夹具也满足AMFI平台依赖。

失败日志为 `artifacts/session-logs/20261101-pid1-pet50-v4-qemu.log`，原serial在对应QEMU目录。日志尾有巨大hex回传，先读report的panic和失败字段，避免整段打印。不要盲目放宽passed判据、屏蔽AMFI、把手机改成VMM，或借此宣称PMGR根因已修复。

### 7.3 更早的桌面 QEMU 仍不是桌面证据

`artifacts/native-xnu-qemu/20261030T234929.685143Z-live-yu0rcuep/report.json` 曾记录148180个真实完成帧，画面仍是启动进度条，`desktop_verified=false`；原paused PID已不在，旧socket不能直接续跑。SpringBoard/backboardd等进程出现和QEMU scratch Data不代表手机服务或可写Data完成。该旧QEMU使用的125157376字节候选也不是当前124444672字节手机成功内核。

## 8. 接手后的主线顺序与停止规则

1. **先处理当前长窗口QEMU的可解释失败。** 使用7.2冻结report/serial定位AMFI在该模拟器ADT下的PMGR依赖，对照已有只读审计和固定原始模块；不要从重新传盘、重新做单块读取或大范围硬件调查开始。本次只定位到明确panic，尚未完成修复。
2. **给真实经过时间留足预算，再延长实机窗口。** 成功100poll实际约13.142秒；500poll名义50秒可能超过60000ms绝对pet期限。不能直接保证500poll可接受。可评估400poll等较短候选，或基于物理计数器的有界终止；当前decoder支持的limit集合需同步核查，不能只改初始化值。但需相应源码/decoder/预算验证及完整构建，明确这次改变的变量；不能把status3改判成功。
3. **复用已成功的准备阶段。** 若kernel、ADT、FAT都不变，复用7.2的payload/stage/extent，仅接续修正后的QEMU→手机构建→串行临时boot。不要从头重跑mainline，它会重复生成和上传Payload。若kernel/ADT改变，则生成新Payload/manifest并重新关联；原OS/SystemOS大盘继续复用。
4. **按实机实际进展推进dyld和PID1服务。** 正结果是匹配nonce、同轮syscall继续前进/关键调用完成、实际读盘及完整恢复；可解释负结果是新的真实panic/ESR/PC/调用返回。当前fcntl终止errno16不等于永久故障；先区分大读尚未完成、性能和独立启动依赖，再做最小修复。
5. **推进本机Data、服务和持续呈现。** launchd main之后仍需可写Data及原服务依赖，明确用户态合成后端、framebuffer/scanout交接和桌面进程实际帧。不能伪造迁移完成、解锁状态或用预制画面验收；原用户态若依赖GPU，首次桌面也可能需要A640能力的一部分。
6. **输入与基本操作独立验收。** 目标OS HID/GT9889或外接输入、打开/退出应用、持续操作10分钟，然后逐项完善GPU/电源/休眠等外设。

手机实验始终串行。上一轮必须确认Android返回、普通重启的新boot ID、root和临时属性清理，再开始下一轮。无nonce/可读原生记录时保持unknown，不原镜像重跑；没有外部串口本身不是所有实验的绝对禁令。仅 `fastboot boot`，不flash、erase、改GPT或覆盖原备份。

## 9. 复用入口与必要命令

操作目录为 `/home/guo/work/raphael-fresh`。先读根/板级/common的AGENTS与 `docs/HARDWARE.zh-CN.md`、`docs/PROGRESS.zh-CN.md`、`docs/NATIVE-XNU.zh-CN.md`。后两份按历史追加，旧段落的“未挂载/未进入用户态”不能覆盖本报告最新实机证据。

| 工作 | 入口 |
|---|---|
| 规范打包入口与只读资格检查 | `UniXNU-raphael/scripts/package.sh`、`UniXNU-raphael/scripts/check-packaging.py`；完整镜像尚未就绪，见第 12 节 |
| 当前最接近下一轮的编排 | `artifacts/session-logs/20261101-pid1-pet50-v4-mainline.py`，作为参数来源，避免直接从头执行 |
| 最新通过的编排 | `artifacts/session-logs/20261101-pid1-pet10-v3-mainline.py` |
| 原生完整构建 | `scripts/build_native_bootstrap.py`，handset-ufs/native-diagnostic profile |
| 预链接 | `scripts/prepare_desktop_kernel.py`；实际参数见对应build.py及prelink日志 |
| Payload生成与stage | `scripts/prepare_handset_payload.py`、`scripts/stage_handset_system_disks.py`、`scripts/ufs_extent_plan.py` |
| QEMU与手机构建/运行 | `scripts/run_native_staging_qemu.py`、`scripts/build_native_staging_handset.py`、`scripts/run_android_return_handset.py` |
| 原始遥测与恢复 | `scripts/native_early.py`、`scripts/native_pmap.py`、`scripts/native_watchdog_budget.py`，SEC与AndroidReturn源码 |

当前500poll候选可复用的QEMU参数如下。**它上一轮失败，只有解决明确的夹具依赖后才重跑；本报告不将其标为可直接部署手机的通过候选。**

```sh
python3 scripts/run_native_staging_qemu.py \
  --unaligned-io-bus-fixture --dt-platform-fixture --no-vmm-policy \
  --external-load-report evidence/private/android-return-run/20261031T194529Z/report.json \
  --external-payload-report evidence/private/handset-payload/20261101T042029Z/report.json \
  --kernel-inspection artifacts/desktop-prelink/20261101T042003Z/inspection.json \
  --stage 6 --arena-mib 320 --load-test --exit-complete --entry-test \
  --mmu-test --early-test --pmap-test --platform-test --platform-stop root-observer \
  --kalloc-zones 200 --ufs-handoff --ufs-read \
  --ufs-extent-plan evidence/private/ufs-readonly/20261101T042314Z/extent-policy.bin \
  --ufs-watchdog-map-fixture
```

通过后，手机构建沿用同一common参数，移除QEMU专用fixture参数，显式提供新的通过QEMU报告、`evidence/private/device/20261027T120325Z`、`evidence/private/watchdog-run/20261029T024843Z/report.json` 和同一Payload extent目录下的 `lun0-known-block.bin`。不要把当前失败QEMU报告传入手机构建。

完整native构建参数可从本轮build.py复用，核心形式为：

```sh
python3 scripts/build_native_bootstrap.py --handset-ufs --native-diagnostic \
  --storage-audit artifacts/native-bootstrap/raphael/ipados-17.7.11-21H461/raphael_desktop_display/tree/build/storage-abi/interface-audit.json \
  --storage-candidate artifacts/desktop-prelink/20261030T072416Z/kernel.macho \
  --root-policy evidence/private/desktop-root-policy/20261030T081351Z/report.json
```

手机runner仍用 `--runtime-only`。`adb devices -l` 按空白拆列、第二列等于 `device` 识别状态，不假设字面tab。不为交接而重新跑成功镜像，不重新审计整盘/备份哈希。

## 10. 私有资料、固件包与恢复状态

用户提供的ZIP：`D:\project\unixnu\miui_RAPHAEL_V12.5.6.0.RFKCNXM_f5fe3b4a6f_11.0.zip`。

已经只读列出34项，包大小2867806132字节；选取metadata、boot、DTBO、XBL、XBL_config、ABL、devcfg、qupv3fw，共172356396字节，提取到：

`evidence/private/vendor-package/20261031T164513Z`

- `report.json`记录来源、每个选取文件摘要、用途和私有属性；没有进行整包哈希、没有整包复制到Linux。
- metadata声明raphael、MIUI12.5.6.0.RFKCNXM、Android11、2021-10-01补丁；尚未独立认证vendor签名。
- `boot-analysis/report.json`已检查原厂boot header v1/page4096、kernel43958745、ramdisk0。
- 该包可用于对照启动链/固件/DT接口；原厂模板DTB可能含占位RAM，优先使用live FDT和实机入口证据。
- 没有执行包内updater-script，没有刷入手机，没有用其boot替换当前定制Android的自动返回胶囊。
- 私有闭源模块不因为“提取成功”就等于已满足重定位、DEPEX之外的服务依赖或可安全重用。

所有设备dump、标识、固件、Apple系统材料、boot产物、私钥及备份保留在ignored/private位置。提交前须按文件清单审查，禁止把这些资料推到公开仓库。不要执行`git add .`收集当前大量未跟踪文件。

本轮最新手机实验只用临时`fastboot boot`，`used_flash_or_erase=false`、`media_written=false`；但历史上曾为系统盘方案创建本项目的私有probe文件，不能声称整个项目从未向userdata写过任何文件。没有GPT修改或原备份覆盖。

最新runner为`runtime_only=true`，`boot_partition_check_performed=false`，分区不变字段为null。它证明运行、恢复及清理门禁通过，**不等于重新完成boot分区完整性或备份恢复验证**。

恢复机制分清三类：实验正常返回胶囊、专门测试过的watchdog/PSCI复位、无USB时人工长按电源。FDT回传依赖Android返回；异常复位可能丢记录，过去确实需要用户人工恢复过，不能承诺任何候选都会无人值守回来。

## 11. 交接完成时的明确状态

截至 2026-11-01 12:36 的设备核查为 Android 已启动、root 正常、临时属性已清理；2026-11-02 本次未重新操作手机或生成新实机报告，当前设备在线状态未知。新增工作仅为上游候选/打包入口与本地检查。最新通过的实机仍是 **100poll有界观察、原launchd/EL0及22次Unix syscall**；最新 **500poll候选停在QEMU AMFI/PMGR panic，未上手机**。

接手优先级为：**长观察夹具与实际时间预算 → 原dyld/PID1继续执行 → Data/系统服务 → 真实桌面帧 → 基本交互**。不再从“系统盘尚未上传、根卷未挂载”开始重复前期工作。当前无法可靠估计桌面时间；首次桌面、基本操作与A640/外设完善均未验收。


## 12. 2026-11-02 设备打包规范接入与接手方法

### 12.1 已实现的源码与入口

依据用户指定的 `https://unixnu.com/zh/porting/packaging` 及 c96b299 的官方模板/文档实施。页面和文档是技术依据，不能替代用户授权；固定脚本内不加入板级地址、参数、尺寸或刷机动作。

| 文件 | 本次结果 |
|---|---|
| `UniXNU-raphael/scripts/package.sh` | 官方 `templates/package.sh` 原样复制并设可执行；只读取 `[package] unixnu`，其余参数转发给 `unixnu release` |
| `UniXNU-raphael/board.toml` | 新增独立打包运行库路径、仓库/完整 pin 及 `[package.defconfig]`；只映射 `ipados-17.7.11-21H461 -> raphael_defconfig` |
| `UniXNU-raphael/scripts/check-packaging.py` | 本地核对运行库 pin、模板一致、OS/defconfig、工作流和记录覆盖；`--require-release` 明确拒绝不完整配方 |
| `UniXNU-raphael/.github/workflows/package.yml` | 独立设备仓库的手动 macOS check/build 入口；不猜 SoC/固件仓库及版本 |
| `.github/workflows/package.yml` | 当前工作区对应入口，默认 device_dir 为 `UniXNU-raphael`；嵌套设备 workflow 不能代替根入口 |
| `UniXNU-raphael/unixnu.local.toml.example` | 标准 `[build]` 私有输入示例；与 `local.toml` 的源码覆盖用途区分；平台种子不入库 |
| `UniXNU-raphael/.gitignore` | 忽略本地 build 配置和生成镜像/清单 |
| `UniXNU-raphael/porting.toml` | packaging 区覆盖新增文件、实际验证与未完成项，仍不宣称正式生产/实机验收 |
| `scripts/check_repository_layout.py` | 接入打包文件及本地检查；根布局与 13 区记录验证通过 |
| `UniXNU-raphael/docs/PACKAGING.zh-CN.md` | 使用、布局、私有输入、CI、完整镜像缺口说明；Windows 导出 `D:\project\unixnu\PACKAGING-20261102.zh-CN.md` |

仅支持已配置的 OS17。工作流资格检查明确拒绝 26/27；未迁移其 ABI、增加 defconfig 或复制另一份驱动。原默认配置继续 compile-only，不能把它写成已经可进入桌面的手机 release 配置。

### 12.2 实际验证及证据边界

总索引 `artifacts/packaging/20261102-validation/report.json`：`passed=true`，**21 个本地检查项**。其中预期失败用例按其指定非零返回码验收，不是完整镜像失败被改判成功。源码维护的脱敏摘要为 `UniXNU-raphael/evidence/packaging-20261102.json`，不是公开不可变启动日志。

- 默认目标、`--os 17`、完整 profile 三条 `--no-deps --check` 均通过，列出相同的 **62 个有序补丁**；只解析、不应用补丁、不编译。
- 原样模板、可执行位、路径含空格、参数边界转发及失败退出码传播通过。
- 源码 pin、已配置 OS 映射、缺失完整配方及未配置 26/27 的拒绝路径通过。
- 两个 workflow 的 YAML、shell 和内嵌 Python 语法通过；隔离源码夹具实际执行布局解析、SoC 覆盖、入口/补丁检查及 build 拒绝分支。
- 仓库布局、13 区记录及 `git diff --check` 通过；实机 backend 与打包运行库源码 diff 为空。

`full_image_build_performed=false`、`release_recipe_complete=false`、`remote_ci_executed=false`、`handset_executed=false`。检查过程中没有新 kernel/UEFI 构建、系统盘传输、手机启动或整盘/备份哈希复查；运行库复用本地候选，不重复 fetch。

### 12.3 可复用命令与 CI

活动仓库根目录：

```sh
python3 UniXNU-raphael/scripts/check-packaging.py --os 17
UniXNU-raphael/scripts/package.sh --no-deps --check --os 17 --out artifacts/packaging/check-os17
python3 scripts/check_repository_layout.py
```

这些入口会写入隔离输出及报告，不访问手机。无需为了接手重复执行全部用例；先读已有报告。`--check` 按 deps/preflight/patches 到构建前停止；`--no-deps` 跳过源码/IPSW 获取。单独运行 `--check` 默认仍会执行 deps，因此已有本地源码时不要漏掉 `--no-deps`。

完整镜像资格检查：

```sh
python3 UniXNU-raphael/scripts/check-packaging.py --require-release
```

此命令目前**应失败**，指出缺失字段；不能通过改检查器或填另一设备占位值绕过。固定 `package.sh` 本身不作板级改写，CI 在调用完整 release 前先执行此资格检查。

手动工作流仅本地验证，未触发远端 Actions。macOS check 模式不需要 seed/固件；独立检出若缺少 SoC，必须提供真实仓库与完整 commit。build 模式还需完整配方、真实固件检出/commit 和 fork 的 `UNIXNU_UNIQUE_CHIP_ID` secret，并安装/断言工具。成功才上传 boot.img、payload.img、kernel.macho、package.manifest.json；不存在产物会报错，保留一天。下载设备绑定私有产物后按规范删除该 Actions 运行，不发布为公开 release。

### 12.4 完整镜像仍缺的条件与后续任务

当前资格检查报告 **8 个缺失字段**：`firmware.config`、`firmware.dsc`、`firmware.fd`、`firmware.packages`、`payload.volume`、`payload.size_mib`、`payload.loader`、`bootimg.dtb`。填齐字段只是必要条件，不能代替正确配方与验证。

1. 将现有独立 SEC/DXE、内存所有权、返回/喂狗门禁表达为本机标准 firmware 配方，不能套用 uefi-sheng 或其他板级参数。
2. 将 storage ABI、signed owner policy、原 trust cache、不可变 extent 和真正的手机运行 ADT 输入表达为 payload 配方；inspection DTS 不能直接充当运行 ADT。
3. 补 DTB 生成、本机 shim/内存布局和返回合同，以及有证据的镜像容量约束。
4. 固定可发布 SoC 源图与官方 `[firmware.image]` 来源/选择性提取/二进制模块生成。现有本地 vendor ZIP 尚未完成独立签名认证，不伪造生产输入来源。
5. 从干净检出完整运行标准 release，验四项产物/清单、命令行字节数和镜像大小；手机启动按原门禁另验。

本轮没有生成新的 `boot.img`、`payload.img`、`kernel.macho` 或 `package.manifest.json`；既有诊断流程仍以第 7–9 节为准。**桌面主线的下一阻塞仍是长观察 QEMU 的 AMFI/PMGR 依赖和实际时间预算，之后推进 dyld/PID1、Data、服务、真实桌面帧与输入。打包预检查成功不改变实机里程碑。**

本次打包改动前的源码备份为 `artifacts/packaging/20261101T160954Z/`。本次交接改动前的两份文档及本地核查摘要另存于 `evidence/private/handoff/20261101T162510Z-packaging-update`；不覆盖原备份、冻结成功/失败产物或 dirty 修改。


## 13. 2026-11-02 主线：原版PMGR、DMA复制与长窗口

- `20261101T165321Z`：真实手机原AMFI `No PMGR?` panic，快照、nonce、恢复和清理成立，实验失败；未改写原报告的旧runner执行字段。
- `20261101T171229Z`：显式诊断ADT使原ApplePMGRNub加载/init/start/attach/注册，自己的AON provider为NULL，与固定iPad7原目标的unsupported AON返回合同相同。非VMM手机身份不变，无新硬件地址、AMFI文本修改或硬件电源管理声明。40.104766秒、77次pet、22次syscall、UFS103154688字节，整轮通过。
- `20261101T172012Z`：同40秒观察，唯一变量为Device DMA CPU复制自然对齐64位访问。READ10仍4096字节、认证逐4KiB。40.112623秒、494388224字节、78次syscall、9个签名对象、489881600签名输入字节，UFS及签名错误0；末尾errno16为有界诊断终止中断，不是独立启动失败。恢复/普通重启/root/清理通过。
- 公开源码摘要：`UniXNU-raphael/evidence/native-pmgr-compat.json`、`native-ufs-dma-copy.json`；原始手机报告/镜像保持私有。
- 120秒候选：`raphael-service-window.patch` limit1200；watchdog ADT v2为56字节，固定180000ms pet/120000ms observer，旧v1的60000/40000合同继续支持；硬件阈值仍20秒，至少500ms间隔刷新。完整XNU ABI构建、host边界与到期检查通过；实机175421Z整轮通过，120097.983ms、235次pet、204次调用、27个签名对象、1489957888字节UFS且错误0。
- 首次长窗口QEMU失败：`artifacts/native-staging-qemu/20261101T174538.645094Z-iedsaorl/report.json`，原root缺失panic和恢复快照保留，不伪称手机故障。该夹具无OS根盘；新的显式QEMU DT-policy observer在40秒退出，手机ADT没有此属性。

下一验收以真正的新调用/原panic为依据继续推进动态链接、PID1服务；可写Data、显示和输入分别开发验证。不要重传原OS/SystemOS大盘、重复无关全盘/备份哈希、改GPT/flash/erase、自动fetch或把QEMU/构建当手机桌面。


第13节续记：180628Z Normal-NC候选的完整验收因128KiB页表快照不足失败，Android/root/清理通过；独立CRC有效globals显示两页Normal-NC、246次syscall、33个签名对象和1873572864字节/零UFS错误，但不代替完整pmap验收。记录容量现为512KiB pmap+4MiB FDT，实际最坏输出2484248字节、18项边界检查及QEMU39通过。v11在手机启动前停止；v12复用同一内核/载荷/extent，只修复返回容量，手机run182129Z待最终结果。v13的240秒/300秒v3合同只属于已通过host验证的候选，不能当手机资格。原失败、容量测试和备份均保留。


第13节续记：182129Z已整轮通过，Normal-NC可作为下一轮冻结基线；源摘要`UniXNU-raphael/evidence/native-ufs-normal-nc.json`。实际132页/135462字节pmap、1982数据页验证成立，120.027秒、246调用、33签名对象、1872835584字节/零错误。当前活动补丁limit2400属于v13候选，完整成功冻结内核仍limit1200。下一验收看原共享缓存验证后是否出现新的PID1/服务调用或原panic；不能凭更多调用认定launchd main。


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
