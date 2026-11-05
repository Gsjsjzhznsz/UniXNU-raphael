# 2026-11-04 UFS读取合并、服务日志分析与修复

本轮已按用户要求停止。手机已人工回Android，并核查启动完成、root和临时FDT属性不存在；没有后续手机实验或自动任务。

045614Z原完整回传超时，原报告保持passed=false、xnu_executed=null。独立UFS日志捕获371条有效记录、297594字节、3587行、279条进度，dropped0、保护块未变、13段详细快照完整。实际观察360090.721ms，watchdog11次签到/0失败，首异常记录为空。独立日志证明原生执行，不替代正常checkpoint。

16KiB合并读取实机生效：早段约3.95块/命令，约21MiB/s，对照固态属性轮约15MiB/s；服务段降至约1.2块/命令，仍约5MiB/s，说明此阶段主要是小块请求，继续扩大最大命令不能直接解释或解决当前等待。最后计数读取4053304320字节、失败0；显示clients4，validations/kicks/frames/retired均0。客户端计数仍是进入数，不能单独称成功返回。

SpringBoard27仍等待BKSDisplayGetMainScreenInfo。BackBoard原PID57不在末尾进程表，而新PID109存在；这证明进程实例发生更替，但没有原始退出原因，不能判断是正常退出、信号、内存回收或其他原因。用户观察黑屏，没有桌面首帧。

确定的问题是采集器按PID递增填满8槽，launchd/SpringBoard/configd/keybagd/usermanagerd/两个cfprefsd/lsd占满后，重启成109的BackBoard被遗漏。修复保持原8槽/8线程/128word布局，使用固定服务优先级替换低优先级记录，清除旧进程槽映射并归零旧线程数据。原解码器无需改变。另在显式service-observer的原proc_exit入口只读记录选定服务的原始status、reason namespace/code/flags和VM页计数；原退出与信号流程不变，日志仍通过现有非阻塞控制台队列。周期控制台增加同样4项VM计数。

日志准备已改为Android自带fallocate预分配，再dd原地填充；两次流式写入失败报告保留，最终新512槽分配只有一个物理extent。没有修改GPT、flash/erase或放宽日志连续性与guard要求。

主机验证：读取extent37项、真实QEMU UFS模型45项、实际controller read函数10项ASan/UBSan通过；读取候选完整887记录内核、预链接/载荷、39项恢复QEMU及临时镜像通过。采集修正3组真实选择器回放覆盖晚PID109、未出现BackBoard和大量候选饱和，验证引用释放、旧槽映射、线程尾部及原解码；退出格式覆盖有reason、无reason及不选中的进程。既有8组捕获/14拒收/4解码回归通过。最终源码完整887记录内核通过，未定义符号0。新增采集修正没有生成或启动新手机镜像，黑屏和桌面未验收。

证据：

- `artifacts/desktop-read-batches/20261104T045012Z/execution-result.json`
- `evidence/private/android-return-run/20261104T045614Z/report.json`
- `evidence/private/ufs-console-log/20261104T045329Z/20261104T050935Z-manual-recovery/`
- `artifacts/ufs-read-batches/20261104T044849Z/production-read-host/report.json`
- `artifacts/service-capture-visibility/20261104T051314Z/host-report.json`
- `artifacts/service-capture-visibility/20261104T051314Z/build-final-report.json`
- `artifacts/service-spawn-host/20261104T051443.718189Z/report.json`

下次由用户明确要求继续后，使用新日志分配、新候选与修正后的服务捕获，读取BackBoard退出原因和当前实例的线程状态；不要重跑045614Z镜像。观察预算、RAM、服务策略和原系统二进制本轮均未因猜测修改。
