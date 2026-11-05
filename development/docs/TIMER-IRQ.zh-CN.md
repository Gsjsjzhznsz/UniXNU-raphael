# 本CPU物理timer单次IRQ窗口

2026-10-28，Asia/Shanghai。默认关闭，只支持stage2，要求同轮GIC/ICC、NS enable两遍全零、timer路由及HPPIR/pending已经确认目标到达。它不初始化整个GIC，也不是完整TimerArch。

## 异常窗口

独立TimerIrq.S是有界leaf。重新检查EL1、DAIF全mask、SPx/SPSel=1、ICC EOImode0；只在既有SEC栈上运行。先登记位于SEC .data的活动结果指针，才解除IRQ屏蔽，保持FIQ/SError/debug屏蔽。窗口由100ms物理counter和1000000次循环限制，未用WFI。只有当前EL SPx IRQ向量进入专用handler；活动指针非零且ELR在链接后窗口边界内才允许处理。

handler保存x8-x17共80字节，不改x0-x7、x18或callee-saved，不调用C。读取IAR1确认一个中断，记录INTID、counter、ELR和实际SPSR。先写CNTP_CTL2并读回可写位确认为2，再EOI；仅接受EOImode0，因而不写DIR。返回SPSR只增加IRQ mask，首个异常后立即重新屏蔽。窗口退出清零活动指针并读DAIF，随后执行既有完整GIC/CNTP恢复和pending/active核验。

未知或spurious ID使窗口失败。1020..1023特殊ID没有确认、不能EOI；其他实际确认的未知ID仍EOI，避免遗留active状态，但不算支持该中断。窗口外异常走既有诊断返回。这里没有通用IRQ分发、周期回调、UEFI事件或TimerArch完成结论。

## 证据约束和来源

IAR/EOIR指令与独立GNU assembler、MiCode固定663db50e…sysreg.h逐编码核对；Arm IHI0069C 8.2.14说明确认语义和特殊ID，8.2.10及中断deactivation章节说明EOImode0。来源文件哈希/行号/PDF页码见timer-irq-source-audit.json。既有SRE、HPPIR、IGRPEN1可访问是本模式前提；不能据此保证EL2/EL3异常恢复。

192字节结果和8字节活动指针均由linker map、FD实际零字节、SEC .data/XIP/PE/FV边界核对。C实际sizeof/offsetof的25个断言固定24项wire布局；Python独立解码检查IRQ实际SPSR为0x340、DAIF前后0x3c0、EOI/目标进入次数各1、80字节handler SP差、ELR在链接窗口范围、counter在100ms内及恢复结果。栈来自已实测诊断预算，不引入其他手机地址或新的RAM区。

## 主机、模拟器和镜像

- 实际C/FDT/UBSan路由105项，包括可选IRQ leaf的成功、拒绝、前提失败不调用和缺结果指针；旧route入口保留。
- IRQ wire破坏/边界32项，实际C布局25断言；初始host测试正则误读原型、stddef与EDK NULL宏冲突，均已修正，失败日志保留。
- 自有QEMU真实IRQ路径54项：实际IAR/EOIR一次，SPSR证明只有I被解除，source mask读回与恢复通过。
- 同源码route-local UDF恢复50项、默认normal/BRK/白名单外UDF40/37/37项、完整模拟TimerArch/UniXNU/Darwin拒绝路径59项通过。模拟器初始条件stub仍不进入手机FD。
- 手机候选003329Z：FD SHA256 48a908b6f7a123736e452918b40f0f96a68916e38d6104263110f75f869c7068；boot SHA256 913b324842f657ddef34f1a646c2d543064e8ca110b94dd4bf1c87baec3a0f7c。编译、结构和结果存储检查通过；本节写入时尚未实机。

```sh
python3 scripts/validate_timer_route.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --gic-enable-map --timer-route-test --timer-irq-test
python3 scripts/validate_timer_irq.py --qemu-report artifacts/sec-dxe-qemu/20261028T003133.680298Z-cd0l7gtv/report.json
python3 scripts/audit_timer_irq.py --qemu-report artifacts/sec-dxe-qemu/20261028T003133.680298Z-cd0l7gtv/report.json
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --gic-probe --icc-probe --gic-enable-map --timer-route-test --timer-irq-test
```

手机结果必须绑定源码/镜像/nonce、原boot哈希、Android/root及正常重启清理，不能用模拟器或编译成功替代。

## 实机单次IRQ结果：20261028T003635Z

IRQ status5，目标与IAR实际ID均18，Entries1/EOI1，source mask写后读回通过，无spurious或未知ID。窗口counter1074224279，IRQ counter1074224333，结束1074224393；54ticks约2.8125微秒内确认已pending的timer。IRQ ELR0x836bf1a0（在本轮链接窗口内），实际SPSR0x345，其DAIF部分0x340；窗口前后DAIF均0x3c0。SPx=1，handler栈比窗口SP低80字节且位于诊断栈内，活动指针清理。

随后原路由完整恢复：active0、pending0x10080000、HPPIR1023、D_CTLR0x10、IGRPEN1/CNTP_CTL/CVAL均0。nonce/stage2/status0、Android/root/原boot哈希通过；003910Z正常重启清理通过。80板级+47UniXNU输入和15项脚本逐Git blob/构建快照绑定42246fbbed0058b3f9ffcd74ee9c8a536a979a4c。见timer-irq-source-binding.json及boot-timer-irq-observation.json。单次IRQ不是持续TimerArch或完整UEFI；没有flash/erase/format或备份修改。
