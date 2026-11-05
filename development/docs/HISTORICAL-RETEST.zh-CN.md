# 历史诊断镜像复测

2026-10-28：人工菜单测试重用原已通过手机 stage2/3/6 的 stage6 镜像，未用正在开发的 GIC 采集代码构建新手机镜像。

- 板级源码：b2e774c2fd940468611ff15c130ddb740cde7f55。
- UniXNU：0fc0fc1f9ddd0fbd4787738afef38667df5e0a95。
- 原构建：evidence/private/sec-dxe-build/20261027T193445Z。
- FD SHA-256：68d9610fc4f4a45b9235c0496ae5c87c406ab55761d62f4945fd58f8e9acaf37。
- boot 镜像 SHA-256：f563406025dc3ab3037eb0a46d44d09694ee08d03d7c592935b57ddf4b6799bf。

run_sec_dxe.py 默认仍要求构建输入与当前工作树一致。显式 --historical-binding 切换到历史模式：核对来源绑定、阶段、98 项构建快照、固定 Git blob、原 QEMU 输入及结果、实际 FD 文件、镜像哈希。每轮结果记录历史版本和报告哈希，不能表述为当前 HEAD 编译产物。--preflight-only 在任何 ADB/fastboot 操作之前退出。

```sh
python3 scripts/run_sec_dxe.py --serial "$SERIAL" \
  --build evidence/private/sec-dxe-build/20261027T193445Z \
  --historical-binding UniXNU-raphael/evidence/sec-menu-source-binding.json \
  --preflight-only
# 去掉 --preflight-only 才进行一次临时 fastboot boot。
python3 scripts/reboot_after_probe.py --serial "$SERIAL"
```

主机核验：真实历史构建的 98 项输入通过；改动镜像哈希、FD 哈希、阶段、上游版本、快照门禁、快照路径、QEMU 路径或输入哈希的八种描述全部拒绝。Python 编译和 git diff --check 通过。证据见 archived-build-preflight.json。

复用镜像的 identifier 与原构建一致，因此不能只凭 identifier 判断是新运行。每次启动前重新读取 FDT，要求所有旧临时诊断属性消失；分开保存启动前后 FDT、带时间的命令日志和不可覆盖的 attempt。每轮结束正常重启，再检查临时属性消失、Android/root 和 boot 分区哈希。

实机观察与按键事件在独立 manual-menu-observation 记录关联同一轮 attempt。编译、结构检查、软件回传和用户可见性/按键观察分别记载。
