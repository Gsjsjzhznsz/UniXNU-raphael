# arm_init C路径的QEMU观测

2026-10-29。手机已经完成NATIVE-MMU.zh-CN.md中的原bootstrap MMU和arm_init入口；本页的更深C初始化仅来自独立QEMU，不是新增手机结论。

新增audit_native_early_c_qemu.py与GDB observer，复用234046Z最终MMU Image及原内核96d31e6。在高VA arm_init硬件断点暂停，仅在QEMU已加载内存恢复原首指令，随后执行原C代码，不修改原内核文件、跳过调用或替换返回值。另设高/低同步向量硬件断点，意外异常时先停止，避免进入仍假设原数据未变的stage10校验器。

235049.602686Z-uxxb1w8s保存5处PC/通用与翻译寄存器，以及每处全部10段文件/BSS的原始快照：arm_init、PE_init_platform(FALSE)入口、真实返回地址、rtclock_early_init入口、arm_vm_init入口。每轮bootstrap页表哈希相同；原PE初始化正常返回。到arm_vm_init入口之后不继续pmap重建，由主机终止QEMU，没有Android恢复验证。

独立validate_native_early_c_qemu.py在235353.342174Z-cpbih7yo核对全部原始文件哈希，按实际Mach-O load commands重新解析10段。初始快照除已声明向量/页表插桩外逐字节匹配原内核和BSS；随后独立重算各段差异与脏页，确认代码无新变化，变化只在__DATA_CONST、__DATA、__BOOTDATA。这些段合计2,637,824字节，都是当前内核软件布局，不是手机硬件参数。

| 停止处 | __DATA_CONST变化字节/页 | __DATA变化字节/页 | __BOOTDATA变化字节/页 |
| --- | ---: | ---: | ---: |
| PE_init_platform入口 | 52/2 | 25/1 | 55/1 |
| PE_init_platform返回 | 114/3 | 75/3 | 437/1 |
| rtclock_early_init入口 | 142/5 | 121/6 | 519/3 |
| arm_vm_init入口 | 173/9 | 7565/89 | 26713/29 |

源代码sources/apple-xnu-native/osfmk/arm/arm_init.c表明，原入口依次复制const_boot_args、初始化CPU数据、调用PE_init_platform(FALSE)、解析拓扑并设置当前线程，随后时钟/启动子系统初始化、arm_vm_init。pexpert/arm/pe_init.c的首次PE调用初始化SecureDT与平台参数；vm_initialized为TRUE后的中断/调试生命周期不在本页已执行范围。

下一步设计早期C可恢复profile：在已审计arena内保存源自Mach-O的全部允许变动段，验证备份及范围，捕获后恢复并重新核对全部10段/args/ADT及CPU状态；再接到arm_vm_init之前的有界检查点。只按QEMU看到的127个脏页保存不足以证明手机允许修改的完整范围。__DATA_CONST在早期仍会写入，不能仅按Mach-O写权限位选择备份。2.52MiB快照是否可分配、手机实际写入范围、cache清理和恢复仍未实现/未实测；后续pmap可能移除物理别名，不能直接延用当前relay恒等映射假设。

公开索引为UniXNU-raphael/evidence/native-early-c-qemu.json。原始内存快照位于ignored artifacts，无手机重启或分区写入。本轮无上游同步，原备份未改动，完整目标继续开发。

```sh
python3 scripts/audit_native_early_c_qemu.py --mmu-report artifacts/native-staging-qemu/20261028T234046.608038Z-kta3_q2o/report.json
python3 scripts/validate_native_early_c_qemu.py --report artifacts/native-early-c-qemu/20261028T235049.602686Z-uxxb1w8s/report.json
```
