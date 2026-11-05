# 原生 XNU 开发输入与编译边界

2026-11-01 规范整改：活动源码已按设备package/SoC kits归属迁移，13区移植记录与构建回归通过；最新实机停点未变。见[整改说明](../UniXNU-raphael/docs/REPOSITORY-COMPLIANCE.zh-CN.md)和[最新交接](HANDOFF-20261101.zh-CN.md)。下文历史记录保留当时状态。

2026-10-29更新：手机已在原DarwinEnter后执行有插桩的5条原始XNU入口指令，并回传精确PC/ESR/args，恢复Android和原内核段CRC通过。381项独立复核见[NATIVE-ENTRY.zh-CN.md](NATIVE-ENTRY.zh-CN.md)。尚未到arm_init或手机XNU平台初始化；以下“手机未执行”属于该项完成前的历史状态。

当前更新（2026-10-29）：真实DT平台已configure成功，独立RaphaelBootCpu和源码pthread已接入；QEMU执行到bsd_init与IOFindBSDRoot入口，物理timer同轮6次真实时钟处理和6次EOI/返回通过。最终内核96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722，887记录、未定义0。源码/构建/失败/执行范围见[NATIVE-CPU.zh-CN.md](NATIVE-CPU.zh-CN.md)。手机XNU仍未执行；下文“驱动关闭/缺平台”属于各历史版本，不能当作当前状态。

2026-10-28。固定通用 UniXNU 的 ipados-17.7.11-21H461 配置提供原生 XNU xnu-10063.141.1/d8b80295118ef25ac3a784134bcf95cd8e88109f 与 Darwin23.6 ABI 开发基线。这是开发版本选择，不是本机已具备该 OS 或驱动 ABI 的证明。

新 board.toml/soc.toml 从配置接口独立编写，没有采用现成 raphael 包，没有引入其他手机板级地址。RAM/保留区/启动显示等仍以本次观测及分段实测为准。observed DTS 仅供检查，不是 OS 完整树；未给 XNU 或 DarwinBoot 授予任何新 RAM。

当前 raphael_bootstrap_defconfig 用于实际编译记录，明确禁用未经审核的 generic 平台/CPU/存储/显示驱动。选取未修改的通用架构补丁及本机明确列出的 OS 补丁；BCM2837 在构建脚本中仅是固定上游携带4KiB页的机器编译配置，不是本机身份或板级配置来源。此目标不执行预链接/不下载完整 IPSW/不打包手机启动镜像。原生编译、链接、预链接、手机执行必须分开记录。

工具链 20261028T045143Z 实测通过 XNU 三个专用 builtin、ARM64 Mach-O 编译/重定位链接/归档、MIG生成、host ELF 编译及 LZFSE 往返。IIG仅确认可执行文件存在；完整内核待实际构建。见 native-toolchain-host.json。

20261028T060402Z 首次真实构建在补丁准备失败，compile_records=0：固定 OS 的 zzz-boot-progress.patch 要求 bsd_init.c 已有 XNU_SHENG_PMGR/sheng_pmgr_run 条件块，而本机没有也未引入其他板平台代码。保存原失败；本机 os-bootstrap.series 仅选择原 OS series 中两项通用 XnuPrelink 版本补丁，明确省略已禁用的 boot-progress 补丁。ARM64、SoC 与设备 series 仍按原顺序。通用 UniXNU、XNU 原始仓库均未修改。

依赖网络曾三次 Git/归档传输中断；corecrypto 固定 11fba65b12d8830630e248dfa8344caf8b065f26 使用 Git 稀疏工作树仅检出根文件。本次关闭 source-corecrypto，编译脚本不消费其实现文件；这不是完整 corecrypto 源码获取或加密实现验证。unixnu.lock 记录所有 Git 引用；本地原始 XNU/Mu 固定版本另列。


## 主机原生编译与结构检查成功（2026-10-28）

固定Apple头文件按Git blob SHA1验证缓存；LLVM 58c46bae21181fb4240cf964461bea738d96d50e和Libc 899a3b2d52d95d75e05fb286a5e64975ec3de757按Git固定提交以cone sparse checkout获取，分别检出57/135个文件。HTTP runtime fallback未用于成功构建；网络失败与中断attempt保留。旧进程在切换依赖策略时被误停止，064440Z的794份当时记录和日志已保留，核对源码后增量构建完成。

065702Z真实原生构建通过：887份对象编译记录，ARM64 MH_EXECUTE，18,104,064字节；SHA256 a96f212f376e0c581294839ab8726e22e8c7847cf896fd98f495e828f6842678。命令为`python3 scripts/build_native_bootstrap.py`，实际后端为固定通用`unixnu.kernel.build`；未调用prelink。

`python3 scripts/inspect_native_kernel.py --build-report artifacts/native-bootstrap-attempt/20261028T065702Z/report.json`独立检查header、25条load command、segment/section范围与4KiB对齐、虚拟segment不重叠、thread入口位于可执行段以及符号/字符串表；未定义符号0。系统llvm-objdump/llvm-nm交叉检查通过。070142Z检查目录冻结内核、原构建报告、887份编译记录和构建日志；native-kernel-structure.json为索引。

这些地址是Mach-O虚拟地址，不能当手机物理加载地址。bootstrap关闭ARMCPU/DT平台等驱动，未实现SM8150 XNU平台初始化；没有prelink、没有打包手机内核镜像、没有在手机执行。本次主机成功不授予手机启动资格或新RAM。


## 原样原生XNU的QEMU早期执行（2026-10-28）

新增NativeXnuFixture与run_native_xnu_qemu.py，QEMU/AAVMF独立512MiB RAM、无手机地址或外设，固定原DarwinBoot经UniXNUBootEntry加载本次真实原生内核。独立UEFI页仅用于ExitBootServices通知与调试器放行，不修改内核字节；硬件断点观察真实PC与寄存器。最小模拟器ADT不是手机完整设备树。缺少gdb-multiarch，已通过Ubuntu包管理器补充15.1；版本与可执行文件哈希写入后续报告。

首次072853.788620Z-rda3p6hm成功到达原生入口0x48414488，x0=0x49218000、EL1、M/C/I关闭，实际执行第一条内核分支后到0x4841605c；随后到达高虚拟地址_arm_init=0xfffffff0079cea88，M/C/I已开启。内核SHA256仍为a96f212f376e0c581294839ab8726e22e8c7847cf896fd98f495e828f6842678。Exit通知恰好一次，ESP文件哈希不变。native-xnu-qemu.json保留首次记录。

下一版观察器增加所有已加载segment文件字节逐段哈希，以及可选PE_init_platform/kernel_bootstrap断点，进一步避免仅凭文件或首个断点推断完整加载。尚无平台初始化完成、完整内核启动、手机XNU或用户态结论。


## 已到达kernel_bootstrap（2026-10-28）

075308.459189Z-cf2rrfds运行通过：所有10个实际加载segment的文件内容在第一条内核指令执行前由GDB逐段读回并核对SHA256；完整原始Mach-O未修改。记录真实入口、MMU/缓存开启后的arm_init、PE_init_platform与kernel_bootstrap断点，Exit通知恰好一次、ESP哈希不变。QEMU当轮MRS核对CNTFRQ=62500000、启动CPU affinity0，与ADT值一致。

初版最小ADT的空arm-io缺少原XNU直接消费的device_type/ranges；修为本轮QEMU dumpdtb推导的I/O窗口及正确u32 CPU reg后，内核继续运行并明确panic缺少chosen/dram-base。再从同份生成FDT读取实际DRAM bank，补齐dram-base/dram-size，内核到达kernel_bootstrap；没有修改内核或跳过检查。073558/073952/074939各失败产物与日志仍保留。此为模拟器输入修正，不是手机硬件参数或SM8150平台完成。

命令：`python3 scripts/run_native_xnu_qemu.py --stop-at kernel_bootstrap`。最终native-xnu-qemu-kernel_bootstrap.json与带run时间的不可变报告保存各层哈希；完整内核启动、IOKit平台和手机执行均仍未验证。


## 原生构建产物立即冻结

082939Z增量调用真实后端再次成功，887份记录、内核SHA256与065702Z一致。build_native_bootstrap.py现在在发布成功前将内核和全部对象编译记录复制进不可变attempt目录，并冻结日志与runner；报告不再把可变build tree当作唯一内核来源。inspect_native_kernel.py兼容旧报告，并核对新增冻结记录；083016Z结构检查通过、未定义符号0。没有改变内核或板级驱动选择。


## 更深启动诊断与已定位缺项

083638Z/083953Z/084433Z的bsd_init目标均失败，但逐段哈希与原生入口成功，实际到machine_startup/kernel_bootstrap。独立硬件断点捕获Apple TUNABLE的kt_fixed_zones=260、29个size class及策略入参/返回数组；48字节类分得16个signature池和17个type池，触发保留共享槽后总数必须<=32的原断言。调试器仅观察，未修改内核或关闭断言。

084657.513468Z-262x1tbe显式使用`--kalloc-zones 200`，这是模拟器诊断预算，经同轮断点核对实际值200；所有类均<=31池，保留原检查，进一步到kernel_bootstrap_thread和PE_init_iokit。随后Kernel data abort，PC定位crypto_random_kmem_ctx_size+0xc、LR为kmem_crypto_init+0x20。当前prelinked模式没有提供并初始化crypto函数表，这是下一处真实依赖缺口；未到bsd_init，不当作完整内核启动。内核文件哈希始终未变。

观察器修正通用panic解码：按真实格式记录栈参数/可读字符串和帧链，避免把普通assert参数误解成异常保存状态。旧失败记录保留各自observer快照；其启发式panic_saved_state字段不作为可靠事实。


## 源码 crypto provider：主机与 QEMU 默认 POST（2026-10-28）

独立 `raphael_sourcecrypto_defconfig` 显式启用固定上游的 source provider，`build_native_bootstrap.py --source-crypto` 选择此配置；无参数仍明确选择原 bootstrap。两个 archive 由固定 UniXNU 的通用脚本构建，没有修改通用实现、屏蔽自检或供应空回调。

原上游指定 ONLYA/corecrypto-2023 快照 `11fba65b12d8830630e248dfa8344caf8b065f26`。全仓/整包获取超时后，fetch_native_crypto.py 从固定 Xcode kernel target 解析 529 份 C，递归获取真实 quoted include，保留 FIPS 头和 KAT，最终 809 文件逐项核对 Git blob SHA1 与 SHA256。093354Z 获取成功；这是第三方快照一致性，未与 Apple 原始 archive 认证，不构成密码模块资质或整仓完整性结论。源码与二进制仅存 ignored artifacts；未上传或提交依赖源码。

092211Z 缺两个 FIPS 头、093205Z 缺 ECDSA KAT 的失败均保留，补齐后 093403Z 构建成功：两个 archive 各 529 份 C，namespaced archive 缺少 kernel external 与重复 global 均为 0；内核 887 份对象记录，18,421,664 字节，SHA256 `e5f1db32113f1e41f6cb252fc08e5e914001da45f0c1c74703018a813d8134aa`。原上游 seal 脚本写入完整性 HMAC。093738Z 独立 Mach-O 检查通过、未定义符号 0；内核、记录、archive、编译/链接调查和日志立即冻结。未执行 prelink 或手机打包。

`python3 scripts/run_native_xnu_qemu.py --stop-at bsd_init --kalloc-zones 200` 的最终独立运行 `094943.352011Z-vyn8innj`：10 个加载 segment 的文件字节在入口前读回哈希一致，真实执行到 kernel_bootstrap_thread、PE_init_iokit；硬件断点观察默认 `fipspost_post` mode=0 返回 0、corecrypto_kext_start 返回 0，随后 source_corecrypto14_status=0、crypto_init=1、函数表非零。未使用 fips_mode 跳检参数，未修改内核字节。早期采样 status=5 是初始化前/返回调用点尚未更新全局值，最终状态另行保存，不能将早期采样误判为 provider 失败。

默认 POST 与注册这项验证通过；**bsd_init 目标仍失败**，明确 panic `Unable to find driver for this platform`（IOPlatformExpert.cpp:2352），与当前禁用 DT 平台/CPU 驱动吻合。显式 kt_fixed_zones=200 仅是模拟器资源预算，不能代入手机。没有完整 OS、平台驱动、ABI 全面兼容或手机 XNU 启动结论。

可重跑的独立证据核验：`python3 scripts/validate_native_crypto_evidence.py`，交叉检查 809 源文件、冻结构建输入/887 记录/辅助产物、加载段和真实 POST/注册状态；见 native-crypto-source.json、native-crypto-verification.json 和不可变 native-xnu-qemu-20261028T094943.352011Z.json。


## 后续平台依赖源码核查（2026-10-28）

固定UniXNU 0fc0fc1的ArmDTPlatform从ADT发布CPU和arm-io nub，要求/cpus、/arm-io、/defaults、/options及chosen的CHRP NVRAM proxy；不能只打开编译选项而跳过这些真实输入。其通用实现不含板级MMIO地址，可作为后续接口参考。当前最小QEMU ADT尚不满足这些完整输入，平台driver仍关闭。

同版本ArmCpu.cpp的kSgiPpiEnable固定包含PPI27，另有SGI及1008起的诊断SPI策略；不能将这些策略直接用于本机。本机本轮有界UEFI验证的实际物理timer目标为PPI18，拥有独立来源和实机IRQ/EOI结果。故继续关闭CONFIG_XNU_ARMCPU，后续独立实现/配置SM8150的CPU、GIC与timer接口；不复制该驱动的板级假设，未在手机执行它。此为源码调查，不是新增平台或XNU启动成功。


## 手机原生bootstrap MMU实测

2026-10-29。手机234327Z已实测原XNU建立bootstrap页表、设置翻译寄存器、开启MMU并到达高VA arm_init首指令检查点。72Q记录和完整64KiB页表通过，4表页/258非零描述符/128组block；全部临时代码、页表与UEFI状态恢复，原10段CRC/零尾/args/ADT重验通过。80.516秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。389项Git输入及原始证据独立复核，详见[NATIVE-MMU.zh-CN.md](NATIVE-MMU.zh-CN.md)。arm_init C函数体、XNU平台/GIC/timer、根卷与用户态仍未执行。下一步建立C初始化阶段的可恢复日志，推进平台初始化。未同步上游，RAM alias暂停，原备份未改动；当前手机正常Android，无运行中的实验。


## 后续C初始化观测（仅QEMU）

235049Z复用最终MMU Image，在模拟器已加载内存恢复arm_init首指令，原C执行过PE_init_platform(FALSE)并到rtclock_early_init及arm_vm_init入口。10段×5处原始快照和独立逐字节复核235353Z通过，页表未变，3个数据/栈段出现真实写入。手机仍只验证到arm_init首指令；下一步需实现这些段的有界备份/恢复和更深检查点。细节及局限见[NATIVE-EARLY-C.zh-CN.md](NATIVE-EARLY-C.zh-CN.md)。


## 手机arm_init C初始化前缀与原字恢复（2026-10-29）

2026-10-29。手机001904Z已执行原arm_init C初始化并到达arm_vm_init首指令，原平台首次初始化/拓扑/当前线程和早期时钟/启动子系统前缀已通过该检查点。2,637,824字节三个数据/栈段完整备份恢复；130,896字节/10,908个变化64位字独立重建，原10段CRC/零尾/args/ADT及UEFI状态恢复通过。80.434秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。396项Git输入与原始证据独立复核，详见[NATIVE-EARLY-RECOVERY.zh-CN.md](NATIVE-EARLY-RECOVERY.zh-CN.md)。arm_vm_init函数体、pmap重建、正常XNU IRQ/timer生命周期、根卷和用户态尚未验证。下一步处理pmap切换后的日志与恢复；原TTBR0将被置为空表，现有物理别名relay不能直接沿用。当前手机正常Android，无运行中的实验；未同步上游、写分区或改原备份，RAM alias暂停。


2026-10-29补充：QEMU原arm_vm_init已真实换TTBR1/置空TTBR0并返回，66页活动页表、644页高地址数据映射及7处完整快照经396份冻结输入独立复核。手机仍仅到arm_vm_init入口。下一步独立TTBR0转换表恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)；未同步上游。


2026-10-29：stage12换表后恢复已实现，QEMU正向36项及同镜像独立5场景通过；旧stage11回归31项通过。手机仍以001904Z的arm_vm_init首指令为准，stage12尚待最终冻结构建、旧分支回归和本机布局预检。原始TTBR与诊断转换根分开，输入ADT的random-seed清零由独立备份恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。上游未同步、RAM alias暂停、原备份未改动。


2026-10-29。手机011328Z的stage12通过：原XNU arm_vm_init完成并换TTBR1/置空原TTBR0，在PE_consistent_debug_inherit首指令捕获后完整恢复3段/原代码/初始表和输入ADT。66页活动表、644页高数据映射及132936字节delta通过；80.337秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。405份Git/blob/冻结输入与原始回传独立复核，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。尚无正常XNU IRQ/timer生命周期、根卷或用户态。下一步推进pmap后的平台初始化与持续日志。未同步上游、未写分区、原备份未改动；当前正常Android且无运行中的手机实验，RAM alias仍暂停。

## 2026-11-05：704MiB显式内存合同主机实现

163051Z原日志已有vm-pageshortage及多个服务被jetsam回收。新增显式704MiB选项，SEC授予、实际DarwinBoot分配、BootArgs期望、接收器、精确恢复映射和检查器保持一致；352个2MiB块，仍限定一个L1跨度，保留原保护区与真实分配检查。原DarwinBoot已允许该对齐容量，无需修改加载器。实际C映射与独立Python解码在256/512/704MiB逐字节一致，3项越界/不支持容量拒绝及ASan/UBSan通过，ADT只有memory-size变化。新载荷已生成；旧Payload extent身份不匹配被拒，704QEMU与手机尚未通过。当前手机仍是冻结512MiB的CommCenter重点采样。证据：artifacts/memory704-contract/20261104T165535Z/host-report.json。
