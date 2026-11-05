# GIC 入口只读诊断

2026-10-28。人工菜单与三键验证完成后，新增默认关闭的 PcdRaphaelGicProbe。只允许 stage2、入口 MMU/cache 关闭；不提供写回调，不访问 ICC、IAR，不确认中断、不修改 GIC 或 timer，不派发架构驱动。

硬件地址全部从同轮 FDT 读取。仅接受已审计的 SM8150 /soc 恒等映射或 QEMU virt 根总线。唯一 GIC、启用状态、cells、两段 reg、单 redistributor region、显式 stride、对齐/溢出/相互重叠、诊断区及 FDT RAM 别名在首次 MMIO 前检查；缺项立即拒绝。不能把此前观测的帧号写死。

读取 GICD PIDR2/CTLR/TYPER/IIDR，再遍历有界的 GICR 帧。各帧读取 PIDR2、TYPER、CTLR、IIDR、WAKER，按 TYPER 高32位与四级 MPIDR affinity 匹配启动 CPU，检查重复 affinity、Last 与 VLPI 步长。最后只读该 CPU SGI 页的分组、启用、pending、active、group modifier、配置和优先级。原始状态可能随硬件变化，这不是原子快照或状态恢复方案。

偏移、架构类型、VLPI/Last 位、64KiB RD/SGI 页和 affinity 规则来自固定 MiCode 663db50e… 的 include/linux/irqchip/arm-gic-v3.h 与 drivers/irqchip/irq-gic-v3.c。audit_gic_probe_sources.py 独立解析21项常量、记录源文件哈希和行号，并交叉核对本机 interrupt-resource-contract；没有采用其他板级配置。最多8帧为诊断设计上限，非通用GIC最大CPU数。

wire v1：80个大端u64、640字节，包含17项header、8帧×6项及15个SGI读值；完整读取数为4+6×frame_count+15。status1=不支持root无MMIO，2=FDT门禁拒绝无MMIO，3=硬件/拓扑不支持且部分有界读取，4=完整。未知或部分结果不能升级为成功。

诊断context保留<=0xf000静态断言，最后4KiB仍作为guided-section scratch。此新增640字节不会扩大Image/arena或取得额外RAM所有权。

## 源码实现、主机编译与模拟器

- 实际C采集器、UBSan、前后64字节canary和独立Python解码55项通过。包括乱序frame、完整Aff3、坏FDT/别名/重复GIC零读取、错误PIDR/缺Last/重复affinity/窗口尾端、VLPI错误步长及wire损坏。
- GIC启用的自有SEC/QEMU stage2完整31项通过，独立接收器重新读取MPIDR，与原SEC记录交叉核对；GIC wire也由Python独立解析。同一次QEMU生成并压紧的FDT用于固件和解码，25次读取、1帧。这些均为模拟器事实。
- GIC默认关闭的stage6正常34项、BRK返回31项；原CPU/GIC/TimerArch+payload+Darwin测试53项通过。后者是既有QEMU专用IRQ模式，禁止加入手机镜像。
- 私有手机stage2 FD编译和镜像结构检查通过：evidence/private/sec-dxe-build/20261027T220720Z。FD SHA-256 05d79849bc2b76a8314edd305083c03018170e0bc68df61d8241a45e49592a6a；boot SHA-256 e6bdbe7157e71e4c14317159ff50407f57f31fbe41d0e8c91a2df0e2ca89df41。此处尚不宣称实机执行。

```sh
python3 scripts/audit_gic_probe_sources.py
python3 scripts/validate_gic_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --gic-probe
python3 scripts/build_sec_dxe.py
python3 scripts/build_sec_dxe.py --payload-test --qemu-arch-test --darwin-test
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --gic-probe
```

## 实机边界

实机结果单独补记。即使只读采集成功，也不证明 ICC 可访问、非安全物理 timer IRQ 可投递、中断完整接管/恢复或手机 TimerArch 已可用。


## 2026-10-28：只读实机结果

20261027T220921Z：临时fastboot boot被接受，nonce/stage2/status0和独立wire解析通过。67次读取获得8帧，affinity依次为0x0/0x100/0x200/0x300/0x400/0x500/0x600/0x700，与该轮FDT CPU reg完全一致。入口MPIDR=0x81000000，压缩affinity=0，动态匹配frame0/base0x17a60000；该结果属于本次硬件观测，不写成未来固定帧号。

GICD PIDR2=0x3b、CTLR=0x10；各帧PIDR2=0x3b、WAKER=0、CTLR=0，最后一帧TYPER.Last=1。启动帧SGI页group/enabled/active/group_modifier读取均0、pending=0x10080000、config_sgi=0xaaaa、config_ppi=0、八个priority字均0。以上仅记录入口读值，访问视图/安全权限和动态pending不能据此泛化成完整GIC状态或可写权限。

Android启动/root/原boot分区哈希通过；20261027T221111Z正常重启后全部临时属性消失。没有GIC/ICC/IAR写入或读取中断确认寄存器，没有flash/erase/format。源绑定bc38c454eedbf31dda20e496d12c127b3eb8f5e0，61板级+47UniXNU输入逐Git blob及私有构建快照一致，三份QEMU回归同源码；8项构建/接收/分析脚本也绑定同版本。见gic-probe-source-binding.json及boot-gic-readonly-observation.json。

下一步：先核实ICC系统寄存器访问门禁及原入口CPU接口配置，再设计仅涉及本CPU和一个timer PPI、可审核且可恢复的中断接管路径。不能直接把QEMU中初始化整个GIC的通用驱动用于手机。
