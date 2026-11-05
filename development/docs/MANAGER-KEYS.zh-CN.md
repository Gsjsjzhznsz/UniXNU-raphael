# 完整管理器的有界实体按键测试

2026-10-28。本轮在固定完整 UniXNURun 的可见菜单上测试实体上下与电源。历史诊断菜单的三键结果不替代本轮。通用 UniXNU、Mu 源码未修改。

## 实现与设计假设

新 PcdRaphaelManagerKeys 默认关闭；`--manager-keys` 生成两项均为 exit 的只读 FAT 配置，默认 Return to Android，另一项 Key test alternate return。测试超时六秒是诊断设计预算，不是硬件参数。物理 TimerArch 原十秒总预算保持。

输入包装器透传本机 SimpleTextIn。完整管理器首键会取消自身倒计时；包装器独立按实际物理计数器的绝对六秒截止点生成 Enter，单独记录 automatic，不能视为实体电源。消费序列、汇总计数、PMIC InputDxe 同轮 events/masks 及完整管理器选择日志由独立解码器交叉核对。还核对控制台与表 CRC 恢复、协议卸载、事件关闭；失败清理保留回调内存直到 SEC 返回。

## 主机编译、结构与模拟器

- 实际输入 C 与 ASan/UBSan：24 项；独立按键日志/PMIC交叉反例：29 项。
- AAVMF 完整管理器三轮：无按键倒计时、合成上/下/Enter 提前退出、单个上键取消倒计时后六秒自动退出；36 项、全屏恢复差异 0，截图已检查。
- 同源码 SEC2/MMU3/DXE6：59/61/75 项。其模型缺本机显示，显式跳过可见路径，不作为实体按键通过。
- 默认模式正常/BRK/UDF：44/41/41 项；路由写入后 UDF 恢复：54 项。UDF 不是真实 data abort。
- 初版夹具备用项仍指向 EFI 子程序，自动 Enter 导致二次菜单；失败目录 20261028T043332Z 保留。修为两个返回目标，EFI 交接另测。初版早期 manager timeout 字段不符，失败保留；已按 PCD 修正并重跑三阶段。

构建入口 `python3 scripts/build_sec_dxe.py --manager-keys --stop-after-stage 2/3/4`。完整检查日志、源码快照、命令与产物哈希由各 report.json 保存。

## 实机验证

实现提交 `513c3b825f5a7e68a396811f2ee2e814714b30bc`，92项板级和47项UniXNU输入逐Git blob与私有快照匹配。stage2 044424Z、stage3 044856Z通过，均分别正常重启清理。

首轮DXE6 045604Z收到实体上/下各1、电源0、自动Enter1，6.00085734375秒退出。用户“都正常”的观察只确认可见操作，没有误标实体电源成功。记录、镜像及日志均独立保留。

同一镜像复测050556Z，上/下/实体Enter=1/1/1、automatic=0、errors=0，顺序及上下高亮/Enter选择与PMIC wire/完整管理器日志一致。用户再次确认“都正常”。完整UniXNURun耗时4.18086515625秒；2527200像素写入并恢复，差异0、fallback0；物理IRQ/EOI/notify各560、完整恢复通过。050950Z正常重启清理、Android/root/原boot哈希通过。

- FD SHA256 `3b1ea51e86cb2fb7f1f38c11855edeb237146f10b176a9d2d10bc5a3b22c7f1c`。
- boot SHA256 `280db12a9d88b33d9c78104cc46ac579bf18205bd05c568d92b6810704b38289`。
- 手机构建 `evidence/private/sec-dxe-build/20261028T045259Z`。
- 机器记录 `manager-keys-observation-20261028T050556Z.json`，人工观察 `manual-manager-keys-observation-20261028T050556Z.json`；source binding按阶段分别保存。

全部为临时fastboot boot，没有flash/erase/format，没有修改原备份。按键结论限本次单次上/下/电源操作，不推广到长按/触摸。手机DarwinBoot/XNU、永久TimerArch和连续内核RAM仍待完成。
