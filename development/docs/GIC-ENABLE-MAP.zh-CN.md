# GIC Non-secure使能视图的两遍只读采集

2026-10-28（Asia/Shanghai）。这是独立SEC stage2诊断，默认关闭，仅使用本次动态GIC快照的地址。没有接管整个GIC，也没有验证IRQ投递。

## 实现和来源

`GicEnableMap.c`读取GICD_CTLR/TYPER，按TYPER.ITLinesNumber读取ISENABLER bank1..N，跳过bank0；对每个已验证动态redistributor读取RD_CTLR和SGI页ISENABLER0。两遍均累计OR并逐字比较，末尾重读Distributor CTLR。读取数为3+2*(SPI字数+2*帧数)。不提供写回调。

固定Arm IHI0069C，PDF SHA256为026e7dba8d8efca43a3593a6914a2f7cba2ff71cd34583ced97d389d1108dcf6；8.9.24定义SPI范围及TYPER保留位，8.9.15和8.11.15定义使能视图，8.11.2定义Enable_LPIs bit0。MiCode固定提交663db50e195a8a54c8565ac4ab0c6d9ba7d80db0的arm-gic-v3.h独立核对偏移，具体页码、行号和哈希见gic-enable-map-source-audit.json。只接受已审阅标准GICv3范围；不把新版扩展INTID当已支持。

Status3表示两遍一致，Status4表示观察到变化，两者均是有效只读诊断。AllObservedDisabled只有在两遍一致、可见Group使能关闭且ARE开、SPI/local enable及LPI开关全零时为1。DS=0时Secure字段可能RAZ/WI；零值只描述Non-secure可见视图，不证明Secure中断关闭、原子快照或完整所有权。

结果为60个u64/480字节的SEC静态数据；linker map、PE .data、RVA/raw offset、FD实际零字节及范围检查证明其完整物化在既有FD中。没有扩展接近容量上限的context，也不借最后4KiB scratch。

## 主机、编译与结构

实际C+UBSan+前后canary共65项：0/31个SPI字、1/8帧、非零SPI/PPI/LPI、每类第二遍变化、header变化、无效架构/范围/重复帧以及损坏wire。QEMU独立C接收器和Python解码器都通过；最初一次主机解码变量覆盖导致总报告失败，已修正并保留失败日志。

```sh
python3 scripts/validate_gic_enable_map.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --gic-enable-map
python3 scripts/audit_gic_enable_map.py --qemu-report artifacts/sec-dxe-qemu/20261027T234446.571875Z-e40gvh5w/report.json
python3 scripts/audit_icc_probe_sources.py --qemu-report artifacts/sec-dxe-qemu/20261027T234446.571875Z-e40gvh5w/report.json
python3 scripts/build_sec_dxe.py
python3 scripts/build_sec_dxe.py --payload-test --darwin-test --qemu-arch-test
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --gic-probe --icc-probe --gic-enable-map
```

QEMU只读模式43项；默认完整DXE normal/BRK/白名单外UDF为38/35/35项；完整架构/真实模拟IRQ/UniXNU/Darwin拒绝路径57项。各模式板级与UniXNU输入均与手机构建快照一致。模拟器不能代替手机IRQ验证。

手机候选构建：evidence/private/sec-dxe-build/20261027T235021Z。FD SHA256为20577ab8649c11da3ab5dc3be8a5f4a7fe17b78fdf00f9abc0e648c67a6a8400，boot SHA256为4abd1d80c4953ad737c0cb6deb3bf65e54548fd5cc898e32dcc885a054419a44。镜像结构通过；本条写入时尚未实机执行。来源绑定与实机结果分别记录，私有boot/FD不提交。

## 实机使能视图：20261027T235238Z

完整93次读取，29个SPI enable字、8帧local enable与RD_CTLR两遍均零，ChangedWords0、D_CTLR前后0x10，status3/AllObservedDisabled1。同轮nonce/stage2/status0、Android/root/原boot哈希通过；235405Z正常重启清理通过。74板级+47UniXNU输入与Git f5fc35959a2160bb1ce4aa67ca25e116fa540089及私有快照逐项绑定。见gic-enable-map-source-binding.json和boot-gic-enable-map-observation.json。只证明本次非原子Non-secure视图，不证明Secure状态、完整GIC所有权或IRQ投递。未flash/erase/format，未改动原备份。
