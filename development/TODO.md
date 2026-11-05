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
