# arm_init C初始化与有界恢复

2026-10-29。新增默认关闭NativeEarlyTest（stage11），要求原服务退出、入口/MMU诊断和独立Android恢复通道。手机stage11已通过并完成原始证据独立复核，arm_vm_init函数体尚未执行。原被冻结内核96d31e6、Mu、UniXNU与DarwinBoot保持原样；只对已加载代码插桩。

policy根据实际Mach-O选择arm_vm_init首指令（原sub sp,sp,#0x190），从arm_init的BL解析唯一返回地址；原arm_init栈帧208字节、const_boot_args及BootArgs指针和0x480字节ABI由原机器码/符号核验。MMU policy保持原格式，额外224字节RAW包含3个完整恢复段及CRC，没有引入板级地址。

Prepare阶段通过原Mu AllocatePool取得2,637,824字节备份及32字节双端guard，严格限制在既有arena的36MiB heap内；不扩RAM或allocator合同。真正ExitBootServices成功、原装载检查通过后保存完整__DATA_CONST、__DATA及__BOOTDATA，逐段CRC匹配原内核/BSS。随后安装已验证的低/高向量relay，仅把arm_vm_init首指令改成BRK #0x5351。原arm_init C执行首次平台初始化、拓扑/当前线程和早期时钟/启动子系统，停在pmap重建前。

原C会产生dirty WB数据/栈。relay在当前映射仍有效时，读取CTR_EL0确定真实D-cache行长，对3段逐行DC CIVAC并DSB，再关闭MMU/cache和恢复UEFI翻译/线程寄存器/SP_EL0。没有将QEMU缓存行长度当手机参数；该路径尚需手机事实验证。

捕获后记录全部变化64位字，单条little-endian offset32/value64，固定256KiB预算；超过预算会拒绝，同时继续原数据恢复。备份guard与每段CRC在写回前重验；坏备份不复制。完整备份恢复、写回、原低/高向量及首指令恢复后，原10段CRC/零尾、args/ADT重新检查。320字节40Q early记录和变化delta、原72Q/MMU/64KiB页表经FDT回传。context仍为0xf000，未新增context字段。

native_early.py按原Mach-O文件/BSS和delta重建全部3段，重算每段CRC/SHA、变化计数、const_boot_args/BootArgs指针及页表快照对应。独立GDB在同一Image的真实检查点读出3段全部字节，重建SHA逐段匹配，避免只凭摘要或检查点推断C阶段内存。

首轮000624Z的原固件已到stage11并完成恢复，主机解码器将20字节命令行误切19字节而失败；修正后原日志离线完整解码通过，旧失败目录未覆盖。000932.774642Z-byk5obyk正向31项通过，delta130,908字节/10,909字。独立001306.772757Z-5ciaysr3复用同Image：trace、wrong-brk、bad-table、backup-corrupt四项通过。第一次独立001059Z的前三项通过，备份注入访问arena在新XNU映射外而失败；改用QEMU明确的物理内存调试模式后成功，没有扩大目标映射或改变固件。

wrong-brk以#0x5352触发真实异常拒绝，bad-table损坏最后高VA block，完整表检查拒绝；均恢复原数据。backup-corrupt将第一备份段首字翻1bit，guard仍在，但CRC失败；该段拒绝复制、其余2段恢复，最终原10段检查只过9段，接收器按预期失败且能够返回。所有负向均只在隔离QEMU执行。

接下来固定提交并重建最终31项QEMU与四项独立审核，执行默认和stage10回归、手机镜像与实际C预检，再进行一次临时fastboot boot和独立原始证据复核。手机仍以NATIVE-MMU.zh-CN.md的arm_init入口为准，不能把本页QEMU提升为手机C初始化证据。arm_vm_init函数体、pmap、正常XNU异常处理、IRQ/timer生命周期、根卷及用户态仍未验证。当前没有同步上游、分区写入或原备份修改，RAM alias扩展暂停。

```sh
python3 scripts/run_native_staging_qemu.py --stage 6 --load-test --exit-complete --entry-test --mmu-test --early-test
python3 scripts/audit_native_mmu_qemu.py --positive-report <stage11 QEMU>/report.json
python3 scripts/build_native_staging_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report <stage11 QEMU>/report.json --qemu-audit <four-case audit>/report.json --stage 6 --load-test --exit-complete --entry-test --mmu-test --early-test
python3 scripts/check_native_staging_plan.py --build <private build> --fdt <last cleanup.dtb>
python3 scripts/run_android_return_handset.py --serial <本机ID> --build <private build>
python3 scripts/validate_native_early_recovery_evidence.py --revision <实现提交> --run <private run> --qemu-audit <four-case audit>/report.json
```

## 最终版本、主机与手机结果

实现 `c8d001c5b4cb90a88dd9e91963b83c7d96eb0bd2`。最终QEMU001542.298120Z-bi91y1_b为31项；相同Image的独立001644.965618Z-oddn27_d四项通过。默认关闭001706.257771Z-f32et11t的normal/BRK/UDF回归为47/44/44；原stage10路径001725.758693Z-7zn5u38g仍通过28项。

手机build为 `evidence/private/android-return-build/20261029T001807.440946Z-f2cstle8`，编译/FD结构通过；实际C布局预检001849.654997Z-8o4yoy_4五项通过。boot SHA256 `d7ec47b6bea0fe1fd13b42de41879a3b82249c401d788b82a62c7d997ae2d75b`，FD SHA256 `b0368687d312e9a9d6a956567f0f7835c31c42e338b3569cf5329b9954fcdb1e`。下载Image仍25,559,040字节，内核grant与56MiB arena未扩。

run `evidence/private/android-return-run/20261029T001904Z` 仅一次临时fastboot boot，SEC stage11/status0，early version1/status3/error0，SavedRanges/RestoredRanges=3/3、ArgsCopyOk=1、DeltaOverflow=0。ELR=0xfffffff00741c110、ESR=0xf2005351、LR=0xfffffff007a12374；x0=0、x1=0xfffffff00717bcf8，SP_EL0=0xfffffff007bbff30，符合原arm_init帧和调用合同。TCR/MAIR/SCTLR、TTBR0/1及原bootstrap64KiB页表仍符合本轮原内核状态。

原3段合计2,637,824字节的备份CRC/guard均通过，变化字数为305/1762/8841，共10,908；delta130,896字节，SHA256 `4588269d3efb03e7dad7f5002d80c43408519f3ce9e1292667e2ff83caac8bbb`。独立从原Mach-O/BSS重建每段，核对CRC/SHA、const_boot_args/BootArgs和页表。范围分别来自__DATA_CONST、__DATA、__BOOTDATA，不将Mach-O只读标志解释为早期不可写。

恢复后10段文件CRC和零尾、args/ADT均通过；80.434秒自动回Android，无bootloader辅助。正常重启/root/原boot哈希/临时属性清理通过。物理TimerArch仍有280次IRQ/EOI及退出恢复，但不当作XNU正常IRQ/timer生命周期证明。回传FDT881,101字节，在既有1.1MiB预算内。

独立核验002146.046009Z-dv4lkdne通过396项Git/blob与源码快照绑定，重新解析原镜像repack、原始wire/FDT/delta、QEMU真实内存和负向、正常清理；公开索引为UniXNU-raphael/evidence/native-early-recovery-verification.json，私有数据保持ignored。

下一步arm_vm_init会换TTBR1并将TTBR0设为invalid_ttep（固定源码arm_vm_init.c约2151/2155）。现有向量先跳物理别名，在此后不成立；需要先从实际同Image QEMU查明新页表、保留的高地址映射和所有权，再实现受控转换表/恢复，不直接去掉BRK或把黑屏解释成进展。完整目标继续开发。
