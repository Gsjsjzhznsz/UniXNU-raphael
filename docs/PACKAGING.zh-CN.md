# 设备打包入口

2026-11-02：按 [官方设备打包规范](https://unixnu.com/zh/porting/packaging) 接入。
当前完成固定入口、配置解析、补丁预检查和手动 CI；**尚未完成从干净检出生成完整手机镜像的验收**。

## 入口和版本

`scripts/package.sh` 原样复制 UniXNU `c96b29975645b711dc06bc435c3ad27321ce817c`
的 `templates/package.sh`，保持可执行。脚本只读取 `board.toml` 的 `[package] unixnu`，
其余参数原样交给 `unixnu release`；不添加板名、地址、尺寸、参数或刷机命令。

`board.toml` 配置 `../sources/UniXNU-packaging` 为打包运行库，记录仓库和完整提交。
该路径是当前工作区的源码布局，独立设备检出时仍须按此相对布局放置运行库，或只修改 TOML 中的路径。
本机运行库由已经拉取的上游候选本地复制获得，包含原固定子模块；未再次联网更新。
现有 `sources/UniXNU` 和实机主线 ABI pin 保持原版本。预检查通过不代表新运行库已经验证完整内核构建。

只配置 `ipados-17.7.11-21H461 -> raphael_defconfig`，默认仍是保守的 compile-only 配置。
`17` 和完整配置名选择同一目标。本次不声明 26/27 支持，也不为它们伪造 defconfig 或复制另一套驱动。

## 本机检查

从设备目录运行，输出使用隔离目录：

```sh
python3 scripts/check-packaging.py
scripts/package.sh --no-deps --check --os 17 --out out/package-check
scripts/package.sh --no-deps --check --os ipados-17.7.11-21H461 --out out/package-check-full-name
```

`--check` 运行 deps/preflight/patches，然后在构建前停止；`--no-deps` 显式跳过已获取源码和 IPSW 的下载。
检查会写出选择的配置并列出补丁，**不会应用补丁、编译、生成启动镜像或操作手机**。
不带 `--check` 的标准入口按 deps、preflight、patches、build、pack、verify 继续运行；
默认 deps 只获取已固定版本，不使用 `--update`。

本机已检查默认 OS、`--os 17` 和完整配置名的补丁顺序一致，共 62 个补丁。
这是路径解析验证，不是补丁应用或新版本构建通过。完整镜像配方资格另用：

```sh
python3 scripts/check-packaging.py --require-release
```

此命令当前明确失败，列出缺失的 firmware/payload/bootimg 字段。
`release_recipe_complete=false` 不可写成镜像打包成功。

## 私有输入

`local.toml` 是源代码覆盖（例如本地 SM8150）；`unixnu.local.toml` 是 `[build]` 输入，两者用途不同。
后者必须显式通过 `--config /absolute/path/to/unixnu.local.toml` 指定，或放在 UniXNU 运行库根目录作为默认输入。
参考 `unixnu.local.toml.example`；平台种子和闭源材料不进入示例、仓库或日志。
种子通过 `UNIXNU_UNIQUE_CHIP_ID` / `--unique-chip-id`，固件检出通过 `UNIXNU_UEFI` / `--uefi` 传入。
源目录、输出目录、私有配置和生成镜像均保持 ignored。

## 手动工作流

设备 `.github/workflows/package.yml` 用于独立设备仓库；工作区根有对应入口，默认 device_dir 为设备目录。
两者运行在 macOS，通过 board.toml 读取 UniXNU 路径/完整 pin，通过 local.toml.example 解析 SoC 布局。
工作区已有 SoC 时直接使用；独立检出缺少 SoC 时必须填写真实仓库及完整提交，不猜 URL。
运行库子模块按其提交递归检出；check 模式运行 `--no-deps --check`，不需要平台种子或固件。

build 模式要求完整镜像配方、真实固件仓库/完整提交以及 fork 的 `UNIXNU_UNIQUE_CHIP_ID` secret。
它安装并断言 dtc、LLVM/lld、cmake、mtools、ipsw，然后调用同一 package.sh。
成功才上传 boot.img、payload.img、kernel.macho、package.manifest.json；找不到产物会失败，保留 1 天。
此为可能包含设备种子的私有产物，下载后按规范删除该 Actions 运行，不发布为公开 release。
本次在隔离源码夹具中执行了工作流的布局解析、SoC 覆盖写入、入口检查、62 补丁预检查及缺失配方拒绝分支；合计 21 项本地检查通过。未触发远端 Actions。

## 完整镜像尚缺的工作

1. 将现有诊断固件门禁表达为标准 `[firmware]` 配方：当前独立 SEC/DXE 包不是可直接套用的其他设备 Mu-Silicium 配方。
2. 把 signed owner policy、存储 ABI、不可变 extent、观测 ADT 的输入和所有权门禁表达为 `[payload]`；不能用 inspection DTS 代替手机运行 ADT。
3. 补齐 `[bootimg]` 的 DTB 生成和本机 shim/内存布局/返回合同。尺寸和分区限制必须来自本机冻结证据。
4. 按规范声明经过认证的官方 `[firmware.image]` 来源、选择性提取和模块生成；现有本地 vendor ZIP 未独立完成签名认证，不把它冒充可公开获取的生产输入。
5. 固定可发布 SoC 和全部源图后，在干净检出完整构建，核对清单、命令行 <1000 字节、镜像尺寸和所选输入；实机启动另验。

这些条件未完成，因此没有生成新的 boot.img、payload.img、kernel.macho 或 package.manifest.json。
标准 verify 对新产物记录尺寸/SHA-256 是打包合同的一部分；本次没有重新扫描 OS/SystemOS 大盘、boot 分区或备份哈希。
