# 完整 UniXNU 管理器显示事务

本轮在固定 UniXNU 0fc0fc1f9ddd0fbd4787738afef38667df5e0a95 上调用真正 UniXNURun，通用源码保持不变。板级新增 RaphaelManagerUiLib，将本机继承 GOP、SimpleTextIn 和有界物理 TimerArch 接到同一实例。当前仅合成只读 RAM FAT、两秒退出配置；没有加载 DarwinBoot 或 XNU。

## 实现与边界

PcdRaphaelVisibleManager 默认关闭。开启时自动要求显示/SMMU/像素只读、GOP、PMIC 输入及 GIC/物理 TimerArch 门禁，跳过旧十秒 GOP 色块测试，避免耗尽十秒 TimerArch 总预算。ManagerUiBegin 精确核对当前及 QueryMode 信息，保存全屏原图；完整管理器返回后逐行统计变化、恢复并回读全屏。失败时保留唯一原图，SEC 用已验证的物理显示恢复路径兜底。所有结果为独立128字节wire，SEC内352字节静态状态已核对实际物化，没有扩大入口context。

手机期望来自本轮既有硬件证据：1080×2340、stride4320、BGRA、base0x9c000000，详见GOP及DISPLAY文档。本轮未重设面板/时钟/刷新或写PMIC配置。手机必须满足真实物理GOP；模拟器的Blt-only支持明确记录base/extent=0，不能替代手机物理显示证据。

## 主机与镜像验证

- `python3 scripts/validate_manager_ui.py`：31项实际C/ASan/UBSan，包含原图保护、分配/备份/写回/回读失败、差异及重试、Blt-only和物理模式隔离。
- `python3 scripts/validate_manager_ui_wire.py`：25项独立wire，拒绝将QEMU缺硬件状态5视为手机成功。
- `python3 scripts/run_payload_fixture.py --manager-ui`：AAVMF 23项，完整管理器两轮；真实EFI事件中合成Up/Down/Enter，第二轮提前退出。两轮全屏恢复差异0，截图已检查；它不是手机截图或实体按键结果。目录artifacts/manager-ui-fixture-qemu/20261028T034054Z。
- `python3 scripts/build_sec_dxe.py --visible-manager --stop-after-stage 2/3`及不带stop的stage6：59/61/75项。自有SEC模型没有继承手机显示，显式状态5并跳过可见分支，不作图形证明。
- 默认stage6/BRK/UDF回归44/41/41；原无GOP物理管理器74项；route写入后UDF恢复54项。UDF不是真实data abort。
- 主机ICC/GIC/IRQ/route/TimerArch审计和来源门禁保持；手机每个阶段重新绑定其确切QEMU产物。

失败构建也保留：手机builder先拒绝不匹配阶段的审计，然后拒绝过期输入host快照；重新生成对应验证解决。组合模式又触发evidence-inputs重复mkdir，已修复为共用既有目录。上游网站本轮重新访问返回403，后续接口核对使用已固定的一手源码。

stage2手机候选evidence/private/sec-dxe-build/20261028T035022Z已编译和结构检查通过；FD SHA256 43a55e0ecd296cc35ecf6285e707f60f32189ced6dcc112f1df0c0082a81a83a，boot SHA256 cf28ab13543e2ced900a73b2bc2b43dafca6109836ffc51e48840731226abee0。此时尚未在手机执行本轮新模式，不能把上述主机和结构结果视为实机可启动。

## 实机验证流程

先提交实现，`record_visible_manager_observation.py bind --build ...`逐Git blob、快照、固定上游及QEMU绑定。依次临时启动stage2、3、6，每轮Android正常返回后正常重启清除临时标记。接收器保留每次不可变attempt，独立验证nonce、原始wire、日志、内存图、像素恢复、TimerArch/GIC/CNTP/CNTV恢复、root和原boot哈希。record子命令独立复核全部阶段与最后cleanup。

自动验证只证明真实管理器执行及像素变化/恢复；用户对完整管理器的可见性和实体按键要另记，不能继承诊断菜单已有三键人工结果。完整UEFI、常驻TimerArch、内核RAM分配、手机DarwinBoot和真正XNU仍未完成。

## 手机同源码三阶段与人工显示确认

实现50956e2dfb9322b7560a97d3189bf0725e94ff7c的90板级+47UniXNU输入逐Git blob/快照绑定。SEC2为035345Z，MMU3为035732Z，DXE6为040314Z。stage6真正管理器2.1313486979166667秒，日志graphics1080x2340/portrait和input yes；2527200像素全部变化且全部恢复，差异0，fallback0；输入200次采样/错误0，无实体键。物理IRQ/EOI/notify各355，后续relative/periodic/cancel/停表稳定及GIC/CNTP/DAIF恢复通过，CNTV未改。040520Z正常重启清理、Android/root/原boot哈希通过。

stage6 FD SHA256 4c27192d470af2fc55d8d1d14b98883305306701d20bb3319e5ea9b2689b6452；boot SHA256 846495a7444fe9f855e326adb419adb89b56eb36255b0bcb45be729b2c824ff6。手机builder stage6命令须显式`--stop-after-stage 4`，其默认值为2。记录器独立复核三阶段、wire/FDT/log/不可变attempt和cleanup，见boot-visible-manager-observation.json、visible-manager-source-binding-stage6.json。

用户对本轮明确回答“是的”，确认看到完整UniXNU菜单；人工结果另存manual-visible-manager-observation-20261028T040314Z.json，自动wire仍不自行宣称人工结果。该轮无按键操作，完整管理器内实体键仍待专门验证，不混用历史诊断菜单三键结果。所有手机操作均临时fastboot boot，无flash/erase/format或原备份修改。
