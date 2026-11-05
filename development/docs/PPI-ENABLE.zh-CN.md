# 本CPU物理timer PPI使能权限实验

2026-10-28。默认关闭且只允许stage2，依赖同轮完整GIC/ICC；与timer source和QEMU故障注入互斥。目的仅为验证单个PPI的Non-secure使能权限与恢复，不启用IRQ。

PpiProbe.c重新解析唯一timer及其interrupt-parent继承链。手机只接受SM8150 PDC→同一GICv3，QEMU只接受直接GICv3；phandle唯一性/别名、provider状态、controller/cells、四个唯一PPI、频率、flags及unsupported extended描述均检查。物理timer按绑定中的第二个specifier选择，原flag完整保留。手机编号18/flag0xf08来自本次FDT与固定一手DTS，不套用QEMU的30/4。

按本轮GICR_TYPER/MPIDR选定的启动CPU帧推导SGI_base=RD_base+64KiB。要求CNTP关闭、DAIF全mask、ICC_IGRPEN1=0、Distributor组使能位关闭、ARE已启用、原PPI disabled/not active/not pending、原RWP=0。重新读取现场状态，任何变化都不写。然后仅向本CPU的ISENABLER0写一个bit，读取权限结果，再向ICENABLER0写同一个bit；不使用读改写，不修改GICD、group、priority、trigger、pending、active或WAKER。

清除后有界等待GICR_CTLR.RWP，核对全部enable字与原值一致、GICD_CTLR未变及目标pending/active未变。status3表示写被忽略且清理已核对，不能宣称有写权限；status6表示可写并恢复。其他结果拒绝成功。

## 一手来源与存储

ISENABLER0/ICENABLER0/PENDING/ACTIVE偏移来自MiCode固定663db50e…的arm-gic-v3.h并解析宏别名核对。Arm IHI0069C的8.10规定连续RD/SGI两个64KiB页，8.11.2规定GICR RWP为bit3，8.11.4/8.11.15规定Non-secure RAZ/WI及write-one语义，8.9.4区分NS GICD_CTLR ARE/组使能别名。

厂商旧wait helper对redistributor复用Distributor的bit31，不能据此取代架构定义。新代码采用规范bit3，来源、页码、旧实现哈希和差异见ppi-probe-source-audit.json。

context已接近0xf000界限，本功能不扩大context或scratch。160字节结果由链接器放在SEC自身的.data中，主机逐镜像核对map符号、XIP RVA=raw offset、完整materialized零字节、SEC PE/FV范围；不借用任何额外物理地址或扩大FD/arena。手机该检查结果保存在私有构建report的ppi_result_storage中。

## 主机、模拟器与镜像

- 实际C/FDT/UBSan/64字节双canary/独立wire94项通过。包括frame5动态选择、WI、清除失败、RWP迟滞/超时/计数器停止、目标pending变化、坏provider/cycle/重复handle/alias和wire损坏。初次Python未把底层FDT Error归一化为ValueError，已修正并重跑；87项之后再增7项继承链检查。
- QEMU PPI正常43项，实际ISENABLER/ICENABLER写入及独立接收器MMIO回读通过；该轮是QEMU PPI30/flags4，不能代替手机18/0xf08。
- 同源码默认stage6正常37/BRK34/白名单外UDF34；完整IRQ+payload+Darwin56；既有masked CNTP source45项通过。目录和哈希在源绑定独立记录。
- audit首次文本锚匹配到目录标题，准确正文锚修正后通过。首次手机构建门禁因audit指向旧QEMU报告而拒绝；该失败保留，尚未执行手机操作。
- 私有手机镜像232317Z已编译并完成FD/FFS/PE/boot及结果存储结构检查。FD SHA-256 9a05bdce56a24cdcbca5e640e2514ec3e39c113e86c798055a1ec9071d63c007；boot SHA-256 306b91372c886fe4cf1346ea97a0e123aa28206bd8e6aed9b761f19fae376550。尚未执行实机，不把主机或QEMU结果当手机成功。

```sh
python3 scripts/validate_ppi_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe --icc-probe --ppi-enable-probe
python3 scripts/audit_ppi_probe.py --qemu-report artifacts/sec-dxe-qemu/20261027T232133.632597Z-9a75fiup/report.json
python3 scripts/audit_icc_probe_sources.py --qemu-report artifacts/sec-dxe-qemu/20261027T232133.632597Z-9a75fiup/report.json
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --gic-probe --icc-probe --ppi-enable-probe
```

IRQ投递、分发器接管、优先级屏蔽、架构timer服务及真正UniXNURun/DarwinBoot/XNU仍待实现和实机验证。


## 实机结果：20261027T232552Z

nonce/stage2/status0及独立wire通过。按本机FDT得到INTID18、flag0xf08；按同轮affinity动态选中SGI_base0x17a70000。enabled原0→0x40000→0，共2次write-one写入、11次读取；RWP查询1次。GICD_CTLR保持0x10；pending前后均0x10080000、active前后0，目标bit原无pending/active且未变化。status6、RestoreOk1，证明本次Non-secure视图的PPI18使能可写并恢复。没有启用分发器、CPU接口或IRQ，没有IAR确认。

Android/root/原boot哈希通过，232753Z正常重启清理通过。72板级+47UniXNU输入、四份QEMU回归和9项脚本逐Git blob/快照绑定5b02d17984dd287e9c1745a477e8ab4a1d89a6de。见ppi-probe-source-binding.json和boot-ppi-enable-observation.json。没有flash/erase/format或备份修改。

下一步先读取所有Non-secure SPI/各CPU SGI-PPI的enable以及LPI门禁。仅本CPU目标PPI可写不足以授权把分发器组全局打开；必须先确认不会使其他已使能中断获得投递机会，再设计有界、可恢复的物理timer路由实验。
