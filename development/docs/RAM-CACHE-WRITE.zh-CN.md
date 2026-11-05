# 带缓存维护的可恢复 RAM 诊断

2026-10-28。目标是降低原 MMU/cache 关闭的首 MiB 测试耗时（实机约 3155.935 ms），先测小范围性能，再决定后续范围。独立 `PcdRaphaelRamCacheWritePages` 默认 0，仅允许阶段2/3；不与旧 uncached 写入、DXE、管理器或其他硬件实验混合。不新增 RAM HOB，分配器仍限 16 MiB 诊断 arena。

候选地址、95项排除策略及四项现场入口保护来自本次采集和同轮 FDT，见 KERNEL-MEMORY、RAM-READ、RAM-MAPPED。阶段2只验证现场保护和原256点读取，记录 armed，不修改候选内存或声称缓存实验成功。阶段3先重新验证 WB/RO 恒等映射、256次读取摘要、读转换/写拒绝及 PAR 保存，再仅清除 EFI_MEMORY_RO 位；重新256点查询 read/write 恒等 PA、WB 属性和 PAR 恢复，之后才允许存储。

恢复算法复用未修改的 RamWrite.c：4096字节完整原页备份、两轮与地址相关的图案、全部原字写回和逐字比较，8秒运行预算不变。每页备份前 clean+invalidate 一次，每轮图案与原字恢复的末字之后各一次，合计每页1次 pre和3次 post。固定 Basecore cfb93724a06ff86ff5ba971413368a7809ee42a5 的 ArmMmuLib.h/ArmMmuLibCore.c 是权限更新来源；ArmCacheMaintenanceLib.c 和 AArch64Support.S 的 WriteBackInvalidateDataCacheRange、逐行 DC CIVAC、DSB SY 是缓存维护来源。cache line长度从CPU读取，不复制其他板参数。

正常和异常 SecFinish 都先恢复 Dirty 页，再恢复只读映射并重新256点核对写权限拒绝。若恢复失败，保留 Dirty 与原备份并停止，不返回 Android。独立缓存状态176字节、原engine和原页备份、恢复状态均核对为镜像真实.data存储，避免SEC的BSS未初始化。独立312字节wire由16项缓存元数据及原23项engine记录组成。

主机 `validate_ram_cache.py` 的44项实际C/ASan/UBSan测试采用独立DRAM/cache/valid/dirty模型和初始stale cache，覆盖read/write/Sync/translation失败、持续PoC失败保留原备份。另18项wire反例通过。主机wire解码测试明确人工补充map_restored/restore_denials两字段，仅测试解码，不能当作硬件权限恢复证据。原门禁73项、mapped74项和旧engine43项回归通过。

真实QEMU使用自己的生成FDT/1GiB RAM推导地址。阶段2 `20261028T112006.734512Z-3wvkjzow` 正常47项；阶段3 `20261028T111211.572593Z-0qls4s0i` 正常53项、写第257次checkpoint UDF恢复55项、mapped load UDF在所有缓存存储之前退出49项。独立MMU/cache关闭的receiver核对所有原DRAM字。UDF是精确指令故障注入，不是真实data abort。`audit_ram_cache.py` 核对相同源码/上游输入、六份固定Git blob、实际STR、DC CIVAC、范围遍历与DSB，以及清RO/恢复RO调用。按完整链接函数范围审计，不能在首个RET处截断成功分支。

默认关闭的完整DXE回归 `20261028T112239.308053Z-h6bi6ip5` 正常47项、BRK44项、unmapped UDF44项通过。

```sh
python3 scripts/validate_ram_cache.py
python3 scripts/run_ram_cache_qemu.py --stage 2 --pages 1
python3 scripts/run_ram_cache_qemu.py --stage 3 --pages 1
python3 scripts/audit_ram_cache.py --stage2 <stage2-report> --stage3 <stage3-report>
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --ram-cache-write-pages 1
python3 scripts/record_ram_cache.py bind --build <private-build>
python3 scripts/run_sec_dxe.py --serial <runtime-serial> --build <private-build> --historical-binding <source-binding>
python3 scripts/reboot_after_probe.py --serial <runtime-serial>
```

当前缓存路径仅主机编译、结构/机器码与模拟器通过；手机尚待单页两阶段临时启动，随后按实测性能扩大。新记录器独立重核Git/快照、原wire/FDT/log、不可变handoff/attempt和正常重启清理；不会把旧mapped报告当缓存写入证据。没有flash/erase/format或修改原备份。

每页恢复与图案测试不证明跨页别名、隐藏DMA所有权、256MiB连续分配合同或手机有效内核交接；这些仍为未知项。


## 缓存单页手机实测：20261028T112932Z / 20261028T113233Z

来源绑定25730912c8a429c9b8c5cd91157ccdb990c7f8f1，两阶段149项板级/上游输入逐Git blob及构建快照一致，另22项验证脚本绑定。stage3在WB和MCI开启下，对0xc0000000第一页4096字节完成两轮图案和原内容恢复，差异均0、Dirty/BackupWords0；pre/post同步1/3，恢复RO并重新256点验证写拒绝。3432ticks/19.2MHz=0.17875ms。boot SHA256 5b59cc000edfa1f5be40ab059d3e19d0adcdf6841bdfabab103ceeab346e5c85，FD 699d28b50f557e85a34546dc2562e4c6e26b5fda3a401f14dcfe6eb217e90ecd。

113122Z及113426Z正常重启清理通过，Android/root/原boot哈希正常，临时属性消失。独立原wire/FDT/log/不可变handoff与attempt复核见boot-ram-cache-observation-pages1.json。不能由单页时延外推整窗口通过或分配权限，下一步前MiB实测。

较大页数首次QEMU构建20261028T112955.790972Z-8ubi7fy_因逻辑OR右侧非布尔常量触发-Werror失败。已保留edk2-build.log与源码快照；恢复开关改为两个无副作用固定PCD的按位OR，任一非零语义不变。修复后256页stage2 113300.772285Z-106bzhpj正常47项、stage3 113415.076733Z-rmqoeqxq正常53/部分写异常55/读取异常49通过，机器码审计通过。单页历史绑定继续指向原2573091，未替换为新源码假装重测。

修复后默认关闭完整DXE回归113541.541837Z-ajk6awr6正常47/BRK44/unmapped UDF44通过。


## 缓存首 MiB 手机实测：20261028T113820Z / 20261028T114127Z

两阶段来源绑定21483399fb35a703370b469b8089b11ea28a8296、149项固件输入和22项验证脚本。0xc0000000起连续256页/1048576字节，图案262144字与原字恢复131072字均零差异，完成/恢复256页，Dirty/BackupWords0，摘要相等。pre/post同步256/768，read/write转换与PAR保存256，恢复RO写拒绝256。830737ticks/19.2MHz=43.2675520833ms，非全窗口性能保证。

114012Z及114346Z正常重启清理、Android/root/原boot哈希通过，临时属性消失。boot SHA256 78d742ded6af740b4e161f5a772d1ef803d47984f74fae2295ef3409f26107f2；FD a3e12eca3d3c6fefd978cff9b9386d09731fe6bb09ae379e5b4f3c5ab1ec2be7。独立原wire/FDT/log/不可变attempt及handoff复核见boot-ram-cache-observation-pages256.json。未扩分配器，跨页别名与隐藏DMA生命周期仍未知；尚无手机有效内核交接。


## 缓存前16 MiB手机实测：20261028T114523Z / 20261028T115003Z

绑定21483399fb35a703370b469b8089b11ea28a8296，149项固件输入/22项验证脚本独立核对。0xc0000000起连续4096页/16777216字节，图案4194304字和原字恢复2097152字全部零差异，完成/恢复4096，Dirty/BackupWords0，摘要相等；pre/post同步4096/12288，RW转换/PAR与恢复RO写拒绝均256。13263027ticks/19.2MHz=690.78265625ms。boot SHA256 92a8824b7721361a5395904ce96216e25d30f078f01a912c9b5a314d32931221，FD df78d859905b87551a771c6396b2ec4a779c86a8e171762b0a0dc1dde8ff272e。

114732Z及115212Z正常重启清理、Android/root/原boot哈希通过，临时属性消失。原wire/FDT/log、不可变handoff/attempt和cleanup独立复核见boot-ram-cache-observation-pages4096.json。这里的16MiB是candidate测试范围，不是把该范围注册为原16MiB诊断arena；分配器仍未扩展。跨页别名/隐藏DMA所有权与手机有效内核交接仍未知。

主机入口新增16384页/64MiB选择，固件算法与8秒预算未变。QEMU 115038.083358Z-vicgaooz阶段2正常47项；115202.479370Z-i0zw6b6e阶段3正常53/部分写UDF恢复55/mapped load UDF49，实际机器码及固定来源审计通过。手机64MiB待两阶段验证，不能根据16MiB结果宣称其已通过。


## 缓存前64 MiB手机实测：20261028T115603Z / 20261028T120013Z

两阶段149项固件输入/22项验证脚本绑定56ba1116b452f957753f020e4b5e5dce4b41be3d。0xc0000000起连续16384页/67108864字节，图案16777216字、原字恢复8388608字均零差异，完成/恢复16384，Dirty/BackupWords0，摘要一致；pre/post同步16384/49152，RW转换/PAR保存与恢复RO写拒绝均256。53150038ticks/19.2MHz=2768.2311458333ms，未延长8秒预算。

115818Z及120318Z正常重启清理、Android/root/原boot哈希通过，全部临时属性消失。boot SHA256 6beae0568c97001da490dba7dcfce0c6fcf6d8b0ab6aaab2cb4ad4480f3ebb79；FD 88ad3e60b6346362fd457a1bb7e79cd30e496a6f59c073966feacf6efb67a59f。原wire/FDT/log、不可变handoff/attempt与cleanup独立复核见boot-ram-cache-observation-pages16384.json。

新增validate_ram_cache_evidence.py可重跑复核4KiB/1MiB/16MiB/64MiB全部历史Git/源码快照/镜像、原wire/FDT/log及正常重启原记录。独立读取cleanup的原baseline FDT确认无raphael诊断属性，核对两次boot哈希、正常reboot、boot_completed及root原命令输出。其恢复结论来自重新解码固件的原字恢复记录，不声称在Android中重新读完整候选DRAM。

完整256MiB测试、跨页别名、隐藏DMA生命周期与分配合同仍未完成；按本轮时延线性估计整256MiB将超过8秒，因此没有直接执行65536页手机配置。分配器仍只有原16MiB arena，手机有效DarwinBoot/XNU交接仍未执行。下一步应在相同8秒预算内审计并改进缓存路径，独立验证跨页别名和分配合同；不能靠放宽预算或直接登记未核实RAM绕过门槛。


## 页面边界屏障实现，尚待新版本手机验证

本轮优化只修改缓存适配回调：普通 WB RAM 的 volatile 64 位 load/store 两侧保留 compiler memory fence；完成屏障移至 SyncCachePage，在 DC CIVAC 范围维护前、后均 DSB SY。固定 Basecore 的 walker 本身另有结尾 DSB SY。备份前、两轮图案后、原字恢复后的 1+3 次维护不变，旧 uncached 回调和 RamWrite.c 未修改。部分存储异常仍经同一恢复函数覆盖整页，在同步完成后逐字比较，最后恢复 RO；原备份与 Dirty 的保留规则不变。

这是基于一手实现的设计推导，尚非新版本实机事实。固定 MiCode 663db50 的 Documentation/memory-barriers.txt 243-260 行说明同 PE 重叠访问的顺序；arch/arm64/mm/cache.S 165-168、269-272 行与 include/asm/assembler.h 388-413 行使用范围 DC CIVAC 后的 DSB。没有将 compiler fence 当 CPU 屏障，也不推断与其他 CPU/隐藏 DMA 的同步或内存所有权。源码均按 Git blob 和 SHA256 记录于本轮 source audit，通用源码没有修改；未取得正文的 Arm 在线文档不作为证据。

缓存专用机器码审计检查完整函数 contribution、单个 LDR/STR、checkpoint 和页面同步前后 DSB/逐缓存行 CIVAC；旧 uncached 审计保持原规则，历史缓存镜像仍按旧双 DSB store 规则重新核对。手机测试前须完成主机模型、QEMU 正常/部分写异常/只读 load 异常、默认关闭完整 DXE 回归，随后先单页实机再扩大。


页面边界版主机44项C/ASan/UBSan及18项wire通过；旧入口73、mapped74、engine43回归通过。单页QEMU阶段2 122246.586860Z-jdazkttt正常47项；阶段3 122335.772941Z-rqgtkc7y正常53、部分写UDF恢复55、mapped load UDF49。独立MMU/cache关闭receiver核对原DRAM，机器码审计通过。审计首次严格匹配未接受LLVM对mov返回值的合法调度和反汇编注释，已按实际四条完整指令修正，未放宽内存访问规则。默认关闭完整DXE 122544.797488Z-i402h3vn正常47/BRK44/unmapped UDF44均通过。历史64MiB镜像的cache/store报告在新审计器下仍逐字段一致。


## 页面边界版单页实机，完整窗口QEMU仍失败

bec9798的两阶段20261028T123018Z/20261028T123517Z单页手机测试成功，实际stage3运行时间以boot-ram-cache-observation-pages1.json的不可变记录为准：0.1115625ms，两轮图案/全部原字恢复零差异、Dirty/BackupWords0，PoC同步1/3、RO恢复256点通过；123622Z正常重启清理、Android/root/原boot哈希通过。前64MiB历史事实仍属于旧版本，尚未以新版本扩测。

完整256MiB的QEMU 123212.707989Z-rj0mf832与123535.809285Z-7sfvk8jg均触发不变的8秒预算，分别完成/恢复65449、60118页；没有残留Dirty/Backup，独立MMU关闭receiver核对原DRAM、RO恢复256点均通过，但整体测试明确失败。原日志/源码快照及两份ram-cache-qemu-timeout报告保留；不能把恢复成功当作整窗口通过，主机并发影响未知。下一步减少逐缓存行的函数间调用开销，仍保持同样CIVAC和完成屏障。


## 模拟器时钟与手机时延分开验证

未提交的直接CIVAC循环实验124123.432439Z-sod3fy3q完成/恢复64961页后同样超时；仅有编译及失败运行，未完成source audit、未上机，源码已撤回到单页实机通过的Basecore路径。失败源码快照和日志哈希保留，不能当作成功实现。

尝试显式--instruction-clock，在隔离1GiB QEMU中使用-icount shift=0,align=off,sleep=off。QEMU 8.2.2官方invocation文档哈希见ram-cache-qemu-clock.json：每条指令推进1ns虚拟时间，不是cycle accurate性能模型。124700.232063Z-e5yzfzm7仍在8秒虚拟预算内超时，完成42092/恢复42093页、Dirty/Backup0、RO恢复256点和独立receiver通过，但全窗口明确失败。此试验没有采纳，两个runner源码已撤回；临时harness、日志和元数据保留。默认模式、固件8秒预算及手机计时没有放宽，不把虚拟时钟作为门禁绕行或手机性能依据。后续优先测本机新版实际吞吐，并设计进一步的实现优化与功能证明。


新版首MiB的默认时钟QEMU阶段2 125056.803559Z-kblntr3s正常47项；阶段3 125234.045603Z-fqpdua3w正常53、部分写UDF恢复55、mapped load异常49及实际机器码审计通过。此为手机扩大至首MiB的准备，不是手机结果。


## 页面边界版首MiB手机实测：20261028T125630Z / 20261028T130021Z

两阶段149项固件输入及22项验证脚本绑定06654aa4907a9193a6b4b0a29c69af48531e840b。0xc0000000起连续256页/1048576字节，完成/恢复各256，两轮图案262144字、原字恢复131072字均零差异，Dirty/BackupWords0、摘要相等；pre/post同步256/768、RW/PAR及恢复RO写拒绝256。实际耗时27.4865625ms；对照旧版43.267552ms减少约36.5%，不外推完整256MiB通过。

20261028T130128Z正常重启清理、Android/root/原boot哈希通过，诊断属性消失。boot SHA256 0629947b1603cb7e6000f070d831e43461b411b7d120d7709cd42e407ffd6f00；FD b2540a1db88f4cc03c2c8ac165152f58e03239a677b345c8f4c2cd9fad337081。完整原wire/FDT/log/不可变attempt与handoff独立核验见boot-ram-cache-observation-pages256.json。未扩分配器、未flash/erase/format、未改原备份。新版64MiB的QEMU阶段2 125631.629511Z-c7qe108p正常47项，阶段3 125736.283359Z-tol8aclq正常53/部分写UDF55/读取异常49及机器码审计通过，尚待新版手机64MiB实测。


## 页面边界版前64MiB手机实测：20261028T130412Z / 20261028T130930Z

两阶段149项固件输入和22项验证脚本绑定e39d25104434edf602d1b54a7dc73a14a07fb8a0（缓存实现为bec9798，通用源码与旧恢复引擎未修改）。0xc0000000起连续16384页/67108864字节，完成/恢复16384，两轮图案16777216字和原字恢复8388608字均零差异，Dirty/BackupWords0、摘要一致；pre/post同步16384/49152，RW/PAR及恢复RO写拒绝256。实际33763913ticks/19.2MHz=1758.5371354166666ms，比旧版本2768.231146ms减少约36.5%。只是此范围实测，不是完整256MiB或分配许可。

20261028T131038Z正常重启清理、Android/root/原boot哈希通过，临时诊断属性消失，当前没有进行中的实验。boot SHA256 a7d2218e29996123f07449affb7bcddf5674f30f0a5742f27d46ed9e1f4e99cc；FD 5000a3b01b07bd0cf9baef136e551425f8b0179ca56fef42a87707653edd93ad。原wire/FDT/log/不可变attempt与handoff及cleanup核验见boot-ram-cache-observation-pages16384.json。分配器仍只有原16MiB诊断arena，未flash/erase/format、未改动原备份。

新增validate_ram_cache_timeouts.py独立重解码四次全窗口QEMU失败的原wire、read/mapped门禁、超时阈值、恢复页数、Dirty/Backup及RO状态，核对596份归档源码文件与固定Git/独立直接循环快照，并检查MMU关闭receiver记录原DRAM完整恢复。ram-cache-qemu-timeout-verification.json只证明负向证据一致、8秒预算生效与恢复记录，不把任何失败当全窗口通过。直接循环及指令时钟均未采纳，当前源码只含已实机测至64MiB的Basecore页边界路径。

下一步需要解决完整256MiB的功能验证与有界运行、跨页别名和分配合同，再进入手机有效DarwinBoot/XNU交接。可评估减少通用engine逐字双层回调的开销，但这是待论证的实现方向，需要保留原备份/Dirty/PoC/RO恢复语义和实际C模型、异常注入及机器码证据；不是已实现或已验证的方案。不能根据本轮64MiB时延线性外推全窗口通过，也不将修改模拟器时间或简单放宽预算作为证明。


## 直接回调版本：完整窗口QEMU通过（2026-10-28）

保留原RamWrite.c、232字节恢复engine、176字节cache状态和312字节wire，增加显式RaphaelWriteRamWithCacheDirect入口。共享BeforeRead/AfterWrite规则内联到本机原始load/store回调，消除每字第二层间接调用；Counter/Sync仍接收原始caller context，紧急恢复仍使用cache context。页前PoC同步、两轮pattern及原字恢复后的同步、Dirty/完整备份与先数据后RO的顺序不变，未扩allocator或放宽8秒预算。

新UniXNU 40d21cc下，90项实际C/ASan/UBSan及18项wire检查通过，另12项编译期ABI断言将状态字段逐一对应机器码。单页QEMU阶段2正常47、阶段3正常53/部分写UDF恢复55/映射读取UDF返回49通过。完整65536页QEMU阶段2同样47项、阶段3同样53/55/49项通过；完整窗口的normal实际4987.654768ms，完成/恢复65536页、图案67108864字和原字恢复33554432字均零差异，Dirty/BackupWords0、摘要一致，恢复RO256点通过。独立MMU关闭receiver核对全窗口原DRAM字；不能将此模拟器地址或性能当手机参数。

严格链接审计检查完整34条read与31条write回调（包括首RET后的失败分支），唯一候选64位load/store、唯一Sync间接调用、257次写checkpoint与准确context/计数偏移。76项opcode/extent/checkpoint负向及历史schema兼容检查通过；旧boundary2审核归档独立文件。Basecore的实际CIVAC、页前后DSB、RW/RO与.data存储审核通过。旧read/mapped/write门禁73/74/43回归通过；默认关闭RAM诊断的完整DXE47/44/44使用完全相同的149项固件输入，无需重复构建。

准确证据：ram-cache-source-audit-pages1.json、ram-cache-source-audit-pages65536.json、ram-cache-native-audit-host.json、ram-cache-host.json。完整QEMU阶段2为20261028T140519.817674Z-ptikv25e，阶段3为20261028T140007.068845Z-brlqocnb；单页阶段2为20261028T140519.817701Z-de8aogqa、阶段3为20261028T140519.817674Z-cu8bi4fl。此版本尚未手机执行，历史手机前64MiB仍属于boundary2。下一步先单页手机两阶段，再逐级扩大；完整所有权/跨页别名/分配合同仍未知。


## 直接回调版完整256MiB手机实测通过（2026-10-28）

本轮4KiB/1MiB/64MiB/256MiB依次进行两阶段临时启动、原字/RO恢复、Android返回和正常重启清理，全部绑定d0a54cc50f47e6996b1a8b970f0032a8c94d71c4，UniXNU为40d21cc65171c3a24faa130a2a8e899f85790485；每份149项固件输入和22项验证脚本逐Git blob与归档快照核对。新阶段3分别为142732Z/143440Z/143848Z/144256Z，实测0.0990104167/23.778125/1521.8653125/6087.08453125ms；未更改8秒预算。

完整窗口为本机来源约束的0xc0000000..0xd0000000，连续65536页全部完成并恢复，图案67108864个64位字、原字恢复33554432字均零差异，Dirty/BackupWords0、摘要3761833498104544988相同；pre/post同步65536/196608次、RW/PAR和恢复RO写拒绝256点。两阶段build为20261028T142442Z/20261028T144222Z，手机run为144040Z/144256Z。阶段3boot SHA256 41cbf90784019284fb4863372ce21b0a22a1e2d56414ec2a8cf3ed4701f8fbbb，FD 2a77e1665d368f769e8fc7e12b09ca04cc086b80b956c5d9b28506813bf7f04d。

144408Z最终正常重启清理通过，Android/root/原boot哈希正常、临时属性消失；当前没有进行中的手机实验。validate_ram_cache_evidence.py的独立核验20261028T144645.527035Z-b5pgi14w重新读取全部5份范围索引及各不可变wire/FDT/log、Git/冻结镜像/源码、正常重启的原命令记录，最大范围268435456字节。原字恢复事实来自固件逐字比较回传，不冒充在Android中再次读取完整原DRAM。原备份未改动，没有flash/erase/format。完整原始证据仍为私有，公开仅来源/哈希/诊断结果。

私有镜像预构建曾有3次秒级目录命名冲突，在创建镜像前退出；失败日志保留于direct-20261028-pages1/256/16384目录。随后串行重试，不覆盖旧目录或放宽门禁。四次旧版本QEMU全窗口失败及恢复证据也保留，新版QEMU/手机通过不重写历史。

分配器仍仅使用原16MiB诊断arena；这次逐页可恢复写不证明跨页别名、长期隐藏DMA所有权或分配合同。下一步独立实现跨页同时标记、异常恢复及其门禁，再建立连续分配合同并推进手机有效DarwinBoot/XNU交接。完整移植目标仍未完成。
