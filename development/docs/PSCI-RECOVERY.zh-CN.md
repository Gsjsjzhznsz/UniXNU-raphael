# 独立镜像自动恢复

2026-10-29，Asia/Shanghai。实现 `da16f56`。本轮验证独立小Image失败返回所需的恢复接口，不是手机XNU实验。没有flash/erase/format，没有改原备份。

## 一手依据和接口查询

固定本机FDT `/psci` 为 `arm,psci-1.0`、`method=smc`。函数ID来自Mu固定源码 `MdePkg/Include/IndustryStandard/ArmStdSmc.h`，并与固定MiCode `drivers/firmware/psci.c` 的FDT conduit选择及reset调用交叉检查。没有借用其他手机硬件地址。

`PsciProbe.c` 复用原入口探针，先完成原Image header恢复和FDT副本，再依据该轮FDT只执行VERSION(0x84000000)和FEATURES(0x8400000a,SYSTEM_RESET 0x84000009)。不调用reset，nonce绑定后继续原Android内核。

手机query：`evidence/private/psci-query/20261028T194116Z`。EL1、SMC、版本0x00010001（PSCI 1.1）、SYSTEM_RESET特性0（支持），reset_called0。Android/root及原boot哈希正常。FDT SHA256 `91d3e532781b1d0edd0e6c3931ecf0b80ca00cdbcc94bbe7fe74f98764496d57`。编译输入、实际反汇编与原始回传私有归档。QEMU对应只验证来自其FDT的HVC，19项通过，不能代替手机SMC证据。

## 独立接收器

新的64KiB ARM64 Linux Image拥有自己的16KiB栈，不含原Android kernel。它要求EL1、MMU/D-cache关闭，按FDT查询版本及reset支持，再依据现场CNTFRQ等待三秒，执行SYSTEM_RESET。手机构建没有HVC或semihost指令；缺少接口或调用意外返回时停机，不猜测PMIC地址。

QEMU `artifacts/psci-reset-qemu/20261028T194433.776529Z-56mju1_q`：先输出READY及SYSTEM_RESET_CALL，3.116秒后 `-no-reboot` 正常退出，没有RETURNED_UNEXPECTEDLY。只证明该模拟器的HVC reset路径。

手机build `evidence/private/psci-reset-build/20261028T194447.618611Z-_9iyomkd`，run `evidence/private/psci-reset-run/20261028T194548Z`：临时fastboot boot接受，36.385秒后Android完成启动，root正常、boot分区哈希不变、新boot_id、全部临时raphael属性清除，无人工按键。

- 独立Image SHA256：`887c04fb1d3982ece6a86799265adb065d5d5aca6f49a51460a7318daacf6156`
- 含本机私有DTB/ramdisk的boot容器 SHA256：`e994438d46152a46b6842249e944cd1901a47e32ce001bb95ef127e348518d34`

这个结果是**自动返回Android的操作证据**。手机没有直接SMC指令跟踪，也没有reset成功后的返回寄存器；不能把自动回Android夸大成对所有reset行为的证明。没有持久化跨reset日志，没有独立UEFI或XNU手机执行结论。

完整原始数据仍在ignored私有目录；公共审核索引 `UniXNU-raphael/evidence/psci-recovery-verification.json`。最初reset汇编因不可编码的TST立即数失败，改为分别检查M/C位；失败目录保留。

## 后续布局预算

以此前本机观测Image base 0x80080000为起点，64KiB接收器+64KiB bridge、24MiB FV、256KiB栈、48MiB arena、0x110000 FDT副本预计落在旧下载extent以内。它们仍是**设计预算**，本轮没有构建/验证这个手机大布局。不能将64KiB恢复接收器成功当作整块arena所有权或有效XNU交接成功。
