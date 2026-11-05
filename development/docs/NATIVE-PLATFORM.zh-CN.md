# XNU 平台初始化到 machine_startup

2026-10-29，主线继续推进；只使用固定上游，没有 fetch/pull。用户要求加快实机迭代，停止逐文件哈希和重复独立证据绑定。保留构建产物标识、镜像结构门禁、运行回传和恢复检查。

## 源码实现

新增默认关闭 `--platform-test` / `PcdRaphaelNativePlatformTest`，依赖现有 pmap/early/mmu/entry/exit/load 路径。目标从固定 Mach-O 的 `_machine_startup` 符号提取，首指令 `0xa9bf7bfd`；唯一原 BL 的 LR 与 arm_init 的 208 字节栈从原机器码推导。early policy version/flags 为3，旧1/2配置保留。MMU记录仍是既有72Q/version2；不修改原始内核文件、不绕过平台函数。

固定实际编译源码 `artifacts/native-bootstrap/raphael/ipados-17.7.11-21H461/raphael_cpu/tree/.cache/xnu-work/` 的 `osfmk/arm/arm_init.c` 执行 serial/kprintf、console、idle、第二次 PE_init_platform、cpu_timebase_init、kptimer_curcpu_up、PE_init_cpu、fiq_context_init，然后进入 machine_startup。`pexpert/arm/pe_identify_machine.c` 无 arm-io 时返回，`hwtrace/hwtrace.c` 无gSocPhys时跳过MMIO；当前ADT不提供Apple串口或Apple debug寄存器，不能当真实串口输出。

`osfmk/arm64/machine_routines.c` 的 fiq_context_init 将 CNTV_CTL 写1、CNTP_CTL 写2；时钟/event-stream路径还会改 CNTV_CVAL 和 CNTKCTL。新增144字节/18Q平台记录：保存、观察并恢复 CNTP_CTL/CVAL、CNTV_CTL/CVAL、CNTKCTL；异常返回仍屏蔽DAIF，先mask两个源、恢复CVAL/CNTKCTL，再恢复可写CTL位，读回验证。ISTATUS是派生位，只比较可写控制位。此也补足早期路径CNTKCTL未纳入恢复的问题，但不追溯改写历史实验结论。

既有256MiB grant转换表、三个可变段备份、ADT恢复继续复用。没有扩RAM/备份范围，也没有应用RAM alias stash。

## 主机编译与镜像结构

新profile已通过实际Mu编译及PE/FV结构检查，独立手机产物待生成。无需重新构建未变的XNU。

## QEMU运行

原函数观察 `artifacts/native-post-pmap-qemu/20261029T013542.741539Z-cflgqrf1` 的20个停止点通过，捕获第一次kprintf参数 `kprintf initialized\n`，serial_init返回0，不证明有UART输出。machine_startup入口SP仍为原interrupt_sp减208，x0为const_boot_args。

第一次新profile运行 `artifacts/native-staging-qemu/20261029T014055.498182Z-2c7dt4m7` 已到达目标并恢复，但错误地要求观察CNTKCTL等于原值而被拒绝；原输出保留。根据实际event-stream源码纠正为核查只改变允许位，并完整恢复原值。

最终 `artifacts/native-staging-qemu/20261029T014353.129369Z-hmmcqyuw` 38项通过，包括目标PC/LR/SP、原参数、活动页表/三个数据段/ADT和定时器恢复，以及回到独立接收器。它不证明手机或正常XNU IRQ生命周期。

复现：

```sh
python3 scripts/run_native_staging_qemu.py --stage 6 --load-test --exit-complete --entry-test --mmu-test --early-test --pmap-test --platform-test
```

## 实机验证

尚未执行新profile。下一步同配置手机构建、临时fastboot boot、回传目标与timer状态、自动回Android。`--runtime-only` 不再反复读boot分区计算哈希；明确记录该项未检查，不将它写成通过。原备份保持只读不改动。


## 手机首次尝试失败与定位

实现6b69420，手机构建 `evidence/private/android-return-build/20261029T014607.988748Z-y6p37dsc`，执行 `evidence/private/android-return-run/20261029T014730Z`：临时镜像被接受，147秒内没有ADB/fastboot/对应USB设备，未得到XNU回传。随后用户长按电源恢复Android，root读取通过。此轮不能声称手机到达machine_startup，也不能用QEMU成功替代。仅fastboot boot，无分区写入；runtime-only未重算boot分区哈希。手动恢复采集在同目录manual-recovery中；当前Android未提供/sys/fs/pstore。

已从上次手机stage12的const_boot_args快照确认Boot_Video六字段为零，不能把失败归因于已启用的framebuffer。增加精确可选检查点serial/console/idle/timebase/cpu/startup，均从原Mach-O符号/BL/栈提取；原三个段及timer恢复不变，中间目标不编造x0参数含义。

platform policy剩余3Q用于两个panic入口和目标编号，224字节大小不变。临时在_panic/_panic_with_options首指令安装BRK #0x5353；异常仍恢复全部原字与timer，因PC不同将明确报告目标失败，并尽量从原内核文字段解码panic格式。该机制不接管正常内核异常，也不把panic当通过。

console目标QEMU `artifacts/native-staging-qemu/20261029T015736.349871Z-rjyedsbn` 38项通过。下一手机测试先停PE_create_console入口，定位首次无法返回的位置；这是故障定位，不能声称startup已完成。


## 2026-10-30：idle检查点手机尝试失败，暂停

本轮只推进一个实机目标：固定本机XNU从已证实的 `_PE_create_console` 入口继续到 `_cpu_machine_idle_init` 首指令，并返回可解码记录。运行前手机处于Android；仅使用临时 `fastboot boot`，未写/擦分区。runner使用runtime-only，故没有核验boot分区哈希。

实机镜像 `evidence/private/android-return-build/20261029T171957.389946Z-ulsclzma/boot-android-return.img`，镜像SHA256 `f893b54c130144ecac3a1630afd117d2d138529e1d5f702da09337ba97c24350`；固定XNU SHA256 `67964d23522f5a093c5199934cc2c512afdddff749961f9dbdfac293f9509e21`。相较前次idle失败镜像，该内核包含 `CONFIG_XNU_DT_PANIC_REGION=y`，仍使用 `kt_fixed_zones=200`，并集成硬件看门狗结果记录。看门狗计数仍取驱动默认频率32765 Hz，实际硬件计时未测，不能据此确认复位时长或原因。

同配置QEMU产物 `artifacts/native-staging-qemu/20261029T171838.097816Z-ook48x2t/report.json` 通过38项，目标检查点编号2，定时器恢复通过；该项仅是QEMU执行结果。

实机run `evidence/private/android-return-run/20261029T172138Z/report.json`：临时boot被fastboot接受；91.123秒后Android完成启动，root、新boot_id、Android清理及临时属性消失通过。但回传FDT的nonce不匹配，本轮没有SEC、native-MMU、native-early、native-pmap、native-platform、watchdog或Android-return记录。run目录没有内核串口日志或panic回传。故本次检查点失败且停点未知；不能判断XNU是否开始执行、是否到达console、是否发生panic，也不能断定看门狗导致Android返回。此结果排除了设备无法接受该临时Image及Android无法自动恢复；没有证明panic-region改动消除了阻塞。

**暂停条件已触发：日志合同未闭合。** 同一镜像不重跑，也不追加第二次实机尝试。手机目前Android/root已确认，临时属性清理通过，未操作分区或原备份。等待reviewer审阅并决定后续如何取得足以判断停点的日志。完整移植、正常Darwin启动、IRQ/timer生命周期、根卷和用户态均未验证。

## R1：stage13 回传缺失的路径分析

本分析只依据冻结产物、原始回传和源码。回传缺失不能证明 XNU 没有执行，也不能证明看门狗触发。

| 节点 | 路径、记录与失败可见性 |
|---|---|
| Image / SEC | fastboot boot 接受只证明镜像传输被接受。Sec.c 入口设 Stage=1 并输出 SEC DEBUG；SecEntry 先校验 FDT/几何/profile，FdtOpenInto 成功后才写 raphael,sec-dxe-id 并设置 D->FdtCopy。nonce 前失败没有可导出的诊断 FDT，且主机不采 DEBUG。 |
| watchdog / XNU handoff | SEC 按输入 FDT 校验并映射 qcom,msm-watchdog。NativeLoadTest.c:RaphaelNativeExitReturned 仅在验证 ExitBootServices 返回后 Arm；DarwinTest.c 随后调用 UniXNUBootEntry，之前有 NATIVE_XNU_READY DEBUG。arm 前失败可走 SEC 返回；arm 后结果只在易失 RAPHAEL_NATIVE_MMU_STATE。 |
| 检查点 / 返回 | NativeMmuTest.c:RaphaelMmuCaptured 收到 BRK 后停止并恢复 watchdog、平台状态、页表和指令；RaphaelNativeMmuFinish 再由 SecFinish 序列化 stage 13。正常 RaphaelFinishAndroidReturn capsule 带修改后的 FDT 返回；runner 在 Android 启动后才读取 /sys/firmware/fdt。 |
| 复位 / 主机采集 | 硬复位会丢失 RAM FDT 与 arena 状态，后续 Android 提供普通启动 FDT。commands.json 只有 ADB/fastboot 操作，没有 XNU 运行期日志；本机 UART 输出也未验证。 |

### 可排除与未决

- 可排除：fastboot 未接受镜像；也可排除经预期诊断完成路径、携带本轮 nonce/FDT 返回 Android。报告 nonce_matched=false、sec_record_found=false，after.dtb 无 raphael, 属性。
- 未能区分：是否进入 SEC；是否在 nonce 建立前退出；是否到 DXE、ExitBootServices 或 XNU handoff；是否在 XNU 检查点前挂起/异常/复位；watchdog 是否 arm/触发；Android 走哪条返回路径。
- 关键缺口：没有经验证、复位前可由主机读取的运行期观测通道。现有 FDT/ADB 数据无法区分“未到 handoff”与“已 handoff 后复位丢失易失记录”。独立 watchdog reset 和 QEMU 38 项均不能填补此缺口。

### R1 当时的下一步建议（已由本轮检查点对照更新）

R1 当时建议先确认复位前 live 主机观测通道，再记录 SEC、handoff 前及 idle trap。该建议是针对 stage13 缺失 FDT 回传的分析，不是外接日志作为所有实机实验的前置条件。本轮已按已批准的检查点对照，沿用现有 capture→Android return→FDT 读取路径测试当前配置下更早的 console 检查点；结果见下方 2026-10-30 小节。

当前实现核实：`uefi-raphael/RaphaelPkg/Library/RaphaelDiagnosticDebugLib/Debug.c:8-13` 的 SEC/DXE `DEBUG` 只追加到易失 `D->Log`（QEMU gate 开启时另写 semihost）；`Diagnostic.dsc:195` 将 `SerialPortLib` 绑定为 Null。`SecFinish`（`Sec.c:195` 起）才把记录序列化进 FDT，runner 只在 Android 返回后读取 `/sys/firmware/fdt`。因此现有 handoff 前标记既没有手机 UART 出口，也不能在 watchdog 复位后从 RAM/FDT 取回；idle trap 同样只走易失结果，不能形成此次所需的复位前主机证据。

本轮修正 runner 初始化字段：`xnu_executed` 从 `false` 改为 JSON `null`，仅在成功解码 native-entry/MMU 记录时置 `true`。缺失记录代表未知，不再被报告成“未执行”。冻结的旧 `report.json` 保持原样；其中 `false` 是旧 runner 默认值，按本次源码核查应解释为未知，不能据此认定 XNU 未执行。这只修正后续报告语义，不增加观测能力，也不改变 `experiment_passed` 门禁。

本轮对照没有取得有效回传，因此仍无足够证据确定停点。后续步骤由 reviewer/planner 审定；缺少外接日志本身不构成禁止实验条件，但任何新实验都须有具体假设、预定可判读结果与恢复路径。不得把普通 Android 返回解释为 XNU 未执行或 watchdog 已触发。

## 2026-10-30：当前配置 console 检查点对照

只比较旧 console 成功镜像、stage13 idle 失败镜像和本次 console 对照的直接相关配置。旧成功 build/run 为 `evidence/private/android-return-build/20261029T020006.728912Z-_dgpntcd` / `evidence/private/android-return-run/20261029T020256Z`：XNU Mach-O SHA256 `96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722`，early policy `reserved2=1`（`_PE_create_console`），无 watchdog qualification，也未配置 `kt_fixed_zones=200`。回传 nonce、MMU/platform 记录及正常 Android 清理均通过；该记录证明的是那份旧内核与旧配置下的 console 入口。

失败 idle build `20261029T171957.389946Z-ulsclzma` 与本次对照 build `20261029T184952.109058Z-ar5rjf66` 使用相同当前 XNU Mach-O SHA256 `67964d23522f5a093c5199934cc2c512afdddff749961f9dbdfac293f9509e21`、watchdog base `0x17be0000`/frequency `32765`/配置20秒、`kt_fixed_zones=200`。当前内核的 `CONFIG_XNU_DT_PANIC_REGION=y` 已由该构建合同确认；旧成功镜像是否同配置没有证据。三份镜像报告中的 `layout` 完全相同（Image、FD、stack、arena、FDT 各基址/大小）；capsule 中 Android kernel/ramdisk 的大小与 SHA256、Android-return stub SHA256也相同。SEC/DXE 返回代码采用同一 `SecFinish`→Android-return capsule→runner 读 Android FDT 路径；当前分支增加 watchdog arm/stop 与状态回传，旧成功镜像没有该 watchdog。当前 idle 与新 console 镜像间唯一行为配置变化是 early policy 检查点 ID `2`→`1`，固件/镜像哈希随目标和新 nonce 改变。

新 console 目标的 QEMU/结构合同 `artifacts/native-staging-qemu/20261029T184857.934569Z-yn8j9vuk/report.json` 38项通过；这仅说明当前内核下目标编号1的捕获/恢复路径可构建及模拟器通过。本次手机镜像结构检查通过，镜像 SHA256 `6877f88e2cfe8e6ac9c014e15825b125053ad1c128542ae36d062a3502beac15`。唯一一次临时启动记录 `evidence/private/android-return-run/20261029T185111Z/report.json`：fastboot 接受；90.967秒后 Android/root 恢复；boot 分区前后哈希相同；普通重启、root和临时属性清理通过。但 Android FDT 无本轮 nonce、SEC、native-MMU、watchdog、platform 或 Android-return 记录，PC 未知，实验失败。

因此当前配置下更早的 `_PE_create_console` 检查点也没有实机证据。不能声称 XNU 已进入/越过 console，不能继续把停点归因于 console 内部，也不能由约91秒恢复推断 watchdog 触发。结果排除了 fastboot 拒绝本镜像和 boot 分区被本次操作改写；未区分 SEC/nonce 前退出、handoff 前阻塞、XNU 更早处挂起/异常，或复位后易失记录丢失。按单次对照规则停止，不重跑。

本轮后续实验门槛：没有外接日志本身不禁止实验。只有当假设、预期的正负结果、所需证据以及恢复路径预先明确，且构建/镜像结构/boot 与 Android 恢复检查通过时才运行；没有有效回传不得登记为新增实机进度。当前 console 对照未产生有效主线证据，原 idle 目标保持暂停并交 reviewer 审查。


## 2026-10-30：修复真实 FDT 总线解析后，startup 实机通过

旧文档两处 0x17be0000 为转写错误；实际旧产物 native_watchdog.base=398524416，即 0x17c10000，与本次 live FDT 和 Xiaomi 固定源码相符。
真正可重现的 SEC 阻塞是要求 /soc ranges 为空：本机为16字节显式恒等 tuple。新增共享恒等资源校验后，本机 machine_startup 首指令通过，run 20261030T070604Z，PC=0xfffffff007427d30；当前内核、kt_fixed_zones=200、watchdog 启停和完整状态恢复均有有效回传。手机自动恢复Android且清理通过。完整记录与后续桌面主线见 DESKTOP-MAINLINE.zh-CN.md。历史无回传实验保持停点未知，不追溯改判。
