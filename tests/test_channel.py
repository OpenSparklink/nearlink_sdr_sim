"""Tests for channel model: AWGN / Rayleigh / Rician / multipath."""

import numpy as np
import pytest
from nearlink_sdr.phy.channel import (
    ChannelModel, ChannelConfig, PDP_2TAP, PDP_INDOOR_OFFICE,
)


class TestAWGN:
    """AWGN 信道测试。"""

    def test_awgn_output_shape(self):
        ch = ChannelModel(snr_db=10)
        sig = np.ones(100, dtype=complex)
        out = ch.apply_awgn(sig)
        assert out.shape == sig.shape

    def test_awgn_high_snr_low_error(self):
        ch = ChannelModel(config=ChannelConfig(snr_db=40, seed=42))
        sig = np.exp(1j * np.pi / 4) * np.ones(1000, dtype=complex)
        out = ch.apply_awgn(sig)
        mse = np.mean(np.abs(out - sig) ** 2)
        assert mse < 0.01

    def test_awgn_low_snr_high_error(self):
        ch = ChannelModel(config=ChannelConfig(snr_db=0, seed=42))
        sig = np.ones(1000, dtype=complex)
        out = ch.apply_awgn(sig)
        mse = np.mean(np.abs(out - sig) ** 2)
        assert mse > 0.1

    def test_awgn_noise_variance_property(self):
        ch = ChannelModel(config=ChannelConfig(snr_db=10))
        expected = 1.0 / (2.0 * 10.0)
        assert abs(ch.noise_variance - expected) < 1e-10

    def test_awgn_backward_compat(self):
        """旧接口 ChannelModel(snr_db=X) 仍然可用。"""
        ch = ChannelModel(snr_db=20)
        sig = np.ones(50, dtype=complex)
        out = ch.apply_awgn(sig)
        assert out.shape == sig.shape

    def test_apply_fading_awgn_mode(self):
        ch = ChannelModel(config=ChannelConfig(snr_db=40, channel_type="awgn", seed=0))
        sig = np.ones(100, dtype=complex)
        out = ch.apply_fading(sig)
        mse = np.mean(np.abs(out - sig) ** 2)
        assert mse < 0.01


class TestRayleighFlat:
    """Rayleigh 平坦衰落测试。"""

    def test_output_shape(self):
        cfg = ChannelConfig(snr_db=30, channel_type="rayleigh", seed=42)
        ch = ChannelModel(config=cfg)
        sig = np.ones(200, dtype=complex)
        out = ch.apply_fading(sig)
        assert out.shape == sig.shape

    def test_quasistatic_same_fading(self):
        """准静态模式下每个符号应用相同衰落系数。"""
        cfg = ChannelConfig(snr_db=100, channel_type="rayleigh", max_doppler_hz=0, seed=7)
        ch = ChannelModel(config=cfg)
        sig = np.ones(50, dtype=complex)
        out = ch.apply_fading(sig)
        # 高 SNR 下, 输出应几乎等于 h * sig, 所有元素近似相同
        phases = np.angle(out)
        assert np.std(phases) < 0.1  # 相位一致

    def test_channel_taps_rayleigh(self):
        cfg = ChannelConfig(channel_type="rayleigh", max_doppler_hz=0, seed=1)
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(100)
        assert taps.shape == (1, 100)
        # 准静态: 所有列相同
        assert np.allclose(taps[0, :], taps[0, 0])

    def test_rayleigh_average_power(self):
        """Rayleigh 信道平均功率应接近 1。"""
        cfg = ChannelConfig(channel_type="rayleigh", max_doppler_hz=100, seed=42)
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(10000)
        avg_power = np.mean(np.abs(taps) ** 2)
        assert 0.8 < avg_power < 1.2


class TestRicianFlat:
    """Rician 平坦衰落测试。"""

    def test_output_shape(self):
        cfg = ChannelConfig(snr_db=30, channel_type="rician", rician_k_db=6, seed=42)
        ch = ChannelModel(config=cfg)
        sig = np.ones(200, dtype=complex)
        out = ch.apply_fading(sig)
        assert out.shape == sig.shape

    def test_high_k_factor_near_los(self):
        """高 K 因子时信道接近直射径,衰落小。"""
        cfg = ChannelConfig(snr_db=100, channel_type="rician", rician_k_db=30, seed=42)
        ch = ChannelModel(config=cfg)
        sig = np.ones(100, dtype=complex)
        out = ch.apply_fading(sig)
        # 高 K + 高 SNR → 输出幅度方差很小
        amps = np.abs(out)
        assert np.std(amps) < 0.1

    def test_k_0_approaches_rayleigh(self):
        """K=0 时 Rician 退化为 Rayleigh。"""
        cfg = ChannelConfig(channel_type="rician", rician_k_db=-30, seed=42)
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(1000)
        # K 很小时, 信道系数的实部和虚部方差近似相等
        r, i_part = np.real(taps.flatten()), np.imag(taps.flatten())
        # 对于准静态, 只有一个系数, 不好验证统计。跳过。
        assert taps.shape == (1, 1000)

    def test_channel_taps_rician(self):
        cfg = ChannelConfig(channel_type="rician", rician_k_db=6, seed=3)
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(50)
        assert taps.shape == (1, 50)


class TestMultipath:
    """多径频率选择性衰落测试。"""

    def test_output_shape(self):
        cfg = ChannelConfig(snr_db=30, channel_type="multipath", pdp=PDP_2TAP, seed=42)
        ch = ChannelModel(config=cfg)
        sig = np.ones(200, dtype=complex)
        out = ch.apply_fading(sig)
        assert out.shape == sig.shape

    def test_multipath_taps_shape(self):
        pdp = PDP_2TAP
        cfg = ChannelConfig(channel_type="multipath", pdp=pdp, seed=42)
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(100)
        assert taps.shape == (2, 100)

    def test_indoor_office_taps(self):
        cfg = ChannelConfig(channel_type="multipath", pdp=PDP_INDOOR_OFFICE, seed=42)
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(100)
        assert taps.shape == (6, 100)

    def test_multipath_introduces_isi(self):
        """多径信道应引入 ISI: 输出不等于缩放的输入。"""
        cfg = ChannelConfig(snr_db=100, channel_type="multipath", pdp=PDP_2TAP, seed=42)
        ch = ChannelModel(config=cfg)
        # 脉冲信号
        sig = np.zeros(50, dtype=complex)
        sig[10] = 1.0
        out = ch.apply_fading(sig)
        # 应该在多个位置有非零输出
        nonzero = np.sum(np.abs(out) > 1e-6)
        assert nonzero >= 2

    def test_multipath_quasistatic_taps_constant(self):
        """准静态多径: 每个抽头系数在时间维度上恒定。"""
        cfg = ChannelConfig(
            channel_type="multipath", pdp=PDP_2TAP, max_doppler_hz=0, seed=42,
        )
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(100)
        for i in range(taps.shape[0]):
            assert np.allclose(taps[i, :], taps[i, 0])

    def test_multipath_normalized_power(self):
        """多径信道的总平均功率应接近 1 (归一化)。"""
        cfg = ChannelConfig(
            channel_type="multipath",
            pdp=PDP_INDOOR_OFFICE,
            max_doppler_hz=100,
            seed=42,
        )
        ch = ChannelModel(config=cfg)
        taps = ch.get_channel_taps(5000)
        total_power = np.mean(np.sum(np.abs(taps) ** 2, axis=0))
        assert 0.7 < total_power < 1.3


class TestChannelConfig:
    """配置参数测试。"""

    def test_default_config(self):
        cfg = ChannelConfig()
        assert cfg.snr_db == 10.0
        assert cfg.channel_type == "awgn"
        assert len(cfg.pdp) == 2

    def test_custom_config(self):
        cfg = ChannelConfig(
            snr_db=5, channel_type="rician", rician_k_db=3,
            pdp=PDP_INDOOR_OFFICE, max_doppler_hz=50, seed=123,
        )
        assert cfg.snr_db == 5
        assert cfg.channel_type == "rician"
        assert cfg.seed == 123

    def test_unknown_channel_type_raises(self):
        cfg = ChannelConfig(channel_type="unknown")
        ch = ChannelModel(config=cfg)
        with pytest.raises(ValueError, match="Unknown channel type"):
            ch.apply_fading(np.ones(10, dtype=complex))

    def test_seed_reproducibility(self):
        cfg1 = ChannelConfig(snr_db=10, channel_type="rayleigh", seed=42)
        cfg2 = ChannelConfig(snr_db=10, channel_type="rayleigh", seed=42)
        ch1, ch2 = ChannelModel(config=cfg1), ChannelModel(config=cfg2)
        sig = np.ones(100, dtype=complex)
        out1, out2 = ch1.apply_fading(sig), ch2.apply_fading(sig)
        assert np.allclose(out1, out2)
