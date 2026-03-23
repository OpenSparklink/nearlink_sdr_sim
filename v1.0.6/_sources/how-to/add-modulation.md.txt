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

示例测试结构:

:::{literalinclude} ../../examples/custom_modulation.py
:language: python
:start-after: "# [custom-test-start]"
:end-before: "# [custom-test-end]"
:::

### 3. 注册到 TX/RX 流水线

在 `phy/tx_pipeline.py` 的 `tx_chain()` 函数中, 根据 `cfg.frame_type` 分支添加新调制方式:

:::{literalinclude} ../../examples/custom_modulation.py
:language: python
:start-after: "# [custom-pipeline-start]"
:end-before: "# [custom-pipeline-end]"
:::

在 `phy/rx_pipeline.py` 的 `rx_chain()` 中添加对应的解调分支。如果新调制方式需要新的 MCS 配置, 还需更新 `common/mcs.py` 中的 MCS 映射表。

### 4. 运行验证

确保 lint 和测试全部通过:

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [lint-start]"
:end-before: "# [lint-end]"
:::

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [test-start]"
:end-before: "# [test-end]"
:::
