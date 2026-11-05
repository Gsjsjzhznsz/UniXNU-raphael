# 原服务退出的诊断返回

2026-10-29。实现29d4a51。独立默认关闭profile在已验证的原DarwinBoot有效加载基础上，观测真实Mu ExitBootServices返回，然后通过高段Android胶囊恢复。手机20261028T224029Z已通过真实原服务退出和Android自动返回；独立复核376项输入及原始回传通过。XNU仍未执行。

## 实现边界

NativeLoadTest保持NativeHandoff=FALSE，新增NativeExitComplete要求LoadTest及实际TimerArch/CPU服务。手机启用此前独立验证的物理TimerArch、ICC/NS使能视图、路由与IRQ诊断，全部在本次入口重新门禁；没有复制QEMU的PPI30/62.5MHz。QEMU使用其自身标准驱动，仅限模拟器。

自有DXE暂时替换BootServices表的ExitBootServices入口，并正确更新表CRC。原loader调用时，诊断入口先恢复准确的原函数及表CRC，不分配、不重新获取内存图，不改变loader的key；随后调用原函数，记录实际返回状态。原Mu定时器关闭、内存图终止、Exit通知、CPU中断关闭、系统表清除、BootServices表清零均由固定上游执行。诊断入口在真实函数返回后核对成功、系统表指针为空、整份原BootServices表逐字节为零，再核对内核段和boot_args/ADT，直接进入原Android恢复通道。它不返回到DarwinEnter，不执行XNU指令，不修改Mu或DarwinBoot源码。

wire version2/status4仅用于这条成功路径；version1/status3仍代表原BeforeExitBootServices检查。Exit失败或内存合同失败均返回带错误的诊断，不将缺记录当通过。实体物理TimerArch的原Exit事件执行硬件恢复，SEC随后只在Dirty仍存在时再次要求恢复；不会从已终止的服务表请求分配。

## 主机与模拟器

- 最初stage8 20261028T223251.178816Z-2bjkdr7n拒绝于SEC status0x110。真实断点证明为稀疏映射数量仍按连续布局计数；新代码按低输出/initrd/arena三段及独立窗口精确计算，MMIO另逐项检查不重叠，不映射洞。
- 最终正向native-staging-qemu/20261028T223811.512878Z-hi66_0gi：25项通过，version2/status4，原服务退出后内核内存保持，receiver完整恢复原46MiB/8MiB零尾及寄存器。
- 负向native-load-negative-qemu/20261028T224024.600265Z-yfyhrcaa：真实Exit通知断点改坏一个已加载字节，原服务退出后检查器正确拒绝该段且Android接收器恢复。前一次223909Z仅复核脚本仍期待version1而失败，原始证据保留；当前脚本根据profile核对version2，并保存实际runner及其哈希。
- 默认normal/BRK/UDF回归47/44/44：sec-dxe-qemu/20261028T223811.512317Z-kx2l3o0p。
- 原有有效XNU真实timer IRQ回归：native-sec-dxe-qemu/20261028T223811.528110Z-s2h42j1o，通过，仍仅QEMU。
- 手机build20261028T223912.222732Z-73jkh_gv编译/结构检查通过，boot SHA256 a69889d388c336f34cb08842eabf632ec04fefd219dd7a4717814892c47c3f50；native-staging-plan/20261028T224028.610006Z-41_z4bho的5项真实C预检通过。实机结果如下。

## 重现

```sh
python3 scripts/run_native_staging_qemu.py --stage 6 --load-test --exit-complete
python3 scripts/run_native_load_negative_qemu.py --positive-report <QEMU>/report.json
python3 scripts/build_native_staging_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report <QEMU>/report.json --stage 6 --load-test --exit-complete
python3 scripts/check_native_staging_plan.py --build <private build> --fdt <last cleanup.dtb>
python3 scripts/run_android_return_handset.py --serial <本机ID> --build <private build>
python3 scripts/validate_native_load_evidence.py --revision 29d4a51 --run <private run> --negative-report <negative>/report.json --exit-complete
```

下一步仍是可诊断的手机XNU指令入口及交接后的CPU/timer生命周期；UART外部接线和输出仍未知。原备份不变，手机镜像只通过临时fastboot boot，私有输入不提交，无自动上游同步。

## 手机执行及独立复核

私有run为20261028T224029Z：nonce匹配、SEC stage8/status0、native-load version2/status4、Exit通知1、Error0。原Mu真实返回EFI_SUCCESS，系统表服务/控制台指针为空、原BootServices表全零；10段文件CRC及10段零尾、args和ADT CRC仍正确。入口只计算为0xc0424488，没有跳转。

本机物理TimerArch收到280次IRQ/280次EOI，无未知或spurious；relative、periodic5、cancel、退出停钟及原GIC/ICC/CNTP/CNTV状态恢复通过。约80.475秒自行进入Android，无bootloader辅助。root、原boot分区哈希及后续正常重启清理通过，临时诊断属性消失。

独立命令使用--revision 29d4a51和--exit-complete，输出artifacts/native-load-verification/20261028T224532.081516Z-1t6jm58x。376项构建/工作流/原上游输入逐Git blob与归档快照核对，原Android内核/ramdisk/DTB/repack、nonce/wire/log、物理timer各层解码与清理均复核通过。公开脱敏索引为UniXNU-raphael/evidence/native-exit-verification.json，原始数据和镜像保持私有。

这证明原ExitBootServices完成及退出后的内存合同/恢复；不证明XNU执行、根卷、用户态、GOP交接、全RAM所有权或UART输出。
