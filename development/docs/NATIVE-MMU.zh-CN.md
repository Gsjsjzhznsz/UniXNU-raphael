# XNU bootstrap MMU 与 arm_init 入口

2026-10-29。默认关闭的 NativeMmuTest 是原生 XNU 启动主线的有界检查点。手机阶段10已通过，并独立复核原始记录；arm_init的C函数体尚未执行。

保持固定原内核96d31e6、UniXNU、DarwinBoot和Mu原样；只在已加载内存临时插桩。原服务退出及10段CRC/零尾、args/ADT检查之后，备份原两套向量、arm_init首指令与64KiB bootstrap页表。原DarwinEnter跳原内核；原汇编读取boot_args、建立页表、设置TCR/TTBR/MAIR/SCTLR并跳到高地址arm_init。首条sub sp临时替换为BRK #0x5351，尚不执行C函数体。

替换的向量入口无栈跳到内核物理别名中的诊断relay；关闭MMU/cache，恢复原UEFI翻译、VBAR、线程寄存器及SP_EL0，使用已有诊断栈。C保存完整64KiB页表并逐描述符检查，恢复全部临时代码和原页表，再检查原10段CRC/零尾及args/ADT。72Q记录与页表快照经FDT和高段Android恢复胶囊回传。没有新硬件地址、外设MMIO或RAM扩展；context维持0xf000预算。

160字节RAW policy由实际冻结Mach-O符号/机器码生成；包括arm_init、向量、页表、两个栈顶和TCR/MAIR/SCTLR。栈和页表是内核软件布局，不能当其他手机硬件参数。实际编译start.s的BCM timer MMIO受已启用的XNU_NATIVE_ARCH_TIMER条件排除；本profile不修改这些指令。

页表期望为38-bit/4KiB、128组2MiB恒等与高地址block、4个表页及258个非零描述符；其余字节为零。原grant起始16KiB偏移，最末16KiB不在该初始block映射内；不能称完整最终pmap。TCR 0x22a51a251a、MAIR 0x0c0804ff00bb44ff、SCTLR 0x3454593d来自实际内核，本轮手机读回已精确匹配。

初轮232315Z确已捕获高地址入口，但38-bit软件walker错误使用高地址完整9bit顶级索引，检查失败；修为先屏蔽有效VA位后232426Z通过27项。快照指针初放context触发61448超过61440编译断言，随后移到arena状态尾部，未扩大预算。232739Z与最终232914.955441Z-j7r3jzvm均通过28项，后者新增C全部64KiB精确比较。完整Python表审核核对128组两端、args与arm_init翻译、所有未用表页。

独立233708.381333Z-duu6wj2q复用232914Z同一Image：硬件断点和单步确认MSR SCTLR、ISB、arm_init高VA、BRK高向量、物理relay与cache关闭。错误BRK #0x5352与最后高VA block物理地址位损坏分别被拒绝，原代码/页表/UEFI恢复及接收器返回正常，接收器按预期报失败。首次独立审核误将最终Error=2期待为1，在正确拒绝后审核断言失败；源码Finish实际写2，修正审核为精确2，失败目录保留。

下一步固定实现提交，重新构建最终QEMU、独立审核、手机构建/实际C预检及一次临时fastboot boot，独立重解码全部原始证据。QEMU通过不等于手机能够启动，arm_init入口不等于C函数体、平台/GIC/timer、根卷或用户态。外部UART引脚/电平及真实输出仍未知；本轮不fetch/pull、不扩展RAM alias、不写分区或原备份。

```sh
python3 scripts/run_native_staging_qemu.py --stage 6 --load-test --exit-complete --entry-test --mmu-test
python3 scripts/audit_native_mmu_qemu.py --positive-report <QEMU>/report.json
python3 scripts/build_native_staging_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report <QEMU>/report.json --qemu-audit <audit>/report.json --stage 6 --load-test --exit-complete --entry-test --mmu-test
python3 scripts/check_native_staging_plan.py --build <private build> --fdt <previous cleanup.dtb>
python3 scripts/run_android_return_handset.py --serial <本机ID> --build <private build>
python3 scripts/validate_native_mmu_evidence.py --revision <实现提交> --run <private run> --qemu-audit <audit>/report.json
```

## 最终版本与手机证据

实现提交为 `d2a82df33cd052e4014eb61090d1257df7938863`。最终QEMU为234046.608038Z-kta3_q2o，通过28项；同Image独立审核234132.768702Z-aduhgp55的trace/wrong-brk/bad-table均通过。默认关闭的normal/BRK/UDF最终回归234505.655862Z-_ferx7g9为47/44/44。

手机build为 `evidence/private/android-return-build/20261028T234211.830607Z-mpqst6en`，实际C布局预检234314.867371Z-evu5yzh0五项通过。boot SHA256 `ff3540a448b538dd47227ea71baa36466c1f82c4bfe474dcd51ddd0cac4e0d93`，FD SHA256 `cd9359d1ef7eb110258a4c2085e2d5cf1ab6f9d1a73834671a77ffd7e1354245`。实际下载Image25,559,040字节，arena和内核grant保持原合同。

手机run为 `evidence/private/android-return-run/20261028T234327Z`，仅一次临时fastboot boot。SEC stage10/status0，MMU status3/error0，armed/trap各1。高VA checkpoint/ELR=0xfffffff007a11bfc，ESR=0xf2005351；x0为高VA boot_args，x20为PA 0xc1274000，x21=0。TCR/MAIR/SCTLR与原内核期望全部一致；TTBR0/1为0xc017e000/0xc017f000，异常栈/中断栈和高向量符合原软件布局。两个arm_init别名的翻译均为PA 0xc0a11bfc。

完整页表65536字节，SHA256 `09ac5aecee04da17d7ca7ebdda82983455d194c75e81149072f8c24b0f741ddc`，258非零描述符、128组block及4个表页通过C和Python独立检查。原低/高向量、首指令、页表和UEFI线程/翻译状态恢复后，原10段文件CRC和零尾、args/ADT仍通过。本机物理TimerArch仍为280次IRQ/EOI，不能当XNU timer生命周期。

80.516秒自动回Android，无bootloader辅助；正常重启、root、原boot分区哈希和临时属性清理通过。原始wire/FDT/代码及输入绑定的389项独立复核为234552.357284Z-5mk70_1d，公开索引为 `UniXNU-raphael/evidence/native-mmu-verification.json`。它覆盖原始repack/loader/ADT、完整页表、最终QEMU逐步轨迹与两种负向、私有原镜像及正常清理；原始数据保留在ignored目录。

下一步推进arm_init C函数体及PE_init_platform之前/之后的可恢复日志，必须处理实际全局/栈修改、cache一致性和后续pmap重建，不能直接套用本检查点的原字节CRC或物理别名恒存假设。完整操作系统启动仍未完成。
