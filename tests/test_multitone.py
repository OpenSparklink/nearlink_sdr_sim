"""多音信号测试 -- TXS-10002-2025 标准 6.2.1.3"""

from __future__ import annotations

import numpy as np
import pytest

from nearlink_sdr.phy.multitone import (
    DELTA_F_TABLE,
    MULTITONE_PHASE_SETS,
    MultitoneConfig,
    generate_multitone,
    multitone_peak_to_avg_ratio,
)


class TestMultitoneConfig:
    """配置参数基本校验。"""

    def test_single_tone_freq(self):
        cfg = MultitoneConfig(n_tones=1)
        assert cfg.frequencies_hz == [0.0]
        assert cfg.phases_rad == [0.0]

    def test_delta_f_1mhz_bw(self):
        assert MultitoneConfig(n_tones=2, sle_bandwidth_mhz=1).delta_f_hz == 0.5e6
        assert MultitoneConfig(n_tones=4, sle_bandwidth_mhz=1).delta_f_hz == 0.25e6
        assert MultitoneConfig(n_tones=8, sle_bandwidth_mhz=1).delta_f_hz == 0.125e6

    def test_delta_f_4mhz_bw(self):
        assert MultitoneConfig(n_tones=2, sle_bandwidth_mhz=4).delta_f_hz == 2.0e6

    def test_frequencies_symmetric(self):
        cfg = MultitoneConfig(n_tones=4, sle_bandwidth_mhz=2)
        freqs = cfg.frequencies_hz
        assert len(freqs) == 4
        # 频率应关于 0 对称
        for i in range(len(freqs) // 2):
            assert abs(freqs[i] + freqs[-(i + 1)]) < 1e-6

    def test_phases_n4_set1(self):
        cfg = MultitoneConfig(n_tones=4, phase_set=1)
        assert cfg.phases_rad == MULTITONE_PHASE_SETS[4][1]

    def test_phases_n8_set2(self):
        cfg = MultitoneConfig(n_tones=8, phase_set=2)
        assert cfg.phases_rad == MULTITONE_PHASE_SETS[8][2]


class TestGenerateMultitone:
    """信号生成测试。"""

    def test_single_tone_dc(self):
        """N=1, 频率=0Hz, 结果为常数。"""
        cfg = MultitoneConfig(n_tones=1, amplitude=2.0, sample_rate_hz=1e6)
        sig = generate_multitone(cfg, duration_s=1e-3)
        assert len(sig) == 1000
        np.testing.assert_allclose(np.abs(sig), 2.0, atol=1e-10)

    def test_two_tone_length(self):
        cfg = MultitoneConfig(n_tones=2, sle_bandwidth_mhz=1, sample_rate_hz=4e6)
        sig = generate_multitone(cfg, duration_s=0.5e-3)
        assert len(sig) == 2000

    def test_output_complex(self):
        cfg = MultitoneConfig(n_tones=4, sle_bandwidth_mhz=2)
        sig = generate_multitone(cfg, duration_s=10e-6)
        assert np.iscomplexobj(sig)

    @pytest.mark.parametrize("n_tones", [2, 4, 8])
    def test_peak_power_within_papr(self, n_tones):
        """峰值功率不超过 N * amplitude^2。"""
        amp = 1.0
        cfg = MultitoneConfig(
            n_tones=n_tones, sle_bandwidth_mhz=2,
            amplitude=amp, sample_rate_hz=16e6,
        )
        sig = generate_multitone(cfg, duration_s=1e-3)
        peak = np.max(np.abs(sig))
        # 理论最大: N * amp (所有音同相叠加)
        assert peak <= n_tones * amp + 0.01

    @pytest.mark.parametrize("n_tones,bw", [(2, 1), (4, 2), (8, 4)])
    def test_spectral_content(self, n_tones, bw):
        """验证 FFT 谱线在期望的频率位置。"""
        cfg = MultitoneConfig(
            n_tones=n_tones, sle_bandwidth_mhz=bw,
            sample_rate_hz=16e6, amplitude=1.0,
        )
        sig = generate_multitone(cfg, duration_s=1e-3)
        fft = np.fft.fft(sig)
        freqs = np.fft.fftfreq(len(sig), d=1 / cfg.sample_rate_hz)
        mag = np.abs(fft)
        # 找到最强的 N 个谱线
        top_indices = np.argsort(mag)[-n_tones:]
        top_freqs = sorted(freqs[top_indices])
        expected = sorted(cfg.frequencies_hz)
        for actual, expect in zip(top_freqs, expected, strict=True):
            assert abs(actual - expect) < cfg.sample_rate_hz / len(sig) * 2


class TestPeakToAvgRatio:
    def test_single_tone(self):
        assert multitone_peak_to_avg_ratio(MultitoneConfig(n_tones=1)) == 1.0

    def test_multi_tone(self):
        assert multitone_peak_to_avg_ratio(MultitoneConfig(n_tones=4)) == 4.0
        assert multitone_peak_to_avg_ratio(MultitoneConfig(n_tones=8)) == 8.0


class TestDeltaFTable:
    """验证频率间隔表完整性。"""

    def test_all_bandwidths(self):
        for bw in [1, 2, 4]:
            assert bw in DELTA_F_TABLE
            for n in [2, 4, 8]:
                assert n in DELTA_F_TABLE[bw]

    def test_delta_f_scales_with_bandwidth(self):
        """delta_f 应该与带宽成正比。"""
        for n in [2, 4, 8]:
            df1 = DELTA_F_TABLE[1][n]
            df2 = DELTA_F_TABLE[2][n]
            df4 = DELTA_F_TABLE[4][n]
            assert abs(df2 / df1 - 2.0) < 1e-10
            assert abs(df4 / df1 - 4.0) < 1e-10


class TestPhaseSymmetry:
    """验证标准表中相位的对称性 (首尾对称)。"""

    @pytest.mark.parametrize("n_tones", [4, 8])
    @pytest.mark.parametrize("phase_set", [1, 2])
    def test_symmetric_phases(self, n_tones, phase_set):
        phases = MULTITONE_PHASE_SETS[n_tones][phase_set]
        assert len(phases) == n_tones
        for i in range(n_tones // 2):
            assert abs(phases[i] - phases[-(i + 1)]) < 1e-10
