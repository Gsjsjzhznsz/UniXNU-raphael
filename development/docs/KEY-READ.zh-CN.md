# 有界PMIC读取与按键寄存器诊断

日期：2026-10-28。默认关闭PcdRaphaelInputRead，依赖同次InputProbe和历史只读映射成功证据。所有APID与observer地址现场重建，绝不硬编码上次结果。

独立RaphaelKeysLib只实现EXT_READL单字节读取。SPMI observer CMD会发生MMIO写入，内容仅为read opcode；不实现PMIC寄存器写入、RW通道、WDATA、中断配置或复位控制。source audit固定MiCode接口语义，timeout采用一手驱动的1ms，额外100000次轮询上限是诊断设计预算。

读取GPIO6的type/subtype/mode/enable/RT_STS和PON RT_STS，共6笔。DONE且无FAILURE/DENIED/DROPPED才读取RDATA，逐笔回传完整事务。拒绝错版本、PPID/owner不符、越界通道，失败立即停止。有限采样不是实体按键响应或完整UEFI输入协议验证。

39项主机UBSan/guard测试覆盖精确命令、硬件错误、计时超时和停滞计时器上限、错误映射无写入、8种按键组合；数据均为模拟。物理按键语义仍需手机按压与状态变化交叉验证。

```sh
python3 scripts/audit_key_read_sources.py
python3 scripts/validate_key_read.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --input-probe --input-read
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --input-probe --input-read
```

实机待运行，不能把主机或QEMU成功视为PMIC访问成功。

## 六笔读取实机结果

20261027T183019Z nonce/stage2/status0通过，6笔observer EXT_READL均DONE=1、每笔2次轮询。GPIO type=0x10/subtype=0x11(MV)/mode=0/enable=0x80，确认为已启用的数字输入；GPIO RT_STS=1、PON RT_STS=4，相关三键位均未按下。只改observer命令寄存器，没有PMIC配置写入。Android/root/原boot哈希审核通过；源码和哈希见sec-keyread-source-binding.json。没有实体按压响应证据。
