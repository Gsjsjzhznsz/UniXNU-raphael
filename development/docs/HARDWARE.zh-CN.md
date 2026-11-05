# 硬件事实、设计假设与未知项

当前验证状态见[CURRENT.zh-CN.md](CURRENT.zh-CN.md)。本文按采集轮次追加，初始“未知”不覆盖后续实测；每条结论只适用于其记录的入口、源码和模式。最新仍未知的是完整RAM所有权、永久TimerArch及完整手机UEFI/XNU平台；NS使能视图与单次物理IRQ已分别实测，但不等于完整GIC所有权。

## 已观测事实（仅指当前 Android 的观测）

| 项目 | 结果 | 来源 |
|---|---|---|
| 型号/代号 | Redmi K20 Pro / raphael | getprop + ADB 枚举 |
| SoC | SM8150, ID 339, revision 2.2 | /sys/devices/soc0 |
| DT 模型 | RAPHAEL | root 读取 live FDT |
| DT compatible | qcom,sm8150-cdp; qcom,sm8150; qcom,cdp | live FDT |
| 当前内核 | 4.14.253-Marisa-r14 | uname；定制内核，不能假定是原厂 |
| Linux MemTotal | 7726320 kB | /proc/meminfo；不是物理 RAM 的完整地图 |
| CPU 在线/DT affinity | 0-7；0x0、0x100、0x200、0x300、0x400、0x500、0x600、0x700 | sysfs + 本次 live FDT；不推断核心类型 |
| 显示驱动路径 | DRM；fb0 不存在 | /sys/class/graphics |
| 根权限 | uid=0, Magisk context | su -c id |

## 本次已解析的内存描述

live FDT `/memory:reg` 描述以下范围，使用左闭右开区间：

| 起始 | 结束 | 字节数 |
|---|---|---:|
| 0x80000000 | 0xbbb00000 | 1001390080 |
| 0xc0000000 | 0x180000000 | 3221225472 |
| 0x180000000 | 0x280000000 | 4294967296 |

合计 8517582848 字节。这是 DT 描述量；不能把地址跨度或 Linux MemTotal 当作可供 UEFI 自由分配的连续 RAM。
固定保留区逐项解析，没有相互重叠。动态池只有 size/alloc-ranges，不能以此得出 UEFI 阶段的实际地址。

完整观测及每项 FDT 节点来源见 `../UniXNU-raphael/evidence/hardware-observations.json`。
GICD 0x17a00000/0x10000、GICR 0x17a60000/0x100000 与 19200000 Hz 定时器频率，均已与本机 live FDT 及 Xiaomi 固定提交的 `sm8150.dtsi` 交叉检查。
这些资源尚未用本项目代码实机驱动。

## 原厂固件声明（不等于新 UEFI 可直接使用）

从本次 XBL 解包所得 `uefiplat.cfg` 读取，配置文件 GUID、文件哈希、XBL 源哈希、原始行号及属性完整记录于 `../UniXNU-raphael/evidence/vendor-declared-layout.json`。
原配置和模块保存在私有目录，不提交原文或二进制。

| 声明项目 | 基址 | 大小 | 原始行 |
|---|---|---|---:|
| Display Reserved | 0x9c000000 | 0x2400000 | 18 |
| UEFI FD | 0x9fc00000 | 0x300000 | 22 |
| SEC Heap | 0x9ff00000 | 0x8c000 | 23 |
| MMU PageTables | 0x9ff8d000 | 0x3000 | 25 |
| UEFI Stack | 0x9ff90000 | 0x40000 | 26 |
| Log Buffer | 0x9fff7000 | 0x8000 | 27 |

原厂固件可能覆盖配置；原 FD、栈和服务数据在交接期间可能仍有使用者。当前没有把这些地址写入新 FD 的活动配置。
显示保留区与本机 live FDT 及 Xiaomi 公开源一致，但它不是已经确认的 GOP FrameBufferBase。

## 启动镜像与外设

- 新读 boot 镜像为 Android header v1，页大小 4096，kernel 48812036 字节、ramdisk 444400 字节。
- kernel 字段观测到 `UNCOMPRESSED_IMG` 包装，ARM64 header 的 text_offset 为 0x80000；这不是 UEFI FD 基址。bootloader 对包装的完整处理语义尚未源码核实。
- dtbo 只有一个条目，结构及范围已核对；运行时 chosen 指示 dtbo_idx=0、dtb_idx=0。
- 当前启动参数选择 Samsung EA8076 命令模式面板，SurfaceFlinger/wm 报告 1080×2340；Xiaomi 本机面板源码也描述该分辨率。像素格式、stride 和实际 scanout 地址仍未知。
- 本机输入可见 qpnp_pon、gpio-keys 与 goodix_ts；本机 Xiaomi DTS 具有 Goodix GT9889 绑定，但当前定制驱动的完整协议和固件选择仍待核对。
- 新读 XBL 解包得到 127 个有 UI 名称的 FFS 对象，已记录模块哈希和 DEPEX；不能把 DEPEX 视为完整运行时依赖证明。

## 本机入口实测

- 已用入口探针实测交接：EL1，SCTLR_EL1=0xc00808，DAIF=0x1c0，x0/FDT=0x85491000，Image=0x80080000，x1-x3=0，CNTFRQ=19200000。完整寄存器及原栈/返回地址见 `../UniXNU-raphael/evidence/entry-handoff.json`；具体方法和验证边界见 `ENTRY-PROBE.zh-CN.md`。这些是已验证的入口事实，不是新 FD 的实机验证。
- 原 SP=0x9ba29f00、LR=0x27bf5be48。不能用默认 SEC 栈来代表 ABL 当时的实际栈，也不能把这些历史地址当作可分配区。
- 入口探针采用自身 Image 内的栈与 FDT 副本，在 Android 读回带随机测试标记的 FDT。该回传通道已实测，可为后续早期诊断提供基础；它不提供当前可复用的原 UEFI 系统表。

## 设计预算与待解决的所有权

- 优先采用非持久的 fastboot boot 验证最小 UEFI。该通道已用当前原 Android 镜像和入口探针实测成功，新诊断 FD 的实机执行须按阶段单独证明。
- 保留 EDK II/Mu 与 UniXNU 通用基础设施，板级参数由本机证据生成。
- 新 FD/SEC/DXE 候选容量与位置见 `../uefi-raphael/Resources/memory-plan.toml` 及 `../UniXNU-raphael/evidence/memory-plan-check.json`，生产配置仍禁用；私有诊断 FD 已按独立门禁构建。扩大 Image 下载已在手机接受，但零填充尾部未逐区写入/读回，不能作为完整所有权证明。具体分段结果见 `SEC-DXE.zh-CN.md`。

## 未知与禁止猜测的输入

- 诊断 FD/SEC 栈、页表及部分堆页已被成功路径使用；完整可用范围、隐藏原厂所有权与存活期仍未验证。不能将这些诊断使用结果泛化为整个 RAM 的分配许可。
- framebuffer 物理地址、格式、stride、scanout 缓冲区生命周期和 GOP 可复用性。
- 完整物理 RAM 与固件隐藏区；live FDT 和 Linux iomem 仅是候选证据。
- 当前引导的设备树是否由第三方内核改写；需与本机 boot/dtbo 和 Xiaomi 公开内核源码交叉核实。
- UEFI 时钟、电源、串口可访问性、SPMI 按键协议。
- Android DRM debugfs 已只读观察到 4352 字节 pitch、1088 宽分配和非零 modifier；这些观测尚未解决原厂启动显示的 framebuffer 物理地址/布局，不能代入 GOP。
- 原备份恢复能力：未验证，且不包含完整手机数据。

## 诊断内存布局与证据边界

新 FD=0x836b0000/0x300000、栈=0x839b0000/0x40000、arena=0x839f0000/0x1000000、FDT 副本=0x849f0000/0x110000 均是从本机 Image base/原大小推导的诊断设计预算，不是原厂公布的可分配许可。bridge=0x836a0000/0x10000，末端=0x84b00000。没有借用原厂 0x9fc00000 FD 或 0x9ff90000 栈。

`extent-download.json` 只证明该大小 Image 被接受并继续 Android；20,283,392 字节尾部当时未由探针访问。最小 SEC/DXE 的主机与模拟器成功不替代手机证据；原厂配置覆盖和完整 arena 所有权仍未知。

## 新 SEC 分段交接观测

修正后的 SEC/FDT 和 HOB/MMU 已在本机回传，见 `sec-stage2-handoff.json`、`sec-stage3-handoff.json`。

- 初始 VBAR_EL1=0x9fc04000，CPACR_EL1=0x300000，TCR_EL1=0x580803510，MAIR_EL1=0xffbb4400。
- 原 TTBR0_EL1 在这两次分别为 0x9ff20000、0x9ff1a000；它们是仍需保护的原厂交接观测，不是新页表分配许可，也说明默认配置表不足以描述当时全部运行时布局。
- 新 MMU 启用后的 SCTLR_EL1=0xc0180d，页表根=0x849ef000，均来自阶段 3 回传。页表容量字段只表示库返回的根表字节数，不代表全部层级的实际页数。
- bridge、SEC 栈、FD 内代码/数据与远端 FDT 副本在成功路径中被使用；这不等于整个 16 MiB arena 已完成 RAM 测试或获得原厂完整所有权证明。

最小 DXE 后续也已回传 stage=6/status=0：2535 字节日志，ST/BS 表 CRC 正确、页面分配写入释放通过，15 项内存描述均未越出诊断 arena。这个结果覆盖实际用到的页，不是对整个 arena 的全面 RAM 测试。结束后已正常重启并确认临时标记清除，见 `sec-dxe-cleanup.json`。


## 新增启动显示只读观测（本轮 stage 2）

证据：`sec-display-handoff.json`、`boot-display-observation.json`；方法与一手源码行号见 `DISPLAY-PROBE.zh-CN.md`。本轮从 ABL→原 Android 内核入口之间只读采样 149 项 MMIO，随机标记回传、Android/root/boot 哈希审核通过。

- MDSS revision=0x50000001；GDSCR=0xf822f000。GCC DISP AHB=0x80000003，结合一手驱动的 HWCG 语义判断，而不是把空闲停钟当成断电。
- 唯一非零尺寸/地址/格式的管线是 VIG0：source/output 均为1080×2340，plane0 地址寄存器=0x9c000000，stride=4320字节；format=0x237ff，unpack=0x03020001，opmode=0x80000000。
- 固定一手源码将其解释为线性 ARGB8888，字节顺序 B/G/R/A；尺寸×stride=10108800字节，落在本次 cont_splash 保留区内。
- 上述数据证明的是启动入口的寄存器配置。活动路由、SMMU/CPU物理映射、alpha混合、命令模式刷新、缓冲区生命周期和 GOP 可写性仍未知，禁止把这一地址寄存器值直接代入启用的 GOP。
- 本轮仅重新验证了扩展后的 stage 2。此前 stage 3/6 证据仍属于原各自源码快照，不能自动绑定到本轮新增的包文件。


## 2026-10-28：入口显示路由配置与 SMMU 声明

wire v3 在本机 stage2 回传507项，只读采样的 CTL0_TOP=0x20000、INTF_ACTIVE=2、LM0_LAYER=0x01000005。结合固定一手接口源码，VIG0 被分配到 LM0 blend3，interface1 mux=0 对应 PP0，TE=1、自动刷新=0x80000001。LM0 尺寸仍为1080×2340；blend3 op=0x400、const=0x00ff0000，对应不依赖像素 alpha 的前景常数255、背景因子0。以上证明编程配置一致，不证明正在 fetch、TE变化或面板更新。

本机 MDP 的 iommus 参数解析为 apps-smmu SID=0x800、SMR mask=0x420，不是 context-bank。声明范围涉及 hf0/hf1 两个 TBU；地址/供应节点均由本次 FDT 重新解析，见 DISPLAY-ROUTE.zh-CN.md。SMMU寄存器/页表未读取，候选像素地址仍不能当作已验证的CPU物理映射，GOP继续禁用。没有写像素、时钟、电源或刷新寄存器；正常重启清理已通过。


## SMMU入口实测（wire v4）

本机stage2读取621项并nonce回传成功。SMR3唯一覆盖SID0x800/mask0x420，S2CR3选择CB2；CBAR type1、AArch64、SCTLR.M=0、TTBR0/1=0，CR0.CLIENTPD=0。配置与S1 bypass/S2 bypass一致。数据仅证明寄存器配置和本次读可访问，未证明CPU像素、DMA和面板刷新；见SMMU-PROBE.zh-CN.md与boot-smmu-observation.json。正常重启/root/原boot审核通过。


## CPU候选缓冲区只读实测

20261027T170622Z在MMU/cache关闭的入口读回64×64稀疏网格，地址由现场VIG0和cont_splash约束，4096样本全部成功；网格RGB均黑。TE行计数移动，但接口状态/帧计数均0，仍未证明可见fetch或面板更新。没有像素写入。见PIXEL-PROBE.zh-CN.md与boot-pixel-observation.json。

## 可恢复显示实机证据

本轮SEC在MMU/cache关闭时，现场重新满足显示与SMMU门禁后向0x9c000000左上256×128写白框RGB。两次32768像素逐字回读与恢复通过；20261027T172041Z用户明确观察到色块，证实此启动入口下的CPU写入可达到面板。范围仍限本次既有启动模式，未证明GOP、模式切换、所有缓冲区或Android运行时复用。单次状态与来源见PIXEL-WRITE.zh-CN.md。正常重启清理及原boot哈希审核通过。

## 2026-10-28：GOP实机验证

GOP在当前继承模式1080x2340/stride4320下实机验证：NC映射后读样本一致，DXE安装GOP、QueryMode及四种Blt通过。256x128像素恢复差异0；用户看到色块。framebuffer保留HOB与18项内存图边界检查通过。范围限本次启动的既有显示，不能泛化为模式切换、所有RAM所有权或Android运行时复用。

## PM8150输入资源入口实测

20261027T182056Z只读配置nonce回传：SPMI v5=0x50000000，EE/channel0，512项APID表共858次读取；PON RT_STS=SID0/0x0810，PPID8有3项，按当前EE选择249；GPIO6 RT_STS=SID0/0xc510，PPID0xc5选择262，owner均0。值由本次FDT和硬件表动态解析；未发送PMIC事务，未验证按键状态或物理操作。

PMIC实机六笔只读取值已验证：GPIO6 type0x10/subtype0x11、mode0、enable0x80，输入有效；GPIO RT_STS1、PON RT_STS4。通过observer读命令事务，没有写PMIC配置。实体按键变化尚未测试。见KEY-READ.zh-CN.md。


## 输入协议与菜单诊断（2026-10-28）

同源码stage2/3/6实机通过；observer现场推导两页映射，stage3读取验证，stage6安装SimpleTextIn。40秒8000次采样错误0且无按键事件。菜单绘制/恢复2527200像素差异0；未收到这轮可见性观察，不把缓冲区证据等同可见菜单。实体按键、TimerArch、完整UniXNURun、DarwinBoot/XNU仍未验证。


## 定时器与中断资源更新（2026-10-28）

本次Android只读复采确认timer继承PDC→GICv3。固定厂商实现将specifier交父GIC转换，四路INTID为17/18/19/16；Android当前arch_timer为PDC-GIC硬件号19、虚拟定时器，Linux逻辑IRQ4。FDT原始flag0xf08保留，不能代入模拟器常见PPI。GICD/GICR范围与stride再次匹配固定厂商源，具体来源与31项解析检查见INTERRUPTS.zh-CN.md、interrupt-resource-contract.json。GICR启动CPU对应帧、ICC状态和新UEFI的IRQ投递/恢复仍未知；未进行MMIO或中断写入。


## 2026-10-28：菜单与实体三键人工交叉验证

历史b2e774c镜像的独立复测20261027T215414Z，用户观察上键到Boot information、下键回Return to Android、电源提前返回均符合预期；同轮wire回传up/down/enter=1/1/1、错误0、Enter退出约7.1058秒。完整2527200像素恢复差异0。Android/root/原boot哈希及215618Z正常重启清理通过。完整可见诊断菜单与三键单次映射在这一轮已验证，不泛化为触摸、长按/组合键、TimerArch或完整管理器。来源见manual-menu-observation-20261027T215414Z.json。


## GIC入口读取实测（2026-10-28）

220921Z只读stage2完整67次读取，8个GICR帧affinity与同轮FDT的8CPU一致；入口MPIDR0x81000000动态匹配frame0/0x17a60000。GICD PIDR2=0x3b、CTLR=0x10；原始每帧和SGI字段见boot-gic-readonly-observation.json。此为读取视图，不证明写权限或完整所有权。Android/root/boot哈希及221111Z正常重启清理均通过。ICC访问、timer中断投递和接管/恢复仍未知。


## ICC/timer入口实测（2026-10-28）

224342Z只读16项完整，SRE=1、CTLR=0x8440、PMR=0xf0、BPR1=3、IGRPEN1=0、RPR=0xff、HPPIR1=1023；CNTP_CTL/CVAL均0；CNTV_CTL=5，CNTV_CVAL=233262653。CNTV仍enable且到期，不能假定所有timer都关闭。GICD_CTLR.DS=0时IGROUPR/IGRPMODR对Non-secure访问RAZ/WI，历史group0读值不能推断真实安全组。来源boot-icc-readonly-observation.json与ICC-READONLY.zh-CN.md。正常重启清理、Android/root/原boot审核通过。没有ICC/timer写入、IAR确认或IRQ投递验证。


## 已关闭的CNTP源与恢复（2026-10-28）

230159Z实机在DAIF全mask且CNTP.IMASK=1时到期，4423次采样、192018ticks约10.00094ms；CTL/CVAL从原0暂改后均恢复0，5次写入无trap。Android/root/boot哈希与230328Z正常重启清理通过。只验证物理source，不证明PPI投递/IRQ或GIC写权限；见boot-timer-source-observation.json。


## 本CPU物理timer PPI使能权限（2026-10-28）

232552Z同轮FDT/affinity解析INTID18/flags0xf08及SGI_base0x17a70000；enable0→0x40000→0、2次write-one操作，pending/active与GICD_CTLR原值保持。手机可写并恢复；没有GICD/ICC配置写入或IRQ。Android/root/boot及232753Z正常重启清理通过。来源boot-ppi-enable-observation.json。

## GIC使能视图的验证范围（2026-10-28）

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


## 有界物理TimerArch实机（2026-10-28）

012324Z在MMU/DXE下使用同轮FDT解析的PPI18、GIC窗口及19.2MHz计数器，真实CpuDxe向量/本机物理TimerArch/DXE事件持续IRQ/EOI各61。relative/periodic/cancel/停表稳定通过，GIC组/目标enable/active、CNTP CTL/CVAL、DAIF均恢复，CNTV_CTL5及CVAL258603056未变。证据仅限当前有界10秒诊断实例；不证明其他PPI、Secure控制、常驻服务或完整RAM所有权。详见PHYSICAL-TIMER.zh-CN.md。


## 完整管理器与有界物理TimerArch实机（2026-10-28）

最新0a91c56三阶段手机实测通过。无GOP、只读RAM退出配置中的真实UniXNURun耗时38472549ticks/19.2MHz，即2.00377859375秒。IRQ/EOI/notify各262，GIC/CNTP/DAIF恢复，CNTV_CTL5、CVAL235337914未变。020320Z正常重启清理、Android/root/原boot哈希通过。此结果不验证可见完整管理器、常驻服务或内核连续RAM；见boot-manager-observation.json和MANAGER.zh-CN.md。


## 最新只读RAM核查（2026-10-28）

021216Z新采集FDT描述8517582848字节；Linux memblock memory与iomem System RAM合并一致，为8086261760字节。memblock reserved可读取；EFI/memmap与MMFR0/PFR0 sysfs不可用，不能由MIDR0x51df805e推定物理地址能力。排除已知范围后，256MiB对齐示例为0xc0000000、0x100000000、0x200000000，均只是主机推导候选，未实测访问或授权分配。真实内核低21位偏移未知、DMA/原厂隐藏生命周期未解决，详见KERNEL-MEMORY.zh-CN.md。


## 入口候选RAM稀疏读取实测（2026-10-28）

030742Z手机在EL1/MCI关闭/DAIF全mask时，0xc0000000..0xd0000000每2MiB首尾各8字节，共256地址全部可读，耗时28854ticks/19.2MHz=1.5028125ms。现场MMFR0=0x101122、Mu ArmGetPhysicalAddressBits=40；95项来源策略guard和4项实时guard通过。241个样本非零只记摘要。030956Z正常重启清理、Android/root/原boot哈希通过。源码258e353，详见RAM-READ.zh-CN.md。没有候选RAM写入、整个窗口测试、分配授权或隐藏DMA生命周期结论。


## 完整管理器可见显示与恢复（2026-10-28）

50956e2同源码stage2/3/6手机通过，040314Z完整UniXNURun使用本机GOP1080x2340/stride4320/BGRA/0x9c000000，2527200像素变化并完整恢复，差异0、fallback0。用户确认看到完整菜单；200次输入采样错误0，无按键操作。物理TimerArch IRQ/EOI/notify355且完整恢复，040520Z正常重启清理、Android/root/原boot哈希通过。此结果限两秒合成退出配置，不证明完整管理器实体按键、常驻TimerArch、手机DarwinBoot或XNU。见MANAGER-UI.zh-CN.md及独立人工记录。


## 完整UniXNU管理器实体三键（2026-10-28）

513c3b8同镜像复测050556Z在完整管理器收到实体上/下/Enter各1、自动0、错误0，用户确认各步正常；4.18086515625秒提前返回。全屏恢复差异0，IRQ/EOI/notify560及原状态恢复通过；050950Z清理、Android/root/原boot哈希正常。首轮045604Z为上下键加六秒自动Enter，不是实体电源验证。范围和来源见MANAGER-KEYS.zh-CN.md。未执行手机DarwinBoot/XNU或扩展RAM写入。


## 候选RAM第一页可恢复写入（2026-10-28）

1b9a735的062031Z实机在现场重新满足95项策略/4项入口保护、EL1/MCI关闭/DAIF全mask/40位PA及256点只读门禁后，测试0xc0000000第一页4096字节。两轮图案1024字、完整恢复512字零差异，原始/恢复摘要相等，235318ticks/19.2MHz约12.2561ms。Dirty和备份字数均清零；062401Z正常重启清理、Android/root/原boot哈希通过。来源见RAM-WRITE.zh-CN.md和boot-ram-write-observation-pages1.json。仅本页可恢复写事实，不推广为整个256MiB、空闲/隐藏DMA所有权或分配器许可。


## 候选RAM前八页可恢复写入（2026-10-28）

063206Z从0xc0000000连续八页32768字节两轮图案与原字恢复零差异；现场256点只读及来源/入口保护门禁重跑通过。耗时98.4048958333ms，Dirty/BackupWords0，063549Z正常重启清理和Android/root/原boot哈希通过。此为八页局部事实，不是256MiB完整窗口、跨页别名、隐藏DMA所有权或UEFI分配许可。详见RAM-WRITE.zh-CN.md及boot-ram-write-observation-pages8.json。


## 第一MiB实机验证：20261028T071253Z

来源绑定a8a3033的065009Z镜像通过临时fastboot boot：0xc0000000起连续256页/1048576字节，completed/restored均256，图案262144字、恢复131072字均零差异，Dirty/BackupWords0，原始/恢复摘要相等。耗时3155.9350520833ms；现场256点只读及95项策略/4项入口保护再次通过。Android/root/原boot哈希正常，071435Z正常重启清理通过、临时属性消失。未flash/erase/format，未修改原备份。

boot SHA256 8d35cb2a36aa17513164ebb32798c913808ef5cb832a1a2a40edda909ac00e65；FD SHA256 a0d8a4e036fe5adecc44197a5622f53fb79821cf71536b4ce8905ef9b69f0ac7。独立原wire/FDT/log/不可变attempt与handoff/cleanup核验见boot-ram-write-observation-pages256.json。事实仅限前MiB，整个256MiB、跨页别名与隐藏DMA所有权仍未证明；分配器仍未扩展，手机DarwinBoot/XNU未执行。


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


## 页面边界版首MiB手机实测：20261028T125630Z / 20261028T130021Z

两阶段149项固件输入及22项验证脚本绑定06654aa4907a9193a6b4b0a29c69af48531e840b。0xc0000000起连续256页/1048576字节，完成/恢复各256，两轮图案262144字、原字恢复131072字均零差异，Dirty/BackupWords0、摘要相等；pre/post同步256/768、RW/PAR及恢复RO写拒绝256。实际耗时27.4865625ms；对照旧版43.267552ms减少约36.5%，不外推完整256MiB通过。

20261028T130128Z正常重启清理、Android/root/原boot哈希通过，诊断属性消失。boot SHA256 0629947b1603cb7e6000f070d831e43461b411b7d120d7709cd42e407ffd6f00；FD b2540a1db88f4cc03c2c8ac165152f58e03239a677b345c8f4c2cd9fad337081。完整原wire/FDT/log/不可变attempt与handoff独立核验见boot-ram-cache-observation-pages256.json。未扩分配器、未flash/erase/format、未改原备份。新版64MiB的QEMU阶段2 125631.629511Z-c7qe108p正常47项，阶段3 125736.283359Z-tol8aclq正常53/部分写UDF55/读取异常49及机器码审计通过，尚待新版手机64MiB实测。


## 页面边界版前64MiB手机实测：20261028T130412Z / 20261028T130930Z

两阶段149项固件输入和22项验证脚本绑定e39d25104434edf602d1b54a7dc73a14a07fb8a0（缓存实现为bec9798，通用源码与旧恢复引擎未修改）。0xc0000000起连续16384页/67108864字节，完成/恢复16384，两轮图案16777216字和原字恢复8388608字均零差异，Dirty/BackupWords0、摘要一致；pre/post同步16384/49152，RW/PAR及恢复RO写拒绝256。实际33763913ticks/19.2MHz=1758.5371354166666ms，比旧版本2768.231146ms减少约36.5%。只是此范围实测，不是完整256MiB或分配许可。

20261028T131038Z正常重启清理、Android/root/原boot哈希通过，临时诊断属性消失，当前没有进行中的实验。boot SHA256 a7d2218e29996123f07449affb7bcddf5674f30f0a5742f27d46ed9e1f4e99cc；FD 5000a3b01b07bd0cf9baef136e551425f8b0179ca56fef42a87707653edd93ad。原wire/FDT/log/不可变attempt与handoff及cleanup核验见boot-ram-cache-observation-pages16384.json。分配器仍只有原16MiB诊断arena，未flash/erase/format、未改动原备份。

新增validate_ram_cache_timeouts.py独立重解码四次全窗口QEMU失败的原wire、read/mapped门禁、超时阈值、恢复页数、Dirty/Backup及RO状态，核对596份归档源码文件与固定Git/独立直接循环快照，并检查MMU关闭receiver记录原DRAM完整恢复。ram-cache-qemu-timeout-verification.json只证明负向证据一致、8秒预算生效与恢复记录，不把任何失败当全窗口通过。直接循环及指令时钟均未采纳，当前源码只含已实机测至64MiB的Basecore页边界路径。

下一步需要解决完整256MiB的功能验证与有界运行、跨页别名和分配合同，再进入手机有效DarwinBoot/XNU交接。可评估减少通用engine逐字双层回调的开销，但这是待论证的实现方向，需要保留原备份/Dirty/PoC/RO恢复语义和实际C模型、异常注入及机器码证据；不是已实现或已验证的方案。不能根据本轮64MiB时延线性外推全窗口通过，也不将修改模拟器时间或简单放宽预算作为证明。


## 直接回调版完整256MiB手机实测通过（2026-10-28）

本轮4KiB/1MiB/64MiB/256MiB依次进行两阶段临时启动、原字/RO恢复、Android返回和正常重启清理，全部绑定d0a54cc50f47e6996b1a8b970f0032a8c94d71c4，UniXNU为40d21cc65171c3a24faa130a2a8e899f85790485；每份149项固件输入和22项验证脚本逐Git blob与归档快照核对。新阶段3分别为142732Z/143440Z/143848Z/144256Z，实测0.0990104167/23.778125/1521.8653125/6087.08453125ms；未更改8秒预算。

完整窗口为本机来源约束的0xc0000000..0xd0000000，连续65536页全部完成并恢复，图案67108864个64位字、原字恢复33554432字均零差异，Dirty/BackupWords0、摘要3761833498104544988相同；pre/post同步65536/196608次、RW/PAR和恢复RO写拒绝256点。两阶段build为20261028T142442Z/20261028T144222Z，手机run为144040Z/144256Z。阶段3boot SHA256 41cbf90784019284fb4863372ce21b0a22a1e2d56414ec2a8cf3ed4701f8fbbb，FD 2a77e1665d368f769e8fc7e12b09ca04cc086b80b956c5d9b28506813bf7f04d。

144408Z最终正常重启清理通过，Android/root/原boot哈希正常、临时属性消失；当前没有进行中的手机实验。validate_ram_cache_evidence.py的独立核验20261028T144645.527035Z-b5pgi14w重新读取全部5份范围索引及各不可变wire/FDT/log、Git/冻结镜像/源码、正常重启的原命令记录，最大范围268435456字节。原字恢复事实来自固件逐字比较回传，不冒充在Android中再次读取完整原DRAM。原备份未改动，没有flash/erase/format。完整原始证据仍为私有，公开仅来源/哈希/诊断结果。

私有镜像预构建曾有3次秒级目录命名冲突，在创建镜像前退出；失败日志保留于direct-20261028-pages1/256/16384目录。随后串行重试，不覆盖旧目录或放宽门禁。四次旧版本QEMU全窗口失败及恢复证据也保留，新版QEMU/手机通过不重写历史。

分配器仍仅使用原16MiB诊断arena；这次逐页可恢复写不证明跨页别名、长期隐藏DMA所有权或分配合同。下一步独立实现跨页同时标记、异常恢复及其门禁，再建立连续分配合同并推进手机有效DarwinBoot/XNU交接。完整移植目标仍未完成。


## 扩展initrd与AndroidReturn入口实测（2026-10-29）

独立initrd-geometry 204315Z实测输入FDT 0x845e8000、完整扩展initrd 0x847e9000..0x856fec8e；204929Z/205204Z成功SEC原始记录再次确认该输入FDT。地址是相应镜像的入口观测，不是固定bootloader ABI。返回内核为本次采集的定制Android raw Image 46,813,200字节、声明56,696,832字节；先前不能只按raw长度布置页表。高段0xd01c0000..0xd0200000由已门禁258MiB策略末尾计算并实际用于stub/栈/scratch/state，没有全面测试额外2MiB。12MiB arena是小规模设计预算；所有initrd、FDT、输入栈/LR和reserved区域仍在当轮检查。详见ANDROID-RETURN.zh-CN.md及其原始private证据。


## 独立大载荷 arena 实机范围

本机审计选择 0xd0400000..0xd3c00000 的56MiB实验性arena，0xd3c00000..0xd3d10000为FDT副本；stage3/6通过只覆盖相应编译输入和现场保护区检查，不证明全部RAM/隐藏DMA所有权。实际下载Image仅25,559,040字节，不能将中间洞算下载或可用区。详细来源、失败和结果见NATIVE-STAGING.zh-CN.md。


## 手机XNU原始入口前缀实测（2026-10-29）

4f66e91的230308Z：原DarwinEnter之后执行5条原XNU指令，checkpoint/ELR0xc042606c、ESR0xf2005350、x0/x20=0xc1274000、x1=0xc0424488、x21=0、EL1、MMU/cache关闭、vector slot4。本机CNTFRQ19.2MHz/affinity0，恢复原指令和UEFI翻译并再次核对10段CRC/零尾/args/ADT。381项输入与原回传独立复核，见NATIVE-ENTRY.zh-CN.md。这些是当前实验grant/插桩入口事实，不是XNU自身页表、CPU平台/GIC/timer初始化或完整RAM所有权。自动Android返回及正常重启/root/原boot/清理通过。


## 手机XNU自身页表切换事实（2026-10-29）

2026-10-29。手机234327Z已实测原XNU建立bootstrap页表、设置翻译寄存器、开启MMU并到达高VA arm_init首指令检查点。72Q记录和完整64KiB页表通过，4表页/258非零描述符/128组block；全部临时代码、页表与UEFI状态恢复，原10段CRC/零尾/args/ADT重验通过。80.516秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。389项Git输入及原始证据独立复核，详见[NATIVE-MMU.zh-CN.md](NATIVE-MMU.zh-CN.md)。arm_init C函数体、XNU平台/GIC/timer、根卷与用户态仍未执行。下一步建立C初始化阶段的可恢复日志，推进平台初始化。未同步上游，RAM alias暂停，原备份未改动；当前手机正常Android，无运行中的实验。

本轮软件布局由固定Mach-O提取，实际读回ELR=0xfffffff007a11bfc，ESR=0xf2005351，TCR=0x22a51a251a，MAIR=0x0c0804ff00bb44ff，SCTLR=0x3454593d，TTBR0=0xc017e000，TTBR1=0xc017f000。页表快照65536字节、SHA256 09ac5aecee04da17d7ca7ebdda82983455d194c75e81149072f8c24b0f741ddc；与256MiB实验grant的原bootstrap算法一致，但首部向下对齐导致末16KiB未映射。此为插桩阶段事实，原向量入口被诊断relay替换，尚非XNU正常fault处理或最终pmap、全RAM/隐藏DMA所有权结论。


## 手机arm_init C初始化前缀与原字恢复（2026-10-29）

2026-10-29。手机001904Z已执行原arm_init C初始化并到达arm_vm_init首指令，原平台首次初始化/拓扑/当前线程和早期时钟/启动子系统前缀已通过该检查点。2,637,824字节三个数据/栈段完整备份恢复；130,896字节/10,908个变化64位字独立重建，原10段CRC/零尾/args/ADT及UEFI状态恢复通过。80.434秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。396项Git输入与原始证据独立复核，详见[NATIVE-EARLY-RECOVERY.zh-CN.md](NATIVE-EARLY-RECOVERY.zh-CN.md)。arm_vm_init函数体、pmap重建、正常XNU IRQ/timer生命周期、根卷和用户态尚未验证。下一步处理pmap切换后的日志与恢复；原TTBR0将被置为空表，现有物理别名relay不能直接沿用。当前手机正常Android，无运行中的实验；未同步上游、写分区或改原备份，RAM alias暂停。


2026-10-29补充：QEMU原arm_vm_init已真实换TTBR1/置空TTBR0并返回，66页活动页表、644页高地址数据映射及7处完整快照经396份冻结输入独立复核。手机仍仅到arm_vm_init入口。下一步独立TTBR0转换表恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)；未同步上游。


2026-10-29：stage12换表后恢复已实现，QEMU正向36项及同镜像独立5场景通过；旧stage11回归31项通过。手机仍以001904Z的arm_vm_init首指令为准，stage12尚待最终冻结构建、旧分支回归和本机布局预检。原始TTBR与诊断转换根分开，输入ADT的random-seed清零由独立备份恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。上游未同步、RAM alias暂停、原备份未改动。


2026-10-29。手机011328Z的stage12通过：原XNU arm_vm_init完成并换TTBR1/置空原TTBR0，在PE_consistent_debug_inherit首指令捕获后完整恢复3段/原代码/初始表和输入ADT。66页活动表、644页高数据映射及132936字节delta通过；80.337秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。405份Git/blob/冻结输入与原始回传独立复核，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。尚无正常XNU IRQ/timer生命周期、根卷或用户态。下一步推进pmap后的平台初始化与持续日志。未同步上游、未写分区、原备份未改动；当前正常Android且无运行中的手机实验，RAM alias仍暂停。
