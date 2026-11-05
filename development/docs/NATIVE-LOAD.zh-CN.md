# 原 DarwinBoot 有效装载与预退出检查

2026-10-29。新 profile 默认关闭，保持 NativeHandoff=FALSE。复用已经验证的独立 arena/高段 Android 返回；自有 DXE 加载固定、未修改的 DarwinBoot，将冻结有效 XNU 和有来源的本机 ADT 交给原 loader。只在 BeforeExitBootServices 通知内检查加载内存并退出至 Android；不能称为 ExitBootServices 完成或手机 XNU 执行。

## 代码和输入

NativeLoadTest.c 预先从 FV 读取独立策略，核查当前内核窗口 HOB、arena 边界、频率与 CPU affinity。策略按原 Mach-O 各 LC_SEGMENT_64 的文件字节 CRC/虚拟跨度/执行入口生成。回调不调用 BootServices，核对各文件段 CRC、各段零尾、Darwin23 boot_args ABI/命令行/空视频、树原字节 CRC，再调用 SEC 的原恢复入口。记录指针和静态结果有 arena 边界检查，64KiB context 的0xf000静态预算保持。

最初直接选 ExitBootServices 通知的 QEMU 候选20261028T221653.058792Z-4bklr_lr在原Mu CoreExitBootServices的gTimer->SetTimerPeriod处异常（ESR 0x96000005，FAR 8）。replay-debug.gdb/log保存真实断点状态。这个profile没有TimerArch，故新检查明确使用原Mu BeforeExitBootServices事件，在定时器关闭和memory map终止之前返回；后续真正完成Exit必须接入实际TimerArch。未增加假服务或修改Mu/DarwinBoot。

## 本机 ADT 来源与政策

raphael_adt.py读取本次设备采集的live.dtb（7b24eee80e40f2444153b8effacd5c476fd394fcff62aa5e807d5a161c9384f5），从cpu@0、interrupt-controller@17a00000、timer读取CPU affinity/GIC/物理PPI；与原观测RAM/入口频率交叉检查。单CPU、19.2MHz、PPI18；GICD0x17a00000/0x10000、GICR0x17a60000/0x100000均来自该FDT，未复制模拟器值。无GOP安装，boot_args视频为0；本轮不验证屏幕交接。

chosen dram-base/size选择包含实验内核窗口的FDT单独物理bank（0xc0000000/0xc0000000）。不会把分离bank和洞压成整段；它用于XNU的gDramBase/gDramSize物理分类，实际可管理内存仍由boot_args的256MiB严格限制。固定实际编译源osfmk/arm/arm_init.c:643-652与osfmk/mach/arm/vm_param.h:302-303是消费依据。这不授予该3GiB其余部分，不声明完整手机RAM所有权。其他bank/保留区仍在独立来源记录中。

64字节random-seed由主机os.urandom产生；CHRP NVRAM为空的通用易失合成bank，不读取或写手机NVRAM。ADT只含单CPU/GIC/timer及通用DT平台必要节点；UFS/根卷/其他外设待实现。原树无终止符的无关ifaa compatible不被消费；所选目标节点仍执行严格字符串检查。

## 已完成验证

- 主机编译和FV/FFS/PE结构：通过；最初context超预算、const限定、缺SEC专有符号、检查器新增对象拒绝均保留在各失败构建目录，未执行手机镜像。
- QEMU stage7：native-staging-qemu/20261028T222009.150760Z-_814olww，25项通过。各段CRC/零尾、boot_args和有效ADT通过，原高段receiver完整恢复46MiB内核/8MiB零尾及寄存器。参数来自当轮QEMU FDT，无手机参数或XNU指令执行。
- 负向：native-load-negative-qemu/20261028T222147.696362Z-3c4s4dv1。真实硬件断点停在原通知回调，调试器只改坏已加载内核第一个字节；检查器仅一个文件段CRC失败，返回status0x23a，receiver仍逐字恢复。expected receiver failure不冒充正常成功。
- 默认诊断normal/BRK/UDF回归47/44/44：sec-dxe-qemu/20261028T222147.707130Z-i4v4ttdz。
- 原有有效XNU自有SEC/DXE真实timer IRQ回归通过：native-sec-dxe-qemu/20261028T222147.702450Z-7d18oaa5；仍仅QEMU。
- 手机镜像构建/检查通过：build20261028T222217.883858Z-f_hm4vi4，boot SHA256 19faaa7d97b5ac62816095897f2605a144819d4b8e5278788665aa34ef4071ad。手机执行与独立复核已通过，详见下节。

## 重现

```sh
python3 scripts/run_native_staging_qemu.py --stage 6 --load-test
python3 scripts/run_native_load_negative_qemu.py --positive-report <QEMU>/report.json
python3 scripts/build_native_staging_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report <QEMU>/report.json --stage 6 --load-test
python3 scripts/check_native_staging_plan.py --build <private build> --fdt <last cleanup.dtb>
python3 scripts/run_android_return_handset.py --serial <本机ID> --build <private build>
```

仅临时fastboot boot，原备份不变；上游固定、不自动fetch/pull，私有产物不提交。

## 手机结果与独立复核

实现 a1c1949；run evidence/private/android-return-run/20261028T222405Z，build 与 boot 哈希如上。nonce/SEC stage7 status0/完整返回/原ramdisk跨度通过，49.674秒自行回Android；正常重启后root、原boot哈希和临时属性清除通过。原DarwinBoot protocol revision为0x20000，实际装载基址0xc0004000，args0xc1274000、tree0xc1275000、entry0xc0424488、window256MiB；10段文件CRC及10段零尾均通过。入口地址为原Mach-O虚拟偏移计算，未执行该入口。

本轮本机ADT通过真实loader解析/复制，实际CNTFRQ19.2MHz、affinity0；BeforeExit通知计数1，原ExitBootServices通知计数0。独立核查器首次把协议revision误写为整数2而拒绝，修正为固定头文件中的0x20000后，native-load-verification/20261028T222806.219478Z-n37imt9_重新核对374个Git/冻结输入、完整repack、本机原始kernel/ramdisk/DTB、独立ADT解码和FDT/wire/log/cleanup通过。公共索引为UniXNU-raphael/evidence/native-load-verification.json。

这证明原loader的有效加载与预退出回调；真实ExitBootServices完成、手机XNU指令、根卷/用户态仍未完成。下一步为真正退出时的TimerArch/CPU服务生命周期和退出后可回读检查。
