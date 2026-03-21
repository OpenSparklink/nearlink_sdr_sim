"""添加自定义调制方式的模板。

对应文档: how-to/add-modulation.md
"""

import numpy as np

# [custom-mod-start]
# src/nearlink_sdr/phy/my_mod.py

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
# [custom-mod-end]


if __name__ == "__main__":
    mod = MyModulator(sps=4)
    print(f"MyModulator created with sps={mod.sps}")
