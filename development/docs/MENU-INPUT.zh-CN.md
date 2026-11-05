# 菜单与输入协议诊断

## 来源和实现

固定 UniXNU 0fc0fc1f9ddd0fbd4787738afef38667df5e0a95 的 Ui/Font/Logo 未修改，直接链接通用绘制实现。审计见 menu-source-audit.json，每个源码与 Git blob 核验并记录行锚。
本端口只实现有界诊断控制循环，不等于完整 UniXNURun。正常 UniXNU 菜单依赖 TimerArch/SetTimer/WaitForEvent；本端口尚未完成周期定时器架构服务。

PmicInputDxe 使用同次 SEC APID 解析结果，推导且只映射所需 observer 4KiB 页，发布 MMIO 保留 HOB。stage2 检查规划，stage3 读取两路状态验证映射，stage6 安装 SimpleTextIn 与 vendor device path，更新系统表 CRC。失败回滚。
WaitForKey 使用 EVT_NOTIFY_WAIT，按需采样，不声称硬件 IRQ 或周期定时服务。5ms 采样限速为设计策略，15ms 去抖来源为本机 FDT。音量上/下映射 SCAN_UP/DOWN，电源映射回车；启动已按住、组合键抑制，释放后重启用，长按只报一次。传输失败锁止。
EXT_READL 仅读取 PMIC，一字节有界事务；会向 observer CMD 写读取命令。没有 PMIC 配置写入。

菜单有三项 Return to Android / Key test / Boot information，40秒硬件计数器超时自动返回，电源选择首项可提前返回。保存可见 framebuffer，绘制后退出逐像素恢复。1080×2340备份约10MB，仍只在16MB诊断 arena内；这不是完整内存所有权证明。

## 主机和模拟器

- 输入实际 C 驱动、EFI 回调及过滤器 26项 ASan/UBSan 通过；总线和 EFI 服务是模拟对象，不是实体按键证据。
- GOP 实际 C 40项通过，包括恢复失败保留备份并重试。
- QEMU SEC 同源码24项通过；板级快照51项，通用UniXNU快照47项。
- AAVMF 菜单 1280×800、1080×2340均通过，合成 UP/DOWN/Enter各1；恢复1024000/2527200像素，差异0。PNG仅为模拟器截图。

## 实机

同源码stage2/3/6实机通过。stage6安装SimpleTextIn与设备路径，8000次采样、错误0、按键事件0；40秒菜单超时后完整恢复2527200像素、差异0。nonce、Android/root、原boot哈希和正常重启清理通过。用户尚未提供这次菜单可见性或实体按键观察，均保持未验证。
51项板级及47项通用输入逐文件绑定提交 b2e774c2fd940468611ff15c130ddb740cde7f55；各阶段FD/boot哈希见sec-menu-source-binding.json。stage6主机QEMU正常29项、注入BRK26项通过。此为通用绘制与有界诊断循环，不是完整UniXNURun。


## 2026-10-28：人工菜单与实体三键验证

重用已验证的 b2e774c 历史镜像，未编译新手机固件；历史输入与快照核验方式见 HISTORICAL-RETEST.zh-CN.md。两轮分别保存启动前后 FDT、不可覆盖 attempt 与用户观察。

- 20261027T214935Z：用户仅短按音量下三次，回传 down=3/up=0/enter=0；40秒超时返回。该轮不验证另两键。
- 20261027T215414Z：按音量上一次、音量下一次、电源一次。用户确认三步均符合预期（上至 Boot information、下回 Return to Android、电源提前返回）；设备独立回传 up/down/enter=1/1/1，1422次采样、错误0，约7.1058秒由 Enter 选择返回。全屏2527200像素恢复、差异0。
- 两轮 Android/root/boot 分区 SHA-256 均通过；各自正常重启清理临时 FDT 属性通过（215236Z、215618Z）。没有 flash/erase/format，原备份未修改。

该证据验证本轮继承显示模式的完整可见诊断菜单、上下选择与电源确认。主机 wire 解码器仍保留 human_visibility_verified/physical_keys_verified=false，因为解码器单独不能验证人工事实；人机结合的成功结果见 manual-menu-observation-20261027T215414Z.json。没有验证长按重复、组合键、触摸、手机 TimerArch、完整 UniXNURun 或 DarwinBoot/XNU。
