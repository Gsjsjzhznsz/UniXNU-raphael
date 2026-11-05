# 继承启动显示的实验性 GOP

日期：2026-10-28。默认关闭PcdRaphaelExperimentalGop，且只能与display/smmu/pixel只读探针同时显式启用；不能与SEC像素写入实验混用。生产memory-plan仍禁用。

## 实现和参数来源

全部物理起点、宽高、stride、extent来自同次入口的本机FDT与只读寄存器采集。新增GopRoute.c仅检查已采集的记录，不增加MMIO访问；核对唯一VIG0→CTL→LM非base stage→PP→DSI、尺寸、无DSC、TE/autorefresh与不依赖像素alpha的255/0混合。未硬编码其他手机的板级地址。

RaphaelFramebufferLib检查样本完整性、布局和页对齐后的范围，拒绝与诊断Image扩展区重叠。SEC将页取整framebuffer加入normal non-cacheable映射，并发布reserved资源与EfiReservedMemoryType分配HOB；该区域不进入DXE堆。MMU开启后比对首末两个已采样像素，单独记录mapped_read_verified。

SplashGopDxe只发布继承的单模式BGR Reserved GOP和软件vendor device path。QueryMode分配返回独立Info，SetMode(0)按接口清空可见区域，不改变面板时序、时钟或刷新寄存器；本阶段实机测试不调用SetMode(0)，其清屏只通过主机验证。Blt填充/读写复用固定Basecore FrameBufferBltLib；固定版的向下视频重叠复制从Height而非Height-1开始，封装采用正确行序和overlap-safe CopyMem，通用上游源码保持固定未改。

保留字节不作为alpha使用。主机测试发现通用Fill只保证RGB并丢弃Reserved，诊断据此按RGB验白；BufferToVideo和VideoToBuffer仍逐字验证及恢复全部原值。

## 诊断与恢复

DXE测试QueryMode、无效模式拒绝、四种Blt操作、实际重叠复制和逐字回读。先备份左上256×128，再绘制10秒白框RGB，恢复全部32768个原值并逐字比较。backup位于诊断arena的Pool；直到Active清除前保持有效。异常/失败路径在映射仍存在时由SEC恢复helper尝试恢复；总线挂死或恢复访问自身异常仍不能保证自动恢复。

26个UINT64的独立GOP回传记录不改变原48字段SEC ABI。stage2只验证现场门禁和布局，stage3验证MMU后的访问，stage6才验证协议与Blt；人眼可见性继续独立记录。内存图中framebuffer保留范围允许在arena外，所有可分配内存仍必须严格位于arena内。

## 验证分层

- 主机：实际端口Gop.c、Framebuffer.c与固定通用Blt库，ASan/UBSan下38项通过；包括边界、padding、向上/下/水平重叠、无效请求不写入、SetMode清屏和异常恢复helper。
- 主机路由：实际GopRoute.c使用本机nonce绑定快照作为fixture，21项通过；模拟修改alpha、路由、尺寸、DSC、刷新等均拒绝。
- 主机构建/FD检查和QEMU：stage2/3各20项，stage4正常路径25项和注入BRK恢复22项通过；QEMU缺少本机硬件时验证不映射framebuffer、不装GOP，不能视为正向显示测试。
- 实机：同源码stage2/3/6依次通过。stage6新GOP协议、QueryMode、无效模式拒绝、四种Blt与重叠复制通过；32768原像素全部恢复、差异0。用户针对20261027T175959Z明确反馈“看到了色块”。Android/root/原boot哈希与正常重启清理均通过。

```sh
python3 scripts/validate_gop.py
python3 scripts/validate_gop_route.py
python3 scripts/audit_gop_sources.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --display-probe --smmu-probe --pixel-probe --experimental-gop
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --display-probe --smmu-probe --pixel-probe --experimental-gop
```

后续同源码依次重测stage2、3、6；每次保留FD/私有boot哈希、nonce回传和正常Android恢复。原备份及私有固件不公开。

## 精确版本及实机证据

固件包源码提交`38fe398612c029f1b032c9f27b89b082943354ba`，每个构建全部39项包内输入与该Git版本逐一匹配，QEMU输入完全一致。绑定见`sec-gop-source-binding.json`；软件回传见`sec-gop-stage2/3/6-handoff.json`；人眼观察独立见`boot-gop-observation.json`；清理见`sec-gop-cleanup.json`。

| 阶段 | 私有构建 UTC | FD SHA-256 | boot SHA-256 |
|---|---|---|---|
| 2 | 20261027T174926Z | `f31ec0003d0907f9af9dde0c194a3a7ee2a675b56ab658d673ec0b1320fbe212` | `6367190a4c43be4f294ad61a5e4f84fd39ecc75d8b6b0d4d87fe37a987eca144` |
| 3 | 20261027T175302Z | `5122b0ced44fd293c1f6aa9cc54f8f05f74654e3e7233f920f41b49928059366` | `ef8bb22a85706131a6300439941f2163d25bcc56fbb40701d68d7cbcc448a9a1` |
| 6 | 20261027T175752Z | `3abc8e8d362ca701cfc55a6cd07dbc86b939bd762c111b47229ffb316e047c47` | `f2e7cd4ffd828fae24399798b1fc37eb85b0c43813f646ed21caa0c3d6065aad` |

本次18项内存描述均满足边界检查，framebuffer为单独保留的NC范围，未进入堆。只证明当前继承模式下的有限读写与可见输出；没有面板重初始化、SetMode(0)实机或完整内存所有权结论。下一步输入资源审计、菜单与按键。
