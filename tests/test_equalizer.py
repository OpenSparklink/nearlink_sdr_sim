"""Tests for equalizer: ZF / MMSE frequency domain, time domain, 1-tap."""

import numpy as np
import pytest

from nearlink_sdr.phy.equalizer import (
    equalize_1tap,
    equalize_mmse_freq,
    equalize_mmse_time,
    equalize_zf,
    estimate_channel_freq,
)


class TestFrequencyDomainZF:
    """ZF 频域均衡测试。"""

    def test_identity_channel(self):
        """全通信道下均衡输出等于输入。"""
        sig = np.array([1, 0, 1, 0, 1, 1, 0, 1], dtype=complex)
        h_freq = np.ones(len(sig), dtype=complex)
        out = equalize_zf(sig, h_freq)
        assert np.allclose(out, sig, atol=1e-10)

    def test_known_channel(self):
        """已知信道 H(f) 下 ZF 恢复原始信号。"""
        rng = np.random.default_rng(42)
        tx = rng.standard_normal(64) + 1j * rng.standard_normal(64)
        # 简单 2 抽头信道
        h = np.array([1.0, 0.5], dtype=complex)
        h_freq = np.fft.fft(h, 64)
        rx = np.fft.ifft(np.fft.fft(tx, 64) * h_freq, 64)
        eq = equalize_zf(rx, h_freq)
        assert np.allclose(eq, tx, atol=1e-8)

    def test_output_length(self):
        sig = np.ones(32, dtype=complex)
        h_freq = np.ones(32, dtype=complex) * 2.0
        out = equalize_zf(sig, h_freq)
        assert len(out) == 32


class TestFrequencyDomainMMSE:
    """MMSE 频域均衡测试。"""

    def test_identity_channel(self):
        sig = np.array([1, -1, 1, -1], dtype=complex)
        h_freq = np.ones(4, dtype=complex)
        out = equalize_mmse_freq(sig, h_freq, noise_var=0.0001)
        assert np.allclose(out, sig, atol=0.01)

    def test_known_channel_low_noise(self):
        """低噪声下 MMSE 接近 ZF。"""
        rng = np.random.default_rng(42)
        tx = rng.standard_normal(64) + 1j * rng.standard_normal(64)
        h = np.array([1.0, 0.3, 0.1], dtype=complex)
        h_freq = np.fft.fft(h, 64)
        rx = np.fft.ifft(np.fft.fft(tx, 64) * h_freq, 64)
        eq = equalize_mmse_freq(rx, h_freq, noise_var=1e-8)
        assert np.allclose(eq, tx, atol=1e-4)

    def test_mmse_better_than_zf_with_noise(self):
        """有噪声时 MMSE 的 MSE 应低于或等于 ZF。"""
        rng = np.random.default_rng(42)
        n = 128
        tx = (rng.integers(0, 2, n) * 2 - 1).astype(complex)
        h = np.array([1.0, 0.5], dtype=complex)
        h_freq = np.fft.fft(h, n)
        rx_clean = np.fft.ifft(np.fft.fft(tx, n) * h_freq, n)
        noise = 0.1 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        rx = rx_clean + noise

        eq_zf = equalize_zf(rx, h_freq)
        eq_mmse = equalize_mmse_freq(rx, h_freq, noise_var=0.01)

        mse_zf = np.mean(np.abs(eq_zf - tx) ** 2)
        mse_mmse = np.mean(np.abs(eq_mmse - tx) ** 2)
        assert mse_mmse <= mse_zf * 1.1  # MMSE 应至少不比 ZF 差太多


class TestChannelEstimation:
    """LS 信道估计测试。"""

    def test_known_channel(self):
        """用已知训练序列估计信道。"""
        rng = np.random.default_rng(42)
        n = 64
        tx_train = rng.standard_normal(n) + 1j * rng.standard_normal(n)
        h = np.array([1.0, 0.5, 0.2], dtype=complex)
        h_freq_true = np.fft.fft(h, n)
        rx_train = np.fft.ifft(np.fft.fft(tx_train, n) * h_freq_true, n)

        h_est = estimate_channel_freq(rx_train, tx_train, n)
        assert np.allclose(h_est, h_freq_true, atol=1e-8)

    def test_estimation_with_noise(self):
        """有噪声的信道估计应仍然合理。"""
        rng = np.random.default_rng(42)
        n = 64
        tx_train = np.exp(1j * rng.uniform(0, 2 * np.pi, n))
        h = np.array([1.0, 0.3], dtype=complex)
        h_freq_true = np.fft.fft(h, n)
        rx_clean = np.fft.ifft(np.fft.fft(tx_train, n) * h_freq_true, n)
        noise = 0.01 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        rx = rx_clean + noise

        h_est = estimate_channel_freq(rx, tx_train, n)
        mse = np.mean(np.abs(h_est - h_freq_true) ** 2)
        assert mse < 0.01


class TestTimeDomainMMSE:
    """MMSE 时域均衡器测试。"""

    def test_identity_channel(self):
        """无 ISI 信道 h=[1] 下均衡器应接近通过。"""
        rng = np.random.default_rng(42)
        tx = (rng.integers(0, 2, 100) * 2 - 1).astype(complex)
        h = np.array([1.0])
        eq = equalize_mmse_time(tx, h, noise_var=1e-6, n_taps_eq=5)
        # 允许边沿效应
        mid = slice(10, 90)
        assert np.allclose(np.sign(np.real(eq[mid])), np.real(tx[mid]), atol=0.5)

    def test_two_tap_channel(self):
        """2 抽头信道下 MMSE 均衡器应降低 ISI。"""
        rng = np.random.default_rng(42)
        n = 200
        tx = (rng.integers(0, 2, n) * 2 - 1).astype(complex)
        h = np.array([1.0, 0.5])
        rx = np.convolve(tx, h, mode='same')
        noise = 0.01 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        rx += noise

        eq = equalize_mmse_time(rx, h, noise_var=0.0001, n_taps_eq=11)
        # 比较中间部分的硬判决
        mid = slice(20, 180)
        decisions = np.sign(np.real(eq[mid]))
        errors = np.sum(decisions != np.real(tx[mid]))
        ber = errors / len(tx[mid])
        assert ber < 0.05  # BER 应该很低

    def test_output_length(self):
        tx = np.ones(50, dtype=complex)
        h = np.array([1.0, 0.3, 0.1])
        eq = equalize_mmse_time(tx, h, noise_var=0.01, n_taps_eq=7)
        assert len(eq) == 50


class TestOneTapEqualizer:
    """1-tap 逐符号均衡测试。"""

    def test_zf_perfect_channel(self):
        tx = np.array([1 + 1j, -1 + 1j, 1 - 1j, -1 - 1j]) / np.sqrt(2)
        h = np.array([0.8 + 0.3j, 0.8 + 0.3j, 0.8 + 0.3j, 0.8 + 0.3j])
        rx = tx * h
        eq = equalize_1tap(rx, h, method="zf")
        assert np.allclose(eq, tx, atol=1e-10)

    def test_mmse_perfect_channel(self):
        tx = np.array([1, -1, 1, -1], dtype=complex)
        h = np.full(4, 0.7 + 0.5j)
        rx = tx * h
        eq = equalize_1tap(rx, h, noise_var=1e-6, method="mmse")
        # MMSE 应接近 ZF (低噪声)
        assert np.allclose(np.sign(np.real(eq)), np.real(tx))

    def test_zf_varying_channel(self):
        rng = np.random.default_rng(42)
        n = 100
        tx = (rng.integers(0, 2, n) * 2 - 1).astype(complex)
        h = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
        rx = tx * h
        eq = equalize_1tap(rx, h, method="zf")
        assert np.allclose(eq, tx, atol=1e-8)

    def test_mmse_with_noise(self):
        rng = np.random.default_rng(42)
        n = 200
        tx = (rng.integers(0, 2, n) * 2 - 1).astype(complex)
        h = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
        rx = tx * h + 0.1 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        eq = equalize_1tap(rx, h, noise_var=0.01, method="mmse")
        decisions = np.sign(np.real(eq))
        errors = np.sum(decisions != np.real(tx))
        ber = errors / n
        assert ber < 0.1

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            equalize_1tap(np.ones(5, dtype=complex), np.ones(5, dtype=complex), method="bad")


class TestEndToEndChannelEqualizer:
    """信道 + 均衡器端到端集成测试。"""

    def test_rayleigh_1tap_eq(self):
        """Rayleigh 衰落 + 1-tap MMSE 均衡 → 低 BER。"""
        rng = np.random.default_rng(42)
        n = 500
        tx = (rng.integers(0, 2, n) * 2 - 1).astype(complex)

        # 手动生成 Rayleigh 衰落系数 (准静态)
        h = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2)
        rx_faded = tx * h

        # 手动加噪
        snr_db = 20
        snr_lin = 10.0 ** (snr_db / 10.0)
        noise_var = 1.0 / (2.0 * snr_lin)
        noise = np.sqrt(noise_var) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        rx = rx_faded + noise

        h_arr = np.full(n, h)
        eq = equalize_1tap(rx, h_arr, noise_var=noise_var, method="mmse")
        decisions = np.sign(np.real(eq))
        errors = np.sum(decisions != np.real(tx))
        ber = errors / n
        assert ber < 0.05

    def test_rician_1tap_eq(self):
        """Rician 衰落 + 1-tap MMSE 均衡 → 低 BER。"""
        rng = np.random.default_rng(42)
        n = 500
        tx = (rng.integers(0, 2, n) * 2 - 1).astype(complex)

        # 手动生成 Rician 衰落系数 (K=6dB)
        k_db = 6.0
        k_lin = 10.0 ** (k_db / 10.0)
        los_amp = np.sqrt(k_lin / (k_lin + 1.0))
        scatter_amp = np.sqrt(1.0 / (k_lin + 1.0))
        scatter = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2)
        h = los_amp + scatter_amp * scatter
        rx_faded = tx * h

        snr_db = 20
        snr_lin = 10.0 ** (snr_db / 10.0)
        noise_var = 1.0 / (2.0 * snr_lin)
        noise = np.sqrt(noise_var) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        rx = rx_faded + noise

        h_arr = np.full(n, h)
        eq = equalize_1tap(rx, h_arr, noise_var=noise_var, method="mmse")
        decisions = np.sign(np.real(eq))
        errors = np.sum(decisions != np.real(tx))
        ber = errors / n
        assert ber < 0.02

    def test_multipath_freq_eq(self):
        """多径信道 + 频域 MMSE 均衡端到端。"""
        rng = np.random.default_rng(42)
        n = 128
        tx = (rng.integers(0, 2, n) * 2 - 1).astype(complex)

        # 确定性 2 抽头信道
        h = np.array([1.0, 0.4], dtype=complex)
        h_freq = np.fft.fft(h, n)
        rx_clean = np.fft.ifft(np.fft.fft(tx, n) * h_freq, n)
        noise = 0.05 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        rx = rx_clean + noise

        eq = equalize_mmse_freq(rx, h_freq, noise_var=0.0025)
        decisions = np.sign(np.real(eq))
        errors = np.sum(decisions != np.real(tx))
        ber = errors / n
        assert ber < 0.05

    def test_channel_estimate_then_equalize(self):
        """信道估计 → MMSE 均衡完整流程。"""
        rng = np.random.default_rng(42)
        n = 64

        # 训练序列
        tx_train = np.exp(1j * rng.uniform(0, 2 * np.pi, n))
        # 数据
        tx_data = (rng.integers(0, 2, n) * 2 - 1).astype(complex)

        h = np.array([1.0, 0.3, 0.1], dtype=complex)
        h_freq = np.fft.fft(h, n)

        rx_train = np.fft.ifft(np.fft.fft(tx_train, n) * h_freq, n)
        rx_data = np.fft.ifft(np.fft.fft(tx_data, n) * h_freq, n)
        noise = 0.02 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
        rx_data += noise

        # 估计信道
        h_est = estimate_channel_freq(rx_train, tx_train, n)

        # MMSE 均衡
        eq = equalize_mmse_freq(rx_data, h_est, noise_var=0.0004)
        decisions = np.sign(np.real(eq))
        errors = np.sum(decisions != np.real(tx_data))
        ber = errors / n
        assert ber < 0.1
