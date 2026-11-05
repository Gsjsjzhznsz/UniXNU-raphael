# Raphael 本机系统盘主线

2026-11-01 路径迁移：本文历史记录中的 `UniXNU-raphael/drivers/` 现位于 `UniXNU-raphael/package/drivers/`；`UniXNU-sm8150-common/drivers/` 现位于 `UniXNU-sm8150-common/kits/Sm8150Platform/`。历史构建/实机结论和冻结artifact不变。当前状态与规范差距见[交接](HANDOFF-20261101.zh-CN.md)及[整改说明](../UniXNU-raphael/docs/REPOSITORY-COMPLIANCE.zh-CN.md)。

2026-11-01（Asia/Shanghai）。目标仍为原目标系统真机进入真实桌面。

OS/SystemOS 已存放在新建的 `/data/unixnu-raphael-system-20261031T174325Z/` 中，完整 SHA-256 与主机原始盘一致、无 fscrypt policy、文件不可变，分别 66/27 个 extent。没有改 GPT 或覆盖旧文件。私有 stage report 见 `evidence/private/handset-system-disks/20261031T174325Z/report.json`。

| 层 | 证据 | 结论 |
|---|---|---|
| 实际 C++ 映射/计划 | `artifacts/extent-plan-host/20261031T175054.479640Z-ydvb8slx/report.json`、`artifacts/readonly-extents-host/20261031T175054.959075Z-dqm2biha/report.json` | ASan/UBSan 18+24 项；越界、回绕、重叠、非对齐、错误数据、失败块和第二轮传输错误拒绝 |
| OS 固件与 QEMU | `artifacts/native-staging-qemu/20261031T175729.003254Z-_8395fdn/report.json`、`evidence/private/android-return-build/20261031T175919.337229Z-54fo9kxs/report.json` | 编译、FD/PE/8384 字节策略检查、21 项 QEMU 合同通过；模拟器无本机 UFS MMIO |
| OS 真机 | `evidence/private/android-return-run/20261031T180012Z/report.json` | 16 轮、128 次物理读取全部一致；匹配 nonce；71.098 秒回 Android；恢复及清理通过 |
| SystemOS 固件与 QEMU | `artifacts/native-staging-qemu/20261031T180327.980299Z-tcrz64_r/report.json`、`evidence/private/android-return-build/20261031T180515.944692Z-pjszmgpn/report.json` | 独立计划，编译/结构/21 项合同通过 |
| SystemOS 真机 | `evidence/private/android-return-run/20261031T180840Z/report.json` | 16 轮、128 次物理读取全部一致；匹配 nonce；71.154 秒回 Android；恢复及清理通过 |

两轮各读取首部、APFS container 超级块、中段、末尾及跨 extent 区域，4096 字节汇总样本在每轮现场与固件内冻结参考逐字节比较。它们是两个独立实验，不能合成一次系统启动。没有 APFS mount、XNU 用户态或桌面证明。runner 是 runtime-only，没有重读 boot 分区完整性。

实现为 `RaphaelReadOnlyExtents.h` → `RaphaelExtentPlan.h` → `UfsRead.cpp`。只增加默认关闭的 UfsExtents PCD 与独立 raw FFS 策略；原 4392 字节记录不扩大，新 version3 明确报告完成轮数/物理读取数。启动前重采 size/FIEMAP/immutable 标志，相对地址不得移用于别的文件。保留分区、完整 LUN 与文件长度边界，拒绝写命令。

常驻驱动 `UniXNU-sm8150-common/drivers/RaphaelUfsBlock.cpp` 是开发候选：一个控制器串行服务两个只读 IOBlockStorageDevice，所有资源从显式 ADT 取得；再次检查 SMMU/8CPU，自有连续 NC DMA，不为其他外设编程地址。传输错误先停止服务，证明恢复或 HCI reset 后才释放 DMA；不能静默重试或返回失败块的旧数据。认证版为两个真实 owner policy 分别分配只读副本，使用固定 VerifiedRoot 的签名与逐块认证；不跳过根认证。独立对象编译成功不代表其 init、cache 属性、DMA、认证或生命周期已在手机运行。

完整内核已使用独立 `raphael_handset_storage_defconfig` 构建通过（`artifacts/native-bootstrap-attempt/20261031T182230Z/report.json`，887 份编译记录）；独立结构检查 `artifacts/native-kernel-inspection/20261031T182920Z` 未定义符号为 0，预链接 `artifacts/desktop-prelink/20261031T183009Z` 生成 124,436,480 字节候选，旧 native-only、模拟器、成功手机候选和原备份保留。本机 ADT 已生成并通过 8 项 host 检查（`evidence/private/handset-adt-host/20261031T185330Z/report.json`），包含两份盘映射、PSCI affinity、HCI 和 APPS SMMU；仅为静态输入。仍需：更大载荷实机资格 → 常驻存储接管 → 常驻 UFS 与 APFS 根卷 → launchd/可写 Data → 持续桌面帧/输入。当前 20MiB FAT、72MiB arena 和 256MiB 诊断 grant 不能直接授权系统桌面内存。

已保留失败：首版/第二版 QEMU 构建仅因结构检查器未列入新增 FFS GUID/类型拒绝，未运行手机；首版主机 handset 构建因相对路径校验拒绝，未生成有效手机候选。XNU 初版对象未通过编译（系统头、对象大小及 init 接口），修正后独立对象通过；旧失败不追认为运行结果。


## 大载荷路径（本轮持续推进）

新增默认关闭的 UfsPayload/NativeFatBytes 配置，原 20MiB 内置 FAT 路径回归通过（`artifacts/native-staging-qemu/20261031T184240.187220Z-iralwyjn`）。新 FAT 不扩大下载 Image，改为读取 Android 中本项目创建的不可变文件，FD 保存每个 4096 字节块的 SHA-256 参考；先验证再复制，写命令仍拒绝。实际哈希/读取代码经 ASan/UBSan 与 hashlib 35 向量、7 个错误处理检查通过（`artifacts/payload-hash-host/20261031T183957Z`）。FAT 128MiB，stage 报告 `evidence/private/handset-system-disks/20261031T184303Z`，7 个 extent，完整 SHA-256 一致。

QEMU 只把相同 FAT 注入独立 RAM fixture 并逐块校验，不模拟本机 UFS。`184821.090822Z-fxcrzqom` 的 21 项布局/返回检查通过；`185148.938291Z-1ca_wq4s` 原 DarwinBoot 实际装载完整 15 个 Mach-O 段，25 项及 args/ADT/段 CRC/零填充检查通过。此路径使用明确 320MiB arena 实验预算，kernel grant 仍 256MiB；不构成整段 RAM 所有权或手机完整系统运行证明。

手机首轮 `evidence/private/android-return-run/20261031T185043Z/report.json`：临时 boot 接受，116.241 秒回 Android，root、新 boot ID 与普通重启清理通过；nonce=false、SEC/return/UFS 记录全部缺失，**整轮不通过，执行停点未知，不能认定整盘读取成功或传输失败**。原镜像不重跑。后续只改变显式 HCI 错误复位恢复分支以争取可解释错误记录。

保留主机失败：首个大 arena QEMU 在 SEC 配置门禁 0x234 被拒（未放开 320MiB）；首个 loader QEMU 在预链接的 minimum VA 与旧固定 VA 不符时被 host 拒绝。修正为从选定 Mach-O inspection 解析 minimum VA，原失败不追认为成功。


## 延迟自动恢复取得异常记录（2026-11-01）

第二轮大载荷 `185859Z` 超过 runner 220 秒窗口后自行回到 Android；用户明确确认没有按键干预。原 timeout 记录保留，后续匹配 FDT 独立保存在 `evidence/private/android-return-run/20261031T185859Z/manual-recovery/`。nonce 匹配、Android/root/新 boot ID 成立；并非人工强制恢复。

SEC 记录显示 `ESR=0x96000061`、`ELR=0x800a9734`、`FAR=0x818dd327`。由同轮 `SecFinish` 和 frozen map 得到 SEC XIP base `0x800a2000`，故障 RVA `0x7734` 的实际指令为 `sturh w8, [sp,#7]`：READ10 CDB 第 7/8 字节被 LTO 合并为奇地址半字写，MMU-off Device 内存访问触发对齐异常。UFS INQUIRY/TUR/CAPACITY 成功，stage6、payload completed0；不能认定整份 FAT 读取成功。显式异常恢复 HCI reset=3、DMA released/watchdog restored，uncached after=0，正常回调未完成。

共享传输新增 volatile 字节 `be16` 写入，阻止该奇地址合并；37 项真实 QEMU UFS 模型检查通过。后续镜像必须重新生成并保留新 nonce，不重跑旧故障镜像。

最新含 teardown 锁修复的完整 native kernel：`artifacts/native-bootstrap-attempt/20261031T190140Z`，inspection `20261031T190305Z`，native SHA256 `b90e920420df2374e7adf6952071a8600906969dcd5498887119046777f5bd44`、91,593,320 字节、undefined0；预链接 `artifacts/desktop-prelink/20261031T190306Z`、124,436,480 字节。尚无此 kernel 的手机执行证据。


## 2026-11-01：完整载荷、原入口和完整内核 pmap 实机推进

194037Z实机已完成128MiB FAT的32768个载荷块读取与缓存恢复后认证，控制器/DMA/看门狗恢复和Android清理通过；194529Z完整15段OS预链接内核装载通过。200605Z实机已完成退出服务和原XNU首5条指令，约199.286秒自动返回Android并清理通过。上述时间戳均为2026-10-31 UTC。

新只读清单布局193742Z完整内核，在201835Z实机已执行原arm_init及arm_vm_init、重建页表并到machine_startup入口。原报告因解析器使用了生成的小ADT而非外置载荷内的实际UFS ADT，错误标记pmap失败；保留原报告。独立重新解码结果在同目录redecode-external-adt/report.json，passed=true，实际76页活动表、644页恢复数据映射、物理timer及看门狗恢复、199.230秒自动返回和普通重启清理全部通过；未重新启动诊断。

组合内核的原start.s从__mh_execute_header而非最低导入段建立bootstrap映射。新增MMU策略v2冻结该差值并逐项验证105对2MiB block和4页临时表；不扩大本机256MiB grant。C内检查点使用真实boot_args副本及页表验证，x22-x25是原C函数内部可使用的保存寄存器，不能强行当作入口寄存器。

仍未证明常驻UFS驱动运行、APFS挂载、launchd或桌面。完整UFS编译诊断候选201852Z/载荷202203Z已准备，正在推进更深IOKit/BSD检查点。无flash/erase/分区表修改，没有重新同步上游。


## 2026-11-01：完整 OS 的实机 panic 已回传，定位 GIC 总线偏移检查

`android-return-run/20261031T212405Z/report.json`：匹配 nonce、完整载荷 UFS 认证、15 段恢复、自动 Android 返回及普通重启清理通过；目标诊断点失败，真实源码 panic 为 `"CPU configuration in device tree is invalid" @%s:%d`。约 199.379 秒自动返回。独立 `panic-telemetry-redecode.json` 从同一份 CRC 验证快照读出 Raphael CPU stage=1/registered=0、ArmDTPlatform configured=1/CPU count=1、UFS start_stage=0。不能把这次 panic 记为 BSD 或常驻 UFS 成功。

新增编译期 panic 记录和 BRK #0x5353，保留完整默认 POST，不再运行时改原系统 text。终止式 panic 返回在单 CPU、全异常屏蔽下无锁停机 UFS，不释放 DMA 内存；停机失败继续原 panic。独立 QEMU 注入记录于 `artifacts/session-logs/20261101-panic-injection/redecode-report.json`，验证实际字符串、完整快照 CRC/恢复及接收器拒绝目标成功；最初字符串期望漏掉原 panic 宏追加的 @%s:%d，仅重解码原日志，没有再次执行。

加入真实 UFS/SMMU 后 arm-io 基址不再必然 64KiB 对齐；原 CPU 驱动错检相对 reg 偏移，导致映射前退出并落入不适用的 AppleARMCPU。`native-staging-qemu/20261031T213757.280707Z-h0m20mg4/report.json` 保留旧内核，QEMU 仅将总线基址降低16KiB、相应增加 reg 偏移，实际 GIC 物理地址保持不变，复现完全相同 panic 和 CPU stage1。新源码改为核验解析后的物理地址；另在显式 unixnu,boot-cpu=1 契约上拒绝 AppleARMCPU 的被动匹配。修正候选仍待本机运行，不声称已成功。

常驻认证表已改为借用内核 __TEXT,__rph_verified 的原只读字节，并逐页通过 AT S1E1R/S1E1W 检查实际读映射和写权限拒绝；保留独立只读密钥页、签名和逐块认证，避免额外约73,287,008字节复制。此为源码/全量构建通过，运行中实际节省和 UFS online 仍须实机记录。

`210336Z`、`211644Z` 均约240秒自动回 Android，但无匹配原生记录；保持 xnu_executed=null，停点未知，不原镜像重跑。全部仅 fastboot boot，runtime-only 未做 boot 分区哈希检查；无 flash/erase/GPT 修改。


## 2026-11-01：完整 OS 内核 BSD 调度实机通过

`evidence/private/android-return-run/20261031T214248Z/report.json` 整轮 passed=true：完整载荷 UFS 认证、15 段装载及恢复、匹配 nonce、原 BSD checkpoint19 均通过；199.409543 秒自动回 Android，新 boot ID/root/普通重启清理通过。CPU stage5/registered1，物理 timer INTID18、19200000Hz，timer IRQ2/EOI2。GIC 解析后物理地址对齐修复已有本机证据。

常驻 UFS start_stage0、online0、requests0，诊断停机 state1/online_before0；尚未证明常驻驱动启动、APFS 根挂载、launchd 或桌面。下一候选只增加终止式存储停机前的500ms调度窗口，检查是否因异步匹配尚未调度就设置 diagnosticShutdown。保留最后 IOSleep100ms 与原检查点，恢复门禁不变。


## 2026-11-01：调度窗口使常驻 UFS 进入 start，修正 ADT cell 声明

`android-return-run/20261101T000448Z/report.json` 整轮 passed=true，200.704278秒自动回 Android，匹配 nonce/BSD id19/恢复和普通重启清理通过。单增停机前 IOSleep500ms 后，常驻 UFS 从 start_stage0 前进至 start_stage1，online_before0、requests0；说明初始化已开始，但资源/所有权/映射检查尚未全部通过，不是常驻块读取成功。

源码核查发现手工 ADT 的 reg/ranges 均按64位地址和长度编码，却遗漏 root/arm-io 的 #address-cells/#size-cells。原 XNU IODTGetCellCounts 默认 address2/size1，导致每组 reg 按12字节而非16字节步进，ranges 按20字节而非24字节步进。固定上游通用 ADT 生成器明确使用2/2。修正本项目生成器，并为原冻结 ADT 仅添加准确2/2声明；其余全部硬件属性、系统盘extent、随机种子字节原样保留。

新 ADT `handset-storage-adt/20261101T001307Z`；12项 host 检查在 `handset-adt-host/20261101T001354Z/report.json`，包括实际双资源地址匹配和缺失/错误cell声明拒绝。新手机候选复用000103Z native build及000329Z prelink，只改变这项ADT编码契约，实机结果另记。手机载荷资格只允许精确2/2声明差异，其他MMIO与所有权属性仍要求与已验证基线完全相同。


`android-return-run/20261101T001528Z/report.json`：新2/2声明在手机使UFS进入start_stage2，确认资源/CPU/SMMU前置门禁已通过。随后原XNU发生内核异常；匹配nonce、panic5353、完整CRC快照恢复，199.474817秒自动Android及普通重启清理通过。目标checkpoint没有达到，整轮passed=false。旧通用panic只保存格式，不能推出原故障PC；没有重跑同一镜像。

独立诊断源码补充在panic_with_thread_kernel_state入口保存第一份原始arm_saved_state64（PC/LR/SP/FAR/ESR/CPSR/x0-x28/FP和原因），仍经原panic与安全UFS终止式停机返回，不绕过默认POST或正常VM故障。新增start_detail细分DMA分配与首次命令进度。新887记录全量build002222Z、prelink002413Z、QEMU002436Z通过；故障注入 `artifacts/session-logs/20261101-fault-state-injection/report.json` 用未修改原LDR指令的明确null-read寄存器输入，原异常处理捕获精确PC/FAR0/ESR/x0=0，接收器正确拒绝目标成功。

`artifacts/session-logs/20261101-dma-allocator/report.json` 在相同QEMU内核实际调用原IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,0x113,8192,4096)，返回真实对象，未复现分配故障。它只排查通用分配调用，不证明手机DMA可达或UFS命令成功。新手机诊断结果另记。


## 2026-11-01：实机精确捕获 DC ZVA 对 Device DMA 映射的故障

`android-return-run/20261101T002729Z/report.json`：新通道捕获原始异常 `Unaligned kernel data abort.`，PC `_bzero+0x44` / `0xfffffff00bfd2484`，同轮冻结Mach-O该处opcode `0xd50b7423`（DC ZVA,x3），ESR `0x96000061`。UFS start_stage2/start_detail5：DMA分配、物理连续地址和Session建立已完成，正在takeOver，尚未提交UFS命令。195秒自动回Android、nonce/CRC恢复和普通重启清理通过；目标失败，不计为常驻读块成功。

Device属性的DMA映射不能用DC ZVA清零，编译器把首个zero-buffer拷贝优化到通用_bzero。Backend::toDevice/fromDevice改为显式volatile字节访问，保留地址/长度边界及DSB，不改变控制器地址、缓存策略、认证或所有权门禁。新候选重建后再上机，不重跑原故障镜像。


2026-11-01 常驻 UFS 首次实机启动通过：`android-return-run/20261101T003353Z/report.json` 最终 `passed=true`、nonce/恢复/清理通过，200.396 秒自动回 Android。`start_stage=4`、`diagnostic_online_before=1`、`last_result=0`：原生存储服务完成控制器接管、设备查询、两卷认证与初始化，终止诊断前在线。上层 `requests=0`，尚无 APFS 挂载、launchd 或桌面证明。下一步为独立 id20 有界根卷观察线程，使原 BSD 继续 setconf/vfs_mountroot/根认证；首次补丁上下文失败保留于 native-bootstrap-attempt/20261101T004537Z，已按全部前置补丁重新生成并进入完整构建。


根卷观察点 id20 已完成887记录完整构建与预链接：/home/guo/work/raphael-fresh/artifacts/native-bootstrap-attempt/20261101T005208Z、desktop-prelink/20261101T005355Z。新 ADT handset-storage-adt/20261101T005453Z 只添加 chosen/root-matching；UUID 从该内核的签名 OS manifest 头提取，严格匹配当前内核，错误UUID与硬件reg更改均被拒绝（artifacts/session-logs/root-matching-qualification/report.json）。

QEMU native-staging-qemu/20261101T005931.517393Z-j_cmnubm 成功：观察线程真实定时唤醒50次，原BSD到setconf，读取根状态后安全停机并恢复。此夹具无手机UFS/系统盘，root_mounted=false属于预期，只证明观察/恢复路径。前一轮005657Z因终止检查点主动屏蔽中断、旧契约仍要求开启而未通过；新增id20明确要求屏蔽态，其他停点规则保持。NativeEarly实际观察frame为64字节，仍由最终链接指令推导并验证，完整诊断结构保持<=0xf000。手机010035Z已接受临时boot，结果待回传。


2026-11-01 最新实机：`android-return-run/20261101T010035Z` 整轮通过，原 BSD 完成 APFS 根挂载（disk1s1）、只读所有者认证和186次/734208字节实际块读取，零失败。观察线程8次100ms唤醒后返回，200.509秒自动Android，恢复与普通重启清理通过。Apple原根认证返回80，最终按已启用的所有者签名块认证策略接受，不能表述为Apple封印认证成功。launchd、显示桌面与输入仍未验证；下一步推进原PID1启动。索引：UniXNU-raphael/evidence/native-apfs-root.json。



实机011142Z（最终passed=true）进一步进入原load_init_program：根认证再次成功，241次/959488字节读取、零失败。5秒观察窗口结束时，native_owner_cache_stage=2，尚未调用exec；空闲28629页、wired36844页。不能把这次记成SystemOS组合挂载或launchd执行通过。新增逐个copyout阶段与原PID1休眠线程栈的只读捕获，保持相同5秒预算，区分实际等待点；011931Z首次构建因extern声明顺序失败，已修正并保留失败记录。
