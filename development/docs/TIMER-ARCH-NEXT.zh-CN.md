# TimerArch之后的下一门槛

2026-10-28：下文设计已由独立PhysicalTimerDxe落实，并经手机SEC2/MMU3/DXE6验证。PPI18持续61次IRQ/EOI、relative/periodic/cancel/停表稳定和完整恢复通过。准确源码/哈希/阶段见PHYSICAL-TIMER.zh-CN.md。下一步为手机完整UniXNURun倒计时与RAM交接，常驻TimerArch尚未完成。

## 本轮采用的设计约束（保留）


单次PPI18 IRQ/EOI已实机验证，但不能直接安装原通用TimerDxe：固定Basecore的TimerInitialize会为virt/hyp/sec/phys四个timer PPI注册handler。此前ICC实测CNTV_CTL=5，虚拟timer仍启用且到期，直接启用其PPI可能引入未经本项目处理的中断。准确Git版本、源哈希和四处注册行号见timer-arch-upstream-review.json。通用源码仍未修改，也未在手机安装该驱动。

下一实现应保留固定CpuDxe/ArmExceptionLib及DXE Core，独立提供仅本机物理PPI18的TimerArch板级实例。资源仍从同轮FDT/GIC/ICC/map门禁生成，不能套用QEMU全GIC初始化。保持虚拟timer和其他CPU/中断配置，先在模拟器验证标准协议、相对事件、周期回调、取消及恢复，再分SEC/MMU/DXE阶段临时boot手机。

必须在MMU中把GICD/GICR作为device映射及HOB保留资源，CPU注册目标handler后才开放目标PPI与组；失败/超时或诊断返回时先停止源，再关闭接口和分发器，恢复原CTL/CVAL/enable/DAIF并核对pending/active。测试使用物理counter双重上限，避免依赖尚待验证的timer事件作为唯一超时。结果放已物化的FD数据或已证明归属的分配，不增加接近上限的context。

TimerArch通过后才集成手机完整UniXNURun/倒计时与菜单，随后推进DarwinBoot交接所需RAM与真正XNU平台。当前16MiB诊断arena不能默认为满足DarwinBoot至少256MiB窗口；完整RAM所有权仍未知，不能照搬模拟器地址或抹掉固定保留区。
