# 有界XNU实际指令入口

2026-10-29。新增默认关闭的NativeEntryTest，要求LoadTest、真实ExitBootServices完成、实际TimerArch和已武装的Android恢复胶囊。它是有明确边界的诊断profile，尚不能当作完整XNU启动。

## 源码实现

保持固定XNU文件96d31e6、通用Mu、UniXNU与DarwinBoot原样。独立核对原Mach-O入口B分支、目标可执行file段和精确五个opcode。原Mu成功退出、表清零、全部原内核段/args/ADT校验后，只将已加载start_first_cpu的第五条ADRP临时换成BRK #0x5350，设置自身有界异常向量，再向原DarwinEnter返回EFI_SUCCESS。

原DarwinEnter关闭MMU/cache并跳原XNU入口；执行原入口B、OSLAR写、DAIFSet、mov x20/x0、mov x21/0五条指令后触发BRK。独立汇编向量记录PC/ESR/SPSR/参数/页表与cache状态，用此前精确保存的SCTLR/VBAR和原诊断栈恢复UEFI执行条件；不调用BootServices。C检查精确checkpoint/标记/寄存器，再恢复原ADRP并重新验证全部10段CRC/零尾和args/ADT，stage9回传40Q记录并进入高段Android恢复胶囊。错误标记或错误寄存器被拒绝且带错误回传。重入直接停止，避免重复恢复。

40项offsetof及320字节ABI编译断言约束汇编。仅在已有独立arena内新增320字节静态状态，64KiB context仅增8字节范围检查指针；没有新增硬件地址或扩大内存合同。NativeHandoff布尔仍表示原先不受此检查点限制的正常profile，本诊断是否真正跳入XNU单独由native_entry_test/实际wire判定。

## 主机编译、结构与QEMU验证

首轮QEMU225607Z通过27项；225918Z同样通过27项。独立230000Z复用225918Z的完全相同Image：硬件断点逐条单步跟踪5条原始指令及BRK到真实向量，正常恢复；另一轮将已加载BRK改为错误标记#0x5351，真实异常被拒绝，仍恢复原指令/页表和Android接收器，接收器按预期返回失败。保存原始trace/GDB/串口日志。之后加强运行时可执行段范围检查，固定最终实现为4f66e91。最终QEMU230113.769341Z-7s8qmra1通过27项；独立230158.578152Z-m6tseu8n再次复用该Image完成上述单步/错误标记两项验证。默认关闭的normal/BRK/UDF回归230000.679208Z-5v24wrz1分别47/44/44项通过；它属于增加最后的可执行段门禁前的源码快照。最终源文件另经230757.702531Z-4qnuhvbp完整默认回归，normal/BRK/UDF仍分别47/44/44项通过，结构检查通过。

本诊断在设置XNU自身VBAR、读取boot_args和建页表之前结束。不能宣称arm_init、XNU平台/GIC/timer、根卷或用户态已在手机执行。UART外部接线/输出仍未知；日志使用独立内存回传，无持久化存储写入。

## 手机构建、预检与执行

build为evidence/private/android-return-build/20261028T230206.640094Z-qe3glqjg，编译及FD/ARM64结构通过；boot SHA256 619c15f11add0100fdecd76f23f65365caedaa0fcff98f4b0478bcb72a5e93b3。FD SHA256 33ec8de61369c8a8b39f5c3629bb624bcace45aaebaeb2053e7fb3a535f8832c。25,559,040字节实际下载Image，56MiB独立arena及256MiB实验内核grant保持不变。实际C内存合同预检230254.652017Z-1dp87t6x五项通过。

run为evidence/private/android-return-run/20261028T230308Z，仅一次临时fastboot boot，无flash/erase/format。nonce匹配，SEC stage9/status0、native-entry version1/status3、armed/trap各1、Error0。原入口0xc0424488，checkpoint/ELR 0xc042606c，ESR 0xf2005350；x0/x20均0xc1274000、x1为入口、x21为0；EL1、SCTLR的MMU/cache位关闭、向量slot4。原ADRP和原UEFI翻译恢复通过，随后全部10段文件CRC/零尾、args/ADT仍正确。

约80.453秒自行返回Android，无bootloader辅助；root、原boot哈希、后续正常重启及临时属性清理通过。本机PhysicalTimerArch的280次IRQ/EOI及退出停钟/原状态恢复通过，频率仍19.2MHz、PPI18；这不是XNU的timer初始化证据。

## 原始证据独立复核

validate_native_entry_evidence.py --revision 4f66e91 --run <上述run> --qemu-audit <230158Z>/report.json，输出artifacts/native-entry-verification/20261028T230546.673234Z-_ljo0txh，通过381项Git blob/冻结源码绑定。独立重新解析实际Mach-O指令/符号，核对固定Apple start.s、原boot/ramdisk/DTB/repack、原始40Q/16Q/FDT/log、QEMU单步轨迹与错误标记拒绝、物理timer全套解码和正常重启清理。公开索引为UniXNU-raphael/evidence/native-entry-verification.json，原始数据仍私有。

最初独立QEMU审核脚本的主机语法检查发现转义错误，在执行前修复；没有由该失败脚本触发手机操作。没有改动通用基础设施或冻结内核文件；运行时唯一指令插桩已在诊断返回前恢复。

下一步需为XNU自己的异常向量、boot_args读取、页表切换和arm_init建立持续日志与恢复，再接本机CPU/GIC/PPI18生命周期。当前不能直接去掉检查点并把黑屏或复位解释为启动成功。上游保持固定，不自动fetch/pull；原备份未改动，RAM alias扩展继续暂停。

## 重现命令

```sh
python3 scripts/run_native_staging_qemu.py --stage 6 --load-test --exit-complete --entry-test
python3 scripts/audit_native_entry_qemu.py --positive-report <QEMU>/report.json
python3 scripts/build_native_staging_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report <QEMU>/report.json --stage 6 --load-test --exit-complete --entry-test
python3 scripts/check_native_staging_plan.py --build <private build> --fdt <previous cleanup.dtb>
python3 scripts/run_android_return_handset.py --serial <本机ID> --build <private build>
python3 scripts/validate_native_entry_evidence.py --revision 4f66e91 --run <private run> --qemu-audit <audit>/report.json
python3 scripts/build_sec_dxe.py
```

以上是已经完成的对应命令；新构建应使用其自身新证据目录和精确版本，不能套用旧nonce或镜像。最终验证脚本在手机构建后新增，单独保留实际verifier.py和SHA256；381项原构建输入仍严格绑定4f66e91，没有把新增验证器混入旧构建快照。
