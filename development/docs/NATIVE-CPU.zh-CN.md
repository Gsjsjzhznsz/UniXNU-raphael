# XNU主线：平台、单启动核和定时器

2026-11-01 路径迁移：本文历史记录中的 `UniXNU-raphael/drivers/` 现位于 `UniXNU-raphael/package/drivers/`；`UniXNU-sm8150-common/drivers/` 现位于 `UniXNU-sm8150-common/kits/Sm8150Platform/`。历史构建/实机结论和冻结artifact不变。当前状态与规范差距见[交接](HANDOFF-20261101.zh-CN.md)及[整改说明](../UniXNU-raphael/docs/REPOSITORY-COMPLIANCE.zh-CN.md)。

2026-10-29，Asia/Shanghai。真实XNU已经在QEMU到达bsd_init和IOFindBSDRoot入口。手机有效DarwinBoot/XNU交接仍未执行；没有根卷挂载或用户态结果。

主线优先。RAM alias的11路径SEC接入WIP已保存在stash `3fb57136db5b293859402f36f8bf44a1f9548a46`，暂停扩展；已有两阶段完整窗口QEMU结果保留，不作为手机或分配合同。只有用户明确要求时才同步上游。

## 源码实现

- 通用UniXNU固定40d21cc65171c3a24faa130a2a8e899f85790485；XNU固定d8b80295118ef25ac3a784134bcf95cd8e88109f；DarwinBoot固定3325e352d7df68a9f9ad74832ed94a6acbbd7390；Mu Basecore固定cfb93724a06ff86ff5ba971413368a7809ee42a5。
- 原样接入ArmDTPlatform 417ff95d6a6e8607ddea9309ec45c3bfd4a67c60。真实IODTPlatformExpert::configure发布CPU、bus、defaults和NVRAM；通用实现不含本机地址。
- 新增独立 `UniXNU-sm8150-common/drivers/RaphaelBootCpu.cpp`，要求版本化ADT标记unixnu,boot-cpu=1、与现场MPIDR一致且仅单启动核。SMP、resume、halt和power management未实现，明确拒绝或panic。
- GIC范围、stride、timer INTID、trigger及物理/虚拟选择均来自明确ADT输入；检查范围、溢出、GICv3 revision、亲和性和现场CNTFRQ。没有复制其他手机地址，没有引入上游ArmCpu的PPI27、1008+ SPI或板型诊断策略。
- GIC使用Arm IHI0069C定义的标准偏移；匹配本核redistributor，有限等待wake/RWP，只接入SGI0及所选timer。真实调用ml_processor_register、IOCPUInterruptController、rtclock_intr和IPI handler，完成EOI。当前GIC接管和失败路径仍需手机验证。
- SGI0发送/分发已实现，但本轮IPI计数为0，尚无IPI投递验证；不能将timer IRQ结果推广到IPI或SMP。
- 本机XNU patch替换CPU personality，并通过现有cpu_set/get_decrementer_func接入CNTP，timer pending跟随所选源。未删除原断言、伪造成功回调或跳过加密自检。
- 接入固定libpthread c0e60fb5ecfc54cf379c261d3f9572cc22ded891的3份真实C与通用bootstrap，解决首次进入BSD后的函数表panic。
- 固定后端使用build/armcpu/libArmCpu.a作为CPU链接槽；该archive的唯一成员实际是独立RaphaelBootCpu.o。上游ArmCpu没有编入，recipe/provenance明确记录来源。

## 主机构建和结构

```sh
python3 scripts/build_native_bootstrap.py --platform
python3 scripts/build_native_bootstrap.py --cpu
python3 scripts/inspect_native_kernel.py --build-report artifacts/native-bootstrap-attempt/20261028T175838Z/report.json
```

--platform仅启用通用DT expert；--cpu使用raphael_cpu_defconfig，另启用独立CPU、标准timer entry和source pthread。构建只装配已在本地的准确固定模块；runtime cache缺失会报错，新profile可复用准确本地缓存，没有隐式fetch/pull。

175838Z构建成功：887份XNU对象记录，独立CPU的Werror ARM64/iOS17对象，真实crypto/pthread archives。最终内核18,463,480字节，SHA256 `96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722`。180002Z独立Mach-O检查通过，未定义符号0。内核、887记录、25项板级/SoC输入、31份辅助产物及日志冻结在不可变attempt。未执行prelink或手机打包。

失败保留：172411Z缺平台archive；172825Z临时recipe路径错误，后改用原组件recipe。175244Z独立CPU首编有2处OSSharedPtr转换和3处volatile increment的Werror，修正源码后通过，未降低检查。175508Z链接成功但未接pthread，该内核的模拟执行到BSD后panic；不能用后续成功改写旧结果。

## 实际执行

```sh
python3 scripts/run_native_xnu_qemu.py --inspection artifacts/native-kernel-inspection/20261028T180002Z/report.json --stop-at cpu_ready --boot-cpu virtual --kalloc-zones 200
python3 scripts/run_native_xnu_qemu.py --inspection artifacts/native-kernel-inspection/20261028T180002Z/report.json --stop-at cpu_ready --boot-cpu physical --kalloc-zones 200
python3 scripts/run_native_xnu_qemu.py --inspection artifacts/native-kernel-inspection/20261028T180002Z/report.json --stop-at timer_irq --boot-cpu physical --kalloc-zones 200
python3 scripts/run_native_xnu_qemu.py --inspection artifacts/native-kernel-inspection/20261028T180002Z/report.json --stop-at find_root --boot-cpu physical --kalloc-zones 200
python3 scripts/validate_native_cpu_evidence.py
```

| 检查点 | 不可变run（UTC） | 结果 |
|---|---|---|
| DT平台configure | 173553.895689Z-x260mw8x | 真实LR返回x0=1；CPU/bus/defaults/NVRAM成功；最终crypto status0、默认POST0 |
| 无CPU驱动的更深执行 | 174156.501951Z-gbvd1ki5 | 期限失败；停机PC/帧链为ml_get_timebase、processor_idle、idle_thread，不推断唯一原因 |
| CPU接入但缺pthread | 175558.928329Z-j7p74ti0 | 到bsd_init后明确panic；cpu_ready目标失败，stage2 |
| 完整CPU start、虚拟timer | 180003.214566Z-4m2pogbm | 真实LR返回x0=1、stage5/registered1；到bsd_init；返回时IRQ0，不能当IRQ通过 |
| 完整CPU start、物理timer | 180134.991843Z-53jpn1ee | start真实返回成功，范围仅此检查点 |
| 物理timer IRQ | 180349.726107Z-e13esz8b | CPU start、bsd_init、真实rtclock_intr，6次timer/6次EOI和IRQ caller返回；pthread status0/函数表非零 |
| 根设备查找入口 | 180646.225922Z-oa3mg6zu | 到IOFindBSDRoot真实入口，不是找到或挂载根设备 |

固定原DarwinBoot加载冻结内核；每轮入口前10个segment实际内存文件字节逐段哈希匹配，再执行原生入口、MMU、平台/CPU/时钟路径。调试器只写测试fixture自有gate进行放行，不修改内核指令；硬件断点读取真实调用/返回和寄存器。

QEMU明确使用virt,gic-version=3、cortex-a57、512MiB，并在每轮dumpdtb。物理timer specifier(1,14,4)对应INTID30；虚拟(1,11,4)对应27。基址、RAM和62500000Hz仅属于该模拟器，不能代入手机PPI18/19.2MHz。kt_fixed_zones=200仅是显式模拟器预算，保留原内核检查。

独立证据核验重新读取冻结源码、辅助产物、887记录和原日志；核对真实LR/返回值、同轮资源/频率、IRQ caller返回/计数、pthread/default crypto，并确认最终内核不含上游_armcpu_registered。见native-cpu-verification.json。证据复核不会扩大执行范围。

## 手机下一步

手机既有SEC/DXE、GOP、完整菜单/实体三键、有界TimerArch等历史结果保留。此轮只有只读Android/root/串口配置核查，没有重启或分区写入。

下一步建立实际DarwinBoot连续窗口的分配/保留合同并执行有日志的手机内核交接；自有UEFI allocator仍仅16MiB，原loader最小窗口256MiB。保持Mach-O低21位偏移，不能缩减loader窗口或把恢复写实测冒认为allocator所有权。随后在手机验证CPU/GIC/PPI18、物理timer和存储。当前不再扩展外围RAM诊断。


## 2026-10-29：手机分配路径已接通

后续7265f56已在手机通过258MiB隔离窗口和256MiB真实AllocateAddress生命周期；这不改变本页XNU执行只发生在QEMU的范围。原生内核尚未放进手机有效装载路径，下一步载荷/staging与原DarwinBoot；见[KERNEL-WINDOW-UEFI.zh-CN.md](KERNEL-WINDOW-UEFI.zh-CN.md)。


## 2026-10-29：自有UEFI路径已接通

后续bd61c3a已让自有SEC/DXE与原Mu allocator实际加载相同有效内核。最终独立run193742Z分别到物理timer IRQ/EOI=3/3及IOFindBSDRoot入口；不再由AAVMF提供UEFI服务。来源/输入和精确边界见[NATIVE-SEC-DXE.zh-CN.md](NATIVE-SEC-DXE.zh-CN.md)。手机仅验证PSCI查询与独立恢复，尚无手机XNU执行。


2026-10-29。手机011328Z的stage12通过：原XNU arm_vm_init完成并换TTBR1/置空原TTBR0，在PE_consistent_debug_inherit首指令捕获后完整恢复3段/原代码/初始表和输入ADT。66页活动表、644页高数据映射及132936字节delta通过；80.337秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。405份Git/blob/冻结输入与原始回传独立复核，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。尚无正常XNU IRQ/timer生命周期、根卷或用户态。下一步推进pmap后的平台初始化与持续日志。未同步上游、未写分区、原备份未改动；当前正常Android且无运行中的手机实验，RAM alias仍暂停。
