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

```python
import numpy as np
from nearlink_sdr.phy.my_modulator import MyModulator, MyDemodulator

class TestMyModulator:
    def test_roundtrip(self):
        """调制→解调往返一致性"""
        mod = MyModulator(sps=4)
        demod = MyDemodulator(sps=4)
        bits = np.array([1, 0, 1, 1, 0, 0], dtype=int)
        iq = mod.modulate(bits)
        rx_bits = demod.demodulate(iq)
        np.testing.assert_array_equal(bits, rx_bits[:len(bits)])

    def test_output_length(self):
        """调制输出长度 = 输入比特数 × 每符号采样数"""
        mod = MyModulator(sps=4)
        bits = np.ones(20, dtype=int)
        iq = mod.modulate(bits)
        assert len(iq) == 20 * 4
```

### 3. 注册到 TX/RX 流水线

在 `phy/tx_pipeline.py` 的 `tx_chain()` 函数中, 根据 `cfg.frame_type` 分支添加新调制方式:

```python
# tx_pipeline.py 中的调制分支
if cfg.frame_type == 1:
    iq = gfsk_modulator.modulate(frame_bits)
elif cfg.frame_type == 5:  # 新帧类型
    iq = my_modulator.modulate(symbols)
```

在 `phy/rx_pipeline.py` 的 `rx_chain()` 中添加对应的解调分支。如果新调制方式需要新的 MCS 配置, 还需更新 `common/mcs.py` 中的 MCS 映射表。

### 4. 运行验证

确保 lint 和测试全部通过:

```bash
uv run ruff check src/ tests/
uv run pytest tests/test_my_modulator.py -v
uv run pytest tests/ -q        # 全量回归
```
