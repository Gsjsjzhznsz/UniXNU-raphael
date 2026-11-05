# 原生 UFS 连续控制台日志

2026-11-04 实机连续日志通过：030111Z临时启动后人工恢复Android，自动提取191条有效4KiB记录、60664字节/917行、184条进度记录，dropped=0，无损坏尾块，counter递增、两侧保护块未变、新Android boot ID成立。日志完整保存至 SERVICE SNAPSHOT DONE; RETURNING；最后tick1831、root7/init4、syscalls7013、clients/frames0。原FDT完整checkpoint仍未通过，不将独立UFS日志改写为该轮passed。证据：evidence/private/ufs-console-log/20261104T024624Z/20261104T031141Z-automatic-return/report.json。

显式 `--ufs-console-log-report` 读取 `scripts/ufs_continuous_log.py prepare` 新建的私有日志分配报告。默认分配8MiB明文不可变文件；当前候选显式使用2MiB/512个追加槽位，前后各保留一个4KiB保护块；实际连续物理位置由本机FIEMAP产生，源码没有固定手机LBA。每次新启动使用新文件与新启动标识，已经写入的文件不复用。

补丁在原 `console_write` 和 `console_write_unbuffered` 捕获输出。捕获路径只向256KiB内存队列追加，使用非阻塞门锁；中断/打印路径不执行UFS I/O。普通root observer每10poll调用flush，每次最多4个4KiB块；UFS尚未online时继续保留队列。直接视频输出的观察器阶段标记也进入队列。

每个4KiB块包含64字节头与最多4032字节文本：启动标识、块序号、物理counter、文本长度、累计丢弃字节数和CRC。使用同一日志范围的一次写授权；各块只追加一次，写前要求全零，并执行WRITE10/FUA、精确范围SYNCHRONIZE CACHE与立即读回。原OS/SystemOS物理范围仍在驱动内排除；单块探针的授权撤销规则保留。

黑屏后可正常或人工重启回Android，再执行：

```sh
python3 scripts/ufs_continuous_log.py extract --report evidence/private/ufs-console-log/<本轮>/report.json
```

输出 `console.raw`、`console.log` 与 `report.json`。提取接受完整前缀，单独标出不完整尾块，不依赖临时FDT、nonce回传或完整诊断checkpoint成功。CRC用于识别断电撕裂记录；该路径不提供实时USB画面或截屏。

正常刷盘每10poll执行，实际墙钟间隔受调度与存储耗时影响；尚未刷出的内存尾部在突然重启时可能丢失；不会在panic/IRQ内强行获取存储锁。已有记录持续保存在专用文件中，文件写满后停止追加。

主机检查：生产队列C代码ASan/UBSan覆盖FIFO、待写重试、环回、容量和中断竞争；生产追加协议C++代码覆盖连续三块共用一份授权、顺序约束、旧数据拒写和末尾撤销；生产C生成的块通过Python提取器互通，并检查撕裂/不同启动/保护块变化。恢复QEMU只证明loader/返回路径，不冒充手机UFS持久性。

## 首轮日志给出的主线线索

030111Z原MKB_INIT报告systembag不存在、无法从Crypto加载并请求进入恢复模式；launchd随后仍继续至Early boot complete，因此尚未把该报错当作唯一根因。源码确认手机profile没有链接已有AppleKeyStoreState，而QEMU显示profile可显式启用它。后续单变量候选在既有易失、无口令Data环境中启用这项状态接口，并通过新日志判断原keybag路径和显示客户端是否推进。原系统密钥、用户Android Data和持久APFS Data均不在该服务能力范围内。


## 服务快照独立读回（2026-11-04，主机验证通过）

034350Z取消首方法提前停点后，完整恢复665.169秒未回连；人工恢复后读回210块/65721字节、丢字0，最后tick2011、显示clients5/frames0，保存至SERVICE SNAPSHOT DONE; RETURNING。原报告仍是失败且xnu_executed=null，独立连续日志证明原生执行；详细服务栈原先只进入未回传的恢复内存，不能据此判断首帧等待原因。

当前源码在既有服务捕获结束后，把原记录按RPH SNAP BEGIN/WORDS/END分段追加到同一UFS通道，包括原进程表、命名服务线程/内核与用户帧、首异常、显示计数及watchdog记录。仅观察线程执行，打印/IRQ路径仍只入队；不改变服务条件、服务槽容量或20/360/420秒预算。每行完整入队，按批刷盘，缺段或截断不会称为完整快照。独立日志解码不等于完整诊断handback。

提取时可指定本轮冻结预链接内核：

```sh
python3 scripts/ufs_continuous_log.py extract --report evidence/private/ufs-console-log/<本轮>/report.json --kernel artifacts/desktop-prelink/<本轮>/native-kernel.macho
```

内核必须对应此日志分配；输出另含service-snapshot.json，服务/异常复用已有native_early解码器。主机以032503Z真实恢复内存验证实际C写入函数，ASan/UBSan通过，13段/126284字节完整互通，服务/异常逐字节等价，截断不验收。首次构建因多加BSD头与OSFMK类型冲突失败；已改用原misc_protos.h中已有snprintf声明，不降低编译检查。040526Z新候选的887记录内核、恢复QEMU39项和镜像构建通过，040940Z唯一临时启动已接受；新增快照通道仍待实机读回。


## 详细服务快照实机读回

040940Z唯一实验完整恢复超时，用户人工恢复Android；042224Z读回322块/286913字节/3454行、230条进度、dropped0、无损坏尾块及保护块变化，13段详细服务快照实机捕获成功。物理观察360046.222ms，watchdog6次check-in/0失败，显示clients/validations/kicks/frames均0，首异常为空。独立UFS快照通过；原完整checkpoint失败、xnu_executed=null保留，桌面未通过。

证据：`evidence/private/ufs-console-log/20261104T040526Z/20261104T042224Z-manual-recovery/report.json`、同目录`service-snapshot.json`与`services-symbolicated.json`。
