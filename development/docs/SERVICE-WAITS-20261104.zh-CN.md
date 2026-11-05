# 服务等待对照与成功停点补采（2026-11-04，北京时间）

本轮继续手机原服务/显示主线，完成C02b证据对照、补采实现/门禁及一次手机实验。唯一补采候选180921Z临时启动接受，但665.449秒内无Android/原生回传，passed=false、xnu_executed=null。用户手动重启后，182112Z独立核查Android/root/新boot ID/无临时FDT通过，没有匹配原生记录。实验已停止，不重跑；最近正常原生成功仍为163215Z。具体服务根因仍未知。

## 已查清的等待位置与缺口

对照脚本 `scripts/analyze_handset_service_waits.py` 重新读取两轮原始 wire/delta 和冻结内核，验证恢复段CRC，再用修改前/后的解码器重解服务记录；二者和原报告一致。报告：`evidence/private/service-wait-analysis/20261103T175347.538817Z/report.json`。

| 证据 | 可以确认 | 仍不能确认 |
|---|---|---|
| 163215Z SpringBoard27 / tid249 | 同步XPC回复等待，栈经过 `_CFPREFERENCES_IS_WAITING_FOR_SYSTEM_AND_USER_CFPREFSDS` | 具体peer、请求内容、launchd check-in是否完成及未回复原因 |
| 同轮 keybagd45 / tid319 | 等待direct CFPrefs回复 | 是什么请求或peer，是否形成依赖环 |
| 同轮 keybagd45 / tid353 | PC落在 `CFPDSource acceptMessage:`，栈含 `CFPrefsDaemon handleSourceMessage:replyHandler:` 与XPC事件分发 | 不等于目标请求已被该线程接收或已完成回复；不能只按cfprefsd进程名缺席认定完全没有CFPrefs处理 |
| 同轮 configd37 | 采样位于dyld/ObjC初始化路径 | 单次快照不证明永久阻塞或具体依赖错误 |
| 同轮41个xpcproxy | PID扫描可见，其service_slot全部为空，没有线程快照 | 每个proxy的job/argv、是在加载、bootstrap接收还是其他等待，以及具体原因 |
| 161209Z独立panic轮 | 原控制台有cfprefsd90/93、backboardd57，CRC有效独立globals见clients=3 | 无正常checkpoint；旧client状态初值0不能证明newUserClient已经成功返回；不能并入163215Z构成连续启动 |

原始PID1 exec记录只覆盖launchd自身两次exec尝试，不能拿来补出每个xpcproxy的目标job。不同轮控制台时间也不能推出固定250–400秒启动延迟。C02b父项和C04继续未勾选。

## 本次最小观测候选

沿用163215Z的 **first-method / marker1**：首次观察到原watchdog方法完成、至少10poll后收尾。新增显式 `--service-spawn-waits`，在既有服务捕获中额外采样PID1..255内最多64个xpcproxy，每个取BSD线程列表中的一个引用线程。保留原8服务×8线程记录及全部进程扫描，不挤占原服务槽。

新增独立记录包含有无线程、是否有更多线程、tid/状态、kernel continuation/wait_event、保存的用户PC/LR、实际task shared-cache slide及resident-only用户栈帧。沿用现有线程/pmap引用和只读栈读取实现。一个线程样本不保证是主线程，也不提供完整job身份或CFPrefs请求/回复关联；若它揭示具体等待路径，再针对该路径修复或补采，不预设XPC失效。

原20秒硬件阈值、360秒物理观察上限、420秒绝对pet预算和方法参数检查不变，没有后延5秒或等待client的停点。默认构建不启用补采。已有失败marker2/3/4镜像不重跑。

## 已实际完成的门禁

| 层次 | 结果与冻结证据 |
|---|---|
| 实际C捕获分支 | 8组ASan/UBSan：0/1/41/64/65/255代理、空线程和多线程；引用释放、容量截断与原命名服务记录逐字节等价通过。`artifacts/service-spawn-host/20261103T175141.321700Z/report.json` |
| 解码 | 14项错误版本/容量/状态/PID/重复身份/帧数等拒收；4组旧格式兼容；两轮真实回传重解码与旧版/原报告一致 |
| 完整内核与结构 | 887编译记录、未定义符号0。`artifacts/native-bootstrap-attempt/20261103T175023Z/report.json`；`artifacts/native-kernel-inspection/20261103T175347Z/report.json` |
| 预链接与载荷 | `artifacts/desktop-prelink/20261103T175410Z/`；`evidence/private/handset-payload/20261103T175524Z/report.json`，128MiB |
| 当前Android暂存 | Android完成启动、raphael/root、无临时FDT属性通过；仅上传新128MiB Payload，4个不可变extent。`evidence/private/handset-system-disks/20261103T175528Z/report.json`、`evidence/private/ufs-readonly/20261103T175538Z/extent-source.json`。没有重传OS/SystemOS，没有flash/erase或启动手机镜像 |
| 恢复QEMU | `artifacts/native-staging-qemu/20261103T175907.097098Z-d6yowwnu/report.json`，39项通过；rootless40秒，补采header完成但代理数0，实际代理分支由主机模型覆盖，不称QEMU运行了原服务 |
| 临时镜像 | `evidence/private/android-return-build/20261103T180016.907052Z-ajn5mm64/report.json`；SHA256 `d13a5a3e3dd9796cb92da2643bcd6d3c8f9f256c3e4261f8b9210e19497bd990`；180921Z上机无回传，失败原报告保留 |
| 最终单变量审查 | `artifacts/service-spawn-build/20261103T175023.518572Z/candidate-review.json`、`candidate-pointers.json`；Windows导出 `service-spawn-candidate-20261104.json` |

首次QEMU编排遗漏了原有六个夹具参数，触发原IOFindBSDRoot找不到根盘的panic，37项通过/整轮失败。失败报告 `artifacts/native-staging-qemu/20261103T175542.821130Z-4_d80h3u/report.json` 和首次日志完整保留。补齐原成功轮参数后才取得上表39项通过，不覆盖失败为成功，也未放宽判定。

冻结对照确认有效补丁顺序/hash、显示实际编译源码、原线程捕获源码、ADT/Trust/Data、固件源码/上游输入、return stub及原Android kernel/ramdisk相同；实测内存布局、watchdog、原启动参数相同。当前显示状态修正仍保留，候选显式选用成功轮显示源码。96字节观察函数帧和first-method marker1保持；内核地址/策略及新Payload映射随新增记录派生更新。

独立记录总69696字节，完全变化时最多新增104544字节delta；成功轮805764字节加此上限为910308，小于原1048576容量。新一轮的其他动态状态仍可能变化，必须实际验证delta_overflow、FDT容量与完整恢复，不能据此预先验收手机。

## 手机结果、菜单核查及下一最小任务

用户确认现场可恢复后，当轮Android/root/FDT、镜像/QEMU哈希及OS/SystemOS/Payload不可变extent均通过。`180921Z`（北京时间11月4日02:09:21）只执行一次fastboot boot；runner在665.449秒后未建立Android回连，`passed=false`、`xnu_executed=null`，没有native wire/delta，不能确定是否进入新增采样器，也不能检查其delta溢出。原失败报告：`evidence/private/android-return-run/20261103T180921Z/report.json`。

现场依次报告黑屏、引导菜单，之后用户手动重启回Android。`182112Z-service-spawn`独立核查Android完成启动、raphael、root、新boot ID、无临时FDT全部通过；没有匹配nonce或原生记录，失败报告SHA保持不变。这是人工恢复，不是自动返回。恢复报告：`evidence/private/android-manual-recovery/20261103T182112Z-service-spawn/report.json`。执行索引：`artifacts/service-spawn-build/20261103T175023.518572Z/execution-result.json`；冻结构建/审查中的未执行字段保留为当时快照。

菜单核查直接从实际Payload FAT提取unixnu.toml，验证timeout0/default diagnostic-exit/action exit；对照冻结PayloadTest.c、Main.c、Menu.c的构建哈希与Menu.obj，源码在绘制菜单后、创建按键等待前直接返回默认项。同源码QEMU日志实际含timeout0和Return to diagnostic。故不需要短按电源确认；屏幕有菜单不能证明正在等待选择，也不能证明手机已越过菜单。报告：`artifacts/service-spawn-build/20261103T175023.518572Z/menu-return-audit.json`。

用户提出的[官方二维码日志方案](https://unixnu.com/porting/log-capture)由AdvancedLogDxe菜单插件冻结固件AdvancedLogger日志，二维码按块显示。当前手机诊断构建未包含该模块，既有诊断FAT也只有自动返回项。冻结源码的CollectLog读取AdvancedLoggerAccessLib；该机制本身不采集XNU接管后新增的服务快照。它可补充UEFI前段日志，但不能仅因已有菜单画面就宣称当前可扫码，或直接补上本轮未知的原生阶段。

下一最小任务是独立验证**复位前阶段回读通道**：只带实验身份与阶段码，区分菜单返回、XNU交接、服务捕获进入/完成、原生返回；先使用已核实显示资源和保存恢复合同，完成实际分支/完整构建/QEMU门禁，再独立验收本机可读性。原生捕获前后标记必须在接管后的实际执行上下文可写，UEFI菜单插件不能替代。尚未实现或验收该新通道，本轮不再启动其他手机候选，也不原样重跑180921Z镜像。

C02b根因、CFPrefs请求/回复关联、C04服务就绪、backboardd成功client返回、实际frame/retired、手机原系统首帧/60秒及输入均保持未完成。现有记录不足以认定采样死锁、watchdog触发、XNU没有执行或返回路径故障中的任一种。

变更前备份：`artifacts/service-spawn-review/20261103T174901Z/`。本轮未同步上游，原失败报告与备份保留。本文不是对其他历史文档及E05摘要的全面清理。
