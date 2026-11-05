# ICC 与定时器入口只读采集

2026-10-28。菜单与实体三键已经人工和日志交叉验证。本阶段只核实入口CPU接口和timer状态，默认关闭、仅stage2，依赖同轮GIC只读采集完整，不启用中断。

源码为独立IccProbe.c、IccReadAdapter.c、IccReadSites.inc和IccRead.S；16项读取依次为CurrentEL、DAIF、MPIDR_EL1、ICC_SRE_EL1、ICC_CTLR_EL1、ICC_PMR_EL1、ICC_BPR1_EL1、ICC_IGRPEN1_EL1、ICC_RPR_EL1、ICC_HPPIR1_EL1、CNTP_CTL_EL0、CNTP_CVAL_EL0、CNTV_CTL_EL0、CNTV_CVAL_EL0、CNTKCTL_EL1、CNTFRQ_EL0。没有IAR/EOIR/DIR访问，没有ICC/timer写入。HPPIR是最高pending优先级信息读取，不确认中断；pending值不是原子快照。

门禁：完整GIC、动态MPIDR匹配、CurrentEL编码4、DAIF四类全mask、SRE.bit0已经启用。失败立刻停止，不尝试开启SRE或继续访问后续寄存器。wire为26个大端u64/208字节：7项header、16项读值、3项QEMU故障注入字段。status1前提拒绝、2 EL/DAIF/MPIDR拒绝、3 SRE关闭、4读取异常、5全部完成；主机只把status5与16项完整视为成功。

只为当前EL同步异常槽0/4加入精确PC白名单恢复。每个reader有单一MRS及失败返回点，局部handler只用ABI caller-saved x8-x17、不用栈、不动x18和callee-saved；EC0或0x18且PC精确匹配才把ESR/ELR写回调用参数并返回FALSE。其他异常继续原有fatal诊断返回。整个SEC仍有既有DAIF/VBAR等控制写，恢复handler会写ELR_EL1，不能把本阶段描述成整个固件没有系统寄存器写入。EL2/EL3 trap不保证在EL1恢复。

架构来源为Arm ARM IHI0069C (ID070116)，788页，SHA-256 026e7dba8d8efca43a3593a6914a2f7cba2ff71cd34583ced97d389d1108dcf6。下载地址及HPPIR/IAR/SRE章节页码记录于icc-probe-source-audit.json；最初下载名暗示F但实际封面是C，现按实际文档记录。MiCode固定663db50e…的arch/arm64/include/asm/sysreg.h交叉核对其中12条编码；全部16条真实COFF MRS指令另与独立GNU assembler逐字匹配。编译后reader无MSR、SYS、DC、IC或callee-saved使用，恢复表为17对/272字节（16读取+1仅QEMU注入）。

## 主机与模拟器

实际C/UBSan、前后64字节canary与独立Python wire解码59项通过，包括每个读取点失败停止和partial不能解码成成功。
- 20261027T223036.931293Z-t92f6eci：normal 37项通过。
- 20261027T223036.931301Z-ux02ybq3：normal 37项通过。
- 20261027T223036.931295Z-6kz_mr0j：normal 35项、injected_brk 32项、unmapped_udf 32项通过。
- 20261027T224028.104046Z-b183gx0t：normal 54项通过。

受控UDF只证明EC0的局部异常恢复；没有宣称真实EC0x18 trap已测试。白名单外UDF与BRK都走原fatal返回，防止新handler误吞无关异常。手机构建永远关闭故障注入和QEMU全GIC初始化模式。

构建失败均保留：222336.882068Z-h0uvyk72中C与S同basename导致object覆盖，C改名IccReadAdapter.c；222458.593697Z-opovhzp4中BaseTools Trim裁掉汇编include内容，改为显式汇编函数与表。修复后重新构建和回归。

## 手机镜像结构检查

私有构建evidence/private/sec-dxe-build/20261027T223612Z，FD大小3145728、boot大小134217728；未修改原kernel/ramdisk，结构检查通过。

- FD SHA-256：784d504b9151c03f08f5eb141bacf0bf8bc48bcb6d6e5d9f85494657466c46f4
- boot SHA-256：b676a4b63c70364c13e044d5fed2eb034b01a15f5f148899e25215cbc942ed82

以上仅主机编译/镜像结果，实机结果随后单独记录。context仍有<=0xf000静态断言，最后4KiB保留scratch；新增208字节没有扩张Image/arena或取得更多RAM所有权。

```sh
python3 scripts/validate_icc_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --icc-fault-test
python3 scripts/build_sec_dxe.py
python3 scripts/build_sec_dxe.py --payload-test --qemu-arch-test --darwin-test
python3 scripts/audit_icc_probe_sources.py --qemu-report artifacts/sec-dxe-qemu/20261027T223036.931293Z-t92f6eci/report.json
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --gic-probe --icc-probe
```

下一步先实机只读核实ICC/timer访问和状态；仅凭读取成功不能证明写权限、IRQ投递、状态恢复或TimerArch可用。后续需设计仅本CPU和一个timer PPI的可恢复实验，保留本机FDT的INTID17/18/19/16与flag0xf08，不复制QEMU板型配置。真正UniXNURun、DarwinBoot和XNU的手机启动仍待完成。


## 实机结果：20261027T224342Z

同轮GIC完整67次读取及ICC全部16项完成，nonce/stage2/status0与独立解码通过；无读取trap。CurrentEL=4、DAIF=0x3c0、MPIDR=0x81000000；SRE=1、CTLR=0x8440、PMR=0xf0、BPR1=3、IGRPEN1=0、RPR=0xff、HPPIR1=1023。CNTP_CTL=0、CNTP_CVAL=0；CNTV_CTL=5、CNTV_CVAL=233262653；CNTKCTL=0、CNTFRQ=19200000。CNTV_CTL的ISTATUS/ENABLE均为1，不能认为所有timer已停用，后续不得无依据改动虚拟timer。

Android/root/原boot哈希通过，224519Z正常重启临时属性清理通过。66板级+47UniXNU源码、四份QEMU回归及8项验证脚本逐Git blob/快照绑定bd3dcdf5c54381bfe819e2079afcca112bb839c7。见icc-probe-source-binding.json、boot-icc-readonly-observation.json。

Arm规范8.11.8/8.11.9指出DS=0时Non-secure读取IGROUPR/IGRPMODR为RAZ/WI。因此此前group读取0不能证明PPI为Secure组，也不能据此跳过权限验证。手机真正IRQ、GIC写权限、定时器接管/恢复仍未验证；下一步先在DAIF全mask下只验证已关闭的CNTP可恢复寄存器和到期状态，不开启IRQ、不触碰仍有状态的CNTV。
