用户最新偏好（2026-11-07）：自动完成启动/等待/日志与RGB画面回收，不再逐轮询问启动文字/进度条/黑屏状态；仅自动恢复失败且需要人工操作时提醒。

# UniXNU 手机桌面主线待办

本次更新：2026-11-04（北京时间），UFS连续日志已实机通过；032503Z离线KeyStore候选完整checkpoint/自动Android恢复和普通重启清理通过，MKB_INIT致命恢复请求已消失，显示clients/frames仍0；正在构建保留原上限的observer-bound候选。

前次核对：2026-11-04 02:26:02 +08:00（北京时间）。唯一补采候选180921Z临时启动接受，但665.449秒内无Android/原生回传，passed=false、xnu_executed=null。用户手动重启后，182112Z独立核查Android/root/新boot ID/无临时FDT通过，没有匹配原生记录。实验已停止，不重跑；最近正常原生成功仍为163215Z。

活动源码位于 WSL Ubuntu-24.04 的 /home/guo/work/raphael-fresh。本文件的主版本为该目录的 TODO.md，Windows 阅读副本为 D:/project/unixnu/todo.md。

## 更新约定

- 后续工作中，每完成一个小任务立即更新对应复选框，并补充证据路径和实际结果，再同步 Windows 副本；这是执行过程中的持续约定。
- 只有满足该条验收条件才打勾；源码、完整构建、QEMU、手机实测分别记录。失败、无回传和恢复成功均不能代替桌面验收。
- 若发现已完成结论失效，取消该项勾选并记录原因；新增阻塞拆成新的小任务。保留旧失败产物和历史条目。
- 每次实机只执行已有证据支持的单变量候选，写清预期、回传与恢复条件；未知镜像不原样重跑。保留脏工作树、私有输入及备份。
- **对齐UniXNU官方文档**：遵循 https://unixnu.com/zh/porting/bring-up 的7个阶段，阶段7（用户态）是当前主线目标。

## 当前现场

2026-11-04 实机连续日志通过：030111Z临时启动后人工恢复Android，自动提取191条有效4KiB记录、60664字节/917行、184条进度记录，dropped=0，无损坏尾块，counter递增、两侧保护块未变、新Android boot ID成立。日志完整保存至 SERVICE SNAPSHOT DONE; RETURNING；最后tick1831、root7/init4、syscalls7013、clients/frames0。原FDT完整checkpoint仍未通过，不将独立UFS日志改写为该轮passed。证据：evidence/private/ufs-console-log/20261104T024624Z/20261104T031141Z-automatic-return/report.json。

以下为前次现场记录，按历史保留。

最新临时启动 20261103T180921Z（北京时间11月4日02:09:21）为first-method补采候选。唯一补采候选180921Z临时启动接受，但665.449秒内无Android/原生回传，passed=false、xnu_executed=null。用户手动重启后，182112Z独立核查Android/root/新boot ID/无临时FDT通过，没有匹配原生记录。实验已停止，不重跑；最近正常原生成功仍为163215Z。当前没有运行中的手机实验或构建。

最新正常原生诊断成功为 20261102T163215Z：原 watchdogd 3 次方法调用、1 次 check-in；231.301 秒提前收尾并自动返回 Android。当前能力（分轮实测，不代表一次连续完整启动）：
- ✅ 存储与根卷：原APFS root/SystemOS挂载
- ✅ 用户态早期：原launchd main、SpringBoard进程已分别观察到  
- ❌ 阶段7完成标准：显示输出、持续首帧、基本交互**未达成**
- ⚠️ 关键指标：display_clients=0, frames=0 - 显示服务未真正提交帧

## 接手入口与本轮结论

| 项目 | 状态 / 证据 |
|---|---|
| 当前阶段 | 原用户态服务启动至显示首帧之间；服务根因未定 |
| 最近正常原生成功 | `evidence/private/android-return-run/20261104T032503Z/report.json`；离线KeyStore调用及MKB_INIT完成，clients=0、frames=0 |
| 最新手机尝试 | `evidence/private/android-return-run/20261104T032503Z/report.json`；整轮通过、自动返回，连续日志独立通过 |
| 独立人工恢复 | `evidence/private/android-manual-recovery/20261103T182112Z-service-spawn/report.json`；通过，不证明原生执行 |
| 五秒候选构建与检查 | 已完成；`artifacts/service-observation-build/20261103T164426.446041Z/candidate-review.json` 为执行前冻结审查 |
| 最新执行与恢复索引 | `artifacts/service-spawn-build/20261103T175023.518572Z/execution-result.json` |

构建脚本已实际执行成功，当前无需重复构建同一镜像。`candidate-pointers.json` 的 `handset_executed=false` 是构建时快照，不能用它覆盖后续165957Z实验记录。本轮180921Z已结束；182112Z为最新恢复核查。构建时handset_executed=false保持原状，后续执行以execution-result.json及原始报告为准。

## C. 显示服务启动与原生首帧输出（当前主线）

当前确认：080848Z独立UFS日志首次451帧提交/完成，现场见加载条后黑屏，未见桌面；SpringBoard已越过显示等待，现等LaunchServices数据库，lsd同步等待online-auth-agent及容器服务。原完整返回仍失败，独立帧证据另报。

- [x] **C01：复核完整进程记录与服务等待栈**
  - 163215Z 在 PID1..255 范围捕获68个进程，其中41个仍名为 xpcproxy；符号化文件的4项只是选定服务线程快照。
  - SpringBoard 的 CFPrefs 等待成立；该快照未见名为 cfprefsd/backboardd 的进程，不代表从未尝试启动。
- [x] **C02：读取本机实际 OS/SystemOS 的服务配置与文件**
  - 原 backboardd plist 为 RunAtLoad=true、KeepAlive=true、UserName=mobile，没有 Aqua/SessionType 限制。
  - 原 cfprefsd daemon 注册 MachServices；另一个 system job 有 System 会话及 feature flag 条件，不能混为一谈。
  - 原 OS 中两个二进制均存在且可执行；未据此宣称全部依赖或 XPC 服务就绪。
  - 161209Z 的匹配 nonce/CRC 恢复控制台实际出现 cfprefsd90/93、backboardd57；它仍是 panic 失败轮。
  - 证据：evidence/private/service-startup-audit/20261103T163155.476963Z/report.json；docs/SERVICE-STARTUP-20261104.zh-CN.md。
- [ ] **C02b：确定待启动/待回复的具体原因**
  - [x] C02b.1（11月4日）：完成两轮原始回传/CRC与等待栈对照；SpringBoard同步等待CFPrefs，keybagd同时存在direct等待及CFPrefsDaemon消息处理线程，不能以缺cfprefsd进程名断言服务未处理请求。41个xpcproxy均未采线程栈，根因仍未知。证据：evidence/private/service-wait-analysis/20261103T175347.538817Z/report.json。
  - [x] C02b.2：显式补采最多64个xpcproxy的单线程状态，沿用first-method marker1停点；8组实际C分支ASan/UBSan、14项解码拒收与4组旧解码兼容检查通过，两轮原始回传重解码与旧版/原报告一致。887记录完整内核构建、未定义0通过。证据：artifacts/service-spawn-host/20261103T175141.321700Z/report.json；artifacts/native-bootstrap-attempt/20261103T175023Z/report.json。
  - [x] C02b.3：补采候选预链接/128MiB载荷、恢复QEMU39项、单变量审查和唯一临时镜像已冻结；该构建门禁完成时Android只暂存新Payload，后续手机执行见C02b.4。证据：artifacts/service-spawn-build/20261103T175023.518572Z/candidate-review.json；docs/SERVICE-WAITS-20261104.zh-CN.md。首次漏带夹具参数的QEMU失败另行保留。
  - [x] C02b.3a：现场恢复确认和当轮完整前置核查通过；证据：artifacts/service-spawn-build/20261103T175023.518572Z/live-handset-preflight.json。
  - [ ] C02b.4：180921Z唯一补采候选665.449秒无Android/原生回传，passed=false、xnu_executed=null；未取得正常checkpoint或补采栈，不验收，不原样重跑。证据：evidence/private/android-return-run/20261103T180921Z/report.json。
  - [x] C02b.4a：用户人工重启后，182112Z独立核查Android/root/新boot ID/无临时FDT通过；无匹配原生回传，原失败报告哈希不变。证据：evidence/private/android-manual-recovery/20261103T182112Z-service-spawn/report.json。
  - [x] C02b.5：核对实际FAT配置、冻结源码哈希/编译Menu.obj和同源码QEMU菜单日志，确认timeout0在按键等待前直接返回诊断；画面先绘制，菜单残留不能定位手机停点。当前构建不含AdvancedLogDxe。证据：artifacts/service-spawn-build/20261103T175023.518572Z/menu-return-audit.json。
  - [x] C02b.6：从163215Z真实恢复内存读取到gc_initialized=1、gc_enabled=0、gc_graphics_boot=1、disableConsoleOutput=1，原生视频映射已存在。新增显式--native-console，复用原initialize_screen(kPETextScreen)，输出root/init/watchdog/display计数及捕获前后标记；887记录完整内核构建通过。证据：artifacts/native-bootstrap-attempt/20261104T022542Z/report.json；源码package/drivers/RaphaelNativeConsole.c。
  - [x] C02b.7（仅可见日志通道）：022942Z手机照片确认原生launchd Early boot complete、tick1931/root7/init4/syscalls6650；clients/frames0。随后黑屏，主机与额外读回均超时，人工重启回Android；原正常checkpoint仍未通过，照片不替代桌面。证据：evidence/private/android-return-run/20261104T022942Z/screen-observation.json。
  - [x] C02b.8：2026-11-04 实机连续日志通过：030111Z临时启动后人工恢复Android，自动提取191条有效4KiB记录、60664字节/917行、184条进度记录，dropped=0，无损坏尾块，counter递增、两侧保护块未变、新Android boot ID成立。日志完整保存至 SERVICE SNAPSHOT DONE; RETURNING；最后tick1831、root7/init4、syscalls7013、clients/frames0。原FDT完整checkpoint仍未通过，不将独立UFS日志改写为该轮passed。证据：evidence/private/ufs-console-log/20261104T024624Z/20261104T031141Z-automatic-return/report.json。
  - [x] C02b.9：连续日志实机读回后发现原MKB_INIT报告systembag缺失并请求恢复；源码确认手机profile此前禁止既有AppleKeyStoreState。现仅在显式handset诊断+易失Data下启用原固定组件，以现有owned display属性准入，记录实际AKS调用；主机边界检查和887记录完整内核通过，新日志分配、载荷、8项实际新旧内核策略检查、恢复QEMU39项（含KeyStore实际发布）和临时镜像均通过；032503Z整轮passed=true，nonce/完整checkpoint/自动Android返回和普通重启清理通过；原KeyStore stage2/opens2/calls4，原MKB_INIT正常DONE，FATAL/恢复请求消失。连续日志79块/48962字节、丢字0。clients/frames仍0，首帧未通过。证据：artifacts/handset-offline-aks/20261104T031813Z/experiment.json。
  - [ ] C02b.10：034350Z observer-bound唯一候选临时启动接受，665.169秒无自动Android回连；人工恢复后UFS读回210块/65721字节/1004行/202条进度、丢字0，最后tick2011/root7/init4/syscalls16490、clients5/frames0，已保存至SERVICE SNAPSHOT DONE; RETURNING。原完整checkpoint失败、xnu_executed=null；物理360秒到点及服务栈尚未回传，不能按正常checkpoint验收。证据：artifacts/desktop-offline-window/20261104T033507Z/execution-result.json。
  - [x] C02b.11：为034350Z恢复后无服务栈的实际缺口，将既有只读服务快照、显示/watchdog计数按完整分段写入现有UFS日志；真实032503Z内存输入、实际C写入函数ASan/UBSan及旧服务/异常解码器等价通过（13段/126284字节），截断不验收。新日志040526Z、887记录完整内核、预链接/载荷、恢复QEMU39项及临时镜像通过，040940Z唯一实验完整恢复超时，用户人工恢复Android；042224Z读回322块/286913字节/3454行、230条进度、dropped0、无损坏尾块及保护块变化，13段详细服务快照实机捕获成功。物理观察360046.222ms，watchdog6次check-in/0失败，显示clients/validations/kicks/frames均0，首异常为空。独立UFS快照通过；原完整checkpoint失败、xnu_executed=null保留，桌面未通过。本轮不改变服务条件或原观察预算。证据：artifacts/ufs-service-snapshot/20261104T040309Z/host-report.json。
  - [x] C02b.12：040940Z原系统UUID匹配完整符号解析完成：SpringBoard已越过CFPrefs，主线程同步等BKSDisplayGetMainScreenInfo；backboardd仍在dyld PrebuiltLoader::applyObjCFixups修复selector、未到main。无首异常。证据：详细快照目录services-symbolicated.json。
  - [ ] C02b.13：日志实际isssd=0，UFS-backed卷缺标准固态介质属性；仅补Device Characteristics/Medium Type=Solid State，沿用原预算与服务策略，并打印现有UFS读取计数；887记录完整内核、预链接/载荷、恢复QEMU39项和唯一临时镜像通过；新日志043043Z，043333Z完整恢复超时，人工恢复后325块/288724字节、丢字0且详细快照完整；OS/SystemOS实际isssd1，修正生效。显示clients/frames仍0，backboardd仍在dyld selector修复；前段读取约15MiB/s、服务阶段约5MiB/s。未实现首帧。
  - [x] C02b.14：依据043333Z实际读取吞吐，将native UFS连续读取合并为最多16KiB/4块命令；逐4KiB原认证与失败收尾保持，固态属性沿用。新增DMA5页和aligned mapper；extent主机37项、真实QEMU UFS模型45项、抽取实际controller read函数10项ASan/UBSan通过，覆盖非4KiB偏移/跨chunk/EOF/后块认证失败整批不发布；887记录内核与预链接/载荷通过，恢复QEMU39项、唯一临时镜像通过；045614Z完整恢复超时，原xnu_executed=null保持；人工回Android后371块/297594字节、dropped0、13段快照完整。实际早段约3.95块/命令、吞吐约21MiB/s，服务段约1.2块/命令、约5MiB/s；读取失败0，clients4/frames0，watchdog11次签到/0失败。只验收读取合并，首帧仍未实现。日志流式分配连续两次碎片化，fallocate预分配新文件取得连续512槽；旧分配保留。
  - 下一最小任务：读取原始watchdog超时描述、发送者及lsd/迁移服务线程，沿实际LaunchServices接收端等待推进桌面。
  - 已验收通道独立记录原控制台文本、实验身份、序号和阶段码；本轮服务候选沿用它，并使用新日志分配。连续日志与完整FDT checkpoint分别报告。
  - 本步产出：给出有原始证据支持的具体等待原因；证据不足时记录缺失字段及下一最小观测，C02b继续保持未勾选。C04服务就绪另验。当前不足以断言 XPC 失效或固定250-400秒启动延迟。
- [ ] **C03：独立短窗口服务观察候选**
  - [x] C03.1：恢复163215Z原 first-method 补丁；旧2500poll修改保存在 artifacts/service-startup-review/20261103T162807Z/before/，未删除。
  - [x] C03.2：新增显式 first-method-plus-5s 模式和独立64字节记录，以物理counter计时；原方法参数检查、20秒硬件、360秒观察及420秒pet上限不变。
  - [x] C03.2a：输入预检通过；独立解码正向/不足5秒/频率与模式错配等拒收检查、补丁应用检查通过。原 apfs 字段不覆盖。
  - [x] C03.3：构建入口实际执行通过（887条编译记录、未定义符号0）；使用成功基线显示源码显式构建，保留当前驱动修正。最终预链接 marker4/seconds5/root_limit3600、独立记录及策略检查通过。证据：artifacts/service-observation-build/20261103T164426.446041Z/candidate-pointers.json。
  - [x] C03.4：最终预链接、128MiB载荷、恢复QEMU39项及临时镜像构建通过；冻结对照确认固件/返回源码、ADT与Data/trust输入、内存布局及watchdog预算不变。证据：artifacts/service-observation-build/20261103T164426.446041Z/candidate-review.json。QEMU只到rootless40秒，不证明实际服务5秒窗口。
  - [ ] C03.5：用户确认现场恢复后执行165957Z唯一候选；临时启动接受，但11分钟回连等待结束仍无Android/原生记录，passed=false、xnu_executed=null。已停止，不原样重跑；独立人工恢复171923Z已核查Android/root/新boot ID/临时FDT清理通过，未找回原生记录，实验仍未通过。证据：evidence/private/android-return-run/20261103T165957Z/report.json。
  - [x] C03.5a：完成该轮人工恢复独立核查，原失败报告字节未改。证据：evidence/private/android-manual-recovery/20261103T171923Z-service-window-confirmed/report.json。
- [ ] **C04：同轮正常 checkpoint 验证服务与显示进展**
  - 原 cfprefsd 回复与 SpringBoard 等待栈发生可解释变化。
  - 原 backboardd 成功打开显示 client，之后验证实际 frame/retired 与现场画面。
- [x] C05a：原用户态合成器非空画面提交/完成链路，080848Z独立UFS日志451帧且现场加载条；不等于SpringBoard桌面。
- [ ] C05-C06：推进SpringBoard桌面首帧与持续显示。

原 C01/C02/C03 的“只有4进程”“Aqua会话阻止启动”“250-400秒根因已定位”结论已撤回，原文件与失败产物保留在本轮备份及历史 evidence 中。

  - [x] C02b.15：修复045614Z的确定采集缺陷：backboardd从PID57换为109后被先到的8个服务挤出快照。保持原8槽/线程/解码ABI，按服务优先级替换低优先级样本，清除旧进程映射与旧线程尾部；补原始proc_exit退出原因和周期VM计数，不改变原退出行为。3组实际选择器ASan/UBSan回放、3种退出格式、原8组捕获/14拒收/4解码回归通过，最终887记录内核/未定义0通过。仅本地主机验收，未生成或启动新手机镜像；BackBoard真实退出原因、黑屏和首帧仍待实机。按用户要求到此停止。证据：artifacts/service-capture-visibility/20261104T051314Z/。

  - [x] C02b.16：用户要求继续排查黑屏；将已验收的显示服务优先采集、原退出原因及VM计数编入新日志候选。887记录内核、预链接/载荷、39项恢复QEMU和新镜像通过；保留原显示策略、16KiB读取、512MiB及20/360/420秒预算，072550Z完整恢复超时，用户人工回Android；375条连续记录/305557字节、丢字0，13段快照完整。BackBoard57及120的退出均为OS_REASON_WATCHDOG/code1/status9；当前134进入窗口服务器并等待原DataMigration。SpringBoard27已到LaunchServices数据库等待。clients6/kicks2/frames0，无桌面。独立连续日志通过，原失败报告保留。证据：artifacts/desktop-service-visibility/20261104T072136Z/。

  - [x] C02b.17：原reason描述/终止发送者补采完成；887记录内核与39项恢复QEMU通过，074823Z临时启动后人工恢复Android。独立363条/298301字节连续日志、dropped0、详细快照完整。watchdogd52终止backboardd57：原描述为ping发送失败、516秒无成功check-in；重启的106已进入WindowServer并创建PUIProgressWindow，lsd在注册bundle/IconServices，SpringBoard仍等显示信息。clients5/frames0，无桌面；原失败/null报告保留。证据：artifacts/desktop-watchdog-details/20261104T074428Z/。

  - [x] C02b.18：仅移除独占UFS只读请求的全SMMU重扫，保留接管/写入准入、锁、认证及收尾；生产read与原DMA准入ASan/UBSan通过，887记录内核与39项恢复QEMU通过。080848Z自动恢复超时，人工回Android后独立388条/309796字节、dropped0；首次451次非空帧提交/完成、0拒收/传输错误；watchdog22签到/0失败，无服务退出记录。用户见加载条后黑屏；非桌面。小块阶段整体中位数4.99升至6.97MiB/s，服务活跃区间约9–10MiB/s。SpringBoard越过显示等待，现等LaunchServices数据库；lsd98实际等待online-auth-agent148和容器服务。证据：artifacts/desktop-session-gate/20261104T080600Z/comparison.json。

  - [x] C02b.19：接收端补采已完成。083013Z人工回Android后独立373条/303915字节、dropped0；clients5/frames0、watchdog18签到/0失败，无记录的BackBoard/SpringBoard退出。lsd101实际在签名/plist解析，容器服务处理请求，非固定online-auth死锁。RAM Data驻留156626944字节、writes1226/failures0，UFS服务段10–13MiB/s；没有桌面。证据：UniXNU-raphael/evidence/native-ls-receiver.json。

  - [x] C02b.20：首次全零写入空页优化及有限回归通过，887记录内核/39项恢复QEMU通过。085854Z实机独立376条/302872字节、dropped0；跳过225280零字节，驻留142708736字节，收益不足以解释黑屏。1非空帧/0传输错误、watchdog18签到/0失败，无记录服务退出；现场一帧进度条后黑屏。SpringBoard仍等LS，lsd仍扫描签名；WindowServer渲染线程在私有CPU ledger等待，不能凭单次快照称持续卡死。证据：UniXNU-raphael/evidence/native-ram-zero.json。

  - [x] C02b.21：显式720秒观察/780秒pet实机窗口完成，原20秒硬件阈值不变。092714Z人工回Android后独立731条/358933字节、dropped0，完整快照；实际720101.807ms、2107帧提交/完成、0拒收/清黑/传输错误，watchdog58签到/0失败，无记录服务退出。原完整checkpoint失败/null保留，现场加载条后黑屏，无桌面。原渲染线程仍运行且CPU ledger低于限额，不能归因为持续限流；SpringBoard仍等LS，lsd98当前同步等待IconServices缓存失效回复，iconservicesagen112未在旧八槽优先名单。证据：UniXNU-raphael/evidence/native-extended-service-window.json。

  - [x] C02b.22：IconServices接收端补采完成。095342Z人工回Android后独立724条/357275字节、dropped0、快照完整，实际720035.919ms、2349帧提交/完成、0拒收/清黑/传输错误，watchdog58签到/0失败，无记录服务退出。lsd继续原应用签名扫描，已越过此前IconServices同步等待；iconservicesagen111在ISStoreMapTable页面缺失/原throttle_lowpri_io，未观察到CoreImage故障或LS回调环。OS/SystemOS为isssd1，RAM Data仍isssd0；下一单变量修正Data介质属性。原完整checkpoint失败/null保持，现场加载条后黑屏，桌面未验收。证据：UniXNU-raphael/evidence/native-icon-receiver.json。

  - [x] C02b.23：RAM Data标准固态属性实机生效，102222Z的spec_open为isssd1。297条/81044字节、dropped0，UFS错误0；原watchdogd selector2提前请求panic，现场启动文字后自动重启。完整返回delta超过1MiB、原失败/null保留；独立7/8区CRC匹配证明panic来源，具体理由未恢复，未到计划服务快照。Android普通重启/root/FDT清理完成；无桌面。证据：UniXNU-raphael/evidence/native-data-ssd.json。

  - [x] C02b.24：原watchdogd panic理由连续日志通过。163051Z自动回Android；429条/98309字节/dropped0。UFS文本与独立CRC匹配的静态副本一致：CommCenter四次被重启后180秒未签到，backboardd等仍正常。原完整返回1MiB delta溢出，失败/null保持；原内存压力杀进程已记录。普通重启/root/FDT清理完成，无桌面。证据：UniXNU-raphael/evidence/native-watchdog-reason.json。

  - [x] C02b.25：CommCenter重点采样及日志回收完成。165251Z独立375条/305200字节/dropped0，详细快照与RETURNING齐全；2帧、显示错误0、watchdog18签到/0失败、未记panic。SpringBoard仍等LS数据库，lsd在原签名扫描，CommCenter主线程CFRunLoop且工作线程运行；未证明基带缺失或死锁。Android/root/临时属性清除已确认；原失败/null保持，无桌面。证据：UniXNU-raphael/evidence/native-commcenter-focus.json。

  - [x] C02b.26：704MiB内存合同及同360秒窗口对照观测完成。171336Z独立378条/314898字节/dropped0，初始VM180166页与704MiB一致；599帧/0显示错误、watchdog22签到/0失败、无记录pressure kill/panic；UFS约3.70GiB，低于512MiB的5.12GiB。SpringBoard仍等LS，lsd在原应用Info.plist扫描；完整原失败/null保留，Android/root/临时属性清除确认，现场黑屏，无桌面。证据：UniXNU-raphael/evidence/native-memory704.json。

  - [x] C02b.27：704MiB/720秒观察与日志分析完成；173412Z人工恢复后独立727条/358407字节/dropped0，720091ms、2299完成帧/0显示传输错误、watchdog55签到/0失败，无记录pressure kill/panic。SpringBoard仍等LS数据库，lsd99同步等MCM签名信息回复；容器64/92存在但未分配线程槽。原返回失败/null保留，Android/root/临时属性清除确认，现场黑屏，桌面未完成。证据：UniXNU-raphael/evidence/native-memory704-long.json。

  - [x] C02b.28：MCM接收端补采完成；180247Z独立727条/360463字节/dropped0、720104ms、2237完成帧/0传输错误、55签到/0失败，无记录pressure kill/panic。两个容器进程均采到：一个CFRunLoop，另一个执行SetDataProtection后的元数据创建；lsd98已越过签名同步等待，正在注册插件。SpringBoard仍等LS；Android/root/临时属性清除确认，原失败/null保留，现场黑屏，无桌面。证据：UniXNU-raphael/evidence/native-mcm-receiver.json。

  - [x] C02b.29：1800/1860秒冷启动合同及每120物理秒独立LS线程进度主机构建完成（最多16组，不占最终八槽）；704MiB与20秒硬件阈值保留。实际C计时/引用寿命/上限、watchdog边界/拒绝、旧日志兼容与新进度解码ASan/UBSan通过；内核、预链接/载荷、39项恢复QEMU及手机镜像结构检查通过。候选未上机、桌面验收仍未完成；按用户“构建完成之后停止”要求停止。证据：artifacts/desktop-ls-scan-window/20261104T182635Z/result.json。
  - [x] C02b.30：LS分段候选072851Z回收分析完成；297条/93412字节/dropped0，仅约361秒独立日志与两组LS采样；第一组lsd尚不存在，第二组lsd98线程612在原系统内容扫描。末尾457帧、UFS读取0失败；未记录panic/pressure kill，无最终快照。停止位置贴近第三次采样，具体中断操作未知，不能宣称完整30分钟或LS死锁。Android/root/新boot ID/临时属性清除已确认，原失败/null保留，现场加载条或黑屏，无桌面。证据：UniXNU-raphael/evidence/native-ls-scan-window.json。
  - [x] C02b.31：周期LS采样阶段持久标记已构建；入口、进程引用及每个线程采集前后均标记，采样在正常线程且进程锁释放后写入。实际C计时/引用/锁边界ASan/UBSan通过；887记录内核、预链接/载荷、39项恢复QEMU及手机镜像检查通过，704MiB、720/780秒。证据：artifacts/desktop-ls-capture-trace/20261105T081126Z/result.json。
  - [x] C02b.32：081841Z阶段标记回收324条/97865字节/dropped0，第三次采样前四线程完成，lsd98线程781进入采集后无返回标记；具体内部操作/阻塞或异常尚未知。约361秒日志、两组完整LS，无最终快照；现场启动文字后黑屏。Android/root/新boot ID/临时属性清除确认，原失败/null保留，无桌面。证据：UniXNU-raphael/evidence/native-ls-capture-trace.json。
  - [x] C02b.33：采样目标task改为原task_lock_try；忙时明确跳过用户栈而保留原始寄存器，记录task_lock_busy。实际C争用/引用/空pmap ASan/UBSan与旧/新解码通过；内核、预链接/载荷、39项恢复QEMU及镜像检查通过。704MiB、720/780秒不变；实机效果待验。证据：artifacts/desktop-ls-capture-trylock/20261105T084821Z/result.json。
  - [x] C02b.34：085206Z回收329条/101912字节/dropped0、361206ms、两组完整LS；第三次采样进入lsd98线程601后仍无返回，task try-lock未解决中断，不能认定task锁根因。末尾638帧、UFS失败0、无最终快照；现场进度条，未确认桌面。Android/root/新boot ID/临时属性清除已确认，原失败/null保留。证据：UniXNU-raphael/evidence/native-ls-capture-trylock.json。
  - [x] C02b.35：诊断用户栈改用固定XNU原pmap_try_lock和pmap_vtophys；持共享锁完成物理读，忙则跳过并记录pmap_lock_busy。实际helper争用/成功/未映射/授权边界ASan/UBSan与旧新解码通过；内核887记录、预链接/载荷、恢复QEMU39项及镜像通过。704MiB、720/780秒与原服务行为不变，实机效果待验。证据：artifacts/desktop-ls-capture-pmap-trylock/20261105T091721Z/result.json。
  - [x] C02b.36：092115Z回收321条/100972字节/dropped0、360922ms、两组完整LS；第三次lsd98线程599进入后仍无返回，pmap try-lock未解决中断，末尾438帧、UFS失败0、无最终快照，现场黑屏。Android发生system_server启动异常并RescueParty入recovery；一次正常ADB重启后boot_completed/root/新boot ID/临时属性清除确认，关联原因未知。原失败/null保留，无桌面。证据：UniXNU-raphael/evidence/native-ls-capture-pmap-trylock.json。
  - [x] C02b.37：修复诊断pmap/ledger引用配对；固定实际编译ARM wrapper复现原引用消耗，修正后2000次配对及争用/空pmap/空ledger ASan/UBSan通过。887记录内核、预链接/载荷、39项恢复QEMU与镜像通过；704MiB、720/780秒和原服务行为保持，实机效果待验。证据：artifacts/desktop-ls-capture-ledger-ref/20261105T093840Z/result.json。
  - [x] C02b.38：095332Z ledger修正版回收835条/444209字节/dropped0，五组LS采样和720079ms最终快照完整，越过此前第三组中断；2774帧/0传输错误、58签到/0失败、UFS失败0、无记录pressure kill/panic。LS持续从plist解析推进到插件注册与应用签名扫描，末尾等MCM查询；SpringBoard仍等LS。Android/root/新boot ID/临时属性清除确认，原失败/null保留，现场进度条，无桌面。证据：UniXNU-raphael/evidence/native-ls-ledger-reference.json。
  - [x] C02b.39：已验证ledger修正版的1800/1860秒候选构建完成；887记录内核、预链接/载荷、39项恢复QEMU、手机镜像检查通过，复用既有长窗口边界与ledger回归证据。704MiB、20秒硬件阈值与原服务/显示保持；实机待验。证据：artifacts/desktop-ls-ledger-long/20261105T101613Z/result.json。
  - [x] C02b.40：102009Z的30分钟观察已回收并分析：14组LS均完成；2048槽日志容量耗尽截断最终快照，已独立还原6个完整服务槽及显示/看门狗段。1800087ms、8912帧/0错误、163签到/0失败，SpringBoard26主线程仍等LS数据库；无记录panic/pressure kill。现场进度条一半多后黑屏。RescueParty后一次正常重启恢复Android/root/新boot ID/FDT清理；原失败/null保留，桌面未验收。证据：UniXNU-raphael/evidence/native-ls-ledger-long.json。
  - [x] C02b.41：16MiB连续日志与VFS实际只读计数候选构建完成；887记录内核、预链接/载荷、39项恢复QEMU及手机镜像检查通过，原704MiB/720秒与服务/显示保持。证据：artifacts/desktop-ls-vfs/20261105T110612Z/result.json。
  - [x] C02b.42：111028Z回收826条/442341字节/dropped0，五组LS与720097ms最终快照完整；63组实测desiredvnodes始终1024，243秒前后实际达到1024。namecache启用、最高1038/1126，未证明名字缓存饱和；LS474仍扫描/插件注册，SpringBoard26等LS。2488帧/0错误、55签到/0失败，无记录panic/pressure kill；Android/root/新boot ID/FDT清理确认，现场黑屏，无桌面。证据：UniXNU-raphael/evidence/native-vfs-cache.json。
  - [x] C02b.43：实际1024 vnode上限的单变量8192 ADT实现完成；原PE_get_default入口、仅新增一个32位属性、删除后同字节还原、watchdog/704MiB保持通过。真实transport qualifier已识别该内核策略，8192正例与两种不支持值/未知default拒绝通过；首次未识别策略的QEMU拒绝日志保留，未上手机。证据：artifacts/desktop-ls-vnode8192/20261105T113210Z/host-report.json。
  - [x] C02b.44：8192 vnode候选构建完成；887记录内核、预链接/载荷、39项恢复QEMU及最终手机镜像检查通过，704MiB/720秒/16MiB与原服务/显示保持。证据：artifacts/desktop-ls-vnode8192/20261105T113210Z/result.json。
  - [x] C02b.45：113744Z的8192 vnode对照完整回收831条/449257字节/dropped0；63组desired8192，实际vnodes5620、names5738/9011、回收884。五组LS与720095ms最终快照完整；SpringBoard27线程250仍等LS，lsd99线程483继续原应用本地化/目录扫描。2724帧/0传输错误、58签到/0失败，无记录panic/pressure kill；现场黑屏，Android/root/新boot ID/FDT清理确认。参数生效但未解决桌面，证据：UniXNU-raphael/evidence/native-vnode8192.json。
  - [x] C02b.46：沿8192/704MiB/720秒实现120秒一次的90×195 RGB缩略采集，附抽样framebuffer像素对照与UFS读/验证/交付耗时累计；显示功能沿冻结成功基线，仅增诊断。实际helper ASan/UBSan、PNG解码与截断处理、887记录内核/符号、预链接/载荷、QEMU39项和手机镜像检查通过。证据：artifacts/desktop-late-frame/20261105T120824Z/result.json。
  - [x] C02b.47：121119Z完整回收971条/894327字节/dropped0，五组LS与720039ms最终快照完整；4张后期RGB图均为黑底加载条，非黑采样55。一次framebuffer抽样差46像素，尚未确定写入者；2299帧/0错误，55签到/0失败。UFS累计elapsed读349.23秒/验证17.55秒/交付5.07秒，包含调度；BackBoard493累计346.44秒CPU，LS472仅2.41秒且仍扫描。Android/root/新boot ID/FDT清理完成，现场黑屏，无桌面。证据：UniXNU-raphael/evidence/native-late-frame.json。
  - [x] C02b.48：离线定位8192与1024最终快照，BackBoard帧提交线程分别累计约407/375秒CPU；原内核0xfffffff005791968经vtable+0x910调用slot290=kickSwapQueue，账本总量不等于纯拷贝耗时。隔离差异拷贝候选复用现有通用helper，首次全量/静态零写/64字节变化/行尾8字节/清屏后全量与边界ASan/UBSan通过；已另备保留标准交接和拷贝计时的隔离源码display-diff-handoff-source；尚未构建或上机，等C02b.50实测拷贝耗时和framebuffer一致性再选。证据：artifacts/native-bootstrap-attempt/display-diff-probe-source/rationale.json。
  - [x] C02b.49：首个有效图形提交前调用标准kPEReleaseScreen，关闭文字/内核启动图并交接framebuffer；UFS捕获入口仍在console suppression判断前。沿8192/704MiB/720秒，仅增只读拷贝耗时；887记录内核、预链接/载荷、39项恢复QEMU、最终镜像与13区记录通过，实机效果待验。证据：artifacts/desktop-console-handoff/20261105T123516Z/result.json。
  - [x] C02b.50：123830Z回收1022条/1011327字节/dropped0，五组LS与720006ms最终快照完整；console_released=1，五张225/347/467/587/707秒RGB图均为加载条（细部像素有变化），抽样framebuffer差异全0。2806帧/0传输错误，watchdog58签到/0失败，无记录panic/pressure kill。拷贝累计elapsed398.639秒、最大0.377秒，包含抢占；BackBoard512账本419.649秒CPU，LS649仅1.756秒并仍同步等容器查询。现场进度条，无桌面；Android/root/新boot ID/FDT清理完成。下一单变量复用差异拷贝helper，保留标准交接、8192/704MiB/720秒及计时。证据：UniXNU-raphael/evidence/native-console-handoff.json。
  - [x] C02b.51：标准交接基础上复用现有64字节差异拷贝helper；首帧全写、后续只写变化块、空白提交使shadow失效。保留逻辑display bytes、拷贝计时、8192/704MiB/720秒及原服务；复用C02b.48实际helper检查，887记录内核、预链接/载荷、恢复QEMU39项及最终镜像通过，实机效果待验。证据：artifacts/desktop-diff-handoff/20261105T130103Z/result.json。
  - [x] C02b.52：130408Z回收1018条/1014515字节/dropped0，五组LS与720021ms最终快照完整；4267帧/0错误，58签到/0失败，无记录panic/pressure kill。差异拷贝累计elapsed398.639降至366.571秒（约8%），最大0.377降至0.141秒；BackBoard提交线程仍400.070秒CPU，LS477仍等容器查询。五张后期RGB仍为加载条、抽样framebuffer差异全0；现场进度条，无桌面。Android/root/新boot ID/FDT清理完成。下一步用原显示刷新ABI限制软件提交频率，保留面板模式与原服务。证据：UniXNU-raphael/evidence/native-frame-diff.json。
  - [x] C02b.53：原显示slot301和原属性发布器接入显式2Hz软件提交周期（500ms/32.32），冻结面板模式/差异拷贝/8192/704MiB/720秒。实际生成vtable确认slot301归适配器，原发布器字节与虚调用检查、887记录内核/符号、预链接/载荷、QEMU39项及手机镜像通过；实机效果待验。证据：artifacts/desktop-software-refresh/20261105T133049Z/result.json。
  - [x] C02b.93：复核896MiB两组完整进程快照：后组136个同名服务PID已更换，仅SpringBoard/launchd/kernel_task保持原PID；逐个退出原因未知，显式Jetsam只归于有reason5的BackBoard。核对chronod真实调用selector为activitiesExceedingReducedPushBudget，最近导出符号偏移2424不能当作精确初始化函数；原CommCenter存在无baseband启动分支，未据此禁用服务或认定死锁。证据：artifacts/desktop-memory896/20261106T031531Z/interpretation.json、process-replacements.json。
  - [x] C02b.97：原locationd的CLMescalSigner初始化等待MIG1203；原fairplayd.A2实际MIG表覆盖1200..1203且1203处理器接受24字节请求，与调用匹配。600/1000秒均未采到fairplay进程，运行时接收端仍未知。证据：artifacts/desktop-memory1536/20261106T041054Z/fairplay-mig-handler.json。
  - [x] C02b.113：153706Z实机自动回Android；1459条/3261754字节/dropped0，360秒完整154进程618线程。14次原fairplay均以128位/32字节/有IV/加密0请求特殊AES selector2201，SoftwareAES在unsupported分支返回e00002c7；普通CBC未执行，真实原因已确认。MIG1203仍排launchd队列2；222帧、两张RGB采样差异0，末张已打开仍加载条，无桌面。下一步临时Data首桌面服务配置；原failed/null保留。证据：artifacts/desktop-fairplay-aes-trace/20261106T153228Z/interpretation.json。
  - [x] C02b.115：修正硬件狗已返回新Android且root/FDT无临时属性时仍强制再重启的冗余步骤；该分支跳过额外重启，cleanup_new_android_boot_id为null，原完整checkpoint接受式及常规恢复分支保持。实际判据1正/7反通过；155932Z硬件返回判据实机通过，未额外重启，完整checkpoint仍failed/null。证据：artifacts/desktop-services-profile/20261106T155431Z/clean-hardware-return-host.json。
  - [x] C02b.119：163425Z实机自动回Android；2605条/5277844字节/dropped0，720秒完整197进程973线程，CommCenter缺席、无watchdog panic/压力kill。MIG1203保持消失，原BackBoard/LS主线程到CFRunLoop；SB仍等BKS，迁移child263等CoreLocation、定位后台线程又同步等ActivityKit/SpringBoard/BLS/IDS，互等因果待验。977帧/五张RGB差异0，末张已打开仍加载条，无桌面；原failed/null保留。下一候选只再停用locationd。证据：artifacts/desktop-no-commcenter/20261106T163033Z/interpretation.json。
  - [x] C02b.131：固定Xiaomi源码确认GT9889走SE19/I2C0x5d、Normandy帧协议及配置文件提供寄存器；独立事件解码/两段读取/应答实现已通过ASan/UBSan主机测试，覆盖按下移动抬起、ID重排、十点、校验、边界及读写失败。尚未连接实机总线/HID，不标记触摸可用。证据：artifacts/touch-driver/20261106T183500Z/。
  - [x] C02b.130：180944Z官方skip-setup实机用户照片显示原生日期/4:17时钟锁屏，已越过你好欢迎UI；用户确认上滑无响应，原生触摸未可用。无图标/Dock桌面，当前唯一30分钟采集继续。证据：artifacts/desktop-skip-setup/20261106T175720Z/native-lockscreen-observation.json。
  - [x] C02b.129：本轮离线全进程符号化按原PC/slide复用相同解析结果，减少上轮约4分钟分析中的重复查符号；语法通过，正在运行的手机镜像不变。证据：artifacts/desktop-skip-setup/20261106T175720Z/analysis-cache.json。
  - [ ] C02b.128：官方跳过首次设置及保持亮屏候选唯一临时启动接受；等待600/1000/1800秒完整进程、原主屏幕、显示提交和自动Android回收。证据：artifacts/desktop-skip-setup/20261106T175720Z/experiment.json。
  - [x] C02b.127：官方skip-setup/no-auto-dim独立种子候选完成887记录内核/预链接/载荷、39项恢复QEMU及手机镜像；保留1536MiB/32MiB/2Hz与1800/1860秒合同，其余内核参数相同。待实机确认原主屏幕，不宣称桌面。证据：artifacts/desktop-skip-setup/20261106T175720Z/build-result.json。
  - [x] C02b.126：确认原ForceNoBuddy受os_variant_has_internal_ui门控，不采用。按本地上游21H461官方skip-setup及no-auto-dim五组偏好创建独立临时Data种子，保留原种子/ADT/服务/显示/1800秒合同；plist回读和原键保留通过。当前Hello轮仍运行，新候选未构建/未启动。证据：artifacts/desktop-skip-setup/20261106T175720Z/seed-review.json。
  - [x] C02b.125：北京时间2026-11-07约01:50，172949Z长窗口实机用户明确报告苹果“你好”欢迎界面；首次越过进度条进入原生首次设置UI。用户后续确认一直停在初始页，欢迎UI超过60秒由现场报告成立；最终UFS-RGB仍待回收，D01桌面保持未完成，不将欢迎页等同桌面。证据：artifacts/desktop-no-locationd-long/20261106T172309Z/native-hello-observation.json。
  - [x] C02b.124：原SpringBoard.migrator相对方法表/三个实机返回PC一致定位到performSystemAppMigrationRecreating及performMigration；原dispatch_time常量300000000000ns、semaphore定时等待，回调原生signal。仅离线调用定位，不等于已超时或迁移成功；30分钟轮次继续观察。证据：artifacts/desktop-no-locationd/20261106T165808Z/migration-timeout-analysis.json。 原trap保存参数按固定ABI解码为299s+999996771ns，与300秒原期限吻合。
  - [x] C02b.123：172949Z长窗口已自动回Android，回收6710条/13949575字节/dropped0；600秒183进程883线程、1000秒209进程1092线程、1800秒189进程655线程均完整。SpringBoard27在1005秒进入原SBDashBoardSetupViewController欢迎文字动画，最终进入UIApplication事件循环，已越过原BKS签到等待；用户两次报告你好欢迎页且持续超过60秒。2698帧、13张RGB采样framebuffer差异0，实际查看低分辨率样本为深灰欢迎背景和细小元素，不能独立读出欢迎文字；无图标桌面。原watchdog165次签到/0失败，无记录panic/压力kill。Android/root/新boot ID/临时FDT清理成立；原完整failed/null保持。下一候选采用官方21H461 skip-setup及no-auto-dim临时Data偏好，已完成887记录内核、39项恢复QEMU和手机镜像。证据：artifacts/desktop-no-locationd-long/20261106T172309Z/interpretation.json。
  - [x] C02b.122：同无定位服务配置1800/1860秒候选构建通过；原seed/其余内核参数/1536MiB/32MiB/2Hz保持，其他ADT逐字节还原。887记录内核、预链接/载荷/恢复QEMU39项/临时镜像通过；待600/1000/1800秒迁移快照与桌面。证据：artifacts/desktop-no-locationd-long/20261106T172309Z/build-result.json。
  - [x] C02b.121：170225Z自动回Android，2717条/5552176字节/dropped0，720秒完整199进程1040线程；locationd/CommCenter缺席，无记录watchdog panic/压力kill。迁移child248不再有CoreLocation迁移栈，thread2258在原SplashBoard/ImageIO/libz PNG编码，SB仍等BKS；单样本不等于进展或死锁。851帧/五张RGB差异0、末张实际查看仍进度条，无桌面，原failed/null保持。下一步同配置原1800/1860秒分段观察。证据：artifacts/desktop-no-locationd/20261106T165808Z/interpretation.json。
  - [x] C02b.120：首桌面配置仅再停用com.apple.locationd候选构建通过；原watchdogd/先前fairplay-adid-CommCenter配置/其余seed及原OS保持，无伪造回复。887记录内核/预链接/载荷/恢复QEMU39项/手机镜像通过；1536MiB/32MiB/720/780秒/硬件狗保持，待实机检验原watchdog及桌面。证据：artifacts/desktop-no-locationd/20261106T165808Z/build-result.json。
  - [x] C02b.118：首桌面配置仅再停用com.apple.CommCenter候选构建通过；原watchdogd/先前fairplay-adid配置/其余seed及原OS保持，无伪造回复。887记录内核/预链接/载荷/恢复QEMU39项/手机镜像通过；1536MiB/32MiB/720/780秒/硬件狗保持，待实机检验原watchdog及桌面。证据：artifacts/desktop-no-commcenter/20261106T163033Z/build-result.json。
  - [x] C02b.117：修复读回解码器因一个可选ALLPROC段中断而丢弃此前全部完整段；原始日志保持、末段不补写，整体captured=false，独立命名服务及170个完整进程可读，ALLPROC_0171_000排除。此前完整冻结快照新旧解码完全相同，无新增手机实验。证据：artifacts/desktop-services-profile/20261106T155431Z/prefix-recovery-checks.json。
  - [x] C02b.116：155932Z实机自动回Android；2387条/4712675字节/dropped0，720秒命名服务完整，但原watchdogd因CommCenter两次诱导重启后180秒未签到panic，末ALLPROC_0171_000中断、整体不完整；读回恢复170进程840线程。无fairplay/AES启动，MIG1203消失、locationd已到CFRunLoop；SB仍等BKS，迁移及CFPrefs尚未完成。871帧/五张RGB差异0，末张已打开仍加载条，无桌面。干净硬件返回已实际跳过额外Android重启，原failed/null保留；下一候选仅再停用CommCenter。证据：artifacts/desktop-services-profile/20261106T155431Z/interpretation.json。
  - [x] C02b.114：首桌面临时Data配置构建通过；原seed全部条目/字节保持，仅追加root0644原launchd disabled.plist停用fairplayd.A2/adid，原OS/SystemOS和特殊AES拒绝保持，无伪造服务回复。完整887记录内核/预链接/载荷/恢复QEMU39项/手机镜像通过；1536MiB/32MiB/720/780秒/硬件狗，实际override/迁移/桌面待实机。证据：artifacts/desktop-services-profile/20261106T155431Z/build-result.json。
  - [x] C02b.112：SoftwareAES入口及八个原返回点的fairplay专用非密钥参数诊断构建通过；恢复原源码逐字节相同，原返回/回调和原FairPlay驱动保持。完整内核887记录、预链接/载荷、恢复QEMU39项及手机镜像通过；1536MiB/32MiB/360/420秒/原服务/硬件狗，待实机AES原错误。证据：artifacts/desktop-fairplay-aes-trace/20261106T153228Z/build-result.json。
  - [x] C02b.110：原FairPlayIOKit显式接入的实际预链接成功，全部原执行字节保持、26种导出addend保留；155处固定内联数据分类，原函数测试拒绝fallthrough及新增直接入边。间接流尚未证明，手机候选构建中；未宣称驱动运行成功。证据：artifacts/desktop-original-fairplay/20261106T062720Z/driver-host-checks.json。
  - [x] C02b.111：063216Z实机自动回Android；1464条/3255897字节/dropped0，360秒完整151进程619线程。原FairPlay的16次匹配/迭代/open全部成功，随后AES helper第233行将非零AES返回转为EINVAL(-22)，16次原fairplay正常退出。MIG1203仍排launchd、队列2；261帧/两张RGB采样差异0，末张已打开仍加载条，无记录panic/压力kill，无桌面。原failed/null保留；下一步AES原错误/非密钥参数定位。证据：artifacts/desktop-original-fairplay/20261106T062720Z/interpretation.json。
  - [x] C02b.109：原FairPlayIOKit显式接入候选构建通过；仅增加该原组件、原执行字节保持、26种导出addend保留，完整内核887记录/预链接/载荷/恢复QEMU39项及手机镜像通过。1536MiB/32MiB日志/原服务/硬件狗保持，以360/420秒验证匹配/open/MIG1203；尚无手机驱动或桌面证据。证据：artifacts/desktop-original-fairplay/20261106T062720Z/build-result.json。
  - [x] C02b.108：离线准备既有360/420秒早期依赖采集合同，20秒硬件阈值和其余ADT完全保持；后续编译必须同时使用observer-budget-ms420000。当前720秒实机未改动、未重复启动；新短窗镜像尚未构建。证据：artifacts/desktop-fairplay-iokit/20261106T060244Z/next-short-budget.json。
  - [x] C02b.106：060806Z实机自动回Android；2531条/5112724字节/dropped0，720秒完整195进程934线程。原fairplay51次匹配com_apple_driver_FairPlayIOKit均无迭代器，随即正常退出；当前未选入该原驱动，启动依赖缺口已确认。921帧、五张采样framebuffer差异0，末张已打开仍加载条；无记录panic/压力kill。原failed/null保留，无桌面；下一步同版本原驱动接入。证据：artifacts/desktop-fairplay-iokit/20261106T060244Z/interpretation.json。
  - [x] C02b.107：离线原FairPlayIOKit预链接原型生成；155处精确原始word均在无条件跳转后，选入模块无直接引用且重定位表无指向，26种符号addend保留、所有原可执行字节未改。间接可达性未证明，原型boot_eligible=false、未上机；当前手机仍是原IOKit返回追踪候选。证据：artifacts/desktop-fairplay-iokit/20261106T060244Z/fairplay-prototype-result.json。
  - [x] C02b.105：原fairplay的IOKit匹配类/迭代结果/open原返回追踪；移除新增观察后原IOUserClient函数语句逐字节一致，原调用次数保持。完整内核887记录、预链接/载荷、恢复QEMU39项与手机镜像通过，1536MiB/32MiB/720秒及原服务不变；实际失败依赖待实机。证据：artifacts/desktop-fairplay-iokit/20261106T060244Z/build-result.json。
  - [x] C02b.104：核对原fairplayd.A2为KeepAlive且无Disabled/会话限制，原临时Data种子仅含launchd目录、无覆盖文件；上一轮1800秒无残留xpcproxy。这不证明作业被launchd接受或执行，实际启动/退出原因等待当前IPC实机。证据：artifacts/desktop-ipc-peer/20261106T051358Z/fairplay-startup-inputs.json。
  - [x] C02b.103：离线穷举原FairPlayIOKit的4146个PC-relative编码，155个指向模块外，其中154个紧随无条件间接跳转、1个紧随无条件直接跳转，均无直接PC-relative入边；88个目标不在原kernelcache任何segment。支持混淆填充候选，但间接可达性未证明，未绕过emitter或生成运行镜像，等待实机IPC/退出原因。证据：artifacts/desktop-ipc-peer/20261106T051358Z/fairplay-relative-inventory.json。
  - [x] C02b.101：IPC接收端诊断新日志/完整内核887记录/预链接/载荷/恢复QEMU39项/手机镜像通过；1536MiB、32MiB日志、720/780秒合同、原服务及硬件狗保持，等待实机端口身份与桌面。证据：artifacts/desktop-ipc-peer/20261106T051358Z/build-result.json。
  - [x] C02b.102：053927Z的IPC版实机自动回Android；2428条/4825634字节/dropped0，720秒完整快照191进程/865线程、截断0。229个IPC均匹配mach_msg2 PC；locationd62/785的MIG1203目的端口属于launchd1且队列4条，回复端口不匹配故不归因；原fairplayd.A2实际51次正常status0退出，无活跃实例；lockdownd/商店同类请求也等launchd。941帧/5张RGB仍加载条且framebuffer差异0，末张已打开，无桌面。Android/root/新boot ID/FDT清理通过，原failed/null保留。证据：artifacts/desktop-ipc-peer/20261106T051358Z/interpretation.json。
  - [x] C02b.100：接收端候选离线恢复既有720/780秒合同；实际ADT除watchdog合同外完全相同，保留1536MiB/32MiB日志/原服务/硬件狗，后续按最终完整进程快照定位接收端。IPC记录同时保存回复端口名，要求与实际receive参数及mach_msg2 PC匹配后才解释。原配方编译及实际18项helper/解码复验通过，手机仍运行前轮。证据：artifacts/desktop-ipc-peer/20261106T051358Z/budget-result.json。
  - [x] C02b.99：确认原FairPlayIOKit为IOResources provider且当前未预链接；26种原导出符号addend可全部重绑定，但原混淆代码含未确认的外部PC-relative分支，完整导入失败，未生成运行镜像。原预链接源码已保持原行为，试验和原型保留；缺驱动尚非已证实根因，等待IPC接收端证据。证据：artifacts/desktop-ipc-peer/20261106T051358Z/fairplay-import-result.json。
  - [x] C02b.98：在原128-word线程记录空位增加IPC目的接收PID/特殊回复send-once复制出PID，均try-lock并显式标记busy；补原fairplay/location退出原因。原OSFMK/BSD两个-Werror对象、实际helper18项ASan/UBSan和18解码/3拒绝通过。尚未上机，不代表问题已修复。证据：artifacts/desktop-ipc-peer/20261106T051358Z/host-result.json、UniXNU-raphael/evidence/native-ipc-peer.json。
  - [x] C02b.96：045854Z的32MiB实机自动回Android；6290条/12905853字节/dropped0，1800093ms末尾快照完整，600/1000/1800秒190/211/212进程、880/763/769线程且截断0。原BackBoard57/LS98/CommCenter83保留，SpringBoard仍等BKS，迁移等CoreLocation，locationd62/785仍等MIG1203；三组均无fairplay，实际接收端待IPC采样。2975帧、13张RGB仍加载条，末张已打开，framebuffer差异0；无记录panic/压力kill。Android/root/新boot ID/FDT清理通过，原failed/null保留，无桌面。证据：artifacts/desktop-log32/20261106T045519Z/interpretation.json。
  - [x] C02b.95：32MiB新日志完整内核/预链接/载荷/手机临时镜像及高PA多L1恢复QEMU39项通过；1536MiB/原服务/采样和硬件狗保持，桌面待实机。证据：artifacts/desktop-log32/20261106T045519Z/build-result.json。
  - [x] C02b.94：实际日志在4096槽耗尽，现扩32MiB/8192槽，连通CLI、顺序追加策略和实际传输上限；8192次实际C++追加ASan/UBSan、UFS模型90项/进程重启47项和记录/布局检查通过，真实32MiB首尾写入/读取及越界拒绝通过。手机效果待验。证据：artifacts/desktop-log32/20261106T045519Z/host-result.json。
  - [x] C02b.92：1536MiB实机自动回Android；4096条/8622633字节/dropped0，日志1137.068秒后槽位用尽。600/1000秒188进程867线程及211进程772线程均完整，截断0；同名服务更换PID由896MiB的136降至4，原BackBoard57/LS98/CommCenter83保留。1000秒SpringBoard仍等BKS签到，BackBoard等迁移，迁移已到CoreLocation同步请求。1585帧、8张RGB抽样仍加载条且framebuffer差异0；无已记录服务退出/panic，但末尾未知。Android/root/新boot ID/临时属性清理通过，原failed/null保留，无桌面。下一步保持1536MiB与原服务，仅扩32MiB日志补全后期证据。证据：artifacts/desktop-memory1536/20261106T041054Z/interpretation.json、memory-comparison.json。
  - [x] C02b.91：1536MiB新日志、完整内核/预链接/载荷及临时手机镜像构建通过；高PA多L1恢复QEMU39项通过。保留原服务和硬件狗返回，桌面仍待实机。证据：artifacts/desktop-memory1536/20261106T041054Z/build-result.json。
  - [x] C02b.90：完成1536MiB多L1恢复映射及全链路预算接线；实际固件C函数ASan/UBSan与独立Python逐页翻译比对、原四档transition逐字节相同、20组bootstrap及60组篡改拒绝通过。原XNU多L2分配逻辑未改；新内存实机效果待验。证据：artifacts/desktop-memory1536/20261106T041054Z/host-regression.json。
  - [x] C02b.89：20261106T034001Z 自动回安卓成功（1253.964秒），无需人工或fastboot恢复；首次bootreason为bootloader，不能单凭此确定硬件狗分支。UFS3548条/7420979字节/dropped0，跨度1006.029秒；600秒174进程795线程、1000秒143进程644线程均完整。SpringBoard已越过BKS签到，1000秒等ChronoServices订阅回复；699.818秒BackBoard被proc-thrashing Jetsam回收，末尾原watchdogd因CommCenter180秒未签到panic。1204帧、六张后期RGB仍加载条且framebuffer抽样差异0，无桌面。Android/root/新boot ID及临时属性清理通过，原报告failed/null保留。下一步扩展本地多L1恢复映射，测试1536MiB；不改原服务。证据：artifacts/desktop-memory896/20261106T031531Z/interpretation.json。
  - [x] C02b.88：896MiB新日志/内核/载荷/手机镜像完整构建通过；本次高PA恢复QEMU39项通过，明确启用硬件狗返回（不尝试旧完整回传）。真实自动复位和桌面待验。证据：artifacts/desktop-memory896/20261106T031531Z/build-result.json。
  - [x] C02b.87：硬件狗返回选择为TRUE的完整手机镜像编译/结构通过；复用当前704MiB输入仅作构建验证，旧日志不可再次上机，未启动。896MiB及真实自动复位仍待验。证据：artifacts/desktop-memory896/20261106T031531Z/hardware-return-build.json。
  - [x] C02b.86：按用户要求增加显式硬件狗复位返回模式，进入固件回传时先保留/重新装载原已验证20/21秒阈值并停止喂狗；绕开过早关闭硬件狗后的恢复卡死窗口。实际C函数opt-in/寄存器顺序/停止喂狗ASan/UBSan通过，硬件效果待下轮手机。证据：artifacts/desktop-memory896/20261106T031531Z/hardware-return-host.json。
  - [x] C02b.85：896MiB在4GiB以上物理区间的真实恢复QEMU39项全部通过；首个原内核、MMU/pmap和恢复路径通过，尚未手机构建/执行，无桌面证明。证据：artifacts/native-staging-qemu/20261106T031644.879302Z-s267tm0u/report.json。
  - [x] C02b.84：896MiB显式预算源码接入，沿用原审计较大区间及单L1恢复；旧256/512/704选择保持，实际serializer覆盖原/极限偏移，未支持960拒绝。高PA QEMU及实机仍待验，不改变当前运行中的704MiB试验。证据：artifacts/desktop-memory896/20261106T031531Z/host-regression.json。
  - [x] C02b.83：修正离线退出解析器按十六进制读取原status与reason_flags；用前轮实际原始日志复验，完整识别SpringBoard ffffff00及3次BackBoard退出。仅分析器变更，无镜像/手机操作。证据：artifacts/desktop-aks-wrap/20261106T025300Z/exit-parser-regression/regression.json。
  - [x] C02b.82：软件密钥封装实机回收2219条/3843504字节/dropped0，AKS10成功7次、11成功2次；600秒131进程657线程完整，LS仍推进且采到vm_page_wait。日志916.330秒终止，未记录panic/服务退出，无最终快照；人工回Android/root/新boot ID/临时属性清理通过，加载条后黑屏，无桌面。证据：artifacts/desktop-aks-wrap/20261106T025300Z/interpretation.json。
  - [x] C02b.81：软件密钥封装候选完整内核/预链接/载荷、39恢复QEMU及手机镜像完成；冻结辅助记录确认实际选中8c70daf和software_wrapping=true，板级身份回调已链接。704MiB/可分页Data/原服务/显示/窗口保持；效果待实机。证据：artifacts/desktop-aks-wrap/20261106T025300Z/host-result.json。
  - [x] C02b.80：针对当前12次AKS selector10不支持，显式选择官方AppleKeyStoreState8c70daf软件封装；板级复用既有16字节私有ADT UUID，原pin/服务/显示/704MiB保持。上游实际C++封装格式/生命周期及实际板级回调ASan/UBSan通过；完整构建和实机效果待验。证据：artifacts/desktop-aks-wrap/20261106T025300Z/host-regression.json。
  - [x] C02b.79：20261106T022413Z自动回Android，3403条/6457475字节/dropped0；600/1000秒两组127进程573线程及130进程624线程完整，截断0，耗时1.498/1.425秒。LS98/477从应用/插件扫描推进至OpenStaging/用户会话，CPU28.02→75.32秒；SpringBoard末次等BKS签到。BackBoard57明确namespace1/code4为VM页不足Jetsam，之后两个重启实例被watchdog终止；原watchdogd本轮因media/audio缺签到panic，CommCenter末次仍正常。末尾1109帧，六张后期采样framebuffer差异0，已查看末张仍为加载条。12次AKS selector10不支持。Android完成/root/新boot ID/FDT清理通过，原failed/null保留；用户末次进度条、最终原生画面未知，无桌面。下一步只接入官方软件密钥封装，保持704MiB/可分页Data/原服务/显示。 证据：UniXNU-raphael/evidence/native-early-processes.json。
  - [x] C02b.78：600/1000秒两次独立全进程快照候选构建完成；实际C/引用配对/sanitizer与缺final解码通过，13区记录/布局、完整内核/预链接/载荷、39项恢复QEMU及手机镜像通过。保留可分页Data、原服务/看门狗、704MiB、1800秒观察与2Hz显示；下一步临时启动以捕获原panic前等待链，无桌面验收。证据：artifacts/desktop-early-processes/20261106T022045Z/host-result.json。
  - [x] C02b.77：复用原allproc/线程采集，在600与1000秒独立命名快照，1800秒最终快照保留；保持可分页Data、原服务/看门狗/704MiB及显示。实际C调度/引用配对/0至513线程与PID1024、ASan/UBSan、缺final/第二组中断及旧日志兼容通过。完整构建中，手机效果未验。证据：artifacts/desktop-early-processes/20261106T022045Z/host-regression.json。
  - [x] C02b.76a：本轮离线分析器保留Data分配量/I/O时序及全部服务退出原因，早退缺最终快照仍可回收；上轮实际日志解析确认236015616字节和BackBoard namespace1/code4，语法通过。仅分析器修改，当前实机镜像不变。证据：artifacts/desktop-pageable-data/20261105T182953Z/analyze-ls-timeline.py。
  - [x] C02b.76b：修复缺最终服务快照时丢弃已完整写入LS路径的解码分支；上轮实际提前panic日志重解码保留8组LS与8组路径，captured仍为false。当前镜像不变，便于本轮直接读取实际路径候选。证据：artifacts/desktop-pageable-data/20261105T182953Z/parent-partial-paths.json。
  - [x] C02b.76：183513Z回收1595条/1299787字节/dropped0、10组LS，日志跨度1229.432秒。Data allocated223297536且pageable1、I/O错误0；末次wired74764对上轮127816（时点不同，不是精确驻留测量）。原media/audio/thermal均恢复签到，原watchdogd本轮因CommCenter缺签到panic；BackBoard57退出namespace1/code5为process-thrashing Jetsam，仍有内存压力。1205帧，8张后期RGB仍加载条且抽样framebuffer差异0。后期PID0只说明PID256以下未找到LS，不证明LS消失；无最终全进程/异常快照。自动回Android/root/新boot ID/FDT清理通过，原failed/null保留，无桌面。下一步仅增加600/1000秒全进程快照，继续原窗口。 证据：UniXNU-raphael/evidence/native-pageable-data.json。
  - [x] C02b.75：Data三个页分配点/两个释放循环改用原pageable API；指针表/暂存区常驻。现有4000次差分稀疏I/O及错误路径ASan/UBSan通过，13区记录/布局、完整内核、预链接/载荷、39恢复QEMU及手机镜像通过。实机内存和桌面效果待验。证据：artifacts/desktop-pageable-data/20261105T182953Z/host-result.json。
  - [x] C02b.74：174751Z长窗口提前被原watchdogd请求panic终止：1271条/848080字节/dropped0、8组LS，日志跨度1025.311秒。BackBoard57退出namespace1/code4已由固定XNU确认VM页不足Jetsam；临时Data占236015616字节常驻。四张RGB仍加载条，采样与framebuffer一致，末尾782帧；无最终快照，不能编造末尾服务/签到。configd末次仍成功签到；原失败/null保留。自动回Android完成/root/新boot ID/临时FDT清理确认，无桌面。下一步只将CPU拷贝的Data页换为原IOMallocPageableZero/IOFreePageable，使冷页可被原VM压缩；所有权和服务策略保持。 证据：UniXNU-raphael/evidence/native-platform-long.json。
  - [x] C02b.73：当前2Hz/全进程/平台UUID修复版1800/1860秒候选完成887记录完整内核、新日志绑定、预链接/载荷、39项恢复QEMU与最终手机镜像，其他行为保持，待实机。证据：artifacts/desktop-platform-long/20261105T174010Z/host-result.json。
  - [x] C02b.72：平台UUID已实机修复后，仅将现有720/780秒合同扩到既有v6的1800/1860秒，硬件20秒保持；其他ADT逐字节还原、私有身份与服务/显示源码保留。当前LS在720秒仍有原配置解析进展；旧30分钟属于旧显示实现，不能代替本轮。完整构建中。证据：artifacts/desktop-platform-long/20261105T174010Z/host-regression.json。
  - [x] C02b.71：171504Z回收1888条/3404681字节/dropped0；120进程568线程、截断0，末尾采集1.472秒。configd37/320已越过gethostuuid进入原CFRunLoop，并新增配置线程；lockdownd71不再等PreferencesMonitor，平台UUID缺口实机修复成立。894帧/0传输错误、55签到/0失败，四张RGB仍加载条；无记录panic/pressure kill。LS478在606及720秒持续解析原MIBundle配置，SpringBoard与迁移等LS；不称固定死锁。Android/root/新boot ID/FDT清理通过；原失败/null保留，现场末次确认进度条，最终黑屏状态未确认，无桌面。 证据：UniXNU-raphael/evidence/native-platform-uuid.json。
  - [x] C02b.70：平台UUID候选完成887记录完整内核、新日志绑定、预链接/载荷、39项恢复QEMU及手机镜像。首次复用旧内核与新日志绑定不一致被检查拒绝，失败记录保留，重编后通过。功能变量仅UUID输入；704MiB/8192 vnode/720秒/全进程诊断及显示保持，待实机。证据：artifacts/desktop-platform-uuid/20261105T170854Z/host-result.json。
  - [x] C02b.69：补齐现有原优先平台身份适配所缺的手机/chosen/unixnu-platform-uuid；私有UUIDv4生成后稳定保留，不冒充Apple或观察到的硬件标识。基线生成器及精确传输元数据比较同步；除该属性外ADT逐字节还原、稳定身份和三项坏输入拒绝通过。服务/显示内核源码不变，新日志分配需重新编译绑定；准备新载荷/QEMU/手机镜像，实机效果待验。证据：artifacts/desktop-platform-uuid/20261105T170854Z/host-regression.json。
  - [x] C02b.68：全进程回收分析器已准备，汇总所有进程线程等待栈、CPU账本、截断与采样耗时，并保留原PC/共享缓存slide；已修复回收脚本继承上一候选路径的问题，改为脚本所在候选。仅离线编排修正，不改变正在执行的镜像。证据：artifacts/desktop-all-services/20261105T163332Z/analyze-all-result.py。
  - [x] C02b.67：164135Z回收2043条/3843564字节/dropped0；125进程648线程全部采到、截断0，末尾广域采集1.546秒。917帧/0传输错误、watchdog58签到/0失败；五张RGB仍加载条，抽样与framebuffer一致，无记录panic/pressure kill。LS484.879秒发送数据库重建通知、605.709秒原数据库等待线程已返回工作队列；迁移254推进到IXPlaceholder图标承诺，installcoordinat290等installd238扫描原framework。确定configd37/320在gethostuuid→IOBSDGetPlatformUUID等缺失IOPlatformUUID，lockdownd71/348等SCPreferences通知；不称这已是桌面唯一原因。Android/root/新boot ID/FDT清理通过，原失败/null保留，现场加载条后黑屏，无桌面。 证据：UniXNU-raphael/evidence/native-all-services.json。
  - [x] C02b.66：全存活进程原proc_iterate/NOWAITTRANS枚举、每进程最多512线程分32线程流式落盘、显式总数/截断/耗时；周期LS及末尾增加仅驻留页路径参数采样。实际C线程0/1/32/33/512/513与PID1024、引用配对及旧解码兼容通过；路径9项ASan/UBSan通过。完整内核/预链接/载荷、39项恢复QEMU与手机镜像通过，实机待验。证据：UniXNU-raphael/evidence/native-all-services.json。
  - [x] C02b.65：160537Z回收965条/941304字节/dropped0，五组LS及720014ms最终快照完整。实际I/O窗口0/0/0、SSD周期5/15/25，睡眠计数143/147/0；零时间窗口仍保留在途高优先级I/O竞争。868帧/0传输错误、watchdog55签到/0失败，四张RGB仍加载条并抽样匹配framebuffer，无记录panic/pressure kill。末尾LS已在原LSDReadClient处理store回复及OpenStaging初始化，不能仍称所有服务都等seeding；SpringBoard等BKS签到，BackBoard等数据迁移，迁移等profiled限制应用，profiled还见lockdown接收。具体剩余接收端待全进程采集。read elapsed345.917→333.313秒，单轮差异不足以认定提速。Android/root/新boot ID/FDT清理确认；现场进度条后黑屏，原失败/null保留，无桌面。 证据：UniXNU-raphael/evidence/native-io-window.json。
  - [x] C02b.64：零I/O节流窗口候选完整内核/未定义0、预链接/载荷、39项恢复QEMU及手机镜像通过；原COPY QUEUE与独立接收快照保持，新增只读实际窗口日志。704MiB/8192 vnode/720秒和16MiB日志保持，接下来实机验证扫描速度及桌面。证据：artifacts/desktop-io-window/20261105T160053Z/result.json。
  - [x] C02b.63：原XNU机器码确认throttle_init三次调用PE_get_default；新增仅三项后台I/O窗口25/100/500ms→0/0/0ms的ADT对照，SSD周期/原服务保持。ADT移除新增字段后逐字节恢复原输入，部分/非零合同拒绝通过；只读末尾日志增加实际窗口/睡眠计数。完整构建中，扫描速度与桌面待实机。证据：artifacts/desktop-io-window/20261105T160053Z/host-regression.json。
  - [x] C02b.62：153215Z完整回收967条/952451字节/dropped0，五组LS及720009ms最终快照完整。BackBoard21线程全部采到、无截断：695等原数据迁移、686等LS数据库；profiled142已采到，1436同等LS。SpringBoard末尾也回到LS应用记录查询，故此前BKS签到等待并非固定不变的死锁。LS488仍扫描本地化/属性列表；多线程落在throttle_lowpri_io，原卷均已报告solidstate。868帧/0传输错误，四张后期RGB仍加载条且抽样匹配framebuffer；UFS逻辑读7.265GB、read elapsed345.917秒含抢占。watchdog55签到/0失败、无记录panic/pressure kill。Android/root/新boot ID/FDT清理确认，原失败/null保留。现场确认进度条，末尾原生画面未知，无桌面。下一步对原XNU后台I/O节流窗口做单变量对照，保持服务及显示。证据：UniXNU-raphael/evidence/native-bks-receiver.json。
  - [x] C02b.61：BackBoard独立32线程及profiled采样候选完整内核、预链接/载荷、39项恢复QEMU及手机镜像通过；最终内核包含COPY QUEUE、BACKBOARD CAPTURE与独立section，失效刷新属性标记0。保持704MiB/8192 vnode/720秒和原服务行为；接收等待原因及桌面仍待实机。证据：artifacts/desktop-bks-receiver/20261105T151856Z/result.json。
  - [x] C02b.60：针对实际BackBoard八线程截断，新增独立BACKBOARD_RECEIVER最多32线程快照，原八槽协议/服务/2Hz队列保持。实际C函数提取测试0/1/8/32/40线程、缺进程/缺槽和所有引用配对通过ASan/UBSan；旧快照解码完全一致，新32线程解码及6个坏记录拒绝通过。另由本轮LS/迁移共同MCProfileConnection签到等待和实际profiled141，提升profiled采样优先级；实际选择ASan/UBSan通过，原八槽保持。完整构建中，接收原因待实机。证据：artifacts/desktop-bks-receiver/20261105T151856Z/receiver-regression.json。
  - [x] C02b.59：145317Z完整回收958条/896954字节/dropped0，五组LS与720073ms最终快照；timer及multi_head标记、855帧/0传输错误，后期1.997Hz确认多帧队列修复。对不限速差异拷贝祖先，copy elapsed366.571→73.178秒，BackBoard提交CPU400.070→23.579秒。四张RGB仍加载条且抽样匹配framebuffer；SpringBoard末尾改等BKSSystemShellService签到，BackBoard57八线程截断，接收处理未知。watchdog55签到/0失败、所采服务无异常；Android/root/新boot ID/FDT清理确认。现场进度条后黑屏，无桌面。下一步补采BackBoard接收线程。证据：UniXNU-raphael/evidence/native-copy-queue.json。
  - [x] C02b.58：多帧队列修正版887记录内核/未定义0、预链接/载荷、39项恢复QEMU及手机镜像通过；最终内核含唯一COPY QUEUE标记，旧PACE/刷新属性标记均0。实际源码队列ASan/UBSan已通过；待实机验证多帧继续提交与LS，无桌面。证据：artifacts/desktop-copy-queue/20261105T144653Z/result.json。
  - [x] C02b.57：定时提交队列修复已实现：允许已验证队首带后继，按原TAILQ语义更新head/backlink/tail，完成后重新唤醒剩余队首，保留原completion引用/代际。实际源码提取测试覆盖1至8帧FIFO、旧两帧拒绝复现、活动帧重入和坏链接/未验证后继，ASan/UBSan通过；正在完整构建，实机因果未验。证据：artifacts/desktop-copy-queue/20261105T144653Z/queue-regression.json。
  - [x] C02b.56：141301Z回收814条/401999字节/dropped0，五组LS与720046ms最终快照完整；原模式恢复，所采服务无异常记录，但仅9帧/13kicks/11validations，实际2Hz未验收。定时代码仍只允许单帧队列，异步积压后可能拒绝队首；下一步修正多帧队首出队及继续唤醒。最终仅扫描PID1..255，缺失服务不能解释为退出或LS完成。Android/root/新boot ID/FDT清理确认；现场仅确认进度条，无桌面。证据：UniXNU-raphael/evidence/native-copy-pace.json。
  - [x] C02b.55：从可提交加载条的差异拷贝父候选恢复原显示模式属性，仅新增原workloop上的IOTimerEventSource，将已验证pending提交限制为至少500ms间隔；首次立即提交，不持裸request跨定时器，不在拷贝中睡眠。887记录内核/未定义0、预链接/载荷、39项恢复QEMU及手机镜像通过；实际节奏、LS进展和桌面待实机。证据：artifacts/desktop-copy-pace/20261105T140919Z/result.json。
  - [x] C02b.54：133438Z回收828条/456390字节/dropped0，五组LS及720120ms最终快照完整；2Hz属性published1，但提交/完成均0、无后期RGB。原SpringBoard在FBSDisplayMode校验触发EXC_BREAKPOINT，累计32次；这是显示初始化回退，不验收2Hz。watchdog58签到/0失败，无记录原生panic；Android/root/新boot ID/FDT清理确认，原失败/null保留。下一步核对原属性消费者再修正；无桌面。证据：UniXNU-raphael/evidence/native-software-refresh.json。
  - [x] C02b.30a：等待实机窗口期间补齐已存在RamBlock本地修改的公开源码补丁；固定原组件提交，隔离应用后四文件与活动源码逐字节一致，未改本轮镜像。证据：artifacts/desktop-ls-scan-window/20261104T182635Z/ramblock-source-export.json。

## D. 手机桌面验收（阶段7完成标志）

- [ ] **D01：手机屏幕显示原生桌面首帧**
  - 首帧出现并保持至少 60 秒无清屏
  - 初始帧内容：桌面、StatusBar、Dock 等标准 SpringBoard 布局
  - 现场观察与 native-bsd-scheduling.json 同轮帧计数对应
  - 允许：软件渲染、未优化帧率、不要求 GPU 加速
  - 不允许：进度条、启动画面、纯色背景、来自 QEMU 的屏幕

- [ ] D02：原生帧持续提交，持续运行不卡死
  - 60 秒内无 panic、watchdog 重启、返回 Android
  - 记录帧率（秒数/帧数）

- [ ] D03：原生输入响应（可选）
  - 触摸屏幕，观察到响应

- [ ] D04：完成本轮人工恢复或定时重启

## B. 诊断优化与内部工具（备选项）

用途：当 C01-C06 的日志分析无法明确指出阻塞点时，使用这些诊断停点收集更细粒度的回传数据。

- [x] B02：独立显式5秒源码已接入C03，完整构建/主机门禁通过；手机验收未完成
  - 前提：已通过 C01 确认需要"更精确的 watchdog 观察"
  - 记录物理计数器起止

- [x] B03：独立记录解码和模式/时间/频率拒收检查已实现并通过主机检查。
- [x] B04-B05：完整构建、QEMU与唯一镜像/差异冻结已通过，见C03.3-C03.4。
- [ ] B06-B09：现场恢复确认、当轮映射预检已完成；165957Z无原生回传，171923Z独立人工恢复通过。手机原生窗口验收仍未完成，见C03.5/C03.5a。

- [ ] **关键约定**：不将 B02-B09 作为主线阻塞。

## E. 后续独立维护

- [x] E09：按用户USB追问单独取回feat/usb 8a9910d（较main7个未合入提交）、QcomDwc3 e4efe95和XnuPrelink f24e398。上游仅sheng/OS27 USB设备枚举/配对等已有报告；raphael/OS17未适配，无手机USB声明。官方记录禁用fairplayd/adid的启动配置，供当前依赖分析。证据：docs/upstream-usb-20261106T154225Z.json。

- [x] E08：2026-11-06 23:42按用户要求再次单次拉取官方main，仍e2fdae4、较今日上午0新提交；19/20 gitlink已取得，ArmCpu2e11cda官方仍not our ref。SoftwareAES与活动组件同版、无新修复。独立候选/失败保留，AES手机采集继续；未改活动pin。证据：docs/upstream-refresh-20261106T154225Z.json。

- [x] E07：2026-11-06按用户要求单次拉取官方main e2fdae4，相对11月5日候选36提交；19/20 gitlink取得，ArmCpu固定2e11cda远端not our ref，依赖完整性未通过。独立候选/失败日志保留，活动pin与当前实机不变；官方目录已索引raphael-guowenye。证据：docs/UPSTREAM-20261106.zh-CN.md。

- [x] E06：2026-11-05按用户要求单次拉取官方上游main350ddc2及20个子模块，独立候选保存；比11月3日候选43提交，vendor_boot离线7项通过。未发现当前LS seeding直接修复；本机适配和活动pin保留。证据：docs/UPSTREAM-20261105.zh-CN.md。

- [ ] E05：核对显示/看门狗证据摘要及porting记录中的旧pending/候选状态，分别保留执行前快照与实际执行结果；交接和TODO更新不等于这些摘要已全部清理。
  - 显示索引的旧 `prepared_candidate.state` 与170735Z实际结果需分别解释；165957Z以独立失败报告和最终人工恢复报告为准。
  - 持久日志、持久APFS Data、A640/外设与生产release仍需各自验收，不作为本轮已完成项。

## 修正说明

### 原TODO的主要问题：

1. **推进方向偏离官方路径**：原TODO在B02-B09花费过多资源于watchdog诊断细化，官方文档明确7阶段验收，当前应专注阶段7完成（显示输出）。

2. **缺少"C. 显示服务"关键章节**：原TODO从A直接跳到B，遗漏了显示问题的主要分析步骤。display_clients=0/frames=0 的真正原因未调查。

3. **缺少明确的阶段7验收标准**：原TODO无"D. 桌面验收"章节，未明确区分"能运行"和"能输出首帧"。

### 修正内容：

- ✅ 重新组织为：A（已有能力）→ **C（显示诊断）** → D（阶段7验收）→ B（诊断备选）
- ✅ C01：将日志分析作为最高优先级，明确表述"无需新实验"
- ✅ D：明确阶段7完成的具体验收条件（首帧、持续运行、可选交互）
- ✅ B：重新分类为"诊断备选项"，明确"仅在C失败后使用"

## F. GitHub源码发布

- [x] F01：按官方命名拆分并公开发布guowenye/UniXNU-raphael与guowenye/UniXNU-sm8150-common；设备feed/lock固定真实SoC提交，保留公开开发编排与源码锁，排除私有输入/备份/生成物，unixnu topic已设置。官方Porting record CI成功（run41968624247）；活动工作区保留，未进行手机实验。证据：docs/GITHUB-PUBLICATION-20261105.zh-CN.md。

- [x] F02：许可证补齐；设备和SoC仓库新增完整BSD-2-Clause-Patent LICENSE及README入口，保留文件原声明，设备固定含许可证的SoC提交。本次仅许可/文档/引用更新，无构建或手机实验。
