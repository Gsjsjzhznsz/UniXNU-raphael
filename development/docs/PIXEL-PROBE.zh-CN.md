# 启动 CPU 像素与计数只读实验

日期2026-10-28。承接wire v4实机SMMU/显示配置，独立实现PixelProbe.c；不加载原厂显示模块，不写像素、时钟、电源、SMMU或刷新寄存器。

## 参数与前提

地址来自本次FDT的cont_splash保留区和本次VIG0寄存器，不是另一手机配置。FDT没有no-map，首次主机模拟暴露错误的no-map前提后已纠正。CPU仍EL1、MMU/cache关闭。仅接受唯一线性ARGB8888、单plane、无crop/scaling/secure、完整extent在保留区内、全部stream唯一关联AArch64且S1 disabled/S2 bypass的CB。每次实验现场重新采集以上门禁。

64×64均匀像素网格、32轮每约2ms采样和有限轮询上限是诊断设计选择。四个只读interface寄存器来源见pixel-source-audit.json；TE内部计数变化不能单独证明外部TE或面板更新。候选CPU读取也不能证明完整缓冲区生命周期与所有权。4096原始像素和原始FDT仅保存在私有目录，公开只记录哈希与统计。

## 分层验证

- 实际C模拟硬件22项通过：artifacts/pixel-probe-host/20261027T170249Z/report.json，覆盖准确4096像素/128寄存器读取、SMMU不支持、格式/尺寸/保留区错误、无刷新和timer停止的有界退出。
- 保留前期失败：编译的缩进和未初始化告警已修正；错误的no-map要求已按本机FDT更正。
- QEMU stage2 18项及FD结构检查通过：artifacts/sec-dxe-qemu/20261027T170436Z/report.json。QEMU不模拟手机显示，仅验证不匹配硬件时不读像素。
- 上下文连同像素记录仍受context+0xf000静态断言约束，guided scratch最后4KiB保留。stage3/6尚需重测。

```sh
python3 scripts/audit_pixel_sources.py
python3 scripts/validate_pixel_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --display-probe --smmu-probe --pixel-probe
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --display-probe --smmu-probe --pixel-probe
```

实机结果在完成后另行追加。本轮不把CPU样本、配置一致性或内部计数当作实际可见输出证明。


## 实机只读结果

`20261027T170622Z` nonce匹配，stage2/status0；4096个CPU像素样本、32轮interface采样全部回传，Android/root和原boot哈希通过。所有网格RGB均黑、只有1个不同像素值；这是稀疏采样，不能声称每个像素全黑。约62ms内TE读/写指针行计数移动，frame_count/read_pointer_frame_count均0，INTF_STATUS均0。内部计数在动不等于证明实际fetch/外部TE/面板更新。

固件源码 `9d85e8809f246726c97ee57bf6d8c6c7878e8987`，全部27个包内输入与手机/QEMU构建逐项相同（以binding内实际计数为准）。FD SHA `891ba94f1feed97d7dfde78cef2df60fa673f7d30a478cc3b9f1b7e7ce6e7d1a`，私有boot SHA `9e2cdbe6f1350294b6625c5dee013b848f867943adf61446309aa4c3c5a88a63`，构建 `20261027T170551Z`。源码绑定和正常重启清理见sec-pixel-source-binding.json/sec-pixel-cleanup.json。私有缩略图由Python标准库生成，不公开原始像素。

下一步进行小范围可恢复写入并核对原值恢复；必须另行验证可见效果，不能把内存写入回读当成GOP/显示成功。
