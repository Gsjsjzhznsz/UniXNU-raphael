# 桌面主线

2026-11-01 路径迁移：本文历史记录中的 `UniXNU-raphael/drivers/` 现位于 `UniXNU-raphael/package/drivers/`；`UniXNU-sm8150-common/drivers/` 现位于 `UniXNU-sm8150-common/kits/Sm8150Platform/`。历史构建/实机结论和冻结artifact不变。当前状态与规范差距见[交接](HANDOFF-20261101.zh-CN.md)及[整改说明](../UniXNU-raphael/docs/REPOSITORY-COMPLIANCE.zh-CN.md)。

2026-11-01 交接更新：最新手机 `170816Z` 真实READ10已读取本项目明文probe对应LBA53068291，4096字节与Android参考全等，整轮passed=true；71.479561秒自动回Android、新boot ID/root/普通重启清理均通过。此轮为stage3 UFS短路径，无XNU执行证明。最深XNU实机仍为`20261030T224923Z`的BSD停点id19。系统根卷、launchd、桌面与基本交互尚未在手机验证。完整版本、证据、失败更正、复现命令及接手顺序见[2026-11-01详细交接报告](HANDOFF-20261101.zh-CN.md)。

2026-11-01 最新主线：手机165548Z真实READ10首块通过，4096字节与Android参考逐字节一致；nonce、stage3、uncached往返、所有UFS命令、SMMU/8CPU门禁、控制器及看门狗恢复均通过。70.208秒自动回Android，正常重启的新boot ID/root/临时FDT清理通过，整轮passed=true；runtime-only，无flash/erase。源码LUN0块读取已从“尚需开发”推进为“本机已验证（单块）”，持续驱动/系统卷仍待接入。此前READ16有效SCSI错误原因仍未知，不以READ10成功反推READ16不支持。

164737Z查询候选已验证cache修复：inside=before&~0x1005、after=before、callback=1。原实验通过，但清理脚本曾把旧Android的boot_completed=1误当成新启动；普通重启稍后实际完成，165044Z/delayed-cleanup-report.json独立确认新ID/root/无临时属性，原失败报告保留。脚本改为明确等待新boot ID。曾准备的sync-reboot helper没有上传或执行。

实际冻结手机Mach-O已核实IOKitInitializeTime首指令直接B到clock_initialize_calendar，函数中不存在30秒IORTC等待。证据native-iokit-time-linked.json；更正此前文档“原30秒RTC发现未跳过”的说法，不能从BCM2837目录名或空nm日志作判断。

下一步系统卷路径：170219Z重新只读采集项目明文probe，未加密、FIEMAP前后一致、原始LUN0块与文件全等，地址217367719936字节/LBA53068291。实现显式ReadLba PCD及version2 wire，保持4392字节记录大小，主机兼容原version1；非零LBA构建必须带采集来源。手机170816Z已经验证文件对应块的native读取，4096字节全等；尚未接成持续系统卷。


2026-11-01：按用户本轮指令独立获取三个 GPU parity 候选分支：Adreno740 b8956437c7a2feac58dccd6b29948d1b89fcc1df、AdrenoMetal fc5ca0b274bec1c26b3a1a1ee2b911da33e15bd2、GopFramebuffer 74ff4c4165c0d84bbca82b1ec732677d2d62a98b。准确提交、原候选差异与目录见 docs/upstream-refresh-20261101.json；活动通用 UniXNU 仍 f0721e9745c45ad2600cd69c74730f1cca55d56a。A740 双 ring 抢占/优先级与 Metal trace/内存改动尚未集成本机 A640；GOP 新增动态生命周期 ring 与等待统计。未把候选拉取当作驱动验收。

本轮确定修复 stage3 UFS 短路径的配置矛盾：冻结候选161936Z的 AutoGen.h 为 UfsRead=1、NativeWatchdogBase=0x17c10000、NativeMmuTest=0，旧 SEC 看门狗映射分支必在返回胶囊准备前以0x23e退出。此前 QEMU 没配看门狗，漏掉此分支。新增显式 QEMU synthetic mapping fixture（独立0x0b000000，不是手机地址，无看门狗MMIO/复位证明）；163823Z QEMU21项及164020Z手机构建/结构通过。手机164138Z nonce/stage3/返回/自有UFS DMA查询/容量/控制器和看门狗恢复通过，71.177秒自动回Android，随后正常重启/root/清理通过；块读取未执行。整轮passed=false，因为uncached回调记录inside=0/callback=0，而UFS结果证明回调执行，不能忽略这个矛盾。汇编进入前清cache时后续读取range table可重填旧cache line，返回后会遮蔽uncached更新；新增M/C off下的三范围DC IVAC后再恢复SCTLR，并限制CTR cache line<=4KiB。164503Z QEMU21项通过，手机候选正在构建；QEMU不模拟本机真实cache一致性。

继承失败补录：004718Z提前准备返回胶囊的候选手机未回USB，经手动恢复；该API已限制QEMU-only。late uncached候选161936Z的手机162556Z虽回Android但nonce=false/无SEC/UFS标记，停点未知，正常重启清理通过，原镜像不重跑。上面的确定门禁缺陷适用于它；不追认该轮执行过UFS，也不将早期所有无记录都归因于同一缺陷。

用户提供原厂MIUI包已经只读检查；选取boot/DTBO/XBL/XBL_config/ABL/devcfg/qupv3fw和metadata复制到evidence/private/vendor-package/20261031T164513Z（172356396字节），原ZIP未改。metadata声明raphael V12.5.6.0.RFKCNXM Android11/2021-10-01补丁，不能代替当前定制内核与现场资源。来源/用途/选取文件哈希保存在私有report，未刷入手机、未重新审计分区哈希，未复制整包。

当前桌面关口仍是本机原生块读取及只读系统卷、足够的载荷内存与持续用户态呈现。真实XNU BSD调度已验证；手机根卷、launchd、首次桌面、基本交互、GPU/外设均未验收。旧QEMU进度条不算桌面；不承诺日期。


2026-10-31 后续：UFS 自有 DMA 已有手机证据，块读取仍未验收。手机 234851Z 的原始 after.dtb 经 235256Z 重放解码（没有再启动实验）确认：INQUIRY、TEST UNIT READY、READ CAPACITY16 均成功，LUN0 为 Samsung KLUEG8U1EA-B0C1，60884992 × 4096 字节，与 Android 现场一致；READ16 返回有效 SCSI 错误，OCS0，旧 wire 未保存 sense，不能断言原因。控制器/看门狗恢复、原 BSD 停点与正常重启清理通过。重放只修主机解码，原失败报告保留。

READ10 候选 235649Z 的手机运行 235948Z 回 Android 时无匹配 nonce、无 UFS 记录，停点和复位原因未知；用户随后确认已恢复。不能称其成功读取或无人值守返回。当前 ADB/root/boot_completed 已确认，chosen 无 raphael 临时属性。采集脚本已修为缺记录返回 unknown，解码异常后仍完成正常清理；原始记录不覆盖。下一候选改用独立 stage3 UFS 短路径（不执行 XNU），保留相同 READ10 核心、8CPU/SMMU/看门狗门禁及 sense 记录，区分读取问题与后续初始化。QEMU 001551Z 的 21 项恢复检查通过，它不证明手机 UFS；真实 QEMU UFS 模型 READ10/READ16 的 31 项测试另行覆盖。

系统卷放置路径：新私有 /data/unixnu-raphael-stage-20261030T235925Z（0700）与 4096 字节 probe 没有文件加密策略，FIEMAP 单段与 /dev/block/sda31 原始读取全字节一致。证据 evidence/private/ufs-stage/20261030T235925Z/report.json；仅创建本项目新文件，未改 GPT、现有文件或备份。该结果只证明 Android 下明文文件到 LUN0 物理块的对应，尚未由 native UFS 读取。后续只读系统盘方案需处理 512 字节虚拟 sector 与 4096 字节物理块、跨 extent、范围及不可变生命周期；尚未上传系统镜像。最新桌面 QEMU 234929Z 已完成 148180 帧但仍为原启动进度条；locationd/迁移/背光同步等待依赖尚未定位完成，不能验收桌面。手机根卷、用户态与桌面均未验证。上游仍固定 f0721e9745c45ad2600cd69c74730f1cca55d56a，未同步。


2026-10-31：手机232235Z通过新增UFS只读交接采集，原bsd-scheduling停点及全部自动返回/清理门禁通过。FDT现场解析HCI0x01d84000/0x2500；两遍36次只读均一致：CAP0x1587031f/VER0x300、HCE1/HCS0x10f、IS0x400/IE0/AHIT0、UTRLRSR1、UTRLDBR/UTMRLDBR0，无UIC错误。原UTRLBA0xffffe000只是ABL仍占用的观测，不能复用为本机DMA池。事实限定入口已有控制器/链路，native DMA与独占所有权仍未知。摘要native-ufs-handoff.json；host实际C资源边界14例与QEMU232022Z39项通过，手机构建232137Z。116.061秒回Android，runtime-only，无flash/erase，原备份未改。

独立只读UFS传输核心已实现INQUIRY/TUR/CAPACITY16/READ16、严格OCS/tag/LUN/sense/residual与超时DMA隔离；26项真实QEMU UFS模型/ASan/UBSan通过，含完整4096字节数据对比。系统QEMU8.2.2在UFS响应DataSegmentLength双重字节序转换，隔离官方8.2.2源码单行修复并独立构建测试，未替换系统QEMU或手机放宽协议。实现与模型通过尚非手机块读取。下一项最影响桌面为自有DMA缓冲区是否可达，随后只读系统卷布局；不会复制Android旧UTRL或改全局SMMU。

2026-10-31：本机首个正常XNU定时IRQ与线程休眠/唤醒已验证。224923Z在原BSD初始化bsd_bufferinit之后、原IOKitInitializeTime之前，显式诊断分支执行IOSleep(100)并返回编译停点id19。独立RaphaelBootCpu实际stage5/registered1，physical timer INTID18，19200000Hz，timer_irqs2/EOI2/IPI0；nonce/MMU/动态线程栈和异常栈/early/pmap/GIC/video均通过，101.773秒自动回Android并正常重启清理。源码构建223846Z（887记录）、内核结构native-bsd-kernel-structure.json、QEMU224644Z39项；主机从实际链接bsd_init0x120帧与原首线程0x50帧得到368字节，不泛化为任意SP。原30秒RTC发现未跳过，本轮停在其之前。摘要UniXNU-raphael/evidence/native-bsd-scheduling.json。只证明这段真实调度与唤醒；根卷、用户态、手机桌面仍未验证，下一重点为本机UFS与系统卷读取。


2026-10-31：手机已通过原 machine_lockdown（222524Z/id17）及 PE_lockdown_iokit 返回（id18，最新摘要 native-iokit-matched.json）两个停点；nonce、MMU、五段备份恢复、原 POST、异常栈、pmap、GIC和视频完整验收，均自动回 Android 并完成正常重启/root/临时属性清理。id17 PC0xfffffff007a001b0，462012字节delta，101.784秒回Android。v8恢复合同新增原16KiB __KLD/__KLDDATA，以及从实际 arm64_replace_bootstack 指令、_percpu_slot_cpu_data+32 和原 EXCEPSTACK_SIZE 推导的新异常栈；逐页现场与主机独立重建。QEMU222226Z/222616Z各39项。早期QEMU220014Z跨2MiB返回代码执行映射缺陷、220536Z旧异常栈假设、222101Z生产者/解码范围计数不一致均保留；已修并验证，未把失败移到手机重试。共享范围函数ASan/UBSan18例通过。CPU驱动NS两安全状态适配已完整构建；id18尚未观察到其start/IRQ执行，继续以原BSD中的实际线程让出和定时唤醒验证，不能把启动匹配等同于驱动就绪。源版本未刷新，原备份未改动，runtime-only未重读boot分区。

桌面依赖仅QEMU：修正显式易失无密码scratch Data的AppleKeyStore lock state为原21H461判断需要的3；完整内核214247Z与预链接214335Z通过，VM480449的220605Z快照已有65376个真实完成帧，reject0，但截图仍为启动进度，尚未出现桌面。原datamigrator100已经越过PreBoard等待，当前在真实迁移插件同步调用；backboardd等待原迁移完成。没有修改原系统文件、伪造迁移完成或解锁。仅QEMU，未部署125MB系统候选到手机。手机系统卷UFS读取仍需实现，首次桌面/基本操作/GPU与外设均未验收。


2026-10-31：实机212551Z通过原首线程更深初始化，在OSKextRemoveKextBootstrap之前的独立pre-lockdown停点捕获（id16，PC0xfffffff007a00130、LR0xfffffff0072d4770、SPSR0x60000204）。nonce/MMU/early/pmap/GIC/platform/video完整通过，原POST通过；103页活动页表稀疏65938字节、三段delta461292字节，106.282秒自动回Android，正常重启/root/清理通过。QEMU212342Z为39项、构建212445Z；摘要UniXNU-raphael/evidence/native-pre-lockdown.json。尚未释放启动元数据、machine_lockdown或IOKit驱动匹配，未证明正常XNU IRQ、手机根卷/用户态/桌面。后续须先扩展释放/权限变化的严格恢复合同，不能只移动停点。

2026-10-31：手机原 POST 与首线程解除中断屏蔽已通过。UTC 211627Z 临时启动完整 nonce/MMU/early/pmap/GIC/platform/video 验收通过，原 PC 0xfffffff007a00128、LR 0xfffffff0072d4640、SPSR 0x204；编译进独立诊断内核的返回桥避免运行时修改原 POST 的受检 text，原 POST 状态0和 crypto 函数表由原变化记录重建。约101.833秒自动回 Android，正常重启/root/清理通过；runtime-only 未重新读 boot 分区，无 flash/erase。摘要 UniXNU-raphael/evidence/native-irq-unmask.json。未证明正常 XNU IRQ/CPU 驱动、根卷、用户态或手机桌面。

本轮修复两处容量不一致：205544Z活动页表快照在65438字节耗尽旧64KiB容量，捕获不完整而严格拒收；首次扩到128KiB的210822Z遗漏SEC原64KiB上限，整份回传被丢弃，该轮停点未知。统一RAPHAEL_NATIVE_PMAP_SPARSE_BYTES与生产者/SEC实际范围检查，ASan/UBSan九项边界用例、libfdt最大记录1588263字节/剩余508889字节、211359Z QEMU39项通过后，211627Z本机完整验收。失败原记录保留。

桌面侧仅QEMU：新增显式非零16字节 /chosen/unixnu-platform-uuid 的独立平台UUID回退，原Apple身份路径优先。203205Z完整构建887记录、203517Z预链接通过；开发VM使用明确uuid5身份，203631Z实例已观察原平台UUID发布，configd越过gethostuuid。210756Z原lsd已结束应用注册并进入服务循环，SpringBoard187越过LS数据库等待，当前等待BKSSystemShellService check-in；backboardd等待原DataMigration，datamigrator仍有PreBoard相关信号量等待。已有12帧但截图仍黑，不是桌面。原系统文件、迁移完成状态和用户态返回值未修改。未同步上游；旧paused VM339287因WSL内存压力释放，文件保留，当前VM421905保留。



2026-10-31实机201516Z：原PE_init_iokit已完整返回，现场PC0xfffffff0072d4624，448908字节变化恢复，nonce/MMU/early/pmap/platform/native_video及新增GIC寄存器恢复读回通过，100.557秒自动回Android，正常重启/root/清理通过。QEMU201243Z 39项、构建201338Z；摘要UniXNU-raphael/evidence/native-iokit-return.json。本轮GIC变化0，证明IOKit基础初始化而非驱动匹配/CPU驱动或正常IRQ；StartIOKitMatching在后续PE_lockdown_iokit。新增GIC合同仅覆盖独立boot-CPU驱动实际会写的本地资源/ICC，不证明Secure或完整GIC所有权。下一步保留原异步向量后解除IRQ屏蔽，正常IRQ投递仍未知。


2026-10-31实机200312Z：原首线程前缀已经执行到PE_init_iokit入口；nonce与各恢复门禁通过，101.811秒自动回Android，正常重启/root/清理完成。新栈仍为16KiB/4页，现场SP等于原栈顶减实际caller80字节帧。QEMU200036Z 38项、构建200208Z，摘要UniXNU-raphael/evidence/native-iokit-entry.json。此时DAIF仍全mask，IOKit体/平台CPU注册/正常XNU IRQ未执行。继续IOKit必须新增其实际GIC配置的保存恢复合同；已有原CPU驱动假设可读IGROUPR，本机NS/DS=0场景不成立，不将该QEMU支持直接视为手机支持。


2026-10-31实机更新：195534Z手机已完成原load_context/machine_load_context/Call_continuation，并到原kernel_bootstrap_thread入口0xfffffff0072d4370；LR0xfffffff0074264a4、DAIF仍全屏蔽。version5将动态栈合同与旧304字节启动帧分开，原machine_stack_attach/Call_continuation指令推导thread字段和208字节上下文，现场读取16KiB栈、逐页走原TTBR1验证四页在owned grant内且不别名。nonce/MMU/early/pmap/platform/native_video通过，359148字节变化记录恢复，100.769秒自动回Android，正常重启/root/清理通过。QEMU195322Z 38项、手机构建195435Z；摘要UniXNU-raphael/evidence/native-first-thread.json。原QEMU195207Z运行恢复成功但主机解码遗漏38位VA掩码导致验收失败；原失败保留，修复后新一轮通过。首线程函数体、正常XNU IRQ、根卷、用户态与手机桌面仍待验证。


2026-10-31更新：手机193657Z已到原`load_context`首指令0xfffffff0072d488c，原LR0xfffffff0072d4200、启动栈304字节合同通过；nonce/MMU/early/pmap/platform/native_video通过，358872字节变化记录恢复，自动返回Android及正常重启/root/清理通过。原VM初始化与sched_init已返回，尚未执行load_context或真正线程栈切换；正常XNU IRQ、根卷、用户态、手机桌面均未验证。对应摘要UniXNU-raphael/evidence/native-load-context.json。下一项是由实际链接的Call_continuation/machine_stack_attach推导动态线程栈合同，而非放宽旧启动栈检查。

## 2026-10-31：修复真实回传容量缺陷；手机 VM 初始化完成已验证

193111Z手机实测通过：原 `vm_mem_bootstrap` 完整返回，在原 `_atm_init` 首指令 `0xfffffff007336df0` 捕获，nonce匹配，native_video/MMU/early/pmap/platform全部通过，326928字节变化记录恢复，101.723秒自动返回Android，正常重启/root/临时属性清理完成。尚未执行atm_init与后续调度/线程。构建192934Z，QEMU192745Z 38项通过；完整原始记录分别为evidence/private/android-return-build与android-return-run对应目录。

已确认的源码缺陷：旧回传FDT容量1114112字节，对原手机FDT/视频/恢复记录不足。actual libfdt回归192745Z以已验证190948Z after.dtb（993135字节，包含134964字节delta）替换为QEMU vm-memory的326808字节delta，准确得到FDT_ERR_NOSPACE(-3)；2MiB可完整pack为1184979字节。最大512KiB delta并将pmap/ADT/log/map提高到相应预算时完整pack1522727字节。固定设计扩大到2MiB；SEC在XNU执行前为native early记录保留1MiB headroom，原64KiB仅供非native路径。新的FDT末端仍经过本机structural unreserved与当轮输入/保留区/重叠检查，不扩大XNU grant或下载Image，不证明隐藏DMA所有权。

191808Z旧容量vm-memory手机自动回Android但无nonce、xnu_executed=null，原失败保留。193111Z仅扩回传容量与对应早期门禁后同目标成功，支持此前缺记录由回传溢出造成；不能据此给无回传185202Z追认某个XNU停点。验证脚本scripts/validate_native_fdt_capacity.py，回归报告artifacts/native-fdt-capacity/20261030T192745.225034Z-9a18t0u6/report.json。

后续原load_context入口已从实际链接代码推导：arm_init208 + kernel_bootstrap96 =304字节，原BL调用点0xfffffff0072d41fc，目标0xfffffff0072d488c；QEMU193207Z 38项通过、变化358776字节，手机构建中。它仍在首次线程切换之前，不是正常IRQ/调度或用户态证明。

桌面QEMU191924Z已完成29081帧与实际只读Data快照（248426496字节驻留、3200目录/文件项）；原进度条约65%。DataMigration原10分钟预防性stackshot指出LaunchServicesMigrator耗时，不能当崩溃或完成。后续192824Z截图约74%，仍非桌面。第一次250MB稀疏快照超主机60秒采集上限，原失败和部分文件保留；新增显式host capture-timeout=300后完整捕获/解析通过，不延长guest运行时间、不修改guest或原盘。手机根卷/用户态/桌面/触摸仍未验证。


## 2026-10-31：手机进入 VM 初始化入口；原系统迁移继续推进

手机临时启动（UTC run `20261030T190948Z`）通过：原 XNU 经 `kernel_bootstrap` 前缀，到 `_vm_mem_bootstrap` 首指令 `0xfffffff007a0e6fc`；实际LR `0xfffffff0072d3b54`、SP `0xfffffff007bbfed0`与链接代码的304字节帧一致。nonce、native_video/MMU/early/pmap/platform全部通过，134964字节变化记录与三个可变段恢复通过；106.421秒自动回Android，正常重启/root/清理完成。尚未执行vm_mem_bootstrap体。源码新增显式 `vm-entry` 点，仍用version4的512KiB预算；QEMU190428Z的38项通过，手机构建190651Z。失败190234Z为结构检查尚未接入id8，未运行手机；修复后保留原失败。

此前vm-ready手机185202Z无本轮nonce回传，xnu_executed=null，停点与复位原因未知。新对照证明相同内核/视频/arena/恢复版本可进入VM入口，下一单变量候选为 `vm-memory`：原vm_mem_bootstrap返回后、atm_init首指令；它不等同于后续STARTUP_SUB_OSLOG、调度、根卷或桌面。

QEMU同一原系统候选，185212Z与190337Z分别完成21515/23660帧，reject0，实际截图仅原进度条（约46%/52%），尚无桌面。原datamigrator已在迁移插件的同步请求，SpringBoard26仍等待Launch Services数据库；原文件和用户态代码未修改。190337Z实例Data实际驻留248303616字节，读363/写5361，失败0，仅模拟器易失Data。后续延续带匹配DWARF只读Data快照以检查具体插件和数据库推进。

固定上游main仍f0721e9745c45ad2600cd69c74730f1cca55d56a；本轮无同步。手机桌面、基本交互、GPU/外设均未验收。


## 2026-10-31：首个原系统非黑画面（QEMU，尚非桌面）

独立无密钥状态回调与固定AppleKeyStoreState已编译/预链接：183534Z构建887记录通过，184007Z候选125157376字节、未定义0；185107Z原组件主机边界断言通过（Linux宿主fixture补常量、cstdint与括号，未改原驱动/断言）。新开关默认关闭，仅QEMU scratch Data允许显式启用，不提供SEP、密钥、密码或数据保护能力。

同候选QEMU184151Z初轮120秒未到帧目标，原report passed=false保留。延续184438Z observer通过，真实状态查询246次、53次open、状态服务stage2；原用户态经IOSurface/原IOMobileGraphicsFamily完成5847次validate/CPU呈现/完成通知，reject0，首次8帧像素样本非黑957。实际qemu-screen.png已打开检查：黑背景上的原系统白色进度条，是可见系统启动/迁移画面，尚不是桌面。没有用户态指令补丁、伪造解锁或迁移完成。原307598实例保持paused供比较；已核对身份并退出被它替代的旧300351以释放RAM，原文件保留。

手机VM候选：新version4仅用于vm-ready（原sched_init首指令），由实际kernel_bootstrap的96字节帧与arm_init208字节帧推导304字节，调用后LR独立匹配。原VM/zone/map bootstrap真实运行后，QEMU184725Z到达目标但330456字节完整变化记录超旧256KiB容量，恢复三段成功但验收正确失败。version4独立512KiB记录预算，旧版本仍256KiB；184935Z QEMU38项通过。185108Z手机候选构建/结构通过；185202Z临时启动约106.102秒自动回Android，但nonce不匹配且无本轮SEC/MMU/early/platform回传，xnu_executed=null，验收失败。正常重启/root/清理完成；停点与复位原因未知，不重复同一不可读镜像。

手机182120Z续验通过：native-video+72 MiB候选181929Z经原DarwinBoot真实退出服务，执行原XNU到kernel_bootstrap首指令；native_video/mmu/early/pmap/platform全部通过，nonce匹配，106.168秒自动回Android，正常重启/root/清理通过。全屏恢复通过，未证明持续XNU scanout、kernel_bootstrap体或桌面。当前最深PC不变，但首次在此点保留真实视频交接。

桌面侧正在集成固定AppleKeyStoreState 42ff83e08b2265fe741d4adaf084bebe003452ba与独立RaphaelOfflineKeyStore回调，显式raphael-offline-keystore=1且只允许QEMU易失scratch Data；默认关闭，不提供密钥/密码/数据保护操作。原21H461 AppleKeyStore状态查询selector7/14/17/35已从原cache只读指令核对；候选尚未编译/运行验收。PreBoard主循环证据不能等同于解锁或可见界面。

## 2026-10-31：真实视频交接与桌面依赖定位（续）

目标仍为 Redmi K20 Pro 实机真实桌面；本轮未同步上游，通用 main 固定 f0721e9745c45ad2600cd69c74730f1cca55d56a。

源码：新增 NativeVideo.c/头文件与默认关闭 PcdRaphaelNativeVideo，经现场 GOP QueryMode/Boot_Video 六字段合同保存全屏；稀疏 SEC 对实际占用区逐项做 framebuffer 重叠检查，恢复失败保留唯一备份。独立 arena 允许56/72 MiB，72 MiB为52 MiB普通堆及20 MiB FAT，原现场保留/重叠门禁保留。不是隐藏 DMA 所有权证明。actual-C ASan/UBSan 24项：artifacts/native-video-host/20261030T175807Z/report.json；72 MiB装载QEMU 25项：artifacts/native-staging-qemu/20261030T180610.438351Z-3hwb8aum/report.json；72 MiB bootstrap恢复QEMU 38项：artifacts/native-staging-qemu/20261030T181346.413952Z-2w7lslbv/report.json。QEMU无本机显示硬件模型。

手机：evidence/private/android-return-run/20261030T180938Z 通过原DarwinBoot BeforeExitBootServices装载检查；现场GOP base0x9c000000、1080x2340、stride4320、BGRA32，原boot_args六字段一致；原18,463,480字节XNU十段/参数/ADT检查通过，全屏2,527,200像素恢复差异0，匹配nonce并自动返回Android及正常重启清理。该次xnu_executed=false，不是XNU视频运行或桌面。runtime-only未重复读取boot分区哈希，无flash/erase。失败175307Z（稀疏空洞误判）及180205Z（56 MiB堆不足）原记录、清理证据均保留；未重复原失败镜像。

桌面QEMU：173610Z延续快照中validations/kicks/frames/retired各14，bytes26880000，reject0；14帧在attached时已存在，900秒未捕获新提交；实际qemu-screen.png纯黑，不能验收桌面。Data快照180648Z实际7751项，仅模拟器易失盘。原datamigrator101线程栈与本体代码匹配证实停在 waitUntilPreboardDidFinishUnlock 的无限信号量等待；本体slide0x10b3000由实际代码匹配得出。未伪造解锁、迁移完成或修改原系统指令。

新增PreBoard详采：181829Z只读observer已采PID267，原cache UUID/现场shared_region slide匹配；PreBoard主线程已在UIApplicationMain→UIApplication _run→CFRunLoop，另一路等待MCProfileConnection checkIn；并非PreBoard尚未执行。完整栈artifacts/host-dyld-format/preboard267.json。下一关键问题是原PreBoard为何未产生解锁完成/可见界面，以及本机kernel_bootstrap体与持续内核运行；不是继续等待更多分钟。

手机最深已验XNU仍085718Z的kernel_bootstrap首指令；native-video+72 MiB+bootstrap候选181929Z已构建/结构通过，尚待实机。当前125MB桌面内核尚不能装入20 MiB FAT；手机持久存储、持续调度、系统scanout、触摸与真实桌面均待验证。首次桌面、基本操作、GPU/外设分别验收，不承诺日期。

## 2026-10-31：显示提交跳过原因与逻辑状态修复（QEMU）

目标仍是本机可见、可基本操作的系统桌面；首次桌面、基本交互、GPU/外设分别验收。用户本轮授权的上游刷新已单独完成，此后未自动刷新。手机 ADB 当前为 device，本轮没有手机启动实验。

原用户态真实提交记录 `artifacts/native-xnu-qemu/20261030T170256.538941Z-live-titc3u4z/debugger-observation.json`：原 backboardd 的 CPU 软件绘制后，原 selector4/SwapBegin 与 selector5/SwapEnd 均返回0；validations/kicks/frames/retired仍0，不能把API成功当呈现成功。此前动态线程读取器的EL0/KPTI错误已改为从同轮EL1实际TTBR1/TCR出发，只读走原页表，QEMU物理读取视图finally恢复；170154Z真实backboardd原指令命中且observer completed通过，未修改guest寄存器/页表/代码。

同一保留QEMU上的定点只读追踪 `artifacts/host-dyld-format/provider-live-20261030T171128Z/observation.json` 证实：原provider178收到请求；内部请求valid=1，surface0非零，其余surface0，两个rect均(0,0,800,600)，flags=(1,0,0)，尺寸800x600；原display+0x16cc为0，原代码将skip设1，跳过原queue/validate并返回0。软件地址/偏移均属于21H461原显示家族，不是手机MMIO或RAM参数。

独立驱动改为经原setDisplayState同时声明逻辑requested=1、powered=1（原先只声明powered）。这是继承framebuffer的始终逻辑开启策略，不实现面板电源控制。构建脚本对原setter四个读写指令及原submit的skip条件增加精确ABI门禁；未修改原系统二进制/返回值。主机完整构建 `artifacts/native-bootstrap-attempt/20261030T171408Z/report.json` 通过，887份编译记录；预链接/结构 `artifacts/desktop-prelink/20261030T171433Z/inspection.json` 通过；同候选ABI `artifacts/20261030T171438.288857Z-2281d0po/report.json`。新QEMU `20261030T171438.584191Z-ukcj37dm` 正验证真实IOSurface→校验→CPU复制→原完成路径，结果待补。Python语法检查与git diff --check通过。

运行结果补充：新候选首轮120秒未到帧目标（report passed=false，debugger_timeout=true，保留）；后续同一QEMU延续300秒 `artifacts/native-xnu-qemu/20261030T171742.307821Z-live-i1z09noa/report.json` observer completed=true，原SpringBoard/backboardd和7个显示client已存在，但validations/kicks/frames/retired仍0，没有目标帧。该结果不证明修复已生效，正在读取新候选原requested/skip决策。构建候选125145088字节，未定义0；摘要 `UniXNU-raphael/evidence/desktop-display-logical-state.json`。

补充：新候选定点provider复核 `artifacts/host-dyld-format/provider-logical-on-20261030T172520Z/observation.json` 在300秒内无目标命中，不能据此升级状态修复或呈现结论。该轮前置EL0内核地址读取错误保留在172427Z失败目录；后续先经原unix_syscall进入EL1再安装原指令匹配断点。新候选300秒快照已按原cache UUID/实际task slide符号化：SpringBoard138当时等待LS数据库同步回复，backboardd原IOMFBServer绘制线程仍在CFRunLoop；仅是采样，不判定死锁。两份符号结果见 `artifacts/host-dyld-format/springboard138-logical-on.json` 与 `backboard57-logical-on.json`。收尾QMP确认300351和新307598均paused；旧302788进程已不存在，原因未核实，旧文件证据保留，不再视为可延续实例。本轮源码修复具备完整构建证据，但无新呈现帧或手机系统进展。

手机证据仍为085718Z原kernel_bootstrap首指令，未运行该125MB系统候选；无手机根卷、用户态、帧、桌面或触摸结论。旧20MiB FAT/56MiB arena/256MiB grant不能直接承载该系统。后续仍需手机持续调度与载荷/内存/存储/scanout/HID验证。


2026-10-30：用户授权一次上游同步并以手机进入可见、可基本交互的系统桌面为目标继续开发。

## 本轮源码与环境

- 上游 main 从 40d21cc65171c3a24faa130a2a8e899f85790485 快进到 f0721e9745c45ad2600cd69c74730f1cca55d56a，3 个提交只更新设备文档，运行时依赖未变。
- 候选 feat/ipados27-gpu-parity 已获取到 310fb75edd53fff5f432066d858dd0ae9403a521；未将其 A740/SM8550 实现当作 A640/SM8150 支持。
- 本地未提交修改及未跟踪文件已在 ignored 私有 continuation 目录保存。原备份未改动。
- 手机 ADB/root 当前核查正常；重新只读采集 live FDT。

## 当前阻塞及修复

实际产物和本次 live FDT 均使用 watchdog 0x17c10000/0x1000。旧 NATIVE-PLATFORM 文档的 0x17be0000 为十六进制转写错误，不是产物所用地址。
SEC 新增 watchdog 映射时错误要求 /soc 的 ranges 为空。实际 ranges 为 child=0,parent=0,size=0xffffffff 的显式恒等映射，故旧条件必拒绝。此时 Android-return 尚未完整初始化，可能经复位回 Android 丢失易失 FDT；这是源码可确认的拒绝路径，尚不能由它重建过去各轮的全部执行经过。

新增 RaphaelFdtRootIdentityRange，核对根总线层级、cells、覆盖长度及精确恒等翻译，拒绝缺失/畸形/非恒等/重复覆盖/越界。未引入其他设备地址。

## 主机与镜像检查

- 本次 live FDT 的实际 C 回归 21 项通过：artifacts/fdt-identity/20261030T070239Z。
- QEMU startup 目标 38 项通过：artifacts/native-staging-qemu/20261030T070321.696336Z-2rk8niat。仅模拟器。
- 私有手机镜像：evidence/private/android-return-build/20261030T070438.577265Z-44yg5vzb；编译与 FD/PE 结构检查通过。
- 镜像 SHA256：4ff1ed003322e46ba29e9e5e1de8a04b637a1465f41000b893755257f6de318a。

## 本轮实机实验（运行前定义）

假设：修复恒等 ranges 校验后能经过 SEC watchdog 资源门禁，当前 XNU 可越过 console 并到 machine_startup 入口。
正结果：匹配本轮 nonce，native-MMU/platform/PC 及 watchdog arm-stop-restore 回传全部通过。
负结果：匹配 nonce 的拒绝/异常可判定具体阶段；若只有普通 Android 返回则停点仍未知，不当作 XNU 进展。
恢复：现有已单独测试的硬件 watchdog 和 Android-return；runner 只临时 fastboot boot，无 flash/erase；故障不盲目重跑相同镜像。

## 桌面验收

1. 首帧：真实目标用户态桌面产生画面并保持至少60秒，非预制图片或UEFI菜单。
2. 基本交互：本机输入能操作桌面、打开/退出基本应用，连续操作10分钟；触摸与外接输入分别记录。
3. GPU与外设：A640命令/fence/渲染/呈现实测，外设逐项验收。

核心未知：所选 iPadOS 用户态在本机缺少可用 GPU 后端时是否具有可落地的桌面渲染路径；CPU framebuffer复制本身不能回答。持续内核运行、系统根卷和匹配的用户态依赖同时是硬阻塞。本轮先修正阻止进入内核的具体代码错误，再推进该链，不承诺日期。

## 2026-10-30 实机结果：machine_startup 入口通过

run：evidence/private/android-return-run/20261030T070604Z。
匹配本轮 nonce；native-MMU、platform、pmap、early、有效装载及 watchdog arm/stop/restore 通过；PC=0xfffffff007427d30，为当前内核 machine_startup 首指令。原 console、idle、timebase 和 CPU 早期初始化前缀已执行。machine_startup 函数体、正常 XNU IRQ/调度、根卷及用户态仍未执行。
86.505秒自动回 Android，后续正常重启、root 及临时属性清理通过。runtime-only 未重算 boot 分区；runner 无 flash/erase，原备份未改动。

## 系统用户态依赖准备

通过固定上游 OS profile 从 Apple CDN 取得 17.7.11 (21H461) j120ap 的原 kernelcache、DeviceTree 和两组 trustcache，均保存在 ignored artifacts/desktop-system。Apple DeviceTree 仅用于 OS ABI 资料，不作为本机板级硬件输入。
新增 scripts/prepare_desktop_kernel.py，直接调用固定 XnuPrelink，生成与本机原生 XNU 组合的 51,306,496字节候选，包含 profile 选择的 APFS、存储、安全、HID、IOSurface 等 OS 依赖；未覆盖 native-only 实机内核索引。
产物：artifacts/desktop-prelink/20261030T071155Z。15段 Mach-O 结构、入口、段范围及未定义符号0通过；候选尚未通过运行验证，不标记为手机可启动。
Apple OS 和 SystemOS 镜像正在主机准备；没有安装到手机。

## 2026-10-30 预链接系统内核运行与原系统磁盘

桌面模式使用独立 raphael_desktop_defconfig，将 crypto bootstrap 设置为 prelinked，保留源库及原系统 POST，避免 source-provider 在原 corecrypto 注册后重复初始化。native-only 配置与证据索引不变。
构建：artifacts/native-bootstrap-attempt/20261030T072115Z，887条编译记录。
预链接：artifacts/desktop-prelink/20261030T072416Z，50,995,200字节，15段及未定义符号0检查通过。
首次运行暴露缺少 /product；加入所选 OS profile 的 root/chosen/product/defaults 软件身份，以及上游生成器使用的空 /chosen/manifest-properties 后，通过 QEMU root-discovery 入口目标。
QEMU：artifacts/native-xnu-qemu/20261030T073936.317680Z-3grox8vg。实际执行 machine_startup/kernel_bootstrap/kernel_bootstrap_thread/PE_init_iokit/bsd_init/IOFindBSDRoot；ArmDTPlatform configure返回成功。CPU已注册并到stage2，但本轮未等待CPU start返回或timer IRQ，不能称完整CPU/timer生命周期验证。没有手机运行该预链接候选。
软件身份是OS兼容资料；CPU、GIC、RAM、MMIO仍只来自同轮QEMU FDT，未导入Apple硬件参数。

Apple OS/SystemOS均完整取得。scripts/prepare_desktop_disks.py 将OS的UDIF解压为只读raw磁盘，SystemOS为raw直接链接；GPT/分区表CRC、APFS超级块与卷资料可读。最新记录 artifacts/desktop-disks/20261030T075713Z/report.json。
OS原始磁盘6,077,580,800字节，APFS从GPT第34扇区即17,408字节开始；卷UUID 04769d26-2ca0-4825-b443-e2e5f88300f2。SystemOS原始3,303,014,400字节，APFS偏移0；卷UUID 8846fe78-2910-4297-af97-d59bb6f8fc16。这些仅为本次原镜像的软件磁盘布局，不是手机分区或RAM布局。
主机安装Ubuntu libfsapfs-utils并只读挂载OS，确认/sbin/launchd存在（561856字节）。SystemOS读取容器/卷元数据成功，但当前旧版fsapfsmount挂载后守护进程未保持，尚无其目录树的验证。

新增scripts/qualify_desktop_storage.py，复用固定上游的通用IOStorage ABI推导，改为显式当前tree/candidate/live-report参数；实际源DWARF推导OSMetaClass成员偏移，当前QEMU读取真实类元数据。190槽、176内核绑定及0x90/0x88实例大小通过。live report：artifacts/native-xnu-qemu/20261030T075355.058030Z-2zbhks4u/report.json。
新增raphael_desktop_storage_defconfig及build-raphael-storage-bindings.py，只给独立模拟器候选接入上游通用SoftwareAES/VirtioMmioBlock，软件虚地址来自固定原kernelcache与当前ABI结果，未导入其他手机地址。构建artifacts/native-bootstrap-attempt/20261030T075542Z，887条记录通过；预链接artifacts/desktop-prelink/20261030T075751Z，51,056,640字节，结构通过。
实盘读、APFS内核挂载、launchd执行及桌面画面均仍待运行结果；未写入手机任何系统卷，也没有将VirtIO当手机UFS适配。

## 原OS实际读盘通过

run：artifacts/native-xnu-qemu/20261030T080140.880536Z-gpiek95y，passed=true。NativeVirtioBlock已读取OS磁盘首512字节；11,870,275扇区与原始镜像容量一致，ready=1/read_requests=1/read_failures=0，实际读取内容与源首扇区一致。这仅证明QEMU中的原OS块I/O；尚不等于APFS挂载或手机UFS工作。
模拟器显式使用virtio-mmio.force-legacy=false，原驱动要求VirtIO 1.2 modern MMIO。所有模拟器设备地址仍来自同轮dumpdtb。
修正QEMU观察器的CPU-return关联：IOService公共调用点被多个服务复用，单靠LR地址会误认其他start返回；现在同时要求与实际RaphaelBootCpu入口SP一致。旧075830轮因此停止于观察器断言，不能当作CPU驱动启动失败。080140轮排除了29个无关返回；CPU仍在stage2，本轮没有CPU start返回或timer IRQ通过的结论。

复现（本轮固定本地源码，不fetch）：
```sh
python3 scripts/build_native_bootstrap.py --desktop-storage --storage-audit artifacts/native-bootstrap/raphael/ipados-17.7.11-21H461/raphael_desktop/tree/build/storage-abi/interface-audit.json --storage-candidate artifacts/desktop-prelink/20261030T072416Z/kernel.macho
python3 scripts/inspect_native_kernel.py --build-report artifacts/native-bootstrap-attempt/20261030T075542Z/report.json --index artifacts/desktop-storage-kernel-structure.json
python3 scripts/prepare_desktop_kernel.py --kernelcache artifacts/desktop-system/ipsw/21H461/kernelcache.decompressed --inspection artifacts/desktop-storage-kernel-structure.json
python3 scripts/run_native_xnu_qemu.py --inspection artifacts/desktop-prelink/20261030T075751Z/inspection.json --os-profile --system-disks artifacts/desktop-disks/20261030T075713Z/report.json --stop-at block_read --boot-cpu physical --kalloc-zones 200 --observe-seconds 60
```

## 正常内核、APFS和认证边界

080300.970778Z-jzw_jnu2：CPU start同入口栈真实返回成功，stage5，169次timer IRQ和169次EOI。原AMFI panic为No PMGR；不是CPU驱动失败。QEMU后续在/defaults设置vmm-present=1，如实描述仿真环境，原AMFI自行选择虚拟机分支；该声明不得用于裸机手机。手机PMGR接口仍需独立实现。
080657.377142Z-0n7bqov5：无panic但60秒内未到launchd加载，CPU正常idle；不以超时PC单独推定唯一原因。
080946.959875Z-cuqo59g_：明确使用原OS实际卷UUID的IOMedia root-matching，并通过现有OSKextLoadKextWithIdentifier加载原APFS（offline-apfs-load=1）。进入vfs_mountroot后停在原bsd_init的rootvp not authenticated after mounting；源码该路径仅在vfs_mountroot返回0后执行。说明已走到APFS挂载后的根认证检查，不代表认证或用户态成功。263次timer/EOI；OS、SystemOS和ESP均读到首扇区。
该APFS probe自身的registered计数为0，不用它声称VFS注册成功；实际挂载后的检查路径是目前更强的运行证据。

根认证处理沿用上游VerifiedRoot：两份完整原镜像、实际卷UUID、同一私有RSA3072所有者公钥生成独立策略；每次DMA完成后CPU快照逐块验证，通过真实挂载设备绑定才可走owner-root授权。原Apple FSIOC_KERNEL_ROOTAUTH调用和拒绝分支保留；owner-root替代授权必须单独报告，不能称Apple原厂封印认证。此处有序块摘要是实际根卷运行认证输入，不做重复的工程文件哈希审计。
私有策略：evidence/private/desktop-root-policy/20261030T081351Z；目录0700、私钥0600，未提交。
原VerifiedRoot小型合成用例通过7组正反例；仅将macOS动态库编译参数适配为Linux shared/PIC，并使用现有交叉SDK，测试源码保留在artifacts/desktop-root-host-check/linux-adapted-check.py。这是host结果，尚非目标运行认证。
新增raphael_desktop_root_defconfig和独立编译recipe，不改native-only手机路径。
Apple原两组trust模块解IM4P后按DarwinBoot格式打包，61356字节，bundle摘要7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7，正好命中固定OS profile允许值。没有加入自有CDHash。记录artifacts/desktop-trust/20261030T081913Z。

## 私有根策略集成候选

构建artifacts/native-bootstrap-attempt/20261030T082251Z通过，887条记录；独立结构artifacts/native-kernel-inspection/20261030T082357Z，native 91,520,672字节/未定义符号0；预链接artifacts/desktop-prelink/20261030T082358Z，124,362,752字节。
新增私有policy编译recipe使用VerifiedRoot原C实现、XNU真实crypto adapter、原可选小型自检和两份实际镜像策略；verified-bundle block驱动以只读受保护的表校验DMA快照。没有复制其他手机的参数。
首次新tree bootstrap link缺少策略符号属预期archive准备前失败；后续三轮失败及日志保留：081717Z和082004Z为复用Apple compile record携带Linux不支持的警告/可选include目录；082141Z为Mach-O内核不能保留可选UFS弱未定义符号。最终按项目其他archive的既有方式规范化为Wall/Wextra/Werror；显式提供“此模拟配置没有UFS”的负返回-1，不接受设备、不伪造认证。全部在独立root配置中。
082418.383198Z-0nyxfuox：512MiB QEMU RAM下原DarwinBoot拒绝Out of Resources，未进入内核。这是loader真实资源失败；未将候选放入手机。
随后允许runner显式--memory-mb 1024（仅模拟器），仍使用256MiB loader窗口并从该轮FDT重新导出RAM/设备资源，待运行结果。

## QEMU所有者根认证与PID1真实EL0执行

082616.833937Z-adtzceul：1024MiB模拟器中，原APFS根挂载后的owner-root认证通过，accepted=1/decision=1/readonly=1，实际mount_device与selected_device均16777222；Apple原厂认证仍返回80，未称原厂seal通过。真实达到load_init_program入口。

084049.094430Z-r1qq2imh：同一候选和两原卷，通过只读调试器观察120次PID1系统调用。实际p_pid=1、p_comm=launchd，proc与该时刻initproc相同；用户CPSR低5位为0、ESR为SVC64、PC前指令svc #0x80，真实用户态指令已执行。结构偏移取本次systemcalls.o的DWARF，含匿名结构父级偏移。exec会替换proc，不能要求它仍等于load_init_program入口的旧指针。083738轮因此被过严的旧指针条件拒绝；083533轮仅停unix_syscall入口，未接入ABI，不升级为完整EL0认证。

捕获的原用户态写出“hello from launchd.1”，随后“failed to lookup preboot: 2”和“ignite() returned 2”。这是目标用户态实际依赖缺口；不把PID1/dyld早期代码称为launchd main或桌面。新增独立desktop-runtime配置，准备复用上游owner-managed OS/SystemOS只读native union、双卷认证后才发布的启动标志/owner manifest；明确替代原Apple ignition路径，不伪称解决了原厂Preboot或seal。可写Data尚未接入。上述均仅为QEMU结果，手机权威停点仍machine_startup入口。

## 实机越过machine_startup

独立bootstrap检查点从当前Mach-O确认machine_startup的真实五条指令：保存16字节帧、machine_conf调用、恢复帧、尾B到kernel_bootstrap。故检查点仍使用arm_init原208字节栈和原LR；没有借用QEMU栈地址，也未改变wire尺寸。policy保留字段目标编号6、结构检查和固件门禁同时扩展；machine_conf源代码仅更新machine_info。

QEMU 20261030T085055.716211Z-gspymcdr：38项通过。首次084851轮在结构检查仍限制旧编号5处被拒绝，未运行；修正后完整重新构建。
手机build evidence/private/android-return-build/20261030T085225.611309Z-jndwlaws，镜像3f74afe2df97c786749f7ffd2d4ca9a89c8af9e6779808c0875ad80e3fc4adec；run evidence/private/android-return-run/20261030T085718Z。匹配nonce，PC=0xfffffff0072d3ae4，为kernel_bootstrap首指令；machine_startup函数体/machine_conf已执行，定时器、MMU/pmap和内核状态恢复通过。85.226秒自动回Android，正常重启/root/临时属性清理通过。kernel_bootstrap函数体、XNU正常IRQ/调度、根卷和用户态尚无手机证据。runtime-only未重读boot分区哈希，未flash/erase或改原备份。

系统组合候选：desktop-runtime build 20261030T084603Z/887记录，native 91,543,312字节；prelink 20261030T085106Z为124,387,328字节，结构检查通过。085154.575977Z-2n8xtxqv在QEMU再次观察120次原PID1 EL0调用，已越过此前ignition错误进入原cache预检；尚不证明全部cache装载或launchd main。


## 原 launchd main 与实际内存预算（2026-10-30）

`artifacts/native-xnu-qemu/20261030T091114.741686Z-7zfhmr_5/report.json` passed，
`original_launchd_main_executed=true`。由本次原 Mach-O LC_MAIN 解析 entryoff=85896，
跟随原 dyld 初始栈和实际 ASLR；EL0 main PC=0x100faff88，main+4 完成首条原指令，
读取原16字节一致。没有改指令、原用户态文件或跳过fault/签名检查。
这只证明 main 开始执行，未证明 launchd 完成、服务图、桌面或手机用户态。

失败保留：090215Z 真实 memorystatus jetsam panic（仅256MiB内核grant）；
090540Z 仍在原cache签名预检读取；090738Z停main入口但指令页尚未驻留，
不算指令完成。现通过原DarwinBoot的真实AllocatePages给予QEMU内核1024MiB，
机器RAM2048MiB；没有关闭jetsam断言。大窗口只用于模拟器，不能作为手机RAM分配证据。
原观察器首版的作用域/页驻留错误也保留在各失败目录。

复现命令见091114Z的commands.json，核心参数：`--stop-at launchd_main --main-program
artifacts/desktop-disks/20261030T074616Z/OS-mount/sbin/launchd --boot-cpu physical
--kalloc-zones 200 --memory-mb 2048 --kernel-window-mb 1024 --observe-seconds 180`。
下一步独立scratch APFS Data；原OS/SystemOS继续只读，手机分区与备份不变。


## 独立可写 Data：原 APFS 实际挂载与读写（2026-10-30）

新 `raphael_desktop_data_defconfig` 基于 runtime；启用固定通用 `RamBlock`，
不引入其他手机的硬件参数。默认私有原 `/private/var` 从本次 OS APFS 重新读取，
39文件、166目录（包含根）和1符号链接，611715字节；UID/GID/mode取原inode。
旧FUSE的1000映射未采用。Ubuntu原libfsapfs20201107不支持压缩方法9，
独立venv安装`libfsapfs-python==20260921`后全部解压成功，无缺项跳过。

`prepare_desktop_data.py`只以exclusive方式新建普通scratch文件。
32/64MiB formatter拒绝（失败保留），128MiB可用。
原apfsprogs20231203的CPM表顺序为65/68/66/67，原Apple驱动明确拒绝其非连续排列；
依据发行版工具源码`include/apfs/raw.h`/`mkapfs/super.c`，新生成卷按65/66/67/68排列，
更新该元数据块自身的Fletcher校验，原APFS检查保持。
`md0`可发现整个容器却没有卷索引，因此实际挂载仍失败；改走通用RamBlock的IOKit枚举，
按本次scratch UUID找到真实APFS卷设备后成功。旧失败分别保留在093559Z、094146Z、
094451Z与094750Z运行目录；没有将apfsck主机通过冒充Apple驱动接受。

成功编译：`artifacts/native-bootstrap-attempt/20261030T095120Z/report.json`，887记录；
结构：095238Z，未定义0；预链接：`artifacts/desktop-prelink/20261030T095239Z`，
125100032字节，SHA256 `cafdd0d74a1feb24ab0c59c26b1c243b9585cccf5daca71c6898144eef5128c6`。
成功运行：`artifacts/native-xnu-qemu/20261030T095316.374322Z-wwitkajk/report.json`，
`emulator_data_seed_verified=true`，原APFS mount stage4/status0/readonly0，
206条创建完成、写入611715/读回611715字节完全一致。
此为QEMU内存盘，不证明重启持久化、手机UFS、系统服务或桌面。
原OS/SystemOS继续只读认证；没有手机分区或备份写入。

`prepare_user_observer_abi.py`另外从本次`subr_log.o`的DWARF解析`msgbuf`，
GDB在停止CPU后只读导出真实内核环形日志`kernel-msgbuf.log`，用于直接取得APFS拒绝原因。
它是模拟器通道，不是手机串口或手机MMU后的日志通道。


## 桌面验收与当前决定性缺口

首次桌面：原用户态的桌面/合成服务产生正确首帧，并通过XNU显示后端到手机面板，
随后能持续更新；固件菜单、启动日志、测试图案和模拟器画面均不作手机桌面验收。
基本操作：在首帧基础上，以手机触摸完成选择、滑动、打开/关闭应用、返回桌面及文字输入，
同时具备可写Data和稳定运行。GPU/外设完善：独立验证A640命令执行、同步与合成加速，
再分别验收电源、存储持久化、音频、无线、电池/温控、休眠、相机和传感器等。
三个阶段分别记录，不作同一验收或日期承诺。

| 手机桌面所需能力 | 当前分类与证据边界 |
|---|---|
| 自有UEFI可见菜单、继承GOP、实体三键 | 本机已验证；尚非XNU显示/桌面 |
| DarwinBoot→XNU MMU/pmap→machine_startup→kernel_bootstrap入口 | 本机已验证；不覆盖bootstrap函数体与调度 |
| 持续XNU线程/中断/时钟与IOKit完整初始化 | 尚需开发；独立CPU实现有QEMU证据，手机仍缺运行验证 |
| 足够内存、桌面大载荷加载与保留 | 尚需开发；旧手机256MiB grant不适合作桌面预算，QEMU1024MiB不可照抄 |
| 手机UFS、DMA/SMMU与电源接管 | 尚需开发；VirtIO/RamBlock不提供手机驱动 |
| 匹配APFS/安全/共享缓存/原launchd | 上游可复用但未验证；QEMU已验证认证双卷、原main、early boot任务完成及SpringBoard首个SVC；手机未验证 |
| 可写Data及权限、持久化 | 尚需开发；QEMU易失Data读写通过，手机与持久化未验证 |
| 原桌面服务能生成可持续更新的完整帧 | 上游可复用但未验证；qemu文档称存在CPU呈现，未在本机或本候选证明 |
| XNU显示发布、IOSurface呈现与本机scanout | 尚需开发；通用接口存在，UEFI GOP不能代替此项 |
| Goodix触摸、桌面HID与文字输入 | 尚需开发；UEFI按键不是桌面输入 |
| Adreno640及其他外设 | 尚需开发；A740代码不能作为A640支持证据 |

最影响“能否出现桌面”的未知仍是：所选原用户态能否在本机可实现的显示/渲染路径上
产生完整、持续更新的桌面帧。本轮已将通用用户态链推进到可写Data、early boot完成和SpringBoard首个SVC，
后续服务启动实验用于识别它是否真正进入合成/显示依赖；若CPU路径不可行，
A640后端将成为首帧前置条件，而非只影响后期加速。这一判断还缺运行证据。


## 2026-10-30 原启动任务链与用户管理目录修复

`artifacts/native-xnu-qemu/20261030T095736.317512Z-59_7fste` 已执行原launchd main，并观察PID2 fsck发出exit(0)。该轮总512停止预算用尽，未完成请求的256次PID1采样；不把observer预算当作guest启动失败。

新增可选事件采样和精确进程comm目标：只读GDB观察原SVC64、PID/comm/initproc，记录首次进程、write、exec/spawn、exit；4096个已选事件与300秒墙钟双重上限。不是补造系统调用或模拟服务成功。

`artifacts/native-xnu-qemu/20261030T100713.995779Z-h7s6iem7`：原main首指令和Data读写仍通过；原启动任务继续经过fsck、mount-phase-1、data-protection、finish-obliteration、detect-installed-roots、commit-boot-mode、mount-phase-2、MSUEarlyBootTask、fips、keybag、usermanagerd、dirs_cleaner、xpcroleaccountd，并启动init_featureflags。部分原工具非零退出必须保留：keybagd exit(71)，不能称数据保护完整可用。最后300秒墙钟到期，停点未证明唯一死因；尚无SpringBoard/backboardd或桌面。

原usermanagerd输出明确在保存`/private/var/keybags/persona.kb`时因父目录不存在而失败。`prepare_desktop_data.py --user-skeleton` 解析本轮固定通用 `sources/UniXNU/scripts/prepare-offline-data.py` 的空目录清单，新私有Data增加20个空目录，未预置密钥或用户记录。新目录权限是明确的本项目设计策略；已有目录、文件、符号链接及元数据保持原输入。候选 `evidence/private/desktop-data/20261030T101301Z/report.json` 为226条目、611715字节原文件内容。新卷与新的编译/运行结果分别记录，不覆盖先前失败证据。

模拟器新增显式 `--shared-data-volume`，传递原APFS的 `-apfs_shared_datavolume` 策略；不改变认证检查，不对应手机已有Data卷。


## 2026-10-30：原启动任务完成与SpringBoard首次EL0指令路径

实现：新增可选 `--user-skeleton`（仅补齐空的通用用户管理目录）、`--shared-data-volume`（原APFS共享Data策略）。运行观察进一步改为真实BSD write/exit/execve/posix_spawn入口，结构偏移从同次编译对象DWARF读取；每次原thread_setentrypoint只跟随该线程首个SVC64，平时删除全系统逐调用断点。原输入文件、guest代码和返回值未修改。事件只证明调用进入；不把write或spawn入口当作成功返回。

主机构建：`artifacts/native-bootstrap-attempt/20261030T101426Z/report.json`，887份编译记录。新native独立检查 `artifacts/native-kernel-inspection/20261030T101547Z`，未定义0；系统预链接 `artifacts/desktop-prelink/20261030T101548Z`，125100032字节，SHA256 `6bbc99ff98bae5eb097d02bea22dd4f850484bba1efbc8b2489237434ac44831`。仅QEMU候选，native-only手机索引未被替换。

实跑：`artifacts/native-xnu-qemu/20261030T101909.608665Z-0k_zigct/report.json` passed=true。226条Data初始化、611715原字节写入/读回；原launchd LC_MAIN首指令完成。原usermanagerd输出`diskSaveUserSessions Success`、创建默认用户501、加载前台用户501，及Personal/System/Default persona成功；原先persona清单父目录缺失错误未再出现。keybagd发出exit(0)，但没有SEP/系统密钥保护完成的结论。该轮同时增加目录与原APFS共享Data参数，不将所有改变归因于其中单一项。

原launchd输出`Early boot complete. Continuing system boot.`，随后请求原SpringBoard路径。PID27/p_comm=SpringBoard的真实首个SVC64检查通过：用户态EL0、ESR SVC64、PC前`svc #0x80`。**这可能仍在dyld启动代码，不证明SpringBoard LC_MAIN、backboardd、渲染或桌面首帧。** 后续原工具异常保留：sysstatuscheck exit(1)、prng_seedctl exit(13)；不能称全部系统依赖已正常。

精简结果：`UniXNU-raphael/evidence/desktop-userspace-boot-tasks.json`，排除了用户会话内容和二进制write数据。

复现使用同一固定源码与新私有Data：
```sh
python3 scripts/run_native_xnu_qemu.py \
 --inspection artifacts/desktop-prelink/20261030T101548Z/inspection.json \
 --os-profile --system-disks artifacts/desktop-disks/20261030T075713Z/report.json \
 --trust-bundle artifacts/desktop-trust/20261030T081913Z/report.json \
 --scratch-data evidence/private/desktop-data/20261030T101301Z/report.json --shared-data-volume \
 --user-abi artifacts/20261030T101845.385742Z-b8ui46pa/report.json \
 --main-program artifacts/desktop-disks/20261030T074616Z/OS-mount/sbin/launchd \
 --stop-at launchd_runtime --runtime-process SpringBoard --boot-cpu physical \
 --kalloc-zones 200 --memory-mb 2048 --kernel-window-mb 1024 --observe-seconds 300
```

手机本段仅重新确认ADB连接，未启动本125MB候选，实机停点仍为085718Z的native-only kernel_bootstrap入口。手机持续调度、UFS/PMGR、足够内存和显示后端仍是独立工作；目标尚未验收。


同候选后续观察：`artifacts/native-xnu-qemu/20261030T102530.468507Z-usp4_g3o` 将明确目标改为backboardd首个SVC，300秒到期，target未达。configd、mediaserverd、logd、driverkitd、IOMFB_FDR_Loader、watchdogd等已有真实EL0 SVC；xpcproxy已请求`/usr/libexec/backboardd`，但本轮未捕获该进程SVC。最后CPU位于内核mac_syscall路径，没有捕获panic；不能据此认定死锁、backboardd已运行或显示已接通。

当前系统内核仍明确关闭NativeMobileDisplay，未链接Legacy显示后端；原DarwinBoot本轮video几何为0，未向该候选提供GOP。下一项首帧能力是：给XNU提供有来源、被保留的显示缓冲区，接入原MobileFramebuffer/IOSurface的真实显示发布、swap和完成路径，再验证原用户态的CPU渲染。单纯延长服务采样或再显示UEFI图案不会补齐这项能力。

本段收尾：四份修改Python通过py_compile，git diff --check通过；新私有Data、seed、root策略仍被ignore。Windows ADB重新确认本机root，手机仍为Android；没有正在运行的手机实验或QEMU进程，没有分区写入或原备份变动。

## 2026-10-30 独立GOP显示服务：仅QEMU

源码：UniXNU-raphael/drivers/RaphaelDesktopDisplay.cpp；独立ABI生成/构建脚本build-raphael-desktop-display.py。原始358槽ABI按固定21H461家族验证，startHardware槽288；不修改原Apple指令，不导入其他设备MMIO。构建artifacts/native-bootstrap-attempt/20261030T123047Z/report.json，预链接artifacts/desktop-prelink/20261030T123112Z/inspection.json，匹配DWARF artifacts/20261030T123115.278461Z-9clcazk5/report.json。

显示发布run artifacts/native-xnu-qemu/20261030T123115.396442Z-d5zq9fyh/report.json：stage8、hardware_stage3、family/surface/meta/video_status均0、guard0；原registerService已返回。真实GOP base0xbc7a0000，800×600，row3200，depth32，map_length1920000。均为同轮QEMU资源，禁止用作手机参数。

用户态run artifacts/native-xnu-qemu/20261030T123229.406503Z-638wo8mq/report.json：原start真实返回true(stage6)，300秒采样结束，clients0，未捕获目标backboardd首SVC；SpringBoard首SVC及多项原服务继续执行。未采到不等于证明未启动；屏幕仍为固件内容，无surface提交或桌面。QMP已保存真实qemu-screen.png。

修正过程中失败证据保留：122106Z注册到不存在的com.apple.kernel，已修为__kernel__；122448Z旧观察器仅按到checkpoint给出passed，实际stage7/base0，不能作成功证据；122749Z暴露startHardware槽位错误，现按原指令修为288。观察器现在要求stage8及非零几何等条件。

复现：`python3 scripts/run_desktop_display_cycle.py` 使用本地固定源码完整构建、结构检查、预链接和QEMU显示发布；追加`--runtime-process backboardd --observe-seconds 300`跟随原用户态。不fetch、不操作手机。原系统125MB候选不得直接放入旧20MiB FAT/56MiB arena。

下一项是严格单层BGRA/blank surface的真实CPU呈现和原队列完成；尚无渲染能力、持续更新帧、手机scanout或触摸结论。

## 桌面能力验收表（2026-10-30；手机与QEMU分开）

| 关键能力 | 分类 | 当前证据及缺口 |
|---|---|---|
| 固件既有模式显示、菜单与实体三键 | 本机已验证 | 这是UEFI输出；不是系统桌面或系统HID |
| DarwinBoot有效加载、退出服务、XNU初始化前缀 | 本机已验证 | 最新到kernel_bootstrap首指令，函数体未通过 |
| XNU持续调度、正常IRQ与线程生命周期 | 尚需开发 | 通用CPU平台在QEMU可运行，本机尚缺后续执行证据 |
| 系统候选所需RAM、staging与完整启动载荷 | 尚需开发 | 手机原合同20MiB FAT/56MiB arena/256MiB grant不能直接容纳当前系统候选 |
| APFS/SystemOS、原launchd、独立Data及用户会话 | 上游可复用但未验证 | 通用实现与本地策略已在QEMU运行；手机UFS/DMA/SMMU/PMGR与根卷均未验证；Data目前易失 |
| 原SpringBoard与backboardd完整初始化 | 上游可复用但未验证 | QEMU原SpringBoard已进入FBS显示及LaunchServices初始化；backboardd原render_for_time命中，仍无完整初始化或桌面 |
| CoreAnimation软件渲染并持续产出完整桌面帧 | 上游可复用但未验证 | 固定原系统存在软件renderer；本候选尚无执行与连续完整帧证据，是首帧路径的关键未知 |
| 原显示家族、单层surface与CPU呈现 | 尚需开发 | QEMU已启动和发布独立Legacy服务；新单层提交/拷贝/原队列完成代码已编译，真实提交未验证 |
| 手机XNU framebuffer映射、显示保持与scanout | 尚需开发 | 固件GOP本机通过，不能代替XNU页表后的持续呈现 |
| 手机触摸/HID驱动、桌面输入语义 | 尚需开发 | UEFI三键通过；未实现系统触摸、点击/滑动和文本输入 |
| Data持久化与应用基本操作 | 尚需开发 | QEMU可写不等于断电/重启持久化，手机无应用操作证明 |
| A640 GPU与其他外设 | 尚需开发 | A740实现不能直接作A640后端；GPU、网络、音频、电源、休眠、相机等独立验收 |

三个验收保持独立：首次桌面画面要求目标手机由真实系统用户态生成且持续60秒；基本操作再要求真实输入、应用打开/退出/返回与文本输入连续10分钟，并单独验证Data持久化；GPU及其他外设要求各自驱动/提交/完成/渲染或对应功能证据。不会用UEFI菜单、预制图片、单个清屏或QEMU截图合并验收。

## 单层提交实现与未触达结果

build artifacts/native-bootstrap-attempt/20261030T124948Z、candidate artifacts/desktop-prelink/20261030T125013Z、ABI artifacts/20261030T125016.400016Z-d5in9cqm。原IOSurface getter实际指令验证后绑定，非借用其他设备surface实现；严格接受完整无变换BGRA或blank，实际descriptor范围/映射检查、标量GOP写入、dsb，再按原TAILQ单头所有权和原state/completion回收。仍未证明原系统调用这些新方法。

125016Z QEMU显示发布通过；125257Z 等待真实frame900秒，实际内核时间约565秒，原start/powered setter成功但clients=validations=kicks=frames=retired=0，目标失败，无panic/guard。大量原logd_helper文件写入被旧观察器记录，但不能据此归因backboardd。下一轮对文件写事件过滤，并按同build DWARF读取真实进程/线程状态、定向记录spawn返回；不再把未采到SVC等同未启动。

130627Z 以同候选验证新process census：显示发布仍通过，停点仅有kernel_task，读取结构通过。这是观察器接入检查，未推进用户态或手机。

## 真实依赖停点：Sandbox容器管理RPC（QEMU）

132123.935093Z-vbbzpdrp，420秒观察，未出现frame。按同build DWARF和XNU queue_enter语义读取的快照显示PID57 exec期间两个xpcproxy对象：新线程在_task_wait_to_return，原exec线程在ipc_mqueue_receive/kernel_mach_msg_rpc_common，来自原com.apple.security.sandbox __TEXT_EXEC +0x28080/+0x298c0/+0x1c000，经mac_cred_label_update_execve/exec_handle_sugid/exec_mach_imgact/posix_spawn。原Sandbox 0xfffffff005a19e94加载HostSpecialPort=25；所选原OS的com.apple.containermanagerd.plist将com.apple.containermanagerd.upcall注册到HostSpecialPort25。该证据把缺显示client收窄到原容器服务同步RPC等待；尚不能将整个系统判为死锁。

SpringBoard两线程已进入Mach消息接收及workqueue等待，未证明LC_MAIN（原首SVC仍是既有边界）；显示仍无client/swap。下一项为原containermanagerd启动与RPC回复依赖，而非继续等待GOP或复制更多显示配置。

观察器新增实际spawn返回、同build process/task/thread/queue/arm_saved_state布局、只读60秒快照和原LC_MAIN首指令完成观察。131011Z旧快照链字段计算错误被断言拒绝，132123Z已按原queue_enter元素基址修正；EL0 KPTI导致的读取失败明确保留，新版延至内核观察点采集。未写任何手机分区或改原系统二进制。

## 2026-10-30：容器服务入口与原Data日志核查

133357Z中容器服务有用户态执行快照，含dyld初始化、Mach调用及Objective-C方法解析候选；这些不能单独证明main或服务回复。135329Z的定向观察器在安装目标线程断点时失败：自定义self.thread覆盖GDB Breakpoint.thread原生属性，64位线程地址被当成主机线程编号，产生OverflowError。失败来自观察器，不是guest异常。现改为target_thread，并记录完整Python traceback；runner会向顶层传递observer failure，成功条件要求observer completed。原失败产物不改写。

134718Z已从暂停的QEMU读取134217728字节真实Data内存盘；新inspect_desktop_data.py以pyfsapfs只读解析244项，取出AKSSetup、usermanagerd及launchd日志，证据保存在同run/data-inspection。原系统生成用户keybag/persona并非本项目预置；不将文件存在称为SEP保护或持久化。快照采于服务大量启动前，不能用未出现MCM日志断定服务未运行。

为定位原服务实际PC，新symbolicate_desktop_user.py只读解析原SystemOS共享缓存及UUID匹配的local symbols/exports；头部格式取自固定Apple dyld a571176。apfs-fuse工具66b86bd525e8cb90f9012543be89b1f092b75cf3及其固定lzfse仅用于主机只读挂载，未同步UniXNU或其他活动项目源码。新增task.shared_region和sr_slide/base/size观察偏移从同build DWARF提取，ABI artifacts/20261030T135631.250809Z-uaqdmgr1。旧样本外部传入的slide明确标为未运行验证，不能冒充读取事实。

140230Z使用修复观察器及新ABI继续跟随原containermanagerd的dyld→LC_MAIN，观察上限660秒、60秒只读快照、480秒Data捕获。此条记录时运行尚未结束，结果另记。没有新的内核构建或手机实验；ADB get-state=device，手机kernel_bootstrap边界不变。

## 2026-10-30：原服务已运行，SpringBoard显示断言已定位

140230Z/141942Z已确认原containermanagerd实际LC_MAIN首指令完成；143035Z同一QEMU无全系统生命周期断点续跑后，MCM主线程在原CFRunLoop，backboardd真实用户线程及CA::Render::Server::server_thread运行。143855Z的原Data launchd日志显示SpringBoard反复SIGTRAP。它们取代此前“MCM同步RPC为当前阻塞”的暂定结论。

144310Z-live-65_ugkb5在原_exception_triage硬件断点捕获SpringBoard PID277、EXC_BREAKPOINT=6、codes=(1,0x1aa2f72ec)。本轮task.shared_region.sr_slide=0xaf18000；跨进程真实pmap只读走表取得的32字节指令与原cache逐字匹配，原符号为-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1148。原静态CFString为`failed to find the main CADisplay`，这是原指令引用字符串的静态解码，不冒充运行日志。原系统二进制和返回值均未修改。

进一步读取原IOMobileFramebuffer的iomfb_populate_all_display_infos发现：它先在IODeviceTree:/arm-io的直接子节点中统计device_type=display-subsystem，再启动服务匹配线程。本项目QEMU ADT缺少该声明。现仅在显式--desktop-display模拟器profile添加/arm-io/raphael-gop、device_type=display-subsystem、compatible=raphael,firmware-gop；不声明Apple控制器、寄存器、IRQ或其他手机硬件参数。150153Z复用同一已冻结内核构建，原显示start/registerService通过；用户态枚举与真实swap结果仍在验证。手机未运行该候选，ADB仍device。

150609Z-live-vqna36ma验证设备树声明产生真实变化：显示clients从0到2，原newUserClient返回0，guard=0。SpringBoard越过主CADisplay查找，进入FBSDisplayMode原初始化检查；下一真实EXC_BREAKPOINT为原0x19f3d0744。151058Z暂停态只读采集通用寄存器及x19指向对象，字段为800×600、preferredScale=0、override=0.0、refresh=60.0、gamut=1、HDR/rotation/virtual=0。原检查拒绝零scale且无override，未篡改检查或返回值。QEMU profile现显式提供/chosen display-scale=1，这是“一逻辑像素对应一GOP像素”的设计策略，不是借用Apple或其他手机面板参数。151233Z同内核候选重新启动显示服务通过，后续用户态验证进行中。frames/retired仍没有通过记录。

## 2026-10-30：原合成器运行、Data 容量阻塞与扩容

- `151359.531310Z-live-decw5sxx`：显示 client=7，guard=0，未捕获新的 SpringBoard 异常，但没有 swap/frame。原 Data launchd 日志确认 PID26 运行194447ms后被 backboardd[57] SIGKILL，随后 PID168 重启，不能称 SpringBoard 初始化通过。
- `152614.222857Z-live-q33bp537`：只读原用户代码断点真实命中 backboardd 的 `CA::WindowServer::Server::render_for_time`，EL0、当前线程及16字节原指令匹配。尚未命中 sw_renderer、软件绘制或 swap，frames=0；观察仅覆盖本轮安装时存在的线程。
- `152939.681846Z-live-2pkjws91`：同build原栈确认 SpringBoard 等待 LaunchServices；lsd 的原服务端等待应用数据库 seeding，另一线程正执行原 MI/Security 应用扩展扫描。`153056.067565Z-live-1p295b5p` 的原 open 断点取得实际 NPTKit 插件扫描路径，证明它仍在工作，未将普通扫描认定死锁。
- 128MiB Data 的原内核日志从约462秒起报告 APFS ENOSPC，后续容器服务/launchd反复写入失败。它是明确容量缺口，不将其认定为所有 SpringBoard 重启的唯一原因。
- `prepare_desktop_data.py` 新增显式 `--size-mib`（128/256/512）和隔离QEMU使用的 `--volume-uuid`。新512MiB卷仅创建到 `evidence/private/desktop-data/20261030T153359Z`，不覆盖旧盘。复用冻结内核已经编入的Data UUID契约，原默认var seed与226项目录策略不变。
- 首次512MiB输入 `153429.886149Z-4minkdwj` 在QEMU目录FAT容量门拒绝；FAT32实验 `153659.242820Z-hclgm5xp` 被原DarwinBoot的256MiB输入上限拒绝，均未执行XNU。最终接入固定上游DBRDISK1无损打包格式，原加载器展开为真实512MiB RAMDisk，没有改上游界限或伪造磁盘容量。最终代码保留目录FAT，未保留不必要的FAT32分支。
- `153915.536593Z-tryl3iri`：复用125145088字节冻结内核及原系统，73,840字节打包输入由原DarwinBoot展开，实际进入XNU并通过显示start检查。原APFS挂载/后续用户态和桌面结果还在运行验证，不能以加载通过代替桌面。

复现扩容准备：
```sh
.venv/bin/python scripts/prepare_desktop_data.py --system-disks artifacts/desktop-disks/20261030T075713Z/report.json --user-skeleton --size-mib 512 --volume-uuid 38a12874-2b24-4eca-9cbc-e05600dba8e9
python3 scripts/run_desktop_display_cycle.py --inspection artifacts/desktop-prelink/20261030T125013Z/inspection.json --user-abi artifacts/20261030T141734.723743Z-xmv93cnr/report.json --scratch-data evidence/private/desktop-data/20261030T153359Z/report.json --keep-paused
```

Python语法和git diff --check通过。手机ADB仍device，未在手机运行系统候选；手机最强证据仍085718Z kernel_bootstrap首指令。没有再次同步上游、写手机分区、修改原备份或公开私有文件。旧128MiB QEMU在完整保留Data/日志后关闭以释放主机内存；当前使用153915Z的新QEMU，旧socket不可再续跑。

## 2026-10-30：稀疏 Data 与实际内核内存修复

154009.618447Z-live-pg7oopi4 的600秒运行，512MiB新Data由原APFS读写，真实Data快照可解析885项、普通文件约141MB；当前内核日志未再见ENOSPC，但frames仍0，SpringBoard26被backboardd杀掉后重启为163。原lsd99栈在应用扫描/容器创建，原MCM64处理recreate请求、MCM182在原CFRunLoop。不能将其描述为初始化死锁。

同轮内核日志从约414秒出现真实available_pages_below_critical及vm-pageshortage jetsam。原因约束：原DarwinBoot将内核MemorySize/Actual限制为实际分配窗口1GiB；连续512MiB Data消耗其中一半。仅增加QEMU机器RAM不会增加此内核可用窗口。

新增显式--sparse-data（PackedRAMDisk）复用固定上游原NativeRamBlock按需页分配；新增模拟器--kernel-window-mb 1536，并按既有固件分配流程取得完整窗口。不改上游代码、原检查、手机RAM/固件地址或手机启动布局。scratch允许新1GiB容量，不覆盖旧卷。超过2GiB的原RamBlock路径要求持久store，本轮不启用该路径。

新卷evidence/private/desktop-data/20261030T155658Z；新模拟器153915Z的后续由155742.764094Z-slfky3j5替代。155909.598585Z-live-kpwprhws暂停态已读到real_phys_size=1610612736、native_ram_block_bytes=1073741824、sparse=1、resident=73728、ready=1、read=14、write=0、failure=0。此时仍在原用户态启动前，不能以设备注册证明APFS写入/桌面。

155255.914162Z-live-pjewa8m0的512MiB快照在GDB结束阶段超过旧20秒限制，被主机结束；observer未completed，不作为成功运行。旧154009Z完整Data/日志保留后关闭该QEMU。runner现为Data捕获留60秒，并将顶层异常写进report.failure，避免空failure掩盖未完成观察。

稀疏Data没有连续内存基址，旧dense snapshot明确跳过并记录原因；不会把原seed或打包输入称为当前已写入的Data。Python语法/git diff检查通过，实机边界仍kernel_bootstrap入口。

## 2026-10-31（Asia/Shanghai）：原稀疏 Data 实际写入与快照通过

`155909.598585Z-live-kpwprhws`（UTC run id）延续180秒后，原APFS已实际产生142次块写入，稀疏驻留122916864字节，块错误0，原SpringBoard26已启动。

`160447.598721Z-live-lxfv1jj1`延续240秒，observer completed=true/failure=null；1GiB逻辑Data的写请求升到2564，驻留178036736字节，块错误仍0。原native_owner_data_seed_base=0正确描述非连续盘；未将初始seed或打包文件作为当前磁盘。

新增prepare_sparse_data_observer.py从同build NativeRamBlock.o的DWARF提取实例、RamSparseDisk字段及冻结内核vtable/I/O入口。continue脚本只在实际doAsyncReadWrite调用观察当前实例，核对真实vtable；单CPU暂停后只读页指针表，核对逻辑容量与实际非空页数/驻留量后重建稀疏raw。当前快照成功，libfsapfs原APFS解析1216项，取得原launchd及MCM日志。它不证明文件系统已卸载、断电持久化或手机存储可用。

原MCM64/92日志确认首次初始化/cleanup完成；有明确Data protection unsupported告警，保留，未伪称SEP或加密保护。原lsd97已进入LSDatabaseRebuildContext注册插件及预热本地化字符串，说明继续推进；原SpringBoard26于约180561ms被backboardd杀掉并重启为150，后者仍同步等待LaunchServices。这不能称为原桌面main/runloop已通过。当前保留内核日志未见前轮ENOSPC或vm-pageshortage。

新增--until-frame仅在独立驱动实际frames>0且retired>0的原frame checkpoint停止，用于首个真实提交核查；不将其设为桌面验收。`161218.527069Z-live-ahr5727v`正在同QEMU原地续跑，带原渲染函数观察及实际Data采集。当前仅原render_for_time命中，真实软件绘制和桌面仍待证据。

复现当前运行（仅在155742Z模拟器仍保留且暂停时）：
```sh
python3 scripts/continue_desktop_qemu.py --report artifacts/native-xnu-qemu/20261030T155742.764094Z-slfky3j5/report.json --observer-source scripts/fixtures/native_xnu_gdb.py --sparse-data-abi artifacts/host-dyld-format/sparse-data-observer.json --user-trace artifacts/host-dyld-format/render-trace-plan.json --until-frame --exception-process SpringBoard --run-seconds 600 --capture-data
```

没有重建或修改冻结的原系统/内核，没有手机重启/分区写入、原备份修改、上游同步或私有产物公开。手机边界不变。


## 2026-10-31：原 CPU 软件绘制实际执行，提交链尚未闭合

161218.527069Z-live-ahr5727v：真实backboardd57原EL0命中render_for_time、render_update两次、sw_renderer及原RET（对象非零）、SWContext::draw_elements两次、IOMobileFramebufferSwapEnd四次，16字节原指令逐字匹配，未改原二进制/返回值。主机提前中断取得暂停快照，不能称完整600秒运行。Data解析7444项，已产生两个真实LaunchServices csstore。仍无validate/kick/frame/retired。

162449.353749Z-live-70tq_b0e：只读实际handle回调表，SwapEnd非空并指向原kern_SwapEnd；原代码以selector5、0x508字节输入调用IOKit。后续45秒无新SwapEnd命中，尚无实际返回状态。原绘制线程0xfffffff48bfd5388仍存在，在IOMFBServer::thread_body的CFRunLoop等待，不能称线程退出。最新SpringBoard150主线程在原BKSSystemShellService::_checkIn，已不再停在LS扫描。backboardd另一原线程等待DataMigration同步回复，原因未定。

本轮接手先修正观察器作用域：每次原代码命中按当前thread_ro.proc核对进程与该task实测cache slide，支持随后创建的线程；不修改guest指令或寄存器。下一决定性未知为selector5真实返回/原家族前置条件，以及真实IOSurface提交能否到validate→copy→completion；仅存在软件绘制函数不足以认定桌面。手机持续调度、足够载荷内存、存储、显示与HID依然分别未完成。


## 2026-10-31：IRQ 前原始 POST 阻塞与桌面主机身份缺口

`artifacts/native-staging-qemu/20261030T202018.004873Z-8mo7dayc/report.json` 的 irq-enabled 目标失败，37项通过；原 panic 字符串为 `FIPS Kernel POST Failed (%d)!`，LR 位于 corecrypto_kext_start+2752，仍在 IRQ mask 状态。恢复路径通过，镜像没有上手机。原 POST 对 __TEXT_EXEC/__text 做 HMAC；诊断断点与向量位于该范围，需进一步隔离插桩影响，不能关 POST 或把恢复成功当目标通过。

原桌面 QEMU `201700.309454Z-live-sdg0yakv` 中 configd37 的三个只读快照均停在原 gethostuuid；固定 XNU 的 IOBSDGetPlatformUUID 等待 IOPlatformUUID 资源，ARM 默认只用 Apple unique-chip-id/chip-id 生成，本项目没有该身份输入。新增独立补丁：原身份路径优先，只有显式非零16字节 /chosen/unixnu-platform-uuid 才使用 port-assigned UUID。模拟器提供专属 UUIDv5，不伪装手机或 Apple 芯片。源码已实现，构建与运行结果待记录；尚未认定此项是桌面唯一阻塞。
