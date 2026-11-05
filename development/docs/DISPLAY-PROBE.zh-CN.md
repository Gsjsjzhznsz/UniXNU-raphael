# 启动显示的只读诊断

本文件保留 version 1/2 的历史过程；2026-10-28 的 version 3 路由核查见 [DISPLAY-ROUTE.zh-CN.md](DISPLAY-ROUTE.zh-CN.md)。最新公开索引指向 version 3，version 2 的六份元数据以 `*-v2.json` 保留。

实验日期：2026-10-27；源码与证据归档：2026-10-28（Asia/Shanghai）。目标是确定 ABL 交接后留下的显示状态；本轮代码不提供 GOP、不写 framebuffer、不设置模式，也不加载原厂 DisplayDxe。

## 参数来源与依赖

`scripts/audit_display_sources.py` 对固定 MiCode 提交 `663db50e195a8a54c8565ac4ab0c6d9ba7d80db0` 的 9 个一手源码文件记录哈希和行号，并逐项核对 18 个 SSPP 配置寄存器偏移、3 个时钟门偏移。来源索引见 `../UniXNU-raphael/evidence/display-source-audit.json`。源码来自 Android P 公开分支，仅用于核实接口，不能当作当前 Android 11 内核或原厂 ABL 的准确源码匹配。

MMIO 基址均在执行时从本次本机 live FDT 获取，主机在启动前重新比较相关资源。不是从其他手机移植复制的常量：

| 资源 | FDT 声明 | 来源 |
|---|---|---|
| MDSS MDP | 0x0ae00000 / 0x84208 | `/soc/qcom,mdss_mdp@ae00000:reg[0]` |
| GCC | 0x00100000 / 0x1f0000 | `/soc/qcom,gcc:reg[0]` |
| DISPCC | 0x0af00000 / 0x20000 | `/soc/qcom,dispcc:reg[0]` |
| MDSS GDSCR | 0x0af03000 / 4 | MDP 的 `sde-vdd-supply` phandle 解析为 `mdss_core_gdsc` |
| SSPP 块 | 0x5000、0x7000、0x9000、0xb000、0x25000、0x27000、0x29000、0x2b000 | MDP 的 `qcom,sde-sspp-off`，相对于 MDP 基址 |

`/soc:ranges` 实际是 `<0 0 0 0xffffffff>`，不是空属性。采集器只接受明确的恒等映射且全部范围均被覆盖，其他总线翻译一律拒绝。主机测试发现并修正了最初只接受空 ranges 的限制；该初版没有在手机执行。

本机 XBL 的 DisplayDxe 来源、模块哈希和 9 个 DEPEX GUID 保持记录。公开接口目前只识别了 PlatformInfo、ChipInfo、Clock 3 项；其余 6 项提供者和完整运行时依赖尚未核实。因此没有把 DEPEX 当作可直接加载该模块的充分条件。

## 只读路径

新 `Sec/DisplayProbe.c` 使用读取回调，没有写寄存器接口。默认 PCD 为 FALSE，只有显式 `--display-probe --stop-after-stage 2` 构建才启用；其他阶段禁止启用该功能。

在原入口确认 MMU/cache 关闭后，先完成 FDT/内存几何检查和日志返回通道，再按顺序读取：

1. GCC DISP AHB 时钟门（GCC + 0xb00c）。
2. MDSS GDSCR（由 phandle 指定）。
3. DISPCC MDSS AHB（DISPCC + 0x2080）。
4. DISPCC MDSS MDP（DISPCC + 0x200c）。
5. 仅在四项检查通过后，读取 MDSS revision 和 8 个 SSPP 的 18 项配置，最多 149 个 32 位采样。

GDSCR 要求 PWR_ON bit31=1；DISPCC 两项时钟门保守要求软件 enable bit0=1 且 CLK_OFF bit31=0。GCC DISP AHB 另按一手源码的 `hwcg_reg=0xb00c/hwcg_bit=1` 处理：要求软件 enable=1，若 HWCG=1 则允许空闲 CLK_OFF=1；这与 `clk_branch_in_hwcg_mode` 下跳过停钟检查的源码语义一致。若不满足，记录原因后直接返回，不启用电源或时钟。检查这些位也不能证明不存在其他隐藏的访问限制。

首轮 wire version 1 对 GCC 也要求 CLK_OFF=0，已保留该实现的私有源码快照、独立尝试记录和原始审计 `display-source-audit-v1.json`（重建后与原构建记录 SHA-256 完全匹配）。当前 version 2 才采用上述 GCC HWCG 规则，主机解码器按版本分别判断。不得用后来的规则改写首轮结果。

采样按地址/值对保存，连同版本、状态、数量以大端 UINT64 写入 `raphael,display-snapshot`，经原 Android FDT 回传。主机依据同一份实时设备树，独立重建允许的读取顺序，拒绝停电/停钟后继续读取或额外地址的结果。

SSPP 配置即使有尺寸、格式和地址，也只能证明寄存器曾经被编程；它们可能是陈旧值，不能直接证明活动路由、物理地址映射、命令模式刷新和缓冲区生命周期。因此本轮禁止向这些地址写像素，`gop_validated=false`。

## 主机与模拟器验证

```sh
python3 scripts/audit_display_sources.py
python3 scripts/validate_display_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --display-probe
python3 scripts/build_handset_sec_dxe.py \
  --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --display-probe
python3 scripts/run_sec_dxe.py --serial <local-device-serial> \
  --build evidence/private/sec-dxe-build/20261027T154240Z
```

主机测试直接编译并执行同一个 C 采集器，以本机 FDT 为输入、用回调模拟 MMIO；它没有访问手机寄存器。当前 version 2 共 19 项测试，新增 GCC HWCG 空闲停钟和 HWCG 不能绕过软件禁用两项；原 17 项包括准确读取序列、每一级关电/停钟、未启用时钟、重复/越界/未对齐/过多管线、截断属性、过小寄存器区、非恒等映射、恒等窗口不足、错误 cells、禁用和不支持的节点。输入哈希、编译命令与产物哈希见 `display-probe-host.json`。

模拟器 `artifacts/sec-dxe-qemu/20261027T154138Z/report.json`：17 项通过。QEMU 没有匹配的 SM8150 节点，确认状态为 no-compatible-hardware、采样 0，并成功恢复交接；此项不模拟手机显示硬件。通电采集分支由主机回调测试覆盖。

首轮 version 1 私有手机构建 `20261027T154240Z`：FD 3145728 字节，SHA-256 `38022ee8fb976625848947f4584d7e946ee6f72aa23fec78a95aad095a5c7821`；私有 boot.img 134217728 字节，SHA-256 `9f362465acc80c464a04f22579f76f1f8ac3d8c1d0291ae9f6d6147a29321d7a`。快照保存全部包内输入且从快照编译；没有把私有镜像加入 Git。

## 实机

执行与回传结果单独保存，不能由上述主机构建和模拟器结果推断。旧版阶段 2/3/6 的成功证据属于各自的源码快照，本轮新增源码并没有重新验证其阶段 3/6 路径。


### 首轮实机结果（version 1）

`evidence/private/sec-dxe-run/20261027T154341Z`：stage=2/status=0，随机标记匹配，Android/root/原 boot 哈希审核通过。98 字节日志，丢弃 0。采样仅 1 项：GCC + 0xb00c = `0x80000003`，软件 enable=1、HWCG=1、CLK_OFF=1，按当时 version 1 的保守规则停止，没有读取 GDSCR、DISPCC 或 SSPP。

这个观测只能证明该时钟寄存器当时的值，不能证明显示电源域断电。源码核对显示 HWCG 模式允许空闲停钟，因此当前 version 2 细化了这一判断；两次实现和结果按版本区分。

`20261027T154610Z` 正常重启清理通过：Android/root 正常、原 boot 哈希不变、入口/SEC/DXE/显示临时属性均消失。

### Version 2 构建

19 项主机测试通过；QEMU `20261027T154858Z` 17 项通过。私有构建 `20261027T154911Z`：FD SHA-256 `6f0c63d4028d8e04385de7056252f4085ef8f5bdca9635d9e66f06873e0a7c9e`，boot SHA-256 `b535b123ef7ba3fc357ea8aa9c897d4e128e30ce7120e88726216f0b914da45c`。源文件快照之外，构建还保存来源审计与主机测试报告的完整输入快照，防止最新索引更新后失去当时依据。


### Version 2 实机结果

`evidence/private/sec-dxe-run/20261027T154955Z`：stage=2/status=0，随机标记、Android/root/原 boot 分区哈希均通过，100 字节日志、丢弃 0。回传 149 个 MMIO 采样，主机独立验证所有读取地址、顺序和门禁。见 `../UniXNU-raphael/evidence/sec-display-handoff.json`。

| 入口采样 | 观测值 | 边界 |
|---|---|---|
| GCC DISP AHB | 0x80000003 | enable=1、HWCG=1、空闲 CLK_OFF=1；本次可继续读取 |
| MDSS GDSCR | 0xf822f000 | PWR_ON=1 |
| DISPCC MDSS AHB | 0x1 | 时钟门运行条件通过 |
| DISPCC MDSS MDP | 0x221 | 时钟门运行条件通过 |
| MDSS revision | 0x50000001 | 本次实际寄存器读数 |
| VIG0 source/output | 1080×2340，原点 0/0 | 其他 7 个管线未观察到非零尺寸/地址/格式 |
| VIG0 plane0 地址寄存器 | 0x9c000000 | 是寄存器值；尚未证明 CPU 物理映射与活动 scanout |
| VIG0 stride0 | 4320 字节 | 启动期采样；不同于 Android DRM 的 4352 |
| VIG0 format/unpack/opmode | 0x237ff / 0x03020001 / 0x80000000 | 对应公开源码的线性 ARGB8888 配置，内存字节为 B/G/R/A |

`scripts/inspect_boot_display.py` 从私有原始回传重新解析，核对哈希和公开记录，再依据固定一手源码解释格式。按 stride×height 得到候选像素范围 `[0x9c000000,0x9c9a3f80)`，10108800 字节，完全位于本次 FDT 的 36 MiB cont_splash 保留区。实际末端以 `boot-display-observation.json` 数值为准。

格式解释有 8 项检查，包括真实配置识别及压缩格式、短 stride、错误字节序、裁剪、多矩形、安全源和越界地址拒绝。没有生成启用的 GOP 配置。UEFI 的 Reserved 字节语义也不能直接等同于当前管线启用的 alpha；后续必须核实混合状态。

`20261027T155236Z` 再次正常重启回原 Android，root/boot 哈希正常，入口/SEC/DXE/显示临时属性全部消失。清理元数据见 `sec-display-cleanup.json`。本轮没有刷写分区、写像素、改时钟/电源、加载闭源模块或操作原备份。

## 下一步的明确边界

现在已得到启动期编程地址、尺寸、stride、格式和电源/时钟观测。仍需沿本机 FDT 的 CTL、mixer、interface/pingpong 资源核实活动连接、混合/alpha、命令模式刷新，并核实 SMMU/CPU 映射及缓冲区存活期；这些条件解决后，才能进行可恢复的像素输出实验。显示未验证前不推进菜单、实体按键或 DarwinBoot/XNU。


本轮 version 2 固件包源码提交：`ac827ab6685947214128a80db05a8d16828815a0`。对该手机构建的 24 项包内源码逐一读取 Git blob 比较 SHA-256，全部匹配；QEMU 输入亦完全一致。此为构建后的哈希绑定，不能将 version 1 或此前 stage 3/6 自动绑定到这个版本。详细记录见 `sec-display-source-binding.json`。
