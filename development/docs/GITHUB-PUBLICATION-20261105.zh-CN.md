# 2026-11-05 GitHub 发布记录

已按官方设备仓库与SoC布局整理，并以guowenye账户发布两个公开仓库：

- [UniXNU-raphael](https://github.com/guowenye/UniXNU-raphael)：设备源码、配置、补丁、package、13区移植记录；原公开主机脚本、测试、文档与源码锁保存在development/。提交`a3348bc9ce703d49eebfd2403946dece8dead474`。
- [UniXNU-sm8150-common](https://github.com/guowenye/UniXNU-sm8150-common)：共享SoC配置、DTSI及kits/Sm8150Platform。提交`aced7f66f2ec832d1d09936b13738782852a6860`。
- 设备feeds.toml及unixnu.lock已固定上述SoC提交；两仓库均设置unixnu、raphael、sm8150 topics，默认分支main。
- [官方Porting record检查](https://github.com/guowenye/UniXNU-raphael/actions/runs/41968624247)成功；发布副本的13区结构/路径归属、269份Python语法及相对SoC头文件链接检查通过。

本地独立发布目录：`/home/guo/publish/unixnu-20261105T043031Z`。未移动或清理活动工作区；未修改其源依赖pin。独立目录可用Git正常继续提交和push；活动适配目录仍是`/home/guo/work/raphael-fresh`。

本次未上传设备dump、私有日志、厂商固件、原系统盘、owner私钥、备份或生成镜像。保留源码已有许可证声明。历史私有artifacts路径只是索引，不是公开下载链接。

当前桌面仍未验证；最新30分钟观察候选未上机。CI成功表示移植记录检查通过；完整生产镜像配方和官网设备目录收录仍不在本次成功声明内。

## 许可证补充

两个仓库已补齐与现有SPDX及官方sheng一致的BSD-2-Clause-Patent完整文本，README已加入入口；各文件及第三方原有许可声明保留。设备feed固定了包含许可证的SoC提交。
