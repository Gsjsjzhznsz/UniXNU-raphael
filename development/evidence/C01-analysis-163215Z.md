# C01 分析报告：20261102T163215Z 显示服务阻塞点定位

**分析时间：** 2026-11-03
**分析对象：** 最新成功诊断 20261102T163215Z

## 执行摘要

**根本原因已定位：** SpringBoard 等待 CFPrefs 服务响应，但关键的系统守护进程 **cfprefsd** 和 **backboardd** 根本没有启动。

**影响：** 没有 cfprefsd，SpringBoard 无法读取配置；没有 backboardd，显示/输入管理无法工作。这导致 `display_clients=0, frames=0`。

## 详细分析

### 1. 进程列表（services-symbolicated.json）

当前只有 **4 个进程** 在运行：
- PID 1: launchd
- PID 27: SpringBoard
- PID 37: configd  
- PID 45: keybagd

**缺失的关键进程：**
- ❌ cfprefsd（系统和用户配置守护进程）
- ❌ backboardd（显示和输入管理守护进程）
- ❌ 其他大量系统服务

### 2. SpringBoard 阻塞点（栈跟踪）

SpringBoard 主线程卡在：
```
_CFPREFERENCES_IS_WAITING_FOR_SYSTEM_AND_USER_CFPREFSDS
  ↓
mach_msg2_trap (等待 IPC 响应)
```

另一个线程也在等待：
```
_CFPREFERENCES_IS_WAITING_FOR_DIRECT_CFPREFSD
  ↓  
-[CFPrefsPlistSource sendRequestNewDataMessage:toConnection:retryCount:error:]
```

**结论：** SpringBoard 在启动早期就尝试读取配置，但 cfprefsd 没有启动，导致 IPC 请求永远等待。

### 3. 控制台日志分析

**成功的部分：**
- ✅ launchd 正常启动 (PID 1)
- ✅ Early boot complete 达成（第359行）
- ✅ SpringBoard 被 launchd 启动（第364行，PID 27）
- ✅ 部分系统服务启动（watchdogd、logd、keybagd、mediaserverd等，第395行）

**问题点：**
- ❌ 控制台中完全没有 cfprefsd 的启动记录
- ❌ 控制台中完全没有 backboardd 的启动记录
- ❌ 大部分预期的系统服务都没有启动

### 4. 显示状态（native_video）

```json
{
  "status": 4,
  "protocol_installed": 1,
  "query_verified": 1,
  // ... GOP 接口正常 ...
  "start": 0,
  "end": 0,
  "hold_ticks": 0
}
```

GOP 显示接口本身工作正常，但没有任何上层服务使用它。`clients=0, frames=0` 是因为 backboardd 没有启动。

### 5. 根本原因链

```
launchd 启动
  ↓
Early boot complete
  ↓
SpringBoard 启动
  ↓
SpringBoard 尝试读取配置 (CFPreferences)
  ↓
等待 cfprefsd 响应
  ↓
❌ cfprefsd 根本没被启动
  ↓
SpringBoard 永远阻塞
  ↓
backboardd 也没有启动（可能依赖 SpringBoard 或被 launchd 配置阻塞）
  ↓
没有显示管理器
  ↓
display_clients=0, frames=0
```

## 下一步修复方向（C02）

### 方案A：调查 launchd 为何没有启动 cfprefsd

**检查项：**
1. cfprefsd 的 launchd plist 是否存在？
   - `/System/Library/LaunchDaemons/com.apple.cfprefsd.system.plist`
   - `/System/Library/LaunchDaemons/com.apple.cfprefsd.xpc.daemon.plist`
2. launchd 是否尝试启动但失败？（需要更详细的 launchd 日志）
3. cfprefsd 二进制文件是否存在且可执行？
4. 是否有依赖关系阻塞了 cfprefsd 启动？

### 方案B：调查是否是 Data 卷挂载问题

cfprefsd 需要访问 `/var/mobile/` 下的用户配置：
1. Data 卷是否正确挂载？
2. `/var` 目录结构是否完整？
3. 权限是否正确？

**已知：** 190907Z 实验有可写 RAM Data，但那是临时的 RAM 盘。163215Z 是否有持久化 Data 卷？

### 方案C：最小化复现

可以尝试：
1. 在 QEMU 中测试 cfprefsd 单独启动
2. 查看 cfprefsd 的库依赖是否都满足
3. 手动调用 cfprefsd 看启动失败原因

## 验收条件（C02）

下一步完成标准：
- [ ] 确认 cfprefsd launchd 配置存在且语法正确
- [ ] 确认 cfprefsd 二进制存在且依赖满足
- [ ] 确认 Data 卷挂载路径和权限正确
- [ ] 识别出 launchd 没有启动 cfprefsd 的具体原因
- [ ] 制定具体的修复方案（例如：修改 launchd 配置、修复 Data 卷、添加缺失依赖等）

## 附录：对比其他实验

| 实验 | cfprefsd | backboardd | SpringBoard | 显示 |
|------|----------|-----------|-------------|------|
| 163215Z | ❌ 无 | ❌ 无 | ✅ PID27 阻塞 | clients=0, frames=0 |
| 161209Z | ? | ✅ 有（日志提到） | ? | clients=3 (panic后) |
| 190907Z | ? | ? | ✅ PID26 | 只有 RAM Data |

**关键差异：** 161209Z 看到了 backboardd57，但那次实验最终 panic。需要查看那次的完整日志对比。

## 结论

**C01 已完成**。阻塞点明确：cfprefsd 和 backboardd 没有启动。

**优先级最高的下一步：** 调查 launchd 配置和 Data 卷状态，确定这些守护进程为何未启动。无需新实验，先检查文件系统内容。
