# 添加新的调制方式

本指南说明如何在 nearlink-sdr 框架中添加一种新的调制方式。

## 步骤

### 1. 在 `src/nearlink_sdr/phy/` 下创建模块

参照 `gfsk.py` 或 `psk.py` 的结构, 创建调制器和解调器类。每个调制器类至少实现 `modulate()` 方法, 解调器至少实现 `demodulate()` 方法:

```python
# src/nearlink_sdr/phy/my_mod.py
import numpy as np

class MyModulator:
    def __init__(self, sps: int = 8):
        self.sps = sps

    def modulate(self, bits: np.ndarray) -> np.ndarray:
        """将比特序列调制为复基带信号。"""
        ...

class MyDemodulator:
    def __init__(self, sps: int = 8):
        self.sps = sps

    def demodulate(self, signal: np.ndarray) -> np.ndarray:
        """将接收信号解调为比特序列。"""
        ...
```

### 2. 添加测试

在 `tests/` 下创建 `test_my_mod.py`, 至少覆盖:

- 调解调回环 (modulate then demodulate, verify lossless)
- 已知输入的输出验证
- 如有标准测试向量, 进行端到端匹配

### 3. 集成到仿真框架

在 `sim/link_sim.py` 中添加对应的仿真函数, 与 `sim_gfsk_link` / `sim_psk_link` 结构一致。

### 4. 验证

```bash
uv run ruff check src/ tests/
uv run pytest tests/ -v --tb=short
```

确保 lint 和全量测试通过。
