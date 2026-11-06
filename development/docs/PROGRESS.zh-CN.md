# 官方跳过首次设置候选已实机启动

180944Z官方skip-setup/no-auto-dim候选唯一临时启动已接受；仅更改独立临时Data种子中的官方21H461首次设置/保持亮屏配置，保留1536MiB/32MiB日志/2Hz及1800/1860秒合同、原watchdogd和现有服务策略。887记录内核、39项恢复QEMU及手机镜像已通过。自动回收进行中，不再常规询问画面；原欢迎UI已实机确认，主屏幕仍待验。候选：`artifacts/desktop-skip-setup/20261106T175720Z`。

# 实机欢迎UI及正常SpringBoard事件循环已确认

172949Z长窗口已自动回Android，回收6710条/13949575字节/dropped0；600秒183进程883线程、1000秒209进程1092线程、1800秒189进程655线程均完整。SpringBoard27在1005秒进入原SBDashBoardSetupViewController欢迎文字动画，最终进入UIApplication事件循环，已越过原BKS签到等待；用户两次报告你好欢迎页且持续超过60秒。2698帧、13张RGB采样framebuffer差异0，实际查看低分辨率样本为深灰欢迎背景和细小元素，不能独立读出欢迎文字；无图标桌面。原watchdog165次签到/0失败，无记录panic/压力kill。Android/root/新boot ID/临时FDT清理成立；原完整failed/null保持。下一候选采用官方21H461 skip-setup及no-auto-dim临时Data偏好，已完成887记录内核、39项恢复QEMU和手机镜像。证据：`artifacts/desktop-no-locationd-long/20261106T172309Z/interpretation.json`。

# 实机首次显示原生你好欢迎界面

北京时间2026-11-07约01:50，172949Z长窗口实机用户明确报告“目前开机了，显示的是苹果你好欢迎页面”。这是本机首次越过进度条进入原生首次设置欢迎UI的现场证据；当前采集仍运行，持续60秒及对应UFS/RGB待回收。D01仍未完成，欢迎页不等同含StatusBar/Dock的SpringBoard桌面；原failed/null完整checkpoint判据保持。后续重点由迁移阻塞转为原首次设置流程及桌面，取消常规画面询问。证据：`artifacts/desktop-no-locationd-long/20261106T172309Z/native-hello-observation.json`。

# 原系统启动图迁移定时等待已定位

对170225Z子进程248/thread2245解析原SpringBoard.migrator相对方法表及反汇编：三个返回PC共同匹配装载基址0x100867000，对应performSystemAppMigrationRecreating:、performSplashBoardSystemLaunchImagesMigrationRecreating:、performMigration。原dispatch_time传入300000000000ns，原dispatch_semaphore_wait使用300秒期限，回调原生signal；返回后不按timeout结果跳转。未捕获装载映像UUID、未测本次实际等待起点，不宣称已超时/迁移完成；当前同配置30分钟自动观察继续。证据：`artifacts/desktop-no-locationd/20261106T165808Z/migration-timeout-analysis.json`。

# 无定位服务同配置30分钟自动实机观察中

172949Z唯一临时启动已接受，同无定位首桌面服务配置，原seed/1536MiB/32MiB日志/2Hz显示保持；使用已有1800/1860秒内核及ADT匹配合同与600/1000/1800秒全进程采样。自动回收后比较迁移子进程的原PNG编码/定时等待是否变化、原watchdogd与RGB；不再询问常规屏幕状态。尚无桌面。候选：`artifacts/desktop-no-locationd-long/20261106T172309Z`。

# 无定位服务同配置30分钟候选构建完成

同无定位服务配置长窗口候选构建通过：只将已有720/780秒合同改为1800/1860秒及既有600/1000/1800进程采样，原seed/服务/1536MiB/32MiB日志/2Hz显示与20秒硬件阈值保持。887记录内核、预链接/载荷、39项恢复QEMU及临时镜像通过；等待原PNG启动快照编码及迁移是否继续。无新桌面证据。候选：`artifacts/desktop-no-locationd-long/20261106T172309Z`。

# 无定位配置解除CoreLocation迁移栈，原启动快照仍在编码

170225Z实机自动回Android，2717条/5552176字节/dropped0，720秒完整199进程1040线程；locationd/CommCenter不在完整快照，无记录watchdog panic/压力kill。迁移child248最终线程不再有CLInternalPerformMigration，thread2258采样在原SplashBoard启动快照PNG编码（ImageIO/libz deflate），thread2245等定时信号量；单样本不能证明持续进展或死锁。SB仍等原BKS签到，851帧/五张RGB采样framebuffer差异0，末张已打开仍进度条，无桌面；原完整failed/null保留。下一轮保持服务/内存/显示，仅使用已有1800/1860秒匹配合同及600/1000/1800秒进程采样，判别冷启动快照生成与持续等待；旧30分钟轮次仍有FairPlay阻塞，不能代替当前配置。用户要求取消常规画面询问，继续自动回收。证据：`artifacts/desktop-no-locationd/20261106T165808Z/interpretation.json`。

# 无定位首桌面配置自动实机观察中

170225Z唯一临时启动接受；在已无CommCenter的首桌面配置中只新增停用com.apple.locationd，原迁移框架/错误处理、原watchdogd和720/780秒、1536MiB/32MiB日志/2Hz显示/硬件狗保持。与NoCommCenter基线的其他内核参数及ADT逐字节相同，只有disabled.plist多一项locationd。等待原迁移处理定位服务不可用时的实际行为、SpringBoard和RGB画面。按用户最新偏好不再逐轮询问屏幕状态，自动启动/等待/回收；仅自动恢复失败需要手动操作时提醒。候选：`artifacts/desktop-no-locationd/20261106T165808Z`。

# 无定位首桌面候选构建完成

仅在上一首桌面配置中再停用com.apple.locationd的新候选构建通过；原watchdogd、其余seed/OS、特殊AES拒绝及720/780秒合同保持。887记录内核、预链接/载荷、恢复QEMU39项及临时手机镜像通过。等待locationd未注册时原watchdogd实际行为、迁移/SpringBoard与现场桌面；不宣称本机定位能力。候选：`artifacts/desktop-no-locationd/20261106T165808Z`。

# 无CommCenter配置恢复完整快照，定位迁移/UI同步依赖

163425Z实机自动回Android，2605条/5277844字节/dropped0，720秒完整197进程973线程；CommCenter未出现在完整快照，原watchdogd无panic，压力kill无记录。MIG1203保持消失，BackBoard主线程和LS主线程已到原CFRunLoop；LS数据库写线程在CSStore deflate。SB仍等BKS签到；迁移child263等CoreLocation NSXPC，定位后台线程同步等ActivityKit/SpringBoard、BLS及IDS，另有迁移thread2728通过MIG40224请求BackBoard渲染启动图。存在启动互等假设，尚未证明完整因果。977帧、五张RGB采样framebuffer差异0，末张已打开仍加载条，无桌面；原完整failed/null保持。下一候选只再停用locationd，使用原迁移错误处理/回退，不伪造迁移完成；原watchdogd及720/780秒合同保持。证据：`artifacts/desktop-no-commcenter/20261106T163033Z/interpretation.json`。

# 无CommCenter首桌面实机观察中

163425Z唯一临时启动接受；只在已验证fairplay/adid停用配置中增加com.apple.CommCenter，原watchdogd/其他服务、720/780秒、1536MiB/32MiB日志/2Hz显示/硬件狗保持。等待原watchdogd在CommCenter未注册情况下的实际行为、迁移和SpringBoard桌面；上一155932Z日志已解除MIG1203，原CommCenter看门狗panic和部分全进程证据单独保留。候选：`artifacts/desktop-no-commcenter/20261106T163033Z`。

# 无CommCenter首桌面候选构建完成

仅在上一首桌面配置中再停用com.apple.CommCenter的新候选构建通过；原watchdogd、其余seed/OS、特殊AES拒绝及720/780秒合同保持。887记录内核、预链接/载荷、恢复QEMU39项及临时手机镜像通过。等待CommCenter未注册时原watchdogd实际行为、迁移/SpringBoard与现场桌面；不宣称本机基带功能。候选：`artifacts/desktop-no-commcenter/20261106T163033Z`。

# 首桌面配置已解除FairPlay等待，原CommCenter看门狗中断

155932Z实机自动回Android，2387条/4712675字节/dropped0；720秒命名服务段完整，原watchdogd因CommCenter两次诱导重启后180秒未签到请求panic，整体快照在ALLPROC_0171_000中断。读回端修复可选末段导致全部完整段被隐藏的问题，保留captured=false，从原始闭合段恢复170进程840线程，不补写尾段；旧完整快照新旧解码相同。FairPlay/AES启动已无记录，MIG1203消失，locationd主线程到原CFRunLoop；SB仍等BKS，BackBoard有CFPrefs同步等待，迁移child仍等CoreLocation迁移NSXPC。871帧、五张RGB采样framebuffer差异0，末张已打开仍加载条，无桌面。干净硬件返回判据实机通过，FDT无临时属性，实际跳过额外Android重启，cleanup_new_android_boot_id=null；原完整failed/null保持。下一候选仅在原首桌面配置中再停用CommCenter，保留原watchdogd及720/780秒，不宣称基带支持。证据：`artifacts/desktop-services-profile/20261106T155431Z/interpretation.json`。

# 首桌面服务配置实机观察中

155932Z唯一临时启动接受；临时Data加入原launchd disabled.plist停用fairplayd.A2/adid，原seed/OS/SystemOS及特殊AES拒绝保持。当前720/780秒、1536MiB/32MiB日志、2Hz显示和硬件狗，等待override实际采用、CoreLocation/迁移/SpringBoard及现场桌面；干净硬件返回分支将跳过冗余Android重启，完整checkpoint接受式未放宽。候选：`artifacts/desktop-services-profile/20261106T155431Z`。

# 首桌面服务配置候选构建完成

首桌面服务配置完整构建通过：原seed全部条目/字节保持，只追加root0644的原launchd disabled.plist停用fairplayd.A2/adid；原OS/SystemOS、特殊AES拒绝和其他服务保持，无伪造服务成功回复。887记录内核、预链接/载荷、恢复QEMU39项及临时手机镜像通过。1536MiB/32MiB/720/780秒/硬件狗；实际override是否被原launchd采用、迁移和现场桌面仍待实机。候选：`artifacts/desktop-services-profile/20261106T155431Z`。

# 2026-11-06 实机确认FairPlay特殊AES2201不支持

153706Z实机自动回Android，1459条/3261754字节/dropped0，360秒完整154进程618线程。14次原fairplay均以128位、32字节、有IV、加密operation0请求特殊AES selector2201；SoftwareAES在原unsupported分支返回e00002c7，普通CBC尚未执行，因此不能归因为CBC算法或空IV。locationd MIG1203仍排launchd、队列2；222帧、两张RGB采样framebuffer差异0，末张已打开仍加载条，无桌面。Android/root/新boot ID及临时属性清理通过，原failed/null保留。下一步采用临时Data的原launchd disabled.plist首桌面配置停用fairplayd.A2/adid，保持特殊密钥拒绝和原系统盘，不伪造服务成功；硬件密钥能力仍为未实现。证据：`artifacts/desktop-fairplay-aes-trace/20261106T153228Z/interpretation.json`。

# 2026-11-06 USB独立分支及相关组件已取得

USB更新位于独立`feat/usb`，最新`8a9910d7acfc2395ebf268161b89e2b71c4cd1fc`（北京时间2026-11-06 23:38:39），比当前main多7个未合入提交。已单独取回分支源码、QcomDwc3 `e4efe95c903a737e0f5955e5b50a8fb4d2a7d718`及该分支XnuPrelink `f24e3983659d3f46010478fa3cfa06ebeb0a5e9f`；候选为`artifacts/upstream-candidates/20261106T154225Z/UniXNU-usb`。仅这两个相关组件取得，不宣称其余分支依赖完整或raphael已适配。官方文档报告sheng/iPadOS27可进行USB设备枚举、信任、Mac配对和lockdown服务；主机外设枚举及持续传输仍待验证。SM8150/OS17的PHY、电源/时钟、角色检测、SMMU和原AppleUSB栈ABI须本机适配。官方该文同时记录fairplayd.A2/adid禁用才能完成SpringBoard，属于上游当前配置证据，不自动当作本机授权指令或成功回复。当前AES实机采集继续，活动pin保持。机器记录：`docs/upstream-usb-20261106T154225Z.json`。

# 2026-11-06 等待AES日志期间单次拉取上游完成

北京时间2026-11-06 23:42按用户要求再次单次拉取官方上游，独立main候选仍为`e2fdae4312d0acc3d8a52bc457101e7918095e6a`，相对今日上午候选新增0提交。20个gitlink中19个已取得指定版本，ArmCpu固定提交`2e11cda72740b985dedde3e32ba72b0fd64eb475`仍被官方远端返回not our ref；保留实际不匹配及失败日志，不宣称依赖完整。SoftwareAES与活动组件同为`4a45326da5c2cd6fe6813d79ee43db20805628af`，没有本轮AES问题的新修复。活动后端f0721e9、打包后端c96b299和正在运行的AES实机镜像保持。候选：`artifacts/upstream-candidates/20261106T154225Z/UniXNU`；机器记录：`docs/upstream-refresh-20261106T154225Z.json`。

# 2026-11-06 AES原错误实机采集中

153706Z唯一临时启动接受；当前360秒观察/420秒喂狗、1536MiB/32MiB日志、原FairPlay驱动/原服务及硬件狗保持，仅观察原AES入口与八个返回点的非密钥参数和状态。用户已重新确认在手机旁；等待自动Android回收和原AES错误，未重复启动旧镜像。候选：`artifacts/desktop-fairplay-aes-trace/20261106T153228Z`。

# 2026-11-06 AES原错误观察候选构建完成

针对原FairPlay AES helper的-22转换，fairplay专用AES原返回及非密钥参数观察候选构建通过；恢复原源码逐字节相同、原返回/回调保持。完整887记录内核、预链接/载荷、恢复QEMU39项和临时手机镜像通过。原FairPlay驱动、1536MiB/32MiB/360/420秒/原服务及硬件狗保持；下一步实机区分参数、密钥类型、准备和CBC错误，尚无桌面。候选：`artifacts/desktop-fairplay-aes-trace/20261106T153228Z`。

# 2026-11-06 原FairPlay驱动open实机通过，定位AES调用失败

063216Z实机自动回Android；1464条/3255897字节/dropped0，360秒完整151进程619线程。原FairPlay的16次匹配、取得服务及open全部成功，缺驱动缺口已修复；随后原FairPlayCryptoUtilities.cpp第233行的AES调用失败被转为EINVAL(-22)，16个原fairplay实例均正常退出。离线确认该行调用IOAESAccelerator虚表0x550，非零返回统一转-22，原AES实际错误码和参数仍未知，不据此推断corecrypto算法错误。locationd MIG1203仍等launchd、队列2；261帧、两张RGB采样framebuffer差异0，末张已打开仍加载条；无记录panic/压力kill，无桌面。用户现场启动文字后自动回安卓；原failed/null保留。下一步仅加AES原返回/非密钥参数诊断，保留原返回和回调。证据：`artifacts/desktop-original-fairplay/20261106T062720Z/interpretation.json`。

# 2026-11-06 原FairPlay驱动接入实机观察中

063216Z唯一临时启动已接受；原FairPlayIOKit组件已选入，原执行字节及26种符号addend保持。当前360秒观察/420秒喂狗、1536MiB/32MiB日志/原服务及硬件狗；等待实际注册、原fairplay匹配/迭代/open、MIG1203和桌面。候选：`artifacts/desktop-original-fairplay/20261106T062720Z`。

# 2026-11-06 原FairPlay驱动候选构建完成

原FairPlayIOKit候选完整构建通过：只增加同21H461原组件，所有原执行字节保持、26种符号addend保留；887记录内核、预链接/载荷、恢复QEMU39项和临时手机镜像通过。1536MiB/32MiB/原服务/硬件狗保持，显式360/420秒用于早期依赖验证；间接控制流、原驱动注册/open/MIG1203和桌面仍待实机。证据：`artifacts/desktop-original-fairplay/20261106T062720Z/build-result.json`。

# 2026-11-06 同版本原FairPlay驱动候选构建中

实机缺失匹配类已确认，原驱动显式预链接及原可执行字节保持通过，26种符号addend保留；155处固定跳转后内联数据分类，实际函数拒绝fallthrough/直接入边破坏。间接控制流仍待实机，不把离线原型字段改为运行成功；新候选重新构建日志/内核/载荷，并使用既有360/420秒合同加快依赖验证。候选：`artifacts/desktop-original-fairplay/20261106T062720Z`。

# 2026-11-06 实机确认原FairPlay驱动匹配缺口

060806Z实机自动回Android，2531条/5112724字节/dropped0，720秒完整195进程934线程。原fairplay的51次查询明确请求com_apple_driver_FairPlayIOKit，均无有效迭代器、未进入iterator-next/open，随后全部正常退出；当前预链接未包含该原驱动，具体启动依赖缺口已确认。921帧、五张RGB采样framebuffer差异0，末张已实际打开仍加载条；无记录panic/压力kill，现场本轮画面未确认，未验桌面。Android/root/新boot ID/临时属性清理通过，原failed/null保留。下一步接入21H461原驱动并以360/420秒验证注册/open/MIG1203，间接控制流与后续桌面仍待实机。证据：`artifacts/desktop-fairplay-iokit/20261106T060244Z/interpretation.json`。

# 2026-11-06 FairPlay原IOKit返回追踪实机运行中

060806Z唯一临时启动已接受，720秒原fairplay匹配/迭代/open结果及完整进程采集；保留1536MiB/32MiB日志/原服务/硬件狗。离线已生成原驱动代码/数据分类假设原型，未取得上机资格且未替换手机当前镜像。候选：`artifacts/desktop-fairplay-iokit/20261106T060244Z`。

# 2026-11-06 FairPlay原IOKit返回追踪候选构建完成

原fairplay启动IOKit结果追踪候选构建通过：原IOUserClient语句/调用次数保持，完整内核887记录、预链接/载荷、恢复QEMU39项及临时手机镜像通过。保持1536MiB/32MiB日志/720秒/原服务及硬件狗；下一步实际确认匹配条件、迭代是否为空或open错误。证据：`artifacts/desktop-fairplay-iokit/20261106T060244Z/build-result.json`。

# 2026-11-06 实机定位fairplay反复退出及launchd队列

IPC采样实机自动回Android，2428条/4825634字节/dropped0，720秒完整191进程/865线程，截断0。229个IPC全部匹配mach_msg2 PC；locationd62/785的MIG1203端口由launchd1持有，积4条请求。原fairplayd.A2在本轮51次正常status0退出，末尾无实例，lockdownd及商店服务同样排队。证明服务持续退出和请求积压，但退出原因仍未知；不能直接认定缺失FairPlayIOKit已是根因。941帧、5张RGB仍加载条且抽样framebuffer差异0，末张已打开；无记录panic/压力kill。Android/root/新boot ID/FDT清理通过，原failed/null保留，无桌面。下一步对原fairplay的IOKit匹配/迭代/open记录原返回，定位实际启动依赖。证据：`artifacts/desktop-ipc-peer/20261106T051358Z/interpretation.json`。

# 2026-11-06 IPC接收端候选已临时启动

053927Z唯一临时启动接受；720秒完整进程/IPC端口身份采集，保留1536MiB/32MiB日志/原服务/硬件狗，等待自动Android回收及现场桌面。候选：`artifacts/desktop-ipc-peer/20261106T051358Z`。

# 2026-11-06 IPC接收端候选构建完成

IPC目的接收PID/特殊回复端口身份及原fairplay/location退出原因采样版：完整内核887记录、预链接/载荷、恢复QEMU39项及临时手机镜像通过。保持1536MiB/32MiB日志/原服务/硬件狗，恢复720/780秒合同；等待实机确认原迁移MIG1203接收端。证据：`artifacts/desktop-ipc-peer/20261106T051358Z/build-result.json`。

# 2026-11-06 完整30分钟日志确认迁移等待持续

32MiB实机045854Z自动回Android，6290条/12905853字节/dropped0；600/1000/1800秒190/211/212进程、880/763/769线程全部完整，末尾1.934秒、截断0。原BackBoard57/LS98/CommCenter83存活，SpringBoard仍等BKS签到，BackBoard等数据迁移，迁移等CoreLocation，locationd62/785在末尾仍等MIG1203；三组均无fairplay进程，但真实IPC接收端尚未知。2975帧、13张RGB仍加载条且framebuffer差异0，已打开1699秒末张。无记录panic/压力kill，watchdog163签到/0失败；Android/root/新boot ID/FDT清理通过，原failed/null保留，无桌面。下一步构建720秒IPC接收端采样候选，保持1536MiB及原服务。证据：`artifacts/desktop-log32/20261106T045519Z/interpretation.json`。

# 2026-11-06 等待迁移IPC接收端，已完成离线采样实现

当前045854Z的32MiB手机实验继续运行，用户最新确认仍为进度条。离线确认原locationd的MIG1203请求与原fairplayd.A2的24字节处理器匹配，但运行时接收端未知；原600/1000秒均无fairplay进程。已在原128-word线程空位增加非阻塞IPC目的接收PID和特殊回复send-once复制出PID，并补原fairplay/location退出原因；原OSFMK/BSD两个-Werror对象、实际helper18项ASan/UBSan及18解码/3拒绝通过。仅主机结果，未启动新候选，等待当前32MiB回收后决定下一步。证据：`UniXNU-raphael/evidence/native-ipc-peer.json`。

# 2026-11-06 32MiB完整日志候选正在实机观察

32MiB/8192槽新日志、完整内核/预链接/载荷及临时手机镜像、高PA多L1恢复QEMU39项通过。保持1536MiB、原服务/watchdogd、2Hz显示、600/1000/1800秒全进程快照和硬件狗返回，仅扩日志容量以读回此前缺失的后期等待链。候选：`artifacts/desktop-log32/20261106T045519Z`。

# 2026-11-06 1536MiB显著减少服务重启，日志容量需补齐

1536MiB实机自动回Android；4096条/8622633字节/dropped0，日志1137.068秒后槽位用尽。600/1000秒188进程867线程及211进程772线程均完整，截断0；同名服务更换PID由896MiB的136降至4，原BackBoard57/LS98/CommCenter83保留。1000秒SpringBoard仍等BKS签到，BackBoard等迁移，迁移已到CoreLocation同步请求。1585帧、8张RGB抽样仍加载条且framebuffer差异0；无已记录服务退出/panic，但末尾未知。Android/root/新boot ID/临时属性清理通过，原failed/null保留，无桌面。下一步保持1536MiB与原服务，仅扩32MiB日志补全后期证据。证据：`artifacts/desktop-memory1536/20261106T041054Z/interpretation.json`。

# 2026-11-06 1536MiB对照已临时启动

20261106T041456Z唯一临时启动已接受；原内核39项QEMU验证通过，实际手机与模拟器均从0x10007c000使用1536MiB授权跨度（跨两个1GiB区间），新transition为24576字节。保留硬件狗返回与原服务，正在等待日志及现场桌面；构建/QEMU不能代替实机结果。候选：artifacts/desktop-memory1536/20261106T041054Z。

# 2026-11-06 1536MiB多L1恢复候选构建通过，准备临时启动

实际固件C逐页/边缘映射、原四档transition同字节、bootstrap20组与篡改60组ASan/UBSan通过；新日志/完整内核/载荷/手机镜像和高PA多L1恢复QEMU39项通过（transition24576字节）。只增加896→1536MiB授权内存并接线对应恢复结构；原XNU bootstrap、服务/watchdogd、AKS、可分页Data、8192 vnode、2Hz显示与600/1000/1800秒快照保持。等待实机内存抖动、SpringBoard及桌面。候选：`artifacts/desktop-memory1536/20261106T041054Z`。

# 2026-11-06 896MiB实机回收完成，准备多段内存映射

20261106T034001Z 自动回安卓成功（1253.964秒），无需人工或fastboot恢复；首次bootreason为bootloader，不能单凭此确定硬件狗分支。UFS3548条/7420979字节/dropped0，跨度1006.029秒；600秒174进程795线程、1000秒143进程644线程均完整。SpringBoard已越过BKS签到，1000秒等ChronoServices订阅回复；699.818秒BackBoard被proc-thrashing Jetsam回收，末尾原watchdogd因CommCenter180秒未签到panic。1204帧、六张后期RGB仍加载条且framebuffer抽样差异0，无桌面。Android/root/新boot ID及临时属性清理通过，原报告failed/null保留。下一步扩展本地多L1恢复映射，测试1536MiB；不改原服务。证据：artifacts/desktop-memory896/20261106T031531Z/interpretation.json。

# 2026-11-06 896MiB＋硬件狗返回版已临时启动

20261106T034001Z唯一临时启动已接受。新日志绑定内核/预链接/896MiB载荷/最终手机镜像和高PA恢复QEMU39项通过；本次显式启用硬件狗返回，保留原服务、软件密钥封装、可分页Data、8192 vnode、2Hz显示与600/1000/1800秒采集。等待内存压力与LS/BackBoard实际推进、现场桌面，以及硬件自动复位与Android bootreason；尚无桌面或硬件返回实测结论。候选：`artifacts/desktop-memory896/20261106T031531Z`。

# 2026-11-06 软件密钥封装实机已回收，开始896MiB与硬件狗候选构建

025712Z人工恢复Android，2219条/3843504字节/dropped0，日志跨度916.330秒。AKS selector10成功7次、11成功2次，接口缺口已推进；600秒131进程657线程完整，7组LS仍推进并采到原vm_page_wait。末尾822帧，5张RGB抽样匹配framebuffer、已查看末张仍加载条。未记录panic或服务退出，无最终快照，停止原因未知。Android完成/root/新boot ID/临时属性清理通过，原failed/null保留；现场加载条后黑屏，无桌面。下一候选增加到896MiB并按用户要求启用硬件狗返回，均待实机验证。证据：`artifacts/desktop-aks-wrap/20261106T025300Z/interpretation.json`。

# 2026-11-06 896MiB候选与硬件狗返回模式准备中

当前025712Z软件密钥封装实机仍运行，用户末次报告进度条后黑屏。等待期间已准备896MiB显式预算：沿用原审计大区间及单L1恢复，4GiB以上物理地址的原内核/恢复QEMU39项通过；并按用户要求新增显式硬件狗返回，在固件采集处理先重新装载原已验证20/21秒阈值后停止喂狗，避免恢复前关闭硬件狗的窗口。实际C函数ASan/UBSan和默认恢复QEMU39项通过；新模式真实复位、896MiB手机构建/执行尚待验。新模式只保留独立UFS日志，不返回完整FDT checkpoint；不改原服务/用户watchdogd。候选：`artifacts/desktop-memory896/20261106T031531Z`。

# 2026-11-06 软件密钥封装修正版已临时启动

20261106T025712Z唯一临时启动接受；选择官方AppleKeyStoreState8c70daf的软件封装并复用既有私有ADT UUID，针对原12次selector10不支持。主机实际C++/板级回调及完整构建、39项恢复QEMU通过。704MiB/可分页Data/原服务/显示/采样和1800秒窗口保持，等待实际结果；尚无桌面。

# 2026-11-06 提前全进程快照完整回收，接入软件密钥封装候选

20261106T022413Z自动回Android，3403条/6457475字节/dropped0；600/1000秒两组127进程573线程及130进程624线程完整，截断0，耗时1.498/1.425秒。LS98/477从应用/插件扫描推进至OpenStaging/用户会话，CPU28.02→75.32秒；SpringBoard末次等BKS签到。BackBoard57明确namespace1/code4为VM页不足Jetsam，之后两个重启实例被watchdog终止；原watchdogd本轮因media/audio缺签到panic，CommCenter末次仍正常。末尾1109帧，六张后期采样framebuffer差异0，已查看末张仍为加载条。12次AKS selector10不支持。Android完成/root/新boot ID/FDT清理通过，原failed/null保留；用户末次进度条、最终原生画面未知，无桌面。下一步只接入官方软件密钥封装，保持704MiB/可分页Data/原服务/显示。

# 2026-11-06 提前全进程快照候选已临时启动

20261106T022413Z唯一临时启动接受。仅新增600/1000秒独立全进程快照，原1800秒最终采样及原watchdogd panic保持；可分页Data、704MiB/8192 vnode与2Hz显示不变。等待原panic前完整等待链与现场桌面；尚无桌面验收。

# 2026-11-06 原panic前全进程快照候选构建通过

600/1000秒两次独立全进程快照候选构建完成；实际C/引用配对/sanitizer与缺final解码通过，13区记录/布局、完整内核/预链接/载荷、39项恢复QEMU及手机镜像通过。保留可分页Data、原服务/看门狗、704MiB、1800秒观察与2Hz显示；下一步临时启动以捕获原panic前等待链，无桌面验收。候选：`artifacts/desktop-early-processes/20261106T022045Z`。

# 2026-11-06 Data可分页实机降低wired压力，剩余CommCenter与process-thrashing

183513Z回收1595条/1299787字节/dropped0、10组LS，日志跨度1229.432秒。Data allocated223297536且pageable1、I/O错误0；末次wired74764对上轮127816（时点不同，不是精确驻留测量）。原media/audio/thermal均恢复签到，原watchdogd本轮因CommCenter缺签到panic；BackBoard57退出namespace1/code5为process-thrashing Jetsam，仍有内存压力。1205帧，8张后期RGB仍加载条且抽样framebuffer差异0。后期PID0只说明PID256以下未找到LS，不证明LS消失；无最终全进程/异常快照。自动回Android/root/新boot ID/FDT清理通过，原failed/null保留，无桌面。下一步仅增加600/1000秒全进程快照，继续原窗口。

# 2026-11-06 Data可分页修正版已临时启动

20261105T183513Z唯一临时启动已接受。功能变量仅Data页使用原pageable API并配对释放；原内核、源对象确实存在对应导入。4000次现有稀疏I/O差分及错误路径sanitizer、13区记录/布局、完整构建、39恢复QEMU和手机镜像通过；704MiB/8192 vnode/1800秒、原服务与2Hz显示保持。等待实际wired压力、BackBoard页不足Jetsam是否解除及现场桌面；构建不等于效果已实测。

# 2026-11-06 Data可分页候选完成构建

针对实机BackBoard VM页不足Jetsam，Data页改用原IOMallocPageableZero/IOFreePageable；4000次差分稀疏I/O及错误路径sanitizer、13区记录/布局、完整内核、载荷、39项恢复QEMU和手机镜像通过。704MiB与原服务、显示、1800秒观察保持，待实机证明内存与桌面效果。候选：`artifacts/desktop-pageable-data/20261105T182953Z`。

# 2026-11-06 BackBoard实机页不足Jetsam，转向Data页分配修复

174751Z长窗口提前被原watchdogd请求panic终止：1271条/848080字节/dropped0、8组LS，日志跨度1025.311秒。BackBoard57退出namespace1/code4已由固定XNU确认VM页不足Jetsam；临时Data占236015616字节常驻。四张RGB仍加载条，采样与framebuffer一致，末尾782帧；无最终快照，不能编造末尾服务/签到。configd末次仍成功签到；原失败/null保留。自动回Android完成/root/新boot ID/临时FDT清理确认，无桌面。下一步只将CPU拷贝的Data页换为原IOMallocPageableZero/IOFreePageable，使冷页可被原VM压缩；所有权和服务策略保持。

# 2026-11-06 当前显示/UUID修复版长窗口已临时启动

20261105T174751Z当前2Hz显示/平台UUID修复版已唯一临时启动。仅720/780秒观察/pet扩为既有v6的1800/1860秒，20秒硬件阈值保持；704MiB/8192 vnode/原服务/全进程采集与16MiB日志保持。887记录内核、预链接/载荷、39项恢复QEMU及镜像通过；前轮已证明configd越过gethostuuid、lockdownd原配置等待解除，但LS在720秒仍活跃，桌面尚未实现。等待本轮14组LS及后期画面/全进程链。

# 2026-11-06 平台UUID缺口实机修复，LS仍活跃

171504Z回收1888条/3404681字节/dropped0；120进程568线程、截断0，末尾采集1.472秒。configd37/320已越过gethostuuid进入原CFRunLoop，并新增配置线程；lockdownd71不再等PreferencesMonitor，平台UUID缺口实机修复成立。894帧/0传输错误、55签到/0失败，四张RGB仍加载条；无记录panic/pressure kill。LS478在606及720秒持续解析原MIBundle配置，SpringBoard与迁移等LS；不称固定死锁。Android/root/新boot ID/FDT清理通过；原失败/null保留，现场末次确认进度条，最终黑屏状态未确认，无桌面。

下一步只延长当前2Hz显示/UUID已修复版本至原有1800秒合同；旧30分钟试验发生在昂贵拷贝实现时期，不能替代当前性能版本的观察。

# 2026-11-06 平台UUID候选已临时启动

20261105T171504Z平台UUID候选唯一临时启动已接受。已有原优先适配读取显式/chosen/unixnu-platform-uuid；本地私有UUIDv4稳定保存，不冒充Apple或观测硬件身份。其余ADT逐字节恢复原值；服务/显示源码不变，仅重编新日志绑定。887记录内核、载荷、39项恢复QEMU及镜像通过。保持704MiB/8192 vnode/720秒/全进程采集和2Hz队列；等待configd的gethostuuid、lockdownd、迁移及现场画面，无桌面证明。

# 2026-11-06 全进程采集完整，定位平台UUID缺口

164135Z回收2043条/3843564字节/dropped0；125进程648线程全部采到、截断0，末尾广域采集1.546秒。917帧/0传输错误、watchdog58签到/0失败；五张RGB仍加载条，抽样与framebuffer一致，无记录panic/pressure kill。LS484.879秒发送数据库重建通知、605.709秒原数据库等待线程已返回工作队列；迁移254推进到IXPlaceholder图标承诺，installcoordinat290等installd238扫描原framework。确定configd37/320在gethostuuid→IOBSDGetPlatformUUID等缺失IOPlatformUUID，lockdownd71/348等SCPreferences通知；不称这已是桌面唯一原因。Android/root/新boot ID/FDT清理通过，原失败/null保留，现场加载条后黑屏，无桌面。

下一步补齐已链接平台UUID适配的显式手机ADT输入，保持服务/窗口/内核及显示。

# 2026-11-06 全存活进程采集版已临时启动

20261105T164135Z全进程/线程采集版唯一临时启动已接受。原proc_iterate/NOWAITTRANS遍历，不再受PID255或八服务限制；每进程512线程上限、32线程分块、总数/截断/耗时明确记录。增加LS驻留页路径参数，按实际PC核对才能解释为正在执行的文件操作。原八槽/服务/704MiB/8192 vnode/720秒/16MiB日志及2Hz显示保持。实际C引用配对、路径9项sanitizer、旧解码兼容、完整内核/预链接/载荷、39项恢复QEMU和镜像通过；等待本轮广域接收链，无桌面。

# 2026-11-06 零I/O窗口对照回收，扩大等待链采集

160537Z回收965条/941304字节/dropped0，五组LS及720014ms最终快照完整。实际I/O窗口0/0/0、SSD周期5/15/25，睡眠计数143/147/0；零时间窗口仍保留在途高优先级I/O竞争。868帧/0传输错误、watchdog55签到/0失败，四张RGB仍加载条并抽样匹配framebuffer，无记录panic/pressure kill。末尾LS已在原LSDReadClient处理store回复及OpenStaging初始化，不能仍称所有服务都等seeding；SpringBoard等BKS签到，BackBoard等数据迁移，迁移等profiled限制应用，profiled还见lockdown接收。具体剩余接收端待全进程采集。read elapsed345.917→333.313秒，单轮差异不足以认定提速。Android/root/新boot ID/FDT清理确认；现场进度条后黑屏，原失败/null保留，无桌面。

证据：`UniXNU-raphael/evidence/native-io-window.json`；下一步一次采集所有存活进程线程及LS路径，保持原服务行为。

# 2026-11-06 零后台I/O窗口对照已临时启动

20261105T160537Z唯一临时启动已接受。原XNU的三项PE_get_default后台节流窗口25/100/500ms改为0/0/0ms，SSD周期、原服务策略、704MiB/8192 vnode/720秒、16MiB日志和2Hz队列保持；只读快照末尾增加实际窗口与节流次数。ADT精确差异/反向还原及两项坏合同拒绝、完整内核、预链接/载荷、39项恢复QEMU和手机镜像通过。等待本轮生效值、LS扫描进度及画面，尚无桌面。候选：`artifacts/desktop-io-window/20261105T160053Z`。

# 2026-11-05（UTC）：接收端完整采到，当前共同等待LS扫描

153215Z完整回收967条/952451字节/dropped0，五组LS及720009ms最终快照完整。BackBoard21线程全部采到、无截断：695等原数据迁移、686等LS数据库；profiled142已采到，1436同等LS。SpringBoard末尾也回到LS应用记录查询，故此前BKS签到等待并非固定不变的死锁。LS488仍扫描本地化/属性列表；多线程落在throttle_lowpri_io，原卷均已报告solidstate。868帧/0传输错误，四张后期RGB仍加载条且抽样匹配framebuffer；UFS逻辑读7.265GB、read elapsed345.917秒含抢占。watchdog55签到/0失败、无记录panic/pressure kill。Android/root/新boot ID/FDT清理确认，原失败/null保留。现场确认进度条，末尾原生画面未知，无桌面。下一步对原XNU后台I/O节流窗口做单变量对照，保持服务及显示。证据：`UniXNU-raphael/evidence/native-bks-receiver.json`。

# 2026-11-05 BKS接收端与profiled采样已临时启动

20261105T153215Z唯一临时启动已接受。针对SpringBoard等待BKS签到回复，新增独立最多32线程BackBoard接收端快照；同时选入实际LS及迁移MCProfileConnection等待链的profiled。原八槽协议、服务行为、已修正2Hz显示队列、704MiB/8192 vnode/720秒及16MiB日志保持。完整内核、预链接/载荷、39项恢复QEMU和最终手机镜像通过。等待接收线程实机证据，尚无桌面。候选：`artifacts/desktop-bks-receiver/20261105T151856Z`。

# 2026-11-05 多帧队列修复实机生效，SpringBoard等待BKS签到

145317Z完整回收958条/896954字节/dropped0，五组LS及720073ms最终快照完整。timer回调和multi_head提交已观察；855帧/0错误，后期两段1.997Hz持续。相对不限速差异拷贝祖先，拷贝elapsed366.571降至73.178秒、BackBoard提交线程CPU400.070降至23.579秒。四张后期RGB仍为加载条、抽样framebuffer差异0。SpringBoard末尾主线程等原BKSSystemShellService签到回复；不再采到此前LS数据库等待，但不扩大为全部LS工作完成。BackBoard57首八线程记录明确截断，实际接收处理尚未知。下一步只增独立有界32线程BackBoard接收端采样，原服务和已修正提交保持。55次watchdog签到/0失败，所采服务无异常；Android/root/新boot ID/临时FDT清理确认，原失败/null保留。现场启动文字→进度条→黑屏，无桌面。证据：`UniXNU-raphael/evidence/native-copy-queue.json`。

# 2026-11-05 多帧队列修正版已临时启动

145317Z唯一临时启动已接受。沿原模式/500ms提交节奏，修正单帧限定：已验证队首允许带后继，按原TAILQ更新head/backlink/tail，完成后重设定时器处理剩余队列；原completion引用和代际保持。实际源码1至8帧FIFO及旧两帧拒绝复现通过ASan/UBSan；887记录内核、预链接/载荷、39项恢复QEMU和最终镜像通过。704MiB、8192 vnode、720/780秒和16MiB日志保持。等待多帧/定时器标记、实际提交及LS；尚无桌面。候选：`artifacts/desktop-copy-queue/20261105T144653Z`。

# 2026-11-05 定时提交完成回收，定位多帧队列处理缺口

141301Z回收814条/401999字节/dropped0，五组LS和720046ms最终快照完整。原模式属性恢复，所采服务未记录异常，但仅9帧/13kicks/11validations；不能将0.994秒拷贝累计解读为性能提升，实际2Hz尚未成立。源代码仍只允许没有后继的pending队首，异步定时延迟可使第二帧入队并阻止继续提交；下一候选修正原TAILQ队首出队与剩余队列唤醒，实机因果待验。末尾服务采样仅覆盖PID1..255，不能由缺失推断服务退出、BackBoard CPU或LS完成。watchdog55签到/0失败；Android启动完成/root/新boot ID/临时FDT清理确认，原失败/null保留。现场确认进度条，末尾画面未知，无桌面。证据：`UniXNU-raphael/evidence/native-copy-pace.json`。

# 2026-11-05 原模式属性加定时提交候选已临时启动

141301Z唯一临时启动已接受。以差异拷贝工作父候选为基线，保留原显示模式属性；仅在原workloop上用IOTimerEventSource延后已验证的pending提交，实际拷贝起始间隔至少500ms，首帧立即提交。保留8192 vnode、704MiB、720/780秒、16MiB日志和原服务。887记录内核/未定义0、预链接/载荷、39项恢复QEMU及手机镜像通过；正在等待实测帧频、CPU与LS，尚无桌面。候选：`artifacts/desktop-copy-pace/20261105T140919Z`。

# 2026-11-05 2Hz候选出现显示模式断言，已完整回收

133438Z回收828条/456390字节/dropped0，五组LS和720120ms最终快照完整。刷新属性published=1，但提交/完成均0；SpringBoard原FBSDisplayMode校验触发EXC_BREAKPOINT，累计32次。这轮回退到显示初始化失败，不能将零拷贝当作性能改善。58次watchdog签到/0失败，无记录原生panic；LS仍持续原数据库扫描，最终等签名验证IPC。现场启动文字后黑屏，无桌面；Android启动完成/root/新boot ID/临时FDT清理确认，原失败/null保留。下一步核对原刷新属性消费者并修正。证据：`UniXNU-raphael/evidence/native-software-refresh.json`。

# 2026-11-05 2Hz软件提交候选已临时启动

133438Z唯一临时启动已接受；原OS软件slot301/getRefreshAttributes与原setDisplayRefreshProperties发布固定500ms周期，用于减少单CPU反复扫描加载条的开销；继承面板模式保持。实际生成358-slot vtable确认适配器slot301、原发布器字节/虚调用检查、887记录内核、预链接/载荷、39项恢复QEMU及最终手机镜像通过。保留标准交接、差异拷贝、8192/704MiB/720秒、16MiB连续日志与原服务。等待published/实测帧间隔、CPU、LS和现场画面，不构成桌面或实际2Hz已生效的证明。候选：`artifacts/desktop-software-refresh/20261105T133049Z`。

# 2026-11-05 差异拷贝仅小幅降低总开销，转向软件提交节奏

130408Z回收1018条/1014515字节/dropped0，五组LS与720021ms最终快照完整；4267帧/0错误，58签到/0失败，无记录panic/pressure kill。差异拷贝累计elapsed398.639降至366.571秒（约8%），最大0.377降至0.141秒；BackBoard提交线程仍400.070秒CPU，LS477仍等容器查询。五张后期RGB仍为加载条、抽样framebuffer差异全0；现场进度条，无桌面。Android/root/新boot ID/FDT清理完成。下一步用原显示刷新ABI限制软件提交频率，保留面板模式与原服务。证据：`UniXNU-raphael/evidence/native-frame-diff.json`。

# 2026-11-05 差异拷贝候选已临时启动

130408Z唯一临时启动已接受；仅将每帧全量scanout写入替换为现有通用helper的cached-shadow差异拷贝，首帧全写、后续64字节变化块、空白提交使shadow失效，额外10,108,800字节缓存。保持标准控制台交接、逻辑display bytes、拷贝计时与RGB/framebuffer采样、8192/704MiB/720秒及原服务。复用实际helper既有ASan/UBSan；887记录内核、预链接/载荷、39项恢复QEMU及最终镜像通过。等待本轮拷贝耗时、LS进展与现场画面，尚无桌面验收。候选：`artifacts/desktop-diff-handoff/20261105T130103Z`。

# 2026-11-05 标准显示交接生效，定位全帧拷贝耗时

123830Z回收1022条/1011327字节/dropped0，五组LS与720006ms最终快照完整；console_released=1，五张225/347/467/587/707秒RGB图均为加载条（细部像素有变化），抽样framebuffer差异全0。2806帧/0传输错误，watchdog58签到/0失败，无记录panic/pressure kill。拷贝累计elapsed398.639秒、最大0.377秒，包含抢占；BackBoard512账本419.649秒CPU，LS649仅1.756秒并仍同步等容器查询。现场进度条，无桌面；Android/root/新boot ID/FDT清理完成。下一单变量复用差异拷贝helper，保留标准交接、8192/704MiB/720秒及计时。证据：`UniXNU-raphael/evidence/native-console-handoff.json`。

# 2026-11-05 标准显示交接候选已临时启动

123830Z唯一临时启动；首个有效图形提交前调用固定XNU标准kPEReleaseScreen，退出文字/内核启动图所有权。UFS捕获入口仍位于disableConsoleOutput判断前；仅另增只读拷贝elapsed累计/最大值与console_released标记。8192 vnode、704MiB、720/780秒、16MiB日志、原服务及全量像素拷贝保持；887记录内核、预链接/载荷、39项恢复QEMU及最终镜像检查通过。等待本轮实机画面、像素一致性和LS快照，不构成桌面证明。候选：`artifacts/desktop-console-handoff/20261105T123516Z`。

# 2026-11-05 已读回后期画面：仍是加载条，发现显示交接缺口

121119Z回收971条/894327字节/dropped0，五组LS与720039ms最终快照完整。274/394/514/634秒四张RGB缩略图均为黑底加载条，尚无桌面；一次framebuffer抽样差46像素，具体写入者和时序尚未确定。2299帧/0传输错误、55次watchdog签到/0失败，无记录panic/pressure kill。UFS累计elapsed读取349.23秒/验证17.55秒/交付5.07秒，包含调度等待；BackBoard493账本累计346.44秒CPU，LS472仅2.41秒且继续原应用注册。现场黑屏，Android/root/新boot ID/FDT清理确认。

当前适配器首帧前没有标准initialize_screen(NULL,kPEReleaseScreen)交接；固定XNU该入口负责关闭文字和内核启动图、释放控制台屏幕所有权。下一单行为补此交接，UFS日志捕获在disableConsoleOutput判断前，因此连续日志保持；差异拷贝隔离候选暂缓。证据：`UniXNU-raphael/evidence/native-late-frame.json`。

# 2026-11-05 后期帧与UFS耗时采样已临时启动

121119Z唯一临时启动已接受；仅增诊断：每120物理秒保留90×195 RGB提交帧缩略图和framebuffer抽样一致性、UFS读取/块验证/交付elapsed ticks。704MiB、8192 vnode、720/780秒、16MiB日志及原服务行为保持；显示以20261102T162658Z冻结基线加采样。实际helper ASan/UBSan、PNG解码、887记录内核、预链接/载荷、39项恢复QEMU及镜像检查通过。正在等实机回收，尚无后期内容或桌面结论。候选：`artifacts/desktop-late-frame/20261105T120824Z`。

# 2026-11-05 8192 vnode已生效，LS扫描仍未完成

113744Z完整回收831条/449257字节/dropped0；五组LS与720095ms最终快照完整。63组desired8192，实际vnodes5620、namecache5738/9011、回收884，缓存未满；扩大缓存未解决桌面。SpringBoard27线程250仍等LS数据库，lsd99线程483继续原应用本地化及资源目录扫描。2724帧/0传输错误、watchdog58签到/0失败，无记录panic/pressure kill。逻辑读量由1024对照的4827329536降至4276941824字节，但不能单凭读量认定扫描加速。

现场黑屏，无桌面；Android启动完成/root/新boot ID/临时FDT清理确认，原失败/null不改。下一步加只读读盘阶段耗时和后期实际提交帧缩略采集，区分扫描迟缓与显示内容问题，不原样重跑或盲目延长窗口。证据：`UniXNU-raphael/evidence/native-vnode8192.json`。

# 2026-11-05 VFS实测：vnode目标实际为1024

111028Z回收826条/442341字节/dropped0，五组LS与720097ms最终快照完整；16MiB日志余量充足。63组实测desiredvnodes始终1024，实际vnodes在243秒前后达到1024；namecache启用、最高1038/1126，不能声称namecache容量饱和。LS98线程474继续扫描、插件注册，SpringBoard26主线程249等LS数据库；2488帧/0错误、watchdog55签到/0失败，无记录panic/pressure kill。现场黑屏，桌面未验收。

本轮Android/root/新boot ID/临时FDT清理已确认，未再次进入recovery。下一单变量使用固定原XNU的PE_get_default入口，在ADT /defaults加入kern.maxvnodes=8192；沿704MiB/720秒/16MiB与原服务/显示，观察LS扫描是否加快及内存影响。低vnode容量与扫描低速的因果尚待对照，不认定为已修复根因。证据：`UniXNU-raphael/evidence/native-vfs-cache.json`。

# 2026-11-05 30分钟冷启动：LS持续扫描，日志容量耗尽

102009Z回收2048条/676476字节/dropped0，14组LS采样全部完成；日志恰好写满8MiB的2048槽，截在最终服务线程数组6656/8256字。独立解析仅使用完整段和6个完整服务槽：1800087ms、8912帧完成/0显示错误、163次watchdog签到/0失败。最终SpringBoard26主线程249仍同步等LaunchServices数据库，lsd99线程483在多轮间持续推进签名、容器、扩展与Info.plist扫描；没有固定死锁证据。无记录panic/pressure kill，最后UFS5875475456字节/756906请求/0失败。显示非黑统计仅覆盖前八帧。

现场进度条一半多后黑屏，桌面未验收；原passed=false/xnu_executed=null不改。Android再次RescueParty进入recovery，保存日志后一次正常ADB重启确认boot_completed/root/新boot ID/临时FDT清除。下一步补16MiB日志及实际vnode/namecache计数，区分低缓存导致反复扫描与正常慢启动，不原样重复30分钟。证据：`UniXNU-raphael/evidence/native-ls-ledger-long.json`。

# 2026-11-05 ledger修正版30分钟冷启动候选已临时启动

102009Z已接受唯一临时启动；仅将已实机完整采样修正版的观察/pet合同从720/780秒延至1800/1860秒，704MiB、20秒硬件阈值、诊断task/pmap try-lock与ledger引用、原服务及显示策略保持。887记录内核、预链接/载荷、39项恢复QEMU与手机镜像检查通过；复用原长窗口边界和ledger回归证据。当前等待周期LS线程和最终快照，未证明LS初始化完成或桌面。候选：`artifacts/desktop-ls-ledger-long/20261105T101613Z`。

# 2026-11-05 ledger修正实机采样完成，恢复冷启动长窗口

095332Z回收835条/444209字节/dropped0；五组周期LS采样全部完成，第三、四、五组正常返回，720079ms最终快照与RETURNING齐全。本轮验证诊断pmap/ledger引用配对修正解决了此前反复出现的第三次采样中断。2774帧完成、0显示传输错误、watchdog58签到/0失败、UFS失败0，无记录pressure kill/panic。帧非黑统计仅覆盖前八帧，不能证明后续桌面内容。

同一lsd98工作线程依次处于plist解析、插件注册和应用签名扫描，末尾同步等MCM容器查询；SpringBoard27仍等LS数据库初始化。现场只确认进度条，没有桌面验收。Android boot_completed/root/新boot ID/临时FDT属性清除均已确认，原完整checkpoint失败和xnu_executed=null保留。下一单变量采用已支持的1800/1860秒冷启动观察合同，保留704MiB、原20秒硬件阈值、已修正观察器和原服务/显示行为。证据：`UniXNU-raphael/evidence/native-ls-ledger-reference.json`。

# 2026-11-05 ledger引用修正版已临时启动

095332Z已接受唯一临时启动；诊断同时保留pmap关联ledger，匹配固定ARM pmap_destroy的无条件ledger释放，原task/pmap try-lock和服务行为保持。实际原ARM wrapper复现旧消耗、修正2000次配对ASan/UBSan、887记录内核、预链接/载荷、39项恢复QEMU及镜像通过。704MiB、720/780秒、runtime-only。等待第三次及后续LS采样、最终快照和实际屏幕，尚未证明实机中断已解决，无桌面验收。候选：`artifacts/desktop-ls-capture-ledger-ref/20261105T093840Z`。

# 2026-11-05 确认诊断pmap/ledger引用配对错误，修复构建中

092115Z的pmap try-lock候选回收321条/100972字节/dropped0，360922ms与两组完整LS；第三次lsd98线程599进入后仍无完成，末尾438帧、UFS失败0、无最终快照，现场黑屏。task/pmap锁修改均未解决中断。固定实际编译ARM源码确认：pmap_reference只增加pmap计数，pmap_destroy却每次释放ledger引用；原诊断循环因此消耗服务账本引用。已改为在目标task锁内同时ledger_reference，原释放接口保持。实际原ARM wrapper复现旧引用消耗，修正后2000次配对、争用/空pmap/空ledger ASan/UBSan通过；实机因果效果尚待新镜像验证。704MiB、720/780秒及原服务行为不变。

本轮Android返回时出现system_server/ActivityStarter空指针及RescueParty进入recovery，已保存私有日志；一次正常ADB重启后boot_completed/root/新boot ID/临时属性清除确认。尚未确定与原生实验的关联，原失败/null保留，无桌面。证据：`UniXNU-raphael/evidence/native-ls-capture-pmap-trylock.json`、`UniXNU-raphael/evidence/native-ls-ledger-reference.json`。候选：`artifacts/desktop-ls-capture-ledger-ref/20261105T093840Z`。

# 2026-11-05 pmap非阻塞用户栈采样已临时启动

092115Z已接受唯一临时启动；仅将诊断用户栈查询改用固定XNU原pmap_try_lock及pmap_vtophys，持共享锁读并标记争用，避免原pmap_find_phys的等待路径。实际helper争用/成功/未映射/授权边界ASan/UBSan、旧新解码、887记录内核、预链接/载荷、39项恢复QEMU和镜像检查通过；704MiB、720/780秒及原服务行为不变。正在等待实机采样，尚未证明pmap锁为中断根因，无桌面验收。候选：`artifacts/desktop-ls-capture-pmap-trylock/20261105T091721Z`。

# 2026-11-05 task try-lock回收：中断仍在第三次线程采样

085206Z回收329条/101912字节/dropped0，361206ms、两组完整LS。第三次进入lsd98线程601后没有完成标记；task try-lock未解决中断，task互斥锁根因仍未成立。末尾638帧、UFS失败0、无最终快照；现场只确认进度条，无桌面。Android/root/新boot ID/临时属性清除确认，原失败/null报告保留。固定XNU源码显示pmap_find_phys对外部pmap会获取可自旋共享锁，诊断目前在禁抢占段调用；下一候选仅将该查询改成原pmap_try_lock及pmap_vtophys，持锁读并明确标记争用，尚不声称实机根因。证据：`UniXNU-raphael/evidence/native-ls-capture-trylock.json`。

# 2026-11-05 目标task非阻塞采样修正版已临时启动

085206Z已接受唯一临时启动；针对已定位的lsd线程采样中断，改用原task_lock_try，忙时跳过用户栈并显式记录，不等待目标task互斥锁。实际C争用/引用检查、旧/新解码、内核/载荷、39项恢复QEMU和手机镜像检查均通过。704MiB、720/780秒及原服务行为不变。当前正在等待日志，尚未证明该task锁是内部中断点，桌面仍未验收。候选：`artifacts/desktop-ls-capture-trylock/20261105T084821Z`。

# 2026-11-05 LS采样中断定位至线程781

081841Z回收324条/97865字节/dropped0、约361秒日志与两组完整LS。第三次采样前四个lsd98线程均完成，线程781进入采集后无完成标记；内部具体操作及阻塞/异常尚未知，不能把诊断中断归因为原LS死锁。无最终快照，现场启动文字后黑屏。Android/root/新boot ID/临时属性清除确认；原失败/null保留，无桌面。下一候选把目标task的阻塞锁改为原task_lock_try，忙时明确跳过用户栈，保持704MiB、720/780秒和原服务行为。证据：`UniXNU-raphael/evidence/native-ls-capture-trace.json`。

# 2026-11-05 LS采样阶段候选已临时启动

081841Z接收窗口已结束，现场启动文字后黑屏，电脑未检测到Android；已请求人工长按恢复，提取器等待连接。本轮日志尚未读回，不对中断原因或桌面作新结论，未启动下一镜像。

081841Z已接受唯一临时启动；周期采样增加入口、进程及逐线程前后持久标记，用已有720/780秒合同定位前轮约361秒日志提前中断；704MiB、20秒硬件阈值和原服务行为保持。主机构建、39项恢复QEMU及镜像结构通过，runtime-only，未重复源/分区哈希。正在等待本轮回收，不构成桌面验证。候选：`artifacts/desktop-ls-capture-trace/20261105T081126Z`。

# 2026-11-05 LS分段回收：约361秒处提前中断

297条/93412字节/dropped0，仅约361秒独立日志与两组LS采样；第一组lsd尚不存在，第二组lsd98线程612在原系统内容扫描。末尾457帧、UFS读取0失败；未记录panic/pressure kill，无最终快照。停止位置贴近第三次采样，具体中断操作未知，不能宣称完整30分钟或LS死锁。Android/root/新boot ID/临时属性清除已确认，原失败/null保留，现场加载条或黑屏，无桌面。证据：`UniXNU-raphael/evidence/native-ls-scan-window.json`。下一候选补采样阶段持久标记，采用已有720/780秒窗口定位中断，不盲目延长等待。

# 2026-11-05 恢复主线：LS分段进度候选已临时启动

用户要求继续推进主线后，072851Z已接受唯一临时启动，runtime-only；704MiB、1800秒观察/1860秒绝对pet和20秒硬件阈值。每120物理秒独立记录LS线程，等待本轮回收；这不构成桌面验证。无flash/erase，未重复源或boot分区哈希。候选experiment.json记录当前状态，之前“构建后停止”的结果保留为历史。

# 2026-11-05 冷启动合同与LS分段日志构建完成，按要求停止

候选 `artifacts/desktop-ls-scan-window/20261104T182635Z/` 已完成内核、预链接/载荷、39项恢复QEMU和手机镜像结构检查。显式v6合同为1800秒观察/1860秒绝对pet，704MiB及20秒硬件阈值保留；每120物理秒保存独立LS线程进度、最多16组，UFS日志分配8MiB。实际C计时/线程引用寿命/上限、watchdog边界与错配拒绝、旧日志兼容和新分段解码已通过ASan/UBSan。

按用户“构建完成之后停止”要求，本候选未上机，未执行生成的run.py；实机效果与桌面仍未验证。上一轮MCM补采的黑屏及原失败/null结果不变。后续若继续，可用本候选区分LS持续扫描与停滞。结果及报告指针：`artifacts/desktop-ls-scan-window/20261104T182635Z/result.json`。

# 2026-11-05 MCM补采已回收：LS已推进到插件注册

180247Z人工回Android后完整回收727条/360463字节/dropped0，720104ms观察、2237帧完成/0传输错误、55次watchdog签到/0失败，未记录pressure kill或panic。两容器进程均有线程：一个在正常CFRunLoop，另一个执行SetDataProtection后的元数据文件创建/VNOP_CREATE；lsd98线程470在LSRegisterPluginWithInfo/LSDatabaseRebuildContext注册插件，已越过上一轮MCM签名同步等待。SpringBoard仍等LS数据库；不能认定MCM固定死锁。现场黑屏，无桌面；Android/root/临时FDT清理确认，原完整返回失败及xnu_executed=null保留。证据：UniXNU-raphael/evidence/native-mcm-receiver.json。下一步为冷启动一次1800秒运行并每120秒采LS线程进度，以区分持续扫描与停滞。

# 2026-11-05 704MiB长窗口已回收：定位MCM同步回复等待

173412Z人工回Android，root/临时FDT清除确认；727条/358407字节连续日志，dropped0、完整快照及RETURNING，实际720091ms。2299帧完成/2300提交、0传输错误，watchdog55签到/0失败，无记录pressure kill/panic。SpringBoard仍等LS seeding；lsd99的492线程在container_set_code_signing_info_for_identifier同步等待MobileContainerManager。两容器进程64/92存在，但八槽优先级使其均未采线程；不能认定固定死锁，扫描位置较360秒轮有变化。现场黑屏，无桌面；完整原返回失败及xnu_executed=null保留。证据：UniXNU-raphael/evidence/native-memory704-long.json。下一候选仅把实际容器接收端提升到采样槽，保留704MiB、720/780秒及原服务策略。

# 2026-11-05 704MiB实机对照：内存状况改善，LS仍在初始化

171336Z人工恢复后回收378条/314898字节连续日志，dropped0、完整快照及RETURNING。初始VM180166个4KiB页与704MiB一致；同360秒窗口显示599帧（512MiB对照2帧）、0传输错误，watchdog22签到/0失败，无记录内存不足杀进程或panic。UFS累计3.70GiB（对照5.12GiB），pageable缓存更多。SpringBoard仍等LS数据库；lsd工作线程在原应用Info.plist解析。现场黑屏；完整原返回失败/null保留，Android/root/临时属性清除确认，无桌面。下一轮沿704MiB采用既有720/780秒合同，观察LS扫描是否完成，其他策略不变。证据：UniXNU-raphael/evidence/native-memory704.json。

# 2026-11-05 CommCenter重点采样回收，转704MiB内存对照

165251Z独立375条/305200字节/dropped0，详细服务快照及RETURNING完整；显示2帧/0传输错误、watchdog18次签到/0失败，未记录原watchdogd panic。现场加载条或黑屏后回Android，root/新boot ID/临时属性清除确认。SpringBoard主线程仍等LaunchServices数据库；lsd在原应用签名扫描，另有页面缺失低优先级I/O等待；CommCenter主线程CFRunLoop、采到活动工作线程，不能认定固定死锁。完整原返回报告仍失败/null，无桌面。

下一轮针对此前已记录的vm-pageshortage，以704MiB对照512MiB，保持360秒观察/420秒pet、原服务策略和显示基线。主机映射/ASan/UBSan通过；新日志分配、内核和载荷准备完成，正在QEMU资格验证，尚未上手机。证据：UniXNU-raphael/evidence/native-commcenter-focus.json。

# 2026-11-05 原watchdogd理由已回收：CommCenter超时

163051Z已自动回Android并普通重启/root/FDT清理。429条独立日志/98309字节/dropped0；原watchdogd指出CommCenter四次被重启后180秒无签到，backboardd等列出服务最后签到均0秒。UFS文本与独立7/8区CRC匹配的静态文本相同；完整delta仍溢出，原失败/null不改，无桌面。原memorystatus已出现below-critical与vm-pageshortage杀MobileGestaltHelper/remoted，不能继续称没有内存压力。

下一轮仅调整诊断采样：既有八槽优先名单加入CommCenter，并采用已支持360/420秒合同，争取在已观察到的368/500秒panic之前取得线程栈；不更改原服务行为或内存分配。原系统有CommCenter非蜂窝启动项，所以不能仅以无基带驱动归因。证据：UniXNU-raphael/evidence/native-watchdog-reason.json。

# 2026-11-05 接续：Data固态属性成立，定位原watchdogd panic

C02b.23：RAM Data标准固态属性实机生效，102222Z的spec_open为isssd1。297条/81044字节、dropped0，UFS错误0；原watchdogd selector2提前请求panic，现场启动文字后自动重启。完整返回delta超过1MiB、原失败/null保留；独立7/8区CRC匹配证明panic来源，具体理由未恢复，未到计划服务快照。Android普通重启/root/FDT清理完成；无桌面。证据：UniXNU-raphael/evidence/native-data-ssd.json。

下一候选仅补存原watchdogd请求的2048字节理由：在selector2正常线程路径、释放clientGate后写既有UFS日志，再进入原panic；不改变服务策略或720/780秒合同。原debug_buf未初始化，原msgbuf中没有具体理由，故现存快照不能补出该文本。

# 2026-11-04 当前唯一实验：RAM Data固态介质属性

候选artifacts/desktop-data-ssd/20261104T101952Z已通过887记录内核、预链接/载荷、39项恢复QEMU和手机镜像，即将/正在唯一临时启动。仅为NativeRamBlock发布标准Device Characteristics/Medium Type=Solid State；保持原节流策略、512MiB、720/780秒和20秒硬件阈值。预期原spec_open的Data isssd从0到1，比较LS数据库初始化及现场桌面；属性成立本身不算桌面。此前095342Z已人工回Android并回收724条完整独立日志，现场加载条后黑屏。

# 2026-11-04 IconServices接收端结果：仍在工作，RAM Data介质属性缺失

095342Z已结束并人工回Android。独立724条/357275字节连续日志、dropped0、详细快照完整，观察720035.919ms；2349帧提交/完成、0拒收/清黑/传输错误，watchdog58签到/0失败，无记录服务退出。现场启动文字→加载条→黑屏，无桌面；完整checkpoint失败/xnu_executed=null报告保持。

lsd正在原应用签名扫描，已经越过前轮IconServices同步回复等待；iconservicesagen111在ISStoreMapTable页面缺失后的原throttle_lowpri_io。未观察到CoreImage上下文故障或LS循环等待。原spec_open显示OS/SystemOS isssd=1，RAM Data isssd=0；固定XNU最低优先级HDD/SSD周期为200/25ms。下一单变量为Data发布标准固态介质属性，不改变原节流策略或720/780秒窗口。证据：UniXNU-raphael/evidence/native-icon-receiver.json。

# 2026-11-04 当前唯一实验：IconServices接收端补采

候选artifacts/desktop-icon-receiver/20261104T095047Z已通过887记录内核、预链接/载荷、39项恢复QEMU与手机镜像，即将/正在唯一临时启动。仅调整原八槽线程采集优先级，加入实际接收端iconservicesagen和iconservicesd；服务行为与720秒观察/780秒pet、20秒硬件阈值沿用。

此前092714Z已结束，731条独立UFS日志/2107帧，SpringBoard仍等LS数据库；lsd同步等IconServices缓存失效回复，未见桌面。详见下一节。

# 2026-11-04 12分钟实机结果：2107帧，LaunchServices等待IconServices

092714Z已结束，手机已人工恢复Android。独立UFS日志731条/358933字节、dropped0、详细快照完整；实际720101.807ms，2107帧提交/完成，0清黑/拒收/传输错误，watchdog58签到/0失败，无记录的服务退出。现场加载条后黑屏，无桌面。原完整checkpoint失败、xnu_executed=null保留。

SpringBoard仍等LaunchServices数据库；lsd98已到IconServices同步缓存失效请求，iconservicesagen112存在但旧名单未采线程。渲染持续且最终CPU ledger低于限额，不支持此前私有ledger持续卡死的假设。下一步沿原IconServices接收端定位，不原样延长窗口。证据：UniXNU-raphael/evidence/native-extended-service-window.json。

# 2026-11-04 零写实测收益有限，原LS扫描与渲染CPU ledger待区分

085854Z独立UFS日志376条/302872字节、dropped0；1非空帧/0传输错误，watchdog18签到/0失败，无记录的服务退出。现场一帧加载条后黑屏，人工回Android。首次零写只跳过225280字节，Data驻留142708736字节；不能称零写优化解决黑屏。原完整checkpoint失败/null保持。

SpringBoard仍等LaunchServices数据库，lsd99仍在扫描应用/验证签名。最终BackBoard渲染线程在私有CPU ledger等待：实际ledger_ast+444的BL指向thread->t_threadledger，等待持续时间未知，不能按单次快照归因。下一显式候选720秒观察/780秒绝对pet，原20秒硬件保持，补实际CPU ledger计数以区别慢启动与持续限流。证据：UniXNU-raphael/evidence/native-ram-zero.json。

# 2026-11-04 接收端补采完成：LS数据库仍在构建，RAM驻留约149MiB

083013Z独立连续日志373条/303915字节、dropped0；显示clients5/frames0，watchdog18签到/0失败，无记录的BackBoard/SpringBoard退出。lsd101在签名信息/plist解析，容器服务在处理请求，不能归因为固定online-auth死锁。RAM Data驻留156626944字节、reads2158/writes1226/failures0；UFS服务段10–13MiB/s。现场黑屏，人工回Android；原完整checkpoint失败/null保留。证据：UniXNU-raphael/evidence/native-ls-receiver.json。

下一步检查稀疏Data首次零写的实际页分配，尚未证明它是黑屏根因。

# 2026-11-04 首次原用户态451帧：加载条后黑屏，桌面仍待实现

080848Z移除每次UFS只读请求全SMMU扫描后，独立UFS日志388条/309796字节、dropped0，首次451帧校验/提交/完成，0空帧/拒收/传输错误。用户见加载条后黑屏并人工回Android；22次原watchdog签到/0失败，未记录BackBoard退出。小块阶段中位数4.99升至6.97MiB/s，活跃区间约9–10MiB/s。原完整checkpoint仍失败，xnu_executed=null保持。

SpringBoard27已越过显示服务等待，现等LaunchServices重建数据库。lsd98原栈的libmis同步调用，经原共享缓存反汇编定位到com.apple.online-auth-agent.xpc，实际进程148在线；另有容器服务同步等待。下一候选只补这些实际接收端及RAM Data计数，不改认证/服务行为。证据：UniXNU-raphael/evidence/native-first-service-frames.json。

# 2026-11-04 原始watchdog超时描述与UFS请求开销修正

074823Z原运行自动恢复超时，人工回Android后独立日志363条/298301字节、dropped0，详细服务快照完整。原watchdogd52以namespace20/code1终止backboardd57，原描述为ping发送失败、516秒无成功check-in；重启的106进入WindowServer及PUIProgressWindow，lsd正在注册bundle/IconServices；clients5/frames0，无桌面。原失败报告及xnu_executed=null保持。

下一候选仅移除独占UFS读会话中每次请求的全SMMU重扫。单CPU与owner-contract、接管前完整准入、原块认证、串行锁、写入准入及失败收尾保留。生产read提取和原DMA准入ASan/UBSan通过；实机吞吐及服务超时效果待验。

# 2026-11-04 BackBoard原始watchdog退出已捕获

072550Z完整恢复超时，用户人工回Android后独立连续日志读回375条/305557字节，dropped0，13段服务快照完整。BackBoard57和120均为status9、OS_REASON_WATCHDOG(20)/code1/flags5，间隔约59秒；未记录为Jetsam。当前134已到窗口服务器，一线程同步等DataMigration；SpringBoard27已越过主屏信息等待，转为LaunchServices数据库等待。clients6/kicks2/frames0，用户仍见黑屏。独立连续日志和完整checkpoint分别报告，桌面未实现。

下一候选仅补原始reason描述、终止发送者与当前迁移/lsd/watchdog线程，保持服务策略和启动预算。证据：evidence/private/ufs-console-log/20261104T072137Z/20261104T073748Z-manual-recovery/。

# 2026-11-04 恢复主线排查

用户已重新要求继续黑屏排查。显示服务优先采集、原退出原因和VM计数的新候选完成887记录内核、预链接/载荷、恢复QEMU39项和手机镜像，正在唯一临时启动；读取、RAM、显示服务策略及原20/360/420秒预算沿用上一轮。目标是拿到重启后BackBoard的具体等待和退出原因。证据：artifacts/desktop-service-visibility/20261104T072136Z/。

# 2026-11-04 本轮结果与停止状态

045614Z读取合并实机独立日志通过：371条/297594字节、丢字0、13段快照完整；前段约21MiB/s，服务段约5MiB/s，读取失败0。显示clients4/frames0、watchdog11次签到/0失败；SpringBoard仍等待主屏信息，BackBoard已换成PID109，其退出原因未被本轮日志记录，不能归因为内存不足。原完整checkpoint失败及xnu_executed=null保留。

已修复日志文件流式分配碎片及晚PID显示服务漏采：保留原8槽ABI并优先采集显示服务，追加原始退出原因/VM页计数。实际C选择和退出格式、旧捕获/解码回归及最终887记录内核/未定义0通过；新增采集修正未上机，尚不能称已解决黑屏。用户确认手动回Android后，Android/root/无临时FDT已核查。按用户要求停止，无运行中的手机实验、提取器或构建；不自动继续。详情见[本轮日志与修复](SESSION-20261104-UFS-READ-SERVICE.zh-CN.md)。

# 当前新增结果（2026-11-04）

040940Z详细快照已完成原系统UUID匹配符号化：SpringBoard主线程从历史CFPrefs等待推进到BKSDisplayGetMainScreenInfo同步等待；backboardd57正在dyld PrebuiltLoader::applyObjCFixups中的selector修复，尚未到main。本轮独立快照没有首异常，360秒内watchdog签到6次且失败0。证据：evidence/private/ufs-console-log/20261104T040526Z/20261104T042224Z-manual-recovery/services-symbolicated.json。

控制台OS/SystemOS实际isssd=0，固定IOStorageFamily的handleStart及DKIOCISSOLIDSTATE都依赖未发布的Device Characteristics/Medium Type属性。仅补固态属性的新候选完整887记录内核、预链接/载荷、39项恢复QEMU和临时镜像通过；043333Z完整恢复超时，人工回Android后读回325条/288724字节、dropped0、13段快照完整。OS/SystemOS实际isssd1，属性修正生效；显示clients/frames仍0，backboardd仍在dyld selector修复，前段读取约15MiB/s、服务阶段约5MiB/s，读取失败0。首帧未实现。证据：artifacts/desktop-solid-state/20261104T043024Z/candidate-pointers.json。

16KiB连续读取合并正在逐层验证：保留逐4KiB认证，真实UFS模型45项、extent37项及抽取生产read函数10项ASan/UBSan通过；887记录完整内核与预链接/载荷已通过，恢复QEMU进行中。日志分配改为先用Android fallocate预分配再dd原地填充，原连续性与guard门禁不变，新512槽分配成功。手机性能与桌面结果待验。证据：artifacts/ufs-read-batches/20261104T044849Z/，artifacts/desktop-read-batches/20261104T045012Z/。

# 进度记录

## 2026-11-04 离线KeyStore手机验证

032503Z整轮正常checkpoint、nonce、自动Android返回及普通重启/root/临时FDT清理通过。仅在现有易失无口令Data诊断中启用已有状态组件，stage2/opens2/calls4；原MKB_INIT正常DONE，先前FATAL KEYBAG/请求进入恢复模式消失。连续日志79块/48962字节/783行，丢字0、保护块未变。显示clients/frames仍0；首次watchdog方法后提前收尾，下一步只取消该提前停点，保留现有360秒观察/420秒pet合同。证据artifacts/handset-offline-aks/20261104T031813Z/execution-result.json。


## 2026-11-04 原生UFS连续日志实机验收

2026-11-04 实机连续日志通过：030111Z临时启动后人工恢复Android，自动提取191条有效4KiB记录、60664字节/917行、184条进度记录，dropped=0，无损坏尾块，counter递增、两侧保护块未变、新Android boot ID成立。日志完整保存至 SERVICE SNAPSHOT DONE; RETURNING；最后tick1831、root7/init4、syscalls7013、clients/frames0。原FDT完整checkpoint仍未通过，不将独立UFS日志改写为该轮passed。证据：evidence/private/ufs-console-log/20261104T024624Z/20261104T031141Z-automatic-return/report.json。


## 当前状态（2026-11-04，北京时间）

最近正常原生成功为032503Z，离线KeyStore已消除MKB_INIT恢复请求。034350Z取消首方法提前收尾后，完整恢复665.169秒未回连；用户人工恢复Android后，UFS连续日志210块/65721字节、丢字0，保存至服务快照完成。显示clients增至5而frames仍0。原报告保持passed=false、xnu_executed=null；独立日志证明原生执行，但没有详细服务栈或360秒物理到点回传。已增加原观察线程收尾时的UFS服务快照，真实内存/实际C互通、887记录内核、恢复QEMU39项与新镜像通过；040940Z唯一实验完整恢复超时，用户人工恢复Android；042224Z读回322块/286913字节/3454行、230条进度、dropped0、无损坏尾块及保护块变化，13段详细服务快照实机捕获成功。物理观察360046.222ms，watchdog6次check-in/0失败，显示clients/validations/kicks/frames均0，首异常为空。独立UFS快照通过；原完整checkpoint失败、xnu_executed=null保留，桌面未通过。证据artifacts/desktop-offline-window/20261104T033507Z/execution-result.json。

以下为此前接续记录，保留当时状态。


完整对话复核后继续原服务/显示主线。原backboardd没有Aqua会话加载条件；163215Z扫描到68进程/41个xpcproxy；161209Z控制台已有cfprefsd/backboardd。固定250–400秒启动延迟与根因仍未证实，详见 [本轮复核与证据](SERVICE-STARTUP-20261104.zh-CN.md)。

独立marker4“五秒物理观察”通过实际C分支ASan/UBSan、10项解码拒收、887记录完整构建、未定义0、预链接/载荷及39项恢复QEMU。最终候选显式编译成功基线显示源码，当前驱动状态修正保留；原20秒硬件、360秒观察/420秒pet预算不变。构建入口已经实际执行成功，无需用户反复试脚本。精确路径见 `artifacts/service-observation-build/20261103T164426.446041Z/candidate-pointers.json`。

用户确认现场可观察/实体电源恢复后，本轮前置Android/root/FDT/不可变extent检查通过，已执行唯一marker4镜像165957Z（北京时间11月4日00:59:57）。临时启动接受，但664.924秒未建立Android回连，无原生记录，passed=false、xnu_executed=null；用户本轮只报告固件菜单。实验已停止，不原样重跑。171923Z独立人工恢复核查Android/root/新boot ID/临时FDT清理通过，没有找回原生回传；失败报告字节保持原状。最近正常原生成功仍为163215Z；没有新增服务就绪、实际五秒窗口、持续check-in或真实首帧证据。TODO同步Windows副本。


## 2026-11-03 核对（历史）

本次按用户要求同步上游main `3fa5ff5`及独立基带分支 `0ecc91f`，19/20子模块准确冻结；详情见 [GPU与基带同步报告](UPSTREAM-20261103.zh-CN.md)。当前手机后端f0721e9和打包后端c96b299保留，本轮没有新的手机实验或桌面/GPU/基带实机验收。

最新手机170735Z已结束：664.598秒未建立Android回连，`passed=false`、`xnu_executed=null`。用户实体电源恢复后，`evidence/private/android-manual-recovery/20261102T172400Z-display-client-return/report.json` 通过Android完成启动、root、新boot ID及无临时FDT属性核查；不是自动返回。163215Z仍为最近一次正常原生诊断成功：首次原watchdog方法和1次check-in通过，尚无持续心跳/桌面首帧。该次核对时无运行中的手机实验或构建。

后续每完成一个小任务立即更新根 `TODO.md` 并同步 `D:/project/unixnu/todo.md`。当时首次方法后5秒候选仅为待办；本轮实现状态见上方2026-11-04更新。

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

2026-11-02 当前主线：v33/223537Z 已完成匹配 nonce 的原生回传与普通重启/root/临时属性清理，505.165秒观察到 Android；原生检查未通过。服务 opens3/closes2、checkins0，无 externalMethod 入口记录。重新以原程序 BRK 和两级返回地址核对，v32/v33 均停在原 IOPMUPrimary=1 服务查找断言（原 PC0x10000b160），此前“selector0失败”的判断已更正。SpringBoard 首个异常已定位到 FBSDisplayMonitor 初始化。v34 仅在显式有界 watchdog 服务发布诊断用 numeric IOPMUPrimary 注册句柄，并验证原属性匹配；继承 setProperties 仍返回 Unsupported，不承认 PMU 硬件、boot-stage 或前台应用持久化。v34/225501Z 完整构建与原属性匹配 QEMU 通过，临时启动已接受，但664.258秒内未取得 Android USB 或原生回传，xnu_executed=null；用户确认全黑并强制重启；20261102T004239Z独立核查Android/root/新boot ID/临时属性清理通过，非自动返回。v35首次沿用冻结3600poll内核被手机构建预算门禁拒绝、未上机；现同步收短为1200poll并重建，独立ADT采用既有version2的120秒物理观察/180秒绝对pet预算，方法检查与20秒硬件不变；待主机和同轮实机验证，不原样重跑v34。20秒硬件与360秒观察/420秒绝对预算不变。最新正常 checkpoint 仍204217Z；display clients/frames0，桌面和交互未完成。

2026-11-02 最新202022Z手机整轮通过：EL0 BRK分流修正后，原用户异常由原XNU处理，240秒正常checkpoint/有界服务快照成立；PID1 7692次syscall，SpringBoard27主线程为原ipc_mqueue_receive_continue，backboardd未观察到，显示clients/frames仍0。463.808秒自动Android，全屏恢复/正常重启/root/清理通过。下一候选仅追加已驻留且位于已准入RAM的用户栈及实际task缓存slide，定位IPC调用链；不触发缺页或放宽预算。无桌面/交互证据。

2026-11-02 最新手机190907Z整轮成功：原APFS根/SystemOS、原launchd main、可写易失APFS Data同轮成立；原msgbuf有Early boot complete和SpringBoard PID26。Data stage4/status0/readonly0，226项seed，611715字节写入/读回一致；RamBlock130写/零失败/1437696实际驻留。真实512MiB、240052.549ms有界观察、6677次PID1 syscall、53签名对象，UFS3215979520字节/零失败。442.754秒自动Android，完整checkpoint/恢复/正常重启/root/属性清理通过。原OS/SystemOS只读，Data重启丢失；无桌面/交互证明。当前独立handset-display候选构建中；不变更keystore或硬件刷新策略。摘要UniXNU-raphael/evidence/native-ephemeral-data.json。以下按原时间保留历史记录。

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


当前具体阻塞（QEMU 132123Z）：backboardd 的exec线程在原Sandbox→HostSpecialPort25同步RPC等待；原OS plist明确该端口是containermanagerd.upcall，原导入stub也已解析到本候选_host_get_special_port。新exec线程尚在_task_wait_to_return，显示clients/swap仍0。下一项是让原容器管理服务完成初始化并回复该请求，然后验证原用户态的软件渲染与完整帧；不是继续调GOP。手机仍停在有证据的kernel_bootstrap入口，未运行本系统候选。

2026-10-30 显示主线更新：独立 RaphaelDesktopDisplay 已真实编译和预链接，QEMU 123115Z 原 IOMobileGraphicsFamily/IOSurface 加载、metaclass 注册、原 start 与 registerService 已通过；实际 GOP 800×600、32位、stride3200、映射1920000字节，参数仅来自同轮模拟器固件。123229Z 延续用户态300秒，原 start 返回true，clients=0，未捕获 backboardd 首SVC；没有桌面帧，也不能据此断定 backboardd 从未运行。手机仍仅有085718Z kernel_bootstrap首指令证据。本轮没有将系统候选用于手机。下一项实现为用户态单层surface校验、CPU呈现及原swap完成路径；能否由所选用户态持续产出完整桌面仍是关键未知。

2026-10-30：用户授权的一次上游同步已完成，main=f0721e9，仅文档变化。手机085718Z已到 kernel_bootstrap 首指令，自动回Android/root/清理通过；函数体和持续调度仍未手机验证。QEMU091114Z已从原认证双卷执行原版launchd的LC_MAIN首条指令，尚无系统服务或桌面。独立可写Data已在QEMU实际挂载并完成206条初始化、611715字节写入/读回；补齐空目录及原共享Data策略后，QEMU101909Z原launchd已完成early boot，原usermanagerd创建/保存501会话与persona，原SpringBoard首个EL0 SVC通过。尚无SpringBoard main/backboardd/桌面；模拟器结果不升级手机结论。详情见[桌面主线](DESKTOP-MAINLINE.zh-CN.md)与[当前状态](CURRENT.zh-CN.md)。

2026-10-29。手机已通过原 DarwinBoot 的有效内核装载检查：本机 ADT 解析/复制、10 段文件 CRC/零尾及 boot_args 全部通过，到达 BeforeExitBootServices 后约49.7秒自动回Android，正常重启清理通过。374 个输入/原始回传独立复核完成。详见 [NATIVE-LOAD.zh-CN.md](NATIVE-LOAD.zh-CN.md)。这尚未完成真正退出服务，手机 XNU 尚未执行。


## 2026-10-29：手机完整原生内核文件读取通过

2026-10-29。手机主线大载荷阶段 3/6 已通过：独立 56MiB arena、20MiB FAT、原 Mu 分配器完整读取 18,463,480 字节有效 XNU，CRC/窗口恢复通过；高段解码本机 Android 后自动返回并正常重启清理。360 个输入/原镜像/原始回传已独立复核，失败记录保留。详见 [NATIVE-STAGING.zh-CN.md](NATIVE-STAGING.zh-CN.md)。这不是 XNU 执行或 ExitBootServices 成功证据。

下一步本机 ADT 与原 DarwinBoot 的有效加载诊断。上游版本固定，本轮没有 fetch/pull；RAM alias 仍暂停。当前手机正常 Android，没有运行中的实验；原备份未改动。


## 2026-10-29：手机连续分配合同通过

独立窗口策略/HOB/MMU和实际分配实现7265f56：候选258MiB隔离保留，保持原DarwinBoot最小256MiB及Mach-O低21位偏移。手机184704Z/185040Z/185509Z依次通过入口、MMU、DXE；最后真实AllocateAddress从0xc0004000分配256MiB，四阶段内存图均通过，并重新保留整段。最后185721Z正常重启清理、Android/root/原boot哈希和标记清除通过，185948Z逐原始FDT/log/map/产物/源码Git blob复核通过。

自有UEFI QEMU47项通过；功能关闭的默认正常47、BRK44、UDF44回归通过。失败首编/结构检查/旧QEMU profile均保留。额外2MiB是对齐预算；PI TESTED位为显式实验启动策略，不作物理测试或隐藏DMA所有权证据。本轮只操作页面分配元数据，没有有效内核、ExitBootServices或手机XNU。完整源码、构建、产物哈希和执行边界见[KERNEL-WINDOW-UEFI.zh-CN.md](KERNEL-WINDOW-UEFI.zh-CN.md)。

没有同步上游或恢复RAM alias。UART未接线，Windows没有枚举串口；既有FDT声明PSCI smc，但没有执行PSCI重启。下一步有效载荷与staging布局，避免18.5MB内核受当前1MB FAT/16MB heap限制；完整移植仍未完成。

## 2026-10-29：主线推进至BSD和根设备查找入口

暂停扩展RAM alias；其11路径SEC接入WIP保存在stash `3fb57136db5b293859402f36f8bf44a1f9548a46`，已有两阶段QEMU证据保留。只在人类明确要求时同步上游，构建默认使用本地固定依赖。

通用DT平台、独立RaphaelBootCpu、物理/虚拟timer及固定源码pthread已接入。175838Z真实编译887记录，内核18,463,480字节，SHA256 96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722；180002Z Mach-O检查未定义0。180349Z同轮DarwinBoot加载10段原文件字节一致，CPU start真实返回成功、到bsd_init、物理timer/rtclock和EOI各6次且IRQ caller返回，pthread status0/函数表非零；180646Z另到IOFindBSDRoot入口。没有根卷挂载、用户态或手机XNU结论。准确源码、构建命令、冻结archive、失败记录和验证范围见[NATIVE-CPU.zh-CN.md](NATIVE-CPU.zh-CN.md)。

用户提供日志文档后，本轮只读重新采集root cmdline及live FDT：console为ttyMSM0/115200，GENI 0xa90000/0x4000、msm-geni-console/status ok；ttyHS0属于0xc8c000的另一个节点。未验证外部引脚/电气/UEFI UART输出，未打开端口。见[LOG-CAPTURE.zh-CN.md](LOG-CAPTURE.zh-CN.md)。Android/root正常，本轮未重启、写分区或改备份。

下一步是实际DarwinBoot连续窗口分配/保留合同与有日志的手机内核交接，保持原loader最小256MiB和Mach-O低21位偏移。当前UEFI allocator仍16MiB；手机CPU/GIC/PPI18、物理timer和存储待验证。当前状态以CURRENT和本条为准，其下保留历史。

更新：2026-10-28（Asia/Shanghai）。产物目录使用UTC时间；各轮来源与边界以精确构建/运行目录为准。当前简表见 [CURRENT.zh-CN.md](CURRENT.zh-CN.md)，其后保留逐轮历史。

当前阶段：独立SEC/MMU/DXE诊断、继承模式GOP、可见菜单和实体上下/电源三键已实机验证。ICC16项读取、屏蔽IRQ的CNTP到期与寄存器恢复、物理timer PPI18的单比特使能/清除恢复也已在手机通过。本CPU物理timer单次IRQ/EOI及恢复也已实机通过。有界物理TimerArch也已实机验证。完整UniXNURun可见菜单和实体三键现已另行实机通过；DarwinBoot驱动拒绝/卸载生命周期已另行手机验证；完整UEFI架构服务、常驻TimerArch、有效内核交接和手机XNU启动仍未完成。缓存可恢复RAM写入已逐步实测到前64MiB，原字与RO恢复通过；分配器仍未扩展。

首轮实现提交：`bc262ca20f056fabf8d4c04da66e99204d687637`。本轮入口探针与内存合同实现：`6af4f550e8d303c1f63a527cf2971cbbe8265021`。仓库仅在本地，无发布 remote。
详细入口实验见 `ENTRY-PROBE.zh-CN.md`；新诊断固件、失败与恢复见 `SEC-DXE.zh-CN.md`。

## 边界

- 不导入现成 raphael 适配包，不从以前移植继承硬件参数。
- 私有原始数据保存在 evidence/private，固件不提交 Git。
- 实现、主机编译、镜像检查、实机执行分别记录。
- 私有诊断 FD/栈由本机入口和显式预算推导，另经证据门禁；不能将诊断镜像称为可安装的完整 UEFI。启动继承framebuffer已独立验证，完整RAM可用范围和隐藏原厂所有权仍未知。

## 初始核查

- Windows ADB/fastboot 37.0.1，可枚举本机，shell root 为 uid 0。
- WSL Ubuntu-24.04，用户 guo，WSL2；工作目录原本不存在，已全新创建。
- /opt/unixnu-linux 已存在，已通过专用 builtin、ARM64 Mach-O 编译/重定位链接/归档和 LZFSE 往返自检。MIG/IIG 存在，但没有据此宣称完整 XNU 构建通过。
- 上游文档已从本次 UniXNU clone 阅读，包括 porting/index、steps、uefi-firmware、bring-up、records。
- Android 运行时属性报告 locked/green，live FDT 的 chosen 则报告 unlocked/orange。fastboot getvar unlocked 与 oem device-info 均已实测为解锁状态。

## 源码与工具版本

全部为本次重新获取；没有导入现成 raphael UEFI/UniXNU 移植包，也没有使用其他手机的板级配置。Xiaomi 源码是原厂公开硬件参考，非第三方 UEFI 适配包。

| 来源 | 固定提交 |
|---|---|
| UniXNU | `0fc0fc1f9ddd0fbd4787738afef38667df5e0a95` |
| Project-Silicium/Mu-Silicium | `4cba43c90e02cdbefbcd9fcdbda33d2328deaec0` |
| Microsoft mu_basecore | `cfb93724a06ff86ff5ba971413368a7809ee42a5` |
| Xiaomi Kernel / raphael-p-oss | `663db50e195a8a54c8565ac4ab0c6d9ba7d80db0` |
| DarwinBoot（UniXNU 固定子模块） | `3325e352d7df68a9f9ad74832ed94a6acbbd7390` |
| Qualcomm ABL 接口源码镜像（仅参考通用 BootLib） | `fd752ab1b6d81ffaec0a9e86ed2b74e7eac9f4fe` |

详细 URL、已初始化子模块及版本见 `../sources.lock.json`。其他组件没有假定已经获取或可用。
Mu Basecore 使用 UniXNU feed 的精确版本；Mu-Silicium 自己所指的 Basecore 版本不同，完整平台组合尚待验证。
Xiaomi 公开分支是 Android P，手机当前系统是 Android 11、定制内核，不能假定二者完全一致。
ABL 镜像来自 arter97 的源码仓库，仅用于协议理解，不是本机 ABL 的准确源码匹配，也没有使用其板级配置。本机模块哈希和源码接口行号分别记录。

已复用原工具链；只补充缺少的 rg、IASL、NASM、AArch64 交叉工具及 QEMU/AAVMF。版本和 14 项工具文件哈希见 `../toolchain.lock.json`。
UEFI 解包器使用独立 venv：uefi_firmware 1.16、future 1.0.0；wheel SHA-256 见 `../tool-inputs.lock.json`。

## 实现、编译、镜像检查与运行结果

| 项目 | 源码实现 | 主机编译/结构检查 | 模拟器 | 本机执行 |
|---|---|---|---|---|
| 二进制安全采集与来源清单 | 完成 | Python 语法检查、实测哈希一致 | 不适用 | Android 只读采集通过 |
| boot/header、DTBO、FDT 解析 | 完成当前输入范围 | header v1、4096 page、段边界及 FDT token 校验通过 | 不适用 | 原始输入来自本机；未执行解析产物 |
| 最小 SM8150/raphael 观测 DTS | 完成核心资源 fixture | dtc 无告警；RAM、固定保留区、CPU affinity、GIC 地址往返一致 | 未用其启动 | 未验证，不能当固件或 XNU 完整 DTS |
| RaphaelDiag UEFI 应用 | 完成 | raw CLANG/LLD 与标准 EDK II DSC/INF 两条路径通过 | 串口、GOP 信息、内存图、G/M/Q 输入及返回通过 | 尚未在手机执行 |
| ARM64 EntryProbe | 完成，位置无关追加探针及 FDT 回传 | ELF、镜像边界、原内核/ramdisk/DTB 比对通过 | EL1/EL2 各 14 项检查通过 | 非持久 fastboot boot 成功；测试标记匹配，Android/root 正常，boot 哈希未变 |
| RaphaelMemoryContractLib | 完成区间检查库；生产布局禁用 | 9 个主机用例及 EDK II AARCH64 库编译通过 | 在 SEC 路径中执行 | 阶段 2/3/6 已执行几何检查；不代表完整 arena 所有权或 RAM 测试 |
| 新平台 SEC/MMU/诊断 FD | 独立 SEC、异常/返回、日志和诊断 DXE；通用核心复用固定 Basecore | 3 MiB FD，FV/FFS/PE/XIP 检查通过 | 分段路径及完整 DXE/异常返回通过；大型本机 FDT 回放 16 项通过 | 早期两次未回传并恢复；修正后阶段 2/3/6 实机通过，表 CRC/内存分配/日志回传通过 |
| 继承模式GOP/诊断菜单与三键 | 独立GOP/PMIC输入，复用固定UniXNU绘制代码 | 编译、结构、host检查通过 | 合成输入及恢复通过 | 单模式显示、完整可见菜单、上下与电源单次实体映射通过；详见MENU-INPUT |
| 完整UniXNURun与DarwinBoot | 诊断消费端集成，通用源码未修改 | 原loader与协议检查通过 | 完整管理器、拒绝路径与合成Mach-O正向交接通过 | 未执行；合成接收器不是XNU |
| ICC/CNTP/PPI权限 | 独立有界采集/源测试/单bit恢复 | 实际C、指令/来源、结构检查通过 | 分层回归通过 | 读取16项、masked source约10ms到期并恢复、PPI18使能权限/恢复通过；IRQ未验证 |
| XNU | 未选 OS/ABI；未实现本机平台操作 | 未构建 | 未验证 | 未验证 |

诊断应用没有硬编码本机 MMIO、FD、栈或 framebuffer 地址；只观察现有 UEFI 服务，不设置显示模式、不写 framebuffer、不访问块设备。
GOP 信息和菜单测试依赖模拟器提供的驱动，不能替代本机显示和实体按键驱动。

## 已执行命令与证据

以下命令从工作根目录执行；采集命令需要显式传本机序列号，序列号只保存在私有日志，文档不重复。

```sh
python3 scripts/collect.py --serial <local-device-serial>
python3 scripts/host_audit.py
python3 scripts/fastboot_probe.py --serial <local-device-serial>
python3 scripts/inspect_device.py evidence/private/device/20261027T120325Z
python3 scripts/inventory_firmware.py evidence/private/device/20261027T120325Z
python3 scripts/extract_vendor.py evidence/private/device/20261027T120325Z
python3 scripts/parse_vendor_layout.py evidence/private/device/20261027T120325Z
python3 scripts/derive_core_dts.py
python3 scripts/build_diag.py
python3 scripts/build_diag_edk2.py
python3 scripts/run_diag_qemu.py artifacts/edk2-diag/20261027T123734Z/Build/RaphaelDiag/DEBUG_CLANGPDB/AARCH64/RaphaelDiag.efi --graphics
python3 scripts/verify_backup.py
python3 scripts/probe_reference_boot.py --serial <local-device-serial> --collection evidence/private/device/20261027T120325Z
python3 scripts/snapshot_environment.py
python3 scripts/describe_checkpoint.py
python3 scripts/extract_vendor.py evidence/private/device/20261027T120325Z --partition abl
python3 scripts/extract_vendor.py evidence/private/device/20261027T120325Z --partition imagefv
python3 scripts/audit_handoff_sources.py
python3 scripts/validate_entry_probe.py
python3 scripts/build_entry_probe.py --collection evidence/private/device/20261027T120325Z
python3 scripts/run_entry_probe.py --serial <local-device-serial> --build evidence/private/entry-probe-build/20261027T131025Z
python3 scripts/check_memory_plan.py
python3 scripts/build_diag_edk2.py --platform memory-contract
python3 scripts/reboot_after_probe.py --serial <local-device-serial>
```

底层编译完整命令和输出分别保存在 `artifacts/*/<timestamp>/commands.json`、`build.log` 与 `report.json`。
标准 EDK II 使用 `build -p RaphaelPkg/RaphaelDiag.dsc -a AARCH64 -b DEBUG -t CLANGPDB -n 4`，其环境设置由 `scripts/build_diag_edk2.py` 固定。
最初缺少 PE relocation 的 raw 构建检查曾失败，随后通过保留地址型 build tag 修正，重编译及模拟器复验均通过；失败目录仍保留。设备树首次编译的两项告警也已修正，当前输出无告警。

| 产物 | 字节数 | SHA-256 |
|---|---:|---|
| raw 构建 RaphaelDiag.efi | 6144 | `8189f90cb70895481ab41b3c57fbd0a962739bbc0bbd96d5be2bde22329258dc` |
| 标准 EDK II RaphaelDiag.efi | 7168 | `723b2c0b74c72842bff0d503bee4c9788832b3766f09d67606ccddd92bef3947` |
| 观测核心 DTB | 见产物文件 | `bff993712576e8efd7ca130de7cbc060d4fae7dfeb5d80bfdba8a0089715206b` |
| 本机 EntryProbe.bin | 1081344 | `4a06127d6c0d76ce69ca0d7a9390bba95bdf158313e2bf47782e04e75c42c2c8` |
| 私有入口探针 boot.img | 134217728 | `412f868c355d0091caa02a769cc78d58e2c3e2ede7bfb6036008612d99683bcd` |
| EDK II 内存检查库 | 9156 | `00d42550b57942a89c9c89f5a08819ab21d4121ab4f1da9ee3d26a9801594a43` |

表中的 RaphaelDiag.efi 是应用。独立诊断 FD 与含本机私有输入的临时 boot.img 现已另行构建；它们不等于完整 UEFI，哈希和执行结果见 `SEC-DXE.zh-CN.md` 及其证据索引。

机器可读的验证索引见 `validation-checkpoint.json`，其中区分了主机、模拟器和手机证据。

## 手机与备份状态

- 原备份 `D:\PhoneBackups\raphael\2026-10-27` 未删除、未覆盖；71 个校验条目共 1161124515 字节全部匹配。没有恢复测试，也没有补成完整手机备份。
- 本次重新读取 7 个分区，每个均核对字节数、本地哈希和手机源分区前后哈希；清单保存在私有采集目录。
- 私有镜像、XBL 解包产物和日志均被 Git 忽略；只提交经过筛选的技术元数据及哈希。
- fastboot 已实测解锁。参考 Android 镜像的非持久 `fastboot boot` 成功；Android 启动完成、root 正常、boot 分区 SHA-256 与测试前相同。
- 新 EntryProbe 临时镜像也已本机执行，FDT 测试标记匹配；读回 EL1、MMU/缓存关闭、Image=0x80080000、原 FDT=0x85491000 和 19.2 MHz 计时器。随后正常重启回原 Android，确认探针属性消失、root 正常、boot 哈希未变；没有持久安装探针。
- 没有执行 flash、erase、format、分区调整、解锁/重锁或备份恢复。

## 下一步

1. 查清本机 `uefiplat.cfg` 的覆盖机制与 ABL 交接后原厂内存区域的存活期；配置引用的 uefiplatLA.cfg 尚未按 UI 名定位，不能假定默认表就是最终表。
2. 在已通过的最小 SEC/MMU/DXE 基础上完善内存初始化、所有权及架构协议；生产配置仍禁用。保留原内核、FDT、initrd 和原厂运行时/显示区域。
3. 扩大 Image 下载已接受，但尾部零填充并非全 arena 写入/读回或所有权证明。继续维护分段日志、失败和恢复记录。
4. 依据本次提取的 DEPEX 审核显示/电源/按键提供者及运行时依赖，再依次验证日志、显示、菜单、实体按键。
5. 固件阶段有实机证据后再接入 UniXNU、DarwinBoot，随后选择 OS/ABI 并推进 XNU。

## 实机验证

已完成 Android 只读采集、fastboot 状态查询、参考镜像与新入口探针临时启动。扩大 Image 下载已验证；诊断 FD 的两次早期尝试未能回传，不推断执行阶段。阶段 2/3/6 均正常返回 Android/root，boot 哈希未变；最后正常重启审核确认临时标记消失；新分段试验结果见 `SEC-DXE.zh-CN.md`。菜单、实体按键、DarwinBoot 和 XNU 均未实机验证。

## 本轮 SEC/DXE 开发补充

- 重新固定并初始化 Basecore 的 Brotli gitlink `e230f474b87134e8c6c85b630084c612057f253e`，版本锁已刷新。其他共享仓库提交未升级。
- 实现 Diagnostic.dsc/FDF、独立 SEC、内存日志与 DiagnosticReturnDxe；未导入其他手机板级代码。
- 发现并修复解压处理表默认地址、整缓存占位 API、RuntimeDxe CRC/对齐、异常返回重入和 FDT 编辑容量等问题；失败构建保留。
- 大型本机 FDT 回放暴露逐节点父查找的平方级扫描，改为有界祖先栈。对照从 15 秒无结果变为约 0.228 秒完成 16 项检查。不能据此单独断定早期手机黑屏原因。
- 主机、结构、模拟器与手机证据分别保存；源码快照用于新编译，失败及恢复公开元数据保留为独立文件。

## 本轮最终状态

- 固件源码提交：`1009c7b7751b185ca6e5ac822c60711214df4381`。三份成功手机构建的全部 22 项包内输入已逐个与该提交的 Git blob 核对；事后绑定说明见 `../UniXNU-raphael/evidence/sec-dxe-source-binding.json`。
- 本机最小 DXE：stage=6/status=0，ST/BS 签名及 CRC 正确，AllocatePages→写→FreePages 成功，720 字节内存图（15 项）越界数为 0；日志 2535 字节，未丢弃。
- 最后清理：20261027T151911Z 正常重启，Android/root 正常、boot 哈希不变、所有临时标记消失；见 `../UniXNU-raphael/evidence/sec-dxe-cleanup.json`。
- 本轮未执行 flash/erase/format、分区修改或备份恢复；未改动原备份。没有发布 remote，也未上传私有镜像或固件。
- 下一开发点：在稳定日志路径上重新核实启动 framebuffer 和显示依赖，再推进可见输出、菜单与按键。DarwinBoot/XNU 仍未执行。


## 后续：启动显示只读采集

- 独立实现 DisplayProbe.c：动态解析本机FDT的GCC、DISPCC、MDP、GDSCR、SSPP资源，检查总线恒等映射、寄存器窗口与电源/时钟门禁；只提供读取回调，默认禁用。
- 9个固定一手源码文件核对18项SSPP偏移及3项时钟门偏移，记录DisplayDxe的9项DEPEX；未加载原厂闭源模块。另按固定格式表和分量枚举解释像素布局。
- 主机直接执行同一个C采集器：version1为17项，version2为19项，均用模拟MMIO；QEMU两轮均17项，确认不匹配硬件时无采样并正常返回。对应证据和产物哈希详见DISPLAY-PROBE.zh-CN.md。
- 两次临时启动均有nonce和stage2成功回传。version1保守停在GCC时钟；version2按已核实HWCG语义继续，成功采样149项，没有写时钟、电源或像素。
- 启动VIG0观测为1080×2340、stride4320、线性ARGB8888、plane0地址寄存器0x9c000000；活动路由、物理映射与刷新仍未验证，GOP保持禁用。
- 20261027T155236Z正常重启清理通过，Android/root正常、原boot哈希不变、临时显示/SEC标记均消失。原备份未修改。
- 当前源码新增加的固件包输入只重新验证了stage2；原stage3/6历史成功继续保留精确来源，未据此宣称新版本完整DXE或显示成功。
- 下一步：只读核对CTL/mixer/interface/pingpong连接、混合/alpha、命令模式刷新与SMMU/CPU映射，再进行可恢复的最小显示输出。


本轮 version 2 固件包源码提交：`ac827ab6685947214128a80db05a8d16828815a0`。对该手机构建的 24 项包内源码逐一读取 Git blob 比较 SHA-256，全部匹配；QEMU 输入亦完全一致。此为构建后的哈希绑定，不能将 version 1 或此前 stage 3/6 自动绑定到这个版本。详细记录见 `sec-display-source-binding.json`。


## 2026-10-28：显示路由只读采集 version 3

- 固定一手源码核实 SM8150 使用 interface TE，避免误用旧 PP TE 刷新寄存器。独立扩展 C 采集器，动态解析全部窗口和 blend offset，并在首次读取前检查重叠/容量；major 5 之外停止。
- 主机 44 项实际 C 模拟 MMIO 测试、QEMU 17 项及 FD 结构检查通过；手机 `20261027T161630Z` nonce 匹配、stage2/status0、507 项读取顺序完整。新输入未重测 stage3/6。
- 寄存器配置表明 VIG0→LM0→PP0→DSI interface1、CTL0 command mode，自动刷新 enable=1/frame_count=1。blend3 op=0x400、const=0x00ff0000，按参考语义为不依赖像素 alpha 的不透明前景。这是配置一致性，尚未证明像素读取和面板更新。
- 本机 FDT 的 SMMU 参数核实为 SID=0x800/mask=0x420；涉及 hf0/hf1 TBU，不能将 mask 当 context-bank。SMMU/页表/CPU映射及存活期仍未知，没有写像素。
- `20261027T161823Z` 正常重启，Android/root/原 boot 哈希正常，全部临时标记消失。v2 的六份公开元数据另存 `*-v2.json`，旧私有构建和独立尝试均保留。
- FD/镜像哈希、命令、逐层结果及下一步见 DISPLAY-ROUTE.zh-CN.md 和 boot-display-route-observation.json。


本轮固件包与主机解码源码提交：`facee82465a67cad6032f23377f5b9e2e94ef62a`。手机与 QEMU 的全部 24 项包内输入逐项匹配 Git blob，证据快照哈希一致；主机分析脚本另有绑定记录。见 `sec-display-source-binding.json` 和 `sec-display-analysis-binding.json`。


## 2026-10-28：SMMU wire v4 开发

独立实现只读 SMMU 采集、来源审计与主机独立解码；50项C模拟MMIO、44项显示回归和17项QEMU通过。新上下文37280字节，scratch移至最后4KiB；stage3/6需重测。实机验证随后单独记录，见 SMMU-PROBE.zh-CN.md。

实机621项回传、stage2/status0，SMR3/CB2配置与早期旁路一致。未读像素/页表，未写MMIO；源码绑定9d2fb86365b30f68375fa5d837ba47209bea8444，共25项包内输入。正常重启清理通过。下一步只读CPU候选缓冲区和刷新活动。


## 2026-10-28：只读CPU像素/计数诊断开发

PixelProbe.c独立实现带门禁的64×64像素抽样和32轮interface计数采集；22项C模拟测试与18项QEMU检查通过。原始像素保持私有，尚未写像素或验证可见输出；见PIXEL-PROBE.zh-CN.md。

只读像素实机已通过：nonce、stage2/status0、4096样本及32轮计数完整，Android/root/原boot正常；正常重启清理通过。原始像素私有，网格RGB均黑、TE行计数移动，但frame/status均0，尚无可见显示证明。


## 2026-10-28：可恢复像素写入开发

新增独立PixelWrite.c，现场只读门禁通过后，保存左上256×128全部原值、写白框RGB、逐字验证、保持10秒、恢复并逐字复验；14项主机模拟通过。实机/可见性单独记录，见PIXEL-WRITE.zh-CN.md。

可恢复像素写入两次实机通过，重复实验用户明确观察到色块；32768像素全部写验恢复、nonce/stage2/Android/root/原boot审核通过，正常重启清理完成。源码绑定e8c73694e86b6839ca36ee68775c95aa63a18b0d。此为SEC可见输出，GOP/菜单/按键仍待验证。

## 2026-10-28：实验性GOP开发

新增动态framebuffer合同、NC映射/保留HOB、单模式GOP和可恢复DXE图案诊断；38项ASan/UBSan实际C测试、21项路由门禁测试和20项stage2 QEMU通过。仅限本次继承模式，尚不宣称GOP实机成功，见GOP.zh-CN.md。

## 2026-10-28：GOP实机验证

实验性GOP同源码stage2/3/6实机通过；stage6四种Blt、32768像素写验恢复无差异，用户明确看到色块。正常重启清理、Android/root/原boot哈希均通过。39项包内输入绑定38fe398612c029f1b032c9f27b89b082943354ba，详见GOP.zh-CN.md。继续菜单和PM8150按键审计，DarwinBoot/XNU尚未执行。

## 2026-10-28：按键仲裁器只读探针开发

独立实现InputProbe.c、来源审计和Python wire复核；40项实际C/UBSan与guard检查通过。默认关闭，仅version/APID/owner配置读取，无PMIC事务或MMIO写。实机单独记录，见INPUT-PROBE.zh-CN.md。

只读仲裁器实机已通过858项读取，Android/root/boot哈希和正常重启清理正常。继续独立RaphaelKeysLib的6笔有界PMIC读取；39项UBSan主机测试通过，硬件事务另记。见KEY-READ.zh-CN.md。


## 2026-10-28：输入协议与通用菜单诊断开发

六笔有界PMIC读取实机成功并正常重启清理。新增PmicInputDxe，实际C/EFI回调26项ASan/UBSan通过；独立诊断控制器链接未修改的固定UniXNU绘制源码。横屏与1080×2340竖屏QEMU合成按键和全屏恢复通过；24项SEC QEMU通过。实机协议/菜单仍待按阶段验证，完整UniXNURun和TimerArch尚未实现。见MENU-INPUT.zh-CN.md。

菜单版同源码stage2/3/6已在手机通过，stage6输入协议安装、8000次采样错误0、40秒全屏绘制恢复差异0。无实体按键事件且尚无菜单人工观察，两者不记成功。正常Android重启清理、root和原boot哈希通过。51+47输入逐文件绑定b2e774c，见MENU-INPUT.zh-CN.md和sec-menu-source-binding.json。继续只读FAT及配置/EFI交接验证；周期定时器、DarwinBoot和XNU尚未执行。


## 2026-10-28：只读负载与完整管理器自动验证

用户已要求菜单实体观察推迟到醒来后，手机保持Android，未进行新的实机重启。新增独立AAVMF测试：实际未修改RAM-disk入口、FAT只读文件系统、EFI子程序参数与父句柄握手、完整UniXNURun倒计时，17项通过且已检查竖屏截图。
另将合成1MiB FAT嵌入自有保留FD，默认禁用且只在QEMU构建启用；SEC另建4KiB FDT/HOB，Android initrd不变。stage6正常36项、BRK返回29项通过；负载CRC不变、默认timeout0完整管理器退出。修改后再次以同源码重跑各阶段并归档；手机未执行本功能。详见PAYLOAD.zh-CN.md。


负载阶段归档：全部54项板级与47项通用输入逐Git blob绑定`6f6d63b125463d4fc009c128a6f00ed6c7d03f32`。最终QEMU stage2/3各25/27项，stage6正常36项及BRK29项；默认关闭负载的全菜单回归正常30项/BRK27项。独立wire检查18项通过。17项AAVMF正向测试亦绑定同一版本，详见payload-sec-source-binding.json、payload-fixture-qemu.json和payload-wire-host.json。人工菜单与实体按键观察经用户要求延期；2026-10-28续接查询Android sys.boot_completed=1，无进行中的手机实验。


## 2026-10-28：DarwinBoot编译、协议与拒绝路径

未修改固定DarwinBoot，新增消费端测试DSC。独立AAVMF实测38项通过，经实际UniXNU配置与启动入口调用后，损坏Mach-O拒绝、固件服务保留；重复加载、卸载/重载及参数边界亦通过。首次头文件声明不足的失败构建保留，已修正测试引用。

自有SEC/DXE另加默认关闭的诊断：临时内存日志SimpleTextOut、手动加载FV中的原DarwinBoot、只读FAT损坏输入、v2调用与清理恢复。首轮QEMU正常43项/BRK30项通过；无有效内核、无ExitBootServices、无XNU、无手机运行。全部源码版本及逐文件绑定在最终阶段归档后补充，见DARWINBOOT.zh-CN.md。实体菜单和按键继续延期，手机留在Android。


DarwinBoot最终归档：固件输入56项、UniXNU47项、DarwinBoot9项全部逐Git blob绑定`48c015077e113aeb2278cb75bf9d5bb06a4f6db1`。阶段2/3分别26/28项，stage6正常43/BRK30项；关闭Darwin的只读负载回归37/30项，全部默认关闭回归31/28项。独立wire复核24项通过；AAVMF38项绑定测试源码`33fdad0`。构建器曾在关闭Darwin时仍加入不存在的快照路径，回归及时发现并已修正；失败目录20261027T202816.569252Z保留。源绑定、命令、产物哈希见darwin-sec-source-binding.json和darwin-fixture-qemu.json。手机未重启；菜单/实体键仍待人工观察。


## 2026-10-28：中断资源重新核实

Android下新FDT/中断行只读采集完成，未重启。沿继承关系解析timer→PDC→GIC，固定一手源码确认转发语义；四路INTID17/18/19/16，当前Android使用virtual19（Linux逻辑IRQ4）。31项资源图和损坏输入检查通过；保留0xf08原始标志，不套用其他板型IRQ。观察用DTS明确其PDC归一化投影并新增合同门禁，dtc与资源回读通过。详见INTERRUPTS.zh-CN.md。手机UEFI周期定时器尚未实现/验证。


## 2026-10-28：自有QEMU架构与真实定时中断

默认关闭并禁止手机的CPU/GICv3/CNTP TimerArch诊断完成。每轮QEMU生成并压紧自己的DTB，SEC独立资源校验/映射/HOB，实际固定通用驱动派发；相对event、周期回调、取消稳定和完整UniXNURun两秒倒计时通过。日志预算调整后全量记录无丢弃，Darwin拒绝路径同时通过。

源码86f1b61下stage2/3/6分别29/31/52项，架构+payload独立回归46项，架构关闭Darwin正常45/BRK32，全默认正常33/BRK30；53项独立wire/资源检查通过。59+47+9源码输入和构建/接收/解析脚本逐Git blob绑定，产物哈希与命令见QEMU-ARCH.zh-CN.md和qemu-arch-sec-source-binding.json。GIC整体状态未恢复，该模式不用于手机；未执行有效内核、ExitBootServices或XNU。菜单/实体键继续等用户醒来后观察，手机本轮未重启。


## 2026-10-28：正向DarwinBoot诊断交接与Apple ABI核对

固定原DarwinBoot在AAVMF/QEMU经真实UniXNUConfigLoad→UniXNUBootEntry→Loader.Boot，接受格式正确的合成Mach-O/ADT，成功ExitBootServices后进入独立接收器。接收器实际验证EL1、MMU/cache关闭、DAIF、boot_args、动态分配/重定位、ADT和RAMDisk；无initrd22项、原始initrd25项、稀疏展开25项全部通过，ESP只读且前后哈希一致。全部输入/runner绑定c780374，命令和产物哈希见HANDOFF.zh-CN.md及handoff-fixture-qemu.json。

新取Apple官方xnu-10002.1.13，tag对象a653a70d…解析到commit1031c584…；追加sources.lock.json。主机/AArch64编译未经改写的原声明与DarwinBoot结构，13字段+大小/对齐15项匹配，见boot-args-abi.json。没有编译或执行XNU，没有选定手机OS profile。手机诊断arena16MiB不能满足原loader最小256MiB窗口，不能照搬模拟器交接。手机仍Android启动完成，本轮未重启，人工菜单/实体键继续延期。


最终只读复核：Android启动完成、root uid0，boot分区SHA-256仍为cbd91d814396ea0aab1cbca25d4f4f904805c69e4bb38b5a35a51b98858b96ec。此轮没有重启手机或执行flash/erase/format，原备份未修改；上游通用源码及新Apple参考源码tracked diff均为空。自动结果与待人工观察边界见overnight-automatic-status.json。


## 2026-10-28：人工菜单测试开始

用户醒来开始实体操作。新增严格历史复测模式，原b2e774c stage6镜像的98项输入逐Git blob/构建快照核验，FD/镜像/QEMU一致；8种损坏描述均拒绝。没有编译新手机固件，GIC开发文件未接入手机镜像。第一轮20261027T214935Z：用户确认只按音量下三次，与设备down=3/up=0/enter=0一致；40秒超时、2527200像素恢复差异0，Android/root/boot哈希通过。正常重启20261027T215236Z清理通过。上键和电源留待第二轮，不能把第一轮“无异常”泛化为三键全部成功。见HISTORICAL-RETEST.zh-CN.md。


## 2026-10-28：人工菜单与实体三键验证

重用已验证的 b2e774c 历史镜像，未编译新手机固件；历史输入与快照核验方式见 HISTORICAL-RETEST.zh-CN.md。两轮分别保存启动前后 FDT、不可覆盖 attempt 与用户观察。

- 20261027T214935Z：用户仅短按音量下三次，回传 down=3/up=0/enter=0；40秒超时返回。该轮不验证另两键。
- 20261027T215414Z：按音量上一次、音量下一次、电源一次。用户确认三步均符合预期（上至 Boot information、下回 Return to Android、电源提前返回）；设备独立回传 up/down/enter=1/1/1，1422次采样、错误0，约7.1058秒由 Enter 选择返回。全屏2527200像素恢复、差异0。
- 两轮 Android/root/boot 分区 SHA-256 均通过；各自正常重启清理临时 FDT 属性通过（215236Z、215618Z）。没有 flash/erase/format，原备份未修改。

该证据验证本轮继承显示模式的完整可见诊断菜单、上下选择与电源确认。主机 wire 解码器仍保留 human_visibility_verified/physical_keys_verified=false，因为解码器单独不能验证人工事实；人机结合的成功结果见 manual-menu-observation-20261027T215414Z.json。没有验证长按重复、组合键、触摸、手机 TimerArch、完整 UniXNURun 或 DarwinBoot/XNU。


## 2026-10-28：GIC只读采集开发与主机验证

默认关闭、限stage2的新采集器完成55项实际C/UBSan/guard/独立wire检查，21项架构常量及固定一手源码语义核验通过。自有SEC/QEMU真实GICv3读取回传31项通过；默认关闭stage6正常34/BRK31、既有IRQ+payload+Darwin回归53项通过。61板级+47UniXNU输入快照独立构建。手机镜像220720Z已编译且结构检查通过，尚未执行。详见GIC-READONLY.zh-CN.md，实机及源码绑定随后独立记录。


GIC只读实机220921Z已通过：67次读取、8帧与同轮CPU affinity完全一致，MPIDR0x81000000动态匹配frame0/0x17a60000。Android/root/原boot哈希通过，221111Z正常重启清理成功。61+47固件输入与8项验证脚本逐Git blob绑定bc38c45，三份QEMU回归同源码。全部原始只读值和边界见GIC-READONLY.zh-CN.md；没有启用IRQ、访问ICC/IAR或验证状态恢复。下一步先核实CPU接口访问状态。


## 2026-10-28：ICC只读探针开发与回归

默认关闭的16项CPU/ICC/timer读取及精确同步异常恢复已实现；59项实际C/UBSan/canary/wire测试通过。正常读取与受控UDF恢复QEMU各37项，默认stage6正常35/BRK32/白名单外UDF32项，完整IRQ+payload+Darwin回归54项通过。16条编译后MRS与独立GNU assembler、其中12条与固定MiCode编码匹配。手机223612Z镜像仅编译/结构检查通过，尚未执行；真实EC0x18 trap仍未实测。失败构建及修复、哈希与命令见ICC-READONLY.zh-CN.md。


## 实机结果：20261027T224342Z

同轮GIC完整67次读取及ICC全部16项完成，nonce/stage2/status0与独立解码通过；无读取trap。CurrentEL=4、DAIF=0x3c0、MPIDR=0x81000000；SRE=1、CTLR=0x8440、PMR=0xf0、BPR1=3、IGRPEN1=0、RPR=0xff、HPPIR1=1023。CNTP_CTL=0、CNTP_CVAL=0；CNTV_CTL=5、CNTV_CVAL=233262653；CNTKCTL=0、CNTFRQ=19200000。CNTV_CTL的ISTATUS/ENABLE均为1，不能认为所有timer已停用，后续不得无依据改动虚拟timer。

Android/root/原boot哈希通过，224519Z正常重启临时属性清理通过。66板级+47UniXNU源码、四份QEMU回归及8项验证脚本逐Git blob/快照绑定bd3dcdf5c54381bfe819e2079afcca112bb839c7。见icc-probe-source-binding.json、boot-icc-readonly-observation.json。

Arm规范8.11.8/8.11.9指出DS=0时Non-secure读取IGROUPR/IGRPMODR为RAZ/WI。因此此前group读取0不能证明PPI为Secure组，也不能据此跳过权限验证。手机真正IRQ、GIC写权限、定时器接管/恢复仍未验证；下一步先在DAIF全mask下只验证已关闭的CNTP可恢复寄存器和到期状态，不开启IRQ、不触碰仍有状态的CNTV。


## 2026-10-28：保持IRQ屏蔽的CNTP源实验开发

独立物理timer源/恢复实现完成，82项实际C/UBSan/canary/wire检查通过。正常QEMU44项和CVAL修改后模拟写失败恢复43项通过；独立接收器MRS核对原物理timer可写位/CVAL及未改动CNTV。默认36/33/33及完整IRQ+payload+Darwin55项通过，3条实际counter/CNTP指令和精确恢复表已审计。225842Z手机镜像仅编译/结构检查通过，实机另记；见TIMER-SOURCE.zh-CN.md。


## 实机结果：20261027T230159Z

nonce/stage2/status0与独立wire全部通过。频率19200000，原CTL/CVAL均0；counter起点703005354，设计deadline703197354，观察到CTL=7、CVAL匹配、终点703197372，4423次采样，经过192018 ticks（约10.00094ms）。5次写入后CTL/CVAL都恢复0，无trap。只证明屏蔽状态下的物理source到期与两寄存器可写位恢复；没有IRQ、GIC或IAR访问。CNTV没有写入。

Android/root/原boot哈希通过；230328Z正常重启后临时属性消失。70板级+47UniXNU源码、四份QEMU回归、9项构建/接收/审计脚本逐Git blob/快照绑定2fb02f67f8e52751b80181d94247b9edf000f3c9。见timer-source-source-binding.json和boot-timer-source-observation.json。下一步在IRQ仍mask、distributor组和CPU接口均关闭时，仅测试动态本CPU的物理timer PPI单比特使能/清除权限；保持原FDT flag，不改group、priority或触发配置。


## 2026-10-28：动态本CPU单PPI权限实验开发

独立FDT继承链/本CPU单bit使能与恢复代码完成，94项实际C/FDT/UBSan/canary/wire通过；QEMU43项、默认37/34/34、完整架构56、CNTP source回归45项通过。写入仅两个SGI页write-one偏移，IRQ/分发器组保持关闭；GICR RWP按Arm规范bit3，未照搬旧厂商helper的bit31。SEC内160字节materialized结果已逐镜像核对，不扩context或FD。232317Z手机镜像仅编译/结构检查通过，实机另记；见PPI-ENABLE.zh-CN.md。


## 实机结果：20261027T232552Z

nonce/stage2/status0及独立wire通过。按本机FDT得到INTID18、flag0xf08；按同轮affinity动态选中SGI_base0x17a70000。enabled原0→0x40000→0，共2次write-one写入、11次读取；RWP查询1次。GICD_CTLR保持0x10；pending前后均0x10080000、active前后0，目标bit原无pending/active且未变化。status6、RestoreOk1，证明本次Non-secure视图的PPI18使能可写并恢复。没有启用分发器、CPU接口或IRQ，没有IAR确认。

Android/root/原boot哈希通过，232753Z正常重启清理通过。72板级+47UniXNU输入、四份QEMU回归和9项脚本逐Git blob/快照绑定5b02d17984dd287e9c1745a477e8ab4a1d89a6de。见ppi-probe-source-binding.json和boot-ppi-enable-observation.json。没有flash/erase/format或备份修改。

下一步先读取所有Non-secure SPI/各CPU SGI-PPI的enable以及LPI门禁。仅本CPU目标PPI可写不足以授权把分发器组全局打开；必须先确认不会使其他已使能中断获得投递机会，再设计有界、可恢复的物理timer路由实验。

## GIC使能视图实现与主机门禁（2026-10-28）

两遍Non-secure SPI/全部redistributor SGI/PPI/LPI只读采集已实现，主机65项、QEMU43项及默认/完整架构回归通过，手机候选构建和结构通过，尚未执行。硬件是否全零仍未知。详见GIC-ENABLE-MAP.zh-CN.md；零读值不得推广为Secure状态或完整所有权。

## 实机使能视图：20261027T235238Z

完整93次读取，29个SPI enable字、8帧local enable与RD_CTLR两遍均零，ChangedWords0、D_CTLR前后0x10，status3/AllObservedDisabled1。同轮nonce/stage2/status0、Android/root/原boot哈希通过；235405Z正常重启清理通过。74板级+47UniXNU输入与Git f5fc35959a2160bb1ce4aa67ca25e116fa540089及私有快照逐项绑定。见gic-enable-map-source-binding.json和boot-gic-enable-map-observation.json。只证明本次非原子Non-secure视图，不证明Secure状态、完整GIC所有权或IRQ投递。未flash/erase/format，未改动原备份。

## timer路由实现与主机门禁（2026-10-28）

屏蔽CPU IRQ的CNTP→本CPU PPI→HPPIR实验已实现，实际C/FDT/UBSan101项、QEMU正向49及GIC写入后UDF恢复49项通过，默认/完整架构回归通过。仅有限组使能和目标PPI写入，异常或超时均尝试完整恢复。手机候选001327Z编译/结构通过，尚未执行。详见TIMER-ROUTE.zh-CN.md；不把主机或模拟器成功当手机IRQ事实。

## 实机路由结果：20261028T001611Z

status6/RestoreOk1。源频率19200000Hz，counter从1080544972至1080737007，deadline1080736972；192035ticks约10.00182ms，2562次查询，HPPIR1023→18→1023。pending0x10080000→0x100c0000→0x10080000；enable0→0x40000→0；active前后0。D_CTLR0x10→0x12→0x10；IGRPEN1为0→1→0；CNTP原/恢复CTL/CVAL全0；DAIF前后0x3c0，4次MMIO写、7次系统寄存器写，无trap。

同轮enable map仍两遍全零，nonce/stage2/status0、Android/root/原boot哈希通过；001818Z正常重启清理通过。78板级+47UniXNU输入和12项脚本逐Git blob及构建快照绑定6bda838faefcaa6517eba63d559a85acbe0513d1。见timer-route-source-binding.json和boot-timer-route-observation.json。CPU IRQ仍保持屏蔽，未IAR/EOI，未执行handler或TimerArch；完整GIC/RAM所有权仍未证明。未flash/erase/format，未修改原备份。

## 单次IRQ实现与主机门禁（2026-10-28）

独立有界EL1 SPx IRQ leaf已实现；只有既有门禁及HPPIR/pending确认后才解除IRQ屏蔽，处理一次后屏蔽返回并完整恢复。实际C路由105项、wire32项/C布局25断言、QEMU真实IRQ54项及默认/完整架构回归通过。手机候选003329Z编译/结构通过，尚未执行；见TIMER-IRQ.zh-CN.md。不得将其称为手机TimerArch或完整平台完成。

## 实机单次IRQ结果：20261028T003635Z

IRQ status5，目标与IAR实际ID均18，Entries1/EOI1，source mask写后读回通过，无spurious或未知ID。窗口counter1074224279，IRQ counter1074224333，结束1074224393；54ticks约2.8125微秒内确认已pending的timer。IRQ ELR0x836bf1a0（在本轮链接窗口内），实际SPSR0x345，其DAIF部分0x340；窗口前后DAIF均0x3c0。SPx=1，handler栈比窗口SP低80字节且位于诊断栈内，活动指针清理。

随后原路由完整恢复：active0、pending0x10080000、HPPIR1023、D_CTLR0x10、IGRPEN1/CNTP_CTL/CVAL均0。nonce/stage2/status0、Android/root/原boot哈希通过；003910Z正常重启清理通过。80板级+47UniXNU输入和15项脚本逐Git blob/构建快照绑定42246fbbed0058b3f9ffcd74ee9c8a536a979a4c。见timer-irq-source-binding.json及boot-timer-irq-observation.json。单次IRQ不是持续TimerArch或完整UEFI；没有flash/erase/format或备份修改。


## 物理PPI专用TimerArch实现（2026-10-28）

独立PhysicalTimerDxe与device映射/HOB、自动relative/periodic/cancel/停表稳定测试已实现；主机63项证据/58项C断言、分阶段QEMU55/55/64项及默认/异常/原通用路径回归通过。修复自有DebugLib未遵循DebugCode掩码的问题。手机候选stage2已编译/结构通过，尚未实机执行。来源、失败和限制见PHYSICAL-TIMER.zh-CN.md；不能把模拟器服务当手机TimerArch或完整移植。


## 手机有界TimerArch通过（2026-10-28）

33481c8同源码三阶段手机实测通过：011425Z SEC2、011849Z MMU3、012324Z DXE6。PPI18持续IRQ/EOI各61，notify61；relative约100.001823ms、periodic5次约104.998698ms，取消后100ms回调稳定、停表后另100ms IRQ不变。GIC/CNTP/DAIF及虚拟timer完整恢复，Android/root/原boot哈希正常；012639Z正常重启临时属性清除。源/构建/镜像/实机各自绑定，464字节SEC数据已确认物化。详见PHYSICAL-TIMER.zh-CN.md。目标仍未完成，下一步手机完整UniXNURun与内核RAM窗口。


## 手机完整管理器诊断实现（2026-10-28）

将只读RAM FAT/配置接入已验证的物理TimerArch，实际调用固定UniXNURun并记录独立倒计时wire。无GOP/OS加载，未访问手机存储。18项manager主机检查/8项C断言、分阶段QEMU56/58/72项与默认/异常/通用架构回归通过。路由采样竞争已修复并新增两项真实C模型复现，合计107项。手机三阶段待验证，详见MANAGER.zh-CN.md。


## 手机完整UniXNURun无GOP诊断通过（2026-10-28）

0a91c56同源码三阶段实机通过：20261028T015002Z stage2, 20261028T015637Z stage3, 20261028T020020Z stage6。真实管理器两秒倒计时实测2.00377859375秒；只读RAM FAT、配置来源和前后CRC通过，IRQ/EOI各262，无异常。随后事件测试和GIC/CNTP/DAIF恢复通过，CNTV未变化。020320Z正常重启清理、Android/root/原boot哈希通过。记录器独立重核84+47源码输入、原wire、各阶段绑定和不可变attempt。完整管理器执行标记为真，可见UI、DarwinBoot/XNU仍为假。详见MANAGER.zh-CN.md。


## 内核连续RAM候选核查（2026-10-28）

新增只读内存采集器，021216Z重采FDT、iomem和memblock内存/保留表。Linux两份RAM视图合并后一致；MMFR0/EFI表不可用。固定原DarwinBoot要求256MiB及2MiB对齐。自有区间审计交集描述并排除全部本轮已知保留范围，推导三组候选；2104项主机检查含256组独立离散集合模型通过。没有RAM读写探针或分配器扩展，所有权与入口PA能力仍未知。来源/命令/边界见KERNEL-MEMORY.zh-CN.md、kernel-window-audit.json及host报告。


## 入口RAM只读实验实现（2026-10-28）

默认关闭、stage2的256点稀疏读取和95项来源保护策略已实现。73项实际C/libfdt/UBSan/canary/wire通过；1GiB QEMU正常41项、实际load位置UDF fatal返回41项通过。默认43/40/40及物理TimerArch+完整管理器73项回归通过。最终链接机器码候选指针仅load、208字节SEC物化存储已审计。030317Z手机候选仅编译/结构通过，待源码绑定和实机；不是分配器扩展或所有权证明。见RAM-READ.zh-CN.md。


## 手机RAM稀疏读取通过（2026-10-28）

258e353同源码030742Z手机stage2/status0，256次读取全部完成；0xc0000000..0xd0000000、2MiB首尾各8字节、28854ticks/1.5028125ms，MMFR0与固定库均为40位PA。95+4项保护完整检查，241个非零样本只存摘要。030956Z正常重启清理、Android/root/原boot哈希通过。独立记录器核对87+47输入、Git/构建快照、wire/FDT/log及不可变attempt。候选仍未写入或注册UEFI内存，见RAM-READ.zh-CN.md及boot-ram-read-observation.json。


## 完整管理器显示整合实现（2026-10-28）

固定完整UniXNURun接入自有全屏可恢复事务、GOP、输入和物理TimerArch，默认关闭。主机实际C/ASan/UBSan31、wire25；AAVMF完整UI两轮23项和截图检查通过；自有SEC2/MMU3/DXE6为59/61/75项，明确缺显示模型，不当手机图形证据。默认44/41/41、无GOP管理器74、route故障恢复54项通过。035022Z手机stage2仅编译/结构通过，尚未实机。失败构建与门禁修复、产物哈希见MANAGER-UI.zh-CN.md。


## 手机完整管理器显示通过（2026-10-28）

50956e2同源码035345Z/035732Z/040314Z三阶段通过。完整UniXNURun2.131348698秒，真实graphics1080x2340/input yes，全屏2527200像素变化/恢复且差异0。用户确认看到菜单；输入200次采样错误0，无实体键。IRQ/EOI/notify355，TimerArch事件测试与GIC/CNTP/DAIF恢复通过，CNTV未改；040520Z正常重启清理、Android/root/原boot哈希通过。137输入、构建、wire/FDT/log/不可变attempt、人工记录独立绑定。下一步完整管理器实体按键和RAM窗口，DarwinBoot/XNU仍未手机执行。详见MANAGER-UI.zh-CN.md。


## 完整管理器实体键测试开发（2026-10-28）

新默认关闭的有界输入包装器和两项安全退出配置已实现；24项实际C/ASan/UBSan、29项独立解码交叉检查、36项AAVMF及SEC2/MMU3/DXE6的59/61/75项通过。六秒自动Enter独立计数，不能作为实体电源。新模式实机尚未执行，详见MANAGER-KEYS.zh-CN.md。


## 完整管理器实体三键实机通过（2026-10-28）

实现513c3b8的stage2/3/6分别044424Z/044856Z/050556Z通过，139项板级与上游输入逐Git/快照匹配。045604Z首轮只有上下键、六秒自动退出，未误算实体电源；同镜像050556Z复测实体up/down/enter=1/1/1、automatic0、errors0，用户确认都正常。完整管理器4.18086515625秒、全屏2527200像素恢复差异0、物理IRQ/EOI/notify560且完整恢复；050950Z正常重启清理通过，Android/root/原boot哈希正常。详见MANAGER-KEYS.zh-CN.md。下一步原生XNU构建与可恢复内存交接。


## 可恢复RAM单页路径与原生构建输入（2026-10-28）

独立RAM事务库、SEC备份/恢复、默认关闭页数PCD、独立wire和来源门禁完成。43组实际C/ASan/UBSan、6154故障位置、25wire反例通过；QEMU正常46/部分写后UDF48/读取UDF通过，默认45/42/42回归通过。061319Z手机候选编译/结构/预检通过，尚未执行。BSS拒绝与修复均保留，详见RAM-WRITE.zh-CN.md。

原生board/soc/defconfig和真实工具链测试已建立。首次构建在固定OS boot-progress补丁依赖其他板PMGR上下文处失败；明确禁用并在本机OS选择series省略可选补丁，未引入其他板代码。之后Apple公开头网络失败，新增校验Git blob的本地下载缓存，通用代码未改；正在继续实际编译。源码/配置、主机结果、产物和实机仍分开记录。


## 手机单页RAM实测通过（2026-10-28）

062031Z同源码1b9a735的143项输入绑定通过，0xc0000000第一页4096字节两轮图案/原内容恢复实测零差异，12.2561458333ms。062401Z正常重启清理、Android/root/原boot哈希正常。独立记录器核对immutable attempt、wire/FDT/log、来源与cleanup，boot-ram-write-observation-pages1.json已生成。未新增分配器或启动DarwinBoot/XNU。八页QEMU通过、手机候选062626Z仅构建/结构通过。原生构建的公开头已按Git blob校验缓存，通用runtime源码传输失败被完整记录，正在按固定提交只取编译所需子树。


## 前八页实机与256页候选（2026-10-28）

八页版构建062626Z、实机063206Z：0xc0000000起连续32768字节，completed/restored均8，读16384次、写12288次，图案与恢复差异均0，Dirty/BackupWords均0，耗时98.4048958333ms。143项输入绑定9ce0974；063549Z正常重启清理、Android/root/原boot哈希通过。boot SHA256 0f8671b2eb7a2d55718c9fbf40e30e874c4cf7b96e02b48a909d468548571687。

记录器改用与来源绑定匹配的不可变attempt，并为每次run冻结handoff，单页和八页报告均引用各自不可变文件，避免后续实验覆盖历史来源。两份原wire/FDT/log和cleanup重新核验通过。

新增256页入口选择，固件算法不变。独立1GiB QEMU的256页正常46项、部分写后UDF恢复48项及读取UDF恢复通过，目录20261028T064119.192965Z-lnm4fiii。手机候选065009Z已编译/结构通过，首MiB预计约3.15秒，8秒设计预算；当前尚未执行。boot SHA256 8d35cb2a36aa17513164ebb32798c913808ef5cb832a1a2a40edda909ac00e65。即使此候选通过，也不表示整个256MiB、隐藏DMA所有权或分配许可。


## 原生XNU主机成功（2026-10-28）

065702Z实际编译/链接成功，887份对象记录，18,104,064字节ARM64 MH_EXECUTE，SHA256 a96f212f376e0c581294839ab8726e22e8c7847cf896fd98f495e828f6842678。070142Z独立结构/符号检查通过，未定义符号0；完整产物、原报告、编译记录和日志冻结。未prelink、未打手机内核镜像、未在手机运行；SM8150 XNU平台仍未实现。细节见NATIVE-XNU.zh-CN.md。


## 第一MiB实机验证：20261028T071253Z

来源绑定a8a3033的065009Z镜像通过临时fastboot boot：0xc0000000起连续256页/1048576字节，completed/restored均256，图案262144字、恢复131072字均零差异，Dirty/BackupWords0，原始/恢复摘要相等。耗时3155.9350520833ms；现场256点只读及95项策略/4项入口保护再次通过。Android/root/原boot哈希正常，071435Z正常重启清理通过、临时属性消失。未flash/erase/format，未修改原备份。

boot SHA256 8d35cb2a36aa17513164ebb32798c913808ef5cb832a1a2a40edda909ac00e65；FD SHA256 a0d8a4e036fe5adecc44197a5622f53fb79821cf71536b4ce8905ef9b69f0ac7。独立原wire/FDT/log/不可变attempt与handoff/cleanup核验见boot-ram-write-observation-pages256.json。事实仅限前MiB，整个256MiB、跨页别名与隐藏DMA所有权仍未证明；分配器仍未扩展，手机DarwinBoot/XNU未执行。


## 原生XNU早期模拟器执行（2026-10-28）

本次真实18MB原生内核经固定DarwinBoot进入QEMU，在调试器中确认第一条原生指令执行，并在MMU/缓存开启后到达_arm_init。没有修改原内核文件或采用合成接收器替代；最小ADT与512MiB AAVMF环境不代表手机资源。新增UEFI Exit通知门与独立GDB观察器，后续扩充逐段内存哈希与平台初始化断点；细节见NATIVE-XNU.zh-CN.md。手机仍在Android，最新RAM正常重启清理通过。


## 原生内核bootstrap与手机loader诊断准备（2026-10-28）

原样原生XNU在QEMU到达kernel_bootstrap，10个加载segment的文件字节读回哈希一致；两处最小ADT输入缺项已按同轮生成FDT和固定XNU接口修正，失败日志保留。手机DarwinBoot拒绝模式接入已验证物理TimerArch；不供应有效内核、ExitBootServices必须0、不扩RAM。新FD模块组合首次被结构检查拒绝并保留，精确增加组合后stage6 QEMU81项通过；stage2/3和故障恢复正在验证。详见NATIVE-XNU与DARWIN-REFUSAL。


## Darwin拒绝模式主机门禁完成（2026-10-28）

新增组合的stage2/3/6 QEMU与路由故障恢复分别59/61/81/55项通过，Darwin独立wire 26项、固定来源审计及物理TimerArch/manager/ICC/使能视图/路由/IRQ门禁刷新通过。082113Z手机stage2仅编译与镜像检查通过，待绑定与临时实机启动；原RAM 065009Z历史Git/快照预检保持通过。没有给手机供应有效内核、没有扩RAM、没有ExitBootServices。


## 手机DarwinBoot拒绝与卸载通过（2026-10-28）

02f39c0的152项输入逐Git/快照绑定，082338Z/082804Z/083159Z SEC2/MMU3/DXE6均通过。实际固定DarwinBoot v2加载、启动、坏输入拒绝、卸载/协议移除与控制台/Boot Services恢复；ExitBootServices0、FAT CRC不变。同轮物理IRQ/EOI/notify262且全部状态恢复。083330Z正常重启清理、Android/root/原boot哈希通过。boot-darwin-refusal-observation.json含独立原wire和不可变记录核验；尚无手机正向内核交接、未扩RAM。

原生构建器补齐立即冻结内核/887编译记录/日志与runner；082939Z增量构建及083016Z结构检查通过，内核哈希与初次成功一致。QEMU继续探查BSD初始化，首次083638Z到machine_startup/kernel_bootstrap后出现kalloc断言，明确为失败，未跳检查；正在核对具体条件。


原生QEMU进一步定位：默认kt_fixed_zones260在48字节类生成33池超过原断言；显式模拟器预算200后通过该阶段，实到kernel_bootstrap_thread/PE_init_iokit，再在crypto_random_kmem_ctx_size空provider处data abort。全部均未到bsd_init，保留失败记录；内核字节未改。下一步补齐公开源码crypto provider及保持完整初始化自检，不能用空回调或跳POST冒充成功。


## 源码 crypto provider 默认自检与注册（2026-10-28）

新增独立 sourcecrypto 配置和显式构建开关；固定上游保持未修改。809 份第三方固定快照文件逐 Git blob/SHA256 验证，保留完整 FIPS 头/KAT；未认证 Apple 原 archive。093403Z 两个 archive 各 529 份 C、887 内核记录成功，18,421,664 字节内核 SHA256 e5f1db32113f1e41f6cb252fc08e5e914001da45f0c1c74703018a813d8134aa；093738Z 结构检查及未定义符号 0 通过，产物/命令/日志冻结。

094943.352011Z-vyn8innj QEMU 核对 10 段真实加载字节，默认 POST mode0/status0、provider 返回0、crypto_init1 与函数表注册通过；随后明确缺平台 driver，bsd_init 仍失败。该模拟器显式 kt_fixed_zones=200，不用于手机。没有 prelink、手机 XNU 或新增 RAM 分配。来源、失败与独立复核见 NATIVE-XNU.zh-CN.md、native-crypto-verification.json。

下一硬件门槛为候选 RAM 在新 MMU 下的只读映射验证；继续区分映射可读、可恢复写入、分配合同与隐藏 DMA 所有权。


## 候选 RAM 只读 MMU 映射：开发与主机验证（2026-10-28）

新增默认关闭的独立mapped wire/状态机/AT权限查询和PAR恢复，复用同轮FDT/策略/入口保护，未扩展allocator。74项mapped与73项原门禁主机检查、QEMU阶段2正常45项/阶段3正常48项及精确mapped load异常返回47项通过；首轮ICF导致故障注入位置错误的失败已保留并修正。来源、命令、限制见RAM-MAPPED.zh-CN.md。手机尚待此版本阶段2/3实测。


## 手机阶段2/3通过：20261028T103622Z / 20261028T104100Z

两阶段固件输入及15项验证脚本绑定5970805ef423e92000fd8f7714a3d392b1482434，146项板级/通用包输入逐Git blob和构建快照相符。阶段2只证明同轮保护与原256点读取；阶段3在EL1/SCTLR0xc0180d/DAIF全mask时，对0xc0000000..0xd0000000的256点完成WB恒等转换、写权限拒绝及PAR原值0恢复。前后摘要2715173488051968377完全一致，2198ticks/19.2MHz约0.114479ms。没有候选RAM写入或新allocator内存。

阶段2之后103822Z及最终104335Z正常重启清理通过；Android/root/原boot哈希正常、全部临时属性消失。阶段3私有boot SHA256 661d93355aa1e98cdfa89194799c39df897bf3ea78a38ddd68c4ba5fe1c8bdac，FD SHA256 a8aad68abc930f591be2e637cdc1a3f9b3024b5135d5fa14c8e7d9c95723292b。两份独立原wire/FDT/log、不可变handoff/attempt及cleanup复核见boot-ram-mapped-observation.json。抽样、只读权限与缓存摘要事实不推广为整窗口测试或隐藏DMA所有权；手机正向Darwin/XNU仍待实现。原备份未改动，未flash/erase/format。


## 带缓存维护的可恢复 RAM 写入实现（2026-10-28）

新增默认关闭的阶段2/3缓存页诊断，复用原完整页恢复engine及8秒预算；WB下逐页PoC clean/invalidate，正常/异常先恢复原字节再恢复RO并重新查询256点。44项实际C/ASan/UBSan、18项wire反例及旧门禁73/mapped74/engine43回归通过。真实QEMU阶段2正常47、阶段3正常53/部分写UDF恢复55/mapped load UDF49通过；默认完整DXE47/44/44通过。最终STR、逐行DC CIVAC/DSB、权限更新、真实.data存储及六份固定Git blob独立审计通过。手机尚待单页两阶段实测，未扩分配器。来源、命令、失败边界与未知项见RAM-CACHE-WRITE.zh-CN.md。


## 缓存单页手机实测：20261028T112932Z / 20261028T113233Z

来源绑定25730912c8a429c9b8c5cd91157ccdb990c7f8f1，两阶段149项板级/上游输入逐Git blob及构建快照一致，另22项验证脚本绑定。stage3在WB和MCI开启下，对0xc0000000第一页4096字节完成两轮图案和原内容恢复，差异均0、Dirty/BackupWords0；pre/post同步1/3，恢复RO并重新256点验证写拒绝。3432ticks/19.2MHz=0.17875ms。boot SHA256 5b59cc000edfa1f5be40ab059d3e19d0adcdf6841bdfabab103ceeab346e5c85，FD 699d28b50f557e85a34546dc2562e4c6e26b5fda3a401f14dcfe6eb217e90ecd。

113122Z及113426Z正常重启清理通过，Android/root/原boot哈希正常，临时属性消失。独立原wire/FDT/log/不可变handoff与attempt复核见boot-ram-cache-observation-pages1.json。不能由单页时延外推整窗口通过或分配权限，下一步前MiB实测。


## 缓存首 MiB 手机实测：20261028T113820Z / 20261028T114127Z

两阶段来源绑定21483399fb35a703370b469b8089b11ea28a8296、149项固件输入和22项验证脚本。0xc0000000起连续256页/1048576字节，图案262144字与原字恢复131072字均零差异，完成/恢复256页，Dirty/BackupWords0，摘要相等。pre/post同步256/768，read/write转换与PAR保存256，恢复RO写拒绝256。830737ticks/19.2MHz=43.2675520833ms，非全窗口性能保证。

114012Z及114346Z正常重启清理、Android/root/原boot哈希通过，临时属性消失。boot SHA256 78d742ded6af740b4e161f5a772d1ef803d47984f74fae2295ef3409f26107f2；FD a3e12eca3d3c6fefd978cff9b9386d09731fe6bb09ae379e5b4f3c5ab1ec2be7。独立原wire/FDT/log/不可变attempt及handoff复核见boot-ram-cache-observation-pages256.json。未扩分配器，跨页别名与隐藏DMA生命周期仍未知；尚无手机有效内核交接。


## 缓存前16 MiB手机实测：20261028T114523Z / 20261028T115003Z

绑定21483399fb35a703370b469b8089b11ea28a8296，149项固件输入/22项验证脚本独立核对。0xc0000000起连续4096页/16777216字节，图案4194304字和原字恢复2097152字全部零差异，完成/恢复4096，Dirty/BackupWords0，摘要相等；pre/post同步4096/12288，RW转换/PAR与恢复RO写拒绝均256。13263027ticks/19.2MHz=690.78265625ms。boot SHA256 92a8824b7721361a5395904ce96216e25d30f078f01a912c9b5a314d32931221，FD df78d859905b87551a771c6396b2ec4a779c86a8e171762b0a0dc1dde8ff272e。

114732Z及115212Z正常重启清理、Android/root/原boot哈希通过，临时属性消失。原wire/FDT/log、不可变handoff/attempt和cleanup独立复核见boot-ram-cache-observation-pages4096.json。这里的16MiB是candidate测试范围，不是把该范围注册为原16MiB诊断arena；分配器仍未扩展。跨页别名/隐藏DMA所有权与手机有效内核交接仍未知。


## 缓存前64 MiB手机实测：20261028T115603Z / 20261028T120013Z

两阶段149项固件输入/22项验证脚本绑定56ba1116b452f957753f020e4b5e5dce4b41be3d。0xc0000000起连续16384页/67108864字节，图案16777216字、原字恢复8388608字均零差异，完成/恢复16384，Dirty/BackupWords0，摘要一致；pre/post同步16384/49152，RW转换/PAR保存与恢复RO写拒绝均256。53150038ticks/19.2MHz=2768.2311458333ms，未延长8秒预算。

115818Z及120318Z正常重启清理、Android/root/原boot哈希通过，全部临时属性消失。boot SHA256 6beae0568c97001da490dba7dcfce0c6fcf6d8b0ab6aaab2cb4ad4480f3ebb79；FD 88ad3e60b6346362fd457a1bb7e79cd30e496a6f59c073966feacf6efb67a59f。原wire/FDT/log、不可变handoff/attempt与cleanup独立复核见boot-ram-cache-observation-pages16384.json。

新增validate_ram_cache_evidence.py可重跑复核4KiB/1MiB/16MiB/64MiB全部历史Git/源码快照/镜像、原wire/FDT/log及正常重启原记录。独立读取cleanup的原baseline FDT确认无raphael诊断属性，核对两次boot哈希、正常reboot、boot_completed及root原命令输出。其恢复结论来自重新解码固件的原字恢复记录，不声称在Android中重新读完整候选DRAM。

完整256MiB测试、跨页别名、隐藏DMA生命周期与分配合同仍未完成；按本轮时延线性估计整256MiB将超过8秒，因此没有直接执行65536页手机配置。分配器仍只有原16MiB arena，手机有效DarwinBoot/XNU交接仍未执行。下一步应在相同8秒预算内审计并改进缓存路径，独立验证跨页别名和分配合同；不能靠放宽预算或直接登记未核实RAM绕过门槛。


## 页面边界缓存屏障版本（待本机新证据）

缓存适配改为普通WB load/store与compiler fence，PoC页维护前后DSB SY；旧uncached与恢复引擎不变。主机44+18及旧73/74/43通过，QEMU单页阶段2正常47、阶段3正常53/部分写UDF恢复55/读取异常49、默认关闭DXE47/44/44通过，实际机器码与固定一手来源审计通过。详见RAM-CACHE-WRITE.zh-CN.md。本版本尚未手机执行；历史前64MiB事实仍只属于旧版本，未扩分配器或放宽8秒预算。


## 页面边界版单页实机，完整窗口QEMU仍失败

bec9798的两阶段20261028T123018Z/20261028T123517Z单页手机测试成功，实际stage3运行时间以boot-ram-cache-observation-pages1.json的不可变记录为准：0.1115625ms，两轮图案/全部原字恢复零差异、Dirty/BackupWords0，PoC同步1/3、RO恢复256点通过；123622Z正常重启清理、Android/root/原boot哈希通过。前64MiB历史事实仍属于旧版本，尚未以新版本扩测。

完整256MiB的QEMU 123212.707989Z-rj0mf832与123535.809285Z-7sfvk8jg均触发不变的8秒预算，分别完成/恢复65449、60118页；没有残留Dirty/Backup，独立MMU关闭receiver核对原DRAM、RO恢复256点均通过，但整体测试明确失败。原日志/源码快照及两份ram-cache-qemu-timeout报告保留；不能把恢复成功当作整窗口通过，主机并发影响未知。下一步减少逐缓存行的函数间调用开销，仍保持同样CIVAC和完成屏障。


## 页面边界版首MiB手机实测：20261028T125630Z / 20261028T130021Z

两阶段149项固件输入及22项验证脚本绑定06654aa4907a9193a6b4b0a29c69af48531e840b。0xc0000000起连续256页/1048576字节，完成/恢复各256，两轮图案262144字、原字恢复131072字均零差异，Dirty/BackupWords0、摘要相等；pre/post同步256/768、RW/PAR及恢复RO写拒绝256。实际耗时27.4865625ms；对照旧版43.267552ms减少约36.5%，不外推完整256MiB通过。

20261028T130128Z正常重启清理、Android/root/原boot哈希通过，诊断属性消失。boot SHA256 0629947b1603cb7e6000f070d831e43461b411b7d120d7709cd42e407ffd6f00；FD b2540a1db88f4cc03c2c8ac165152f58e03239a677b345c8f4c2cd9fad337081。完整原wire/FDT/log/不可变attempt与handoff独立核验见boot-ram-cache-observation-pages256.json。未扩分配器、未flash/erase/format、未改原备份。新版64MiB的QEMU阶段2 125631.629511Z-c7qe108p正常47项，阶段3 125736.283359Z-tol8aclq正常53/部分写UDF55/读取异常49及机器码审计通过，尚待新版手机64MiB实测。


## 页面边界版前64MiB手机实测：20261028T130412Z / 20261028T130930Z

两阶段149项固件输入和22项验证脚本绑定e39d25104434edf602d1b54a7dc73a14a07fb8a0（缓存实现为bec9798，通用源码与旧恢复引擎未修改）。0xc0000000起连续16384页/67108864字节，完成/恢复16384，两轮图案16777216字和原字恢复8388608字均零差异，Dirty/BackupWords0、摘要一致；pre/post同步16384/49152，RW/PAR及恢复RO写拒绝256。实际33763913ticks/19.2MHz=1758.5371354166666ms，比旧版本2768.231146ms减少约36.5%。只是此范围实测，不是完整256MiB或分配许可。

20261028T131038Z正常重启清理、Android/root/原boot哈希通过，临时诊断属性消失，当前没有进行中的实验。boot SHA256 a7d2218e29996123f07449affb7bcddf5674f30f0a5742f27d46ed9e1f4e99cc；FD 5000a3b01b07bd0cf9baef136e551425f8b0179ca56fef42a87707653edd93ad。原wire/FDT/log/不可变attempt与handoff及cleanup核验见boot-ram-cache-observation-pages16384.json。分配器仍只有原16MiB诊断arena，未flash/erase/format、未改动原备份。

新增validate_ram_cache_timeouts.py独立重解码四次全窗口QEMU失败的原wire、read/mapped门禁、超时阈值、恢复页数、Dirty/Backup及RO状态，核对596份归档源码文件与固定Git/独立直接循环快照，并检查MMU关闭receiver记录原DRAM完整恢复。ram-cache-qemu-timeout-verification.json只证明负向证据一致、8秒预算生效与恢复记录，不把任何失败当全窗口通过。直接循环及指令时钟均未采纳，当前源码只含已实机测至64MiB的Basecore页边界路径。

下一步需要解决完整256MiB的功能验证与有界运行、跨页别名和分配合同，再进入手机有效DarwinBoot/XNU交接。可评估减少通用engine逐字双层回调的开销，但这是待论证的实现方向，需要保留原备份/Dirty/PoC/RO恢复语义和实际C模型、异常注入及机器码证据；不是已实现或已验证的方案。不能根据本轮64MiB时延线性外推全窗口通过，也不将修改模拟器时间或简单放宽预算作为证明。


## 重新获取并接入上游 main（2026-10-28）

按用户要求重新fetch并以fast-forward接入UniXNU `40d21cc65171c3a24faa130a2a8e899f85790485`（此前0fc0fc1，共4个新提交、73个变更文件），随后ls-remote再次确认main/HEAD未变化。新提交主要是设备记录及recovery日志读取指南；运行时package、CLI、profiles、patches、drivers gitlinks与feeds/components声明逐Git object相同，固定Mu/Basecore/DarwinBoot/XNU/source-crypto依赖保持原版本。

sources.lock.json已更新，7个当前构建/审计脚本改为读取集中精确锁定SHA；历史校验器保留旧SHA，上游工作树干净。旧checkout保留独立baseline引用，6个RAM直接回调WIP文件与更新前binary patch完全一致。未修改硬件参数或继承其他板型配置。

新版本重新编译并验证：上游terminal单测45项运行、44通过/1跳过；完整UniXNURun与只读payload QEMU17项；DarwinBoot拒绝/生命周期38项；packed ramdisk合成接收器正向交接25项；默认关闭RAM写入的SEC/DXE正常47/BRK恢复44/UDF恢复44项。ARM64 PE/重定位和FD结构分别检查；371项构建快照输入、其中206项上游Git blob独立核对。首轮payload fixture的旧PACKAGES_PATH缺目录失败已保留，修正本地runner后重跑通过。源码和结果详情、命令及产物哈希见UPSTREAM-REFRESH.zh-CN.md与upstream-refresh-20261028.json。

本轮没有重启手机或写分区，原备份未变；不把模拟器或新版本主机构建当作新增手机验证。直接回调优化仍需严格机器码审计、完整256MiB阶段3与恢复、逐级实机复测；完整移植目标保持未完成。


## 直接回调版本：完整窗口QEMU通过（2026-10-28）

保留原RamWrite.c、232字节恢复engine、176字节cache状态和312字节wire，增加显式RaphaelWriteRamWithCacheDirect入口。共享BeforeRead/AfterWrite规则内联到本机原始load/store回调，消除每字第二层间接调用；Counter/Sync仍接收原始caller context，紧急恢复仍使用cache context。页前PoC同步、两轮pattern及原字恢复后的同步、Dirty/完整备份与先数据后RO的顺序不变，未扩allocator或放宽8秒预算。

新UniXNU 40d21cc下，90项实际C/ASan/UBSan及18项wire检查通过，另12项编译期ABI断言将状态字段逐一对应机器码。单页QEMU阶段2正常47、阶段3正常53/部分写UDF恢复55/映射读取UDF返回49通过。完整65536页QEMU阶段2同样47项、阶段3同样53/55/49项通过；完整窗口的normal实际4987.654768ms，完成/恢复65536页、图案67108864字和原字恢复33554432字均零差异，Dirty/BackupWords0、摘要一致，恢复RO256点通过。独立MMU关闭receiver核对全窗口原DRAM字；不能将此模拟器地址或性能当手机参数。

严格链接审计检查完整34条read与31条write回调（包括首RET后的失败分支），唯一候选64位load/store、唯一Sync间接调用、257次写checkpoint与准确context/计数偏移。76项opcode/extent/checkpoint负向及历史schema兼容检查通过；旧boundary2审核归档独立文件。Basecore的实际CIVAC、页前后DSB、RW/RO与.data存储审核通过。旧read/mapped/write门禁73/74/43回归通过；默认关闭RAM诊断的完整DXE47/44/44使用完全相同的149项固件输入，无需重复构建。

准确证据：ram-cache-source-audit-pages1.json、ram-cache-source-audit-pages65536.json、ram-cache-native-audit-host.json、ram-cache-host.json。完整QEMU阶段2为20261028T140519.817674Z-ptikv25e，阶段3为20261028T140007.068845Z-brlqocnb；单页阶段2为20261028T140519.817701Z-de8aogqa、阶段3为20261028T140519.817674Z-cu8bi4fl。此版本尚未手机执行，历史手机前64MiB仍属于boundary2。下一步先单页手机两阶段，再逐级扩大；完整所有权/跨页别名/分配合同仍未知。


## 直接回调版完整256MiB手机实测通过（2026-10-28）

本轮4KiB/1MiB/64MiB/256MiB依次进行两阶段临时启动、原字/RO恢复、Android返回和正常重启清理，全部绑定d0a54cc50f47e6996b1a8b970f0032a8c94d71c4，UniXNU为40d21cc65171c3a24faa130a2a8e899f85790485；每份149项固件输入和22项验证脚本逐Git blob与归档快照核对。新阶段3分别为142732Z/143440Z/143848Z/144256Z，实测0.0990104167/23.778125/1521.8653125/6087.08453125ms；未更改8秒预算。

完整窗口为本机来源约束的0xc0000000..0xd0000000，连续65536页全部完成并恢复，图案67108864个64位字、原字恢复33554432字均零差异，Dirty/BackupWords0、摘要3761833498104544988相同；pre/post同步65536/196608次、RW/PAR和恢复RO写拒绝256点。两阶段build为20261028T142442Z/20261028T144222Z，手机run为144040Z/144256Z。阶段3boot SHA256 41cbf90784019284fb4863372ce21b0a22a1e2d56414ec2a8cf3ed4701f8fbbb，FD 2a77e1665d368f769e8fc7e12b09ca04cc086b80b956c5d9b28506813bf7f04d。

144408Z最终正常重启清理通过，Android/root/原boot哈希正常、临时属性消失；当前没有进行中的手机实验。validate_ram_cache_evidence.py的独立核验20261028T144645.527035Z-b5pgi14w重新读取全部5份范围索引及各不可变wire/FDT/log、Git/冻结镜像/源码、正常重启的原命令记录，最大范围268435456字节。原字恢复事实来自固件逐字比较回传，不冒充在Android中再次读取完整原DRAM。原备份未改动，没有flash/erase/format。完整原始证据仍为私有，公开仅来源/哈希/诊断结果。

私有镜像预构建曾有3次秒级目录命名冲突，在创建镜像前退出；失败日志保留于direct-20261028-pages1/256/16384目录。随后串行重试，不覆盖旧目录或放宽门禁。四次旧版本QEMU全窗口失败及恢复证据也保留，新版QEMU/手机通过不重写历史。

分配器仍仅使用原16MiB诊断arena；这次逐页可恢复写不证明跨页别名、长期隐藏DMA所有权或分配合同。下一步独立实现跨页同时标记、异常恢复及其门禁，再建立连续分配合同并推进手机有效DarwinBoot/XNU交接。完整移植目标仍未完成。


## 重新 fetch 与候选源码独立固定（2026-10-28，23 点后）

远端 main/HEAD 仍为40d21cc，活动锁未改。本次新拉到feat/ipados27-gpu-parity的fb5cdd6/63cc454，已独立检出63cc454及19个固定gitlink；与main为7/28个提交分叉。21仓库2490个原始源码文件与Git blob及执行位一致、全部干净。候选native/UDIF10、terminal44+1跳过、XnuPrelink59通过，另实际DarwinBoot C解析器和稀疏ramdisk两组检查通过，37份Python变更语法通过。

候选包含arm64e/新XNU构建及9个组件更新；PAC尚未逐核核实，ArmCpu仍用PPI27而本机物理timer是18，DarwinBoot新fileset/RootPolicies尚无本轮完整UEFI/QEMU/手机结果，Mac Metal脚本未执行。因此只固定候选供后续接口适配，未替换活动固件/OS profile或改写历史证据。本轮没有手机操作或原备份修改。详见UPSTREAM-REFRESH.zh-CN.md与upstream-recheck-20261028.json。原跨页RAM/分配合同与手机有效XNU交接工作仍待继续。


## 跨页同时标记与恢复引擎实现、主机及独立 EDK II 编译（2026-10-28）

57555b0 新增独立 RaphaelRamAliasLib/INF/DEC class/RamAlias.dsc，旧页恢复、cache、read/mapped wire 与 native adapter 未改。每页首尾各8字节、全部备份后两轮同时标记；逐样本 RW 恒等翻译/PAR 查询，先排空全体脏缓存，再取得备份。store前单调恢复范围/反码及Dirty，强制恢复不超时；所有备份摘要和journal有效才允许恢复store，先排空标记缓存再原字写回、PoC、全体独立读回成功后清除Dirty/备份。失败保留全部备份允许显式重试，恢复重入拒绝。

155542.543576Z-pm9nqcft 实际C/ASan/UBSan 249项通过，覆盖65536页首尾样本、远距DRAM别名、全部callback位置/执行后失败/期限/损坏/恢复重试；独立AArch64 ELF对象7528字节、无未定义符号，真实Mu Basecore/INF/DEC/DSC CLANGPDB库归档编译及LTO bitcode目标检查通过。构建前冻结全部源码/本包头文件，独立逐Git blob绑定57555b02d601ded4a0badd7bc9f0fd84b62315c5并重算产物/原日志。首次NULL定义顺序及LTO归档检查器错误的失败日志均保留。

完整样本备份仍需1MiB owned存储；当前只有库，没有新增FD或SEC/PCD/allocator接入，也未做新库QEMU/手机或真实同步异常恢复。此前手机完整256MiB逐页恢复事实仍只属于旧诊断；本轮没有手机操作或原备份修改。下一步落实FD/.data范围与异常可访问备份、原生PoC及RW/RO/PAR恢复，再做两阶段QEMU与手机门禁，详见RAM-ALIAS.zh-CN.md和ram-alias-host-20261028.json。


## 备份存储的只读容量核查（2026-10-29）

重新核对原144222Z的FD原字节哈希、PE/data及SEC map，现有3MiB FD对齐后全0xff尾部2426960字节，原页备份4KiB位于实际.data文件覆盖中。拟议1MiB别名样本备份仅从算术上有空间；新增代码/对齐/下游模块重排必须经新FD实编和结构审计。未选择新物理区、未实现新存储、未改allocator。来源和限制见ram-alias-storage-20261029.json。


## 上游源码重新拉取（2026-10-29）

用户要求重新拉取上游。实际 fetch 先得到 2c40ae9，主机检查期间远端再更新至9fe4855117709d1a0119baefaa66180682dee52c，随后再次 fetch 并独立检出9fe4855及19个精确gitlink。main/HEAD仍40d21cc，候选与main为7/30提交分叉；活动sources.lock.json未变，旧63cc454和中间2c40ae9快照均保留。

最新候选21仓库2504文件逐Git blob/执行位一致，工作树干净；native/UDIF10、terminal44+1跳过、XnuPrelink59及两组实际DarwinBoot C检查通过。精确metal2vulkan pin上37份bridge补丁依次应用、逐前缀tree SHA和Turnip补丁结构检查通过。首次完整fetch与partial clone普通write-tree超时保留；以blob filter和write-tree --missing-ok完成只涉及修改内容的精确索引审核，不修改上游源码。

新增内容为Turnip单ring同步、AdrenoMetal绘制/Core Image/编译器探测和Adreno740重启前SMMU故障终止。A740/SM8550代码没有接入本机，PPI27/PPI18、PAC与DarwinBoot手机交接门禁仍未消除。没有候选固件编译/FD/QEMU/手机或Mac Metal验证；无手机命令或原备份改动，板级/SoC/SEC/allocator代码与活动依赖均保持原样。准确版本、命令与哈希见UPSTREAM-REFRESH.zh-CN.md和upstream-refresh-20261029.json；继续既有跨页RAM诊断的SEC备份/恢复接线工作。


## 上游拉取结果复核（2026-10-29 01:08:08 +08:00）

实际再次 fetch 并核对全远端分支，main 40d21cc、候选 9fe4855 均未继续变化。候选19个gitlink与21仓库2504文件原字节/执行位一致，历史11份证据及5份测试日志哈希复核通过；未重复旧测试，也未将旧手机结果绑定候选。source lock及11份RAM alias WIP原样保留，未操作手机或备份。准确UTC、版本、命令与本次边界见upstream-reconfirm-20261029.json。


## 2026-10-29：自有UEFI有效内核主线与独立恢复

bd61c3a新增默认关闭native profile：分块20MiB FAT、24MiB FV、48MiB staging和Mu原生type bins，原loader有效加载256MiB窗口。自有SEC/DXE QEMU最终193742Z两轮分别到物理timer IRQ/EOI=3/3及IOFindBSDRoot入口，完整buffer和10段哈希/EL1/DAIF/MMU状态核验通过。独立复核194101Z逐Git blob绑定；旧1MiB路径66项回归通过。64-zone断言失败及两次构建失败保留。见NATIVE-SEC-DXE.zh-CN.md。

da16f56新PSCI query手机194116Z：SMC、EL1、PSCI1.1和SYSTEM_RESET支持，nonce回传；独立64KiB receiver的194548Z临时启动自动回Android，原boot/root/新boot_id/清理通过。无直接phone reset instruction trace。原备份不变、没有分区写入或上游同步。手机大FAT布局和有效XNU仍未执行，下一步按PSCI-RECOVERY.zh-CN.md推进。


## 高段Android返回通道手机实测（2026-10-29）

默认关闭的AndroidReturn用固定Mu原decoder恢复本机当前定制Android内核；主机4,107项ASan/UBSan、QEMU阶段3/6的19/20项，以及手机204929Z/205204Z的nonce、CRC、完整输出和正常重启清理通过。DXE阶段连续窗口保留高256KiB，原Mu分配器未包装。16MiB失败和独立入口geometry记录全部保留；成功小规模预算12MiB。主线有效XNU的自有SEC/DXE QEMU物理timer IRQ回归通过，手机有效XNU没有执行。详见ANDROID-RETURN.zh-CN.md。无上游同步、分区写入、RAM alias扩展或private产物发布。


## 真实原ExitBootServices手机通过（2026-10-29）

实现29d4a51，手机224029Z的version2/status4确认原服务成功返回、表清零及退出后内核/args/ADT完整。物理timer 280 IRQ/EOI、停钟与状态恢复通过；80.475秒自行回Android，正常重启/root/原boot哈希/临时属性清理通过。376项输入和原始证据独立复核见NATIVE-EXIT.zh-CN.md及native-exit-verification.json。QEMU正向25项、实际破坏字节负向拒绝及恢复通过，旧失败保留。没有执行XNU或修改分区/原备份，没有同步上游。下一步手机XNU指令入口与诊断恢复。


## 手机XNU有界实际指令入口通过（2026-10-29）

实现4f66e91。原Mu真实ExitBootServices之后，原DarwinEnter跳原XNU入口，执行B/OSLAR/DAIFSet/mov x20/mov x21共5条原始指令，临时BRK在0xc042606c捕获ESR0xf2005350及正确args，随后恢复原指令/UEFI翻译和10段CRC/零尾/ADT。最终QEMU27项、相同Image的独立单步跟踪及错误标记拒绝/恢复通过。手机230308Z约80.453秒自动回Android，正常重启/root/原boot哈希/清理通过；381项Git及原始数据独立复核。命令/版本/哈希/边界见NATIVE-ENTRY.zh-CN.md与native-entry-verification.json。尚未到arm_init、XNU自身页表/平台/GIC/timer或用户态；未同步上游、写分区或修改原备份。


## 手机原XNU bootstrap MMU与arm_init入口（2026-10-29）

2026-10-29。手机234327Z已实测原XNU建立bootstrap页表、设置翻译寄存器、开启MMU并到达高VA arm_init首指令检查点。72Q记录和完整64KiB页表通过，4表页/258非零描述符/128组block；全部临时代码、页表与UEFI状态恢复，原10段CRC/零尾/args/ADT重验通过。80.516秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。389项Git输入及原始证据独立复核，详见[NATIVE-MMU.zh-CN.md](NATIVE-MMU.zh-CN.md)。arm_init C函数体、XNU平台/GIC/timer、根卷与用户态仍未执行。下一步建立C初始化阶段的可恢复日志，推进平台初始化。未同步上游，RAM alias暂停，原备份未改动；当前手机正常Android，无运行中的实验。

实现d2a82df；最终QEMU234046Z通过28项，相同Image的234132Z独立单步/错误BRK/末端页表损坏三项通过；默认关闭回归234505Z的normal/BRK/UDF为47/44/44。手机构建234211Z和实际C布局预检234314Z五项通过；389输入独立复核234552Z通过。具体版本、命令、镜像哈希、失败和范围见NATIVE-MMU.zh-CN.md及native-mmu-verification.json。


## 后续C初始化观测（仅QEMU）

235049Z复用最终MMU Image，在模拟器已加载内存恢复arm_init首指令，原C执行过PE_init_platform(FALSE)并到rtclock_early_init及arm_vm_init入口。10段×5处原始快照和独立逐字节复核235353Z通过，页表未变，3个数据/栈段出现真实写入。手机仍只验证到arm_init首指令；下一步需实现这些段的有界备份/恢复和更深检查点。细节及局限见[NATIVE-EARLY-C.zh-CN.md](NATIVE-EARLY-C.zh-CN.md)。


## 手机arm_init C初始化前缀与原字恢复（2026-10-29）

2026-10-29。手机001904Z已执行原arm_init C初始化并到达arm_vm_init首指令，原平台首次初始化/拓扑/当前线程和早期时钟/启动子系统前缀已通过该检查点。2,637,824字节三个数据/栈段完整备份恢复；130,896字节/10,908个变化64位字独立重建，原10段CRC/零尾/args/ADT及UEFI状态恢复通过。80.434秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。396项Git输入与原始证据独立复核，详见[NATIVE-EARLY-RECOVERY.zh-CN.md](NATIVE-EARLY-RECOVERY.zh-CN.md)。arm_vm_init函数体、pmap重建、正常XNU IRQ/timer生命周期、根卷和用户态尚未验证。下一步处理pmap切换后的日志与恢复；原TTBR0将被置为空表，现有物理别名relay不能直接沿用。当前手机正常Android，无运行中的实验；未同步上游、写分区或改原备份，RAM alias暂停。


2026-10-29补充：QEMU原arm_vm_init已真实换TTBR1/置空TTBR0并返回，66页活动页表、644页高地址数据映射及7处完整快照经396份冻结输入独立复核。手机仍仅到arm_vm_init入口。下一步独立TTBR0转换表恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)；未同步上游。


2026-10-29：stage12换表后恢复已实现，QEMU正向36项及同镜像独立5场景通过；旧stage11回归31项通过。手机仍以001904Z的arm_vm_init首指令为准，stage12尚待最终冻结构建、旧分支回归和本机布局预检。原始TTBR与诊断转换根分开，输入ADT的random-seed清零由独立备份恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。上游未同步、RAM alias暂停、原备份未改动。


2026-10-29。手机011328Z的stage12通过：原XNU arm_vm_init完成并换TTBR1/置空原TTBR0，在PE_consistent_debug_inherit首指令捕获后完整恢复3段/原代码/初始表和输入ADT。66页活动表、644页高数据映射及132936字节delta通过；80.337秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。405份Git/blob/冻结输入与原始回传独立复核，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。尚无正常XNU IRQ/timer生命周期、根卷或用户态。下一步推进pmap后的平台初始化与持续日志。未同步上游、未写分区、原备份未改动；当前正常Android且无运行中的手机实验，RAM alias仍暂停。


2026-10-29：主线推进machine_startup，新增platform profile和CNTP/CNTV/CNTKCTL完整恢复；QEMU38项通过。手机014730Z未返回且无回传，用户电源键恢复Android，失败保留。新增panic自动捕获及serial/console/idle/timebase/cpu中间目标继续定位。用户明确停止逐文件哈希和重复证据绑定，本轮采用runtime-only，未重算boot分区哈希。未同步上游或写分区，备份未改；见NATIVE-PLATFORM.zh-CN.md。

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


## 2026-11-01：原始系统盘的真机 extent 虚拟扇区读取

2026-11-01 主线续进：原始 OS/SystemOS 已分别上传至新建的本项目私有明文目录，完整 SHA-256 与主机一致，设置不可变标志并冻结 66/27 个 extent。OS 实机 20261031T180012Z、SystemOS 实机 20261031T180840Z 均完成 16 轮/128 次真实 READ10；首部、APFS 超级块、中段、尾部、跨物理块/extent 的 512 字节虚拟扇区逐字节一致，两轮分别约 71.098/71.154 秒自动返回 Android，nonce、控制器/看门狗恢复及普通重启清理均通过。两轮为独立 stage3 存储实验，无 XNU/挂载/用户态证明。新增常驻 XNU 控制器与两个只读卷，逐块认证代码已写并通过独立 ARM64 对象编译；190 槽存储 ABI/11 个原始接口绑定已核对早期对象，认证版及完整内核集成仍在验证。详见 docs/HANDSET-STORAGE.zh-CN.md。


## 2026-11-02：规范打包入口与预检查

新增原样 upstream templates/package.sh、board.toml 的 package/defconfig 映射、设备与工作区手动 macOS workflow、私有 build 输入示例、打包检查及说明。复用已拉取 c96b299 的独立运行库，不改变原实机 backend，不重新 fetch。
默认/17/完整 OS 名的检查均解析同一 62 补丁；21 项本地检查通过，包括参数与错误传播、路径空格、配置拒绝、YAML/shell/Python 片段及本地 CI 源码夹具。记录和布局检查通过；远端 Actions、完整镜像构建和实机执行未进行。
完整 release 仍缺 firmware.config/dsc/fd/packages、payload.volume/size_mib/loader 和 bootimg.dtb；--require-release 明确失败。这一项不能标为干净检出打包验收。详情见 UniXNU-raphael/docs/PACKAGING.zh-CN.md；本机验证索引 artifacts/packaging/20261102-validation/report.json。


## 2026-11-02 原版 PMGR 服务依赖与物理观察截止

`20261101T165321Z` 首次扩展窗口在手机原始 AMFI 返回 `No PMGR?` panic；nonce、原生快照恢复与 Android 清理成立，整轮失败。原报告的 `xnu_executed=null` 是旧 runner 未将已验证的编译 panic 计为执行的字段缺口；原始报告保留，后续 runner 分开记录执行证据和 checkpoint 验收。

独立接入原版 ApplePMGRNub 的显式诊断模式，保留其空 AON provider 路径：读取 UINT32_MAX、写入无操作，与固定 iPad7 原 AppleT8011PMGR 的对应槽位相同；不改变 AMFI 指令、不接入或宣称手机硬件 PMGR。非 VMM QEMU 39 项通过，随后手机 `20261101T171229Z` 整轮通过：原 nub class1856 字节、init/start/attach/注册成功；原 APFS/SystemOS 与 launchd EL0 保留，22 次系统调用。

400-poll 上限新增物理40秒截止；实际307poll、40.104766秒，20秒硬件阈值不变，60000ms绝对pet预算内77次刷新，终止后约4.457ms交还存储，Android普通重启/root/临时属性清理通过。累计UFS103154688字节、失败0；4K签名准备101138432字节、bad/no-hash均0。没有 dyld完成、launchd main、系统桌面证据。接续在同窗口比较DMA缓冲区复制性能，OS/SystemOS原盘不重传。详见 `UniXNU-raphael/evidence/native-pmgr-compat.json` 和对应冻结实机报告。


### 同日：DMA 缓冲复制实机对照

`20261101T172012Z` 整轮通过；唯一行为变量为 DMA 缓冲区 CPU 复制宽度（字节改自然对齐64位，尾部仍字节），控制器和READ10大小、DMA范围、逐4KiB认证不变。40.112623秒内读取494388224字节，对照上一轮103154688字节约4.79倍吞吐；原PID1从22次到78次Unix调用，签名对象从1到9，签名输入489881600字节；UFS失败0、代码签名bad/no-hash均0。末尾fcntl errno16仍由终止诊断中断大读产生。存储交还约2.064ms，恢复/普通重启/root/清理全部通过。下一变量为120秒物理观察和180秒绝对pet预算，硬件20秒阈值保留；尚无dyld完成、launchd main或桌面证据。


### 同日：120秒实机观察通过，PID1推进到204次调用

`20261101T175421Z`整轮通过，nonce、原生恢复、Android普通重启/root/属性清理成立。实际观察120097.982708ms、946 polls、235次pet；硬件20秒阈值不变。原APFS/SystemOS保持挂载，PID1累计204次Unix调用，27个签名对象就绪；UFS1489957888字节、签名输入1479376896字节，transport/bad-hash/no-hash均0。末尾仍是诊断主动终止共享缓存读取，没有dyld完成、launchd main或桌面证据。

首次长窗口QEMU在无OS根盘的夹具中遇原IOFindBSDRoot约60秒超时；失败保留为174538Z。显式QEMU DT-policy现增加40000ms物理截止，175243Z为39项通过、实际40073.039ms；手机ADT无此属性，不能用该模拟器结果声称手机120秒资格。手机120秒事实来自本轮独立实测。源码摘要见`UniXNU-raphael/evidence/native-service-window120.json`。

下一候选只改自有8192字节DMA缓冲的缓存类型：固定XNU IOBMD的kIOMapWriteCombineCache→VM_WIMG_WCOMB→MAIR0x44，Normal内外层non-cacheable；逐页AT读/写验证物理一致及PAR0x44，失败即停止初始化，不降级。控制器MMIO、READ10大小、DMA范围、DSB屏障和逐4KiB认证不变。尚待构建及手机数据；不声称已有性能收益。


### 同日：Normal-NC与返回记录容量修复

`20261101T180628Z`已自动返回Android并普通重启清理，但整轮失败：活动pmap图在109页、130188序列化字节后超过旧131072字节上限。原checkpoint、UEFI/控制器/看门狗恢复成立；缺完整页表，不能验收完整原生观察。对已恢复的8个mutable段及720264字节delta独立核验CRC，得到受限诊断记录：DMA两页读写AT/PAR身份及0x44属性成立，原PID1 246次调用、33个签名对象、UFS1873572864字节，transport/bad/no-hash均0。这些记录保存为原run的`verified-globals-only.json`，不改写原失败报告。

producer/serializer/receiver/decoder的pmap上限统一到512KiB，返回FDT由2MiB改4MiB；实际libfdt最坏记录（1MiB delta+512KiB pmap及其他最大输出）packed2484248字节、余1710056字节，18项ASan/UBSan边界检查通过。先前2MiB容量测试明确失败，尚未上手机的v11编排已停止，失败产物保留。v12复用同一冻结内核/载荷/extent，仅修复观测容量；QEMU39通过，手机182129Z正在恢复验证。

后续runner分开保留`native_verified_globals`与正常checkpoint验收：3份旧实测的重解码及破坏delta负例通过；缺页表不再遮蔽已经CRC证明的执行记录，`experiment_passed`仍要求完整原验收。240秒物理观察/300秒绝对pet预算的精确v3合同已通过host边界/到期/不匹配拒绝测试，候选构建可独立准备，手机启动必须等待v12整轮通过及清理。硬件20秒不变。


`20261101T182129Z`：Normal-NC同一冻结内核在修复返回容量后整轮通过，普通重启/root/临时属性清理通过。完整pmap132页、135462字节（超过旧128KiB），全部1982个恢复数据页与checkpoint验收成立；两页DMA身份/Normal-NC属性成立。120027.466406ms内UFS1872835584字节、246次syscall、33个签名对象、1860272128签名输入字节，失败0。同120秒旧映射基线吞吐约1.258倍；仍未越过dyld/证明launchd main。详情`UniXNU-raphael/evidence/native-ufs-normal-nc.json`。v13完成构建/预链接并在前轮清理后继续QEMU资格，尚无240秒手机结果。


### 2026-11-02：原launchd main实机证据与只读Data阻塞

240秒候选实机182935Z在约427.674秒自动返回Android，nonce、8个mutable段恢复及普通重启/root/属性清理成立，整轮checkpoint失败。原XNU的PID1-only一次性`kern.initproc_spawned`已为1；原msgbuf显示launchd执行init-with-data-volume、keybag、usermanagerd等任务。累计1474次PID1 syscall、53个签名对象、UFS3255964672字节，transport/签名错误0。不能再将main固定写为false；解码器现读原始标志。原报告不改，独立派生结果在同run的launchd-main-derived.json，公开摘要为native-launchd-main.json。

原panic是critical child tzinit PID17以signal0/status30退出后的proc_exit路径，并非PID1退出；前有fixup-mobile-tmp只读文件系统错误。尚无独立可写Data或桌面。退出时free131页，下一变量为真实分配窗口256→512MiB：同一冻结内核/240秒观察不变，SEC审计/guard、DarwinBoot实际分配、ADT和期望值必须一致，恢复映射仍限定单个L1跨度且不映射grant外页。39项host边界/混合合同拒绝通过，尚待QEMU和手机；之后再接独立稀疏APFS Data。


### 同日：512MiB实际分配QEMU资格与独立Data候选

内存候选经历的镜像检查失败和QEMU失败均保留，未上手机。QEMU初次512MiB实际基址含原内核0x7c000对齐偏移，跨越单L1恢复跨度，入口守卫拒绝；将模拟器窗口从同份FDT推导为bank+256MiB后，完整返回暴露ExactTables的128块历史限制。该限制按显式512MiB扩到256块，逐描述符检查仍保留；真实返回表通过原C检查器ASan/UBSan执行，修改一描述符被拒绝。185542Z QEMU全部39项通过；185720Z手机正在单变量512MiB观察，冻结kernel/240秒不变。

独立handset-data配置和构建入口已接入RamBlock、Data挂载与原var seed。复用原DarwinBoot PackedRAMDisk接口，将现有全新1GiB逻辑APFS seed无损打包为73840字节；不将逻辑容量视为物理驻留量。NativeLoad v3追加私有Data的CRC/精确装载范围及ADT位置，保留原TrustCache，独立检查两者不重叠、范围和树CRC，loader明确initrd路径。11项格式/装载布局/坏格式/缺placeholder拒绝通过。原UFS依然只读、Data持久store回调明确mode0。候选编译中，尚无手机可写Data结果。


185720Z已返回并普通重启清理：DarwinBoot分配/BootArgs与恢复快照中的real_phys_size同为536870912；原launchd main再次成立，1475次syscall、53签名对象，UFS3079885824字节、错误0。原tzinit17仍以30退出，故experiment_passed=false，不是完整checkpoint成功；内存扩展仅记录其分配/执行快照/恢复范围。空闲页数不能单独证明OOM，实际硬阻塞仍是原只读var。公开摘要native-memory512.json。Data独立候选190057Z内核887记录构建通过、预链接125177856字节、128MiB载荷生成通过；v20在前轮清理后继续资格，未提前上手机。


Data v20在主机资格阶段因8757248字节mutable备份超过旧8MiB拒绝，未构建新固件或上手机。host producer、固件与镜像检查器统一为有界12MiB，八个原区域和完整CRC/恢复不变；v21复用同一冻结内核/载荷/extent继续。实现与逐层验收见UniXNU-raphael/docs/HANDSET-DATA.zh-CN.md。


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
