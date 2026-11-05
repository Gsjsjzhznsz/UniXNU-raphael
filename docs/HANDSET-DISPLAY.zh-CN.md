# 继承 framebuffer 的手机原系统显示候选

修正状态标记的marker3候选已通过QEMU39项与手机镜像门禁，`evidence/private/android-return-run/20261102T170735Z/report.json` 临时启动已接受，目前原生回传与显示结果待定。固定原watchdogd只读指令审计显示监控循环使用10秒名义dispatch期限（`artifacts/session-logs/20261103-original-watchdogd-interval.json`）；这不是实机持续check-in证据，也未改变20秒硬件阈值或420秒绝对pet预算。


164851Z超时后，用户实体电源恢复。独立 `evidence/private/android-manual-recovery/20261102T170319Z-display-client/report.json` **passed=true**：Android新boot ID、root、临时FDT属性不存在；未取得匹配nonce，仍 `xnu_executed=null`，不能称自动返回或原生验收。现在仅对marker3修正候选继续QEMU/镜像门禁，通过后进行一轮临时启动。


2026-11-03 后续 `20261102T164851Z`：从163215Z成功基线仅将诊断停点移到原watchdog方法后的首个display client；164318Z完整887记录构建、164648Z QEMU39项通过，但手机665.674秒内没有Android回连或原生记录，**passed=false、xnu_executed=null**。用户先观察到本轮固件菜单，超时后确认全黑；电脑ADB/fastboot均无设备，正在等待实体电源恢复。保留镜像与失败报告，不原样重跑。

停点主机复查发现返回码初始0可能与尚未返回的newUserClient混淆，故旧marker2只能称“客户端进入”，不能宣称成功返回。源码现先记录NotReady再计进入、原调用返回后发布实际状态；新marker3明确区分。165046Z完整887记录内核与本地预链接/载荷已准备，**未上机**；后续依赖当前手机Android恢复与清理，不能自动继续启动。刚通过的163215Z首次原watchdog方法/check-in证据不受此未知轮影响。


2026-11-03 接续实验（UTC run `20261102T155924Z`）：补齐继承 framebuffer 的 OS 枚举输入。旧手机 ADT 已有诊断显示 opt-in，却没有 `/arm-io/raphael-gop` 的 `device_type=display-subsystem` 和 `/chosen/display-scale=1`；相同原用户态的 QEMU 历史记录已证明这些输入会影响原 CADisplay 枚举与 FBSDisplayMode 的零缩放检查。此处 scale 是本项目的一逻辑像素对应一物理像素策略，不是新测得的面板硬件参数。

本轮冻结 `204217Z` 成功内核、512MiB、240秒观察/300秒绝对 pet、原只读 extent/Data/trustcache/PMGR；只增加无 reg/IRQ 的显示声明和逻辑缩放。工作区 `scripts/native_display_adt.py --enumeration-only` 生成新 ADT，`prepare_handset_payload.py` 只允许这份精确声明通过硬件等价比较；附加资源或不同缩放被拒绝。9项主机保护检查、恢复 QEMU 与手机镜像构建通过。155924Z已整轮通过，463.187秒自动回Android，普通重启/root/临时属性清理通过；clients/frames仍0，backboardd未观察到。原task slide与UUID匹配的共享缓存符号化显示SpringBoard仍等待系统/用户cfprefsd。用户照片显示固件菜单，只证明面板有输出，不证明系统帧。第二候选使用原211750Z已有回传的360秒/420秒诊断基线和原冻结内核，仅补相同显示声明，观察真正服务启动后的原异常；不是重复无回传v34。原生显示/完整恢复与 Android 清理分别验收。索引：`../evidence/native-display-enumeration.json`。


2026-11-03 显示枚举第二轮 `20261102T161209Z` 已结束：匹配 nonce 与 CRC 验证的恢复 globals 显示 **display clients=3**、family/surface/meta/client 状态0，原控制台证明 backboardd57 启动；validation/kick/frame/retired 仍0。捕获的首异常中未再见 SpringBoard 的 missing-main-CADisplay 断言，但这不证明它已就绪。原 watchdogd 缺失服务断言及第五次关键进程退出触发 `_proc_exit` panic，**passed=false、experiment_passed=false，正常 checkpoint 未通过**。520.653秒自动回Android，全屏恢复、普通重启/root/临时FDT清理通过；不能把独立恢复 globals 当作正常 checkpoint。

当前显式候选新增 `--watchdog-method-checkpoint`：保持 v4 的360秒物理观察上限/420秒绝对pet、20秒硬件阈值和原方法参数检查，在首次原 watchdogd externalMethod 完成后至少10poll提前收尾；解码分别标记 first-watchdog-method-complete 与完整观察到期，不将提前退出当360秒覆盖。默认构建不启用，原生写探针与此选项互斥。`162658Z` 完整887记录XNU构建与 `163031.517829Z-22bhcg7a` QEMU39项通过。手机run `20261102T163215Z` **整轮通过**：nonce/完整checkpoint/全屏恢复/Android清理成立，452.986秒自动回Android；原watchdogd首次selector0成功、3次方法调用、1次check-in、0失败/0首异常。1819poll、物理231300.639ms、437次pet后以 first-watchdog-method-complete 提前退出，不能当完整360秒观察。此时clients/frames0，SpringBoard仍等待原CFPrefs回复。摘要 `UniXNU-raphael/evidence/native-watchdog-client.json`。下一候选只将停点移到原方法完成后的首次显示client成功打开，构建中，尚未上机。不重复旧v34无回传镜像。用户更正本次附件属于上一轮菜单画面，不能归入此候选；当前屏幕未知。

2026-11-02 当前主线：v33/223537Z 已完成匹配 nonce 的原生回传与普通重启/root/临时属性清理，505.165秒观察到 Android；原生检查未通过。服务 opens3/closes2、checkins0，无 externalMethod 入口记录。重新以原程序 BRK 和两级返回地址核对，v32/v33 均停在原 IOPMUPrimary=1 服务查找断言（原 PC0x10000b160），此前“selector0失败”的判断已更正。SpringBoard 首个异常已定位到 FBSDisplayMonitor 初始化。v34 仅在显式有界 watchdog 服务发布诊断用 numeric IOPMUPrimary 注册句柄，并验证原属性匹配；继承 setProperties 仍返回 Unsupported，不承认 PMU 硬件、boot-stage 或前台应用持久化。v34/225501Z 完整构建与原属性匹配 QEMU 通过，临时启动已接受，但664.258秒内未取得 Android USB 或原生回传，xnu_executed=null；用户确认全黑并强制重启；20261102T004239Z独立核查Android/root/新boot ID/临时属性清理通过，非自动返回。v35首次沿用冻结3600poll内核被手机构建预算门禁拒绝、未上机；现同步收短为1200poll并重建，独立ADT采用既有version2的120秒物理观察/180秒绝对pet预算，方法检查与20秒硬件不变；待主机和同轮实机验证，不原样重跑v34。20秒硬件与360秒观察/420秒绝对预算不变。最新正常 checkpoint 仍204217Z；display clients/frames0，桌面和交互未完成。

2026-11-02：基于190907Z已通过的512MiB、240秒有界观察、可写易失Data合同，只增加原系统显示接入。193023Z手机整轮通过：原显示服务启动与完整framebuffer映射/恢复成立；clients/frames均0，尚无可见帧或桌面结论。

## 接入与恢复合同

- 显式`--handset-display --handset-data --handset-ufs --native-diagnostic`选择独立`raphael_handset_display_defconfig`；默认配置不变。
- 使用已有、按固定21H461原始指令和358-slot vtable审计的IOMobileFramebufferLegacy适配器及原IOSurface getter。只做受检单层BGRA CPU内存拷贝，不声称A640渲染或硬件fence。
- 精确`/chosen/unixnu,diagnostic-display=<u32 1>`仅由手机显示profile消费；使用当前Boot_Video的实际起点、尺寸、stride，不引入新的板级地址。
- 手机构建必须`--native-video`并使用实际C的ASan/UBSan报告。固件同次检查路由/GOP/像素、备份完整画面，进入原XNU前检查Boot_Video匹配；返回时逐像素恢复全屏，任何不符均拒收。
- 已成功的Data轮及Android清理是构建前提。原OS/SystemOS UFS只读、原trustcache、原PMGR策略、20秒硬件watchdog/300秒绝对pet预算保持相同。无keystore新策略或面板MMIO写入。

## 当前验证

首次主机构建在旧DT函数名编译时拒绝，未上手机；改用固定XNU的SecureDTLookupEntry/SecureDTGetProperty后192545Z完整887编译记录与预链接通过。

正常checkpoint解码已追加原msgbuf和显示计数；用190907Z保存的原始回传重新解码，全部原验收及Data遥测一致，原控制台early boot/SpringBoard证据可读。重放没有重新启动手机，也没有覆盖原report。

193342Z补充QEMU39项通过：精确启用分支实际到stage2，原显示family/IOSurface/metaclass状态全0，headless零帧；摘要`evidence/handset-display-headless-gate.json`。首次补充夹具的ADT长度局部变量遮蔽RAM尾边界，在主机镜像检查时拒绝，已修复；未改运行中的手机镜像。

主机/模拟器与手机分别记录。QEMU staging无本机显示硬件，只验headless装载/原XNU/恢复；不能把它当成手机正向呈现结果。

## 实机判定

先要求本轮完整checkpoint、nonce、原pmap、GIC、看门狗、UFS及全屏恢复/Android清理。再看原显示family和IOSurface加载状态、stage、guard、client、validation/reject、frame/retired及原控制台。

接到真实frame且内存拷贝完成仍需独立观察面板可见内容。首次桌面要求原系统UI真实画面保持至少60秒；基本操作和持久Data另行验收。不把预制图、boot进度、进程出现或单帧计数称为桌面。

193023Z本机：family/surface/meta状态0、stage6/hardware3，1080x2340/stride4320/32bpp，10108800字节映射，2527200像素完整恢复零差异。可写Data与early boot/SpringBoard27再验；完整checkpoint和Android清理通过。下一候选只增加有界原进程/线程保存状态采样，保持所有运行预算。

只读service observer v4已完成195621Z完整887记录构建、200044Z预链接和200137Z QEMU39项门禁；rootless夹具实际采到原kernel-task线程保存栈，PID1不存在是该夹具的预期状态。手机200315Z在452.770秒自动Android并完成清理，全屏恢复通过；但普通EL0 BRK1提前被诊断桥接管，严格checkpoint拒收，service observer尚未执行。未将该轮作为正常验收。已删除仅lower-EL的诊断hook，保留原XNU用户异常路径及EL1诊断/恐慌桥；201432Z完整887记录和201705Z预链接通过，专门QEMU以最终分支字节实际触发EL0 BRK1/BRK5351并返回用户态。v25完整门禁运行中，尚无修正后实机结果。

202022Z修正后实机整轮通过：原用户BRK进入原XNU异常处理，240秒正常checkpoint/服务快照与Android清理成立，PID1达7692次syscall。SpringBoard27主线程停在ipc_mqueue_receive_continue，未观察到backboardd，clients/frames0。下一v27只追加task实际缓存slide及最多16个已驻留用户栈帧，task锁下持有原pmap引用，单CPU禁抢占期间只读已准入RAM；缺页停止、不调用vm_fault或copyin。203829Z完整887记录、ASan/UBSan物理保护7项、新记录解码6项、v27 QEMU39项通过；手机204217Z运行中，结果未定。v26仅因只读宽度字段未被恢复段解码而被主机拒收，未上手机。


2026-11-02 首个显示异常静态定位：223537Z 的 SpringBoard26 实际 task shared-cache slide 为243646464，PC0x1adc3b2ec 映射到原 FrontBoardServices 的 `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1148`。同一 UUID 的原共享缓存显示，对应断言为 `failed to find the main CADisplay`，触发条件是 `[CADisplay displays].firstObject == nil`。原 QuartzCore 的枚举路径经 `CARenderServerGetServerPort` 与 `__CASGetDisplays` IPC，不能仅凭“空列表”断定 framebuffer 驱动失败，也不能把它解释成 CADisplay 类缺失。原框架/服务二进制保持不变；下一步用正常服务快照区分 backboardd/渲染服务器就绪、IPC 返回和原显示驱动发布。静态审计位于 `artifacts/watchdog-method-observer-host/original-FBSDisplayMonitor.disasm.txt` 及 `original-CADisplay-query.disasm.txt`。
