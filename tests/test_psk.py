import numpy as np
import pytest
from nearlink_sdr.phy.psk import PSKModulator, PSKDemodulator, rrc_filter, SLE_RRC_BETA


class TestRRCFilter:
    def test_filter_symmetry(self):
        h = rrc_filter(0.4, 4, 10)
        np.testing.assert_allclose(h, h[::-1], atol=1e-12)

    def test_matched_filter_isi_free(self):
        """RRC匹配滤波后应为RC脉冲，采样点处ISI为零"""
        sps = 8
        h = rrc_filter(0.4, sps, 10)
        rc = np.convolve(h, h)  # RC脉冲
        center = len(rc) // 2
        # 在符号间隔的整数倍处，主峰外的采样值应接近零
        for k in range(-5, 6):
            if k == 0:
                continue
            idx = center + k * sps
            if 0 <= idx < len(rc):
                assert abs(rc[idx]) < 1e-3, f"ISI at k={k}: {rc[idx]}"


class TestPSKModulator:
    @pytest.mark.parametrize("mod_type,bps", [
        ("BPSK", 1), ("QPSK", 2), ("8PSK", 3), ("BPSK_NOROT", 1)
    ])
    def test_bits_per_symbol(self, mod_type, bps):
        mod = PSKModulator(mod_type=mod_type)
        assert mod.bits_per_symbol == bps

    def test_qpsk_output_length(self):
        mod = PSKModulator(mod_type="QPSK", sps=4, rrc_span=3)
        bits = np.array([0, 0, 1, 0, 1, 1, 0, 1] * 10, dtype=int)
        signal = mod.modulate(bits)
        # mode='same' 返回 max(upsampled_len, filter_len)
        n_symbols = len(bits) // 2
        upsampled_len = n_symbols * 4
        assert len(signal) == max(upsampled_len, len(mod._rrc))

    def test_bpsk_constellation(self):
        mod = PSKModulator(mod_type="BPSK")
        # 比特0 -> 90度 (j)
        symbols = mod.map_symbols(np.array([0]))
        np.testing.assert_allclose(symbols[0], 1j, atol=1e-10)
        # 比特1 -> -90度 (-j)
        symbols = mod.map_symbols(np.array([1]))
        np.testing.assert_allclose(symbols[0], -1j, atol=1e-10)

    def test_qpsk_constellation(self):
        mod = PSKModulator(mod_type="QPSK")
        # 00 -> 45度
        symbols = mod.map_symbols(np.array([0, 0]))
        expected = np.exp(1j * np.pi / 4)
        np.testing.assert_allclose(symbols[0], expected, atol=1e-10)

    def test_bpsk_norot_constellation(self):
        mod = PSKModulator(mod_type="BPSK_NOROT")
        symbols = mod.map_symbols(np.array([0]))
        np.testing.assert_allclose(symbols[0], 1.0 + 0j, atol=1e-10)
        symbols = mod.map_symbols(np.array([1]))
        np.testing.assert_allclose(symbols[0], -1.0 + 0j, atol=1e-10)


class TestPSKRoundtrip:
    @pytest.mark.parametrize("mod_type", ["BPSK", "QPSK", "8PSK", "BPSK_NOROT"])
    def test_roundtrip_no_noise(self, mod_type):
        sps = 8
        mod = PSKModulator(mod_type=mod_type, sps=sps)
        demod = PSKDemodulator(mod_type=mod_type, sps=sps)
        rng = np.random.default_rng(42)
        bps = mod.bits_per_symbol
        n_bits = bps * 100
        bits = rng.integers(0, 2, n_bits)
        signal = mod.modulate(bits)
        rx_bits = demod.demodulate(signal)
        # 跳过RRC收敛期
        margin = bps * 5
        valid = min(len(bits), len(rx_bits))
        errors = np.sum(bits[margin:valid-margin] != rx_bits[margin:valid-margin])
        assert errors == 0, f"{mod_type} 无噪声下 {errors} 比特错误"

    def test_qpsk_high_snr(self):
        sps = 8
        mod = PSKModulator(mod_type="QPSK", sps=sps)
        demod = PSKDemodulator(mod_type="QPSK", sps=sps)
        rng = np.random.default_rng(7)
        bits = rng.integers(0, 2, 500)
        if len(bits) % 2:
            bits = bits[:-1]
        signal = mod.modulate(bits)
        noise_power = 0.001
        noise = np.sqrt(noise_power / 2) * (
            rng.standard_normal(len(signal)) + 1j * rng.standard_normal(len(signal)))
        rx_bits = demod.demodulate(signal + noise)
        margin = 10
        valid = min(len(bits), len(rx_bits))
        ber = np.sum(bits[margin:valid-margin] != rx_bits[margin:valid-margin]) / (valid - 2 * margin)
        assert ber < 0.01, f"QPSK高SNR下BER={ber}"
