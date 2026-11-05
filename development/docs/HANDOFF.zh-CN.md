# DarwinBoot 正向诊断交接

本测试在独立 AAVMF/QEMU 中实际执行固定、未修改的 DarwinBoot `3325e352d7df68a9f9ad74832ed94a6acbbd7390`。它加载我们生成的最小 ARM64 Mach-O，成功 ExitBootServices 后，经原 Entry.S 的清缓存、关闭MMU并跳转，进入独立裸机接收器。**接收器不是XNU内核**，没有手机执行或正式OS启动成功的结论。

## 源码与设计输入

`tests/RaphaelTestPkg/HandoffFixture.*` 是消费端EFI应用与DSC；`scripts/fixtures/darwin_handoff_*` 是独立接收器。构建器从源码快照编译。Basecore、UniXNU、DarwinBoot仍固定原版本；Mach-O load command、boot_args布局、ADT/RAMDisk格式均按该DarwinBoot的一手源码实现，没有修改上游。

合成虚拟基址 `0xffff000000200000`、单段容量128KiB、段内16KiB栈、默认256MiB窗口都是测试设计。虚拟基址没有借用其他手机；物理地址由真实AAVMF内存图和原DarwinBoot的AllocatePages动态选出。窗口最小值来自原WindowSize.h，不代表手机有该范围的可分配内存。**手机当前诊断arena仅16MiB，不满足此分配窗口要求，不允许照搬QEMU结果。**

合成ADT仅有fixture根、chosen/memory-map及诊断属性，不描述SM8150或任何真实OS硬件。第一种无RAM-disk；第二种为4097字节原始数据，检验两页发布及零填充；第三种为DBRDISK1两段稀疏数据，逻辑16KiB、中间8KiB为空，检验真实展开。所有输入均从本项目生成，未使用私有模块、固件或内核镜像。

## 实际调用与检查

EFI应用LoadImage/StartImage原DarwinBoot并从其句柄读取loader v2，实际UniXNUConfigLoad→UniXNUBootEntry→Loader.Boot。应用通过单独分配、cache-line隔离的页记录ExitBootServices通知；回调只增加计数并写回该页缓存。命令行传递该诊断页地址。未用替换Boot Services或改写loader的方式模拟成功。

接收器在自己的段内设置栈，使用QEMU semihosting输出，每一项判断均在退出Boot Services之后执行。核对EL1、SCTLR.M/C/I关闭、DAIF全屏蔽、x0的16KiB对齐及boot_args v2、VA/PA重定位与2MiB对齐、实际256MiB窗口、kernel-data边界、ADT VA→PA与长度、通知恰好一次、无GOP时video零值、未指定flags/machine字段与段尾零填充。

独立ADT遍历器核对完整边界、chosen/memory-map/RAMDisk路径，CRC只将loader允许修改的16字节RAMDisk地址长度对归零后与原ADT比较。原始/稀疏模式进一步核对RAMDisk物理位置和界限、发布长度、独立预期文件的内容CRC、页尾零填充。预期数据由主机构造，不调用loader的解包函数生成。

ESP以只读方式给QEMU，并逐文件比较启动前后哈希。AAVMF代码、初始变量模板、两个EFI文件、接收器Mach-O、ADT、输入与预期RAM-disk均记录哈希，构建和QEMU命令完整保存。

运行：

```sh
python3 scripts/run_handoff_fixture.py --ramdisk-mode none
python3 scripts/run_handoff_fixture.py --ramdisk-mode raw
python3 scripts/run_handoff_fixture.py --ramdisk-mode packed
```

## 失败与修正

- `20261027T211642.066404Z-esumh8wf`：runner未初始化UniXNU Python模块路径；改用已有inspect_device入口。
- `20261027T211659.482282Z-guw7zy3y`：使用上游boot_args头触发UEFI wchar_t静态断言；增加-fshort-wchar并移除冲突的stddef引用。
- `20261027T211719.809391Z-6w0cg6po`：接收器与EFI构建日志文件重名，排他创建明确拒绝覆盖；改为单独保存receiver-build.log/receiver-commands.json。
- `20261027T211736.315165Z-ya7t7sxd`：首轮无initrd，19项通过；此时尚无新增ADT路径和video检查。
- `20261027T212102.448537Z-_2eap34h`：扩展后的稀疏展开25项通过；固定源码最终三模式结果随后另记。

## 边界

AAVMF提供架构协议、内存图、文件系统和运行时服务。此测试与自有SEC/DXE的架构测试分别记录，不能合并声称自有固件或手机已经完成内核交接。没有XNU执行、Darwin用户态、磁盘根文件系统、OS profile选型、实体按键或手机完整RAM所有权验证；正向交接只覆盖上述合成格式和状态。实际XNU还需要核实版本ABI、平台驱动、可保留的连续内存及完整设备树。

## 固定源码最终运行

消费端和接收器固定源码 `c7803747631becbe400e3844b4e3aa8660b8d024`；每种模式的全部73项输入及runner逐Git blob核对，报告保存在 `handoff-fixture-qemu.json`，包括完整构建/QEMU命令和所有产物哈希。

| 模式 | 检查 | artifacts/handoff-fixture-qemu/ |
|---|---:|---|
| none |22通过|20261027T212339.490632Z-qyjme3ug|
| raw |25通过|20261027T212339.491163Z-k_2j4so4|
| packed |25通过|20261027T212339.490626Z-iz6rw6tq|

各模式原DarwinBoot均为19968字节，实际文件分别记录哈希，未宣称不同构建目录的字节可复现：

| 模式 | DarwinBoot SHA-256 |
|---|---|
|none|`9480b0b91d43eecd4b69023e5039a192aa2e08262d730cb4ba002b167354f5d4`|
|raw|`8f4136f44810b149f91bdb82f46b3f73342736727969ab6df07197b3e0dea35e`|
|packed|`fdcf01676a8b2d9eb385f1294381850ea0df0e249387a7a16d1ee4a6f9eaf68d`|

三种只读ESP启动前后逐文件哈希一致，QEMU正常退出，无超时。

## Apple一手ABI复核

本次新建 `sources/apple-xnu-abi`，从Apple官方仓库取得tag对象 `a653a70d861014a544bffa506779088605bbabac`（xnu-10002.1.13），解析为commit `1031c584a5e37aff177559b9f69dbd3c8c3fd30a`，准确版本追加到sources.lock.json。它是ABI参考，不是已选手机OS或已构建内核。

`audit_boot_args_abi.py` 从该commit的arm64/boot.h提取未经改写的Boot_Video和boot_args声明，去掉仅供内核的include后，分别以主机和AArch64编译器编译，与原DarwinBoot头逐字段比较。13字段偏移、size和alignment共15项全部匹配；两种目标的布局记录完全相同，size0x480、alignment8。字段包括Video0x28、deviceTreeP0x60、CommandLine0x6c、memSizeActual0x478。完整源哈希、命令、对象哈希见 `boot-args-abi.json`。此结果只证明一个版本的结构布局，不证明早期页表、异常模型、平台驱动或XNU实际执行。

不同构建目录的DarwinBoot文件包含不同绝对PDB路径（经llvm-readobj --coff-debug-directory确认），所以逐模式保留实际哈希，不混用此前独立拒绝测试的二进制哈希。通用源码tracked diff为空。
