# 2026-11-05 GitHub 源码发布

按官方[设备仓库](https://unixnu.com/zh/porting/device-repository)及[SoC 支持](https://unixnu.com/zh/porting/soc-support)规范拆分：

- 设备：`guowenye/UniXNU-raphael`，板级配置、DTS、补丁、package、移植记录与工作流。
- 共享平台：`guowenye/UniXNU-sm8150-common`，SoC配置、DTSI及`kits/Sm8150Platform`。
- `feeds.toml`及`unixnu.lock`固定SoC提交`c77321d82010250d6f100d7c17d7e721c17782bf`；本地覆盖仍通过忽略的`local.toml`设置。
- 原大工作区的公开scripts、tests、docs、源码与工具锁保存在`development/`，恢复路径见其README；历史文档中绝对路径与private/artifacts引用只表示原实验位置。

发布采用独立目录，不移动或清理活动工作区。只发布当前源码快照与公开文本摘要；备份、pycache、本机配置、设备dump、私有原始日志、厂商固件、原系统盘、owner私钥及生成镜像均未纳入本次提交。

保留每个文件原有许可证声明；上游源码依赖通过固定版本获取，没有将完整第三方源码树或闭源系统镜像复制进仓库。

截至本次发布，实机出现过加载条后黑屏。MCM补采显示LS已进入原插件注册，SpringBoard仍等待LS数据库；没有可见桌面或交互证明。最新1800/1860秒候选完成内核/载荷、39项恢复QEMU及手机镜像结构检查，未上机。当前源码提交不能追溯替代每次历史实验当时的完整源码图；原失败/null报告不改写，结构化完成等级不升级。

标准生产firmware/payload/bootimg配方和干净检出完整手机镜像构建仍待完成。公开源码和Porting record检查通过不等于生产移植或实机桌面完成。官方目录是否收录由其扫描和维护流程决定。
