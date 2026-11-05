# C02 结论和下一步行动方案

**分析时间：** 2026-11-03  
**状态：** C02 初步完成，已识别根本原因

## 执行摘要

**核心发现：** cfprefsd 和 backboardd 没有启动是因为：

1. **cfprefsd** 配置为**按需启动（on-demand）的 XPC 服务**
   - `RunAtLoad=false`，不会在boot时自动启动
   - 等待第一个 mach消息/XPC连接才启动
   - **问题：** XPC框架可能无法正确响应SpringBoard的连接请求

2. **backboardd** 需要**GUI会话（SessionType=Aqua）**
   - 当前可能只有 console 会话
   - launchd跳过了不满足会话类型要求的服务
   - **问题：** 没有建立Aqua/GUI会话机制

## 详细分析

### 1. cfprefsd 的按需启动机制

**iOS/macOS标准行为：**
```
SpringBoard 启动
  ↓
调用 CFPreferencesGetAppBooleanValue() 等 API
  ↓
libCoreFoundation.dylib 尝试连接 XPC 服务 "com.apple.cfprefsd.user"
  ↓
发送 mach 消息到 bootstrap_look_up("com.apple.cfprefsd.user")
  ↓
launchd 收到消息，检查 MachServices 注册表
  ↓
找到 com.apple.cfprefsd.xpc.daemon.plist
  ↓
启动 /usr/sbin/cfprefsd
  ↓
cfprefsd check-in 并开始响应请求
```

**当前实际情况：**
```
SpringBoard 启动 ✓
  ↓
调用 CFPreferences API ✓
  ↓
尝试连接 XPC 服务 ✓（证据：栈上有 mach_msg2_trap）
  ↓
❌ launchd 没有响应？或者启动失败但无日志？
  ↓
SpringBoard 永远等待（当前状态）
```

**可能的失败点：**
- XPC子系统本身有问题
- launchd的 MachServices 注册表未正确加载plist
- cfprefsd二进制文件缺失或依赖库缺失
- cfprefsd启动了但立即崩溃（无日志）

### 2. backboardd 的会话类型要求

**标准配置：**
```xml
<key>SessionType</key>
<string>Aqua</string>
```

这要求：
- loginwindow或类似的会话管理器已启动
- 系统处于GUI模式，不是纯console模式
- 通常在用户登录后才建立Aqua会话

**当前系统状态：**
- 没有看到 loginwindow 或 SessionManager 启动
- SpringBoard直接启动，可能没有正确的会话上下文
- launchd可能认为当前是console会话，跳过了backboardd

### 3. 与已启动服务的对比

**成功启动的20+服务的共同特点：**
- `RunAtLoad=true` 或 `KeepAlive=true`
- 不要求特定 SessionType（或要求console）
- 不依赖复杂的XPC/mach服务发现

**未启动的服务：**
- cfprefsd：按需启动 + XPC
- backboardd：Aqua会话 + 可能的display依赖

## 建议的修复方案

### 方案A：最小化修复 - 强制启动 cfprefsd（推荐优先尝试）

**目标：** 让 cfprefsd 自动启动，避免按需启动的XPC问题

**实施：**
1. 在内核或早期启动代码中，显式启动 cfprefsd
2. 或在 launchd 配置中强制 `RunAtLoad=true`（如果可以修改plist）
3. 或创建一个 stub/wrapper 替代 cfprefsd

**优点：**
- 无需解决复杂的XPC机制
- SpringBoard可以继续

**缺点：**
- 不是根本修复（XPC仍然有问题）
- 可能影响其他按需服务

### 方案B：建立GUI会话机制

**目标：** 让 launchd 认为当前是Aqua会话，启动 backboardd

**实施：**
1. 研究 launchd 的会话类型检测机制
2. 在启动时设置环境变量或状态，声明为Aqua会话
3. 或修改 backboardd 的 plist，移除 SessionType 要求
4. 或创建一个轻量级的 loginwindow/SessionManager

**优点：**
- 更符合iOS标准架构
- 其他依赖GUI会话的服务也能启动

**缺点：**
- 需要更深入理解会话管理
- 可能需要修改多个组件

### 方案C：增强launchd日志和调试

**目标：** 确切了解为什么这些服务没启动

**实施：**
1. 在XNU的 `bsd/kern/kern_exec.c` 和 launchd相关代码添加printf
2. 记录每个plist的加载、条件检查、启动尝试
3. 记录XPC服务的注册和查找
4. 重新构建并运行

**优点：**
- 能确切知道失败原因
- 指导精确修复

**缺点：**
- 需要重新构建和测试
- 可能需要多轮迭代

### 方案D：参考UniXNU官方示例或社区

**目标：** 查看其他移植是否遇到相同问题

**实施：**
1. 检查 UniXNU 官方文档中关于 launchd/用户态的部分
2. 查看是否有示例项目展示完整的服务启动
3. 在社区/Discord询问

**优点：**
- 可能有现成方案
- 避免重复劳动

**缺点：**
- 可能没有直接答案（该项目可能还没人走到这一步）

## 立即行动计划（C03）

### C03.1：验证 cfprefsd 二进制和依赖

**无需新实验，文件系统检查：**
```bash
# 在挂载的SystemOS中检查
ls -la /usr/sbin/cfprefsd
file /usr/sbin/cfprefsd
otool -L /usr/sbin/cfprefsd  # 查看依赖库
```

### C03.2：尝试方案A.1 - 内核启动 cfprefsd

**需要代码修改：**
```c
// 在 bsd/kern/kern_exec.c 或 launchd 初始化后
// 添加显式启动逻辑
if (strcmp(name, "SpringBoard") == 0) {
    // 先启动 cfprefsd
    fork_and_exec("/usr/sbin/cfprefsd", "-f");
}
```

### C03.3：尝试方案A.2 - 修改 launchd plist

如果能访问和修改SystemOS镜像：
```xml
<!-- 修改 com.apple.cfprefsd.xpc.daemon.plist -->
<key>RunAtLoad</key>
<true/>  <!-- 改为true -->
```

### C03.4：尝试方案B - 设置 Aqua 会话

在 launchd 早期：
```c
// 伪代码
setenv("XPC_SESSION_TYPE", "Aqua");
// 或修改 launchd 内部会话检测逻辑
```

### C03.5：增强日志（并行）

在 bsd/kern/kern_exec.c 添加：
```c
printf("[exec] starting: %s (pid %d)\n", name, pid);
```

在 launchd 中（如果有源码访问）：
```c
printf("[launchd] loading plist: %s, RunAtLoad=%d, SessionType=%s\n", ...);
printf("[launchd] skipping %s: reason=%s\n", ...);
```

## 预期结果和验收标准

### C03 完成标准：

- [ ] **C03.1：验证文件存在** 
  - cfprefsd 和 backboardd 二进制存在
  - 依赖库都存在
  - 如果缺失，问题在文件系统准备

- [ ] **C03.2 或 C03.3：实施方案A**
  - cfprefsd 在启动日志中出现
  - SpringBoard 不再阻塞在 CFPreferences 等待
  - 无需立即解决XPC根本问题

- [ ] **C03.4：实施方案B（如果A不够）**
  - backboardd 在启动日志中出现
  - display_clients > 0

- [ ] **C03.5：增强日志**
  - 能看到每个服务的加载决策
  - 能看到XPC服务的注册过程

### 最终目标（C04-C06）：

- SpringBoard 解除阻塞
- backboardd 启动并连接显示
- `display_clients > 0, frames > 0`
- 达到 D01：首帧显示

## 风险评估

**方案A风险：** 低
- 即使失败，也只是增加一个进程
- 不影响现有功能

**方案B风险：** 中
- 可能影响其他服务的启动条件
- 需要仔细测试

**总体风险：** 低到中
- 最坏情况：这些修改无效，但不会破坏已有进展
- 有良好的回退路径（回到163215Z配置）

## 时间估计

- C03.1（验证文件）：1-2小时
- C03.2+C03.5（代码修改+日志）：2-4小时
- C03.3（plist修改，如果可行）：1-2小时
- 构建+测试循环：每次2-3小时
- 总计：1-2个工作日

## 成功指标

**短期（C03完成）：**
- cfprefsd 启动日志出现
- SpringBoard 继续执行，不再阻塞在CFPreferences

**中期（C04-C06）：**
- backboardd 启动
- display_clients从0变为非零

**长期（D01）：**
- 手机屏幕显示第一帧桌面
- 达到 "真实可见桌面" 里程碑
