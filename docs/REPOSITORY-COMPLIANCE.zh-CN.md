> 这是2026-11-01历史整改记录。仓库发布及SoC固定已在2026-11-05推进，当前发布状态见[PUBLICATION.zh-CN.md](PUBLICATION.zh-CN.md)，实机状态以根README和最新handoff为准。

# 设备仓库规范整改（2026-11-01）

本次在活动工作区 `/home/guo/work/raphael-fresh` 实施目录、构建引用、记录与文档整改。`D:\project\unixnu` 继续作为交接导出目录。没有执行手机实验、刷写、上传系统盘或重新计算系统盘哈希。

规范依据为已固定的 UniXNU 一手文档：

- [设备仓库](https://unixnu.com/zh/porting/device-repository)：设备 package、配置/补丁、私有输入、解析构建和发布要求。
- [SoC 支持](https://unixnu.com/zh/porting/soc-support)：共享资源和平台操作归属 SoC 的 kits/；板级内存、连接和选择归设备。
- [记录](https://unixnu.com/zh/porting/records)：13 个必需区域、组件依赖覆盖、英语正文、证据等级和变更检查。
- [驱动](https://unixnu.com/zh/porting/drivers)、[UFS](https://unixnu.com/zh/porting/ufs)、[设备树](https://unixnu.com/zh/porting/device-tree)、[启动验证](https://unixnu.com/zh/porting/bring-up)：硬件输入、所有权、ABI、逐层实机验收。

官网正文访问受限，本次以活动 UniXNU 固定版本 `f0721e9745c45ad2600cd69c74730f1cca55d56a` 的 `docs/zh/porting/` 原文和官方模板/检查器执行。记录规范与已有独立上游候选中的版本一致；未把交接材料中的操作文字当作新的用户授权。

## 已修复

| 原问题 | 现在的处理 |
| --- | --- |
| 板级驱动游离于设备 package | 移至 `UniXNU-raphael/package/drivers/`，显示配方通过组装树 `kits/raphael/drivers/` 读取 |
| 板级固件在工作区外置目录 | 全部归入 `UniXNU-raphael/package/firmware/`，包含 RaphaelPkg、DSC/FDF、Resources；更新全部活动脚本引用 |
| SoC 平台操作放在 drivers 根目录 | 移至 `UniXNU-sm8150-common/kits/Sm8150Platform/`；CPU/UFS配方、主机fixture同步 |
| 迁移导致跨仓库头文件链接失效 | 修正 5 个固件 Include 链接指向唯一 SoC 源码；冻结构建时仍物化为自足文件 |
| 缺规范 DTS/config 名称 | 新主入口 `dts/raphael.dts`、`configs/raphael_defconfig`，SoC `dts/sm8150.dtsi`、`configs/sm8150.config`；board 与生成器同步 |
| 缺正式移植记录 | 新建 `porting.toml`，完整配置/固件/CPU/内存/存储/显示/输入/GPU/网络/音频/电源/组装/诊断 13 区，覆盖静态组件与显式开发profile的附加组件 |
| 缺固件来源/哈希入口 | 新建 `proprietary-files.txt`，复用已有观测哈希；修正旧 JSON 中 boot 的过时用途描述；不分发blob或私钥 |
| 嵌套 workflow 不会在工作区根执行 | 补官方设备 workflow，并另加工作区根 `.github/workflows/porting-record.yml`，固定记录工具版本 |
| 独立设备 ignore 不完整 | 补 out、pycache、pyc等，保留 local.toml/.cache/build 忽略规则；SoC也自足 |
| README/AGENTS仍停留在未实现状态 | 更新责任、输入、规范链接、构建命令、实机边界、待开发与发布条件 |
| 显示独立配方当前编译失败 | 暴露固定XNU分配宏缺尾字段 kt_zshared 的诊断；按已有UFS配方精确允许该warning类别，保留 -Werror；显示及offline keystore重新编译通过 |

旧 observed DTS/config 名称以及工作区 `uefi-raphael` 为相对兼容链接，没有第二份可变源码。历史 artifacts、private报告和失败产物保持原路径；当前交接源码路径更新。SoC文件仍沿用既有Raphael符号名，不代表其他SM8150设备已验证。

`package/`内核对象是静态接入，固件服务由已有DSC/FDF启动。没有输出可动态加载EFI驱动时，不伪造 `Kit.toml` 的driver条目。默认 `raphael_defconfig` 仍是保守的compile-only配置，专用handset profile已有独立APFS/PID1证据；这两件事必须同时写清楚。

## 已实际验证

- 官方检查器：`raphael: 13 structured areas checked`。`python3 scripts/check_repository_layout.py`通过布局、引用、跨仓库头文件链接及记录检查。
- 官方 `unixnu defconfig raphael_defconfig`、`status --json`、`tree` 在新的隔离输出成功，确认 `tree/kits/raphael` 指向设备package。SoC为显式本地覆盖；未使用的refer显示未解析，完整构建通过已有本地固定缓存接入，不假称新输出已fetch全部依赖。
- 新旧DTS由dtc编译，DTB逐字节一致；RAM/保留区/CPU/GIC roundtrip通过。156个迁移源文件逐字节未变。
- `python3 scripts/build_native_bootstrap.py --cpu --native-diagnostic`完整构建通过，887份编译记录；独立Mach-O检查通过，未定义符号0。这是CPU诊断profile，不替代成功实机的冻结handset镜像。
- 新位置的SEC/DXE完整构建及QEMU normal/injected_brk/unmapped_udf三组通过，分别47/44/44项。
- UFS真实XNU ABI对象编译通过；实际只读传输在既有独立QEMU8.2.2 UFS模型37项通过。extent plan18、readonly extents24、UFS handoff14、native video24项及payload hash小型向量/reader测试通过，均非实机新结果。
- 新package路径的显示配方在隔离输出编译通过358-slot原始ABI、绑定archive及offline keystore。没有声称完成新的显示运行或手机显示验收。

最终 `git diff --check`、246个Python脚本语法、README相对链接、新记录私有字段及package二进制/密钥检查通过；固定UniXNU源码无改动，交接两个副本逐字节一致。

本次源备份、原dirty清单、迁移对照和完整检查索引：工作区 `artifacts/repository-layout/20261101T140258Z/`，主要文件 `source-before.tar.gz`、`migration.json`、`validation.json`。失败的显示编译日志保留为 `display-build.before-warning-fix.log`。

## 尚未达到的规范完成条件

这些是当前工程实际缺口，不能靠补文件或填占位参数消除：

1. **可复现发布**：设备/SoC仍在现有工作区，尚无完整适配提交、公开SoC URL/审查commit。feeds不伪造URL/提交；local.toml明确本地覆盖。未嵌套git init、未混入提交整棵脏树，也未发布仓库/topic或触发远端CI。下一步冻结审查后的独立源码图，再更新feed并验远端CI。
2. **正式证据等级**：记录正文如实保留本机APFS/SystemOS、原launchd exec/EL0及22次syscall事实；因缺完整对应源码commit和可访问的不可变日志，结构化状态仅标implemented/planned。脱敏摘要是源码说明，不能伪装device日志。提交前还需确保所引证据文件已纳入提交；检查器只核存在性，不证明已提交或内容真实性。
3. **变更CI**：设备独立工作流按官方模板可用；工作区根工作流检查结构。官方 `--base` 比较已提交代码，当前未提交改动不能声称已通过该检查；完整提交后需按真实base执行，并核对每个代码路径的区域更新。
4. **标准生产构建链**：诊断固件/内核/载荷依赖工作区编排、私有原盘与owner策略；`board.toml`尚无完整生产firmware/payload/bootimg recipe。已把板级源码、现有构建配方和启动接入写清，未编造分区几何、RAM所有权或可直接运行的生产镜像。后续需要将同样门禁表达为标准recipe，独立检出验证。
5. **驱动与桌面**：单CPU和只读存储不等于完整SM8150支持。输入、GPU、网络、音频、完整时钟电源与持久Data仍待开发/验证；显示有开发实现但无手机桌面证明。当前最深仍是原PID1真实EL0及22次Unix syscall，尚无dyld完成、launchd main、SpringBoard或基本交互证据。

因此，本次完成的是可在本地修复的结构和记录整改及构建回归。不能把“记录检查通过”表述成“规范发布、生产移植或桌面目标全部完成”。
