# 屏蔽IRQ的物理定时器源实验

2026-10-28。先核实已关闭CNTP的写入、到期与恢复；IRQ始终mask、不修改GIC或虚拟timer，不涉及PPI投递。新模式PcdRaphaelTimerSourceTest默认FALSE，仅stage2且要求同轮GIC和ICC完整。

独立TimerSource.c只接受物理counter、CNTP_CTL、CNTP_CVAL三个selector。再次读取CTL/CVAL，要求仍与刚才ICC一致且ENABLE=0；EL1、DAIF四类mask、SRE、完整16项及频率门禁在任何写入前检查。按CNTFRQ设计10ms到期、100ms超时和1000000次上限；这些是实验预算，不是硬件参数。counter接近溢出、倒退、过早ISTATUS、读写异常或回读不符均拒绝成功。

顺序：设置CVAL并回读，写CTL=3（ENABLE+IMASK），在保持IMASK时等待ISTATUS，然后尝试全部三步恢复：CTL=2禁用并屏蔽、原CVAL、原CTL的可写低两位。无论前面哪一步失败都进入恢复；恢复后独立读取低两位与CVAL。即使一次恢复写失败，后两次也会执行，整轮记恢复失败。CTL只读ISTATUS不要求逐位恢复。

TimerAccess.S仅1条MRS CNTPCT及2条MSR CNTP_CTL/CVAL，写后均ISB；三个精确PC恢复地址沿用仅当前EL同步槽/EC0或0x18的局部机制。编译后指令与独立GNU assembler逐字匹配，48字节恢复表及无栈/callee-saved使用均检查。原16项ICC读取表保持独立。

ENABLE/IMASK/ISTATUS位定义与写后ISB来自MiCode固定663db50e…的include/clocksource/arm_arch_timer.h、arch/arm64/include/asm/arch_timer.h；完整文件哈希和行号见timer-source-audit.json。没有引入其他板型地址或IRQ。

## 分层验证

- 实际C/UBSan、前后64字节canary、独立wire共82项通过。包括每个读取位置异常、写入部分生效后失败、所有恢复位置失败、写忽略、source停滞、counter停止/倒退/溢出与损坏wire。
- 初次host测试把中间禁用写被忽略误判为最终必定恢复失败。实际最后CTL写仍能恢复；改正测试期待并补充最终CTL/CVAL写被忽略的失败检查。初始失败日志与目录保留，未宣称82项属于初次运行。
- QEMU 225559.720028Z-abuxbw59正常44项；真正CNTP在IMASK下到期，独立接收器再次MRS核对物理寄存器已恢复、虚拟timer可写状态未变。
- QEMU 225559.719978Z-0_qnbvf0故障43项：CVAL真实改写后，通过ABI受控UDF模拟一次CTL写失败，恢复并独立读回通过。此为失败分支测试，不是真实MSR trap测试。
- 默认关闭stage6正常36/BRK33/白名单外UDF33；完整IRQ+payload+Darwin回归55项均通过。目录见后续源绑定。
- wire为17个大端u64/136字节，status1前提拒绝、2状态变化或不支持、3写异常、4读异常、5回读不符、6超时、7恢复失败、8完整。部分记录只保留诊断，不视为成功。

新手机镜像evidence/private/sec-dxe-build/20261027T225842Z已编译，FD/FFS/PE与boot结构检查通过。FD SHA-256 d7ec41c465d17ba52dc44b08ff523507050668f6fa63e55cb9d081caa0540799，boot SHA-256 ea103470aff68f03e8427f1c58206e8c50b5c60d860089f583f85d3487af670a。尚未执行手机实验，不能把模拟器到期当作手机结果。

```sh
python3 scripts/validate_timer_source.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --timer-source-test
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --timer-source-test --icc-fault-test
python3 scripts/build_sec_dxe.py
python3 scripts/build_sec_dxe.py --payload-test --qemu-arch-test --darwin-test
python3 scripts/audit_icc_probe_sources.py --qemu-report artifacts/sec-dxe-qemu/20261027T225559.720028Z-abuxbw59/report.json
python3 scripts/audit_timer_source.py --qemu-report artifacts/sec-dxe-qemu/20261027T225559.720028Z-abuxbw59/report.json --fault-qemu-report artifacts/sec-dxe-qemu/20261027T225559.719978Z-0_qnbvf0/report.json
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --gic-probe --icc-probe --timer-source-test
```

后续仍须独立验证本CPU/PPI写权限、IRQ路由、有限接管和恢复，再做手机TimerArch及真正UniXNURun/DarwinBoot/XNU。该source实验不提供任何IRQ成功结论。


## 实机结果：20261027T230159Z

nonce/stage2/status0与独立wire全部通过。频率19200000，原CTL/CVAL均0；counter起点703005354，设计deadline703197354，观察到CTL=7、CVAL匹配、终点703197372，4423次采样，经过192018 ticks（约10.00094ms）。5次写入后CTL/CVAL都恢复0，无trap。只证明屏蔽状态下的物理source到期与两寄存器可写位恢复；没有IRQ、GIC或IAR访问。CNTV没有写入。

Android/root/原boot哈希通过；230328Z正常重启后临时属性消失。70板级+47UniXNU源码、四份QEMU回归、9项构建/接收/审计脚本逐Git blob/快照绑定2fb02f67f8e52751b80181d94247b9edf000f3c9。见timer-source-source-binding.json和boot-timer-source-observation.json。下一步在IRQ仍mask、distributor组和CPU接口均关闭时，仅测试动态本CPU的物理timer PPI单比特使能/清除权限；保持原FDT flag，不改group、priority或触发配置。
