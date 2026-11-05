# 只读负载与 UniXNU 集成

## 已通过：独立 AAVMF/QEMU 测试

运行 `python3 scripts/run_payload_fixture.py`，实际编译并调用未修改 UniXNURamDiskDxe.c 的入口、UniXNULib 配置解析和EFI交接。入口参数为模拟器中构造的本模块HOB/FDT，内存来自AAVMF分配；未接触手机分区。
1MiB FAT12是诊断设计预算，使用已有mtools生成，无须新增格式化工具。测试载荷和源码快照均在artifacts中；公开记录哈希与结果，不公开镜像。

17项检查通过：BlockIo发布、扇区边界、媒体ID、写保护、DiskIo/FAT连接、文件写入拒绝、从RAM卷读取配置、EFI子程序参数与ParentHandle握手、完整UniXNURun倒计时退出。计时约2.09秒；1080×2340截图已人工检查布局。
模拟器提供DiskIo/FAT、CPU与周期定时器架构服务，不能将其称为手机驱动成功。见payload-fixture-qemu.json。

## 开发中：自有SEC/DXE的合成只读负载

默认关闭PcdRaphaelPayloadTest，目前仅QEMU构建脚本提供启用参数；手机构建器明确排除该模式。
FAT作为RAW section放进已保留的自有FD，SEC检查实际section长度与FD范围，创建独立的4KiB合成FDT并发布Mu入口参数HOB。没有覆盖Android的initrd属性。
使用固定Basecore的UnicodeCollation、DiskIo、FAT和固定UniXNU RAM-disk驱动；诊断检查写保护、文件系统、配置和负载CRC。完整UniXNURun设置timeout=0自动退出，这不提供周期TimerArch。
首次集成限定headless，不改动已验证GOP画面；也不宣称新的可见菜单。所有地址来自本次自有FV布局和arena分配，不使用其他手机配置。
自有SEC/DXE的stage2/3 QEMU通过，stage6正常36项、注入BRK29项通过；修正已连接文件系统被错误判为连接失败的诊断逻辑。最终同源码stage2/3/6已重新通过，全部54项板级/47项通用输入逐文件绑定提交6f6d63b125463d4fc009c128a6f00ed6c7d03f32；实际计数见payload-sec-source-binding.json。独立wire校验3个正常阶段及15个损坏记录全部通过。手机尚未执行此功能。用户休息期间保持手机在Android，实体菜单与按键观察推迟。

## 边界

这不是XNU负载，也未调用DarwinBoot。完整物理内存所有权、定时器/中断架构、设备实际FAT输入与EFI负载执行仍需单独验证。
