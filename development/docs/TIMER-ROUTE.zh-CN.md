# 屏蔽CPU IRQ的物理timer路由实验

2026-10-28，Asia/Shanghai。仅stage2，默认关闭，要求GIC/ICC及同轮两遍enable map。它观察HPPIR和物理timer/PPI pending，不读IAR、不EOI、不执行IRQ handler，不作为TimerArch成功。

## 门禁、写入与恢复

重新解析本机FDT timer→PDC→GIC继承链，并复用经过94项实际C/FDT验证的物理PPI解析器；编号不从其他手机或模拟器复制。本CPUredistributor由MPIDR/affinity和同轮硬件帧确定。要求Non-secure可见SPI/local/LPI使能全零且两遍不变、ARE开、组关闭、ICC_IGRPEN1=0、RPR=255、HPPIR=1023、PMR非零、CNTP关闭。现场再读DAIF、IGRPEN1、HPPIR、CNTP与GIC状态；发现变化不写。

设置物理CVAL=counter+frequency/100；仅write-one使能本CPU目标PPI；GICD_CTLR只增加已审阅ARE模式的Group1 bit1；CPU ICC_IGRPEN1设1；物理timer CTL设1。CPU DAIF始终屏蔽。循环检查timer ISTATUS、HPPIR编号、物理counter和目标pending，遇到其他编号即退出。100ms和1000000次双重上限。

所有失败分支均尝试撤销source（CTL2）、恢复IGRPEN1、恢复Distributor并等待RWP bit31、清除目标enable并等待Redistributor RWP bit3、恢复原CVAL和CTL可写位。随后有界等待目标pending恢复，并核对enable/active、D_CTLR、IGRPEN1、CNTP、DAIF。所有结果字段单独回传。没有改priority、group、trigger、WAKER、pending或active；恢复不靠ACK或清pending。

全零enable是两遍非原子NS观察，Secure状态不可见；它不是完整所有权证明。尚不能处理未知中断，也不把HPPIR可见等同于真正IRQ投递。

## 来源与异常处理

Arm IHI0069C 8.9.4区分NS ARE模式bit1别名；8.2.12定义HPPIR非确认读取；8.2.16定义IGRPEN1；8.11.2定义RWP。PDF固定SHA256沿用026e7dba8d8efca43a3593a6914a2f7cba2ff71cd34583ced97d389d1108dcf6。新MSR同时与独立GNU assembler及MiCode固定663db50e…sysreg.h编码核对。

RouteAccess.S只有一个IGRPEN1 MSR，以及QEMU故障注入UDF。两对精确PC恢复表挂在现有当前EL同步异常白名单后，不扩展为通用恢复；不动栈或callee-saved寄存器。EL2/EL3异常不能保证由EL1恢复。实际EC0 UDF已验证，未声称真实EC0x18 trap。

352字节结果在已有FD的SEC .data中逐字节物化，linker map/RVA/raw offset/PE与FV边界检查通过；不增加context或借用scratch。

## 主机、QEMU与镜像检查

实际C/FDT+UBSan+双canary+独立timer/GIC行为模型101项通过，覆盖WI、未知HPPIR、超时、RWP/撤销迟滞、每步写trap、读trap、恢复失败、坏前提和wire破坏。共享PPI解析器94项回归通过。

QEMU正向49项、写入GIC之后的route-local UDF恢复49项；默认DXE normal/BRK/白名单外UDF39/36/36项；完整模拟IRQ/TimerArch/UniXNU/Darwin拒绝路径58项，所有板级和UniXNU输入与候选手机构建快照一致。首次QEMU因其原PMR=0及PPI/休眠前提未准备而被正确拒绝。现在专用fixture入口从QEMU自己的DTB推导地址，仅为模拟器设置PMR/目标分组/WAKER。这个stub不链接入FD或任何手机镜像；手机不执行该初始化，也不修改这些状态。

```sh
python3 scripts/validate_timer_route.py
python3 scripts/validate_ppi_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --gic-enable-map --timer-route-test
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --gic-enable-map --timer-route-test --timer-route-fault-test
python3 scripts/audit_timer_route.py --qemu-report artifacts/sec-dxe-qemu/20261028T000853.205409Z-s_63b42a/report.json --fault-qemu-report artifacts/sec-dxe-qemu/20261028T000853.205398Z-jxm355ac/report.json
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --gic-probe --icc-probe --gic-enable-map --timer-route-test
```

候选手机构建001327Z：FD SHA256 364e09ee9152f6a4e44bf4c265a1f511b253bb7ac5e7c65b68623678b739d2ab；boot SHA256 79e7424a4a587f19c90e0ba58038cfde2464ecf4cdd37903aaaba96e26bc2716。编译和结构检查通过；写入本节时尚未实机。源码绑定、Android/root/boot哈希和正常重启清理另行记录。

## 实机路由结果：20261028T001611Z

status6/RestoreOk1。源频率19200000Hz，counter从1080544972至1080737007，deadline1080736972；192035ticks约10.00182ms，2562次查询，HPPIR1023→18→1023。pending0x10080000→0x100c0000→0x10080000；enable0→0x40000→0；active前后0。D_CTLR0x10→0x12→0x10；IGRPEN1为0→1→0；CNTP原/恢复CTL/CVAL全0；DAIF前后0x3c0，4次MMIO写、7次系统寄存器写，无trap。

同轮enable map仍两遍全零，nonce/stage2/status0、Android/root/原boot哈希通过；001818Z正常重启清理通过。78板级+47UniXNU输入和12项脚本逐Git blob及构建快照绑定6bda838faefcaa6517eba63d559a85acbe0513d1。见timer-route-source-binding.json和boot-timer-route-observation.json。CPU IRQ仍保持屏蔽，未IAR/EOI，未执行handler或TimerArch；完整GIC/RAM所有权仍未证明。未flash/erase/format，未修改原备份。
