# 原XNU pmap换表与恢复接口

2026-10-29。手机仍以c8d001c的stage11为准：原arm_init C到arm_vm_init首指令，完整三段数据恢复和Android返回通过。以下为QEMU独立观察，不能提升为手机arm_vm_init函数体执行或换表后恢复证据。

复用最终stage11同一Image（001542.298120Z-bi91y1_b），只在QEMU已加载内存恢复arm_vm_init首条原指令；没有改原内核文件、跳过调用或提供假返回。002613.342287Z-atqmwzun的7处真实断点覆盖arm_vm_init入口、set_mmu_ttb_alternate调用前后、set_mmu_ttb调用前后、原arm_vm_init返回和PE_consistent_debug_inherit入口。原换表函数的机器码分别使用DSB SY/DSB ISH，独立验证器按实际Mach-O核对，不以函数名推断屏障。

原TTBR0/1为0x6017e000/0x6017f000；本次执行后的根为0x61278000/0x61279000。TCR保持0x22a51a251a，4KiB/38bit。这些物理地址是本次QEMU布局，禁止移入手机板级配置。空TTBR0根页4096字节全0，原物理relay别名未映射；保留的TTBR1仍将原低/高向量、arm_vm_init、PE_consistent_debug_inherit与3段全部644页映射到原物理页。

递归物理读取全部可达活动表，共66页/270336字节，SHA256 0ac96e0cd825d960e17af1029ac17d550e395ad6fcd173ba7b9f7b3466d6df42。全部表页在本次实际分配的256MiB grant内。7处各有3段完整原始快照；最后相对原Mach-O/BSS变化为395/1828/8856个64位字，合计132948字节的12字节delta，仍在既有256KiB预算内。

validate_native_pmap_evidence.py独立核对原文件SHA、396份Git/blob/冻结输入、Mach-O符号与BL返回地址、7处实际寄存器、每页层级/范围/唯一性/可达关系与描述符、空低根/高地址644页映射，以及所有快照的变化计数。首次复核003259Z在预期屏障机器码检查处拒绝（把原DSB SY误写为DSB ISH）；更正验证器后003335.884868Z-nq0nercu全部通过，旧失败保留。公开索引UniXNU-raphael/evidence/native-pmap-observation.json不含私有原始采集。

固定源码依据：apple-xnu-native d8b80295118ef25ac3a784134bcf95cd8e88109f的osfmk/arm64/arm_vm_init.c设置gVirtBase/gPhysBase并使用args.memSize；调用set_mmu_ttb_alternate(cpu_ttep)与set_mmu_ttb(invalid_ttep)。实际编译树使用既有native arch timer补丁，不能仅看原Apple平台代码推断本轮MMIO行为。

下一阶段设计：在原高VA文本内先捕获真实TTBR状态，使用自有arena内的独立TTBR0转换表，只重新映射物理relay所在2MiB block；保持原TTBR1与高PC有效，再跳物理relay、清理原3段dirty缓存并恢复UEFI。转换表状态必须与原XNU状态分开记录。该设计尚未实现或手机验证。

活动页表本轮270KB，不能直接原样追加到余量约233KB的既有FDT；下一实现需有严格容量/页数/范围检查的稀疏描述符格式，不扩大内存合同。pmap动态表位于原topOfKernelData后，原3段备份不覆盖它们，不能声称恢复整个256MiB。const_boot_args可能被重定位，下一合同须核实实际字段，不能静默放宽stage11门禁。

```sh
python3 scripts/audit_native_pmap_qemu.py --mmu-report artifacts/native-staging-qemu/20261029T001542.298120Z-bi91y1_b/report.json
python3 scripts/validate_native_pmap_evidence.py --revision c8d001c --run artifacts/native-pmap-qemu/20261029T002613.342287Z-atqmwzun
```

本轮ADB再次在线，Windows无串口设备。用户提供的log-capture指南已按固定本地40d21cc文档核对：UEFI Advanced Logger、交接后UART/屏幕、独立日志读取器与测试证据目录分阶段使用。真实UART引脚、电平与输出未知；未复制其他板型PMIC、watchdog或存储区域。未同步上游、写分区或修改原备份，RAM alias仍暂停。

## 换表后恢复实现（stage12，手机待验证）

默认关闭PcdRaphaelNativePmapTest/--pmap-test，依赖stage11完整链。checkpoint从冻结Mach-O提取PE_consistent_debug_inherit首条sub sp,sp,#0x30，唯一BL返回地址来自arm_init；此函数固定头文件声明(void)，所以不要求无ABI意义的残留x0/x1；仍记录这两个原值，完整比较const_boot_args/BootArgs及原callee-saved状态，没有放宽stage11的x0/x1门禁。

高向量先到同一原内核文本的高VA relay前缀，在寄存器x8保存原TTBR0，保持原TTBR1/TCR，安装独立TTBR0并跳同一relay的低物理body。4页转换表由原Mu分配器在既有36MiB heap内分配；一页L1、一页L2、两页部分边界L3，精确映射原loader的256MiB grant。首尾16KiB不向外舍入，relay所在2MiB块允许EL1执行，其他块PXN；页表与每项原字节经主机独立重建比较。它是临时诊断映射，不能冒充原XNU空TTBR0。

原高物理映射区经过arm_vm_physmap_slide重定位，本次QEMU活动页表均无原线性高VA别名。原physical aperture有新别名，但不把QEMU差值移入手机。因此在转换后按精确低地址grant逐行DC CIVAC，行长读CTR_EL0，DSB后才关MMU/cache；覆盖原数据、栈、新活动表和ADT。交接前也显式清理独立UEFI heap与context，因为原DarwinEnter只清理其kernel grant。未扩大arena、RAM或FDT合同。

新256字节/32Q pmap记录将原TTBR0/1、实际转换根、clean范围、完整表CRC、容量/页数/描述符、映射门禁及ADT前后/恢复CRC分开。活动表最多256页、稀疏快照最多65536字节，每页LE<QHHI>为PA/层级/非零项数/完整4096字节CRC，每项LE<HQ>为索引/描述符；DFS严格核归属/深度/唯一层级/容量。主机独立重建所有4096字节表并检查可达集合、空TTBR0、旧relay未映射和644页高数据映射。完整16KiB转换表另行回传。外部arena state加Pmap指针，context仍0xf000。

首轮004704Z走通恢复，但最终ADT CRC拒绝。原因已查明：原pexpert/gen/pe_gen.c的随机数读取循环将/chosen/random-seed清零，原3段备份不包含装载ADT。新增独立有界64KiB ADT备份/变化快照与恢复；主机要求原ADT除64字节random-seed清零外所有结构和值一致。没有把CRC门禁关掉。005218Z的36项通过，首轮独立005556Z在CTR_EL0寄存器别名读取失败，修正观察器后005631Z全部5场景通过；失败目录保留。

补齐独立heap/context交接前PoC清理后，010040.816661Z-89015ian的36项通过；010136.826021Z-bjus6xrp复用同一Image的trace、wrong-brk、bad-active-table、transition-corrupt、backup-corrupt五场景通过。trace在原arm_vm_init换两表并返回后读取三段全部字节、全部活动页表和ADT，与回传逐字节/重建SHA一致，并跟踪高前缀、原x8、安装转换根、物理body、首条DC CIVAC和cache-off。活动页表叶项损坏会拒绝644页门禁；转换表仅损坏未活动根项，用于证明完整表CRC拒绝，不声称任意转换映射损坏仍可恢复。数据备份损坏仍拒绝复制坏段并返回。

```sh
python3 scripts/run_native_staging_qemu.py --stage 6 --load-test --exit-complete --entry-test --mmu-test --early-test --pmap-test
python3 scripts/audit_native_pmap_recovery_qemu.py --positive-report <stage12>/report.json
python3 scripts/validate_native_pmap_recovery_evidence.py --revision <实现提交> --qemu-report <stage12>/report.json --qemu-audit <五场景审核>/report.json
```

本实现尚无手机stage12证据；旧手机仍仅到arm_vm_init入口。动态新页表虽在owned grant内，记录后不做整256MiB原字恢复；原3段、原向量/代码/初始表和输入ADT有单独恢复证据。尚无正常XNU IRQ/timer生命周期、根卷或用户态。下一步固定实现、最终构建/QEMU/旧分支回归、手机布局预检与一次临时启动。

## 最终冻结与手机实测

实现03e07a3，最终QEMU010739.199487Z-nmv0jqcb为36项；相同Image独立010918.351195Z-z02x2sib五项全部通过。011036.454365Z-kk5a1enm在手机测试前绑定405份Git/blob/冻结输入及全部正负向原始证据。默认关闭回归010650.746921Z-3b0t8n7e为normal/BRK/UDF=47/44/44；stage10的010650.746489Z-775l6din为28项，stage11的010449.868706Z-bn2jpplg为31项。公开QEMU索引native-pmap-recovery-qemu.json。

手机build evidence/private/android-return-build/20261029T011108.128888Z-hpl1ieaz编译/结构与405输入独立通过，011308.399617Z-ty6waksj实际C布局预检五项通过，ADT9772字节。boot SHA256 d45b18c8fd518f41862c27116038e9a6b78c1e111cde9bd258761d093e1a55fc；FD SHA256 e22b203563b17017ee5fb064564d433ba2e85c062d2febc2ddd584844fa2fe60。下载Image仍25559040字节。

实机run evidence/private/android-return-run/20261029T011328Z：仅一次临时fastboot boot。SEC stage12/status0、MMU version2/status3/error0、early version2/status3/error0、pmap version1/status3/error0。实际ELR=0xfffffff0079b00d0，ESR=0xf2005351，LR=0xfffffff007a1238c，interrupted SP_EL0=0xfffffff007bbff30。原XNU TTBR0/1=0xc1278000/0xc1279000，与诊断转换根0xd2600000分开记录。TCR=0x22a51a251a、SCTLR=0x3454593d、MAIR=0x0c0804ff00bb44ff。

66页活动表/2679非零描述符，稀疏27846字节，独立重建完整270336字节，SHA256 9e10fa87dfca9dc8e2ea20de432380bb87c0c4bb50347b82fbd7d100951f5dae；原低根全零/旧物理relay未映射/644页高数据及三个高代码probe均通过。完整16KiB转换表与独立生成的每项原字节一致。输入ADT随机种子64字节清零是唯一变化，原备份CRC及完整恢复通过。

三段2,637,824字节备份/恢复3/3，变化64位字395/1827/8856，共11078字，delta132936字节，SHA256 ce5c7d1921348627b9fc7035a5a9729a1a67a055efc61038b9afa4167322cdb4。原10段CRC/零尾、boot_args/ADT、原代码/向量/初始页表及UEFI寄存器恢复全部通过。FDT937551字节，仍在既有1114112字节预算内。

80.337秒自动回Android，没有bootloader辅助恢复；随后正常重启，root/原boot SHA/临时属性清理通过。011633.014700Z-mrmj68pt重新核对405份Git输入、私有boot repack/恢复胶囊、原始FDT/wire/delta/表、同镜像QEMU实际快照/五种场景及正常重启命令记录。公开索引native-pmap-recovery-verification.json不含设备标识或私有原始镜像。

```sh
python3 scripts/build_native_staging_handset.py --collection evidence/private/device/20261027T120325Z --qemu-report artifacts/native-staging-qemu/20261029T010739.199487Z-nmv0jqcb/report.json --qemu-audit artifacts/native-pmap-recovery-qemu-audit/20261029T010918.351195Z-z02x2sib/report.json --stage 6 --load-test --exit-complete --entry-test --mmu-test --early-test --pmap-test
python3 scripts/check_native_staging_plan.py --build evidence/private/android-return-build/20261029T011108.128888Z-hpl1ieaz --fdt evidence/private/android-return-run/20261029T001904Z/cleanup.dtb
python3 scripts/run_android_return_handset.py --serial <本机ID> --build evidence/private/android-return-build/20261029T011108.128888Z-hpl1ieaz
python3 scripts/validate_native_pmap_recovery_evidence.py --revision 03e07a3 --run evidence/private/android-return-run/20261029T011328Z --qemu-audit artifacts/native-pmap-recovery-qemu-audit/20261029T010918.351195Z-z02x2sib/report.json
```

本轮请求用户指定porting与log-capture在线页面，但未取得可读正文；按本地固定40d21cc版本重读相关文档，未fetch/pull或替换固定源码。UART外部引脚、电平、适配器及输出仍未知，Windows未枚举串口；现有完整原始内存/FDT/Android自动回传是本机阶段诊断。正常XNU fault/IRQ/timer、平台驱动完整生命周期、根卷和用户态继续开发，不能把本次插桩恢复当完整移植。
