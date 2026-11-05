# 当前状态

2026-11-01 规范整改：活动源码已按设备package/SoC kits归属迁移，13区移植记录与构建回归通过；最新实机停点未变。见[整改说明](../UniXNU-raphael/docs/REPOSITORY-COMPLIANCE.zh-CN.md)和[最新交接](HANDOFF-20261101.zh-CN.md)。下文历史记录保留当时状态。

2026-11-01 12:36交接更新：最新实机041841Z整轮passed=true，APFS根与SystemOS组合挂载、原launchd exec/EL0及22次Unix syscall已有同轮证据；2159次/30929920字节UFS读取、硬件失败0。20秒硬件watchdog加60000ms有界pet，100poll名义10秒实际13.142秒、pet25次，恢复与普通重启清理通过。500poll候选已完成构建/预链接/上传/extent，但042318Z QEMU报AMFI: No PMGR?，尚未手机构建或运行；需先定位夹具依赖并复核实际时间余量，不盲放宽门禁。本次现场Android/ADB/root/清理正常、无运行中实验；未有dyld完成、launchd main、桌面或可靠ETA。完整接续产物与失败边界见[更新后的交接](HANDOFF-20261101.zh-CN.md)。以下历史条目保留各轮当时状态。

2026-11-01 十秒实机030853Z整轮passed=true：原PID1/launchd继续真实读盘，2141次/30647296字节UFS读取零硬件失败；终止诊断主动中止一次大读，5.018ms完成DMA交还。22次syscall末尾fcntl97的errno16由该终止中断造成，不能当独立启动错误。随后90秒看门狗032441Z/033532Z在XNU前严格拒绝；033532Z原日志实际requested2948850/2981615、readback851698/884463，均差2^21，EFI_DEVICE_ERROR；自动Android及普通重启清理通过。正准备60秒预算的独立实机验证，并完整构建50秒用户态观察窗口；尚无launchd main/桌面证明。索引native-watchdog-budget.json及native-pid1-service-window.json。


2026-11-01 十秒观察025627Z失败：240.924秒自动回Android/root及普通重启清理通过，但nonce不匹配、没有原生回传，xnu_executed=null，不能更新最深停点或断言看门狗复位。真实libfdt以024411Z回传和当前全部可变记录上限测试，2MiB中pack2091032字节，余6120字节；未复现FDT溢出。源码发现诊断quiesce必须等同一gate保护的整笔任意长度读结束；候选只为终止诊断增加16KiB已验签chunk边界的停止通知，部分读明确kIOReturnAborted并记录实际bytes，保留DMA恢复门禁与原十秒窗口/二十秒看门狗。完整构建、结构/预链接与QEMU39项通过；新候选待手机。索引native-pid1-service-window.json。

2026-11-01 PAN修正实机024411Z整轮passed=true：原copyin权限异常循环消失，PID1/launchd从3次推进到22次Unix系统调用，最新在fcntl命令97内实际UFS读盘。同步异常从4957297降至173，内核VM fault仅6次；1827次/25564160字节读取零失败。自动返回Android、新boot ID/root及普通重启清理通过。当前五秒观察窗口到时，采样位于ReadOnlyExtents/cluster_io，尚不能宣称dyld完成或launchd main；下一单变量将窗口延至十秒，保持二十秒看门狗。详见UniXNU-raphael/evidence/native-pid1-pan.json。

2026-11-01 PID1后续023001Z：整轮passed=true且Android返回/清理完成。真实exec用户线程在Mach vm_allocate的初次copyin发生4957297次同步异常；最新ESR0x9600000f/FAR0x16f2ba570/CPSR0x20400204，PAN=1、SCTLR.SPAN=0，fast_fault返回0后持续重入。handset profile继承PAN=n，最终copyio没有PAN开关。现仅在raphael_handset_storage_defconfig启用既有CONFIG_XNU_NATIVE_PAN=y；887记录完整构建、结构/预链接、最终copyin/copyout成对PAN指令及QEMU门禁通过，024411Z手机单变量验证运行中。当前不称修复实机已通过；launchd主函数、服务、桌面与输入仍未验证。索引：UniXNU-raphael/evidence/native-pid1-pan.json。

2026-11-01 PID1后续022035Z：原launchd exec/EL0复现，三次Unix调用74→0、372→0（tid198）、294→ENOMEM12均已返回。294是共享区为空的正常探测，不是卡点或内存耗尽证明。对真实exec用户线程持引用后采样，当前在Mach vm_allocate trap初始copyin的同步异常路径被IRQ抢占；wait_event0、state4、空闲25032页。该轮experiment_passed=true，已自动回Android；继续扩展已有PC/ESR/FAR/VM原始记录到当前用户线程，查具体异常。仍无launchd main或桌面证明。

2026-11-01 重大实机进展：020626Z整轮passed=true。原/sbin/launchd exec返回0，PID1/launchd真实EL0（CPSR0）发出3次Unix系统调用；首次74/mprotect，最新294/shared_region_check_np，尚未记录其返回。APFS根与SystemOS组合挂载再验，343次/1631232字节UFS读取零失败。原2554条/61356字节TrustCache补齐后，已越过前两轮exec安全策略拒绝；原记录不增owner cdhash，不宣称Apple签名链认证。204.483秒自动回Android，新boot ID/root/临时属性清理通过。launchd主函数、服务、桌面和交互仍未验证；下一步捕获当前exec用户线程及系统调用返回，推进原dyld/服务启动。索引：UniXNU-raphael/evidence/native-pid1-el0.json。

2026-11-01 最新PID1实机：014449Z/015623Z两轮均完成首次copyout（一次正常translation fault，vm_fault返回0）及SystemOS组合挂载（stage6/status0/readonly1/native_union1/root_recheck1），随后原/sbin/launchd在exec安全策略被拒，SIGKILL namespace9/code8。前一次开发版路径返回ENOENT，不是原launchd不存在。两轮主动panic诊断使experiment_passed=false，已自动回Android并完成普通重启/root/临时属性清理；不能标整轮成功或EL0已执行。当前载荷没有原TrustCache，正在补齐原记录sidecar及精确loaded ADT修正/字节校验。此前5秒窗口的copyout采样不能泛化为永久重试；没有修改原缺页/VM处理，未宣布其根因已修复。索引：UniXNU-raphael/evidence/native-init-development.json。

2026-11-01 PID1推进：手机011142Z和012734Z均整轮通过并自动回Android/清理。原APFS根挂载后已到load_init_program，SystemOS查找stage2；用户scratch页分配成功（0x1000/result0），第一次copyout尚未返回。内核栈在同步异常处理路径，未有ESR/PC/FAR，不推断为内存不足或存储等待。exec_attempts0、EL0 syscall0，尚无launchd或桌面证据。下一轮仅增加原异常/VM遥测，按实测故障修复。索引：UniXNU-raphael/evidence/native-init-development.json。

2026-11-01 最新实机：`android-return-run/20261101T010035Z` 整轮通过，原 BSD 完成 APFS 根挂载（disk1s1）、只读所有者认证和186次/734208字节实际块读取，零失败。观察线程8次100ms唤醒后返回，200.509秒自动Android，恢复与普通重启清理通过。Apple原根认证返回80，最终按已启用的所有者签名块认证策略接受，不能表述为Apple封印认证成功。launchd、显示桌面与输入仍未验证；下一步推进原PID1启动。索引：UniXNU-raphael/evidence/native-apfs-root.json。

2026-11-01 本轮最新：常驻 UFS/owner 验签版完整内核已编译及预链接通过，124,436,480 字节候选；QEMU 原 DarwinBoot 已装载全部 15 段。128MiB FAT 已上传并锁定，静态 ADT/逐块 SHA256/恢复路径 host 与 QEMU 检查通过。首轮大载荷实机 185043Z 回 Android、root/清理通过，但无 nonce/SEC/UFS 记录，执行未知，原镜像不重跑。正在推进可回传错误的恢复分支；本机根卷、launchd 与桌面仍未验证。详见 [本机存储主线](HANDSET-STORAGE.zh-CN.md)。

2026-11-01 主线续进：原始 OS/SystemOS 已分别上传至新建的本项目私有明文目录，完整 SHA-256 与主机一致，设置不可变标志并冻结 66/27 个 extent。OS 实机 20261031T180012Z、SystemOS 实机 20261031T180840Z 均完成 16 轮/128 次真实 READ10；首部、APFS 超级块、中段、尾部、跨物理块/extent 的 512 字节虚拟扇区逐字节一致，两轮分别约 71.098/71.154 秒自动返回 Android，nonce、控制器/看门狗恢复及普通重启清理均通过。两轮为独立 stage3 存储实验，无 XNU/挂载/用户态证明。新增常驻 XNU 控制器与两个只读卷，逐块认证代码已写并通过独立 ARM64 对象编译；190 槽存储 ABI/11 个原始接口绑定已核对早期对象，认证版及完整内核集成仍在验证。详见 docs/HANDSET-STORAGE.zh-CN.md。

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

2026-10-31 桌面主线：目标为这部 Redmi K20 Pro 进入真实可见、可基本操作的系统桌面。手机最强证据仍是085718Z原kernel_bootstrap首指令；尚无手机根卷、用户态或桌面验证。本轮ADB为device，没有重启手机。

QEMU原CPU软件绘制已实际执行。170256Z确认原selector4/SwapBegin与selector5/SwapEnd均返回0，但validations/kicks/frames/retired仍0；171128Z定点只读追踪进一步证实原display+0x16cc（requested）为0，原submit因此把skip置1，主动跳过queue/validate。实际单层surface、双rect和尺寸800×600匹配。独立驱动现改为经原setter同时声明逻辑requested与powered，未实现物理面板电源控制。完整构建171408Z（887编译记录）、预链接/结构171433Z（未定义0）及同候选ABI171438Z通过。同候选QEMU延续300秒后已存在原SpringBoard/backboardd与7个显示client，但validations/kicks/frames/retired仍0；呈现修复尚未获运行验证，不能将源码修复或API成功当成桌面。

下一项决定性未知是原用户态提交能否经真实IOSurface完成validate→CPU copy→原completion并持续产生完整系统画面；后续仍需手机持续调度、足够载荷内存、存储、scanout和真实输入分别验证。首次桌面、基本操作、GPU及其他外设分别验收，不承诺日期。上游已按本轮明确授权刷新一次，之后没有自动刷新。

## 此前阶段记录

当前显示主线（QEMU）：150609Z原用户态已成功打开2个显示client，主CADisplay缺失断言已越过。下一停点为FBSDisplayMode原模式有效性断言；151058Z真实对象参数为800×600、60Hz、preferredScale=0且override=0。QEMU声明/chosen display-scale=1作为明确1:1逻辑策略后，151233Z已启动，正验证后续用户态。仍无真实swap/frame/retirement，未证明软件renderer执行或桌面。MCM已在原CFRunLoop，backboardd/CA render server已运行。手机仍以085718Z kernel_bootstrap首指令为最强证据，未运行本系统候选。

2026-10-30 显示主线更新：独立 RaphaelDesktopDisplay 已真实编译和预链接，QEMU 123115Z 原 IOMobileGraphicsFamily/IOSurface 加载、metaclass 注册、原 start 与 registerService 已通过；实际 GOP 800×600、32位、stride3200、映射1920000字节，参数仅来自同轮模拟器固件。123229Z 延续用户态300秒，原 start 返回true，clients=0，未捕获 backboardd 首SVC；没有桌面帧，也不能据此断定 backboardd 从未运行。手机仍仅有085718Z kernel_bootstrap首指令证据。本轮没有将系统候选用于手机。下一项实现为用户态单层surface校验、CPU呈现及原swap完成路径；能否由所选用户态持续产出完整桌面仍是关键未知。

2026-10-30：本轮显式同步上游一次至f0721e9。手机最新有效停点已推进到kernel_bootstrap首指令0xfffffff0072d3ae4，machine_startup函数体已执行；run 20261030T085718Z，nonce和状态恢复通过，85.226秒自动回Android，正常重启/root/清理通过。kernel_bootstrap函数体、持续XNU IRQ/调度、根卷、用户态和桌面仍无手机验证。

QEMU中原APFS所有者根认证、认证OS/SystemOS组合及原launchd LC_MAIN首条指令已通过。新独立RamBlock Data已由原APFS按UUID实际可写挂载；206条默认内容创建、611715字节写入并逐字节读回一致（095316Z）。原Apple seal仍拒绝，采用独立所有者根策略；Data目前为易失内存盘，未证明持久化。补齐空的用户管理目录并启用原APFS共享Data策略后，QEMU101909Z原launchd已完成early boot，原usermanagerd创建/保存默认用户501及persona，PID27 SpringBoard首个EL0 SVC64通过。尚未证明SpringBoard main、backboardd、渲染或桌面；sysstatuscheck exit(1)、prng_seedctl exit(13)等异常仍保留。以上均非手机用户态或桌面证据。后续102530Z已观察多项常驻服务EL0及backboardd启动请求，300秒内未捕获backboardd本体SVC。下一项首帧能力为XNU显示发布/IOSurface swap与真实呈现；新显示候选现已具备QEMU GOP和独立Legacy服务，但无client或frame。详情见[桌面主线](DESKTOP-MAINLINE.zh-CN.md)。

## 以下为本轮修复前状态

2026-10-30。最新有效手机XNU回传仍为10月29日 stage13 console 入口检查点；其内核为 `96d31d6e…b0d722`，无本轮 watchdog 与 `kt_fixed_zones=200` 参数，不能代表当前配置。10月30日 idle 镜像及本次仅改目标为 console 的对照均使用 XNU `67964d23…f9509e21`、watchdog 与相同内存布局。console 对照临时镜像 SHA256 `6877f88e2cfe8e6ac9c014e15825b125053ad1c128542ae36d062a3502beac15`；fastboot 接受后约90.97秒 Android/root恢复，原 boot 分区哈希和清理通过，但 FDT 无本轮 nonce、SEC、MMU、watchdog、platform 或 PC 回传。故当前更早 console 检查点也未获验证；停点及 watchdog 是否触发未知，不能归因于 console 内部、不能宣称 XNU 越过 console 或 Darwin 启动。单次对照后停止，不重跑。QEMU38项仅验证模拟器。无分区写入/上游同步，原备份不变。详情见[NATIVE-PLATFORM.zh-CN.md](NATIVE-PLATFORM.zh-CN.md)。

## 以下为先前状态

2026-10-29。手机011328Z的stage12通过：原XNU arm_vm_init完成并换TTBR1/置空原TTBR0，在PE_consistent_debug_inherit首指令捕获后完整恢复3段/原代码/初始表和输入ADT。66页活动表、644页高数据映射及132936字节delta通过；80.337秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。405份Git/blob/冻结输入与原始回传独立复核，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。尚无正常XNU IRQ/timer生命周期、根卷或用户态。下一步推进pmap后的平台初始化与持续日志。未同步上游、未写分区、原备份未改动；当前正常Android且无运行中的手机实验，RAM alias仍暂停。

## 以下为stage12手机执行前的历史状态

2026-10-29：stage12换表后恢复已实现，QEMU正向36项及同镜像独立5场景通过；旧stage11回归31项通过。手机仍以001904Z的arm_vm_init首指令为准，stage12尚待最终冻结构建、旧分支回归和本机布局预检。原始TTBR与诊断转换根分开，输入ADT的random-seed清零由独立备份恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。上游未同步、RAM alias暂停、原备份未改动。

2026-10-29补充：QEMU原arm_vm_init已真实换TTBR1/置空TTBR0并返回，66页活动页表、644页高地址数据映射及7处完整快照经396份冻结输入独立复核。手机仍仅到arm_vm_init入口。下一步独立TTBR0转换表恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)；未同步上游。

2026-10-29。手机001904Z已执行原arm_init C初始化并到达arm_vm_init首指令，原平台首次初始化/拓扑/当前线程和早期时钟/启动子系统前缀已通过该检查点。2,637,824字节三个数据/栈段完整备份恢复；130,896字节/10,908个变化64位字独立重建，原10段CRC/零尾/args/ADT及UEFI状态恢复通过。80.434秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。396项Git输入与原始证据独立复核，详见[NATIVE-EARLY-RECOVERY.zh-CN.md](NATIVE-EARLY-RECOVERY.zh-CN.md)。arm_vm_init函数体、pmap重建、正常XNU IRQ/timer生命周期、根卷和用户态尚未验证。下一步处理pmap切换后的日志与恢复；原TTBR0将被置为空表，现有物理别名relay不能直接沿用。当前手机正常Android，无运行中的实验；未同步上游、写分区或改原备份，RAM alias暂停。

## 以下为arm_init C实机验证前的历史状态

2026-10-29。手机234327Z已实测原XNU建立bootstrap页表、设置翻译寄存器、开启MMU并到达高VA arm_init首指令检查点。72Q记录和完整64KiB页表通过，4表页/258非零描述符/128组block；全部临时代码、页表与UEFI状态恢复，原10段CRC/零尾/args/ADT重验通过。80.516秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。389项Git输入及原始证据独立复核，详见[NATIVE-MMU.zh-CN.md](NATIVE-MMU.zh-CN.md)。arm_init C函数体、XNU平台/GIC/timer、根卷与用户态仍未执行。下一步建立C初始化阶段的可恢复日志，推进平台初始化。未同步上游，RAM alias暂停，原备份未改动；当前手机正常Android，无运行中的实验。

## 后续C初始化观测（仅QEMU）

235049Z复用最终MMU Image，在模拟器已加载内存恢复arm_init首指令，原C执行过PE_init_platform(FALSE)并到rtclock_early_init及arm_vm_init入口。10段×5处原始快照和独立逐字节复核235353Z通过，页表未变，3个数据/栈段出现真实写入。手机仍只验证到arm_init首指令；下一步需实现这些段的有界备份/恢复和更深检查点。细节及局限见[NATIVE-EARLY-C.zh-CN.md](NATIVE-EARLY-C.zh-CN.md)。


## 以下为bootstrap MMU实机验证前的历史状态

2026-10-29。手机首次完成有证据的XNU实际指令入口：原DarwinBoot退出服务后跳原入口，执行5条原始指令，在计划BRK检查点捕获PC/ESR/参数并恢复原指令与UEFI状态。230308Z自动回Android，正常重启/root/原boot哈希/清理通过。381项输入及原始记录独立复核；详见[NATIVE-ENTRY.zh-CN.md](NATIVE-ENTRY.zh-CN.md)。这只是有插桩的入口前缀，尚未到arm_init/XNU页表/平台、根卷或用户态。下一步交接后的持续异常/页表日志和arm_init。没有同步上游，RAM alias继续暂停，原备份未改动；当前无运行中的手机实验。

## 以下为实际XNU入口验证前的历史状态

2026-10-29。手机真实原Mu ExitBootServices已返回成功，退出后的10段CRC/零尾、boot_args和本机ADT完整；物理TimerArch 280次IRQ/EOI与原状态恢复通过。224029Z自动回Android，正常重启/root/原boot哈希/清理通过，376项输入和原始回传独立复核完成。详见[NATIVE-EXIT.zh-CN.md](NATIVE-EXIT.zh-CN.md)。手机XNU仍未执行；下一步实现有独立日志的实际指令入口。不自动同步上游，RAM alias继续暂停。

## 以下为真实服务退出前的历史状态

2026-10-29。手机已通过原 DarwinBoot 的有效内核装载检查：本机 ADT 解析/复制、10 段文件 CRC/零尾及 boot_args 全部通过，到达 BeforeExitBootServices 后约49.7秒自动回Android，正常重启清理通过。374 个输入/原始回传独立复核完成。详见 [NATIVE-LOAD.zh-CN.md](NATIVE-LOAD.zh-CN.md)。这尚未完成真正退出服务，手机 XNU 尚未执行。


2026-10-29。手机主线大载荷阶段 3/6 已通过：独立 56MiB arena、20MiB FAT、原 Mu 分配器完整读取 18,463,480 字节有效 XNU，CRC/窗口恢复通过；高段解码本机 Android 后自动返回并正常重启清理。360 个输入/原镜像/原始回传已独立复核，失败记录保留。详见 [NATIVE-STAGING.zh-CN.md](NATIVE-STAGING.zh-CN.md)。这不是 XNU 执行或 ExitBootServices 成功证据。

下一步本机 ADT 与原 DarwinBoot 的有效加载诊断。上游版本固定，本轮没有 fetch/pull；RAM alias 仍暂停。当前手机正常 Android，没有运行中的实验；原备份未改动。

## 以下为大载荷验证前的历史状态

2026-10-29。新完成：**小规模自有UEFI的阶段3/6均在手机通过高段LZMA恢复本机Android内核，带回匹配nonce、CRC和日志，自动返回Android；正常重启后root/原boot哈希/临时属性清理通过。** 详见[ANDROID-RETURN.zh-CN.md](ANDROID-RETURN.zh-CN.md)。

16MiB布局失败、电脑bootloader恢复和125.5MiB旧布局失败均保留。扩展initrd探针实测输入FDT后，小规模arena改为12MiB并继续现场检查；大20MiB FAT/48MiB arena尚未手机验证。有效XNU的自有SEC/DXE QEMU timer IRQ本轮回归通过，手机XNU尚未执行。

下一步接入与输入FDT/initrd分开的主线大载荷布局、本机ADT及有效DarwinBoot/XNU。上游保持固定版本，本轮没有fetch/pull；RAM alias扩展暂停。原备份未改动，私有产物未公开，当前手机正常Android且无运行中的实验。

## 以下为本次返回通道完成前的历史状态

2026-10-29，Asia/Shanghai。**主线现已用自有SEC/DXE及原Mu分配器，经真实UniXNU/DarwinBoot加载有效XNU，在QEMU进入bsd_init、物理timer IRQ及IOFindBSDRoot入口。手机XNU尚未执行。**

实现bd61c3a，独立复核两轮原始内存/日志、10段SHA256、实际源文件buffer、源码Git blob均通过。大载荷20MiB FAT/24MiB FV/48MiB arena为默认关闭的独立profile，旧1MiB路径66项回归通过。细节、失败和重现见[NATIVE-SEC-DXE.zh-CN.md](NATIVE-SEC-DXE.zh-CN.md)。

手机本轮已实测PSCI SMC VERSION=1.1、FEATURES(SYSTEM_RESET)=支持；独立64KiB临时镜像自动回Android，root/原boot哈希不变、新boot_id和临时属性清理通过。它是恢复流程证据，没有直接reset指令跟踪；见[PSCI-RECOVERY.zh-CN.md](PSCI-RECOVERY.zh-CN.md)。最终设备在Android，没有正在运行的实验。

下一步是独立小Image大布局的手机分段验证、交接后诊断、本机ADT与CPU/PPI18，随后有效内核交接。QEMU的INTID30/62.5MHz不能用于手机。RAM alias扩展保持暂停。

本轮没有fetch/pull，UniXNU仍40d21cc，DarwinBoot3325e35、Mu cfb9372。只在用户明确要求时同步上游。UART外部引脚/电平/接线及实际输出仍未验证；原备份未改动，私有数据未公开。

## 以下为自有UEFI有效内核接通前的历史记录

最新更新：2026-10-29，Asia/Shanghai。**手机已验证独立UEFI的256MiB连续分配生命周期；有效DarwinBoot/XNU手机交接尚未执行。** 实现提交7265f5676851298000346176971658223c7a36fb，详见[KERNEL-WINDOW-UEFI.zh-CN.md](KERNEL-WINDOW-UEFI.zh-CN.md)。

手机185509Z：候选258MiB整段隔离，真实AllocateAddress(EfiLoaderCode)取得0xc0004000起256MiB，保留/释放/分配/重新保留四次内存图均通过。入口stage2、MMU stage3和DXE stage6分别实测；最后185721Z正常重启清理，Android/root/原boot哈希正常，临时标记消失。独立原始证据复核185948Z通过。该结果不等于全面物理RAM/隐藏DMA所有权证明，也没有加载有效内核或ExitBootServices。

原生XNU仍以此前QEMU到达bsd_init/IOFindBSDRoot入口及6次物理timer IRQ/EOI为准。下一步接有效内核载荷、staging内存和原DarwinBoot；现有1MiB诊断FAT和16MiB普通heap不足以装入18,463,480字节原内核。独立小Image布局及PSCI自动恢复尚属设计，不能当实测。

仅在人类明确要求时同步上游；活动版本40d21cc，本轮无fetch/pull。RAM alias仍暂停。Windows本轮未枚举到串口；本机GENI 0xa90000只是Android console配置，外部UART输出未验证。原备份未改动，无正在运行的手机实验。

## 以下为连续分配接入前的历史状态

最新更新：2026-10-29，Asia/Shanghai。**主线已推进到QEMU真实XNU的bsd_init及IOFindBSDRoot入口，手机有效DarwinBoot/XNU交接仍未执行。** 独立CPU/GICv3和物理timer同轮6次rtclock_intr/6次EOI及IRQ caller返回通过，源码pthread status0、函数表非零；默认crypto POST保留。不是根卷或用户态启动。

最新主线内核18,463,480字节，SHA256 96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722，887编译记录、结构检查未定义0。源码、冻结输入、失败和准确模拟器范围见[NATIVE-CPU.zh-CN.md](NATIVE-CPU.zh-CN.md)。

只在人类明确要求时同步上游；本轮没有fetch/pull。活动版本仍为40d21cc，GPU候选未接入。RAM alias SEC接入的11路径WIP保存在stash 3fb57136db5b293859402f36f8bf44a1f9548a46，暂停扩展，历史QEMU输入/结果保留。

下一步是实际DarwinBoot连续窗口分配/保留合同与有日志的手机交接。当前UEFI allocator仍为16MiB，loader最小256MiB及Mach-O低21位偏移保持原合同；手机CPU/GIC/PPI18仍待验证，不把模拟器INTID30/62.5MHz代入本机。

手机本轮只读确认Android/root正常，并重新核实GENI console的cmdline/live FDT；没有重启或写分区，原boot哈希本轮未重算。串口范围、接线未知项和用户提供文档的适用边界见[LOG-CAPTURE.zh-CN.md](LOG-CAPTURE.zh-CN.md)。原备份未改动。目标继续进行中。

## 以下为本次主线推进前的历史状态快照

2026-10-29，Asia/Shanghai。权威工作树 `/home/guo/work/raphael-fresh`。完整移植仍在开发；手机实验全部使用临时 `fastboot boot`。最后一次记录的正常重启清理为 `20261028T144408Z`，当时 Android/root/原boot哈希正常，临时诊断属性全部消失。此轮源码更新未重新查询或重启手机，没有进行中的手机实验。

当前 UniXNU 为 `40d21cc65171c3a24faa130a2a8e899f85790485`，准确依赖见 sources.lock.json。上游新增4个提交主要更新设备记录和日志指南，运行时基础设施未变；更新及独立回归见 [UPSTREAM-REFRESH.zh-CN.md](UPSTREAM-REFRESH.zh-CN.md)。本轮直接回调实现与全部新手机固件绑定 `d0a54cc50f47e6996b1a8b970f0032a8c94d71c4`，通用恢复engine保持不变。

2026-10-29 再次 fetch，最新候选为 `feat/ipados27-gpu-parity` 的 `9fe4855117709d1a0119baefaa66180682dee52c`，固定于 `sources/UniXNU-gpu-parity-9fe4855`，19 子模块齐全。21 仓库、2,504 文件与 Git 原字节/执行位一致；候选主机 113 项单测通过、1 跳过及两组实际 C 检查通过，固定 translator 上 37 份 bridge 补丁按顺序应用通过。本轮新增 Turnip 同步、Metal bridge 和 Adreno740 SMMU 故障恢复代码；候选与 main 为 7/30 提交分叉，继续作为独立参考候选。活动手机构建、硬件参数及准确 source lock 保持原版本，本轮无候选固件、QEMU、Mac Metal 或手机验证。见 [上游更新](UPSTREAM-REFRESH.zh-CN.md) 和 [本轮版本/检查记录](upstream-refresh-20261029.json)。

| 功能 | 当前证据 | 验证范围 |
|---|---|---|
| 独立SEC/MMU/DXE | 手机分阶段通过 | 各诊断按其Git及归档快照绑定；完整管理器513c3b8、Darwin拒绝02f39c0，不能泛化为完整UEFI合规 |
| 继承GOP | 手机通过 | 1080×2340、stride4320、BGRA、base0x9c000000；只验证既有模式 |
| 完整UniXNURun与实体三键 | 手机通过 | 用户确认up/down/enter各1、automatic0、errors0；4.180865秒提前退出，属于该次来源版本 |
| 显示恢复 | 手机通过 | 2527200像素变化并全部恢复，差异0、fallback0 |
| GIC/ICC、CNTP与物理TimerArch | 手机有界诊断通过 | 目标PPI18的IRQ/EOI、事件与状态恢复分别验证，未证明常驻服务或完整所有权 |
| RAM只读WB映射 | 手机通过 | 同轮256点恒等转换、写拒绝、PAR与摘要恢复 |
| RAM关闭缓存可恢复写 | 手机前1MiB通过 | 历史071253Z、连续256页、3155.935ms，范围和来源不变 |
| RAM缓存可恢复写 | 手机完整256MiB通过 | d0a54cc的144256Z，65536页、两轮图案/全部原字恢复零差异、6087.08453125ms，PoC同步与RO恢复通过 |
| DarwinBoot拒绝生命周期 | 手机通过 | 083159Z加载/启动v2驱动、无效输入拒绝、卸载和服务恢复；ExitBootServices=0 |
| DarwinBoot有效内核交接 | 手机未执行 | AAVMF合成接收器有正向证据，不能当作手机有效交接 |
| 原生XNU与源码crypto | 主机编译、结构及QEMU部分阶段通过 | 887对象、未定义符号0，真实POST/注册通过，到PE_init_iokit后缺平台driver；未到bsd_init或手机执行 |

当前缓存写入的独立手机证据：

| 范围 | 阶段3 run（UTC） | 实测时间 | 固件来源 |
|---|---|---:|---|
| 4KiB | 20261028T142732Z | 0.0990104167ms | d0a54cc直接回调 |
| 1MiB | 20261028T143440Z | 23.778125ms | d0a54cc直接回调 |
| 16MiB | 20261028T115003Z | 690.78265625ms | 2148339历史版本 |
| 64MiB | 20261028T143848Z | 1521.8653125ms | d0a54cc直接回调 |
| 256MiB | 20261028T144256Z | 6087.08453125ms | d0a54cc直接回调 |

本机完整候选窗口为 `0xc0000000..0xd0000000`。完整实测65536页、图案67108864个64位字和恢复33554432个原字均零差异，Dirty/BackupWords0；页前/后PoC同步65536/196608次、RW/PAR及恢复RO写拒绝256点。没有修改原8秒预算。每个直接回调范围均重新执行两阶段手机启动、正常返回Android和正常重启清理；149项固件输入与22项验证脚本逐Git blob/快照绑定。

完整窗口阶段3 boot SHA256 `41cbf90784019284fb4863372ce21b0a22a1e2d56414ec2a8cf3ed4701f8fbbb`；FD SHA256 `2a77e1665d368f769e8fc7e12b09ca04cc086b80b956c5d9b28506813bf7f04d`。原boot SHA256仍为 `cbd91d814396ea0aab1cbca25d4f4f904805c69e4bb38b5a35a51b98858b96ec`。

`python3 scripts/validate_ram_cache_evidence.py` 已独立重解码全部原wire/FDT/log、历史Git和冻结镜像/源码、正常重启原记录；最新核验20261028T144645.527035Z-b5pgi14w覆盖到268435456字节。恢复结论来自固件逐字比较及其原始回传，不声称Android中重新读取了全部原DRAM。细节见 [RAM-CACHE-WRITE.zh-CN.md](RAM-CACHE-WRITE.zh-CN.md)。

主机90项实际C/ASan/UBSan、18项wire与12项ABI断言通过；76项完整native opcode/extent/checkpoint负向与历史schema兼容检查通过。完整窗口QEMU正常53、部分写UDF恢复55、映射读取UDF返回49项通过，normal4987.654768ms。四次旧实现全窗口QEMU超时和恢复证据仍保留，并未因新版通过而重写历史。

分配器仍只使用原16MiB诊断arena。完整窗口逐页恢复写不证明跨页别名不存在、长期隐藏DMA所有权或连续分配合同；下一步实现独立的跨页同时标记/恢复诊断及分配合同，再推进手机有效DarwinBoot/XNU交接。XNU仍需本机CPU/GIC/timer/platform适配，不能采用上游固定PPI27策略。完整UEFI、常驻TimerArch、存储/其他外设及手机XNU/用户态尚未完成。

跨页同时标记库已在 `57555b0` 实现，暂未接入 SEC/allocator。`155542.543576Z-pm9nqcft` 的实际 C 分离 DRAM/cache 模型 249 项 ASan/UBSan 通过，包括 65,536 页首尾样本与远距离解码别名、恢复失败后重试、整份备份/journal 损坏拒绝和总预算耗尽后的强制恢复。固定 clang-18 的 AArch64 ELF 对象检查通过、未定义符号 0；真实 Mu/INF/DEC/DSC AARCH64/DEBUG/CLANGPDB 独立归档构建及 bitcode triple 检查通过。所有冻结输入已逐 Git blob 绑定实现提交。新库没有新 FD、QEMU、同步异常或手机执行证据；还需落实 owned 备份存储及原生恢复路径。见 [跨页诊断](RAM-ALIAS.zh-CN.md) 和 [主机证据](ram-alias-host-20261028.json)。

原备份 `D:\PhoneBackups\raphael\2026-10-27` 未改动，仍不完整且未经恢复验证。私有镜像、固件、标识及原始采集数据均在ignored目录；无发布remote，未执行flash/erase/format。各历史结果只覆盖其记录的版本与模式。


## 2026-10-31：IRQ 前原始 POST 阻塞与桌面主机身份缺口

`artifacts/native-staging-qemu/20261030T202018.004873Z-8mo7dayc/report.json` 的 irq-enabled 目标失败，37项通过；原 panic 字符串为 `FIPS Kernel POST Failed (%d)!`，LR 位于 corecrypto_kext_start+2752，仍在 IRQ mask 状态。恢复路径通过，镜像没有上手机。原 POST 对 __TEXT_EXEC/__text 做 HMAC；诊断断点与向量位于该范围，需进一步隔离插桩影响，不能关 POST 或把恢复成功当目标通过。

原桌面 QEMU `201700.309454Z-live-sdg0yakv` 中 configd37 的三个只读快照均停在原 gethostuuid；固定 XNU 的 IOBSDGetPlatformUUID 等待 IOPlatformUUID 资源，ARM 默认只用 Apple unique-chip-id/chip-id 生成，本项目没有该身份输入。新增独立补丁：原身份路径优先，只有显式非零16字节 /chosen/unixnu-platform-uuid 才使用 port-assigned UUID。模拟器提供专属 UUIDv5，不伪装手机或 Apple 芯片。源码已实现，构建与运行结果待记录；尚未认定此项是桌面唯一阻塞。
