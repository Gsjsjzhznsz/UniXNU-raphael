# DarwinBoot 接口验证

固定未修改的 DarwinBoot `3325e352d7df68a9f9ad74832ed94a6acbbd7390`，通过消费端 DSC 编译 `DarwinBootPkg/Driver/DarwinBoot.inf`，不创建伪造的上游 DSC。UniXNU 固定 `0fc0fc1f9ddd0fbd4787738afef38667df5e0a95`，Basecore 固定 `cfb93724a06ff86ff5ba971413368a7809ee42a5`。接口为 loader v2（0x00020000），协议 GUID 0f0a492e-5a6a-49f6-a1bf-743c87ab1cfe。

运行 `python3 scripts/run_darwin_fixture.py`。新测试程序实际 LoadImage/StartImage 原驱动，经过配置解析和 UniXNUBootEntry→loader Boot 调用，不修改通用代码。未选择 OS/ABI，没有有效内核、ADT、trust cache 或本机内存/外设参数。

首轮 AAVMF/QEMU 共38项通过：EL1、驱动句柄上的v2协议、父句柄与卸载入口、重复加载拒绝、空请求与缺失字段、FDT/kext拒绝、ramdisk布局、命令行1023/1024字符边界与ASCII限制、文件系统/缺文件/空文件/目录错误、8种短小损坏Mach-O、真正UniXNU调用后的错误返回、卸载移除及重载。每次Boot调用后均实际分配/释放内存并调用CRC服务；ExitBootServices通知从未触发。

主机已生成 ARM64 PE32+：DarwinBoot是EFI Boot Service Driver，测试程序是EFI Application，均具有重定位节。准确源码输入、构建命令、二进制哈希和串口日志保存在各自artifact目录。首次测试程序只包含公开UniXNULib头，编译暴露内部配置/日志接口未声明；已修正为显式包含固定内部头，失败构建目录保留。没有修改上游。

自有SEC/DXE现增加默认关闭的PcdRaphaelDarwinTest，仅QEMU构建器可用，且必须配合合成只读FAT。DarwinBoot作为FREEFORM/PE32存入自有FD，避免DXE提前派发；诊断控制器先安装临时SimpleTextOut内存日志协议、更新系统表CRC，再通过GetSectionFromAnyFv→LoadImage→StartImage执行未修改的驱动。日志虚拟几何80×25是诊断设计，不是本机显示参数，也不绘制像素。测试后UnloadImage、移除loader与文本协议、恢复ConOut/StdErr/句柄和系统表CRC。

自有DXE首轮QEMU正常43项、注入诊断入口BRK返回30项均通过；loader v2在本固件中安装，NULL/缺文件/损坏Mach-O和UniXNUBootEntry错误返回准确，ExitBootServices未触发、分配/CRC服务可用、合成FAT前后CRC不变。该测试没有借用AAVMF服务。状态另用18个u64的大端FDT属性回传并由独立Python严格复核。

运行：`python3 scripts/build_sec_dxe.py --payload-test --darwin-test`；阶段2/3分别增加`--stop-after-stage 2`或`3`。手机构建器明确排除darwin_test候选，不提供开启参数。手机尚未执行DarwinBoot，XNU未执行。此测试不覆盖合法Mach-O、ADT校验、256MiB以上连续内存窗口、ExitBootServices、MMU关闭和内核入口；不能称为DarwinBoot内核启动成功。


最终同源码分阶段结果及全部输入绑定见`darwin-sec-source-binding.json`（源码48c015077e113aeb2278cb75bf9d5bb06a4f6db1，56+47+9项）。独立wire24项通过，见`darwin-wire-host.json`。固定消费端源码AAVMF38项另见`darwin-fixture-qemu.json`。关闭Darwin的路径回归曾发现PACKAGES_PATH包含不存在的可选目录，已修复并重新通过；失败产物保留。


后续正向模拟器实验另见HANDOFF.zh-CN.md：原DarwinBoot经真实UniXNUBootEntry成功ExitBootServices并跳入合成裸机接收器，无initrd/原始/稀疏三模式22/25/25项通过。它与本页的拒绝测试分开归档；仍没有XNU或手机DarwinBoot执行。Apple官方xnu-10002.1.13结构ABI15项复核通过，只作结构参考。
