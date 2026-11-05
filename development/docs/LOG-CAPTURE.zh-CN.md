# 本机日志路径核查

2026-10-29。已阅读用户提供的 https://unixnu.com/porting/log-capture ，并与本地固定 UniXNU 40d21cc 的 `docs/zh/porting/log-capture.md` 对照，没有同步上游。

指南依次使用 UEFI Advanced Logger/二维码、交接后的 UART/屏幕，以及具备存储预留和读取器后的持久化日志。指南没有给出 raphael 串口引脚；其他板型的 PMIC 地址、日志偏移和 Linux reader 镜像不能直接用于本机。

本轮仅只读 ADB/root 查询，原始输入保存在 ignored 的 `evidence/private/log-capture-readonly/`。

| 已验证事实 | 来源 |
|---|---|
| Android 正常、root可用，单一授权设备 | 180037.450637Z 的 boot-state 原输出 |
| console=ttyMSM0,115200n8；earlycon=msm_geni_serial,0xa90000；androidboot.console=ttyMSM0 | 180108.572820Z 的 root /proc/cmdline；SHA256 b74c645ad175013e4518c20f730ef971e9be89c49403eaa67a622e82e2eccd2c |
| qcom,qup_uart@0xa90000；范围0xa90000/0x4000；compatible qcom,msm-geni-console；status ok | 180431.470698Z 本轮 live FDT；SHA256 cdf077cfba57051a344687c62f007a0f37134288bdf97d8ee5fd2138120ef0c4 |
| 相同地址另有 disabled 的 I2C/SPI 复用节点 | 同一 FDT；不能仅凭地址认定所有节点活动 |
| /dev/ttyHS0 的 of_node 指向0xc8c000 | 同轮 sysfs只读输出；它不是上述 console节点 |

首次非root读取cmdline被拒绝，失败原记录保留，后续root读取成功。同份FDT在解析根节点/不支持reg布局及一个未用导入时出错，最后复用原文件解析成功，没有再次采集或修改设备。

仍未知：外部 UART 测试点、引脚电平和接线、Windows USB转串口端口、ABL持续输出，以及独立UEFI/XNU下的时钟/pinctrl/所有权。cmdline和FDT只确认Android配置，不证明UEFI串口已经工作。没有打开TTY、写UART MMIO、切换复用或拆机。

手机内核交接可先使用已有GOP屏幕检查点。UART实现需继续依据固定MiCode的GENI console源码和本轮FDT核对，不能套用其他手机地址。Advanced Logger仅覆盖固件日志，持久化存储范围尚未分配，本轮没有写日志分区。


## 本轮接口可用性补查

Windows Win32_SerialPort查询没有枚举到串口，未打开任何端口或写GENI MMIO。本次再次在线请求用户链接返回HTTP403；后续依据已固定的本地日志指南及此前读取记录，不因此同步仓库。已采集FDT中PSCI节点声明arm,psci-1.0/method=smc，但没有执行PSCI VERSION/FEATURES/SYSTEM_RESET。按名称未找到ramoops/pstore节点，不能据此断言系统没有其他持久化日志实现；目前没有获得可写持久化日志范围。

连续窗口实验仍采用已验证的固件日志/FDT回传和Android原始读取，手机三阶段及正常重启清理均通过。它没有ExitBootServices之后的日志证据，UART真实输出和接线仍未知。


## PSCI恢复与交接日志边界

后续da16f56已通过本机SMC查询PSCI1.1及SYSTEM_RESET支持；独立小Image自动回Android的操作恢复通过，参见PSCI-RECOVERY.zh-CN.md。reset后没有保存独立接收器日志，也没有直接手机SMC指令跟踪。UART配置事实仍仅属于Android；外部接线、电平、UEFI/XNU真实输出继续未知。自有UEFI有效XNU链路的新日志和硬件断点证据仅来自QEMU semihost，不能当手机串口。


## 高段解码返回日志

ANDROID-RETURN.zh-CN.md的手机阶段3/6现已通过高段LZMA恢复本机Android并回读nonce/FDT/CRC/日志。它不依赖串口，覆盖UEFI诊断正常结束后的回读。尚无手机有效XNU执行、ExitBootServices后日志或持久化存储证明；用户提供的日志指南继续作为UART/持久日志接口参考，未套用其他板的地址。


## 大载荷阶段日志

本轮再次枚举 Windows 串口为空；在线请求用户指南未取得正文，沿用固定40d21cc的已读正文。大载荷stage3/6已通过FDT返回wire/log和本机Android回读，仍是UEFI诊断回传，没有手机XNU或ExitBootServices后的日志证据。外部UART电平、引脚及真实输出仍未知。


## 原DarwinBoot加载日志

手机222405Z已回读原DarwinBoot装载日志及新的native-load wire，到达BeforeExitBootServices。尚无真正退出后的手机日志；374项独立复核范围见NATIVE-LOAD.zh-CN.md，UART真实接线/输出仍未知。


## 真实服务退出后的回传

手机224029Z通过真实原ExitBootServices返回后的CRC、args/ADT和物理timer恢复回传，376项输入与原始wire/log独立复核完成，见NATIVE-EXIT.zh-CN.md。本通道已覆盖退出服务后的诊断，尚未覆盖XNU指令。2026-10-29本轮Windows串口仍为空，在线用户链接未取得正文；使用已固定的本地指南，无fetch/pull。UART引脚/电平/外部输出保持未知。


## 首次手机XNU指令回传

230308Z已覆盖原DarwinEnter后的XNU原始5指令前缀，精确BRK标记、PC/ESR/SPSR/启动寄存器、MMU关闭和恢复结果由独立40Q记录回传，381项输入/原始证据复核通过，见NATIVE-ENTRY.zh-CN.md。此证据是临时内存恢复通道，不是串口或持久化日志；尚不覆盖XNU自身异常向量/页表切换及arm_init。


## XNU MMU开启后的完整页表与寄存器回传

234327Z已通过高VA arm_init检查点的72Q与64KiB原bootstrap页表快照回传，389项输入/原记录独立复核；精确PC/ESR、翻译状态和恢复结果见NATIVE-MMU.zh-CN.md。日志通道现已覆盖原XNU页表建立/MMU切换，但arm_init C体尚未执行。本轮Windows仍无串口，在线用户指南请求未取得正文，依据本地固定指南；没有UART引脚/电平/真实输出或持久存储声明。


## 手机C初始化变化记录与恢复

001904Z已带回arm_vm_init入口的72Q/MMU、40Q early及130,896字节变化delta。对原Mach-O/BSS重建全部3段后校验CRC/SHA与const_boot_args、BootArgs及页表对应，396输入/原记录独立复核通过，见NATIVE-EARLY-RECOVERY.zh-CN.md。此仍是内存/FDT/Android恢复日志，没有UART/持久化存储结论；尚不覆盖pmap换表后的执行。


2026-10-29补充：QEMU原arm_vm_init已真实换TTBR1/置空TTBR0并返回，66页活动页表、644页高地址数据映射及7处完整快照经396份冻结输入独立复核。手机仍仅到arm_vm_init入口。下一步独立TTBR0转换表恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)；未同步上游。


2026-10-29：stage12换表后恢复已实现，QEMU正向36项及同镜像独立5场景通过；旧stage11回归31项通过。手机仍以001904Z的arm_vm_init首指令为准，stage12尚待最终冻结构建、旧分支回归和本机布局预检。原始TTBR与诊断转换根分开，输入ADT的random-seed清零由独立备份恢复，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。上游未同步、RAM alias暂停、原备份未改动。


2026-10-29。手机011328Z的stage12通过：原XNU arm_vm_init完成并换TTBR1/置空原TTBR0，在PE_consistent_debug_inherit首指令捕获后完整恢复3段/原代码/初始表和输入ADT。66页活动表、644页高数据映射及132936字节delta通过；80.337秒自动回Android，正常重启/root/原boot哈希/临时属性清理通过。405份Git/blob/冻结输入与原始回传独立复核，详见[NATIVE-PMAP.zh-CN.md](NATIVE-PMAP.zh-CN.md)。尚无正常XNU IRQ/timer生命周期、根卷或用户态。下一步推进pmap后的平台初始化与持续日志。未同步上游、未写分区、原备份未改动；当前正常Android且无运行中的手机实验，RAM alias仍暂停。
