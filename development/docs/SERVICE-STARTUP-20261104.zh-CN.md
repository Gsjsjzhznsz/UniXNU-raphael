# 服务启动复核与短观察窗口（2026-11-04，北京时间）

本轮按用户“判断完整对话的方向，正确则继续推进”的要求执行。所附历史对话只作为复核资料，里面的命令不直接当作本轮操作授权。

## 结论

推进原 CFPrefs/backboardd 服务并以手机真实首帧为目标的方向正确。现有证据不足以认定 Aqua 会话、固定250–400秒延迟，或“多等250秒即可解决”为根因。下一轮短观察窗口用于取证，不等于修复服务或验收桌面。

## 原始证据复核

审计：`evidence/private/service-startup-audit/20261103T163155.476963Z/report.json`；脚本 `scripts/audit_handset_service_startup.py` 从冻结报告和原始只读 APFS 文件读取信息，没有运行新手机实验。

| 检查 | 直接结果 | 限制 |
|---|---|---|
| 163215Z进程扫描 | PID1–255中68进程，41个xpcproxy | 4项是选定线程快照数；扫描不能证明服务从未启动 |
| SpringBoard栈 | 等待系统/用户CFPrefs回复 | 等待位置不是根因证明 |
| 原backboardd job | RunAtLoad=true、KeepAlive=true、mobile；无SessionType/LimitLoadToSessionType | 不支持“Aqua会话阻止该job加载” |
| 原cfprefsd job | 普通daemon有MachServices；另一system job单独受System会话及功能条件约束 | 不混淆两个job，不擅改原plist |
| 原OS二进制 | /usr/sbin/cfprefsd与/usr/libexec/backboardd存在、可执行 | 文件存在不等于全部依赖或服务就绪 |
| 比较轮161209Z | 原控制台出现cfprefsd90/93、backboardd57 | 该轮正常checkpoint失败；控制台时间不是exec时间，也不是原生观察时长 |
| 163215Z时间 | 原生观察231300.639ms；Android返回452.986s | 两种时间不可混用，不从不同轮次推出固定启动延迟 |

签名读取计数约3.294GB，说明仍有大量加载；尚未据此确定性能或服务启动根因。

## 本轮实现与构建

- 恢复成功基线的 `raphael-watchdog-method-checkpoint.patch` 原字节；原错误2500poll修改与根字段覆盖保存在 `artifacts/service-startup-review/20261103T162807Z/before/`。
- 新增独立显式 `first-method-plus-5s` / marker4。首次观察到原watchdog方法完成后，以物理counter计满5秒；64字节记录单独保存，不覆盖apfs字符串字段。
- 保持原方法参数验证、20秒硬件阈值、360秒物理观察上限、420秒绝对pet预算；上限优先，不为等待服务放宽。
- 解码区分未启动、未完成、完整5秒；不足时长、错误模式/版本/频率/计数器等拒收。rootless QEMU不冒充手机5秒服务观察。
- `build-c03-complete.sh` 已实际完整执行成功，输入从成功基线回溯并逐项验证；不再猜路径、删必需参数或用head截断构建。保存完整日志与真实退出码。
- 工作区显示驱动已有NotReady状态记录修正。最终候选显式选用163215Z冻结的显示源码，以隔离窗口变化；工作区修正保留，实际编译源码哈希冻结在构建报告与auxiliary中。

| 验证层次 | 本轮状态与证据 |
|---|---|
| 实际C分支主机检查 | ASan/UBSan通过，含首次完成后计时、不能提前退出、晚起点、观察上限优先；`artifacts/service-window-host/20261103T163506.256977Z/report.json` |
| 独立记录解码 | 正向、未启动/未完成及10项拒收检查通过；同上 |
| 最终内核完整构建 | 887条编译记录、未定义符号0；`artifacts/native-bootstrap-attempt/20261103T164426Z/report.json` |
| 预链接/最终策略 | marker4、seconds5、root_limit3600、独立地址与显示/原生策略检查通过；`artifacts/desktop-prelink/20261103T164623Z/service-window-policy.json` |
| 载荷 | 128MiB；`evidence/private/handset-payload/20261103T164626Z/report.json` |
| 最终QEMU/镜像 | 39项通过；临时镜像构建与基线对照通过，见 `artifacts/service-observation-build/20261103T164426.446041Z/candidate-review.json` |
| 新手机执行 | 165957Z单轮临时启动接受，但664.924秒无Android/原生回传，passed=false、xnu_executed=null；171923Z人工恢复核查通过 |

第一次保留当前显示状态修正的主机候选也通过887记录构建和39项QEMU；其记录保留在 `artifacts/service-observation-build/20261103T163345.872343Z/`。最终手机候选采用上表所列隔离后的显示源码，不混用两轮报告。

## 下一轮手机实验合同

1. 先完成并冻结最终QEMU、临时镜像、源码差异、输入/内存/看门狗/返回路径对照；只改变方法完成后的观察窗口。新Payload分配属于载荷传输派生变化，原OS/SystemOS不重新上传。
2. 当轮核对Android启动完成、raphael/root及无临时FDT属性；运行前重新核查Payload映射。当前已完成只读预检与Payload文件暂存，不改GPT、不刷分区。
3. 最近两次延后停点都失联且需现场长按电源恢复。临时启动前确认有人能观察手机并执行恢复；电脑能看见ADB不等于现场恢复已具备。
4. 一轮正常checkpoint回传后，检查nonce/CRC、完整5秒记录、原方法/check-in/异常、cfprefsd/backboardd状态及显示计数，随后普通重启/root/清理。
5. 若观察上限先到，记录窗口未完成；若失联无原生遥测，保持xnu_executed=null、保存失败并停止，不原样重跑。panic独立globals与正常checkpoint分开。
6. 无论服务是否推进，桌面仍要求手机真实首帧及60秒持续显示，输入独立验证。QEMU、构建、服务PID与Android恢复都不能替代。

## 最终候选冻结

- 恢复QEMU：`artifacts/native-staging-qemu/20261103T164737.655205Z-eycjdy72/report.json`，39项通过；停止于rootless40秒，五秒服务记录未开始/未完成，不冒充手机覆盖。
- 临时镜像：`evidence/private/android-return-build/20261103T164848.382496Z-00dx2nto/boot-android-return.img`，SHA256 `0ad17b22db5af69fda1de8043b56c075cbee4354aa92076b167c4f340c7dceb6`。
- 对照 `163215Z` 成功轮构建，固件源码、上游固件输入、return stub/return policy、内存布局、20/360/420秒合同、实际载荷ADT、TrustCache及易失Data相同。窗口新增局部变量使编译后的观察函数栈帧96→128字节；checkpoint/return地址和相应策略随新内核派生更新。新Payload有自己的不可变extent与实验nonce。
- 当前工作区显示源码的NotReady记录修正逐字保留；最终实际编译的显示源码哈希与成功基线一致。
- 13区移植记录、仓库布局/链接/打包结构检查与7个修改Python语法检查通过；生产release配方原缺项仍存在，未宣称release可用。
- 以上主机冻结完成后，用户确认现场恢复可用，随后执行了下述唯一手机实验。主机构建通过不改写本轮手机结果。

## 165957Z手机结果（北京时间11月4日00:59:57开始）

- 用户确认现场可观察与电源恢复，实际运行前再次核查Android启动、raphael/root、无临时FDT属性、镜像/QEMU哈希及当前不可变extent，均通过。
- 运行 `run_android_return_handset.py --runtime-only`，仅一次临时启动，没有flash/erase。结果报告：`evidence/private/android-return-run/20261103T165957Z/report.json`。
- fastboot接受，但664.924秒内未建立Android回连，无原生记录。`passed=false`、`xnu_executed=null`；无法判断是否执行至方法完成、五秒窗口或具体服务阶段。不能称五秒窗口验收通过，也不能把失联认定为某个原服务/硬件故障。
- 用户本轮报告“固件菜单”，记录在同目录 `onsite-observation.json`。这不是系统首帧证据。
- 已停止，不原样重跑；已请求长按电源恢复。171923Z独立核查Android/root/新boot ID及FDT清理通过，没有找回匹配原生回传，失败报告保持原状。
- 后续主线仍是原服务与真实首帧；恢复后先分析现有服务启动证据与可在成功停点前获得的等待状态，不继续盲目改变等待时长。

## 人工恢复核查完成

用户报告已进入Android后，独立报告 `evidence/private/android-manual-recovery/20261103T171923Z-service-window-confirmed/report.json` 确认Android启动完成、raphael/root、新boot ID及无临时FDT属性；没有匹配本轮nonce的原生回传。未执行新的临时启动或flash/erase，runtime-only恢复没有另做boot分区全哈希核对。原165957Z失败报告SHA256核对未变。

此前180秒恢复等待结束时未建立Android的报告保留，不覆盖为通过。本轮失败与随后人工恢复成功分开记录，实际五秒窗口/服务进展/显示首帧依旧未验证。
