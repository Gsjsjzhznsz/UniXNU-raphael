# 物理PPI专用TimerArch

2026-10-28。本轮独立实现PhysicalTimerDxe，复用固定Basecore CpuDxe、异常向量和DXE事件核心；通用源码没有修改。这里只接管本轮FDT解析的物理PPI，手机预期18，模拟器30；不把模拟器编号带入手机。

## 实现边界

SEC先重新执行GIC/ICC/两遍NS enable map和单次IRQ完整恢复，再生成专用HOB。GICD/GICR地址、范围、启动CPU帧及PPI均来自同轮输入；只建立device映射和MMIO保留HOB，DXE重新检查使能、pending、active、RWP、WAKER、DAIF、EOImode、CNTP及ICC组门禁后才开放目标PPI。没有全GIC初始化，也没有写虚拟、Secure或hyp timer。NS enable视图不代表Secure所有权或原子快照。

固定CpuDxe收到HardwareInterrupt协议前仅维护影子中断开关，因此驱动同时安装只接受目标物理PPI的HardwareInterrupt和TimerArch协议；其注册动作本身不使能目标。固定通用ArmGic的RegisterInterruptSource则会调用EnableInterruptSource，已核对准确源码。没有用通用TimerDxe注册四源。

物理定时服务设计周期初始10ms，测试切换5ms；支持1us至1s范围，其余拒绝。硬件周期向上取整。IRQ通过固定异常库保存完整上下文，IAR后先屏蔽物理source、确认读回，再EOI；只支持EOImode0。按物理counter修正延迟和上报经过的100ns时间，避免补周期的无界循环。诊断服务生命周期上限10秒。未知ID会EOI、记录失败并在返回SPSR保持IRQ mask。

退出按source→ICC组→GICD组→目标PPI的顺序撤销，等待正确的D/R RWP位和pending撤销，恢复CNTP CTL/CVAL及DAIF，核对enable/active和虚拟timer未变。Shutdown通过SEC状态/HOB指针可达。结果448字节，状态总464字节，在物化SEC数据中，未扩大接近上限的context。

## 主机、结构与模拟器

新增63项独立wire破坏/交叉验证、58项实际C ABI断言；复用了105项实际C路由/恢复检查及单次IRQ32项wire/25项C断言。独立审计固定上游CPU/IRQ/事件协议，检查优化后C代码的MSR范围和允许的ArmLib调用。ArmLib汇编目标含未调用的其他timer函数，不把整个链接镜像所有MSR误判为执行调用。

同一包内源码快照：

- SEC stage2：artifacts/sec-dxe-qemu/20261028T010442.103184Z-n2v1s6gq/report.json，55项通过。
- MMU stage3：artifacts/sec-dxe-qemu/20261028T010442.103157Z-05tzuyyf/report.json，55项通过。
- DXE stage6：artifacts/sec-dxe-qemu/20261028T010442.103092Z-e3hvc7gh/report.json，64项通过；IRQ/EOI各60、notify60、周期回调5、无spurious/unknown、恢复成功。
- route-local UDF恢复：20261028T010442.103382Z-7typr_4o，51项通过。
- 默认/BRK/白名单外UDF：20261028T010442.103069Z-c4_coxnk，41/38/38项通过。
- 原通用CPU/GIC/TimerArch/UniXNU/Darwin拒绝路径：20261028T010442.103181Z-6672zdzm，60项通过。

事件测试包含100ms relative、20ms periodic至少5次、取消后100ms回调不变、SetTimerPeriod(0)后100ms IRQ计数不变。非法period、NULL GetPeriod、重复Notify注册、其他INTID请求与未确认EOI均验证拒绝且服务继续。所有等待另有物理counter与轮询数上限。

开发失败保留：最初镜像检查器缺新驱动白名单；005941.632355Z-_1nwtb_c被DAIF门禁拒绝，未开放持续IRQ。原因是自有DebugLib无条件启用DEBUG_CODE，固定CpuDxe由此解除SError屏蔽；现已按PcdDebugPropertyMask=0x03返回false。010149.726324Z-q9d1kwg0是修复后首个成功，但缺后加的负向协议/停表稳定测试，最终依据010442的完整回归。主机审计的字段破坏边界、LTO/汇编范围及路径修正没有在手机执行失败版本。

构建命令：python3 scripts/build_sec_dxe.py --physical-timer-arch [--stop-after-stage 2|3]。手机生成命令：python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --physical-timer-arch --stop-after-stage 2|3|4。4代表完成DXE并回传stage6。各次日志、命令、产物和快照位于对应私有/主机目录。实机结果另附，当前尚未据此宣称手机TimerArch通过。

## 下一步

按同一源码分阶段临时boot手机；确认日志、寄存器恢复、Android/root/原boot哈希及正常重启清理。随后集成完整UniXNURun倒计时。16MiB诊断arena仍不能满足DarwinBoot至少256MiB窗口，真实XNU尚未构建或运行。

## 手机实测（准确来源绑定）

实现提交33481c8072624336f3872951c0be3aa4b2fb262b。84板级+47 UniXNU包内输入逐项与Git blob及各构建快照一致，11项主机脚本另行绑定；stage2/3/6绑定文件分别保留，主索引为physical-timer-source-binding.json。三个阶段均为临时fastboot boot，未flash/erase/format。

| 阶段 | 手机运行 | 构建 | FD SHA-256 | boot SHA-256 |
|---|---|---|---|---|
| SEC2 | 20261028T011425Z | 011133Z | 3aca44083aa9025c768fc8da47574c5d4efbb9f8a818fda28eb543f6c2ce4e35 | 55a2212d949a9e023a4874081d950f66acc7c5c84551e084bdc5f04db030968b |
| MMU3 | 20261028T011849Z | 011705Z | eecf2a3460e2925b186768b3c63e086eb69ddfb3fccb36ca234feb7fba40b9ff | 7382acd65c9fde72ade8444d6d6b1cfac6dbee5be3da3ecb29bbc87dab7c9aac |
| DXE6 | 20261028T012324Z | 012129Z | 416a700a1a84c8c10ea553f73e06603a7b68082df8506a9700557102320c7295 | 727969edd91113bf9b8ae4826288d76390c482da484494c3efe01fc14bf2c416 |

同轮手机FDT解析INTID18/flags0xf08、19.2MHz；GIC窗口仍由本次输入动态解析。SEC2完整单次IRQ恢复通过；MMU3 device映射读取一致；DXE6安装真实Cpu/HardwareInterrupt/TimerArch并经DXE Core事件测试。IRQ61、EOI61、notify61、spurious0、unexpected0。relative1920035 ticks约100.001823ms，periodic5次/2015975 ticks约104.998698ms；取消后1920000 ticks=100ms回调稳定，停表后另100ms IRQ不变。开始1097682378、首次IRQ1097786947、末次1103546943、结束1105467218。

完整恢复：D_CTLR0x10、IGRPEN1/CTL/CVAL/enable/active均0、pending0x10080000、DAIF0x3c0；虚拟CTL5和CVAL258603056未变。状态4、Reason0、RestoreOk1。结果状态464字节在SEC物化数据RVA66176/FD168576/physical2204996224，未扩大context。

三个阶段Android启动完成、root和原boot哈希均通过，011629Z/012129Z/012639Z各自正常重启清理成功，临时属性消失。公开元数据为boot-physical-timer-observation.json、sec-physical-timer-stage2/3/6-handoff.json及各immutable attempt；原始日志和镜像仍私有。

这是有界诊断TimerArch的实机证据，不是完整UEFI、常驻服务、UniXNURun、DarwinBoot或真正XNU成功。下一步保持上述已证实边界并集成完整管理器倒计时。
