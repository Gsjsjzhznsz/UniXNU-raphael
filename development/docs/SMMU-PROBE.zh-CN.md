# 本机启动显示 SMMU 只读诊断

日期：2026-10-28（实验目录用 UTC）。这是 wire v4 的独立实现，不继承其他设备的板级值。

## 来源与访问边界

本次 live FDT 将 MDP 关联到 apps-smmu，SID=0x800、mask=0x420，匹配四个 stream；相关 hf1/hf0 TBU 和 GDSCR 地址由 phandle 链重新解析。mask 不是 context-bank。固定 MiCode `663db50e195a8a54c8565ac4ab0c6d9ba7d80db0` 的 arm-smmu-regs.h、arm-smmu.c、gdsc-regulator.c 和 sm8150-gdsc.dtsi 是接口一手参考，不代表当前 Android 11 ABL 的精确实现。逐文件 SHA、行号和 36 个常量见 smmu-source-audit.json。

采集前先完成 FDT/范围/依赖校验，读取两个 TBU GDSCR 后才读全局 ID/CR0、全部 SMR、匹配的 S2CR 和唯一 context-bank 配置。拒绝 secure alias、static-CB、扩展 SID、未知 clocks/regulators、重复/遗漏的 stream、越界 bank 和未知寄存器几何。最多1024项；不写 MMIO，不调用 ATOS，不读页表或像素。

**设计假设**：原厂交接保留了 APPS SMMU 全局寄存器访问所需的总线路径。GDSCR bit31 不足以证明这个条件；总线挂死也不保证能由异常回传恢复。物理映射、页表所有权、实际 fetch、面板更新仍未知。生产 GOP 继续禁用。

## 实现与主机验证

新增 Sec/SmmuProbe.c；默认关闭 PcdRaphaelSmmuProbe，仅 stage2 显式启用。上下文扩容至37280字节；guided-section scratch 由 context+0x8000移到+0xf000，末页保留4KiB，统一静态断言限制上下文小于该偏移。stage3/6必须重测，不继承历史成功。

- 实际 C 采集器 + 模拟 MMIO：50项通过，artifacts/smmu-probe-host/20261027T164942Z/report.json。
- 显示采集器回归44项通过，artifacts/display-probe-host/20261027T164821Z/report.json。
- QEMU stage2：17项及FD结构检查通过，artifacts/sec-dxe-qemu/20261027T165026Z/report.json。QEMU不模拟本机SMMU，只证明无匹配设备时零额外MMIO并正常返回。
- 保留失败：20261027T164945Z构建因Sec.c旧32768字节断言失败；修正重复的旧断言后重建。
- 早期主机审计曾因错误的源码锚点 vdd 失败，改为准确的电源资源初始化函数；一轮恶意FDT解码在旧显示recipe拒绝非法iommu-cells，C安全停止测试仍保留，非法FDT用例与正常wire解码分别验证。

命令：
```sh
python3 scripts/audit_smmu_sources.py
python3 scripts/validate_display_probe.py
python3 scripts/validate_smmu_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --display-probe --smmu-probe
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --display-probe --smmu-probe
```

## 实机验证

本段在实机执行后追加；当前实现/主机/QEMU结果不代表手机访问成功。


实机 `20261027T165210Z` 成功：nonce匹配、stage2/status0、621项读取顺序完整；Android/root正常，原boot SHA不变。私有构建 `20261027T165139Z`，FD SHA `ce05b6faf880d32d39ec8115ff1b5b6d4868f12eed20036d23ad17a48d961e58`，boot镜像 SHA `8347b5548b38b31a6e4e42ed55c68bb1ff9a79145023bd3a4fa79c6012afeb3f`。全部包内输入与固件提交 `9d2fb86365b30f68375fa5d837ba47209bea8444` 逐项匹配，见sec-smmu-source-binding.json。未重新验证stage3/6。

ID0=0x4c017e5e、ID1=0x60000038、ID2=0x5555（原始值以boot-smmu-observation.json为准）；94个stream groups、56个context banks，4KiB寄存器页。SMR3覆盖四个目标stream，S2CR3=2，唯一CB2。CBAR type1（S1 translation/S2 bypass）、CBA2R=1、SCTLR=0xe0（M=0）、TTBR0/1=0。配置与早期stage1 bypass一致；MiCode arm-smmu.c的DOMAIN_ATTR_S1_BYPASS/EARLY_MAP分支正是通过不置SCTLR.M实现该行为。尚未直接采集CPU像素或证明正在DMA。

正常重启清理成功：Android/root/boot哈希通过、临时标记消失，见sec-smmu-cleanup.json。下一步先只读验证cont_splash内候选CPU内存及interface刷新计数，再做可恢复的小范围像素实验。无分区刷写、恢复或原备份改动。
