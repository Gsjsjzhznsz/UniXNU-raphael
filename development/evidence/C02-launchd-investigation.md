# C02 调查报告：launchd 配置和服务启动分析

**调查时间：** 2026-11-03  
**基于实验：** 20261102T163215Z

## 执行摘要

**发现：** launchd 成功启动了大约20个守护进程，但**cfprefsd 和 backboardd 完全没有尝试启动**，控制台中没有任何相关日志。

**可能原因：**
1. 这些服务的 launchd plist 配置中有条件限制（依赖项、GUI会话要求等）
2. 这些服务的 plist 文件不在已挂载的卷中
3. launchd 的配置加载路径有问题

## 详细分析

### 1. 成功启动的守护进程（约20个）

从第395-400行的日志可见，launchd 成功启动了：

**核心系统服务：**
- launchd (PID 1) - init进程
- watchdogd (52) - 看门狗
- logd (25) - 日志服务
- configd (37) - 配置守护进程 ✓（在services列表中）
- keybagd (45) - 密钥管理 ✓（在services列表中）

**通知和事件：**
- notifyd (87) - 系统通知
- distnoted (86) - 分布式通知  
- UserEventAgent (24) - 用户事件

**媒体和时间：**
- mediaserverd (29) - 媒体服务
- timed (59) - 时间同步
- mobiletimerd (50) - 移动定时器

**安全和容器：**
- amfid (47) - AMFI守护进程
- containermanagerd (64) - 容器管理
- AppleCredentialManagerDaemon (75) - 凭证管理

**文件系统和硬件：**
- fseventsd (84) - 文件系统事件
- driverkitd (66) - 驱动程序管理

**其他：**
- remoted (44), DumpPanic (48), thermalmonitord (55), sleepd (68), ptpd (69), rapportd (78), mtmergeprops (79), logd_helper (89)

### 2. 缺失的关键服务

**完全没有出现在日志中：**
- ❌ cfprefsd - CoreFoundation配置守护进程
- ❌ backboardd - 显示和输入管理守护进程
- ❌ frontboardd - 应用程序生命周期管理（如果iOS 17有）

**重要性：**
- 没有 cfprefsd，任何应用程序调用 CFPreferences API 都会阻塞
- 没有 backboardd，显示和输入管理无法工作，没有window server

### 3. 可能的原因分析

#### 原因A：launchd plist 配置条件不满足

iOS/Darwin 的 launchd plist 可以包含启动条件：

```xml
<key>UserName</key>
<string>mobile</string>  <!-- 需要特定用户 -->

<key>SessionType</key>
<string>Aqua</string>  <!-- 需要GUI会话 -->

<key>RunAtLoad</key>
<false/>  <!-- 不自动启动，需要按需启动 -->

<key>KeepAlive</key>
<dict>
  <key>PathState</key>
  <dict>
    <key>/var/run/some.socket</key>
    <true/>  <!-- 需要某个socket存在 -->
  </dict>
</dict>
```

**可能情况：**
- cfprefsd 的 plist 可能要求 `RunAtLoad=false`，等待XPC连接时才按需启动
- backboardd 可能要求 `SessionType=Aqua`（GUI会话），但当前只是console会话

#### 原因B：Data 卷路径问题

虽然 `RaphaelScratchData` 挂载成功，但：
- 这是一个**临时1GB RAM盘**（从HANDOFF可知）
- 真实的用户 Data 可能需要更复杂的解锁流程
- cfprefsd 需要访问 `/var/mobile/Library/Preferences/`，这个路径可能不存在或为空

**证据：**
```
[  403.105465]: /private/var/mobile/tmp already exists, skipping
```
这说明基本的 `/var/mobile/` 结构存在，但不能保证 Library/Preferences 存在。

#### 原因C：依赖链问题

可能的依赖链：
1. backboardd 依赖 cfprefsd（读取配置）
2. cfprefsd 作为XPC服务，可能依赖某个已启动的XPC框架服务
3. 两者都可能依赖 "LoginWindow" 或类似的会话管理器

**观察：**
- SpringBoard(27) 启动了，说明launchd尝试启动UI相关进程
- 但 SpringBoard 立即阻塞在等待 cfprefsd
- 如果 cfprefsd 依赖 backboardd，或反之，就形成死锁

#### 原因D：AMFI Launch Constraint

第356行：
```
AMFI: Launch Constraint Violation (not enforcing), error info: c[6]p[2]m[3]e[255], 
(Process was launched as a system service unexpectedly but met System Service constraints) 
launching proc[vc: 1 pid: 23]: /usr/libexec/init_exclavekit, launch type 1, 
failure proc [vc: 1 pid: 1]: /sbin/launchd
```

虽然是 "not enforcing"，但这说明 AMFI 在检查启动约束。**可能 cfprefsd/backboardd 的启动约束更严格，被AMFI拒绝了，但没有产生日志**。

### 4. iOS/macOS 标准行为对比

**正常 iOS 启动顺序：**
1. launchd 启动
2. 早期系统服务启动（configd, logd等）
3. **cfprefsd.system** 自动启动（系统级配置）
4. **cfprefsd.xpc.daemon** 注册XPC服务
5. **backboardd** 启动（如果有显示硬件和GUI会话）
6. **SpringBoard** 启动并连接到 backboardd 和 cfprefsd
7. SpringBoard 显示UI

**当前实际：**
1. launchd 启动 ✓
2. 早期系统服务启动 ✓
3. cfprefsd - **完全没启动** ❌
4. backboardd - **完全没启动** ❌  
5. SpringBoard 启动 ✓ 但立即阻塞 ⚠️

## 下一步调查方向

### 方案1：检查 launchd plist 文件（最优先）

**需要做：**
1. 列出 SystemOS 镜像中的所有 LaunchDaemons plist
2. 确认是否存在：
   - `/System/Library/LaunchDaemons/com.apple.cfprefsd.*.plist`
   - `/System/Library/LaunchDaemons/com.apple.backboardd.plist`
3. 解析这些 plist，检查启动条件：
   - `RunAtLoad`
   - `KeepAlive`
   - `SessionType`
   - `UserName`
   - `PathState` 依赖
   - `MachServices` XPC服务名称

**工具：**
- 使用 `hdiutil` 或 `7z` 挂载/解压 DMG
- 或从已构建的 payload 中提取
- Python plistlib 解析

### 方案2：检查 launchd 日志级别

当前控制台可能没有显示launchd的详细日志。需要：
1. 检查是否有 boot-arg 可以启用 launchd 详细日志
2. 查看是否有 `/var/log/launchd.log` 或类似文件（需要Data卷持久化）
3. 在内核中添加更详细的 exec/spawn 跟踪

### 方案3：手动启动测试

如果能进入shell（未来改进），尝试：
```bash
# 测试二进制是否存在
ls -la /usr/sbin/cfprefsd
ls -la /usr/libexec/backboardd

# 查看动态库依赖
otool -L /usr/sbin/cfprefsd

# 尝试手动启动
/usr/sbin/cfprefsd -f  # 前台运行看错误
```

### 方案4：对比完整 iOS 系统

获取一个真实 iPad/iPhone 的：
- `launchctl list` 输出（所有已加载的服务）
- `/System/Library/LaunchDaemons/` 完整列表
- cfprefsd 和 backboardd 的确切启动时机和依赖

### 方案5：简化方案 - 绕过 cfprefsd（实验性）

**如果问题太复杂，临时绕过：**
1. 修改 SpringBoard 或提供一个stub cfprefsd
2. 返回默认配置，避免IPC阻塞
3. 优先让 backboardd 启动，验证显示管道

**风险：** 这会破坏很多功能，但可以验证显示路径是否工作。

## 建议的立即行动

### C02 完成标准（修订）

- [ ] **C02.1: 提取并列出 SystemOS 中的所有 LaunchDaemons plist**
  - 使用 `hdiutil`、`7z` 或 APFS 工具挂载 044-76034-038.dmg
  - 列出 `/System/Library/LaunchDaemons/` 所有文件
  - 确认 cfprefsd 和 backboardd 的 plist 是否存在
  - **无需新实验，文件系统操作**

- [ ] **C02.2: 解析关键 plist 的启动条件**
  - 如果存在，解析 cfprefsd 和 backboardd 的 plist
  - 识别所有启动条件和依赖项
  - 对比已启动的服务，找出差异
  - **无需新实验，静态分析**

- [ ] **C02.3: 制定修复方案**
  - 基于 C02.1 和 C02.2 的结果
  - 确定是修改 plist、添加依赖项，还是修改启动序列
  - 评估是否需要更完整的 Data 卷或会话管理
  - **输出：具体的代码/配置修改计划**

## 临时结论

launchd 本身工作正常（成功启动了20+服务），但 cfprefsd 和 backboardd **根本没被尝试启动**。

最可能的原因是：
1. **按需启动（On-demand）**：cfprefsd 配置为 XPC 服务，等待连接时才启动，但 XPC 基础设施可能有问题
2. **会话要求**：backboardd 需要 GUI 会话，但当前只有 console 会话
3. **plist 缺失**：这些服务的配置文件可能不在标准路径

**优先级：C02.1 - 必须先确认 plist 文件是否存在**。如果不存在，问题在 SystemOS 镜像准备；如果存在，问题在启动条件。
