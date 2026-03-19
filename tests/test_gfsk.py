import numpy as np

from nearlink_sdr.phy.gfsk import GFSKDemodulator, GFSKModulator


class TestGFSK:
    def test_modulator_output_length(self):
        mod = GFSKModulator(sps=8)
        bits = np.array([1, 0, 1, 1, 0], dtype=int)
        signal = mod.modulate(bits)
        assert len(signal) == len(bits) * 8

    def test_modulator_output_is_complex(self):
        mod = GFSKModulator(sps=8)
        bits = np.array([0, 1, 0], dtype=int)
        signal = mod.modulate(bits)
        assert np.iscomplexobj(signal)

    def test_modulator_constant_envelope(self):
        """GFSK是恒包络调制，信号幅度应恒为1"""
        mod = GFSKModulator(sps=8)
        bits = np.array([1, 0, 1, 0, 1, 1, 0, 0], dtype=int)
        signal = mod.modulate(bits)
        np.testing.assert_allclose(np.abs(signal), 1.0, atol=1e-10)

    def test_roundtrip_no_noise(self):
        """无噪声环境下GFSK调制解调的逆运算"""
        mod = GFSKModulator(sps=8, mod_index=0.5)
        demod = GFSKDemodulator(sps=8)
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, 100)
        signal = mod.modulate(bits)
        rx_bits = demod.demodulate(signal)
        # 允许首尾少量比特由于高斯滤波器截断导致误差
        valid = min(len(bits), len(rx_bits))
        margin = 3  # 高斯滤波器拖尾
        errors = np.sum(bits[margin:valid-margin] != rx_bits[margin:valid-margin])
        assert errors == 0, f"无噪声下解调错误 {errors} 比特"

    def test_roundtrip_high_snr(self):
        """高信噪比下GFSK误码率应极低"""
        mod = GFSKModulator(sps=8, mod_index=0.5)
        demod = GFSKDemodulator(sps=8)
        rng = np.random.default_rng(7)
        bits = rng.integers(0, 2, 500)
        signal = mod.modulate(bits)
        # 添加少量噪声 (SNR ~20dB)
        noise_power = 0.01
        noise = np.sqrt(noise_power / 2) * (rng.standard_normal(len(signal)) +
                                              1j * rng.standard_normal(len(signal)))
        rx_signal = signal + noise
        rx_bits = demod.demodulate(rx_signal)
        valid = min(len(bits), len(rx_bits))
        margin = 3
        ber = np.sum(bits[margin:valid-margin] != rx_bits[margin:valid-margin]) / (valid - 2*margin)
        assert ber < 0.01, f"高信噪比下BER={ber}过高"

    def test_mod_index_range(self):
        """标准要求调制系数在0.45~0.55之间"""
        for h in [0.45, 0.50, 0.55]:
            mod = GFSKModulator(sps=8, mod_index=h)
            bits = np.array([1, 0, 1, 0], dtype=int)
            signal = mod.modulate(bits)
            assert len(signal) == 32

    def test_all_zeros(self):
        mod = GFSKModulator(sps=8)
        demod = GFSKDemodulator(sps=8)
        bits = np.zeros(20, dtype=int)
        signal = mod.modulate(bits)
        rx_bits = demod.demodulate(signal)
        valid = min(len(bits), len(rx_bits))
        margin = 3
        np.testing.assert_array_equal(rx_bits[margin:valid-margin], bits[margin:valid-margin])

    def test_all_ones(self):
        mod = GFSKModulator(sps=8)
        demod = GFSKDemodulator(sps=8)
        bits = np.ones(20, dtype=int)
        signal = mod.modulate(bits)
        rx_bits = demod.demodulate(signal)
        valid = min(len(bits), len(rx_bits))
        margin = 3
        np.testing.assert_array_equal(rx_bits[margin:valid-margin], bits[margin:valid-margin])
