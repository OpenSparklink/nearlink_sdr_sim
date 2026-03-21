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


# [custom-test-start]
# tests/test_my_modulator.py

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
# [custom-test-end]


def _pipeline_example(cfg, gfsk_modulator, frame_bits, my_modulator, symbols):
    # [custom-pipeline-start]
    # tx_pipeline.py 中的调制分支
    if cfg.frame_type == 1:
        iq = gfsk_modulator.modulate(frame_bits)
    elif cfg.frame_type == 5:
        iq = my_modulator.modulate(symbols)
    # [custom-pipeline-end]
    return iq


if __name__ == "__main__":
    mod = MyModulator(sps=4)
    print(f"MyModulator created with sps={mod.sps}")
