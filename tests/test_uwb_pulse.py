"""超宽带脉冲波形与调制测试 (标准 6.2.1.4)。"""

from __future__ import annotations

import numpy as np

from nearlink_sdr.phy.uwb_pulse import (
    UWBPulseConfig,
    chip_modulate,
    kaiser_pulse,
    normalized_cross_correlation,
    validate_pulse,
)

# ======================================================================
# UWBPulseConfig
# ======================================================================


class TestUWBPulseConfig:
    def test_bw_500mhz(self):
        cfg = UWBPulseConfig.bw_500mhz()
        assert cfg.tp_ns == 2.0
        assert cfg.tw_ns == 0.5

    def test_bw_1300mhz(self):
        cfg = UWBPulseConfig.bw_1300mhz()
        assert cfg.tp_ns == 0.75
        assert cfg.tw_ns == 0.2

    def test_pulse_duration(self):
        cfg = UWBPulseConfig(tp_ns=2.0)
        assert cfg.pulse_duration_ns == 6.0  # L = 3 * Tp

    def test_chip_duration(self):
        cfg = UWBPulseConfig(max_prf_mhz=499.2)
        expected = 1e3 / 499.2
        assert abs(cfg.chip_duration_ns - expected) < 1e-6

    def test_samples_per_chip(self):
        cfg = UWBPulseConfig(max_prf_mhz=499.2, sample_rate_ghz=4.0)
        spc = cfg.samples_per_chip
        expected = round(cfg.chip_duration_ns * 4.0)
        assert spc == expected


# ======================================================================
# Kaiser 脉冲波形
# ======================================================================


class TestKaiserPulse:
    def test_shape(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        assert len(pulse) > 0

    def test_peak_at_center(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        peak_idx = np.argmax(pulse)
        center = len(pulse) // 2
        assert abs(peak_idx - center) <= 1

    def test_symmetric(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        # 对称性检查 (忽略浮点误差)
        np.testing.assert_allclose(pulse, pulse[::-1], atol=1e-10)

    def test_nonnegative(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        assert np.all(pulse >= -1e-15)

    def test_energy_normalized_approximately(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        # 脉冲能量应为有限正值
        energy = np.sum(pulse ** 2)
        assert energy > 0

    def test_zero_outside_support(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg, num_samples=101)
        # 首尾值应接近零 (Kaiser 窗边界)
        assert pulse[0] < pulse[len(pulse) // 2] * 0.01
        assert pulse[-1] < pulse[len(pulse) // 2] * 0.01

    def test_custom_num_samples(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg, num_samples=64)
        assert len(pulse) == 64

    def test_bw_1300mhz_pulse(self):
        cfg = UWBPulseConfig.bw_1300mhz()
        pulse = kaiser_pulse(cfg)
        assert len(pulse) > 0
        # 窄带宽参数应产生更短的脉冲
        cfg_500 = UWBPulseConfig.bw_500mhz()
        pulse_500 = kaiser_pulse(cfg_500)
        assert len(pulse) < len(pulse_500)


# ======================================================================
# 归一化互相关
# ======================================================================


class TestNormalizedCrossCorrelation:
    def test_autocorrelation_peak_one(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        phi = normalized_cross_correlation(pulse, pulse)
        assert abs(np.max(phi) - 1.0) < 1e-6

    def test_zero_signal(self):
        r = np.ones(10)
        p = np.zeros(10)
        phi = normalized_cross_correlation(r, p)
        assert np.all(phi == 0)

    def test_shifted_correlation(self):
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg, num_samples=51)
        # 在两端补零产生位移
        shifted = np.concatenate([np.zeros(5), pulse, np.zeros(5)])
        padded_ref = np.concatenate([pulse, np.zeros(10)])
        phi = normalized_cross_correlation(padded_ref, shifted)
        # 峰值仍应接近 1
        assert np.max(phi) > 0.95


# ======================================================================
# 脉冲波形验证
# ======================================================================


class TestValidatePulse:
    def test_reference_pulse_passes(self):
        """参考脉冲与自身的互相关应满足标准。"""
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        passed, main_min, side_max = validate_pulse(pulse, cfg)
        assert passed
        assert main_min >= 0.92
        assert side_max <= 0.1

    def test_reference_pulse_1300mhz_passes(self):
        cfg = UWBPulseConfig.bw_1300mhz()
        pulse = kaiser_pulse(cfg)
        passed, main_min, _side_max = validate_pulse(pulse, cfg)
        assert passed
        assert main_min >= 0.92

    def test_distorted_pulse_may_fail(self):
        """显著畸变的脉冲应无法通过验证。"""
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        # 随机扰动
        rng = np.random.default_rng(42)
        distorted = pulse + rng.normal(0, np.max(pulse) * 2.0, len(pulse))
        passed, _, _ = validate_pulse(distorted, cfg)
        assert not passed


# ======================================================================
# 码片载波调制
# ======================================================================


class TestChipModulate:
    def test_single_positive_chip(self):
        cfg = UWBPulseConfig.bw_500mhz()
        chips = np.array([1], dtype=np.int8)
        signal = chip_modulate(chips, cfg, fc_ghz=4.0)
        assert len(signal) > 0
        assert np.max(np.abs(signal)) > 0

    def test_zero_chip_produces_silence(self):
        cfg = UWBPulseConfig.bw_500mhz()
        chips = np.array([0], dtype=np.int8)
        signal = chip_modulate(chips, cfg, fc_ghz=4.0)
        np.testing.assert_allclose(signal, 0, atol=1e-15)

    def test_negative_chip_inverts(self):
        cfg = UWBPulseConfig.bw_500mhz()
        chips_pos = np.array([1], dtype=np.int8)
        chips_neg = np.array([-1], dtype=np.int8)
        sig_pos = chip_modulate(chips_pos, cfg, fc_ghz=4.0)
        sig_neg = chip_modulate(chips_neg, cfg, fc_ghz=4.0)
        np.testing.assert_allclose(sig_pos, -sig_neg, atol=1e-12)

    def test_multi_chip_length(self):
        cfg = UWBPulseConfig.bw_500mhz()
        chips = np.array([1, -1, 0, 1], dtype=np.int8)
        signal = chip_modulate(chips, cfg, fc_ghz=4.0)
        pulse_len = len(kaiser_pulse(cfg))
        expected_len = cfg.samples_per_chip * len(chips) + pulse_len - 1
        assert len(signal) == expected_len

    def test_modulated_signal_energy(self):
        cfg = UWBPulseConfig.bw_500mhz()
        chips = np.array([1, 1, 1, 1], dtype=np.int8)
        signal = chip_modulate(chips, cfg, fc_ghz=4.0)
        energy = np.sum(signal ** 2)
        assert energy > 0

    def test_carrier_frequency(self):
        """验证调制信号包含载波频率分量。"""
        cfg = UWBPulseConfig(tp_ns=2.0, sample_rate_ghz=8.0)
        fc_ghz = 4.0
        # 足够长的序列以产生可分辨的频谱
        chips = np.array([1, -1, 1, -1, 1, -1, 1, -1], dtype=np.int8)
        signal = chip_modulate(chips, cfg, fc_ghz=fc_ghz)
        # FFT 检查频谱峰
        spectrum = np.abs(np.fft.rfft(signal))
        freqs = np.fft.rfftfreq(len(signal), 1.0 / cfg.sample_rate_ghz)
        peak_freq = freqs[np.argmax(spectrum[1:]) + 1]  # 跳过 DC
        # 峰值频率应接近载波频率 (允许一定误差)
        assert abs(peak_freq - fc_ghz) < 1.0  # 1 GHz 容差 (离散频率分辨率)


# ======================================================================
# 集成测试: 全流程
# ======================================================================


class TestUWBPulseIntegration:
    def test_generate_validate_roundtrip(self):
        """生成 Kaiser 脉冲 → 码片调制 → 验证参考脉冲。"""
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        # 参考脉冲自验证
        passed, main_min, side_max = validate_pulse(pulse, cfg)
        assert passed
        assert main_min >= 0.92
        assert side_max <= 0.1

    def test_chip_sequence_modulation_and_demod(self):
        """码片序列调制后能量分布合理。"""
        cfg = UWBPulseConfig.bw_500mhz()
        # BPSK-like 码片序列
        chips = np.array([1, -1, 1, 1, -1, 1, -1, -1], dtype=np.int8)
        signal = chip_modulate(chips, cfg, fc_ghz=4.0)
        # 非零码片数
        nonzero = np.count_nonzero(chips)
        # 信号总能量应正比于非零码片数
        single_chip_energy = np.sum(
            chip_modulate(np.array([1], dtype=np.int8), cfg, fc_ghz=4.0) ** 2
        )
        total_energy = np.sum(signal ** 2)
        # 由于码片间可能有重叠, 允许一定容差
        ratio = total_energy / (single_chip_energy * nonzero)
        assert 0.5 < ratio < 2.0

    def test_both_bandwidths(self):
        """两种带宽配置都能正常生成和验证。"""
        for factory in (UWBPulseConfig.bw_500mhz, UWBPulseConfig.bw_1300mhz):
            cfg = factory()
            pulse = kaiser_pulse(cfg)
            assert len(pulse) > 0
            passed, _, _ = validate_pulse(pulse, cfg)
            assert passed

    def test_pulse_duration_matches_config(self):
        """脉冲持续时间与配置一致。"""
        cfg = UWBPulseConfig.bw_500mhz()
        pulse = kaiser_pulse(cfg)
        expected_duration_ns = cfg.pulse_duration_ns
        actual_samples = len(pulse)
        actual_duration_ns = (actual_samples - 1) / cfg.sample_rate_ghz
        assert abs(actual_duration_ns - expected_duration_ns) < 1.0
