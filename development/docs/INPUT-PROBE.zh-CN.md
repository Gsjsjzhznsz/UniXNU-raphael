# PM8150按键资源和只读仲裁器探针

日期：2026-10-28。默认关闭PcdRaphaelInputProbe。没有链接原厂闭源模块，也没有采用其他设备板级代码。

## 来源和范围

本次live FDT重新解析：音量上键linux code115，gpios指向PM8150 SPMI GPIO硬件号6、active-low、15ms debounce；不是TLMM。GPIO物理编号从1开始，地址由provider基址+(硬件号-1)*0x100推导，禁止按压缩后的逻辑pin编号计算。电源/音量下键分别为PON type0/code116与type1/code114，RT_STS偏移0x10。

固定MiCode提交663db50e195a8a54c8565ac4ab0c6d9ba7d80db0的一手驱动和绑定文件逐项哈希、行号见input-source-audit.json。SPMI区域来自FDT的reg-names，独立检查恒等总线、所有窗口边界、不重叠、EE/channel、provider和键绑定，在首次MMIO读取前完成。实际仲裁器version必须位于已审计v5区间，否则只读version后停止。

InputProbe.c只接受Read32回调：读取version、v5 APID映射表、非零映射的所有者配置。记录完整表，重复PPID优先当前EE匹配项，未匹配EE也只报告事实。没有访问observer command、PMIC寄存器或修改中断、复位、电源、时钟。读取PMIC今后需要向observer command写入命令，不能称其为完全无MMIO写入。

## 验证分层

主机执行实际C采集器，UBSan及输出guard检查，40项覆盖完整/重复映射、EE选择、版本拒绝、空表、错误FDT、越界和重叠；独立Python解码器复核全部wire字段和计数。所有模拟值明确仅为测试，不能当实机参数。

手机尚待本次nonce绑定stage2采样。保留SPMI互连已可访问是实验假设，可能同步异常或总线挂起。尚未采样任何PMIC按键状态，不能宣称按键成功。

```sh
python3 scripts/audit_input_sources.py
python3 scripts/validate_input_probe.py
python3 scripts/build_sec_dxe.py --stop-after-stage 2 --input-probe
python3 scripts/build_handset_sec_dxe.py --collection evidence/private/device/20261027T120325Z --stop-after-stage 2 --input-probe
```

## 只读实机结果

手机20261027T182056Z：nonce/stage2/status0通过，858次配置读取完整，硬件version=0x50000000，512项APID表。PON PPID0x008存在3项，当前EE0选择APID249；GPIO6 PPID0x0c5选择APID262；两者owner均0。所有地址/索引为本次观测，后续仍须同次重采样，不能硬编码。没有PMIC事务或按键成功结论。Android/root/原boot哈希审核通过。源码绑定和产物哈希见sec-input-source-binding.json；完整配置证据见boot-input-map-observation.json。
