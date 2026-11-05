# 入口稀疏 RAM 只读实验

2026-10-28。实现默认关闭、仅SEC阶段2。258e353同源码手机只读实测与正常重启清理已通过。只读候选RAM，没有扩大分配器、写候选页或启动OS。

## 来源和访问预算

由已提交kernel-window-audit.json中最低的256MiB对齐候选计算得到0xc0000000..0xd0000000，右端不含。95项保护范围逐项来自此前本轮FDT、memblock、iomem、本机XBL声明、原initrd与诊断布局，完整原始来源/哈希见KERNEL-MEMORY.zh-CN.md和kernel-window-audit.json。没有手写另一手机的参数。

不可变RAW FV策略GUID d2cd8ed5-a64e-45d3-8b4e-3d02d1f1b0fb；固定64字节头+95×16字节guard，每项u64为little-endian，精确长度1584字节。每2MiB块首尾各读取8字节，共256个地址、2048字节；100ms时间上限。256MiB和2MiB来自原DarwinBoot要求，256次采样和100ms为本项目诊断设计，不能代表完整RAM测试。

入口独立读取ID_AA64MMFR0_EL1，并与固定Mu的ArmGetPhysicalAddressBits结果核对。32/36/40/42/44/48/52映射以mu_basecore cfb93724a06ff86ff5ba971413368a7809ee42a5的MdePkg/Library/ArmLib/AArch64/ArmLibSupport.S为一手源；保留值拒绝。读取时要求EL1、M/C/I关闭、DAIF全mask。现场重新解析FDT兼容性、RAM包含关系、固定和header reserved区、原initrd，并额外保护整个原Image/诊断区、实时FDT、原SP/LR页。动态池只计数，不推定地址或所有权。

ReadRam64只有一次通过候选指针的volatile const UINT64 load。最终链接机器码审计确认地址参数进入x20，候选只有ldr x8,[x20]；存储仅至独立输出指针x19和自身栈，前后dsb sy/dmb sy。结果为208字节SEC物化零数据mRamRead，经实际FD逐字节核验；没有扩大接近满的入口context。回传只含计数、摘要、时间和资源元数据，没有原始RAM word。

## 主机、镜像与模拟器

73项实际C/libfdt/UBSan/canary/独立wire检查通过；覆盖精确256地址、策略和CPU状态、PA、guard/FDT/header/initrd、callback失败、计时超限/倒退/回绕和损坏wire。

QEMU为独立生成的1GiB RAM，候选从模拟器RAM bank中点计算，不能作为手机参数。正常41项、在实际读取指令处注入UDF后的fatal返回41项通过；接收器独立重读并计算摘要，检查入口状态和Image恢复。UDF在第一次读取前触发，保留status2/attempted1/completed0/active_address；它是受控未定义指令异常，不是真实data abort。保留原fatal handler，不增加泛化异常恢复。

- RAM QEMU：artifacts/sec-dxe-qemu/20261028T030046.492563Z-n4k9zp0m/report.json
- host：artifacts/ram-read-host/20261028T030148.642785Z-bdbwxntc/report.json
- 默认stage6/BRK/UDF回归：artifacts/sec-dxe-qemu/20261028T030150.110950Z-di3pm5ys/report.json，43/40/40项通过。
- 真实物理TimerArch+完整UniXNURun回归：artifacts/sec-dxe-qemu/20261028T030150.117201Z-_1aoia60/report.json，73项通过。
- 私有手机候选：evidence/private/sec-dxe-build/20261028T030317Z，编译/结构通过；030742Z同镜像实机通过。
- FD SHA256：96a24f638fef462c8fe97218f10bee92576b6fd6e49d2f10b73b95eaa3ed8507
- boot镜像SHA256：93367780e0d3db8495fd1b469cfe07998223e1136636984485fdce44a5de3db0

早期025115Z构建后，新增策略FFS组合未在inspector允许列表而被拒；收紧加入只含策略的最小集合后025330Z正常QEMU通过。后续异常用例在主机inspector处因bytearray类型被拒，改传bytes后030046Z正常和UDF均通过；实际目录名以artifacts内保存为准。两次均未启动手机。

```sh
python3 scripts/validate_ram_read.py
python3 scripts/run_ram_read_qemu.py
python3 scripts/audit_ram_read.py --qemu-report artifacts/sec-dxe-qemu/20261028T030046.492563Z-n4k9zp0m/report.json
python3 scripts/build_sec_dxe.py
python3 scripts/build_sec_dxe.py --physical-timer-arch --payload-test
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --ram-read-probe
python3 scripts/record_ram_read_observation.py bind --build evidence/private/sec-dxe-build/20261028T030317Z
python3 scripts/run_sec_dxe.py --serial <serial> --build evidence/private/sec-dxe-build/20261028T030317Z --historical-binding UniXNU-raphael/evidence/ram-read-source-binding.json
python3 scripts/reboot_after_probe.py --serial <serial>
python3 scripts/record_ram_read_observation.py record --cleanup <本轮cleanup目录>
```

## 验证边界与下一步

源码、主机、结构检查和模拟器分别记录；本轮只确认256个采样地址可读，不能证明整个窗口可读写、空闲或全部固件/DMA生命周期已结束。保持UEFI新增内存为关闭，先记录手机结果和恢复，再设计能恢复原字节的有界写实验。DarwinBoot和真正XNU仍未在手机执行。


## 手机结果：20261028T030742Z

实现提交258e3531fda14175e636133a33850ae9222a79ab；87项板级+47项UniXNU输入逐Git blob与构建快照绑定。nonce/stage2/status0、独立208字节wire及Android/root/原boot哈希全部通过。窗口0xc0000000..0xd0000000共256次读取，attempted=completed=256，最后地址0xcffffff8，无exception。counter655802176→655831030，19200000Hz，即28854ticks/1.5028125ms。MMFR0=0x101122，固定库独立返回40位，与PARange=2一致。

同轮FDT有3段RAM、19个固定reserved、0个header reserved、8个动态池；95项策略guard和4项实时guard均完整检查。241个样本非零，仅记摘要，没有公开原始RAM值。这不说明当前分配状态，也不能当空闲容量。

030956Z正常重启完成，Android/root正常，boot分区哈希保持不变，所有临时raphael属性清除。记录器独立复核不可变attempt和handoff共同字段、FDT/日志/wire、源码绑定及cleanup，见boot-ram-read-observation.json、ram-read-source-binding.json和sec-ram-read-stage2-handoff.json。全程临时fastboot boot，没有flash/erase/format或原备份修改。下一步仍需可恢复写与入口所有权假设；不能将稀疏读取推广为整个256MiB可分配。
