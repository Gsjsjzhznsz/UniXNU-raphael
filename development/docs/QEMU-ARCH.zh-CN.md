# 自有 QEMU 固件的架构协议诊断

本功能默认关闭，只允许模拟器构建。独立 SEC/DXE 使用固定 Mu 的 CPU、GICv3、CNTP TimerDxe 与真实 DXE 事件服务；没有借用 AAVMF 的架构协议。手机的 GIC 状态接管和恢复仍未验证，不允许在本机镜像启用。

## 实现与参数来源

`build_sec_dxe.py --payload-test --qemu-arch-test` 每次先让所运行的 QEMU `virt,gic-version=3,virtualization=off` 产生自己的 DTB，再由 dtc 去掉填充。原始和压紧后的 DTB、命令、哈希、QEMU 版本均保存。压紧前后资源必须相同，实际启动显式使用同一份压紧 DTB。

主机与 SEC 分别检查唯一 GICv3、直接根节点、2/2 cells、interrupt-controller、三 cell IRQ、根 phandle 继承、单 GICR 区域、恒等 ranges、两个范围和四个唯一 level-high PPI。SEC 再核对构建时显式 PCD 与现场 FDT 一致，拒绝窗口溢出、未对齐和与诊断 extent 重叠。地址、IRQ 值不取自手机或其他板型。

仅本次 QEMU 生成资源为 GICD `0x08000000/0x10000`，GICR `0x080a0000/0xf60000`，四路 INTID 29/30/27/26。这里的模拟器值绝不代入 SM8150。CPU/GIC/Timer 驱动、计数器实现与 DXE event 关键接口逐文件匹配固定 Basecore `cfb93724a06ff86ff5ba971413368a7809ee42a5`，审计见 `qemu-arch-source-audit.json`。

`PcdTimerPeriod=100000` 为诊断选择的 10ms 周期。合成只读 FAT 的 UniXNU 配置倒计时为2秒，普通 payload 模式仍为0。为容纳通用 CPU 驱动的日志，原 context 中 map/log 的预算从12/8KiB调整为4/16KiB，总体积60432字节不变，仍小于最后4KiB scratch 前的0xf000边界。GetMemoryMap 超过4KiB会明确失败，不截断地图。

当前诊断固件没有生产内存保护合同，QEMU 条件下关闭 `PcdRemapUnusedMemoryNx`；不能声称该 RWX 诊断映射满足生产安全要求。

## 验证范围

stage2只解析资源，stage3增加DEVICE映射/HOB；stage6执行实际通用CPU/GIC/Timer架构驱动。完整管理器真实等待约2秒后退出；另验证100ms相对timer事件的WaitForEvent、20ms周期回调至少5次、取消后100ms计数不变。物理计数器独立约束耗时，不以SetTimer返回成功代替中断执行。

结束前TimerArch设为0、禁用四路timer中断并查询状态、屏蔽CPU IRQ；SEC恢复CNTP CVAL与CTL可写位并记录回读，再经原恢复路径交回接收器。**GICD/GICR整体状态没有恢复**，因此此模式不可用于手机，也不是可返回Android的硬件中断接管方案。通用CpuDxe接管异常向量后，旧SEC的BRK注入测试不再适用，本模式明确跳过；关闭本模式的正常/BRK回归仍保留。

29项u64大端wire由独立接收器核对，再由Python解析并与本轮DTB比较。早期阶段不允许出现后期执行字段。完整检查还要求日志丢弃数为0。固件结构检查严格要求三个架构FFS同时存在，并验证 Runtime→CPU→GIC→Timer→GOP→Input→payload 的apriori顺序。

## 失败记录

- `20261027T205604.770813Z`：DSC错误使用INF的FeaturePcd节名；修正为PcdsFeatureFlag。
- `20261027T205618.359365Z`：FdtLib包装头不提供fdt32_t；改用UINT32。
- `20261027T205731.306307Z`：直接传入填充DTB，QEMU扩展后超过输入预算，未产生诊断wire。改为显式压紧同一DTB。
- `20261027T205918.733912Z`一次构建：接收器已返回成功，但Python同名decode导入遮蔽架构解析器；修正显式别名。失败目录保留，未生成成功报告。
- `20261027T210209.074571Z`：C接收器51项通过、真实IRQ/管理器成功，但8KiB日志截断、Darwin全文校验失败，整轮记失败。扩大日志且增加零丢弃断言后重跑。
- `20261027T210537.838254Z`：修正后首次完整52项通过；源码固定后的最终重跑、哈希与绑定另行归档。

- 固定源码后首次并发重跑有两进程读到相同微秒时间戳，mkdir明确拒绝重用输出目录；未覆盖产物。输出目录改为时间戳加原子mkdtemp后缀，重新固定构建器再重跑。

## 层次与后续

源码实现、主机编译、FD/PE/FFS检查、QEMU执行分别记录。手机没有执行本功能；人工菜单/实体按键观察仍延期。本功能没有有效Mach-O交接、ExitBootServices或XNU执行。下一步需完善本机GIC只读状态/可恢复接管合同，并独立测试有效负载的内核入口交接；不能照搬此QEMU资源或中断配置。

## 固定源码最终结果

全部59项板级、47项UniXNU、启用时9项DarwinBoot输入逐个匹配Git blob，并将构建器、接收器、结构检查器和独立解码器绑定源码 `86f1b61058c0117d74e7f5170f3f0cb08784933e`。

| 运行 | 检查数 | 私有产物目录（artifacts/sec-dxe-qemu/） |
|---|---:|---|
| stage2 + Darwin + 架构 |29|20261027T210948.322271Z-q_gzprmb|
| stage3 + Darwin + 架构 |31|20261027T210948.322270Z-qqhszhy1|
| stage6 + Darwin + 架构 |52|20261027T210948.322873Z-9pmvcqhi|
| stage6 + payload + 架构 |46|20261027T211003.805847Z-roccj35f|
| 架构关闭 + Darwin |正常45 / BRK32|20261027T211003.880901Z-3nom4gdb|
| 全部默认关闭 |正常33 / BRK30|20261027T211008.219987Z-kd1qnfmj|

上述均通过，完整命令、固件与Image哈希、DTB来源和各层结果见 `qemu-arch-sec-source-binding.json`。独立wire与资源损坏输入53项通过，见 `qemu-arch-wire-host.json`。新架构模式未运行旧BRK注入；表格只将关闭该模式的BRK记为通过。
