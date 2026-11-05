# DarwinBoot连续内存窗口核查

2026-10-28。此轮为Android只读采集和主机区间分析，没有写RAM、探测MMIO或新增UEFI分配范围。

## 固定一手接口

DarwinBoot固定`3325e352d7df68a9f9ad74832ed94a6acbbd7390`。`DarwinBootPkg/Driver/WindowSize.h`要求窗口至少0x10000000（256MiB）、至多0x200000000，2MiB倍数；原`DarwinBoot.c`的默认值为SIZE_256MB、块对齐SIZE_2MB。真正分配还要求UEFI中有连续EfiConventionalMemory，并通过AllocateAddress成功。候选地址为align_up(run.start,2MiB)+(Mach-O虚拟基址低21位)，不能仅把run起点当内核物理基址。当前实际XNU Mach-O尚未选定，低21位未知。

固定MiCode`663db50e195a8a54c8565ac4ab0c6d9ba7d80db0`的`Documentation/arm64/booting.txt`第139–142行说明，描述给kernel且未reserved的内存会被kernel视为可用；第146行起要求quiesce所有DMA设备。这是Linux启动协议，不证明本机ABL完全遵守，也不能取代具体UEFI/外设生命周期。审计逐Git blob核对一手文件并记录精确行号、哈希。

## 本轮只读来源

`collect_memory_ownership.py`从root ADB读取FDT、/proc/iomem、/proc/meminfo、memblock/memory与reserved、CPU标识及可用的固件内存接口。记录每笔命令、退出码、原始字节和SHA-256；完整内容留在ignored私有目录。采集前后原boot哈希相等，Android完成、root正常且临时探针已清除。未改动原备份。

第一轮020950Z取到memblock后扩展CPU只读采集，完整第二轮为`evidence/private/memory-ownership/20261028T021216Z`。第二轮CPU MIDR读到0x51df805e；MMFR0/PFR0 sysfs不可用，EFI/memmap均不可用，不根据MIDR猜测PA宽度。FDT最大地址要求至少34位地址表示，这不是MMFR0实测值。

FDT描述8517582848字节，Linux memblock memory为8086261760字节，/proc/iomem的System RAM合并后与memblock完全一致；三者数量差异不当成丢失RAM或直接可用容量。

## 算法与结构候选

`audit_kernel_window.py`先交集FDT RAM、Linux memblock memory与iomem System RAM，再排除：全部FDT固定/header保留区、本轮Linux memblock reserved、RAM内有名资源、从本机XBL提取的全部MemoryMap声明、原Android initrd和现有诊断布局。原厂声明只作保守排除，未假设未列出的范围自动空闲。Linux动态池的alloc-ranges仍完整记录，没有把范围起点误当已分配地址。

| 结构剩余区间，右端不含 | 256MiB对齐示例 | 任意Mach-O低21位偏移均有容量余量 |
|---|---|---|
| 0xc0000000..0xed000000 | 0xc0000000..0xd0000000 | 是 |
| 0xffffffc0..0x1f8c00000 | 0x100000000..0x110000000 | 是 |
| 0x1fffffffe..0x280000000 | 0x200000000..0x210000000 | 是 |

这些地址由本轮数据和通用加载器约束计算，未使用其他板型配置。表中的示例尚未选为实际内核地址，也没有生成启用的PCD/HOB。

主机报告`kernel-window-audit.json`保存每项排除区的来源及原始采集哈希；`kernel-window-host.json`记录2104项区间/解析/对齐/越界检查，含256组独立离散集合模型，以及对真实候选逐项检查无保留区交叠。报告目录分别为`artifacts/kernel-window-audit/20261028T021613.877608Z-ksh3l3k_`与`artifacts/kernel-window-host/20261028T021746.087943Z-ga70q2x_`。

```sh
python3 scripts/collect_memory_ownership.py --serial <本机序列号>
python3 scripts/audit_kernel_window.py --collection evidence/private/memory-ownership/20261028T021216Z
python3 scripts/validate_kernel_window.py
```

## 下一步

在入口同轮重新解析FDT与保护区，读取CPU实际PA能力，设计默认关闭、严格限界的候选页只读/可恢复写探针，核对异常回传和原Android恢复后再扩展。随后才考虑把已授权的连续范围交给分配器与原DarwinBoot。Linux事后memblock、原厂静态表和参考ABL都不能单独证明入口全部RAM/DMA所有权。当前16MiB arena继续不满足256MiB请求；手机DarwinBoot/XNU仍未执行。
