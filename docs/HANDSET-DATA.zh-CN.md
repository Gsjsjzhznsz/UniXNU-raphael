# 独立手机易失 Data 候选

2026-11-02手机190907Z整轮通过，已解除原launchd/tzinit的只读`/private/var`阻塞。原launchd完成early boot，SpringBoard PID26被观察到；尚无桌面或交互证明。

## 输入与边界

- 使用固定 iPadOS 17.7.11/21H461 的原 var 文件与元数据，以及已明确记录的空目录 skeleton。
- 新建的 APFS scratch 逻辑容量 1GiB，DBRDISK1 无损 packed 为 73840 字节；原 RamBlock 按需分配，逻辑容量不等于物理驻留。
- 原 OS/SystemOS 的不可变 UFS extent、逐4KiB认证及只读 transport 保持原合同。
- `native_ufs_store_mode()` 明确返回0；Data仅在RAM中，重启丢失。不是持久Data或加密保护验收。
- 只在显式 `--handset-ufs --handset-data --scratch-data <private report>` 选择，不影响默认 compile-only 配置。

## 实现

`configs/raphael_handset_data_defconfig` 选择原 RamBlock、原 APFS Data 挂载与本设备的 var seed。固定 DarwinBoot 通过原 `Entry.Initrd` / `PackedRAMDisk` 接口装载；不改其源码。

工作区 `scripts/native_data_adt.py` 保存私有 packed 与ADT placeholder；`prepare_handset_payload.py --packed-data-report` 将精确输入放入128MiB只读载荷。NativeLoad v3在原TrustCache描述之后追加Data描述。固件在进入XNU前检查完整CRC、实际装载地址、两处不重叠ADT fixup、分配范围、原TrustCache和最终ADT CRC，任何不符则停止。恢复阶段也按同一顺序独立重建预期ADT。

真实内核内存512MiB由独立185720Z实测确认，不能将更大逻辑Data当作额外RAM。恢复备份仍是同八个mutable区域，当前8757248字节，显式上限12MiB；区域CRC、完整恢复、页表与nonce验收未放宽。

## 当前检查

- Data内核190057Z：完整887编译记录；预链接125177856字节；128MiB载荷生成通过。
- 11项packed格式、精确装载布局、破坏格式及缺placeholder拒绝检查通过。
- 仓库布局/13区记录检查与Python语法通过。
- v20因原8MiB备份上限在主机阶段拒绝，未上手机；v21复用同一冻结内核/载荷/extent验证12MiB容量。
- 手机190907Z：Data stage4/status0/readonly0；226项seed与611715字节写入/读回一致；130次RamBlock写、零失败、1437696字节驻留。真实512MiB、240秒观察及全部恢复/Android清理通过。详见`evidence/native-ephemeral-data.json`。
- 原控制台已证明early boot完成及SpringBoard26进程出现；服务整体就绪和可见桌面仍需后续验收。

## 实机验收

要求同轮原 `native_owner_data_stage=4`、status=0、readonly=0，seed状态0且写入/读回字节一致、RamBlock写入大于0且失败0，原launchd main、完整checkpoint与恢复清理。后续仅根据原日志的新阻塞继续；不关闭原launchd的critical-child行为，不将QEMU或更多syscall称为桌面。
