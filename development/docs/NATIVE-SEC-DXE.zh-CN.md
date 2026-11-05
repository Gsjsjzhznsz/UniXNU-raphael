# 自有 UEFI 加载原生 XNU

2026-10-29，Asia/Shanghai。实现 `bd61c3a`；主线现已从自有 SEC/DXE、真实 Mu 分配器及只读 FAT，经原 UniXNU/DarwinBoot 进入 XNU。**本页所有 XNU 执行结果仅来自 QEMU，没有手机 XNU 执行结果、根卷挂载或用户态。**

## 载荷与内存

活动上游没有更新：UniXNU 40d21cc65171c3a24faa130a2a8e899f85790485，DarwinBoot 3325e352d7df68a9f9ad74832ed94a6acbbd7390，Mu cfb93724a06ff86ff5ba971413368a7809ee42a5。代码和原通用分配器、ReadFile、AllocateWindow 都保留。没有服务表分配函数 wrapper。

原生内核仍是冻结的18,463,480字节，SHA256 `96d31e6d36abed20e48f337cf01040d35db8eecfe1b446d20636664bc7b0d722`。未重新编译或修改内核字节。

`PcdRaphaelNativeBoot` 默认关闭。启用时，24MiB FV存入两份10MiB RAW，避免旧解析器不支持的24位扩展section/FFS长度；SEC验证两块普通header长度，先从arena顶部预留20MiB FAT backing，再启用MMU、拼接。通用只读RamDiskDxe/FAT、UniXNURun均实际执行。

48MiB arena是显式设计预算。顶部20MiB供SEC FAT使用，底部28MiB是带 `gEfiMemoryTypeInformationGuid` Owner 的独立资源，内含24MiB EfiBootServicesData首选bin及约4MiB其他类型预算。三个resource HOB互不重叠；没有在整段system-resource上叠加bin-resource。Mu固定源码的MemoryBin/Page.c决定实际分配，不替换通用分配服务。该布局取代了初步讨论中的44MiB bin：SEC先占20MiB后无法再申请连续44MiB。

258MiB内核窗口先隔离，完整生命周期成功后，在调用原UniXNUBootEntry前才释放。返回失败时要求重新保留整段。原loader仍分配256MiB EfiLoaderCode，并保留Mach-O低21位偏移0x4000。实际QEMU pa=0x60004000；这个地址来自同轮1GiB模拟器RAM中点，不能用于手机。

## 实际执行证据

验证提交 `bd61c3a`，独立复核 `artifacts/native-sec-dxe-verification/20261028T194101.408650Z-kp4qxaa_/report.json`；公共索引 `UniXNU-raphael/evidence/native-sec-dxe-verification.json`。

| 检查点 | 不可变QEMU run（UTC） | 结果 |
|---|---|---|
| 原生入口/arm_init首次接通 | 192850.576007Z-44nn2txb | 10段实际内存字节哈希一致，真实入口执行；后续里程碑以最终run为准 |
| 最终物理timer IRQ | 193742.103974Z-k89r7y52 | own SEC/DXE→原loader→CPU start→bsd_init→真实rtclock_intr和IRQ caller返回；timer/EOI=3/3，pthread status0/表非零 |
| 最终根设备查找入口 | 193742.103975Z-rx0lpobr | 到IOFindBSDRoot入口；不是找到根卷。较早停止时CPU start尚未返回，不能拿该轮当IRQ证据 |
| 兼容回归 | sec-dxe-qemu/193315.825621Z-681hu_qs | 原1MiB FAT、通用管理器、timer及Darwin无效输入拒绝，66项通过 |

最终两轮来自 `-kernel native-uefi.Image`，没有AAVMF、pflash或virtio ESP提供UEFI服务。硬件输入每轮由QEMU dumpdtb生成；cortex-a76、1GiB RAM、物理timer INTID30与62500000Hz均只属于模拟器。

QEMU专用 `PcdRaphaelNativeQemuGate` 默认关闭；builder拒绝手机scope开启。Semihost日志和调试等待仅用于QEMU。GDB先在preload gate观察原Mu AllocatePool真实调用/返回，确认18,463,480字节源缓冲区位于arena、在内核窗口外；FreePool调用前读取完整缓冲区并核对原内核SHA256。随后在真实ExitBootServices回调计数1后放行，逐10个段核对实际内存字节，检查EL1、DAIF全mask、MMU/cache关闭并执行原生入口。调试器仅写自有gate，不补丁内核或函数。

## 失败与边界

192727Z因缺MdeModulePkg声明失败，192744Z因PrePiHobLib缺WithOwner helper链接失败；改用标准CreateHob明确写Owner。192941Z与193135Z使用过小的QEMU `kt_fixed_zones=64`，实际触发kalloc.c:1387 remaining_zones断言，完整失败保留。最终使用此前已验证的显式模拟器预算200，保留原内核检查；手机分支没有这个override。

普通arena和FAT backing尚未在新布局中做手机验证。手机已验证的旧窗口分配合同仍是旧下载布局；不能将QEMU大FAT成功扩大为手机成功。没有把HOB TESTED标志或成功分配解释为完整物理内存/隐藏DMA所有权证明。

## 重现

```sh
python3 scripts/run_native_sec_dxe_qemu.py --stop-at timer_irq
python3 scripts/run_native_sec_dxe_qemu.py --stop-at find_root
python3 scripts/validate_native_sec_dxe_evidence.py --implementation bd61c3a \
  artifacts/native-sec-dxe-qemu/20261028T193742.103974Z-k89r7y52/report.json \
  artifacts/native-sec-dxe-qemu/20261028T193742.103975Z-rx0lpobr/report.json
```

下一步是独立小Image布局的手机分阶段验证、交接后诊断与本机ADT/CPU/PPI18，再尝试手机有效XNU交接。自动恢复接口的独立结果见[PSCI-RECOVERY.zh-CN.md](PSCI-RECOVERY.zh-CN.md)。RAM alias扩展继续暂停。
