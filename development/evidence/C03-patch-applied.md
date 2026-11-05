# C03 补丁已应用：延长服务启动等待窗口

**时间：** 2026-11-03 20:30  
**状态：** ✅ 代码修改完成，等待构建和测试

## 修改内容

### 文件：`UniXNU-raphael/patches/xnu/raphael-watchdog-method-checkpoint.patch`

**关键变更：**
1. 添加 `raphael_native_service_grace_polls = 2500`（250秒额外等待）
2. 修改退出逻辑：在 watchdog 方法完成后不立即退出，而是继续等待
3. 总观察时间：约 23秒(方法) + 250秒(服务等待) = **273秒**
4. 仍在420秒绝对pet预算和20秒硬件阈值内

**预期行为：**
```
poll 0-230:    正常启动，等待 watchdog 方法
poll ~230:     watchdog 方法完成（首次 check-in）
poll 230-2500: 继续等待服务启动（backboardd、cfprefsd）
poll 2500:     退出观察窗口，返回诊断数据
```

**证据标记：**
- `raphael_native_root_record[8]` 设置为 `0x53564345584E5452` ("RTNXECVS")
- 表示使用了扩展服务窗口

### 备份

原补丁已备份到：
```
UniXNU-raphael/patches/xnu/raphael-watchdog-method-checkpoint.patch.backup-20261103xxxxxx
```

## 理论依据

### 实验证据对比

| 实验 | 观察时长 | backboardd | 结果 |
|------|---------|------------|------|
| 161209Z | 520秒 | ✅ 启动了 (backboardd57) | panic但证明可以启动 |
| 163215Z | 231秒 | ❌ 未启动 | 正常退出但太早 |
| **新实验** | **~273秒** | **预期启动** | 目标：正常观察到服务 |

### 时间窗口分析

根据证据，backboardd 的启动时间在：
- **下限：** > 231秒（163215Z未启动）
- **上限：** < 520秒（161209Z已启动）
- **估计：** 约 250-400秒

选择 250秒等待（2500 poll）是保守但合理的：
- 覆盖估计下限
- 仍在硬件和软件预算内
- 如果还不够，可以继续增加

## 下一步

### 1. 完整内核构建（必须）

```bash
cd /home/guo/work/raphael-fresh

# 使用与163215Z相同的配置，但新的补丁会自动应用
python3 scripts/build_native_bootstrap.py \
    --native-diagnostic \
    --handset-display \
    --handset-data \
    --handset-ufs \
    --service-observer \
    --watchdog-method-checkpoint first-method \
    --scratch-data <path-to-scratch-data-report>

# 预计时间：2-3小时
```

### 2. QEMU 验证（可选但推荐）

```bash
# 使用新构建的内核运行 QEMU
# 验证补丁逻辑正确（虽然QEMU不会启动真实的launchd服务）
```

### 3. 手机镜像构建

```bash
# 构建手机镜像
python3 scripts/build_native_staging_handset.py \
    --kernel-inspection <new-kernel-report> \
    --native-video \
    # ... 其他参数与163215Z相同
```

### 4. 手机测试

```bash
# 启动手机实验
python3 scripts/run_android_return_handset.py \
    --image <new-handset-image> \
    --android-return-timeout 660
    
# 预计观察：
# - ~273秒后自动返回Android
# - 控制台中出现 backboardd 启动日志
# - services-symbolicated.json 中有更多进程
```

## 验收标准

### 最小成功 ✅
- [ ] 构建通过（887记录）
- [ ] QEMU 通过（39项）
- [ ] 手机接受临时启动
- [ ] 观察时长 > 250秒（不是231秒）
- [ ] 正常返回 Android
- [ ] `raphael_native_root_record[8]` = `0x53564345584E5452`

### 理想成功 🎯
- [ ] backboardd 在控制台日志中出现
- [ ] 至少5个以上的进程（不只是launchd/SpringBoard/configd/keybagd）
- [ ] SpringBoard 状态有变化（不再完全阻塞在 CFPreferences？）

### 完全成功 🌟
- [ ] backboardd 和 cfprefsd 都启动
- [ ] display_clients > 0
- [ ] frames > 0
- [ ] 达到 D01：首帧显示

## 风险评估

**极低风险：**
- 只延长等待时间，不修改核心逻辑
- 仍在所有硬件和软件预算内
- 可以随时回退到备份补丁

**可能的失败场景：**
1. **250秒还不够：** backboardd 需要更长时间
   - **应对：** 增加到3000 poll（300秒）或更多
   
2. **backboardd 启动后 crash：** 如161209Z
   - **应对：** 至少证明服务可以启动，然后分析crash原因（C04）
   
3. **cfprefsd 仍然不启动：** XPC机制问题
   - **应对：** 单独处理 cfprefsd（可能需要从内核强制启动）

## 时间估算

- ✅ **代码修改：** 完成（10分钟）
- ⏳ **构建：** 2-3小时
- ⏳ **QEMU：** 30分钟
- ⏳ **手机镜像：** 30分钟
- ⏳ **手机测试：** 15分钟
- **总计：** ~4-5小时一个完整循环

## 后续计划

如果这次成功（backboardd 启动）：
→ **C04：验证服务启动和显示连接**  
→ **C05：调试帧输出**  
→ **D01：首帧验收**

如果这次失败（backboardd 还是不启动）：
→ **回到 C02，深入调查 launchd 配置**  
→ **考虑直接从内核启动 backboardd**