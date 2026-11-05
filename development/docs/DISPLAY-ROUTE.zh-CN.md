# 启动显示路由与地址映射核查

日期：2026-10-28（Asia/Shanghai）。目录名使用 UTC；本轮实机 `20261027T161630Z` 是本地 10 月 28 日 00:16:30。

本轮完成 wire version 3 只读采集器、主机解码、结构检查、QEMU 和手机 stage 2 回传。没有输出像素、创建 GOP 或加载闭源模块。version 1/2 原始私有构建、独立尝试记录均保留；version 2 的六份公开记录另存 `*-v2.json`，不以 version 3 的规则重写旧结果。

## 实现与来源

`Sec/DisplayProbe.c` 的 507 项读取由以下组成：4 项电源/时钟门、1 项 MDSS revision、144 项 SSPP、156 项 CTL、144 项 mixer、40 项 interface、18 项 pingpong。上限 640 项，采样返回属性为 8136 字节；新增静态断言保证诊断 context 不超过 bridge 的 64 KiB 设计预算。FDT 副本原有 64 KiB 编辑余量没有改变。

- CTL/mixer/interface/pingpong 的全部窗口、数量、blend offset 均从本机 FDT 解析。固件在首次 MMIO 前检查数量、对齐、边界、全部窗口之间的重叠及 blend 子窗口重叠，拒绝缺失/截断/不一致描述。
- 沿用 version 2 电源/时钟门禁；MDSS revision 的 major 必须为 5，否则记录 `unsupported-mdss-revision`，不读取 SSPP 或路由。上述门禁不是对所有隐藏固件限制的证明。
- CTL_LAYER 的 LM5 特殊偏移由固定一手源码核实，不能按连续六个寄存器计算。读 CTL_TOP/INTF_ACTIVE 和四组 layer，不触发 start/flush/reset。
- 固定 MiCode 的 catalog 对 MDSS major 5 启用 interface TE，legacy pingpong TE 只用于较早 major。因此只读 interface 的 TE/自动刷新，pingpong 只读 DSC/swap 配置，不套用旧 PP 的 tearcheck/refresh 地址。
- `audit_display_sources.py` 对固定 MiCode 提交 `663db50e195a8a54c8565ac4ab0c6d9ba7d80db0` 的 15 个一手文件记录哈希/行号，核对原 18 项 SSPP、19 项新增 scalar 及 CTL_LAYER 宏。该 Android P 源仍是接口参考，不能假定与当前 Android 11 或 ABL 实现完全一致。

## 分层验证

| 层次 | 结果 | 证据 |
|---|---|---|
| 源码实现 | 只读 C 回调；独立主机地址序列和解码；SMMU 仅解析 FDT | DisplayProbe.c、display_probe.py、inspect_boot_route.py |
| 主机执行 | 同一 C 采集器的 44 项模拟 MMIO 检查通过 | artifacts/display-probe-host/20261027T161447Z/report.json |
| 主机结构/模拟器 | 3 MiB FD 结构检查通过，QEMU 17 项通过 | artifacts/sec-dxe-qemu/20261027T161456Z/report.json |
| 手机执行 | nonce 匹配，stage=2/status=0；507 项地址/顺序通过；Android/root/boot 哈希正常 | evidence/private/sec-dxe-run/20261027T161630Z/report.json |
| 解释审核 | 像素格式 8 项、路由/alpha 8 项（含坏配置拒绝）通过 | boot-display-observation.json、boot-display-route-observation.json |
| 清理 | 正常重启后 Android/root/原 boot 哈希正常，入口/SEC/显示标记消失 | evidence/private/entry-probe-cleanup/20261027T161823Z/report.json |

QEMU 没有 SM8150 显示硬件，验证的是不匹配时不采样及恢复返回。通电读取由主机模拟回调和本机回传分别覆盖。主机编译成功没有被当作显示成功；当前包输入仅重新验证 stage 2，不能继承旧 stage 3/6 的源码版本。

私有构建目录：`evidence/private/sec-dxe-build/20261027T161547Z`。全部包输入快照在编译前保存并从快照构建；来源审计和主机报告快照亦保存。

| 产物 | 字节数 | SHA-256 |
|---|---:|---|
| 诊断 FD | 3145728 | `313e354fb5e47fe2b4deb2e503bd9c9379fd22912abfc4b76cc2ac082179f565` |
| 含本机私有输入的临时 boot | 134217728 | `9fcdc45f0339f0f6a1e94a0a58978dd604f437468c365dc11f4b507ec24ce3dd` |

## 本机寄存器事实与受限解释

回传保留全部 507 个地址/值。以下是采样瞬间的寄存器事实；连接和 blend 含义依据固定一手源码解释，不等于实际 DMA 或面板已更新。

| 项目 | 读数 / 解释 |
|---|---|
| CTL0 TOP | `0x20000`，command-mode 位为 1 |
| CTL0 INTF_ACTIVE | `0x2`，选择 interface 1 |
| CTL0 LM0 layer | `0x01000005`；VIG0 stage code=5，border-output 位为 1，其他三组 extension 为 0 |
| LM0 | 1080×2340；VIG0 对应 blend index=3（零起算） |
| LM0 blend 3 op/const | `0x400` / `0x00ff0000` |
| interface 1 mux | 0，按固定接口语义选择 PP0；catalog 对当前非零 LM 列表按序配对 PP |
| interface 1 TE | enable=1，SYNC_CONFIG_VSYNC=`0x180088` |
| interface 1 自动刷新 | `0x80000001`，enable=1、frame_count=1 |
| interface timing engine / frame counter | 均为 0；不能据此单独判断 command-mode 没刷新，也没有观察计数变化 |
| PP0 DSC_MODE | 0 |

CTL0/INTF_ACTIVE、layer、mixer 尺寸和 mux 配置形成一致的候选链：VIG0 → LM0 → PP0 → interface 1（DSI），由 CTL0 控制。主机没有将这条链标为已验证的活动 scanout。

`0x400` 的前景来源是 FG_CONST，背景来源也是 FG_CONST 且取反；FG_CONST=255，所以参考语义得到前景 255/255、背景 0。当前这组 blend 不依赖像素 alpha，不能把“源格式有 alpha”直接解释为“正在按像素 alpha 混合”。未来 GOP 仍需明确处理 Reserved 字节和所有写入路径。

## SMMU：已定位声明，尚未验证实际映射

- 本机 MDP `iommus=<0x26 0x800 0x420>`，phandle 解析为 `/soc/apps-smmu@0x15000000`，compatible 为 `qcom,qsmmu-v500`，`#iommu-cells=2`。
- `base=0x15000000/0x100000`，`tcu-base=0x15182000/0x20` 均从本次 FDT 获取。`arm_smmu_of_xlate` 将第一参数作为 stream ID，第二参数移到 SMR mask 字段；`0x420` 不是 context-bank 编号。
- 按固定源码匹配语义，声明覆盖 ID `0x800/0x820/0xc00/0xc20`。本机子节点将其划入 hf0 `[0x800,0xc00)`、hf1 `[0xc00,0x1000)` 两个 TBU 范围。实际哪些 SID 用于当前 VIG0 还未采样。
- hf0 的 TBU 窗口 `0x1518d000/0x1000`，电源供应节点寄存器 `0x17d050/4`；hf1 为 `0x15191000/0x1000`，供应节点 `0x17d058/4`。这些仅是新解析的声明，未在固件中读取或启用。
- 根节点 `qcom,skip-init`、`qcom,use-3-lvl-tables`、`qcom,disable-atos` 均是 FDT 声明。`skip-init` 不等于 bypass 或关闭 SMMU；不能以 SSPP 地址恰好等于 cont_splash 基址来证明一对一映射。
- 原厂页表根、SMR/S2CR、context-bank、CPU 对该范围的访问，以及 buffer 在交接后的存活期仍未知。本轮没有读取 SMMU/TBU MMIO 或页表，更未改变映射。

## 命令

从权威 WSL 工作根目录执行；本机标识仅存私有日志：

```sh
python3 scripts/audit_display_sources.py
python3 scripts/validate_display_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --display-probe
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --display-probe
python3 scripts/run_sec_dxe.py --serial <local-device-serial> --build evidence/private/sec-dxe-build/20261027T161547Z
python3 scripts/inspect_boot_display.py
python3 scripts/inspect_boot_route.py
python3 scripts/reboot_after_probe.py --serial <local-device-serial>
```

## 下一步

先审核 hf0/hf1 的电源、总线及全局 SMMU 寄存器访问条件，设计有界的只读 stream/context-bank 采集，再核实候选 buffer 的 CPU 物理映射、存活期和实际刷新活动。只有获得这些证据后才设计备份/恢复像素的小范围显示实验。当前 GOP、可见输出、菜单、实体按键、DarwinBoot 和 XNU 均未验证。

没有执行 flash/erase/format、分区修改或备份恢复；原备份保持原位，未删除或覆盖，恢复能力仍未验证。私有原始 FDT、固件和镜像继续留在忽略目录。


本轮固件包与主机解码源码提交：`facee82465a67cad6032f23377f5b9e2e94ef62a`。手机与 QEMU 的全部 24 项包内输入逐项匹配 Git blob，证据快照哈希一致；主机分析脚本另有绑定记录。见 `sec-display-source-binding.json` 和 `sec-display-analysis-binding.json`。
