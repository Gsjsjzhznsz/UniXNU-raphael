# 候选 RAM 的只读 MMU 映射诊断

2026-10-28。独立 PcdRaphaelRamMappedProbe，默认关闭；只允许阶段2/3，禁止与候选RAM写入、DXE/管理器或其他硬件诊断混合。未增加 conventional/system-memory HOB，分配器仍限既有16MiB诊断arena。

本机候选来源仍是 KERNEL-MEMORY/RAM-READ 的本次采集与95项排除策略，0xc0000000..0xd0000000不是其他设备参数。现场首先重新检查原FDT、保留区、Image/FDT/SP/LR四个入口保护、MMFR0/PA宽度、EL1、MMU/cache关闭与DAIF全mask，完成原256点稀疏读取。独立ram-mapped wire在stage2只记录保护已通过，不能据此声称已执行映射读取。

stage3仅将同轮候选添加为WRITE_BACK_RO恒等映射。固定Basecore cfb9372 的 ArmLib.h枚举、AArch64Mmu.h的MAIR=0xff与AP=RO、ArmMmuLibCore.c:62-87 为来源。独立C状态机限100ms，逐点AT S1E1R查询实际PA和WB属性、AT S1E1W检查写转换拒绝，随后只读原采样地址；每次查询恢复PAR_EL1，异常退出也执行恢复。AT写权限查询不是store。<=48位/4KiB限制显式检查；不宣称支持52位/LPA2。

读取摘要及非零样本数必须与同轮MMU关闭结果一致；不公开原始候选RAM值。只读映射及抽样通过仍不能证明整窗口测试、完整连续分配合同或隐藏DMA生命周期。

主机74项实际C/UBSan/canary/独立wire检查通过，原RAM门禁73项回归通过。QEMU使用自己的生成FDT与1GiB RAM推导候选，绝不代入手机地址：102433.631100Z-p69tfqtm阶段2正常45项，102433.631134Z-l_zndxbo阶段3正常48项及精确mapped load位置UDF异常返回47项通过。全部包输入相同；AT转换、只读权限拒绝、PAR保存/恢复与摘要相等在真实执行中核对。

首轮101558Z正常映射通过，但异常注入暴露LLD ICF合并两个相同读取函数、实际击中了MMU前位置。失败保留。新mapped读取加入启用转换后的ISB，两个链接位置独立；最终机器码审核核对没有候选store，并确认两个不同load位置。101840Z复测已通过；随后明确volatile恢复状态宽度、冻结解码哈希，最终证据以上述102433Z两份为准。

命令：

```sh
python3 scripts/validate_ram_read.py
python3 scripts/validate_ram_mapped.py
python3 scripts/run_ram_mapped_qemu.py --stage 2
python3 scripts/run_ram_mapped_qemu.py --stage 3
python3 scripts/audit_ram_mapped.py --stage2 <stage2-report> --stage3 <stage3-report>
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --ram-mapped-probe
```

默认关闭配置的完整DXE回归102840Z正常46项、BRK43项、unmapped UDF43项均通过。

主机、镜像结构和模拟器已分别验证；手机待执行，实机成功后另加不可变尝试、原wire/FDT/log、源码绑定和正常重启清理。没有flash/erase/format或修改原备份。


## 手机阶段2/3通过：20261028T103622Z / 20261028T104100Z

两阶段固件输入及15项验证脚本绑定5970805ef423e92000fd8f7714a3d392b1482434，146项板级/通用包输入逐Git blob和构建快照相符。阶段2只证明同轮保护与原256点读取；阶段3在EL1/SCTLR0xc0180d/DAIF全mask时，对0xc0000000..0xd0000000的256点完成WB恒等转换、写权限拒绝及PAR原值0恢复。前后摘要2715173488051968377完全一致，2198ticks/19.2MHz约0.114479ms。没有候选RAM写入或新allocator内存。

阶段2之后103822Z及最终104335Z正常重启清理通过；Android/root/原boot哈希正常、全部临时属性消失。阶段3私有boot SHA256 661d93355aa1e98cdfa89194799c39df897bf3ea78a38ddd68c4ba5fe1c8bdac，FD SHA256 a8aad68abc930f591be2e637cdc1a3f9b3024b5135d5fa14c8e7d9c95723292b。两份独立原wire/FDT/log、不可变handoff/attempt及cleanup复核见boot-ram-mapped-observation.json。抽样、只读权限与缓存摘要事实不推广为整窗口测试或隐藏DMA所有权；手机正向Darwin/XNU仍待实现。原备份未改动，未flash/erase/format。
