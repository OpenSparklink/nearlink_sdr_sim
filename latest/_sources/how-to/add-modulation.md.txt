# 添加新的调制方式

本指南说明如何在 nearlink-sdr 框架中添加一种新的调制方式。

## 步骤

### 1. 在 `src/nearlink_sdr/phy/` 下创建模块

参照 `gfsk.py` 或 `psk.py` 的结构, 创建调制器和解调器类。每个调制器类至少实现 `modulate()` 方法, 解调器至少实现 `demodulate()` 方法:

:::{literalinclude} ../../examples/custom_modulation.py
:language: python
:start-after: "# [custom-mod-start]"
:end-before: "# [custom-mod-end]"
:::

### 2. 在 `tests/` 下创建对应的测试文件

测试文件命名为 `test_<模块名>.py`, 覆盖核心功能:

- 调制输出长度和类型
- 往返一致性 (调制 → 解调 → 比较)
- 不同输入长度的边界条件

### 3. 注册到 TX/RX 流水线

在 `phy/tx_pipeline.py` 和 `phy/rx_pipeline.py` 中添加新的帧类型映射, 使新调制方式可以集成到全链路流水线中。
