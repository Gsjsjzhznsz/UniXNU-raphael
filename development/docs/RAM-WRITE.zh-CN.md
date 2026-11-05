# 可恢复 RAM 页诊断

2026-10-28。本机候选由 RAM-READ.zh-CN.md 与同轮原始证据推导，不使用其他手机参数。本实现仍默认关闭，仅 stage2、EL1、M/C/I 关闭、DAIF 全屏蔽。原始 RAM 字只留在 SEC 备份区，不写入公开证据或镜像。

库逐页保存全部512个64位字，写入地址相关图案和互补图案，每轮读回，然后写回全部原字并独立读回。入口默认关闭，显式支持1/8/256页；已验证范围以对应实机记录为准；不授予分配器或 DarwinBoot 新内存。4096字节、两轮图案及8秒预算均为诊断设计；256MiB候选/2MiB间隔由原loader要求与本轮内存审计产生。完整窗口/跨页别名/隐藏DMA所有权仍未证明。

同一次适配器调用先从不可变FV策略、live FDT、CPU寄存器和实时保护区重新完成256点只读门禁，再进行写入；不能用旧启动结果授权新启动。备份、状态、policy、read gate不得重叠，PA编码/地址上限、溢出、字段尺寸与窗口全部核对。备份摘要在恢复前复核；Dirty在首写之前设置，仅整页恢复并读回后清除。恢复不受诊断超时取消。若原内容无法验证，SEC停止，不进入Android。

原始页备份4096字节和恢复状态232字节显式放入SEC物化.data，并核对实际FD字节、地址、范围。首次构建检测到未物化BSS而被结构检查拒绝；未放宽检查，改为显式.data后重建通过。未扩大接近满的入口context。

主机真实C/ASan/UBSan43组、6154个故障注入位置通过，包括首/中/末及每个字的备份读、图案写前/写后、图案读/错值、恢复写/读/错值，以及时钟倒退/超时。恢复失败保留原备份且拒绝新Run；可再次恢复。另有25项独立wire反例与实际C结果解码。

QEMU1GiB与候选由其独立RAM bank计算，预加载非零原始数据。正常执行46项；第257个图案字写入后把独立NOP改为UDF，沿原fatal SEC路径恢复原页，48项通过；第一次稀疏读处UDF也通过。独立接收器逐字核对原数据与寄存器/原Image恢复。UDF不是实际data abort，恢复期间真实总线错误与异步SError未验证。最终机器码审计确认WriteRam64只有一次64位候选store、前后dsb sy；读取仅自有状态/栈。手机镜像检查点为NOP，异常注入只在QEMU副本进行。

固定QEMU：artifacts/sec-dxe-qemu/20261028T060730.612618Z-kmq9_fpg。默认normal/BRK/UDF回归45/42/42通过。主机、wire、镜像结构、模拟器与手机分别记录。

手机候选 evidence/private/sec-dxe-build/20261028T061319Z 仅编译/结构/预检通过，尚未执行。FD SHA256 2c693be861c07bce651729b4ffe6f4d2dc2bfa2cd226368855396a49bbf8c6a9；boot SHA256 8dbb5998d77428c6349300ed6c74c9c2937c0915a4e9d71a0a93c0c7c5564380。

```sh
python3 scripts/validate_ram_write.py
python3 scripts/run_ram_write_qemu.py
python3 scripts/audit_ram_read.py --qemu-report <本轮report.json>
python3 scripts/audit_ram_write.py --qemu-report <本轮report.json>
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --ram-write-pages 1
python3 scripts/run_sec_dxe.py --serial <serial> --build <本轮私有build目录> --preflight-only
```

下一步源码绑定后临时fastboot boot，独立解码ram-read/ram-write wire，确认Android/root/原boot，并正常重启清理。只有该轮通过才讨论扩大页数。DarwinBoot和真正XNU尚未在手机执行。


## 手机单页结果：20261028T062031Z

实现1b9a7351a095b92ea5f3d64f2ef07a63adf145e5的143项输入逐Git/快照绑定。现场只读256点通过后，0xc0000000第一页4096字节两轮图案1024字、512字恢复均通过；读2048次、写1536次，Dirty0/BackupWords0，原始与恢复摘要相等。235318ticks/19.2MHz，12.2561458333毫秒；没有异常。未公开原始RAM字。

nonce/stage2/status0、Android/root/原boot哈希通过，062401Z正常重启清理通过。独立记录器重新核对原wire/FDT/log、不可变attempt、构建/源码绑定及cleanup；见boot-ram-write-observation-pages1.json及ram-write-source-binding-20261028T061319Z.json。只是当前启动第一页可写可恢复，不代表整个256MiB或隐藏DMA所有权，也没有新增UEFI分配器内存。

八页版QEMU正常46/部分写后UDF48以及读取UDF通过，目录20261028T062434.104003Z-6mgpxc4_。062626Z手机八页候选完成编译/结构检查，尚未执行。


## 前八页实机与256页候选（2026-10-28）

八页版构建062626Z、实机063206Z：0xc0000000起连续32768字节，completed/restored均8，读16384次、写12288次，图案与恢复差异均0，Dirty/BackupWords均0，耗时98.4048958333ms。143项输入绑定9ce0974；063549Z正常重启清理、Android/root/原boot哈希通过。boot SHA256 0f8671b2eb7a2d55718c9fbf40e30e874c4cf7b96e02b48a909d468548571687。

记录器改用与来源绑定匹配的不可变attempt，并为每次run冻结handoff，单页和八页报告均引用各自不可变文件，避免后续实验覆盖历史来源。两份原wire/FDT/log和cleanup重新核验通过。

新增256页入口选择，固件算法不变。独立1GiB QEMU的256页正常46项、部分写后UDF恢复48项及读取UDF恢复通过，目录20261028T064119.192965Z-lnm4fiii。手机候选065009Z已编译/结构通过，首MiB预计约3.15秒，8秒设计预算；当前尚未执行。boot SHA256 8d35cb2a36aa17513164ebb32798c913808ef5cb832a1a2a40edda909ac00e65。即使此候选通过，也不表示整个256MiB、隐藏DMA所有权或分配许可。


## 第一MiB实机验证：20261028T071253Z

来源绑定a8a3033的065009Z镜像通过临时fastboot boot：0xc0000000起连续256页/1048576字节，completed/restored均256，图案262144字、恢复131072字均零差异，Dirty/BackupWords0，原始/恢复摘要相等。耗时3155.9350520833ms；现场256点只读及95项策略/4项入口保护再次通过。Android/root/原boot哈希正常，071435Z正常重启清理通过、临时属性消失。未flash/erase/format，未修改原备份。

boot SHA256 8d35cb2a36aa17513164ebb32798c913808ef5cb832a1a2a40edda909ac00e65；FD SHA256 a0d8a4e036fe5adecc44197a5622f53fb79821cf71536b4ce8905ef9b69f0ac7。独立原wire/FDT/log/不可变attempt与handoff/cleanup核验见boot-ram-write-observation-pages256.json。事实仅限前MiB，整个256MiB、跨页别名与隐藏DMA所有权仍未证明；分配器仍未扩展，手机DarwinBoot/XNU未执行。
