# 2026-11-07 原生触摸开发

实机已出现原生你好欢迎页和日期/时钟锁屏；用户上滑无响应。目前镜像尚无原生Goodix/HID提供者，不能把锁屏当作图标桌面或交互通过。

固定Xiaomi raphael-p-oss 663db50e195a8a54c8565ac4ab0c6d9ba7d80db0描述GT9889位于SE19/I2C0x5d，GPIO54复位、122中断、98/100电源，坐标0..1079、0..2339。坐标寄存器来自匹配的私有Goodix配置文件，不能直接采用源码默认常量。

独立Normandy帧解码、分段读取和应答位于package/drivers/RaphaelGoodixProtocol.h。ASan/UBSan主机fixture覆盖按下/移动/抬起、ID重排、十触点、坏校验、越界及总线失败。当前尚未连接实机总线与原IOHIDFamily；仍须原生自动日志及最后真实滑动验证。构建通过不等于触摸可用。
