# 手机DarwinBoot拒绝与卸载诊断

2026-10-28。默认关闭的darwin-test模式复用固定、未修改DarwinBoot 3325e352d7df68a9f9ad74832ed94a6acbbd7390，通过本机独立SEC/MMU/DXE、物理TimerArch和只读FAT加载驱动。该模式只供应40字节故意损坏的Mach-O：load command只占8字节却声称segment command长72字节，没有合法segment或入口；不提供有效内核/ADT，不请求256MiB窗口，不调用DarwinEnter。

实测项目包括FV内PE32的LoadImage/StartImage重定位、v2 loader协议、空请求/缺文件/坏Mach-O直接请求及UniXNUBootEntry拒绝、Boot Services继续可用、UnloadImage后协议移除、虚拟日志控制台与系统表CRC恢复，以及只读FAT CRC不变。ExitBootServices事件必须为0。显示/按键不启用、不新增RAM；原生XNU不在本诊断中执行。

构建前核对原loader全部文件Git blob、来源审计、独立wire反例、FD精确模块集合、QEMU同源码stage2/3/6和路由故障恢复。新组合初次被FD检查器拒绝，保留失败；仅增加明确的CPU+PhysicalTimer+Darwin模块组合，并继续校验FFS类型、PE子系统与APRIORI顺序，不放宽其他集合。

20261028T080626.718885Z的stage6 QEMU 81项、080914的stage2/3 59/61项和路由故障恢复55项均通过。对应源码/定时器/loader主机审计已刷新；082113Z手机stage2镜像编译与结构通过，boot SHA256 42fca6b7db4e797a62b92c44ea28e4709b589e4d29d01d41eac8c1b8a0565c1a。历史256页RAM镜像的Git/快照预检回归通过。手机阶段结果尚未执行。绑定、原wire/FDT/log、不可变attempt/handoff、Android/root/原boot哈希与正常重启清理通过后，再单独归档。驱动拒绝路径成功也不等同退出Boot Services或内核交接。

```sh
python3 scripts/build_sec_dxe.py --stop-after-stage 4 --darwin-test --payload-test --physical-timer-arch
python3 scripts/validate_darwin_wire.py
python3 scripts/audit_darwin_sources.py
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --darwin-test
```


## 手机实测通过

实现02f39c0b8313cdfb8d0e22651b4197d2b03d581a，152项板级/UniXNU/固定DarwinBoot输入逐Git blob及构建快照核对。三阶段：SEC2 082338Z、MMU3 082804Z、DXE6 083159Z；对应构建082113Z/082636Z/083017Z。每阶段均nonce匹配、status0、Android/root/原boot哈希通过。

DXE中v2协议0x20000、LoadImage/StartImage/UnloadImage均通过。空请求EFI_INVALID_PARAMETER，缺文件EFI_NOT_FOUND，直接与UniXNUBootEntry损坏Mach-O请求均EFI_LOAD_ERROR；ExitBootServices=0、日志207字节、Boot Services仍可分配/释放。驱动协议移除，原控制台句柄/指针及系统表CRC恢复；只读FAT前后CRC2975978888一致。同轮物理TimerArch的IRQ/EOI/notify各262，relative/periodic/cancel及GIC/CNTP/DAIF/CNTV完整恢复。

最终boot SHA256 173fff434312ffef554132848ac705fb4aa07dc3074795a3d445013bbfe963a2；FD SHA256 725a1caa59415c624e8c9e66c5e0abb6778514ade23ddeb8142c654d80d34163。阶段间082602Z/082934Z正常重启清理，最终083330Z正常重启后临时属性消失，原boot哈希不变。

`record_darwin_refusal.py ... record --cleanup evidence/private/entry-probe-cleanup/20261028T083330Z`独立核验各阶段原wire/FDT/log、immutable attempt/handoff、来源绑定与cleanup；公开索引boot-darwin-refusal-observation.json。原始内容与镜像留ignored私有目录。没有有效内核、没有新RAM或手机内核交接。
