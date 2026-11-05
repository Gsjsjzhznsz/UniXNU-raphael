# 可恢复的小范围像素写入诊断

日期2026-10-28。基于本次CPU只读、SMMU和显示配置，在同一次入口重新满足门禁后，只修改候选缓冲区左上角256×128。没有显示寄存器写入、CTL_START/flush、面板初始化或分区写入。

## 设计与来源

物理起点、stride、extent全部来自现场PixelProbe记录；其依据是本机FDT及现场寄存器。矩形256×128、白框RGB三栏、10秒保持是诊断设计选择。缓存/MMU仍关闭，单次volatile32位写入后DSB。128KiB原值保存在本次Image派生的256KiB SEC栈内，运行时检查整个backup落在栈预算内。

先读取保存全部32768个原值，再写入，再逐字回读图案；之后按CNTFRQ/COUNTER等待10秒，恢复全部原值并逐字比较。字摘要是word-wise FNV-like校验，不能替代密码学哈希或逐字比较。异常返回路径在保存信息仍有效时尝试恢复；总线挂死或恢复访问自身出错无法保证自动恢复。没有把栈预算称为原厂所有权许可。

## 验证分层

实际PixelWrite.c主机模拟14项通过：准确保存/写/验/恢复/复验顺序、故意丢写后的恢复、非法尺寸/stride/地址/证明、backup越出栈等。artifacts/pixel-write-host/20261027T171355Z/report.json。

QEMU及手机记录随后追加。内存图案回读和恢复成功仍不等于面板可见；实体屏幕观察是独立验证。原始像素和镜像保持私有，保留原备份。

```sh
python3 scripts/validate_pixel_write.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --display-probe --smmu-probe --pixel-probe --pixel-write
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --display-probe --smmu-probe --pixel-probe --pixel-write
```

## 实机与可见性结果

源码 `e8c73694e86b6839ca36ee68775c95aa63a18b0d` 的全部29项包内输入匹配Git blob和QEMU快照；QEMU19项通过，FD结构检查通过。手机构建20261027T171546Z，第一次20261027T171629Z及重复20261027T172041Z均nonce匹配、stage2/status0。每次32768个像素全部写入、回读、恢复，mismatches=0，原值与恢复值摘要一致；保持计时至少192000000 tick（19.2MHz下10秒）。

第一次用户未及观察；重复实验用户明确回答“看到了色块”。这是独立的人眼面板可见证据，仅覆盖本次SEC/MMU关闭的小矩形图案。不是GOP、菜单或持续显示服务证明。随后正常重启清理通过，Android/root正常、原boot哈希不变、临时标记消失。

- FD SHA-256：`3828919210d94e134e76f185238c3779df506399cb37166fe6c65b2b69efe9d4`
- 私有boot SHA-256：`14c3340d704ee837cef96b6f7a2afb047d1f15a964a723552b462b0da1d0c410`
- 公开索引：boot-pixel-write-observation.json、sec-pixel-write-source-binding.json、sec-pixel-write-cleanup.json。
- 原始像素、固件、boot及设备日志保持私有，原备份未动。下一步实验性GOP需要新增uncached映射、保留内存HOB，并对当前源码重测stage2/3/6。
